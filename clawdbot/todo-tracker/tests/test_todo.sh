#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TODO_SCRIPT=$(cd "$SCRIPT_DIR/../scripts" && pwd)/todo.sh
TEST_ROOT=$(mktemp -d)

cleanup() {
    rm -rf -- "$TEST_ROOT"
}
trap cleanup EXIT

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 1
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    [[ "$haystack" == *"$needle"* ]] || fail "expected output to contain: $needle"
}

file_mode() {
    stat -f '%Lp' "$1" 2>/dev/null || stat -c '%a' "$1"
}

run_todo() {
    TODO_FILE="$1" TODO_DATE=2026-08-29 bash "$TODO_SCRIPT" "${@:2}"
}

test_no_file_reads() {
    local todo_file="$TEST_ROOT/no-file/TODO.md"
    local output
    mkdir "$TEST_ROOT/no-file"
    output=$(run_todo "$todo_file" list)
    assert_contains "$output" "No TODO file found"
    [[ ! -e "$todo_file" ]] || fail "list created a TODO file"
    output=$(run_todo "$todo_file" summary)
    [[ "$output" == "TODO counts: total=0 high=0 medium=0 low=0 stale=0" ]] || \
        fail "unexpected empty summary: $output"
    [[ ! -e "$todo_file" ]] || fail "summary created a TODO file"
}

test_special_characters_and_literal_matching() {
    local todo_file="$TEST_ROOT/special.md"
    local output
    local special="Fix [a/b] & regex .* \$(literal)? at C:\\tmp\\new\\tfile"
    run_todo "$todo_file" add high "$special" >/dev/null
    run_todo "$todo_file" add medium 'Fix aZZ and leave first literal' >/dev/null
    output=$(run_todo "$todo_file" "done" "$special")
    assert_contains "$output" "Completed T000001"
    grep -Fq -- "- [x] [T000001] $special" "$todo_file" || \
        fail "special-character task was not completed literally"
    grep -Fq -- '- [ ] [T000002] Fix aZZ and leave first literal' "$todo_file" || \
        fail "literal matching changed the wrong task"
}

test_removed_highest_id_is_not_reused() {
    local todo_file="$TEST_ROOT/monotonic.md"
    local output
    run_todo "$todo_file" add high "first task" >/dev/null
    run_todo "$todo_file" add high "removed highest task" >/dev/null
    run_todo "$todo_file" remove T000002 --confirm T000002 >/dev/null
    run_todo "$todo_file" "done" T000001 >/dev/null
    mv -- "$todo_file.bak" "$todo_file.rotated-backup"
    output=$(run_todo "$todo_file" add low "replacement task")
    assert_contains "$output" "Added T000003"
    grep -Fq -- '- [ ] [T000003] replacement task' "$todo_file" || \
        fail "removed highest stable ID was reused"
}

test_counter_mode_corruption_and_bootstrap() {
    local todo_file="$TEST_ROOT/counter.md"
    local counter_file="${todo_file}.next-id"
    local before
    local output

    run_todo "$todo_file" add high "first task" >/dev/null
    [[ -f "$counter_file" ]] || fail "monotonic counter was not created"
    [[ "$(file_mode "$counter_file")" == "600" ]] || fail "counter mode is not 600"
    [[ "$(<"$counter_file")" == "2" ]] || fail "counter did not reserve T000001"

    before=$(<"$todo_file")
    chmod 644 "$counter_file"
    if output=$(run_todo "$todo_file" add low "must fail permissions" 2>&1); then
        fail "broad counter permissions were accepted"
    fi
    assert_contains "$output" "counter must have mode 0600"
    [[ "$(<"$todo_file")" == "$before" ]] || fail "permission failure changed TODO file"

    printf '%s\n' 'not-a-number' >"$counter_file"
    chmod 600 "$counter_file"
    if output=$(run_todo "$todo_file" add low "must fail corruption" 2>&1); then
        fail "corrupt counter was accepted"
    fi
    assert_contains "$output" "counter is corrupt"
    [[ "$(<"$todo_file")" == "$before" ]] || fail "corrupt counter changed TODO file"

    printf '%s\n' '2' >"$counter_file"
    chmod 600 "$counter_file"
    awk '
        $0 == "## 🟡 Medium Priority" {
            print
            print "- [ ] [T000010] imported task (added: 2026-08-29)"
            next
        }
        { print }
    ' "$todo_file" >"$todo_file.seed"
    chmod 600 "$todo_file.seed"
    mv "$todo_file.seed" "$todo_file"
    output=$(run_todo "$todo_file" add medium "after imported ID")
    assert_contains "$output" "Added T000011"
    [[ "$(<"$counter_file")" == "12" ]] || fail "counter did not bootstrap past current file"
}

