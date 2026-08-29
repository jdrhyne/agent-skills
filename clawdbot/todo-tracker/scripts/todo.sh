#!/usr/bin/env bash

set -euo pipefail

TODO_FILE="${TODO_FILE:-$PWD/TODO.md}"
TODAY="${TODO_DATE:-$(date +%Y-%m-%d)}"
LOCK_DIR="${TODO_FILE}.lock"
COUNTER_FILE="${TODO_FILE}.next-id"
LOCK_HELD=0
TEMP_FILES=()
NEW_TEMP=""
SOURCE_FILE=""
COUNTER_VALUE=""
RESERVED_FIRST=""

cleanup() {
    local path
    for path in "${TEMP_FILES[@]:-}"; do
        if [[ -n "$path" && -f "$path" ]]; then
            rm -f -- "$path"
        fi
    done
    if [[ "$LOCK_HELD" -eq 1 && -d "$LOCK_DIR" ]]; then
        rmdir -- "$LOCK_DIR" 2>/dev/null || true
    fi
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

usage() {
    cat <<'EOF'
Usage: todo.sh <command> [args]
  add <high|medium|low> <item>         Add a unique open task and print its ID
  done <ID|exact-text>                 Mark one exact open task done
  remove <ID|exact-text>               Preview removal and print confirmation command
  remove <ID> --confirm <same-ID>      Remove one already-approved exact task
  list [high|medium|low|done]          Read tasks without creating a file
  summary                              Read count-only summary
  heartbeat                            Count-only summary when explicitly enabled

Set TODO_FILE to choose the task file. It defaults to TODO.md in the current workspace.
EOF
}

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

require_parent_directory() {
    local parent
    parent=$(dirname -- "$TODO_FILE")
    [[ -d "$parent" ]] || die "TODO parent directory does not exist: $parent"
    [[ ! -L "$TODO_FILE" ]] || die "Refusing to replace a symbolic-link TODO file: $TODO_FILE"
    if [[ -e "$TODO_FILE" && ! -f "$TODO_FILE" ]]; then
        die "TODO path is not a regular file: $TODO_FILE"
    fi
    [[ ! -L "$COUNTER_FILE" ]] || die "Refusing a symbolic-link ID counter: $COUNTER_FILE"
    if [[ -e "$COUNTER_FILE" && ! -f "$COUNTER_FILE" ]]; then
        die "TODO ID counter is not a regular file: $COUNTER_FILE"
    fi
}

acquire_lock() {
    require_parent_directory
    umask 077
    if ! mkdir -- "$LOCK_DIR" 2>/dev/null; then
        die "TODO file is locked by another writer: $LOCK_DIR"
    fi
    chmod 700 "$LOCK_DIR"
    LOCK_HELD=1
}

make_temp_for() {
    local destination="$1"
    local parent
    local base
    parent=$(dirname -- "$destination")
    base=$(basename -- "$destination")
    NEW_TEMP=$(mktemp "$parent/.${base}.tmp.XXXXXX")
    chmod 600 "$NEW_TEMP"
    TEMP_FILES+=("$NEW_TEMP")
}

make_temp() {
    make_temp_for "$TODO_FILE"
}

write_initial_file() {
    local destination="$1"
    cat >"$destination" <<EOF
# TODO Tracker

*Last updated: $TODAY*

## 🔴 High Priority

## 🟡 Medium Priority

## 🟢 Nice to Have

## ✅ Done
EOF
    chmod 600 "$destination"
}

max_task_number() {
    local files=()
    local path

    for path in "$@"; do
        if [[ -f "$path" ]]; then
            files+=("$path")
        fi
    done
    if [[ "${#files[@]}" -eq 0 ]]; then
        printf '0\n'
        return
    fi

    awk '
        /^- \[[ x]\] \[T[0-9][0-9][0-9][0-9][0-9][0-9]\] / {
            value = substr($0, 9, 6) + 0
            if (value > max) max = value
        }
        END { print max + 0 }
    ' "${files[@]}"
}

file_mode() {
    if stat -f '%Lp' "$1" >/dev/null 2>&1; then
        stat -f '%Lp' "$1"
    else
        stat -c '%a' "$1"
    fi
}

read_counter() {
    local value

    [[ -f "$COUNTER_FILE" && ! -L "$COUNTER_FILE" ]] || \
        die "TODO ID counter is missing or not a regular file: $COUNTER_FILE"
    [[ "$(file_mode "$COUNTER_FILE")" == "600" ]] || \
        die "TODO ID counter must have mode 0600: $COUNTER_FILE"
    value=$(<"$COUNTER_FILE")
    [[ "$value" =~ ^[1-9][0-9]*$ ]] || \
        die "TODO ID counter is corrupt; expected one positive decimal integer: $COUNTER_FILE"
    ((value <= 1000000)) || die "TODO ID counter exceeds the T999999 ID limit"
    printf '%s\n' "$value"
}

persist_counter() {
    local value="$1"
    local counter_temp

    ((value >= 1 && value <= 1000000)) || die "TODO ID counter exceeds the T999999 ID limit"
    make_temp_for "$COUNTER_FILE"
    counter_temp="$NEW_TEMP"
    printf '%s\n' "$value" >"$counter_temp"
    chmod 600 "$counter_temp"
    mv -f -- "$counter_temp" "$COUNTER_FILE"
}

ensure_counter() {
    local observed_next
    local counter_value

    observed_next=$(($(max_task_number "$TODO_FILE" "${TODO_FILE}.bak") + 1))
    if [[ -e "$COUNTER_FILE" ]]; then
        counter_value=$(read_counter)
        if ((counter_value < observed_next)); then
            persist_counter "$observed_next"
            counter_value="$observed_next"
        fi
    else
        persist_counter "$observed_next"
        counter_value="$observed_next"
    fi
    COUNTER_VALUE="$counter_value"
}

reserve_ids() {
    local count="$1"
    local first
    local next

    ((count >= 1)) || die "Internal error: ID reservation count must be positive"
    ensure_counter
    first="$COUNTER_VALUE"
    next=$((first + count))
    ((next <= 1000000)) || die "No stable task IDs remain after T999999"

    # Persist the reservation before the task file is published. A crash may leave
    # a gap, but a later writer will never reuse an allocated ID.
    persist_counter "$next"
    RESERVED_FIRST="$first"
}

legacy_task_count() {
    awk '
        /^- \[[ x]\] / && $0 !~ /^- \[[ x]\] \[T[0-9][0-9][0-9][0-9][0-9][0-9]\] / { count++ }
        END { print count + 0 }
    ' "$1"
}

prepare_source() {
    local legacy_count
    local next_number

    if [[ ! -f "$TODO_FILE" ]]; then
        make_temp
        write_initial_file "$NEW_TEMP"
        SOURCE_FILE="$NEW_TEMP"
        return
    fi

    # Tombstone every ID already visible in the current file or its recoverable
    # backup before a mutation can remove either copy.
    ensure_counter >/dev/null

    legacy_count=$(legacy_task_count "$TODO_FILE")
    if [[ "$legacy_count" -eq 0 ]]; then
        SOURCE_FILE="$TODO_FILE"
        return
    fi

    reserve_ids "$legacy_count"
    next_number="$RESERVED_FIRST"
    make_temp
    awk -v next_number="$next_number" '
        /^- \[[ x]\] / && $0 !~ /^- \[[ x]\] \[T[0-9][0-9][0-9][0-9][0-9][0-9]\] / {
            printf "%s[T%06d] %s\n", substr($0, 1, 6), next_number, substr($0, 7)
            next_number++
            next
        }
        { print }
    ' "$TODO_FILE" >"$NEW_TEMP"
    SOURCE_FILE="$NEW_TEMP"
}

commit_file() {
    local replacement="$1"
    local backup_temp

    if [[ -f "$TODO_FILE" ]]; then
        make_temp
        backup_temp="$NEW_TEMP"
        cp -- "$TODO_FILE" "$backup_temp"
        chmod 600 "$backup_temp"
        mv -f -- "$backup_temp" "${TODO_FILE}.bak"
    fi

    chmod 600 "$replacement"
    mv -f -- "$replacement" "$TODO_FILE"
}

validate_item_text() {
    local item="$1"
    [[ -n "$item" ]] || die "Task text must not be empty"
    [[ "$item" != *$'\n'* && "$item" != *$'\r'* && "$item" != *$'\t'* ]] || \
        die "Task text must be a single line without tabs"
}

active_exact_count() {
    local file="$1"
    local target="$2"
    TODO_AWK_TARGET="$target" awk '
        BEGIN { target = ENVIRON["TODO_AWK_TARGET"] }
        /^- \[ \] / {
            text = $0
            sub(/^- \[ \] \[T[0-9][0-9][0-9][0-9][0-9][0-9]\] /, "", text)
            sub(/ \(added: [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]\)$/, "", text)
            if (text == target) count++
        }
        END { print count + 0 }
    ' "$file"
}

find_matches() {
    local file="$1"
    local target="$2"
    local state="$3"
    local id_mode=0
    if [[ "$target" =~ ^T[0-9]{6}$ ]]; then
        id_mode=1
    fi

    TODO_AWK_TARGET="$target" awk -v state="$state" -v id_mode="$id_mode" '
        BEGIN { target = ENVIRON["TODO_AWK_TARGET"] }
        /^- \[[ x]\] \[T[0-9][0-9][0-9][0-9][0-9][0-9]\] / {
            if (state == "open" && $0 !~ /^- \[ \] /) next
            id = substr($0, 8, 7)
            text = $0
            sub(/^- \[[ x]\] \[T[0-9][0-9][0-9][0-9][0-9][0-9]\] /, "", text)
            sub(/ \((added|done): [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]\)$/, "", text)
            if ((id_mode && id == target) || (!id_mode && text == target)) {
                printf "%d\t%s\t%s\n", NR, id, text
            }
        }
    ' "$file"
}

resolve_target() {
    local file="$1"
    local target="$2"
    local state="$3"
    local matches
    local count

    matches=$(find_matches "$file" "$target" "$state")
    count=$(printf '%s\n' "$matches" | awk 'NF { count++ } END { print count + 0 }')
    if [[ "$count" -eq 0 ]]; then
        die "No exact $state task found for: $target"
    fi
    if [[ "$count" -gt 1 ]]; then
        printf 'ERROR: Ambiguous exact text matched %s tasks; use one stable ID:\n%s\n' "$count" "$matches" >&2
        exit 2
    fi
    printf '%s\n' "$matches"
}

section_for_priority() {
    case "$1" in
        high) printf '%s\n' '## 🔴 High Priority' ;;
        medium) printf '%s\n' '## 🟡 Medium Priority' ;;
        low) printf '%s\n' '## 🟢 Nice to Have' ;;
        *) die "Priority must be high, medium, or low" ;;
    esac
}

