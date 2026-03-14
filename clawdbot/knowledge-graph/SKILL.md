---
name: knowledge-graph
description: Three-Layer Memory System — automatic fact extraction, entity-based knowledge graph, and weekly synthesis. Manages life/areas/ entities with atomic facts and living summaries.
metadata: {"version":"1.1.0","openclaw":{"emoji":"🧠"}}
---

# Knowledge Graph Skill

Manages a Three-Layer Memory System for compounding knowledge across sessions.

## Architecture

### The Three Layers

1. **Entity Knowledge** (`life/areas/`) — Structured facts about people, companies, and projects stored as atomic JSONL entries with living summaries
2. **Daily Notes** (`memory/YYYY-MM-DD.md`) — Session logs, decisions, and events captured chronologically
3. **Persistent Memory** (`MEMORY.md` or equivalent) — High-level patterns, preferences, and agent-wide context

The knowledge graph (Layer 1) is the durable, structured layer. Daily notes feed it; synthesis distills it.

### The Compounding Flywheel

```
Conversations → Daily Notes → Fact Extraction (cron) → Entity Facts
                                                            ↓
                              Weekly Synthesis (cron) → Living Summaries
                                                            ↓
                                          Richer Context → Better Conversations
```

Every conversation makes your agent smarter. Facts compound. Summaries stay fresh. Context improves over time.

## When to Use

- **Fact Extraction** (cron): Extract durable facts from recent conversations
- **Weekly Synthesis** (cron): Rewrite summaries, prune stale facts
- **Entity Lookup**: When any agent needs context about a person, company, or project
- **Manual**: User says "remember that...", "update X's info", "what do we know about Y"

## Directory Structure

```
<workspace>/life/areas/
├── people/<slug>/       → summary.md + facts.jsonl
├── companies/<slug>/    → summary.md + facts.jsonl
└── projects/<slug>/     → summary.md + facts.jsonl
```

## Fact Schema (JSONL — one object per line)

```json
{
  "id": "<slug>-NNN",
  "fact": "The actual fact in plain English",
  "category": "relationship|milestone|status|preference|context|decision",
  "ts": "YYYY-MM-DD",
  "source": "conversation|manual|inference",
  "status": "active|superseded",
  "supersedes": "<id>"
}
```

### Rules

1. **Append-only** — never edit or delete lines in facts.jsonl
2. **Supersede, don't delete** — when a fact changes, add a new fact with `"supersedes": "<old-id>"` and mark the old fact's status as `"superseded"` (edit that one line)
3. **Auto-increment IDs** — `<slug>-001`, `<slug>-002`, etc.
4. **Be atomic** — one fact per entry, not paragraphs
5. **Skip ephemera** — no "user said hi", no transient chat

### What Qualifies as a Durable Fact

✅ Extract:
- Relationship changes (new job, new team, promotions)
- Life milestones (moved cities, had a baby, started a project)
- Status changes (left company, started freelancing)
- Stated preferences ("I prefer X over Y")
- Key decisions ("decided to use Rust for the backend")
- Important context ("allergic to shellfish", "works night shifts")

❌ Skip:
- Casual conversation, jokes, greetings
- Temporary states ("feeling tired today")
- Already-known facts (check existing facts first)
- Vague or uncertain information

## Task: Fact Extraction (Cron — Every 4 Hours)

```
1. Read today's daily note: memory/YYYY-MM-DD.md
2. Read recent conversation context (last few hours)
3. For each durable fact found:
   a. Determine entity type (person/company/project) and slug
   b. Create entity folder if new: mkdir -p life/areas/<type>/<slug>
   c. Check existing facts.jsonl — skip if already known
   d. If fact contradicts existing: supersede the old one
   e. Append new fact to facts.jsonl
4. Log extraction count to daily note
```

**Cost target**: Use the cheapest available model. Should cost < $0.01/day.

## Task: Weekly Synthesis (Sunday Cron)

```
1. List all entities in life/areas/
2. For each entity with facts modified this week:
   a. Load all facts from facts.jsonl
   b. Filter to status: "active" only
   c. Write a new summary.md (3-8 lines):
      - Who/what is this entity
      - Current relationship/status
      - Key active facts
      - Last updated date
   d. Mark any contradicted facts as superseded
3. Produce a brief synthesis report in daily note
```