test_failed_publication_does_not_reuse_reserved_id() {
    local todo_file="$TEST_ROOT/reservation-gap.md"
    local saved_file="$TEST_ROOT/reservation-gap.saved"
    local output

    run_todo "$todo_file" add high "published first" >/dev/null
    cp "$todo_file" "$saved_file"
    awk '$0 != "## 🟡 Medium Priority" { print }' "$todo_file" >"$todo_file.malformed"
    chmod 600 "$todo_file.malformed"
    mv "$todo_file.malformed" "$todo_file"

    if run_todo "$todo_file" add medium "fails after reservation" >/dev/null 2>&1; then
        fail "add unexpectedly published without its target section"
    fi
    [[ "$(<"${todo_file}.next-id")" == "3" ]] || \
        fail "failed publication did not persist its ID reservation"

    cp "$saved_file" "$todo_file"
    chmod 600 "$todo_file"
    output=$(run_todo "$todo_file" add medium "published after failure")
    assert_contains "$output" "Added T000003"
    if grep -Fq -- '[T000002]' "$todo_file"; then
        fail "ID reserved by failed publication was reused"
    fi
}

test_counter_bootstraps_from_rotated_backup() {
    local todo_file="$TEST_ROOT/backup-bootstrap.md"
    local output

    printf '%s\n' \
        '# TODO Tracker' \
        '' \
        '*Last updated: 2026-08-29*' \
        '' \
        '## 🔴 High Priority' \
        '- [x] [T000009] task visible only in backup (done: 2026-08-29)' \
        '' \
        '## 🟡 Medium Priority' \
        '' \
        '## 🟢 Nice to Have' \
        '' \
        '## ✅ Done' >"${todo_file}.bak"
    chmod 600 "${todo_file}.bak"

    output=$(run_todo "$todo_file" add low "after backup-only ID")
    assert_contains "$output" "Added T000010"
    [[ "$(<"${todo_file}.next-id")" == "11" ]] || \
        fail "counter did not bootstrap past backup-only ID"
}

test_duplicate_and_ambiguity_refusal() {
    local todo_file="$TEST_ROOT/duplicates.md"
    local output
    run_todo "$todo_file" add medium "same task" >/dev/null
    if run_todo "$todo_file" add high "same task" >/dev/null 2>&1; then
        fail "duplicate open task was accepted"
    fi

    awk '
        $0 == "## 🟡 Medium Priority" {
            print
            print "- [ ] [T000002] ambiguous task (added: 2026-08-29)"
            print "- [ ] [T000003] ambiguous task (added: 2026-08-29)"
            next
        }
        { print }
    ' "$todo_file" >"$todo_file.seed"
    chmod 600 "$todo_file.seed"
    mv "$todo_file.seed" "$todo_file"

    if output=$(run_todo "$todo_file" "done" "ambiguous task" 2>&1); then
        fail "ambiguous exact text was accepted"
    fi
    assert_contains "$output" "Ambiguous exact text matched 2 tasks"
    run_todo "$todo_file" "done" T000002 >/dev/null
    grep -Fq -- '- [x] [T000002] ambiguous task' "$todo_file" || \
        fail "stable ID did not disambiguate task"
}

test_atomic_write_backup_and_mode() {
    local todo_file="$TEST_ROOT/atomic.md"
    local before
    run_todo "$todo_file" add low "first task" >/dev/null
    [[ "$(file_mode "$todo_file")" == "600" ]] || fail "TODO file mode is not 600"
    before=$(<"$todo_file")
    run_todo "$todo_file" add high "second task" >/dev/null
    [[ -f "$todo_file.bak" ]] || fail "backup was not created"
    [[ "$(<"$todo_file.bak")" == "$before" ]] || fail "backup is not the prior state"
    [[ "$(file_mode "$todo_file.bak")" == "600" ]] || fail "backup mode is not 600"
    if find "$TEST_ROOT" -maxdepth 1 -name '.atomic.md.tmp.*' -print -quit | grep -q .; then
        fail "atomic temporary file was left behind"
    fi
}