add_item() {
    local priority="$1"
    local item="$2"
    local section
    local next_number
    local task_id
    local entry
    local output

    validate_item_text "$item"
    section=$(section_for_priority "$priority")
    acquire_lock
    prepare_source

    if [[ "$(active_exact_count "$SOURCE_FILE" "$item")" -gt 0 ]]; then
        die "An open task with that exact text already exists; use its stable ID"
    fi

    reserve_ids 1
    next_number="$RESERVED_FIRST"
    printf -v task_id 'T%06d' "$next_number"
    entry="- [ ] [$task_id] $item (added: $TODAY)"
    make_temp
    output="$NEW_TEMP"
    if ! TODO_AWK_ENTRY="$entry" awk -v section="$section" -v today="$TODAY" '
        BEGIN { entry = ENVIRON["TODO_AWK_ENTRY"] }
        /^\*Last updated: / { print "*Last updated: " today "*"; next }
        $0 == section { print; print entry; inserted = 1; next }
        { print }
        END { if (!inserted) exit 42 }
    ' "$SOURCE_FILE" >"$output"; then
        die "TODO file is missing the expected priority section: $section"
    fi
    commit_file "$output"
    printf 'Added %s: %s\n' "$task_id" "$item"
}

mark_done() {
    local target="$1"
    local match
    local line_number
    local task_id
    local item
    local output

    validate_item_text "$target"
    [[ -f "$TODO_FILE" ]] || die "No TODO file found: $TODO_FILE"
    acquire_lock
    prepare_source
    match=$(resolve_target "$SOURCE_FILE" "$target" "open")
    IFS=$'\t' read -r line_number task_id item <<<"$match"

    make_temp
    output="$NEW_TEMP"
    if ! TODO_AWK_ITEM="$item" awk -v target_line="$line_number" -v task_id="$task_id" -v today="$TODAY" '
        BEGIN { item = ENVIRON["TODO_AWK_ITEM"] }
        NR == target_line { next }
        /^\*Last updated: / { print "*Last updated: " today "*"; next }
        $0 == "## ✅ Done" {
            print
            printf "- [x] [%s] %s (done: %s)\n", task_id, item, today
            inserted = 1
            next
        }
        { print }
        END { if (!inserted) exit 42 }
    ' "$SOURCE_FILE" >"$output"; then
        die "TODO file is missing the Done section"
    fi
    commit_file "$output"
    printf 'Completed %s: %s\n' "$task_id" "$item"
}

