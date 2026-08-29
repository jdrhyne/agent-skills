---
name: todo-tracker
description: Persistent TODO scratch pad for tracking tasks across sessions. Use when the user asks to add, list, complete, remove, or summarize tasks in a portable workspace Markdown file. Uses stable task IDs and exact matching; heartbeat reporting is opt-in and count-only.
---

# TODO Tracker

Maintain a portable Markdown task file without a service or database. Use the bundled script for every operation; do not edit task lines with ad hoc regex commands.

Runtime requirements: Bash and standard `awk`, `cp`, `chmod`, `mkdir`, `mktemp`, and `mv` utilities. Tasks are stored in a user-configurable local Markdown file.

## File and Script

- `TODO_FILE` selects the task file. Default: `TODO.md` in the current workspace.
- Always invoke the bundled script through `{baseDir}` so execution does not depend on the current directory.
- Read operations do not create a file.
- Writes use an adjacent lock, atomic same-directory renames, mode `600`, and a recoverable previous-state backup at `${TODO_FILE}.bak`.
- `${TODO_FILE}.next-id` is an adjacent mode-`600` monotonic ID counter. Keep it with the task file when moving or restoring the tracker; backup rotation must not replace or delete it.

```bash
TODO_FILE="$PWD/TODO.md" bash "{baseDir}/scripts/todo.sh" list
```

Do not use a machine-specific path. Quote `TODO_FILE`, IDs, and item text.

## Stable Identity

New tasks receive monotonic IDs such as `T000001`. Task text is matched literally and exactly, never as a regex or substring.

- Under the same writer lock, the script bootstraps the counter from the current task file, `${TODO_FILE}.bak`, and any valid existing counter. It reserves and atomically persists the next counter value before publishing a task-file mutation, so a crash may create an ID gap but cannot reuse an ID.
- Only the structured ID field immediately after a task checkbox participates in counter bootstrapping. ID-looking text inside a task title remains literal task content and never advances the counter.
- A missing counter is created safely on the next write. A corrupt, symbolic-link, non-regular, or non-`0600` counter fails closed; do not delete or reset it to bypass the check.
- Prefer an ID for `done` and always use an ID for approved removal.
- An exact-text target must match one task only.
- Duplicate open task text is rejected.
- An ambiguous exact-text target is rejected and the script reports the matching IDs.
- On the first operation that must resolve or mutate a legacy file, task lines without IDs are assigned deterministic IDs under the writer lock and the migration is persisted atomically; the original remains in the backup. A removal preview can trigger this recoverable metadata migration even though it removes no task.

## Commands

### Read

```bash
TODO_FILE="$PWD/TODO.md" bash "{baseDir}/scripts/todo.sh" list
TODO_FILE="$PWD/TODO.md" bash "{baseDir}/scripts/todo.sh" list high
TODO_FILE="$PWD/TODO.md" bash "{baseDir}/scripts/todo.sh" summary
```

If the file does not exist, `list` reports that fact and `summary` returns zero counts. Neither creates state.

### Add

```bash
TODO_FILE="$PWD/TODO.md" bash "{baseDir}/scripts/todo.sh" add high "Review launch checklist"
```

Priority must be `high`, `medium`, or `low`. Capture the returned stable ID.

### Complete

```bash
TODO_FILE="$PWD/TODO.md" bash "{baseDir}/scripts/todo.sh" done T000001
```

Exact text is accepted only when it identifies one open task. Completion preserves the stable ID and moves the task to Done.

### Remove

Removal is destructive and requires an exact preview plus action-time approval.

1. Resolve and preview without removing the task. For a legacy file, this first operation may atomically persist stable IDs and the adjacent monotonic counter before returning the preview. The pre-migration file remains in `${TODO_FILE}.bak`, and no task is removed:

   ```bash
   TODO_FILE="$PWD/TODO.md" bash "{baseDir}/scripts/todo.sh" remove "exact task text"
   ```

   The command exits without removal and prints the exact stable ID. Repeating the operation uses the persisted ID rather than migrating or advancing the counter again.

2. Show the user that ID and task text. Ask for approval to remove that exact task.
3. Only after approval, run the command contract naming and confirming the same ID:

   ```bash
   TODO_FILE="$PWD/TODO.md" bash "{baseDir}/scripts/todo.sh" remove T000001 --confirm T000001
   ```

Never infer approval from a partial name, prior unrelated removal, or a bulk request. Remove tasks one exact stable ID at a time.

## Heartbeat

Heartbeat access is off by default. Enable it only when the user explicitly opts in by configuring `TODO_HEARTBEAT_ENABLED=1` for that heartbeat workflow.

```bash
TODO_FILE="$PWD/TODO.md" TODO_HEARTBEAT_ENABLED=1 \
  bash "{baseDir}/scripts/todo.sh" heartbeat
```

Heartbeat output contains counts only: total, high, medium, low, and stale. It never prints task titles or notes. Do not create a schedule merely because this skill is installed.

## File Format

```markdown
# TODO Tracker

*Last updated: 2026-08-29*

## 🔴 High Priority
- [ ] [T000001] Review launch checklist (added: 2026-08-29)

## 🟡 Medium Priority

## 🟢 Nice to Have

## ✅ Done
- [x] [T000002] Verify release notes (done: 2026-08-29)
```

If a write fails because the lock exists, do not remove the lock while another process may be active. Investigate the writer and retry only after the lock is known to be stale.
