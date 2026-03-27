---
name: elegant-reports
description: Generate beautifully designed PDF reports with a Nordic/Scandinavian aesthetic. Use when creating polished executive briefings, analysis reports, or presentation-style PDF outputs from markdown and HTML via Nutrient DWS.
metadata: {"clawdbot":{"requires":{"bins":["node","npm"]}}}
permissions:
  - exec: "Runs the local Node generator to list templates, render preview HTML, and create PDF outputs when the user asks."
  - file_read: "Reads bundled templates, themes, examples, and design references inside the skill directory plus user-approved input markdown files."
  - file_write: "Writes generated HTML/PDF outputs and user-requested template or theme files inside approved working directories."
  - network: "Calls Nutrient DWS and any hosted font assets used by the bundled templates when the user requests report generation."
---

# elegant-reports

Generate minimalist PDF reports inspired by Scandinavian editorial design.

## When to Use

Use this skill when the user wants:
- polished executive briefings or board-style reports
- presentation-like PDFs generated from markdown
- a clean Nordic visual language instead of default developer styling
- a reusable report template system that can be extended carefully

## Quick Start

Install the pinned dependencies from `package-lock.json`, then run:

```bash
cd /path/to/elegant-reports
node ./generate.js --list
node ./generate.js examples/sample-executive.md output.pdf --template executive --theme light
```

For HTML debugging, add `--output-html` so the generator saves the rendered HTML alongside the PDF.

## Available Templates

| Template | Use Case |
|----------|----------|
| `executive` | polished briefings and compact executive summaries |
| `report` | denser narrative reports and analysis writeups |
| `presentation` | bold slide-like outputs with one idea per page |
| `report-demo` | legacy report variant for comparison/testing |
| `presentation-demo` | legacy presentation variant for comparison/testing |

Each template supports `light` and `dark` themes where available.

## Frontmatter

Add YAML frontmatter to control the rendered output:

```markdown
---
title: Q4 Competitive Analysis
subtitle: Market Intelligence Report
author: Report Author
template: report
theme: dark
---

Your content here...
```

## Workflow

1. Pick the closest existing template instead of starting from scratch.
2. Write or refine the source markdown.
3. Generate a PDF.
4. If layout tuning is needed, inspect the emitted HTML with `--output-html` and adjust the corresponding template/theme pair.
5. Re-run until the design is clean and the PDF is stable.

## Extending the Skill

When authoring a new visual variant:
- start from the nearest bundled template and theme
- keep token names and spacing scales consistent with the existing system
- make one visual change at a time and regenerate after each step
- prefer additive variants over rewriting the whole design language
- keep legacy/demo templates available until the replacement is verified

The bundled Nordic design research note is the canonical reference for the visual system. Read it only when you need deeper design rationale.

## Safety Boundaries

- Do not send sensitive source documents to third-party services unless the user explicitly requested PDF generation through Nutrient DWS and accepts that network boundary.
- Do not browse arbitrary local files. Limit reads to the skill bundle and user-approved input/output paths.
- Do not overwrite or delete files outside the user-approved working directory.
- Do not install extra packages, change dependency versions, or add new external services unless the user explicitly asks for that setup work.
- Do not claim a report was generated successfully unless the output artifact exists and the generator completed without error.
- Do not fetch external design inspiration or web references unless the user explicitly wants fresh visual research.

## Dependencies

- Node.js 18+
- pinned npm dependencies from `package-lock.json`
- `NUTRIENT_DWS_API_KEY` environment variable for PDF generation

## File Map

- main generator CLI and module entrypoint
- bundled HTML templates
- bundled visual themes
- sample markdown input
- optional deeper design rationale bundled with the skill

## Validation

Before calling the skill done:
- run `node ./generate.js --list`
- run `npm test`
- verify the expected PDF or HTML artifact exists in the requested output path
