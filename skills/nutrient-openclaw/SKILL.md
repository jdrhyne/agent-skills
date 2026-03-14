---
name: nutrient-openclaw
description: >-
  OpenClaw-native document processing skill for Nutrient DWS. Use when OpenClaw
  users need to convert files, extract text or tables, OCR scans, redact PII,
  watermark PDFs, digitally sign documents, or check credit usage from chat
  attachments or workspace files. Triggers on OpenClaw tool names
  (`nutrient_convert_to_pdf`, `nutrient_extract_text`, etc.), "OpenClaw plugin",
  "Nutrient OpenClaw", and document-processing requests in OpenClaw chats.
  Files are processed by Nutrient DWS over the network, so use it only when
  third-party document processing is acceptable. For non-OpenClaw environments,
  use the universal Nutrient document-processing skill instead.
homepage: https://www.nutrient.io/api/
clawdis:
  emoji: "📄"
  requires:
    config:
      - plugins.entries.nutrient-openclaw.config.apiKey
  install:
    - id: nutrient-openclaw
      kind: node
      package: "@nutrient-sdk/nutrient-openclaw"
      label: Install Nutrient OpenClaw package
  links:
    homepage: https://www.nutrient.io/api/
    repository: https://github.com/PSPDFKit-labs/nutrient-openclaw
    documentation: https://www.nutrient.io/api/documentation/security
  config:
    example: |
      plugins:
        entries:
          nutrient-openclaw:
            config:
              apiKey: "your-api-key-here"
---

# Nutrient Document Processing (OpenClaw Native)

Best for OpenClaw users. Process documents directly in OpenClaw conversations via native `nutrient_*` tools.

## Quick examples

- "Convert this Word file to PDF"
- "OCR this scanned contract and extract the text"
- "Redact all SSNs and email addresses from this PDF"
- "Add a CONFIDENTIAL watermark to this document"
- "How many Nutrient credits do I have left?"

## Installation

Preferred install flow inside OpenClaw:

```bash
openclaw plugins install @nutrient-sdk/nutrient-openclaw
```

Configure your API key:

```yaml
plugins:
  entries:
    nutrient-openclaw:
      config:
        apiKey: "your-api-key-here"
```

Get an API key at [nutrient.io/api](https://www.nutrient.io/api/).

## Data Handling

- `nutrient_*` operations send the file or extracted document content to Nutrient DWS for processing.
- Review Nutrient's [Processor API security](https://www.nutrient.io/api/documentation/security) and [privacy details](https://www.nutrient.io/api/processor-api/) before using production or sensitive documents.
- Nutrient documents its hosted Processor API as using HTTPS for data in transit and as not persistently storing input or output files after processing; confirm that matches your organization's requirements before uploading sensitive material.
- Start with non-sensitive sample files and a least-privilege API key.

## Tool selection

- `nutrient_convert_to_pdf` for Office, HTML, or image to PDF conversion.
- `nutrient_convert_to_image` for rendering PDF pages as PNG, JPEG, or WebP.
- `nutrient_convert_to_office` for PDF to DOCX, XLSX, or PPTX conversion.
- `nutrient_extract_text` for text, tables, and key-value extraction.
- `nutrient_ocr` for scanned PDFs or standalone images.
- `nutrient_redact` for deterministic preset-based redaction.
- `nutrient_ai_redact` for natural-language or contextual PII removal.
- `nutrient_watermark` for text or image watermarks.
- `nutrient_sign` for digital signing workflows.
- `nutrient_check_credits` before batch or AI-heavy runs.

## Workflow

1. Confirm the source file and desired output format before running any transform.
2. Prefer the narrowest tool that matches the request instead of chaining broad operations blindly.
3. Preserve the original file and write outputs with clear suffixes such as `-ocr`, `-redacted`, or `-signed`.
4. If the user asks for multiple steps, run them in the safest order: OCR first, then extraction or redaction, then watermarking or signing last.

## Decision rules

- OCR before extraction if the PDF is image-only, has unselectable text, or extraction looks sparse.
- Use `nutrient_redact` for explicit patterns like SSNs, emails, or phone numbers. Use `nutrient_ai_redact` only when the request is semantic, broad, or context-dependent.
- Render only the pages the user needs when converting PDFs to images. Avoid whole-document renders unless explicitly requested.
- Ask for signing intent and signer details before using `nutrient_sign`; do not assume legal signature requirements from a casual request.
- Check credits before batch OCR, repeated conversions, or AI redaction so the run does not fail mid-task.

## Anti-patterns

- Do not use AI redaction when a preset pattern will do. It is slower, costlier, and harder to verify.
- Do not extract text from a scan and assume failure means the file is empty. Run OCR first.
- Do not overwrite the user's source document with a transformed output.
- Do not promise a legally sufficient digital signature without confirming the workflow requirements.

## Troubleshooting

- Plugin missing or unavailable: install `@nutrient-sdk/nutrient-openclaw` first.
- Unauthorized or quota errors: verify the API key and available credits.
- Weak extraction results: rerun with OCR.
- Poor OCR quality: confirm the document language and source scan quality.

## Links

- [npm package](https://www.npmjs.com/package/@nutrient-sdk/nutrient-openclaw)
- [GitHub](https://github.com/PSPDFKit-labs/nutrient-openclaw)
- [Nutrient API](https://www.nutrient.io/)
