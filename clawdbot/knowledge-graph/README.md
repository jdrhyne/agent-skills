# 🧠 Knowledge Graph

**Three-Layer Memory System for AI Agents**

Give your agent a compounding memory that gets smarter with every conversation.

## What It Does

Most AI agents forget everything between sessions. This skill builds a structured knowledge graph that persists, compounds, and stays fresh — automatically.

### The Three Layers

| Layer | What | Where |
|-------|------|-------|
| **Entity Knowledge** | Structured facts about people, companies, projects | `life/areas/` |
| **Daily Notes** | Chronological session logs | `memory/YYYY-MM-DD.md` |
| **Persistent Memory** | High-level patterns and preferences | `MEMORY.md` |

### The Compounding Flywheel

```
Conversations → Daily Notes → Fact Extraction (every 4h) → Entity Facts
                                                                 ↓
                                Weekly Synthesis (Sundays) → Living Summaries
                                                                 ↓
                                             Richer Context → Better Conversations
```

Every conversation makes your agent smarter. Facts accumulate. Summaries stay current. Context improves over time. The longer you run it, the more valuable it becomes.

## How Facts Work

Facts are stored as **append-only JSONL** — one JSON object per line:

```json
{"id":"alice-001","fact":"Frontend engineer at Acme Corp","category":"context","ts":"2026-01-15","source":"conversation","status":"active"}
{"id":"alice-002","fact":"Promoted to senior engineer at Acme Corp","category":"milestone","ts":"2026-06-01","source":"conversation","status":"active","supersedes":"alice-001"}
```

### Key Principles

- **Append-only** — never edit or delete existing facts
- **Supersede, don't delete** — when facts change, add a new entry that supersedes the old one
- **Atomic** — one fact per entry, keep them small and specific
- **Categorized** — relationship, milestone, status, preference, context, or decision

### What Gets Extracted

✅ Job changes, life milestones, stated preferences, key decisions, important context

❌ Casual chat, temporary states, already-known facts, vague information

## How Crons Work

### Fact Extraction (Every 4 Hours)

A lightweight cron reads recent daily notes and conversations, extracts any durable facts, and appends them to the relevant entity's `facts.jsonl`. Uses the cheapest available model — typically costs less than $0.01/day.

### Weekly Synthesis (Sundays)

A weekly cron rewrites `summary.md` for any entity modified during the week. It:
- Reads all active facts
- Generates a 3-8 line summary
- Marks any contradicted facts as superseded
- Logs a synthesis report

Summaries are the "fast path" — agents read `summary.md` first and only dig into `facts.jsonl` when they need more detail.

## Setup

### 1. Create the directory structure

```bash
mkdir -p life/areas/{people,companies,projects}
```

### 2. Install the skill

Add `clawdbot/knowledge-graph` to your Clawdbot skills config.

### 3. Add the AGENTS.md block

Copy the Knowledge Graph section from `SKILL.md` into your workspace's `AGENTS.md` so all agents know how to use the graph.

### 4. Create the cron jobs

Add two crons to your Clawdbot config:
- **Fact extraction** — `0 */4 * * *` (every 4 hours)
- **Weekly synthesis** — `0 9 * * 0` (Sundays at 9am)

See `SKILL.md` for the full cron task descriptions.

### 5. Multi-agent setups (optional)

Symlink `life/` across agent workspaces so all agents share one knowledge graph:

```bash
ln -s /path/to/primary-workspace/life ./life
```

## Entity Structure

```
life/areas/
├── people/
│   └── alice/
│       ├── summary.md      # Quick context (3-8 lines)
│       └── facts.jsonl     # Atomic facts (append-only)
├── companies/
│   └── acme-corp/
│       ├── summary.md
│       └── facts.jsonl
└── projects/
    └── my-project/
        ├── summary.md
        └── facts.jsonl
```

## Low-token Recall Policy

To minimize context window usage, recall should be **triggered**, not automatic.

### Rules

| Rule | Behavior |
|------|----------|
| **Trigger-based** | Only recall on proper nouns, "remember/recall" phrases, or project keywords |
| **Summaries only** | Inject summary.md (max 5 lines), never facts.jsonl unless asked |
| **Single profile** | When topic is preferences/planning, use one profile summary |

### Why This Matters

- **No recall unless triggered** — most messages skip recall entirely, saving tokens
- **Summaries only** — 5 lines vs potentially hundreds of raw facts
- **Lean context** — keeps your agent fast and cost-effective

### Add to AGENTS.md

```markdown
### Low-token Recall Policy
- Only recall on triggers (proper nouns, "remember/recall", or project keywords).
- Inject summary.md only (max 5 lines); never inject facts.jsonl unless asked.
- Use a single profile summary when preferences/planning are the topic.
```

### Add to HEARTBEAT.md

```markdown
## Low-token Recall (Rule)
- [ ] Only recall on triggers (proper nouns, "remember/recall", project keywords)
- [ ] Inject summary.md only (max 5 lines) unless user explicitly asks for details
```

## Credits

Inspired by [@spacepixel's article on X](https://x.com/spacepixel) about building memory systems for AI agents.

## License

MIT
