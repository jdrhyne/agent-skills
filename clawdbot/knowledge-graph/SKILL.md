---
name: knowledge-graph
description: Three-Layer Memory System — automatic fact extraction, entity-based knowledge graph, and weekly synthesis. Manages life/areas/ entities with atomic facts and living summaries.
metadata: {"version":"1.1.0","openclaw":{"emoji":"🧠"}}
permissions:
  - exec: "Uses local filesystem commands when creating entity folders or scheduled knowledge-graph jobs."
  - file_write: "Appends facts, summaries, and daily-note synthesis inside the workspace knowledge graph."
---

# Knowledge Graph Skill

Maintain a lightweight, append-only entity graph that compounds durable facts across sessions.

## When to Use

- Extract durable facts from recent work or conversation history
- Rewrite entity summaries from active facts
- Answer "what do we know about X?" without reopening large transcripts
- Keep shared context for people, companies, and projects inside the workspace

## Data Model

Store the graph under:

```text
<workspace>/life/areas/
  people/<slug>/
  companies/<slug>/
  projects/<slug>/
```

Each entity folder should contain:

- `summary.md` for the short, current snapshot
- `facts.jsonl` for atomic, append-only facts

Use one JSON object per line:

```json
{
  "id": "<slug>-NNN",
  "fact": "Plain-English fact",
  "category": "relationship|milestone|status|preference|context|decision",
  "ts": "YYYY-MM-DD",
  "source": "conversation|manual|inference",
  "status": "active|superseded",
  "supersedes": "<older-id>"
}
```

## Fact Rules

- Keep facts atomic. One durable fact per entry.
- Append new facts instead of rewriting history.
- When something changes, add a new fact and mark the old one as superseded.
- Skip ephemera, greetings, speculation, and low-value chatter.
- Check existing facts before adding duplicates.

Durable facts usually include:

- role or relationship changes
- key decisions
- long-lived preferences
- major project milestones
- stable operating context

## Workflows

### Fact Extraction

1. Read the recent daily note and the recent conversation window.
2. Identify durable facts worth preserving.
3. Resolve entity type and slug.
4. Create the entity folder if it does not exist.
5. Append new facts to `facts.jsonl`.
6. Note extraction activity in the daily note if the workspace uses one.

### Weekly Synthesis

1. List entities changed during the week.
2. Load active facts only.
3. Rewrite `summary.md` in 3 to 8 concise lines.
4. Ensure contradicted facts are marked superseded.
5. Record a short synthesis note in the daily log if applicable.

### Entity Lookup

1. Read `summary.md` first.
2. Open `facts.jsonl` only if the summary is stale or the user asked for detail.
3. Fall back to broader memory search only when the entity is missing from the graph.

## Low-Token Recall

Recall should be triggered, not automatic.

- Recall when the user names a tracked person, company, or project.
- Recall when the user explicitly asks to remember, recall, or summarize prior context.
- Inject only the short summary by default.
- Avoid loading raw facts unless the user asked for specifics or contradictions need resolution.

## Setup

Create the core directories once:

```bash
mkdir -p life/areas/people life/areas/companies life/areas/projects
```

If multiple agents share one workspace, point them at the same `life/` directory so they operate on the same entity store.

## Safety Boundaries

- Do not store sensitive secrets, credentials, or highly personal data unless the user explicitly asked for it.
- Do not create entities or facts for casual chat that has no durable value.
- Do not inject the graph into every conversation by default.
- Do not delete historical facts; supersede them with a newer fact instead.
