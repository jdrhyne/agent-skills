# Reviewed plugin contract

This compatibility record was reviewed against the official package and source on 2026-08-29. Recheck it before changing the pin or relying on a newer OpenClaw release.

## Pinned package

- Package: `@nutrient-sdk/nutrient-openclaw`
- Version: `0.1.1`
- Reviewed upstream commit: `64077d47c648c5a3219131de2dbddc22836cbf09`
- Runtime: Node.js 18 or newer
- Upstream peer declaration: optional `openclaw` with range `*`

The wildcard peer range is an upstream declaration, not proof that the plugin works with every past or future OpenClaw release. After an explicitly requested install or update, verify the installed version, manifest, Node.js requirement, configuration validation, and exposed tool inventory before processing a document. Stop on drift; do not guess a changed schema.

The pinned package's configuration schema defines optional `apiKey` and `sandboxDir` fields and marks `apiKey` sensitive in its UI hint. The full key target is `plugins.entries.nutrient-openclaw.config.apiKey`. Its manifest does not declare `secretInputs`. A current OpenClaw runtime can use a SecretRef for a plugin field only when that binding validates and resolves in the actual installation. Do not promise support from the sensitive UI hint alone, and never expose a credential as a compatibility workaround.

## Tool inventory

Version `0.1.1` declares exactly these tools:

1. `nutrient_convert_to_pdf`
2. `nutrient_convert_to_image`
3. `nutrient_convert_to_office`
4. `nutrient_extract_text`
5. `nutrient_ocr`
6. `nutrient_redact`
7. `nutrient_ai_redact`
8. `nutrient_watermark`
9. `nutrient_sign`
10. `nutrient_check_credits`

The first nine invoke hosted Nutrient DWS processing. The credit checker reads a JSONL usage tracker under the plugin sandbox and returns prior local state. It is not a live quote, exact preflight, or credit reservation.

Version `0.1.1` does not expose Nutrient's Analyze operation. When an already-configured, protected, authenticated Analyze capability is available for a Build-compatible payload, it can calculate the Build cost without processing and is free according to the current official documentation. Otherwise derive a numeric estimate or bounded range from current official pricing and disclose assumptions. Do not add a raw authenticated request example.

The signing tool calls the DWS signing endpoint and accepts signing metadata/appearance options, but it exposes no user-supplied certificate or private-key field. Treat that as a material workflow limitation, not proof of signer identity or legal sufficiency.

The AI-redaction tool produces a permanently redacted output in one call and exposes no dry-run. Keep the source, use a candidate output, and require complete human verification. Any rendering used for review is a separately estimated and confirmed DWS call.

## Primary sources

- [Package source and manifest](https://github.com/PSPDFKit-labs/nutrient-openclaw)
- [Published npm package](https://www.npmjs.com/package/@nutrient-sdk/nutrient-openclaw)
- [OpenClaw skill metadata and base-directory paths](https://docs.openclaw.ai/skills)
- [OpenClaw SecretRef model](https://docs.openclaw.ai/gateway/secrets)
- [OpenClaw plugin secret guidance](https://docs.openclaw.ai/plugins/tool-plugins)
- [Nutrient DWS credit calculation](https://www.nutrient.io/guides/dws-processor/pricing/calculate-credit-usage/)
