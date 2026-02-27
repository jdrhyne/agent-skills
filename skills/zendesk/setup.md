# Setup — Zendesk

Read this when `~/zendesk/` doesn't exist or is empty.

## Your Attitude

You're connecting to their support system. Be helpful and efficient — support teams are busy. Get credentials, verify they work, then start helping.

## Priority Order

### 1. First: Get Credentials (CRITICAL)

You need three things to connect:
- **Subdomain** — The `xxx` in `xxx.zendesk.com`
- **Email** — The email for API access
- **API Token** — From Admin > Channels > API

Ask naturally:
- "What's your Zendesk subdomain? (the part before .zendesk.com)"
- "And the email address for API access?"
- "Do you have an API token? You can create one in Admin > Channels > API"

Test immediately after getting credentials:
```bash
curl -s -u "$EMAIL/token:$TOKEN" "https://$SUBDOMAIN.zendesk.com/api/v2/users/me.json" | jq .user.name
```

If it works, confirm: "Connected! I can see your account."
If it fails, help diagnose: "That didn't work. Let me check — is the token active? Did you include /token in the auth?"

### 2. Then: Understand Their Workflow

Once connected, understand how they use Zendesk:
- "What kind of tickets do you handle most?"
- "Any specific views or tags you use regularly?"
- "Do you want me to help proactively when you mention support issues?"

### 3. Finally: Integration

Ask about automatic activation:
- "Should I jump in whenever you mention tickets or support?"
- "Want daily summaries of open tickets?"

Save their preference to their main memory for future sessions.

## What You're Saving (internally)

In `~/zendesk/memory.md`:
- Credentials (subdomain, email, token)
- Common views they use
- Preferred ticket templates
- SLA targets if mentioned

In user's MAIN memory:
- When to activate this skill
- Any standing preferences (daily reports, etc.)
