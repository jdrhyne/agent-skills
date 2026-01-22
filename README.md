# jdrhyne-skills

A collection of AI agent skills for Clawdbot, Claude Code, Codex, and other LLM-based coding assistants.

## Available Skills

<!-- SKILLS_START -->
- `elegant-reports`: Generate beautifully designed PDF reports with Nordic/Scandinavian aesthetic. Uses Nutrient DWS API for HTML-to-PDF c...
- `humanizer`: Remove signs of AI-generated writing from text. Use when editing or reviewing text to make it sound more natural and ...
- `jira`: Manage Jira issues, boards, sprints, and projects via the jira-cli. Search, create, update, and transition issues dir...
- `munger-observer`: Daily wisdom review applying Charlie Munger's mental models to your work and thinking. Use when asked to review decis...
- `nudocs`: Upload, edit, and export documents via Nudocs.ai. Use when creating shareable document links for collaborative editin...
- `planner`: Create structured plans for multi-task projects that can be executed by the task-orchestrator skill. Use when breakin...
- `remotion-best-practices`: Best practices for Remotion - Video creation in React
- `senior-engineering`: Engineering principles for building software like a senior engineer. Load when tackling non-trivial development work,...
- `frontend-design`: Expert frontend design guidelines for creating beautiful, modern UIs. Use when building landing pages, dashboards, or...
- `sysadmin-toolbox`: Tool discovery and shell one-liner reference for sysadmin, DevOps, and security tasks. AUTO-CONSULT this skill when t...
- `task-orchestrator`: Autonomous multi-agent task orchestration with dependency analysis, parallel tmux/Codex execution, and self-healing h...
- `web-design-guidelines`: Review UI code for Web Interface Guidelines compliance. Use when asked to review my UI, check accessibility, audit de...
<!-- SKILLS_END -->

## Installation

### With Clawdbot

Add skills to your Clawdbot config:

```yaml
skills:
  paths:
    - /path/to/jdrhyne-skills/skills/skill-name
```

### With Claude Code / Codex

Copy the skill folder to your project or user instructions directory:

```bash
# Copy a specific skill
cp -r skills/elegant-reports ~/.codex/skills/

# Or symlink
ln -s /path/to/jdrhyne-skills/skills/elegant-reports ~/.codex/skills/
```

### Manual

Each skill is self-contained in its folder. Copy the SKILL.md (and any supporting files) to your agent's context.

## Skill Structure

Each skill follows this structure:

```
skills/
└── my-skill/
    ├── SKILL.md          # Main skill definition (required)
    ├── scripts/          # Helper scripts (optional)
    ├── templates/        # Templates/assets (optional)
    └── README.md         # Additional docs (optional)
```

### SKILL.md Format

```markdown
---
name: my-skill
description: Brief description of what the skill does
---

# Skill Name

Detailed instructions for the AI agent...
```

## Creating a New Skill

1. Create a folder in `/skills`:
   ```bash
   mkdir skills/my-new-skill
   ```

2. Create `SKILL.md` with frontmatter:
   ```markdown
   ---
   name: my-new-skill
   description: What this skill does
   ---
   
   # My New Skill
   
   Instructions...
   ```

3. Run the README updater:
   ```bash
   ./scripts/update-readme.sh
   ```

4. Commit and push:
   ```bash
   git add skills/my-new-skill
   git commit -m "Add my-new-skill"
   git push
   ```

## Scripts

- `scripts/update-readme.sh` — Scans `/skills` and updates this README
- `scripts/validate-skills.sh` — Validates all skills have proper SKILL.md

## License

MIT — Use these skills however you like.

## Author

Jonathan Rhyne ([@jdrhyne](https://github.com/jdrhyne))
