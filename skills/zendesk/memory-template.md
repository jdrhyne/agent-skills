# Memory Template — Zendesk

Create `~/zendesk/memory.md` with this structure:

```markdown
# Zendesk Memory

## Status
status: ongoing
version: 1.0.0
last: YYYY-MM-DD
integration: pending

## Credentials
subdomain: 
email: 
token: 

## Preferences
default_view: 
default_priority: normal
notify_urgent: true

## Common Views
<!-- Views they use frequently -->

## Templates
<!-- Saved response templates -->

## Recent Context
<!-- Recent tickets worked on, patterns noticed -->

---
*Updated: YYYY-MM-DD*
```

## Status Values

| Value | Meaning | Behavior |
|-------|---------|----------|
| `ongoing` | Still learning preferences | Gather context over time |
| `complete` | Has full context | Work normally |
| `paused` | User said "not now" | Don't ask, work with basics |

## Credential Security

- Store credentials in `~/zendesk/memory.md` or use environment variables
- Environment variables: ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_TOKEN
- Never echo credentials in responses
- Never commit credentials to any repo
- If user shares credentials in chat, remind them to rotate

## Key Principles

- Credentials are required before any operation
- Test auth immediately after receiving credentials
- Learn view preferences over time
- Track common ticket patterns for efficiency
