---
name: elegant-reports
description: Generate beautifully designed PDF reports with Nordic/Scandinavian aesthetic. Uses Nutrient DWS API for HTML-to-PDF conversion.
---

# elegant-reports

Generate minimalist, elegant PDF reports inspired by Scandinavian design principles.

## Quick Start

```bash
cd ~/clawd-nuri-internal/skills/elegant-reports

# Generate a report (dense layout)
node generate.js report.md output.pdf --template report

# Generate a presentation (bold slides)
node generate.js data.md slides.pdf --template presentation

# Dark mode
node generate.js report.md --template report --theme dark

# List templates
node generate.js --list
```

## Templates

| Template | Style | Use Case |
|----------|-------|----------|
| `report` | Dense, multi-column | Deep dives, analysis, strategy docs |
| `presentation` | Big & bold, one idea/page | Exec briefings, board decks |
| `report-demo` | Static example | Demo only (hardcoded Apryse content) |
| `presentation-demo` | Static example | Demo only (hardcoded Apryse content) |

Each template supports `--theme light` (default) or `--theme dark`.

**Note:** The `report` and `presentation` templates dynamically inject your markdown content via `{{content}}`. The `-demo` variants contain static example content for reference.

## Frontmatter

Add YAML frontmatter to control output:

```markdown
---
title: Q4 Competitive Analysis
subtitle: Market Intelligence Report
author: Nuri
template: report
theme: dark
---

Your content here...
```

## Design Philosophy

