---
name: self-improvement
description: "Captures learnings, errors, and corrections to enable continuous improvement. Use when: (1) A command or operation fails unexpectedly, (2) User corrects Claude ('No, that's wrong...', 'Actually...'), (3) User requests a capability that doesn't exist, (4) An external API or tool fails, (5) Claude realizes its knowledge is outdated or incorrect, (6) A better approach is discovered for a recurring task. Also review learnings before major tasks."
permissions:
  - file_write: "Appends learning, error, and feature-request notes inside the local .learnings directory."
---

# Self-Improvement Skill

Capture non-obvious lessons, failures, and feature requests in a small local knowledge base so the same mistakes are less likely to repeat.

## When to Use

- A command, tool, or integration fails in a way worth remembering
- The user corrects an assumption or teaches a project-specific convention
- You discover a better repeatable workflow
- The user asks for a missing capability that should be tracked
- You are starting work in an area with known prior learnings

## Storage

Keep entries in a local `.learnings/` directory:

- `.learnings/LEARNINGS.md`
- `.learnings/ERRORS.md`
- `.learnings/FEATURE_REQUESTS.md`

Create the directory on first use if it does not exist.

## Record Types

### Learning

Use for corrections, conventions, and better practices.

```markdown
## [LRN-YYYYMMDD-XXX] category

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Summary
One-line learning

### Details
What happened and what is now known to be correct

### Suggested Action
Specific follow-up or rule

### Metadata
- Source: conversation | error | user_feedback
- Related Files: path/to/file.ext
- Tags: tag1, tag2
- See Also: LRN-20250110-001
```

### Error

Use for reproducible failures or flaky workflows.

```markdown
## [ERR-YYYYMMDD-XXX] tool_or_workflow

**Logged**: ISO-8601 timestamp
**Priority**: high
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Summary
Short failure description

### Error
Exact error text or symptoms

### Context
- Operation attempted
- Inputs or environment details

### Suggested Fix
Likely next step
```

### Feature Request

Use for missing capabilities the user wants tracked.

```markdown
## [FEAT-YYYYMMDD-XXX] capability_name

**Logged**: ISO-8601 timestamp
**Priority**: medium
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Requested Capability
What the user wanted

### User Context
Why it matters

### Suggested Implementation
Likely extension point or implementation direction
```

## Workflow

1. Log the learning as soon as the context is clear.
2. Link related entries with `See Also` when patterns repeat.
3. Update status when the issue is resolved, rejected, or turned into a reusable rule.
4. Review `.learnings/` before major work in a familiar problem area.

## Promotion Rules

If a learning becomes broadly reusable:

- distill it into a concise rule
- move it into the repo's shared guidance only if the user explicitly wants that promotion
- update the learning entry to note where the rule now lives

Recurring patterns are good candidates for extraction into a dedicated skill when the solution is verified, portable, and no longer project-specific.

## Safety Boundaries

- Do not modify user-owned policy or guidance files unless the user explicitly asked for that promotion.
- Do not log secrets, access tokens, private keys, or sensitive personal data in `.learnings/`.
- Do not treat every failure as worth logging; prefer durable lessons over noise.
- Do not mark an entry resolved unless the fix was actually verified.
