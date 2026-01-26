---
name: task-orchestrator
description: Autonomous multi-agent task orchestration with dependency analysis, parallel tmux/Codex execution, and self-healing heartbeat monitoring. Use for large projects with multiple issues/tasks that need coordinated parallel execution.
metadata: {"clawdbot":{"emoji":"🎭","requires":{"anyBins":["tmux","codex","gh"]}}}
---

# Task Orchestrator

Autonomous orchestration of multi-agent builds using tmux + Codex with self-healing monitoring.

**Load the senior-engineering skill alongside this one for engineering principles.**

## Core Concepts

### 1. Task Manifest
A JSON file defining all tasks, their dependencies, files touched, and status.

```json
{
  "project": "project-name",
  "repo": "owner/repo",
  "workdir": "/path/to/worktrees",
  "created": "2026-01-17T00:00:00Z",
  "model": "gpt-5.2-codex",
  "modelTier": "high",
  "phases": [
    {
      "name": "Phase 1: Critical",
      "tasks": [
        {
          "id": "t1",
          "issue": 1,
          "title": "Fix X",
          "files": ["src/foo.js"],
          "dependsOn": [],
          "status": "pending",
          "worktree": null,
          "tmuxSession": null,
          "startedAt": null,
          "lastProgress": null,
          "completedAt": null,
          "prNumber": null
        }
      ]
    }
  ]
}
```

### 2. Dependency Rules
- **Same file = sequential** — Tasks touching the same file must run in order or merge
- **Different files = parallel** — Independent tasks can run simultaneously
- **Explicit depends = wait** — `dependsOn` array enforces ordering
- **Phase gates** — Next phase waits for current phase completion

### 3. Execution Model
- Each task gets its own **git worktree** (isolated branch)
- Each task runs in its own **tmux session**
- Use **Codex with --yolo** for autonomous execution
- Model: **GPT-5.2-codex high** (configurable)

---

## Setup Commands

### Initialize Orchestration

```bash
# 1. Create working directory
WORKDIR="${TMPDIR:-/tmp}/orchestrator-$(date +%s)"
mkdir -p "$WORKDIR"

# 2. Clone repo for worktrees
git clone https://github.com/OWNER/REPO.git "$WORKDIR/repo"
cd "$WORKDIR/repo"

# 3. Create tmux socket
SOCKET="$WORKDIR/orchestrator.sock"

# 4. Initialize manifest
cat > "$WORKDIR/manifest.json" << 'EOF'
{
  "project": "PROJECT_NAME",
  "repo": "OWNER/REPO",
  "workdir": "WORKDIR_PATH",
  "socket": "SOCKET_PATH",
  "created": "TIMESTAMP",
  "model": "gpt-5.2-codex",
  "modelTier": "high",
  "phases": []
}
EOF
```

### Analyze GitHub Issues for Dependencies

```bash
# Fetch all open issues
gh issue list --repo OWNER/REPO --state open --json number,title,body,labels > issues.json

# Group by files mentioned in issue body
# Tasks touching same files should serialize
```

### Create Worktrees

```bash
# For each task, create isolated worktree
cd "$WORKDIR/repo"
git worktree add -b fix/issue-N "$WORKDIR/task-tN" main
```

### Launch Tmux Sessions

```bash
SOCKET="$WORKDIR/orchestrator.sock"

# Create session for task
tmux -S "$SOCKET" new-session -d -s "task-tN"

# Launch Codex (uses gpt-5.2-codex with reasoning_effort=high from ~/.codex/config.toml)
# Note: Model config is in ~/.codex/config.toml, not CLI flag
tmux -S "$SOCKET" send-keys -t "task-tN" \
  "cd $WORKDIR/task-tN && codex --yolo 'Fix issue #N: DESCRIPTION. Run tests, commit with good message, push to origin.'" Enter
```

---

## Monitoring & Self-Healing

### Progress Check Script