Based on Nordic/Scandinavian design principles:
- **Bold typography** — Poppins for headlines, Inter for body
- **High contrast** — Dark headers, clear hierarchy
- **Generous whitespace** — Content breathes
- **One accent color** — Blue (#2563EB) used sparingly
- **Functional beauty** — Form follows function

See `NORDIC_DESIGN_RESEARCH.md` for complete design documentation.

---

# Creating New Templates

## The Visual Iteration Workflow

This is how to create new templates with visual feedback:

### Step 1: Research References

```bash
# Use browser tool to study design examples
browser navigate https://www.canva.com/templates/...
browser screenshot

# Look for:
# - Typography choices (font, size, weight)
# - Color palette (backgrounds, text, accents)
# - Layout patterns (grids, spacing)
# - Component styles (cards, tables, callouts)
```

### Step 2: Create Theme CSS

Create a new CSS file in `themes/`:

```css
/* themes/my-theme.css */

@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800&family=Inter:wght@400;500&display=swap');

:root {
  /* Color tokens */
  --color-bg: #FAFAFA;
  --color-surface: #FFFFFF;
  --color-text-primary: #0A0A0A;
  --color-text-secondary: #404040;
  --color-accent: #2563EB;
  
  /* Typography tokens */
  --font-display: 'Poppins', sans-serif;
  --font-body: 'Inter', sans-serif;
  
  /* Spacing tokens */
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
}

/* Component styles... */
```

### Step 3: Create Template HTML

Create HTML in `templates/`:

```html
<!-- templates/my-template.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{title}}</title>
  <style>
{{styles}}
  </style>
</head>
<body>
  <div class="page">
    <h1>{{title}}</h1>
    <p>{{subtitle}}</p>
    {{content}}
  </div>
</body>
</html>
```

Available variables: `{{title}}`, `{{subtitle}}`, `{{author}}`, `{{date}}`, `{{content}}`, `{{styles}}`

### Step 4: Test with Visual Feedback

```bash
# Generate test HTML manually
node -e "
const fs = require('fs');
const css = fs.readFileSync('themes/my-theme.css', 'utf8');
let html = fs.readFileSync('templates/my-template.html', 'utf8');
html = html.replace('{{styles}}', css);
html = html.replace(/\{\{title\}\}/g, 'Test Title');
html = html.replace(/\{\{subtitle\}\}/g, 'Test Subtitle');
html = html.replace(/\{\{date\}\}/g, 'January 2026');
html = html.replace(/\{\{author\}\}/g, 'Nuri');
html = html.replace(/\{\{content\}\}/g, '<p>Test content</p>');
fs.writeFileSync('test-output.html', html);
"

# Preview in browser
browser navigate file://$(pwd)/test-output.html
browser screenshot

# See what's wrong, fix it, repeat
```

### Step 5: Register in Generator

Add to `TEMPLATES` object in `generate.js`:

```javascript
const TEMPLATES = {
  // ...existing templates...
  
  'my-template': {
    description: 'My custom template description',
    template: 'my-template.html',
    themes: {
      light: 'my-theme.css',
      dark: 'my-theme-dark.css'
    }
  }
};
```

### Step 6: Test PDF Generation

```bash
node generate.js test.md output.pdf --template my-template --output-html
```

---

## Design Tokens Reference

### Typography Scale

| Token | Size | Use |
|-------|------|-----|
| `--text-xs` | 11-12px | Labels, captions |
| `--text-sm` | 13-14px | Body (dense) |
| `--text-base` | 14-16px | Body (normal) |
| `--text-lg` | 16-18px | Lead paragraphs |
| `--text-xl` | 18-20px | Section headers |
| `--text-2xl` | 20-24px | H3 |
| `--text-3xl` | 24-32px | H2 |
| `--text-4xl` | 32-40px | H1 (report) |
| `--text-5xl` | 48-56px | H1 (presentation) |
| `--text-6xl` | 64-72px | Hero text |

### Spacing Scale

| Token | Size | Use |
|-------|------|-----|
| `--space-1` | 2-4px | Tight gaps |
| `--space-2` | 4-8px | Inline spacing |
| `--space-3` | 8-12px | Component padding |
| `--space-4` | 12-16px | Card padding |
| `--space-6` | 20-24px | Section gaps |
| `--space-8` | 28-32px | Major sections |
| `--space-10` | 36-40px | Page sections |
| `--space-12` | 44-48px | Page margins |

### Color Palette

**Light Mode:**
```css
--color-bg: #FAFAFA;
--color-surface: #FFFFFF;
--color-text-primary: #0A0A0A;
--color-text-secondary: #404040;
--color-text-muted: #737373;
--color-accent: #2563EB;
```

**Dark Mode:**
```css
--color-bg: #09090B;
--color-surface: #18181B;
--color-text-primary: #FAFAFA;
--color-text-secondary: #D4D4D8;
--color-text-muted: #A1A1AA;
--color-accent: #3B82F6;
```

---

## Component Patterns

### KPI Strip (horizontal metrics)
```html
<div class="kpi-strip">
  <div class="kpi-item">
    <div class="kpi-value">$10.8M</div>
    <div class="kpi-label">Revenue</div>
    <div class="kpi-change positive">+12%</div>
  </div>
  <!-- more items -->
</div>
```

### Key Findings Box
```html
<div class="key-findings">
  <div class="key-findings-title">Key Points</div>
  <ul>
    <li><strong>Point 1</strong> — Details</li>
    <li><strong>Point 2</strong> — Details</li>
  </ul>
</div>
```

### Two-Column Layout
```html
<div class="two-col">
  <div>Left column content</div>
  <div>Right column content</div>
</div>
```

### Callouts
```html
<div class="callout callout-tip">
  <div class="callout-title">Tip</div>
  <p>Content here</p>
</div>
```
Types: `callout-tip` (green), `callout-warning` (amber), `callout-danger` (red)

### Tables with Dark Headers
```html
<table class="no-break">
  <thead>
    <tr><th>Header</th><th class="num">Value</th></tr>
  </thead>
  <tbody>
    <tr><td>Row</td><td class="num">123</td></tr>
  </tbody>
</table>
```

---

## Page Break Control

Add these classes to prevent awkward breaks:

```html
<div class="no-break">This won't split across pages</div>
<div class="page-break">Forces new page before this</div>
```

Tables, cards, callouts, and KPI strips have `page-break-inside: avoid` by default.

---

## Files Structure

```
elegant-reports/
├── SKILL.md                    # This file
├── NORDIC_DESIGN_RESEARCH.md   # Design principles documentation
├── generate.js                 # Main generator script
├── package.json
├── themes/
│   ├── nordic-v2.css           # Presentation light
│   ├── nordic-report.css       # Report light
│   └── nordic-report-dark.css  # Report dark
├── templates/
│   ├── executive-v2.html       # Presentation template
│   └── report-v2.html          # Report template
└── examples/
    └── sample-executive.md     # Example input
```

---

## Dependencies

- Node.js 18+
- axios, form-data (`npm install`)
- Nutrient DWS API key (configured in mcporter or NUTRIENT_DWS_API_KEY env var)

## API Usage

```javascript
const { generateReport } = require('./generate.js');

await generateReport({
  input: 'report.md',
  output: 'report.pdf',
  template: 'report',
  theme: 'dark',
  title: 'My Report',
  author: 'Nuri'
});
```
