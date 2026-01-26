---
name: planner
description: Create structured plans for multi-task projects that can be executed by the task-orchestrator skill. Use when breaking down complex work into parallel/sequential tasks with dependencies.
metadata: {"clawdbot":{"emoji":"📋"}}
---

# Planner

Create structured, orchestrator-ready plans for multi-task projects.

**Source**: Based on [am-will/codex-skills](https://github.com/am-will/codex-skills)  
**Pairs with**: task-orchestrator skill for execution

---

## Quick Start

Load the full planner prompt from `prompts/planner.md` and follow its process:

1. **Phase 0**: Clarify requirements (ask up to 5 targeted questions)
2. **Phase 1**: Research & understand the codebase
3. **Phase 2**: Create detailed plan with sprints, tasks, acceptance criteria
4. **Phase 3**: Subagent review of the plan
5. **Phase 4**: Save the plan file

---

## Key Principles

### Task Atomicity
Each task must be:
- **Atomic and committable** — small, independent pieces of work
- **Specific and actionable** — not vague
- **Testable** — include tests or validation method
- **Located** — include file paths and code locations

### Bad vs Good Task Breakdown

❌ Bad: "Implement Google OAuth"

✓ Good:
- "Add Google OAuth config to environment variables"
- "Install and configure passport-google-oauth20 package"  
- "Create OAuth callback route handler in src/routes/auth.ts"
- "Add Google sign-in button to login UI"

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

## Execution

Once plan is ready, hand off to the **parallel-task executor**:

```
Please execute parallel-task.md against my-plan.md
```

Or invoke directly:
> "Run all unblocked tasks in plan.md using parallel subagents. Keep looping until all tasks are complete."

---

## Files

- `prompts/planner.md` — Full planner agent prompt
- `prompts/parallel-task.md` — Parallel task executor prompt

Both are based on am-will's codex-skills prompts.
