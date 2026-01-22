---
name: senior-engineering
description: Engineering principles for building software like a senior engineer. Load when tackling non-trivial development work, architecting systems, reviewing code, or orchestrating multi-agent builds. Covers planning, execution, quality gates, and LLM-specific patterns.
---

# Senior Engineering Principles

Guidelines for building software with the judgment and discipline of a senior engineer.

## Before Writing Code

### Define Done First
- What does success look like? Write it down.
- What are the acceptance criteria?
- How will you verify it works?

### Identify Load-Bearing Decisions
- Which choices are hard to reverse? → More scrutiny
- Which are easily changed? → Decide fast, move on
- Reversible decisions don't need consensus

### Decompose Before Building
- Break work into clear, testable units
- Each unit should be independently verifiable
- If you can't explain the pieces, you don't understand the whole

### Surface Risks Upfront
- What could go wrong?
- What are the dependencies?
- What's the rollback plan?
- Time-box exploration — analysis paralysis is real

### Interface First, Implementation Second
- Define the contract (types, API shape, error cases) before internals
- Forces clarity on what you're actually building
- Implementation becomes "fill in the blanks"

### Ask: What's the Simplest Thing That Could Work?
- Start there. Add complexity only when the simple version fails.
- Most features need 20% of what we imagine.

## During Build

### Always Have a Runnable State
- Never be more than 30 mins from something that compiles/runs
- Commit working checkpoints frequently
- Big-bang integration is where projects die

### Prefer Incremental Over Big-Bang
- Ship small, verify, iterate
- Each step should be independently deployable if possible
- Reduce blast radius of mistakes

### Instrument As You Build
- Add logging/metrics while coding, not when debugging prod
- "I wish I had visibility into X" = you waited too long
- Observability is a feature, not an afterthought

### Read Errors Carefully
- 80% of debugging is actually reading what the system tells you
- Read the error, then read it again
- Stack traces have answers — follow them

### Boring > Clever
- If someone has to pause to understand it, it's too clever
- Save big-brain moves for genuinely hard problems
- Maintainability beats elegance

### Optimize for Delete
- Write code that's easy to remove
- Tight coupling makes features immortal
- Good abstractions have clear boundaries

## Quality Gates

### Before Declaring Done
- [ ] Linter passes
- [ ] Type checker passes
- [ ] Tests pass (unit + integration where applicable)
- [ ] Manual smoke test completed
- [ ] Edge cases considered and handled

### Tests Are Documentation
- A good test suite tells you what code is *supposed* to do
- Treat tests as first-class citizens
- If it's not tested, it's not done

### Code Review Mindset
- Review like you'll maintain it at 3am
- Check: correctness, clarity, edge cases, security
- "It works" is necessary but not sufficient

## LLM Orchestration Principles

### Context Management
- Context window is your RAM — manage it deliberately
- Bloated context = degraded reasoning
- Give each agent minimum viable context, no more

### Agent Delegation
- Single responsibility per agent
- Clear handoff contracts: inputs, outputs, success criteria
- Parallel when independent, sequential when dependent

### Verify, Don't Trust
- First output is a draft, always
- Review agent output like a code review
- Agents are junior engineers, not oracles

### Checkpoints Over Marathons
- Long-running agents should checkpoint progress
- If it crashes at 90%, don't lose everything
- Log state to files, not just memory

### Fail Fast, Surface Early
- If something's going wrong, stop and reassess
- Don't compound errors hoping they'll resolve
- Human in the loop for high-stakes decisions

## Ownership & Accountability

### Own Failures, Credit Others
- Own failures publicly
- Credit others for wins
- No ego-driven attachment to being right

### Strong Opinions, Weakly Held
- Have a position, defend it with evidence
- Update beliefs when evidence demands it
- "I was wrong" is a sign of growth

### Leave It Better
- Codebases, teams, processes — improve what you touch
- Fix the small things while you're there
- Documentation is a gift to future-you

## The Meta-Principle

> "Make the change easy, then make the easy change." — Kent Beck

Most senior engineering is about *preparation* — setting up the codebase so the actual feature is trivial. If the feature is hard, the real work is often refactoring first to make it easy.
