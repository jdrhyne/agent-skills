# Nudocs CLI formats

Read this reference only for an upload or export whose format is not already explicit.

The maintained `@nutrient-sdk/nudocs-cli` documentation currently lists these formats:

## Upload

| Format | Extensions |
|---|---|
| Markdown | `.md` |
| Microsoft Word | `.doc`, `.docx` |
| PDF | `.pdf` |
| HTML | `.html` |
| Plain text | `.txt` |
| OpenDocument | `.odt` |
| Rich Text | `.rtf` |
| EPUB | `.epub` |
| LaTeX | `.tex`, `.latex` |

## Export

| Format | CLI value |
|---|---|
| Microsoft Word | `docx` (default) |
| Markdown | `md` |
| PDF | `pdf` |
| HTML | `html` |
| Plain text | `txt` |

Confirm the installed version with `nudocs upload --help` or `nudocs pull --help` before rejecting a format or promising conversion fidelity. The service may change supported formats independently of this skill.

Examples using the maintained CLI:

```bash
nudocs upload report.md
nudocs pull 01ABC123XYZ --format pdf --output report.pdf
nudocs pull 01ABC123XYZ --format md --output report.md
```

Resolve the exact output path first and do not overwrite an existing file without confirmation. Format conversion can lose layout, comments, or other features; do not promise lossless round trips unless the current service documents them.
