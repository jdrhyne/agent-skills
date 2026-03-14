---
name: auto-updater
description: "Automatically update OpenClaw and selected skills once daily. Runs via cron, checks for updates, applies them, and messages the user with a summary of what changed."
metadata: {"version":"1.1.0","openclaw":{"emoji":"🔄","os":["darwin","linux"]}}
---

# Auto-Updater Skill

Keep OpenClaw and skills up to date automatically with daily update checks.

## What It Does

This skill sets up a daily cron job that:

1. Updates OpenClaw itself (via package manager)
2. Updates installed ClawHub skills (via `clawhub update --all`)
3. Sends a summary of what changed

## Setup

### Quick Start

Ask OpenClaw to set up the auto-updater:

```
Set up daily auto-updates for OpenClaw and installed skills.
```

Or manually add the cron job:

```bash
openclaw cron add \
  --name "Daily Auto-Update" \
  --cron "0 4 * * *" \
  --tz "America/Los_Angeles" \
  --session isolated \
  --wake now \
  --deliver \
  --message "Run daily auto-updates: check for OpenClaw updates and update installed skills. Report what changed."
```

## How Updates Work

### OpenClaw Updates

For npm installs:

```bash
npm update -g openclaw@latest
```

After update, run health checks:

```bash
openclaw --profile default doctor --fix
openclaw gateway restart
```

### Skill Updates

```bash
clawhub update --all
```

This checks installed ClawHub skills and updates to latest versions.

## Manual Commands

Run a manual skill update:

```bash
clawhub update --all --no-input --force
```

List installed ClawHub skills:

```bash
clawhub list
```

Check OpenClaw version:

```bash
openclaw --version
```

## Troubleshooting

### Updates Not Running

1. Verify cron is enabled (`openclaw cron list`)
2. Ensure gateway is running continuously (`openclaw gateway status`)
3. Confirm cron entry exists and timezone is correct

### Common Failures

- **Permission errors**: ensure the OpenClaw user can write to install paths
- **Network errors**: verify internet connectivity
- **Broken plugin/provider state**: run `openclaw --profile default doctor --fix`

### Disable Auto-Updates

```bash
openclaw cron remove "Daily Auto-Update"
```

## Resources

- https://docs.openclaw.ai
- https://clawhub.com