## Task: Entity Lookup

When an agent needs context about an entity:

```
1. Check life/areas/<type>/<slug>/summary.md first (cheap)
2. Only load facts.jsonl if summary is stale or more detail needed
3. Use memory_search as fallback for entities not yet in the graph
```

## Low-token Recall Policy

To minimize token usage, recall should be **triggered**, not automatic.

### Rules

1. **Only recall on triggers:**
   - Proper nouns (names of people, companies, projects you track)
   - Explicit recall phrases: "remember", "recall", "what do we know about"
   - Project keywords that match entity slugs

2. **Inject summary.md only** (max 5 lines) — never inject facts.jsonl unless:
   - User explicitly asks for details/specifics
   - Summary is stale or missing
   - Contradictory information needs resolution

3. **Use a single profile summary** when the topic is preferences or planning

### Why This Matters

- **No recall unless triggered** — most messages skip recall entirely
- **Summaries only** — very short injections (5 lines vs potentially hundreds of facts)
- **No raw facts unless requested** — keeps context window lean

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

## Creating New Entities

When you encounter a new person/company/project worth tracking:

```bash
# Create structure
mkdir -p life/areas/people/alice

# Write initial fact
echo '{"id":"alice-001","fact":"Frontend engineer at Acme Corp, works on the design system","category":"context","ts":"2026-01-15","source":"conversation","status":"active"}' > life/areas/people/alice/facts.jsonl

# Write initial summary
cat > life/areas/people/alice/summary.md << 'EOF'
# Alice
Frontend engineer at Acme Corp.
Works on the design system team.
_Last updated: 2026-01-15_
EOF
```

## Integration with Other Layers

- **Layer 2 (Daily Notes)** → Source material for fact extraction
- **Layer 3 (MEMORY.md)** → Patterns/preferences stay there; entity facts come here
- **memory_search** → Indexes summaries for semantic lookup

---

## Setup

### 1. Create Directory Structure

```bash
mkdir -p life/areas/people
mkdir -p life/areas/companies
mkdir -p life/areas/projects
```

Optionally create a `life/README.md` explaining the structure for your own reference.

### 2. Add to AGENTS.md

Add this block to your workspace's `AGENTS.md`:

```markdown
## Knowledge Graph — Three-Layer Memory

### Layer 1: Entity Knowledge (`life/areas/`)
- `people/` — Person entities
- `companies/` — Company/org entities
- `projects/` — Project entities

Each entity has: `summary.md` (quick context) + `facts.jsonl` (atomic facts).

**Retrieval order:** summary.md first → facts.jsonl only if more detail needed.

**Rules:**
- Save durable facts to the relevant entity's `facts.jsonl` (append-only JSONL)
- Never delete facts — supersede instead (`"status":"superseded","supersedes":"old-id"`)
- When encountering a new notable entity, create its folder + initial fact + summary
- Cron handles periodic extraction and weekly synthesis — manual saves welcome too

See `skills/knowledge-graph/SKILL.md` and `life/README.md` for full conventions.
```

### 3. Create Cron Jobs

Set up two cron jobs in your OpenClaw config:

**Fact Extraction** — runs every 4 hours:
```yaml
crons:
  - name: fact-extraction
    schedule: "0 */4 * * *"
    task: >
      Run the fact extraction task from skills/knowledge-graph/SKILL.md.
      Read today's daily notes and recent conversations.
      Extract durable facts into life/areas/ entities.
      Use the cheapest available model.
```

**Weekly Synthesis** — runs every Sunday:
```yaml
  - name: weekly-synthesis
    schedule: "0 9 * * 0"
    task: >
      Run the weekly synthesis task from skills/knowledge-graph/SKILL.md.
      Rewrite summaries for all entities modified this week.
      Mark contradicted facts as superseded.
      Log a synthesis report to today's daily note.
```

### 4. Multi-Agent Setups (Optional)

If you run multiple agents that share a workspace, symlink `life/` so all agents read from the same knowledge graph:

```bash
# From each agent's workspace
ln -s /path/to/primary-workspace/life ./life
```

All agents will read/write to the same entity store. The cron jobs only need to run from one agent.

---

## Links

- [GitHub](https://github.com/jdrhyne/agent-skills/tree/main/clawdbot/knowledge-graph)
