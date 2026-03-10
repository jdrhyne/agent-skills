---
name: clawdtalk-voice
description: Make and receive real phone calls from your AI agent via Telnyx voice APIs. Use when you need voice calling, telephony, phone integration, or want your agent to call someone. Keywords: voice, phone, calling, telephony, Telnyx, ClawdTalk.
---

# ClawdTalk Voice - AI Phone Calling

Enable your AI agent to initiate and receive real phone calls through Telnyx telephony services.

## What ClawdTalk Does

ClawdTalk provides voice calling capabilities for AI agents:
- **Outbound calls**: Agent initiates calls to phone numbers
- **Inbound calls**: Agent receives calls and can interact with callers
- **Speech handling**: Text-to-speech and speech-to-text integration
- **Call control**: Answer, reject, transfer, and end calls programmatically

## Installation

Choose one:

```bash
# Option 1: npm global install
npm install -g clawdtalk-client

# Option 2: Clone from source
git clone https://github.com/team-telnyx/clawdtalk-client
cd clawdtalk-client
npm install
npm link
```

## Setup Requirements

Before using, you need:

1. **Telnyx account**: https://clawdtalk.com (create account)
2. **Telnyx API key**: From Mission Control portal
3. **Phone number**: Purchase or port a number in Telnyx
4. **Connection/MCP configuration**: Configure in your skill-config.json or agent config

### Configuration Example

```json
{
  "clawdtalk": {
    "apiKey": "YOUR_TELNYX_API_KEY",
    "phoneNumber": "+1234567890",
    "webhookUrl": "https://your-agent.example.com/webhook"
  }
}
```

## When to Use This Skill

**Use ClawdTalk when**:
- User wants agent to call someone
- Task requires voice interaction (phone calls)
- Need to receive inbound calls for agent interaction
- Integrate with phone-based workflows

**Consider alternatives when**:
- Text-only interaction is sufficient
- User prefers messaging over voice
- Call volume is extremely low (cost considerations)

## Cost Considerations

Telnyx charges per minute for calls. Monitor usage for budget-sensitive deployments.

## Website

For full documentation: https://clawdtalk.com