```bash
#!/bin/bash
# check_progress.sh - Run via heartbeat

WORKDIR="$1"
SOCKET="$WORKDIR/orchestrator.sock"
MANIFEST="$WORKDIR/manifest.json"
STALL_THRESHOLD_MINS=20

check_session() {
  local session="$1"
  local task_id="$2"
  
  # Capture recent output
  local output=$(tmux -S "$SOCKET" capture-pane -p -t "$session" -S -50 2>/dev/null)
  
  # Check for completion indicators
  if echo "$output" | grep -qE "(All tests passed|Successfully pushed|❯ $)"; then
    echo "DONE:$task_id"
    return 0
  fi
  
  # Check for errors
  if echo "$output" | grep -qiE "(error:|failed:|FATAL|panic)"; then
    echo "ERROR:$task_id"
    return 1
  fi
  
  # Check for stall (prompt waiting for input)
  if echo "$output" | grep -qE "(\? |Continue\?|y/n|Press any key)"; then
    echo "STUCK:$task_id:waiting_for_input"
    return 2
  fi
  
  echo "RUNNING:$task_id"
  return 0
}

# Check all active sessions
for session in $(tmux -S "$SOCKET" list-sessions -F "#{session_name}" 2>/dev/null); do
  check_session "$session" "$session"
done
```

### Self-Healing Actions

When a task is stuck, the orchestrator should:

1. **Waiting for input** → Send appropriate response
   ```bash
   tmux -S "$SOCKET" send-keys -t "$session" "y" Enter
   ```

2. **Error/failure** → Capture logs, analyze, retry with fixes
   ```bash
   # Capture error context
   tmux -S "$SOCKET" capture-pane -p -t "$session" -S -100 > "$WORKDIR/logs/$task_id-error.log"
   
   # Kill and restart with error context
   tmux -S "$SOCKET" kill-session -t "$session"
   tmux -S "$SOCKET" new-session -d -s "$session"
   tmux -S "$SOCKET" send-keys -t "$session" \
     "cd $WORKDIR/$task_id && codex --model gpt-5.2-codex-high --yolo 'Previous attempt failed with: $(cat error.log | tail -20). Fix the issue and retry.'" Enter
   ```

3. **No progress for 20+ mins** → Nudge or restart
   ```bash
   # Check git log for recent commits
   cd "$WORKDIR/$task_id"
   LAST_COMMIT=$(git log -1 --format="%ar" 2>/dev/null)
   
   # If no commits in threshold, restart
   ```

### Heartbeat Cron Setup

```bash
# Add to cron (every 15 minutes)
cron action:add job:{
  "label": "orchestrator-heartbeat",
  "schedule": "*/15 * * * *",
  "prompt": "Check orchestration progress at WORKDIR. Read manifest, check all tmux sessions, self-heal any stuck tasks, advance to next phase if current is complete. Do NOT ping human - fix issues yourself."
}
```

---

## Workflow: Full Orchestration Run

### Step 1: Analyze & Plan

```bash
# 1. Fetch issues
gh issue list --repo OWNER/REPO --state open --json number,title,body > /tmp/issues.json

# 2. Analyze for dependencies (files mentioned, explicit deps)
# Group into phases:
# - Phase 1: Critical/blocking issues (no deps)
# - Phase 2: High priority (may depend on Phase 1)
# - Phase 3: Medium/low (depends on earlier phases)

# 3. Within each phase, identify:
# - Parallel batch: Different files, no deps → run simultaneously
# - Serial batch: Same files or explicit deps → run in order
```

### Step 2: Create Manifest

Write manifest.json with all tasks, dependencies, file mappings.

### Step 3: Launch Phase 1

```bash
# Create worktrees for Phase 1 tasks
for task in phase1_tasks; do
  git worktree add -b "fix/issue-$issue" "$WORKDIR/task-$id" main
done

# Launch tmux sessions
for task in phase1_parallel_batch; do
  tmux -S "$SOCKET" new-session -d -s "task-$id"
  tmux -S "$SOCKET" send-keys -t "task-$id" \
    "cd $WORKDIR/task-$id && codex --model gpt-5.2-codex-high --yolo '$PROMPT'" Enter
done
```

### Step 4: Monitor & Self-Heal

Heartbeat checks every 15 mins:
1. Poll all sessions
2. Update manifest with progress
3. Self-heal stuck tasks
4. When all Phase N tasks complete → launch Phase N+1

### Step 5: Create PRs

```bash
# When task completes successfully
cd "$WORKDIR/task-$id"
git push -u origin "fix/issue-$issue"
gh pr create --repo OWNER/REPO \
  --head "fix/issue-$issue" \
  --title "fix: Issue #$issue - $TITLE" \
  --body "Closes #$issue

## Changes
[Auto-generated by Codex orchestrator]

## Testing
- [ ] Unit tests pass
- [ ] Manual verification"
```

