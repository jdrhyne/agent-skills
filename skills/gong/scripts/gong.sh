#!/usr/bin/env bash
# Read-only helper for bounded Gong API queries.

set -euo pipefail
set +x

readonly DEFAULT_CREDS="${HOME}/.config/gong/credentials.json"
readonly CREDS="${GONG_CREDS:-$DEFAULT_CREDS}"
readonly RETRIES="${GONG_MAX_RETRIES:-3}"
RESULT_TEMPS=()
RESULT_TEMP=""
PAGE_CURSOR=""
STATS_FROM_DATE=""
STATS_TO_DATE=""
STATS_RESPONSE_FROM=""
STATS_RESPONSE_TO=""
STATS_RESPONSE_FROM_INSTANT=""
STATS_RESPONSE_TO_INSTANT=""

cleanup_result_temps() {
  local path
  for path in "${RESULT_TEMPS[@]:-}"; do
    if [[ -n $path && -f $path ]]; then
      rm -f -- "$path" 2>/dev/null || true
    fi
  done
  RESULT_TEMPS=()
}

cleanup_on_exit() {
  local exit_code=$?
  trap - EXIT INT TERM
  cleanup_result_temps
  exit "$exit_code"
}

handle_signal() {
  local exit_code=$1
  trap - EXIT INT TERM
  cleanup_result_temps
  exit "$exit_code"
}

trap cleanup_on_exit EXIT
trap 'handle_signal 130' INT
trap 'handle_signal 143' TERM

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

print_help() {
  cat <<'EOF'
Gong read-only helper

Commands:
  users [max_pages]             List user IDs, names, and active state (default: 5)
  calls [days] [max_pages]      List recent call metadata (defaults: 7, 5)
  call <call_id>                Read bounded call metadata
  transcript <id> [segments]    Read a transcript excerpt (default: 20)
  stats [days] [max_pages]      Read company-timezone activity stats (defaults: 30, 5)
  test                          Probe first user page without exposing credentials

Environment:
  GONG_CREDS                    Credential JSON path
  GONG_MAX_RETRIES              Transient retry count from 0 to 5 (default: 3)
EOF
}

validate_integer() {
  local value=$1
  local minimum=$2
  local maximum=$3
  local label=$4

  [[ $value =~ ^[0-9]+$ ]] || fail "$label must be an integer from $minimum to $maximum"
  ((value >= minimum && value <= maximum)) || fail "$label must be from $minimum to $maximum"
}

path_mode() {
  if stat -f '%Lp' "$1" >/dev/null 2>&1; then
    stat -f '%Lp' "$1"
  else
    stat -c '%a' "$1"
  fi
}

path_owner() {
  if stat -f '%u' "$1" >/dev/null 2>&1; then
    stat -f '%u' "$1"
  else
    stat -c '%u' "$1"
  fi
}

validate_call_id() {
  [[ $1 =~ ^[0-9]{1,20}$ ]] || fail "call_id must contain 1 to 20 decimal digits"
}

iso_days_ago() {
  local days=$1
  if date -u -v-"${days}"d '+%Y-%m-%dT00:00:00Z' >/dev/null 2>&1; then
    date -u -v-"${days}"d '+%Y-%m-%dT00:00:00Z'
  else
    date -u -d "$days days ago" '+%Y-%m-%dT00:00:00Z'
  fi
}

