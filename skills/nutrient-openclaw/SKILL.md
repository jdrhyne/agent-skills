---
name: nutrient-openclaw
description: OpenClaw-native PDF/document processing skill for Nutrient DWS. Best for OpenClaw users who need PDF conversion, OCR, text/table extraction, PII redaction, watermarking, digital signatures, and API credit checks via built-in `nutrient_*` tools. Triggers on OpenClaw tool names (`nutrient_convert_to_pdf`, `nutrient_extract_text`, etc.), "OpenClaw plugin", "Nutrient OpenClaw", and document-processing requests in OpenClaw chats. For non-OpenClaw environments, use the Universal Nutrient Document Processing skill instead.
homepage: https://www.nutrient.io/api/
metadata:
  {
    "openclaw":
      {
        "emoji": "📄",
        "requires":
          {
            "config":
              ["plugins.entries.nutrient-openclaw.config.apiKey"],
          },
        "install":
          [
            {
              "id": "nutrient-openclaw",
              "kind": "plugin",
              "package": "@nutrient-sdk/nutrient-openclaw",
              "label": "Install Nutrient OpenClaw plugin",
            },
          ],
      },
  }
---

# Nutrient Document Processing (OpenClaw Native)

Best for OpenClaw users. Process documents directly in OpenClaw conversations — PDF conversion, text/table extraction, OCR, PII redaction, digital signatures, and watermarking via native `nutrient_*` tools.

## Installation

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

Get an API key at [nutrient.io/api](https://www.nutrient.io/api/)

## Available Tools

| Tool | Description |
|------|-------------|
| `nutrient_convert_to_pdf` | Convert DOCX, XLSX, PPTX, HTML, or images to PDF |
| `nutrient_convert_to_image` | Render PDF pages as PNG, JPEG, or WebP |
| `nutrient_convert_to_office` | Convert PDF to DOCX, XLSX, or PPTX |
| `nutrient_extract_text` | Extract text, tables, or key-value pairs |
| `nutrient_ocr` | Apply OCR to scanned PDFs or images |
| `nutrient_watermark` | Add text or image watermarks |
| `nutrient_redact` | Redact via patterns (SSN, email, phone) |
| `nutrient_ai_redact` | AI-powered PII detection and redaction |
| `nutrient_sign` | Digitally sign PDF documents |
| `nutrient_check_credits` | Check API credit balance and usage |

## Example Prompts

**Convert:** "Convert this Word doc to PDF"

**Extract:** "Extract all text from this scanned receipt" / "Pull tables from this PDF"

**Redact:** "Redact all PII from this document" / "Remove email addresses and phone numbers"

**Watermark:** "Add a CONFIDENTIAL watermark to this PDF"

**Sign:** "Sign this contract as Jonathan Rhyne"

## Links

- [npm package](https://www.npmjs.com/package/@nutrient-sdk/nutrient-openclaw)
- [GitHub](https://github.com/PSPDFKit-labs/nutrient-openclaw)
- [Nutrient API](https://www.nutrient.io/)