remove_item() {
    local target="$1"
    local confirm_flag="${2:-}"
    local confirmed_id="${3:-}"
    local match
    local line_number
    local task_id
    local item
    local output

    validate_item_text "$target"
    [[ -f "$TODO_FILE" ]] || die "No TODO file found: $TODO_FILE"
    acquire_lock
    prepare_source

    # A removal preview must return an ID that the confirmation command can
    # resolve later. Persist a first-time legacy ID migration under the same
    # lock before previewing; this changes task identity metadata only and does
    # not remove any task.
    if [[ "$SOURCE_FILE" != "$TODO_FILE" ]]; then
        commit_file "$SOURCE_FILE"
        SOURCE_FILE="$TODO_FILE"
    fi

    match=$(resolve_target "$SOURCE_FILE" "$target" "any")
    IFS=$'\t' read -r line_number task_id item <<<"$match"

    if [[ "$confirm_flag" != "--confirm" || "$confirmed_id" != "$task_id" ]]; then
        printf 'Removal preview: [%s] %s\n' "$task_id" "$item" >&2
        printf 'After explicit approval, run: remove %s --confirm %s\n' "$task_id" "$task_id" >&2
        exit 2
    fi

    [[ "$target" == "$task_id" ]] || die "Confirmed removal must target the exact stable ID: $task_id"
    make_temp
    output="$NEW_TEMP"
    awk -v target_line="$line_number" -v today="$TODAY" '
        NR == target_line { next }
        /^\*Last updated: / { print "*Last updated: " today "*"; next }
        { print }
    ' "$SOURCE_FILE" >"$output"
    commit_file "$output"
    printf 'Removed %s: %s\n' "$task_id" "$item"
}

