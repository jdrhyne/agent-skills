---
name: skill-sync
description: Sync skills between local installation and the GitHub source-of-truth repository. Use when asked to install, update, list, or push skills.
---

# Skill Sync

Manage skills from the shared GitHub repository with GitHub as canonical source of truth.

> Never commit secrets. Keep keys/tokens out of SKILL.md and scripts.

## Quick Reference

```bash
# List available skills in the repo
skill-sync list

# Install one skill
skill-sync install <skill-name>

# Install/update all skills from repo
skill-sync install --all

# Push a local skill update to repo via PR
skill-sync push <skill-name>

# Refresh local repo cache
skill-sync update
```

## Commands

### `skill-sync list`
Shows all skills available in the remote repository.

### `skill-sync install <name>`
Installs/updates a skill from repo into local skills directory.

### `skill-sync install --all`
Installs/updates all skills from repo.

### `skill-sync push <name>`
Pushes local skill changes via branch + PR (`gh` CLI).

### `skill-sync update`
Pulls latest repo changes without installing.

## Configuration

Default paths:
- Repo clone: `~/.agent-skills-repo`
- Local skills: `~/clawd/skills` (or `$CLAWD_SKILLS_DIR`)
- Remote: `https://github.com/jdrhyne/agent-skills.git`