test_locking_and_remove_confirmation() {
    local todo_file="$TEST_ROOT/lock-remove.md"
    local before
    local output
    run_todo "$todo_file" add high "protected task" >/dev/null
    before=$(<"$todo_file")
    mkdir "$todo_file.lock"
    if run_todo "$todo_file" add low "must not write" >/dev/null 2>&1; then
        fail "write succeeded while lock was held"
    fi
    [[ "$(<"$todo_file")" == "$before" ]] || fail "locked write changed the file"
    rmdir "$todo_file.lock"

    if output=$(run_todo "$todo_file" remove "protected task" 2>&1); then
        fail "unconfirmed removal succeeded"
    fi
    assert_contains "$output" "Removal preview: [T000001] protected task"
    grep -Fq -- '[T000001] protected task' "$todo_file" || fail "preview removed the task"
    run_todo "$todo_file" remove T000001 --confirm T000001 >/dev/null
    if grep -Fq -- '[T000001] protected task' "$todo_file"; then
        fail "confirmed stable-ID removal did not remove the task"
    fi
}

test_legacy_remove_preview_persists_stable_id() {
    local todo_file="$TEST_ROOT/legacy-remove.md"
    local counter_file="${todo_file}.next-id"
    local output

    cat >"$todo_file" <<'EOF'
# TODO Tracker

*Last updated: 2026-08-28*

## 🔴 High Priority
- [ ] Discuss [T999999] migration (added: 2026-08-28)

## 🟡 Medium Priority

## 🟢 Nice to Have

## ✅ Done
EOF
    chmod 600 "$todo_file"

    if output=$(run_todo "$todo_file" remove "Discuss [T999999] migration" 2>&1); then
        fail "legacy removal preview unexpectedly removed the task"
    fi
    assert_contains "$output" "Removal preview: [T000001] Discuss [T999999] migration"
    grep -Fq -- '- [ ] [T000001] Discuss [T999999] migration' "$todo_file" || \
        fail "legacy removal preview did not persist its stable ID"
    grep -Fq -- '- [ ] Discuss [T999999] migration' "${todo_file}.bak" || \
        fail "legacy removal preview did not preserve the pre-migration backup"
    [[ "$(file_mode "$todo_file")" == "600" ]] || fail "migrated TODO file mode is not 600"
    [[ "$(file_mode "${todo_file}.bak")" == "600" ]] || fail "migration backup mode is not 600"
    [[ "$(file_mode "$counter_file")" == "600" ]] || fail "migration counter mode is not 600"
    [[ "$(<"$counter_file")" == "2" ]] || fail "legacy migration did not reserve exactly one ID"

    output=$(run_todo "$todo_file" remove T000001 --confirm T000001)
    assert_contains "$output" "Removed T000001: Discuss [T999999] migration"
    if grep -Fq -- '[T000001] Discuss [T999999] migration' "$todo_file"; then
        fail "confirmed legacy task removal did not remove the migrated task"
    fi
    grep -Fq -- '- [ ] [T000001] Discuss [T999999] migration' "${todo_file}.bak" || \
        fail "confirmed removal backup did not preserve the migrated task"
    [[ "$(<"$counter_file")" == "2" ]] || \
        fail "confirmed removal repeated the legacy migration or counter reservation"
}

test_heartbeat_opt_in_and_counts_only() {
    local todo_file="$TEST_ROOT/heartbeat.md"
    local output
    run_todo "$todo_file" add high "private title" >/dev/null
    output=$(TODO_FILE="$todo_file" TODO_DATE=2026-08-29 bash "$TODO_SCRIPT" heartbeat)
    [[ "$output" == "TODO heartbeat disabled" ]] || fail "heartbeat was not disabled by default"
    output=$(TODO_FILE="$todo_file" TODO_DATE=2026-08-29 TODO_HEARTBEAT_ENABLED=1 \
        bash "$TODO_SCRIPT" heartbeat)
    assert_contains "$output" "TODO counts: total=1 high=1 medium=0 low=0"
    [[ "$output" != *"private title"* ]] || fail "heartbeat leaked task title"
}

test_no_file_reads
test_special_characters_and_literal_matching
test_removed_highest_id_is_not_reused
test_counter_mode_corruption_and_bootstrap
test_failed_publication_does_not_reuse_reserved_id
test_counter_bootstraps_from_rotated_backup
test_duplicate_and_ambiguity_refusal
test_atomic_write_backup_and_mode
test_locking_and_remove_confirmation
test_legacy_remove_preview_persists_stable_id
test_heartbeat_opt_in_and_counts_only

printf 'PASS: todo-tracker regression suite\n'
