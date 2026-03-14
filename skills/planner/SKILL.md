---
name: planner
description: Create structured plans for multi-task projects that can be used by the task-orchestrator skill. Use when breaking down complex work into parallel and sequential tasks with dependencies.
metadata: {"clawdbot":{"emoji":"📋"}}
permissions:
  - file_write: "May save the completed plan to a file when the user asks for a persisted artifact."
---

# Planner

Create structured, orchestrator-ready plans for multi-task projects.

**Source**: Adapted from am-will's codex-skills workflow patterns
**Pairs with**: task-orchestrator skill for follow-on implementation

---

## Quick Start

Load the full planner prompt from `prompts/planner.md` and follow its process:

1. **Phase 0**: Clarify requirements (ask up to 5 targeted questions)
2. **Phase 1**: Research & understand the codebase
3. **Phase 2**: Create detailed plan with sprints, tasks, acceptance criteria
4. **Phase 3**: Subagent review of the plan
5. **Phase 4**: Return the plan in markdown and save a file only if the user asked for a persisted artifact

---

## Key Principles

### Task Atomicity
Each task must be:
- **Atomic and committable** — small, independent pieces of work
- **Specific and actionable** — not vague
- **Testable** — include tests or validation method
- **Located** — include file paths and code locations

### Bad vs Good Task Breakdown

❌ Bad: "Implement third-party sign-in"

✓ Good:
- "Add sign-in config to environment variables"
- "Install and configure the required authentication package"
- "Create sign-in callback route handler in src/routes/auth.ts"
- "Add the sign-in button to the login UI"

### Sprint Structure

Each sprint must:
- Result in a **demoable, runnable, testable** increment
- Build on prior sprint work
- Include clear demo/verification checklist

---

## Plan Template

```markdown
# Plan: [Task Name]

**Generated**: [Date]
**Estimated Complexity**: [Low/Medium/High]

## Overview
[Brief summary of what needs to be done and the general approach]

## Prerequisites
- [Dependencies or requirements that must be met first]
- [Tools, libraries, or access needed]
- [Tooling limitations, e.g., browser relay/CDP restrictions]

## Sprint 1: [Sprint Name]
**Goal**: [What this sprint accomplishes]
**Demo/Validation**:
- [How to run/demo this sprint's output]
- [What to verify]

### Task 1.1: [Task Name]
- **Location**: [File paths or components involved]
- **Description**: [What needs to be done]
- **Perceived Complexity**: [1-10]
- **Dependencies**: [Any previous tasks this depends on]
- **Acceptance Criteria**:
  - [Specific, testable criteria]
- **Validation**:
  - [Test(s) or alternate validation steps]

### Task 1.2: [Task Name]
[...]

## Sprint 2: [Sprint Name]
[...]

## Testing Strategy
- [How to test the implementation]
- [What to verify at each sprint]

## Potential Risks
- [Things that could go wrong]
- [Mitigation strategies]

## Rollback Plan
- [How to undo changes if needed]
```

---

## Hand-off

Once plan is ready, hand off to the **parallel-task worker**:

```
Please run parallel-task.md against my-plan.md
```

Or invoke directly:
> "Run all unblocked tasks in plan.md using parallel subagents. Keep looping until all tasks are complete."

## Safety Boundaries

- Do not save a plan file unless the user asked for one or the surrounding workflow explicitly needs a persisted artifact.
- Do not assign overlapping write scopes to parallel tasks without calling out the conflict.
- Do not invent dependencies, validation steps, or completion status that the repo context does not support.
- Do not turn a planning request into implementation work unless the user explicitly asks to move from planning to implementation.

---

## Files

- `prompts/planner.md` — Full planner agent prompt
- `prompts/parallel-task.md` — Parallel task worker prompt

Both are based on am-will's codex-skills prompts.