validate_iso_date() {
  local value=$1
  local label=$2
  local normalized

  [[ $value =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || fail "$label must use YYYY-MM-DD"
  if normalized=$(date -j -f '%Y-%m-%d' "$value" '+%Y-%m-%d' 2>/dev/null); then
    :
  elif normalized=$(date -u -d "$value" '+%Y-%m-%d' 2>/dev/null); then
    :
  else
    fail "$label is not a valid calendar date"
  fi
  [[ $normalized == "$value" ]] || fail "$label is not a valid calendar date"
}

escape_curl_config() {
  local value=$1
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  printf '%s' "$value"
}

cmd=${1:-help}
if (($# > 0)); then
  shift
fi

case $cmd in
  help|-h|--help)
    print_help
    exit 0
    ;;
esac

require_command jq
require_command curl
validate_integer "$RETRIES" 0 5 GONG_MAX_RETRIES

CREDS_PARENT=$(dirname -- "$CREDS")
[[ -f $CREDS && ! -L $CREDS ]] || fail "Credentials must be a regular non-symbolic-link file: $CREDS"
[[ $(path_owner "$CREDS") == "$(id -u)" ]] || fail "Credential file must be owned by the current user: $CREDS"
[[ $(path_mode "$CREDS") == 600 ]] || fail "Credential file must have mode 0600: $CREDS"
CREDS_PARENT_MODE=$(path_mode "$CREDS_PARENT")
[[ $CREDS_PARENT_MODE =~ ^[0-7]{3,4}$ ]] || fail "Could not validate credential directory permissions: $CREDS_PARENT"
CREDS_PARENT_ACCESS=${CREDS_PARENT_MODE: -2}
[[ $CREDS_PARENT_ACCESS == 00 ]] || fail "Credential directory must reject group and other access: $CREDS_PARENT"

BASE=$(jq -er '.base_url | strings | select(length > 0)' "$CREDS") || fail "Credential file is missing base_url"
ACCESS_KEY=$(jq -er '.access_key | strings | select(length > 0)' "$CREDS") || fail "Credential file is missing access_key"
SECRET_KEY=$(jq -er '.secret_key | strings | select(length > 0)' "$CREDS") || fail "Credential file is missing secret_key"
if ! jq -e '
  (has("company_timezone") | not)
  or ((.company_timezone | type) == "string")
' "$CREDS" >/dev/null; then
  fail "company_timezone must be a string when present"
fi
COMPANY_TIMEZONE=$(jq -r '.company_timezone // ""' "$CREDS")

[[ $BASE =~ ^https://[A-Za-z0-9.-]+\.api\.gong\.io/?$ ]] || fail "base_url must be an https://*.api.gong.io tenant URL"
BASE=${BASE%/}
[[ $ACCESS_KEY != *$'\n'* && $ACCESS_KEY != *$'\r'* && $SECRET_KEY != *$'\n'* && $SECRET_KEY != *$'\r'* ]] || fail "Credential values must not contain line breaks"
[[ $COMPANY_TIMEZONE != *$'\n'* && $COMPANY_TIMEZONE != *$'\r'* && $COMPANY_TIMEZONE != *$'\t'* ]] || fail "company_timezone must not contain control characters"

readonly BASE ACCESS_KEY SECRET_KEY COMPANY_TIMEZONE

api() {
  local method=$1
  local endpoint=$2
  local body=${3:-}
  local cursor=${4:-}
  local escaped_access
  local escaped_secret
  local -a args

  [[ $endpoint == /v2/* && $endpoint != *..* ]] || fail "Refusing unexpected Gong endpoint"

  escaped_access=$(escape_curl_config "$ACCESS_KEY")
  escaped_secret=$(escape_curl_config "$SECRET_KEY")
  args=(
    --config -
    --silent
    --show-error
    --fail-with-body
    --retry "$RETRIES"
    --retry-delay 1
    --retry-max-time 15
    --connect-timeout 10
    --max-time 60
    --request "$method"
    --url "$BASE$endpoint"
    --header 'Content-Type: application/json'
  )
  if [[ -n $body ]]; then
    args+=(--data-binary "$body")
  fi
  if [[ -n $cursor ]]; then
    [[ $method == GET && $endpoint == /v2/users ]] || fail "Cursor query is allowed only for the users endpoint"
    [[ ${#cursor} -le 4096 && $cursor != *$'\n'* && $cursor != *$'\r'* ]] || fail "Gong returned an invalid pagination cursor"
    args+=(--get --data-urlencode "cursor=$cursor")
  fi

  printf 'user = "%s:%s"\n' "$escaped_access" "$escaped_secret" | curl "${args[@]}"
}

cleanup_temp_and_fail() {
  local path=$1
  shift
  remove_result_temp "$path"
  fail "$*"
}

register_result_temp() {
  umask 077
  RESULT_TEMP=$(mktemp) || fail "Could not create a temporary result file"
  RESULT_TEMPS+=("$RESULT_TEMP")
  if ! chmod 600 "$RESULT_TEMP"; then
    cleanup_temp_and_fail "$RESULT_TEMP" "Could not protect a temporary result file"
  fi
}

remove_result_temp() {
  local target=$1
  local path
  local -a remaining=()

  rm -f -- "$target"
  for path in "${RESULT_TEMPS[@]:-}"; do
    if [[ $path != "$target" ]]; then
      remaining+=("$path")
    fi
  done
  # The `:-` form keeps Bash 3.2 + nounset portable when the array is empty.
  RESULT_TEMPS=("${remaining[@]:-}")
}

extract_cursor() {
  local response=$1
  local cursor
  local LC_ALL=C

  if ! cursor=$(printf '%s' "$response" | jq -er '
    if (.records | type) != "object" then error("records must be an object")
    elif (.records | has("cursor") | not) or .records.cursor == null then ""
    elif (.records.cursor | type) != "string" then error("cursor must be a string or null")
    elif (.records.cursor | length) == 0 then error("cursor must not be empty when present")
    elif (.records.cursor | test("[\\r\\n]")) then error("cursor must not contain line breaks")
    else .records.cursor
    end
  '); then
    return 1
  fi
  ((${#cursor} <= 4096)) || return 1
  PAGE_CURSOR="$cursor"
}

validate_users_page() {
  local response=$1
  printf '%s' "$response" | jq -e '
    if (.users | type) != "array" then false
    else all(.users[];
      (type == "object")
      and ((.id | type) == "string")
      and (.id | test("^[0-9]{1,20}$"))
      and ((.firstName | type) == "string")
      and ((.lastName | type) == "string")
      and ((.firstName + " " + .lastName) | test("[^[:space:]]"))
      and ((.active | type) == "boolean")
    )
    end
  ' >/dev/null
}

validate_calls_page() {
  local response=$1
  printf '%s' "$response" | jq -e '
    if (.calls | type) != "array" then false
    else all(.calls[];
      (type == "object")
      and ((.metaData | type) == "object")
      and ((.metaData.id | type) == "string")
      and (.metaData.id | test("^[0-9]{1,20}$"))
      and ((.metaData.title | type) == "string")
      and ((.metaData.title | length) > 0)
      and ((.metaData.started | type) == "string")
      and (.metaData.started | test("^[0-9]{4}-[0-9]{2}-[0-9]{2}T"))
      and ((.metaData.duration | type) == "number")
      and (.metaData.duration >= 0)
      and ((.metaData.url | type) == "string")
      and ((.metaData.url | length) > 0)
    )
    end
  ' >/dev/null
}

validate_stats_page() {
  local response=$1
  printf '%s' "$response" | jq -e '
    if (.usersAggregateActivityStats | type) != "array" then false
    else all(.usersAggregateActivityStats[];
      . as $record
      | (type == "object")
        and (($record.userId | type) == "string")
        and ($record.userId | test("^[0-9]{1,20}$"))
        and (($record.userEmailAddress | type) == "string")
        and (($record.userEmailAddress | length) > 0)
        and (($record.userAggregateActivityStats | type) == "object")
        and (($record.userAggregateActivityStats | length) > 0)
        and all($record.userAggregateActivityStats[];
          (type == "number")
          and (. >= 0)
          and ((floor) == .)
        )
    )
    end
  ' >/dev/null
}

compute_stats_dates() {
  local timezone_name=$1
  local days=$2
  local dates

  [[ -n $timezone_name && ${#timezone_name} -le 255 ]] || \
    fail "company_timezone is required for stats and must be a valid IANA timezone"
  [[ $timezone_name != *$'\n'* && $timezone_name != *$'\r'* && $timezone_name != *$'\t'* ]] || \
    fail "company_timezone must not contain control characters"
  require_command python3
  if ! dates=$(python3 - "$timezone_name" "$days" 2>/dev/null <<'PY'
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import sys

zone = ZoneInfo(sys.argv[1])
today = datetime.now(zone).date()
start = today - timedelta(days=int(sys.argv[2]))
print(f"{start.isoformat()}\t{today.isoformat()}")
PY
  ); then
    fail "company_timezone is not available through Python zoneinfo: $timezone_name"
  fi
  IFS=$'\t' read -r STATS_FROM_DATE STATS_TO_DATE <<<"$dates"
  validate_iso_date "$STATS_FROM_DATE" fromDate
  validate_iso_date "$STATS_TO_DATE" toDate
  [[ $STATS_FROM_DATE < $STATS_TO_DATE ]] || fail "fromDate must be earlier than exclusive toDate"
}

validate_stats_provenance() {
  local response=$1
  local timezone_name=$2
  local from_date=$3
  local to_date=$4
  local fields
  local response_from
  local response_to
  local canonical
  local canonical_from
  local canonical_to

  if ! fields=$(printf '%s' "$response" | jq -er --arg timezone "$timezone_name" '
    .records as $records
    | select(($records | type) == "object")
    | select(($records.timeZone | type) == "string" and ($records.timeZone | length) > 0)
    | select($records.timeZone == $timezone)
    | select(($records.fromDateTime | type) == "string")
    | select(($records.toDateTime | type) == "string")
    | select($records.fromDateTime | test("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$"))
    | select($records.toDateTime | test("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$"))
    | [$records.fromDateTime, $records.toDateTime]
    | @tsv
  '); then
    return 1
  fi
  IFS=$'\t' read -r response_from response_to <<<"$fields"
  if ! canonical=$(python3 - "$timezone_name" "$from_date" "$to_date" "$response_from" "$response_to" 2>/dev/null <<'PY'
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
import sys

zone = ZoneInfo(sys.argv[1])
expected_from, expected_to = sys.argv[2], sys.argv[3]
start = datetime.fromisoformat(sys.argv[4].replace("Z", "+00:00"))
end = datetime.fromisoformat(sys.argv[5].replace("Z", "+00:00"))
expected_start = datetime.combine(date.fromisoformat(expected_from), time.min, tzinfo=zone)
expected_end = datetime.combine(date.fromisoformat(expected_to), time.min, tzinfo=zone)
if start.tzinfo is None or end.tzinfo is None:
    raise SystemExit(1)
if start != expected_start or end != expected_end:
    raise SystemExit(1)
print(
    start.astimezone(timezone.utc).isoformat(),
    end.astimezone(timezone.utc).isoformat(),
    sep="\t",
)
PY
  ); then
    return 1
  fi
  IFS=$'\t' read -r canonical_from canonical_to <<<"$canonical"
  if [[ -z $STATS_RESPONSE_FROM ]]; then
    STATS_RESPONSE_FROM="$response_from"
    STATS_RESPONSE_TO="$response_to"
    STATS_RESPONSE_FROM_INSTANT="$canonical_from"
    STATS_RESPONSE_TO_INSTANT="$canonical_to"
  elif [[ $STATS_RESPONSE_FROM_INSTANT != "$canonical_from" || $STATS_RESPONSE_TO_INSTANT != "$canonical_to" ]]; then
    return 1
  fi
}

validate_exact_transcript() {
  local response=$1
  local call_id=$2
  printf '%s' "$response" | jq -e --arg call_id "$call_id" '
    (.callTranscripts | type) == "array"
    and (.callTranscripts | length) == 1
    and (.callTranscripts[0] | type) == "object"
    and (.callTranscripts[0].callId | type) == "string"
    and .callTranscripts[0].callId == $call_id
    and (.callTranscripts[0].transcript | type) == "array"
    and all(.callTranscripts[0].transcript[];
      (type == "object")
      and ((.speakerId | type) == "string")
      and ((.speakerId | length) > 0)
      and ((.sentences | type) == "array")
      and all(.sentences[];
        (type == "object")
        and ((.text | type) == "string")
        and ((.text | length) > 0)
      )
    )
  ' >/dev/null
}

list_users() {
  local max_pages=${1:-5}
  local response
  local cursor=
  local page=0
  local has_more=false
  local results_file
  local page_rows

  validate_integer "$max_pages" 1 20 max_pages
  register_result_temp
  results_file="$RESULT_TEMP"

  while ((page < max_pages)); do
    if ! response=$(api GET /v2/users "" "$cursor"); then
      cleanup_temp_and_fail "$results_file" "Gong users API request failed"
    fi
    if ! validate_users_page "$response"; then
      cleanup_temp_and_fail "$results_file" "Gong returned a malformed users response"
    fi
    if ! page_rows=$(printf '%s' "$response" | jq -c '.users[] | {id,name: ((.firstName + " " + .lastName) | gsub("^ +| +$"; "")),active}'); then
      cleanup_temp_and_fail "$results_file" "Could not minimize the Gong users response"
    fi
    if [[ -n $page_rows ]] && ! printf '%s\n' "$page_rows" >>"$results_file"; then
      cleanup_temp_and_fail "$results_file" "Could not store the bounded users result"
    fi
    page=$((page + 1))
    if ! extract_cursor "$response"; then
      cleanup_temp_and_fail "$results_file" "Gong returned a malformed users cursor"
    fi
    cursor="$PAGE_CURSOR"
    [[ -n $cursor ]] || break
  done

  if [[ -n $cursor ]]; then
    has_more=true
  fi
  if ! jq -s --argjson pages "$page" --argjson has_more "$has_more" \
    '{pages:$pages,returned:length,has_more:$has_more,users:.}' "$results_file"; then
    cleanup_temp_and_fail "$results_file" "Could not assemble the bounded users result"
  fi
  remove_result_temp "$results_file"
}

list_calls() {
  local days=${1:-7}
  local max_pages=${2:-5}
  local from
  local to
  local request
  local response
  local cursor
  local has_more=false
  local page=0
  local results_file
  local page_rows

  validate_integer "$days" 1 365 days
  validate_integer "$max_pages" 1 20 max_pages
  from=$(iso_days_ago "$days")
  to=$(date -u '+%Y-%m-%dT23:59:59Z')
  request=$(jq -cn --arg from "$from" --arg to "$to" '{filter:{fromDateTime:$from,toDateTime:$to},contentSelector:{}}')
  register_result_temp
  results_file="$RESULT_TEMP"

  while ((page < max_pages)); do
    if ! response=$(api POST /v2/calls/extensive "$request"); then
      cleanup_temp_and_fail "$results_file" "Gong calls API request failed"
    fi
    if ! validate_calls_page "$response"; then
      cleanup_temp_and_fail "$results_file" "Gong returned a malformed calls response"
    fi
    if ! page_rows=$(printf '%s' "$response" | jq -c '.calls[] | {id:.metaData.id,title:.metaData.title,started:.metaData.started,duration_min:(.metaData.duration / 60 | floor),url:.metaData.url}'); then
      cleanup_temp_and_fail "$results_file" "Could not minimize the Gong calls response"
    fi
    if [[ -n $page_rows ]] && ! printf '%s\n' "$page_rows" >>"$results_file"; then
      cleanup_temp_and_fail "$results_file" "Could not store the bounded calls result"
    fi
    page=$((page + 1))
    if ! extract_cursor "$response"; then
      cleanup_temp_and_fail "$results_file" "Gong returned a malformed calls cursor"
    fi
    cursor="$PAGE_CURSOR"
    [[ -n $cursor ]] || break
    if ! request=$(printf '%s' "$request" | jq -c --arg cursor "$cursor" '. + {cursor:$cursor}'); then
      cleanup_temp_and_fail "$results_file" "Could not construct the next calls page request"
    fi
  done

  if [[ -n $cursor ]]; then
    has_more=true
  fi
  if ! jq -s --argjson pages "$page" --argjson has_more "$has_more" \
    '{pages:$pages,returned:length,has_more:$has_more,calls:.}' "$results_file"; then
    cleanup_temp_and_fail "$results_file" "Could not assemble the bounded calls result"
  fi
  remove_result_temp "$results_file"
}

call_metadata() {
  local call_id=$1
  local response
  validate_call_id "$call_id"
  response=$(api GET "/v2/calls/$call_id")
  if ! printf '%s' "$response" | jq -e --arg call_id "$call_id" '
    (.call | type) == "object"
    and (.call | length) > 0
    and (.call.id | type) == "string"
    and .call.id == $call_id
    and (.call.title | type) == "string"
    and (.call.title | length) > 0
    and (.call.started | type) == "string"
    and (.call.started | test("^[0-9]{4}-[0-9]{2}-[0-9]{2}T"))
    and (.call.duration | type) == "number"
    and (.call.duration >= 0)
    and (.call.url | type) == "string"
    and (.call.url | length) > 0
  ' >/dev/null; then
    fail "Gong returned no single exact call object for call_id $call_id"
  fi
  printf '%s' "$response" | jq '.call | {id,title,started,duration,url}'
}

transcript_excerpt() {
  local call_id=$1
  local max_segments=${2:-20}
  local body
  local response
  local excerpt
  validate_call_id "$call_id"
  validate_integer "$max_segments" 1 100 max_segments
  body=$(jq -cn --arg call_id "$call_id" '{filter:{callIds:[$call_id]}}')
  response=$(api POST /v2/calls/transcript "$body")
  if ! validate_exact_transcript "$response" "$call_id"; then
    fail "Gong returned no single exact transcript object for call_id $call_id"
  fi
  excerpt=$(printf '%s' "$response" | jq -r --argjson limit "$max_segments" '
    [.callTranscripts[0].transcript[]? as $turn
      | $turn.sentences[]?
      | {speaker: $turn.speakerId, text: .text}]
    | .[:$limit][]
    | "\(.speaker): \(.text)"
  ')
  [[ -n $excerpt ]] || fail "Transcript for call_id $call_id has no available segments"
  printf '%s\n' "$excerpt"
}

activity_stats() {
  local days=${1:-30}
  local max_pages=${2:-5}
  local from
  local to
  local request
  local response
  local cursor=
  local page=0
  local has_more=false
  local results_file
  local page_rows

  validate_integer "$days" 1 365 days
  validate_integer "$max_pages" 1 20 max_pages
  compute_stats_dates "$COMPANY_TIMEZONE" "$days"
  from="$STATS_FROM_DATE"
  to="$STATS_TO_DATE"
  STATS_RESPONSE_FROM=""
  STATS_RESPONSE_TO=""
  STATS_RESPONSE_FROM_INSTANT=""
  STATS_RESPONSE_TO_INSTANT=""
  request=$(jq -cn --arg from "$from" --arg to "$to" '{filter:{fromDate:$from,toDate:$to}}')
  register_result_temp
  results_file="$RESULT_TEMP"

  while ((page < max_pages)); do
    if ! response=$(api POST /v2/stats/activity/aggregate "$request"); then
      cleanup_temp_and_fail "$results_file" "Gong activity statistics API request failed"
    fi
    if ! validate_stats_page "$response"; then
      cleanup_temp_and_fail "$results_file" "Gong returned a malformed activity statistics response"
    fi
    if ! validate_stats_provenance "$response" "$COMPANY_TIMEZONE" "$from" "$to"; then
      cleanup_temp_and_fail "$results_file" "Gong returned malformed or mismatched activity statistics provenance"
    fi
    if ! page_rows=$(printf '%s' "$response" | jq -c '
      .usersAggregateActivityStats[]
      | {userId,userEmailAddress,userAggregateActivityStats}
    '); then
      cleanup_temp_and_fail "$results_file" "Could not minimize the Gong activity statistics response"
    fi
    if [[ -n $page_rows ]] && ! printf '%s\n' "$page_rows" >>"$results_file"; then
      cleanup_temp_and_fail "$results_file" "Could not store the bounded activity statistics result"
    fi
    page=$((page + 1))
    if ! extract_cursor "$response"; then
      cleanup_temp_and_fail "$results_file" "Gong returned a malformed activity statistics cursor"
    fi
    cursor="$PAGE_CURSOR"
    [[ -n $cursor ]] || break
    if ! request=$(printf '%s' "$request" | jq -c --arg cursor "$cursor" '. + {cursor:$cursor}'); then
      cleanup_temp_and_fail "$results_file" "Could not construct the next activity statistics page request"
    fi
  done

  if [[ -n $cursor ]]; then
    has_more=true
  fi
  if ! jq -s \
    --argjson pages "$page" \
    --argjson has_more "$has_more" \
    --arg from_date "$from" \
    --arg to_date "$to" \
    --arg timezone "$COMPANY_TIMEZONE" \
    --arg response_from "$STATS_RESPONSE_FROM" \
    --arg response_to "$STATS_RESPONSE_TO" \
    '{
      range: {
        fromDate: $from_date,
        toDate: $to_date,
        toDateExclusive: true,
        timeZone: $timezone,
        fromDateTime: $response_from,
        toDateTime: $response_to
      },
      pages: $pages,
      returned: length,
      has_more: $has_more,
      usersAggregateActivityStats: .
    }' "$results_file"; then
    cleanup_temp_and_fail "$results_file" "Could not assemble the bounded activity statistics result"
  fi
  remove_result_temp "$results_file"
}

connection_test() {
  local response
  local first_page_count
  local has_more=false

  response=$(api GET /v2/users) || fail "Gong users connectivity probe failed"
  if ! validate_users_page "$response"; then
    fail "Gong returned a malformed users response"
  fi
  if ! extract_cursor "$response"; then
    fail "Gong returned a malformed users cursor"
  fi
  if ! first_page_count=$(printf '%s' "$response" | jq -er '.users | length'); then
    fail "Could not count the first Gong users page"
  fi
  if [[ -n $PAGE_CURSOR ]]; then
    has_more=true
  fi
  jq -cn --argjson count "$first_page_count" --argjson has_more "$has_more" \
    '{connected:true,first_page_user_count:$count,first_page_has_more:$has_more}'
}

case $cmd in
  users)
    (($# <= 1)) || fail "Usage: gong.sh users [max_pages]"
    list_users "${1:-5}"
    ;;
  calls)
    (($# <= 2)) || fail "Usage: gong.sh calls [days] [max_pages]"
    list_calls "${1:-7}" "${2:-5}"
    ;;
  call)
    (($# == 1)) || fail "Usage: gong.sh call <call_id>"
    call_metadata "$1"
    ;;
  transcript)
    (($# >= 1 && $# <= 2)) || fail "Usage: gong.sh transcript <call_id> [max_segments]"
    transcript_excerpt "$1" "${2:-20}"
    ;;
  stats)
    (($# <= 2)) || fail "Usage: gong.sh stats [days] [max_pages]"
    activity_stats "${1:-30}" "${2:-5}"
    ;;
  test)
    (($# == 0)) || fail "Usage: gong.sh test"
    connection_test
    ;;
  *)
    fail "Unknown command: $cmd"
    ;;
esac