### Step 6: Cleanup

```bash
# After all PRs merged or work complete
tmux -S "$SOCKET" kill-server
cd "$WORKDIR/repo"
for task in all_tasks; do
  git worktree remove "$WORKDIR/task-$id" --force
done
rm -rf "$WORKDIR"
```

---

## Manifest Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Not started yet |
| `blocked` | Waiting on dependency |
| `running` | Codex session active |
| `stuck` | Needs intervention (auto-heal) |
| `error` | Failed, needs retry |
| `complete` | Done, ready for PR |
| `pr_open` | PR created |
| `merged` | PR merged |

---

## Example: Security Framework Orchestration

```json
{
  "project": "nuri-security-framework",
  "repo": "jdrhyne/nuri-security-framework",
  "phases": [
    {
      "name": "Phase 1: Critical",
      "tasks": [
        {"id": "t1", "issue": 1, "files": ["ceo_root_manager.js"], "dependsOn": []},
        {"id": "t2", "issue": 2, "files": ["ceo_root_manager.js"], "dependsOn": ["t1"]},
        {"id": "t3", "issue": 3, "files": ["workspace_validator.js"], "dependsOn": []}
      ]
    },
    {
      "name": "Phase 2: High",
      "tasks": [
        {"id": "t4", "issue": 4, "files": ["kill_switch.js", "container_executor.js"], "dependsOn": []},
        {"id": "t5", "issue": 5, "files": ["kill_switch.js"], "dependsOn": ["t4"]},
        {"id": "t6", "issue": 6, "files": ["ceo_root_manager.js"], "dependsOn": ["t2"]},
        {"id": "t7", "issue": 7, "files": ["container_executor.js"], "dependsOn": []},
        {"id": "t8", "issue": 8, "files": ["container_executor.js", "egress_proxy.js"], "dependsOn": ["t7"]}
      ]
    }
  ]
}
```

**Parallel execution in Phase 1:**
- t1 and t3 run in parallel (different files)
- t2 waits for t1 (same file)

**Parallel execution in Phase 2:**
- t4, t6, t7 can start together
- t5 waits for t4, t8 waits for t7

---

## Tips

1. **Always use GPT-5.2-codex high** for complex work: `--model gpt-5.2-codex-high`
2. **Clear prompts** — Include issue number, description, expected outcome, test instructions
3. **Atomic commits** — Tell Codex to commit after each logical change
4. **Push early** — Push to remote branch so progress isn't lost if session dies
5. **Checkpoint logs** — Capture tmux output periodically to files
6. **Phase gates** — Don't start Phase N+1 until Phase N is 100% complete
7. **Self-heal aggressively** — If stuck >10 mins, intervene automatically
8. **Browser relay limits** — If CDP automation is blocked, use iframe batch scraping or manual browser steps

---

## Integration with Other Skills

- **senior-engineering**: Load for build principles and quality gates
- **coding-agent**: Reference for Codex CLI patterns
- **github**: Use for PR creation, issue management

---

## Lessons Learned (2026-01-17)

### Codex Sandbox Limitations
When using `codex exec --full-auto`, the sandbox:
- **No network access** — `git push` fails with "Could not resolve host"
- **Limited filesystem** — Can't write to paths like `~/nuri_workspace`

### Heartbeat Detection Improvements
The heartbeat should check for:
1. **Shell prompt idle** — If tmux pane shows `username@hostname path %`, worker is done
2. **Unpushed commits** — `git log @{u}.. --oneline` shows commits not on remote
3. **Push failures** — Look for "Could not resolve host" in output

When detected, the orchestrator (not the worker) should:
1. Push the commit from outside the sandbox
2. Create the PR via `gh pr create`
3. Update manifest and notify

### Recommended Pattern
```bash
# In heartbeat, for each task:
cd /tmp/orchestrator-*/task-tN
if tmux capture-pane shows shell prompt; then
  # Worker finished, check for unpushed work
  if git log @{u}.. --oneline | grep -q .; then
    git push -u origin HEAD
    gh pr create --title "$(git log --format=%s -1)" --body "Closes #N" --base main
  fi
fi
```
