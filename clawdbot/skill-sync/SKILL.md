---
name: skill-sync
description: Sync Clawdbot skills between local installation and the shared skill repository. Use when asked to install, update, list, or push skills.
permissions:
  - file_write: "Copies skill files between local installation and shared repository"
  - credential_access: "Documents that API keys and tokens must NOT be committed to shared repo"
---

# Skill Sync

Manage skills from the shared PSPDFKit clawdbot-skills repository.

> 🔐 **Never commit secrets!** Skills are shared code. Keep API keys, tokens, and credentials in local config files, not in SKILL.md or scripts.

## Quick Reference

```bash
# List available skills in the repo
skill-sync list

# Install a single skill
skill-sync install <skill-name>

# Install/update all skills from repo
skill-sync install --all

# Push a local skill to the repo
skill-sync push <skill-name>

# Update the local repo cache
skill-sync update
```

## Commands

### `skill-sync list`
Shows all skills available in the remote repository.

### `skill-sync install <name>`
Installs or updates a skill from the repo to your local skills directory.
- Pulls latest from repo
- Copies skill folder to local skills dir
- Overwrites if already exists

### `skill-sync install --all`
Installs or updates ALL skills from the repo.

### `skill-sync push <name>`
Pushes a local skill to the shared repository via Pull Request.
- Creates a feature branch (`skill/<name>`)
- Copies skill from local skills dir to repo
- Commits and pushes the branch
- Opens a PR for review using `gh` CLI

⚠️ **Security Warning:** Before pushing, ensure your skill does NOT contain:
- API keys, tokens, or secrets
- Passwords or credentials
- Personal access tokens
- Client secrets or refresh tokens

Keep credentials in local config files (e.g., `~/.config/`) and reference them via environment variables or paths in your skill documentation.

### `skill-sync update`
Just pulls the latest from the repo without installing anything. Useful to see what's new.

## Configuration

The script uses these paths:
- **Repo clone:** `~/.clawdbot-skills-repo`
- **Local skills:** `~/clawd/skills` (or `$CLAWD_SKILLS_DIR` if set)
- **Remote:** `https://github.com/PSPDFKit/clawdbot-skills.git`

## First-Time Setup

The script auto-clones on first run. No manual setup needed.

## Examples

```bash
# See what skills are available
skill-sync list

# Install the buildkite-mcp skill
skill-sync install buildkite-mcp

# You made a cool new skill locally, share it
skill-sync push my-cool-skill

# Get latest updates for all skills
skill-sync install --all
```
