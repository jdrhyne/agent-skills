---
name: Zendesk
slug: zendesk
version: 1.0.0
homepage: https://clawic.com/skills/zendesk
description: Manage Zendesk tickets, users, and support workflows with API integration and automation.
changelog: Initial release with ticket management, user lookup, and workflow automation.
metadata: {"clawdbot":{"emoji":"🎫","requires":{"bins":[],"env":["ZENDESK_SUBDOMAIN","ZENDESK_EMAIL","ZENDESK_TOKEN"]},"os":["linux","darwin","win32"]}}
---

## Setup

On first use, read `setup.md` for API credentials and workspace integration.

## When to Use

User needs to interact with Zendesk: create or update tickets, search support history, check user details, or automate support workflows. Agent handles API operations, ticket management, and reporting.

## Architecture

Memory at `~/zendesk/`. See `memory-template.md` for structure.

```
~/zendesk/
├── memory.md        # Credentials + preferences + recent context
├── templates/       # Saved ticket templates and macros
└── exports/         # Report exports and ticket dumps
```

## Quick Reference

| Topic | File |
|-------|------|
| Setup process | `setup.md` |
| Memory template | `memory-template.md` |
| API operations | `api-reference.md` |
| Common issues | `troubleshooting.md` |

## Core Rules

### 1. Authenticate Before Operations
Credentials from environment variables (ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_TOKEN) or `~/zendesk/memory.md`.
```bash
# Test auth
curl -u "$ZENDESK_EMAIL/token:$ZENDESK_TOKEN" "https://$ZENDESK_SUBDOMAIN.zendesk.com/api/v2/users/me.json"
```

### 2. Search Before Create
Always search existing tickets before creating new ones to avoid duplicates.
```bash
curl -u "$AUTH" "$BASE/search.json?query=type:ticket+subject:issue"
```

### 3. Use Views for Efficiency
Don't list all tickets. Use views to get relevant subsets.
| View | Use Case |
|------|----------|
| `/views/active` | Get available views |
| `/views/{id}/tickets` | Tickets in specific view |
| `/tickets/recent` | Recently updated |

### 4. Preserve Ticket History
When updating, add internal notes explaining changes. Never delete ticket data.

### 5. Rate Limits
Zendesk limits: 700 requests/minute (Enterprise), 200/minute (others). Add delays for bulk operations.

### 6. Always Confirm Destructive Actions
Before closing, merging, or deleting tickets, confirm with user and summarize what will happen.

## Common Operations

Set auth: `AUTH="$ZENDESK_EMAIL/token:$ZENDESK_TOKEN"` and `BASE="https://$ZENDESK_SUBDOMAIN.zendesk.com/api/v2"`

### Create Ticket
```bash
curl -X POST "$BASE/tickets.json" -u "$AUTH" -H "Content-Type: application/json" \
  -d '{"ticket":{"subject":"Issue","comment":{"body":"Description"},"priority":"normal"}}'
```

### Update Ticket Status
```bash
curl -X PUT "$BASE/tickets/$ID.json" -u "$AUTH" -H "Content-Type: application/json" \
  -d '{"ticket":{"status":"solved","comment":{"body":"Resolution","public":false}}}'
```

### Search Tickets
```bash
curl -u "$AUTH" "$BASE/search.json?query=type:ticket+status:open+priority:urgent"
```

### Get User Details
```bash
curl -u "$AUTH" "$BASE/users/search.json?query=email:user@example.com"
```

## Ticket Statuses

| Status | Meaning | Next Actions |
|--------|---------|--------------|
| new | Unassigned | Assign, respond |
| open | Being worked | Update, solve |
| pending | Waiting on customer | Follow up, solve |
| hold | Waiting internally | Unhold, update |
| solved | Resolution provided | Close (auto after 4 days) |
| closed | Final | Reopen creates new ticket |

## Priorities

| Priority | SLA Target | Use For |
|----------|-----------|---------|
| urgent | 1 hour | System down, revenue impact |
| high | 4 hours | Major feature broken |
| normal | 8 hours | Standard issues |
| low | 24 hours | Questions, minor bugs |

## Common Traps

- **Auth format wrong** → Must be `email/token:API_TOKEN`, not just token
- **Searching with special chars** → URL-encode queries
- **Bulk updates failing** → Check rate limits, add 100ms delay
- **Missing ticket fields** → Some fields require specific plans
- **Pagination ignored** → Results capped at 100, use `next_page` URL

## External Endpoints

| Endpoint | Data Sent | Purpose |
|----------|-----------|---------|
| `https://{subdomain}.zendesk.com/api/v2/*` | Ticket/user data | All operations |

No other data is sent externally.

## Security & Privacy

**Data that leaves your machine:**
- Ticket content sent to Zendesk API
- Search queries sent to Zendesk

**Data that stays local:**
- API credentials in ~/zendesk/memory.md
- Exported reports in ~/zendesk/exports/

**This skill does NOT:**
- Store credentials in plain text outside ~/zendesk/
- Send data to any service other than Zendesk
- Access tickets without explicit user request

## Trust

By using this skill, ticket and user data is sent to Zendesk's API.
Only install if you have authorized Zendesk API access.

## Related Skills
Install with `clawhub install <slug>` if user confirms:
- `api` - REST API patterns
- `customer-support` - Support best practices
- `csv` - Export and analyze ticket data

## Feedback

- If useful: `clawhub star zendesk`
- Stay updated: `clawhub sync`