list_items() {
    local priority="${1:-}"
    local section

    if [[ ! -f "$TODO_FILE" ]]; then
        printf 'No TODO file found: %s\n' "$TODO_FILE"
        return
    fi

    if [[ -z "$priority" ]]; then
        cat -- "$TODO_FILE"
        return
    fi

    case "$priority" in
        high) section='## 🔴 High Priority' ;;
        medium) section='## 🟡 Medium Priority' ;;
        low) section='## 🟢 Nice to Have' ;;
        done) section='## ✅ Done' ;;
        *) die "List filter must be high, medium, low, or done" ;;
    esac

    awk -v section="$section" '
        $0 == section { found = 1 }
        found && /^## / && $0 != section { exit }
        found { print }
    ' "$TODO_FILE"
}

week_ago() {
    date -v-7d +%Y-%m-%d 2>/dev/null || date -d '7 days ago' +%Y-%m-%d
}

summary() {
    local cutoff
    if [[ ! -f "$TODO_FILE" ]]; then
        printf 'TODO counts: total=0 high=0 medium=0 low=0 stale=0\n'
        return
    fi

    cutoff=$(week_ago)
    awk -v cutoff="$cutoff" '
        $0 == "## 🔴 High Priority" { priority = "high"; next }
        $0 == "## 🟡 Medium Priority" { priority = "medium"; next }
        $0 == "## 🟢 Nice to Have" { priority = "low"; next }
        /^## / { priority = "" }
        priority != "" && /^- \[ \] / {
            counts[priority]++
            total++
            if (match($0, /\(added: [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]\)$/)) {
                added = substr($0, RSTART + 8, 10)
                if (added < cutoff) stale++
            }
        }
        END {
            printf "TODO counts: total=%d high=%d medium=%d low=%d stale=%d\n", \
                total + 0, counts["high"] + 0, counts["medium"] + 0, \
                counts["low"] + 0, stale + 0
        }
    ' "$TODO_FILE"
}

heartbeat() {
    if [[ "${TODO_HEARTBEAT_ENABLED:-0}" != "1" ]]; then
        printf 'TODO heartbeat disabled\n'
        return
    fi
    summary
}

command="${1:-}"
case "$command" in
    add)
        [[ $# -eq 3 ]] || die "Usage: add <high|medium|low> <item>"
        add_item "$2" "$3"
        ;;
    done)
        [[ $# -eq 2 ]] || die "Usage: done <ID|exact-text>"
        mark_done "$2"
        ;;
    remove)
        [[ $# -eq 2 || $# -eq 4 ]] || die "Usage: remove <ID|exact-text> [--confirm <same-ID>]"
        remove_item "$2" "${3:-}" "${4:-}"
        ;;
    list)
        [[ $# -le 2 ]] || die "Usage: list [high|medium|low|done]"
        list_items "${2:-}"
        ;;
    summary)
        [[ $# -eq 1 ]] || die "Usage: summary"
        summary
        ;;
    heartbeat)
        [[ $# -eq 1 ]] || die "Usage: heartbeat"
        heartbeat
        ;;
    *)
        usage >&2
        exit 1
        ;;
esac
