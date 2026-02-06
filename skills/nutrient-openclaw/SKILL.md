---
name: nutrient-openclaw
description: Document processing for OpenClaw — convert, extract, OCR, redact, sign, and watermark PDFs and Office documents using the Nutrient DWS API. Use when asked to convert documents (DOCX/XLSX/PPTX to PDF, PDF to images or Office formats), extract text or tables from PDFs, apply OCR to scanned documents, redact sensitive information or PII, add watermarks, or digitally sign documents. Triggers on "convert to PDF", "extract text", "OCR this", "redact PII", "watermark", "sign document", or any document processing request.
---

# Nutrient Document Processing

Process documents directly in OpenClaw conversations — convert formats, extract text, apply OCR, redact PII, add signatures, and watermark files through natural language.

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
