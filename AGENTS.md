# AGENTS.md

Instructions for AI agents working on this repository.

## Repository Structure

```
agent-skills/
├── skills/      # Skills with tooling, scripts, or workflows
├── prompts/     # Pure instruction prompts (text only)
├── clawdbot/    # Clawdbot-specific skills
├── scripts/     # Repo maintenance scripts
├── README.md    # Main documentation (auto-generated sections)
└── AGENTS.md    # This file
```

## Adding Content

### Adding a Skill (with tooling)

1. Create folder in `/skills`:
   ```bash
   mkdir -p skills/my-skill
   ```

2. Create `SKILL.md` with frontmatter:
   ```markdown
   ---
   name: my-skill
   description: What this skill does
   ---

   # My Skill

   Instructions, scripts, templates...
   ```

3. Add supporting files:
   - `scripts/` — Helper scripts
   - `templates/` — Template files
   - `examples/` — Example inputs/outputs

### Adding a Prompt (pure guidance)

1. Create folder in `/prompts`:
   ```bash
   mkdir -p prompts/my-prompt
   ```

2. Create `SKILL.md` with frontmatter:
   ```markdown
   ---
   name: my-prompt
   description: Guidance for X
   ---

   # My Prompt

   Instructions and guidelines...
   ```

Prompts should be self-contained — no external dependencies or scripts.

### Adding Clawdbot Skills

Same as skills, but in `/clawdbot`:
```bash
mkdir -p clawdbot/my-clawdbot-skill
```

## SKILL.md Requirements

**Required frontmatter:**
- `name`: Identifier (lowercase, hyphens)
- `description`: One-line description

**Good SKILL.md structure:**
1. Quick usage examples at the top
2. Detailed instructions
3. Edge cases / troubleshooting
4. References to supporting files

## Validation

Before committing:

```bash
./scripts/validate-skills.sh
```

## Sync Rule (Required)

If you add or update a skill **locally**, you must also:
1) Add/update the corresponding skill folder in this repo
2) Update the README skill list (Skills + Clawdbot-specific)
3) Run `./scripts/validate-skills.sh`
4) Open a **draft PR** with a clear What/Why/How/Testing description

Use `clawdbot/skill-sync` if you want a helper, but the steps above are still required.

## Conventions

- Skill names: lowercase with hyphens (`elegant-reports`)
- Scripts should be executable (`chmod +x`)
- No hardcoded machine-specific paths
- Don't commit credentials or API keys
