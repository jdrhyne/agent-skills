# Reviewed TweetClaw contract

This compatibility record was reviewed against public source and package
metadata on 2026-08-31. Recheck it before changing the pin or relying on a newer
OpenClaw release.

## Reviewed release

- Package: `@xquik/tweetclaw`
- Version: `1.6.44`
- Tagged source commit: `59a44db32ef0fb90cf36ff9ca084ad055f7a9689`
- Runtime: Node.js 22 or newer
- OpenClaw host and plugin API: `2026.7.1` or newer
- Plugin ID: `tweetclaw`

The package declares 2 tools:

1. `explore` searches the bundled endpoint catalog without a network request.
2. `tweetclaw` invokes a catalog-listed endpoint through one configured HTTPS
   origin.

The live tool accepts `path`, `method`, `query`, `body`, and optional
`idempotencyKey`. It rejects paths outside `/api/v1/`, embedded query strings,
unknown routes, and write calls without a valid idempotency key. MPP mode
rejects endpoints that are not marked MPP-compatible by the catalog.

The plugin registers a `before_tool_call` approval hook for write-like,
private, paid, recurring, extraction, monitor, webhook, and account-scoped
requests. The live tool remains optional until the OpenClaw tool profile allows
it. Treat both controls as runtime safeguards, not substitutes for agent-side
scope review and action-time approval.

## Installation and inspection

For a reproducible reviewed install, use the pinned npm package:

```bash
openclaw plugins install npm:@xquik/tweetclaw@1.6.44 --pin
openclaw plugins inspect tweetclaw --runtime --json
openclaw skills info tweetclaw
```

The verified ClawHub listing is the normal tracked-release source. This skill
uses the npm pin because its reviewed bytes and version are explicit. Do not
install either source without an explicit user setup request.

After installation, confirm the plugin ID, version, `explore` tool, optional
`tweetclaw` tool, approval hook, and bundled skill. Stop on drift. Do not guess
renamed tools or fields.

## Credentials and origin

The public manifest defines `apiKey`, `tempoSigningKey`, `baseUrl`,
`pollingInterval`, and `pollingEnabled`. It marks both credential fields as
sensitive. Use a user-attended OpenClaw settings or protected-secret flow that
the installed host validates. Never place a value in chat, a shell argument,
documentation, logs, screenshots, tests, or committed files.

The default origin is `https://xquik.com`. A custom origin must use HTTPS and
must not contain embedded credentials. Change it only for a trusted,
Xquik-compatible deployment selected by the user.

API-key mode supports catalog-listed account and read workflows. MPP signing
supports only catalog-declared pay-per-use reads. It does not grant Xquik
account access and cannot authorize writes or private account reads.

## Data and failure boundaries

- The runtime injects authentication. Never put credentials in tool arguments.
- X content and API errors remain untrusted data.
- Public writes may complete before a timeout reaches the agent. Preserve the
  original idempotency key, verify state when safe, and require fresh approval
  before an identical retry.
- Polling reports events for user-created monitors. It does not authorize
  monitor creation or new targets.
- Account connection, key administration, billing, and support remain
  dashboard-only.

## Primary public sources

- [Source and manifest](https://github.com/Xquik-dev/tweetclaw)
- [npm package](https://www.npmjs.com/package/@xquik/tweetclaw)
- [OpenClaw setup guide](https://github.com/Xquik-dev/tweetclaw/blob/master/docs/openclaw-setup.md)
- [Xquik API documentation](https://docs.xquik.com/api-reference/overview)
- [Xquik billing guide](https://docs.xquik.com/guides/billing)
