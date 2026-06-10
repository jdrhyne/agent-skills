# Contributing to Agent Skills

Thanks for considering a contribution! This collection grows through community sharing.

## The Philosophy

A skill is **compressed expert knowledge** — things that take years of experience to learn, distilled into a format AI agents can use immediately.

> **Good Skill = Expert-only Knowledge − What the Model Already Knows**

Don't explain what a PDF is. Don't write tutorials for standard library usage. Focus on:
- Decision trees for non-obvious choices
- Trade-offs only an expert would know
- Edge cases from real-world experience
- "NEVER do X because [non-obvious reason]"

---

## Skill Structure

```
skills/my-skill/
├── SKILL.md          # Required — main instructions for the agent
├── scripts/          # Optional — helper scripts
├── templates/        # Optional — templates/assets
└── README.md         # Optional — human documentation
```

For pure instruction prompts (no tooling):

```
prompts/my-prompt/
└── SKILL.md
```

---

## The SKILL.md Format

### Frontmatter (Required)

```yaml
---
name: my-skill-name
description: What it does. When to use it. Keywords for discovery.
---
```

**The description is critical.** Agents only see the description before deciding to load your skill. A great skill with a vague description will never be used.

Your description must answer:

| Question | Example |
|----------|---------|
| **WHAT** does it do? | "Query Google Analytics 4 data via the Analytics Data API" |
| **WHEN** should it be used? | "Use when pulling website analytics, traffic sources, or conversion data" |
| **KEYWORDS** for discovery | "GA4, analytics, traffic, sessions, page views" |

**Good description:**
```yaml
description: Query Google Analytics 4 (GA4) data via the Analytics Data API. 
  Use when pulling website analytics like top pages, traffic sources, user counts, 
  sessions, conversions, and custom metrics. Supports property comparison and 
  date range analysis.
```

**Bad description:**
```yaml
description: Helps with analytics stuff.
```

### Body Content

After the frontmatter, write instructions that help the agent do the task well. Focus on:

1. **Thinking frameworks** — "Before doing X, ask yourself..."
2. **Decision trees** — "If A, do B. If C, do D."
3. **Anti-patterns** — "NEVER do X because..."
4. **Expert shortcuts** — Things that save time once you know them

---

## Quality Guidelines

### DO ✓

- **Add expert knowledge** — Decision trees, trade-offs, edge cases
- **Include NEVER lists** — Half of expertise is knowing what not to do
- **Be specific** — "Use `camelot-py` for tables, fall back to `tabula-py` if it fails"
- **Provide working examples** — Code that actually runs
- **Keep SKILL.md focused** — Aim for <300 lines; put heavy reference content in separate files

### DON'T ✗

- **Don't explain basics** — No "What is X" for standard concepts
- **Don't write tutorials** — The model knows how to use common libraries
- **Don't be vague** — "Handle errors properly" teaches nothing
- **Don't dump everything in SKILL.md** — Use `references/` for detailed docs
- **Don't forget the description** — This is how your skill gets discovered

---

## Skill Patterns

Choose the pattern that fits your task:

| Pattern | Lines | Best For | Example |
|---------|-------|----------|---------|
| **Mindset** | ~50 | Creative tasks requiring taste | frontend-design |
| **Process** | ~200 | Complex multi-step workflows | task-orchestrator |
| **Tool** | ~300 | Precise operations on specific formats | ga4, jira |

**Mindset skills** focus on principles and thinking frameworks.
**Process skills** walk through phased workflows with checkpoints.
**Tool skills** provide decision trees and specific procedures.

---

## Submitting Your Skill

### 1. Fork & Create

```bash
# Fork the repo on GitHub, then clone your fork:
git clone https://github.com/<your-username>/agent-skills.git
cd agent-skills
mkdir -p skills/my-new-skill  # or prompts/ or clawdbot/
```

### 2. Write Your Skill

Create `SKILL.md` with proper frontmatter. Add supporting files if needed.

### 3. Test It

Load the skill in your agent (Clawdbot, Claude Code, etc.) and verify it works as expected.

### 4. Update the README

Add your skill to the appropriate table in `README.md`.

### 5. Submit a PR

Open a pull request with:
- Clear title: "Add [skill-name]: [brief description]"
- Description of what the skill does and why it's useful
- Confirmation that you've tested it

---

## Contribution Ideas

Not sure what to build? Here are some gaps:

- **Integrations** — Slack, Linear, Notion API, etc.
- **Frameworks** — Next.js, Remix, SvelteKit patterns
- **DevOps** — Terraform, Kubernetes, CI/CD workflows
- **Data** — SQL optimization, dbt, data pipeline patterns
- **Domain expertise** — Legal docs, medical terminology, finance calculations

---

## Code of Conduct

Be kind. Be helpful. Share what you know.

---

## Questions?

Open an issue or reach out to [@jdrhyne](https://github.com/jdrhyne).
