---
name: clawdbot-release-check
description: Check for new OpenClaw releases and notify once per new version.
homepage: https://github.com/openclaw/openclaw
metadata: {"openclaw":{"emoji":"🔄","requires":{"bins":["curl","jq"]}}}
---

# OpenClaw Release Check

Checks for new OpenClaw releases from GitHub and notifies once per version (no spam).

## Installation

```bash
clawhub install clawdbot-release-check
```

## Quick Setup (cron)

```bash
# Add daily update check at 9am, notify via Telegram
{baseDir}/scripts/setup.sh --telegram YOUR_TELEGRAM_ID

# Custom hour
{baseDir}/scripts/setup.sh --hour 8 --telegram YOUR_TELEGRAM_ID

# Remove cron job
{baseDir}/scripts/setup.sh --uninstall
```

After setup, restart gateway:

```bash
openclaw gateway restart
```

## Manual Usage

```bash
{baseDir}/scripts/check.sh
{baseDir}/scripts/check.sh --status
{baseDir}/scripts/check.sh --force
{baseDir}/scripts/check.sh --all-highlights
{baseDir}/scripts/check.sh --reset
{baseDir}/scripts/check.sh --help
```

## Files

- State: `~/.openclaw/clawdbot-release-check-state.json`
- Cache: `~/.openclaw/clawdbot-release-check-cache.json`

## Configuration

Environment variables:

- `OPENCLAW_DIR` — path to OpenClaw source/install
- `CACHE_MAX_AGE_HOURS` — cache TTL in hours (default: 24)
