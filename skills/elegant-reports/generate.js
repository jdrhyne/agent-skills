#!/usr/bin/env node
/**
 * elegant-reports - Generate beautiful Nordic-style PDF reports
 * Uses Nutrient DWS API for HTML-to-PDF conversion
 * 
 * Templates:
 *   - presentation: Big bold slides, one idea per page
 *   - report: Dense information, multi-column layouts
 * 
 * Themes:
 *   - light: Clean light background
 *   - dark: Dark mode with gradients
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const CONFIG = {
  apiKey: process.env.NUTRIENT_DWS_API_KEY || '',
  apiUrl: 'https://api.nutrient.io/build',
  templatesDir: path.join(__dirname, 'templates'),
  themesDir: path.join(__dirname, 'themes'),
  sandboxDir: path.join(process.env.HOME, 'nuri_workspace/nutrient-dws-sandbox')
};

// Available templates and their themes
const TEMPLATES = {
  presentation: {
    description: 'Big bold slides, one idea per page (exec briefings, board decks)',
    template: 'presentation-dynamic.html',
    themes: {
      light: 'nordic-v2.css',
      dark: 'nordic-v2.css'  // TODO: create presentation dark
    }
  },
  report: {
    description: 'Dense information layout, multi-column (deep dives, analysis)',
    template: 'report-dynamic.html',
    themes: {
      light: 'nordic-report.css',
      dark: 'nordic-report-dark.css'
    }
  },
  'presentation-demo': {
    description: '[Demo] Static Apryse example - presentation format',
    template: 'executive-v2.html',
    themes: {
      light: 'nordic-v2.css',
      dark: 'nordic-v2.css'
    }
  },
  'report-demo': {
    description: '[Demo] Static Apryse example - report format',
    template: 'report-v2.html',
    themes: {
      light: 'nordic-report.css',
      dark: 'nordic-report-dark.css'
    }
  },
  // Legacy templates
  executive: {
    description: '[Legacy] Original executive template',
    template: 'executive.html',
    themes: {
      light: 'nordic-light.css',
      dark: 'nordic-dark.css'
    }
  }
};

// Load API key from mcporter config if not in env
function loadApiKey() {
  if (CONFIG.apiKey) return;
  
  try {
    const configPath = path.join(process.env.HOME, 'clawd-nuri-internal/config/mcporter.json');
    const mcpConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    CONFIG.apiKey = mcpConfig.mcpServers?.['nutrient-dws']?.env?.NUTRIENT_DWS_API_KEY || '';
  } catch (e) {
    // Ignore
  }
}

// Simple Markdown to HTML conversion
function markdownToHtml(markdown) {
  let html = markdown;
  
  // Step 1: Extract code blocks and replace with placeholders to protect them
  const codeBlocks = [];
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
    const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
    codeBlocks.push(`<pre><code class="language-${lang || 'text'}">${escapeHtml(code.trim())}</code></pre>`);
    return placeholder;
  });
  
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // Headers
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  
  // Bold and italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  
  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  
  // Blockquotes
  html = html.replace(/^> (.+)$/gm, '<blockquote><p>$1</p></blockquote>');
  
  // Horizontal rules
  html = html.replace(/^---$/gm, '<hr>');
  
  // Tables
  html = parseMarkdownTables(html);
  
  // Lists
  html = html.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
  
  // Paragraphs - skip lines that are placeholders or already HTML tags
  html = html.replace(/^(?!<[a-z]|__|$)(.+)$/gm, '<p>$1</p>');
  
  // Step 2: Restore code blocks from placeholders
  codeBlocks.forEach((block, i) => {
    html = html.replace(`__CODE_BLOCK_${i}__`, block);
  });
  
  return html;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function parseMarkdownTables(html) {
  const tableRegex = /\|(.+)\|\n\|[\-\|: ]+\|\n((?:\|.+\|\n?)+)/g;
  
  return html.replace(tableRegex, (_, headerRow, bodyRows) => {
    const headers = headerRow.split('|').map(h => h.trim()).filter(Boolean);
    const rows = bodyRows.trim().split('\n').map(row => 
      row.split('|').map(cell => cell.trim()).filter(Boolean)
    );
    
    let table = '<table class="no-break"><thead><tr>';
    headers.forEach(h => { table += `<th>${h}</th>`; });
    table += '</tr></thead><tbody>';
    
    rows.forEach(row => {
      table += '<tr>';
      row.forEach(cell => { table += `<td>${cell}</td>`; });
      table += '</tr>';
    });
    
    table += '</tbody></table>';
    return table;
  });
}

// Parse frontmatter
function parseFrontmatter(markdown) {
  const match = markdown.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return { meta: {}, content: markdown };
  
  const meta = {};
  match[1].split('\n').forEach(line => {
    const [key, ...valueParts] = line.split(':');
    if (key && valueParts.length) {
      meta[key.trim()] = valueParts.join(':').trim();
    }
  });
  
  return { meta, content: match[2] };
}

// Load template and theme, combine them
function loadTemplate(templateName, theme = 'light') {
  const templateConfig = TEMPLATES[templateName];
  if (!templateConfig) {
    throw new Error(`Unknown template: ${templateName}. Available: ${Object.keys(TEMPLATES).join(', ')}`);
  }
  
  const templatePath = path.join(CONFIG.templatesDir, templateConfig.template);
  const themePath = path.join(CONFIG.themesDir, templateConfig.themes[theme] || templateConfig.themes.light);
  
  if (!fs.existsSync(templatePath)) {
    throw new Error(`Template file not found: ${templatePath}`);
  }
  
  let template = fs.readFileSync(templatePath, 'utf8');
  let styles = '';
  
  if (fs.existsSync(themePath)) {
    styles = fs.readFileSync(themePath, 'utf8');
  }
  
  return { template, styles };
}

// Replace template variables
function populateTemplate(template, styles, data) {
  let html = template.replace('{{styles}}', styles);
  
  // Replace simple variables
  Object.entries(data).forEach(([key, value]) => {
    if (typeof value === 'string') {
      html = html.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), value);
    }
  });
  
  // Clean up remaining placeholders
  html = html.replace(/\{\{[^}]+\}\}/g, '');
  
  return html;
}

// Generate PDF via Nutrient API
async function generatePdfApi(html, outputPath) {
  const FormData = require('form-data');
  const axios = require('axios');
  
  // Write HTML to sandbox
  const htmlPath = path.join(CONFIG.sandboxDir, 'report.html');
  fs.writeFileSync(htmlPath, html);
  
  const form = new FormData();
  form.append('report.html', fs.createReadStream(htmlPath));
  form.append('instructions', JSON.stringify({
    parts: [{ html: 'report.html' }],
    output: { type: 'pdf' }
  }));
  
  const response = await axios.post(CONFIG.apiUrl, form, {
    headers: {
      ...form.getHeaders(),
      'Authorization': `Bearer ${CONFIG.apiKey}`
    },
    responseType: 'arraybuffer'
  });
  
  fs.writeFileSync(outputPath, response.data);
  return outputPath;
}

// Generate PDF via curl (fallback)
function generatePdfCurl(html, outputPath) {
  const htmlPath = path.join(CONFIG.sandboxDir, 'report.html');
  fs.writeFileSync(htmlPath, html);
  
  const cmd = `curl -s -X POST '${CONFIG.apiUrl}' ` +
    `-H 'Authorization: Bearer ${CONFIG.apiKey}' ` +
    `-F 'report.html=@${htmlPath}' ` +
    `-F 'instructions={"parts":[{"html":"report.html"}]}' ` +
    `-o '${outputPath}'`;
  
  execSync(cmd);
  return outputPath;
}

// Main generate function
async function generateReport(options) {
  loadApiKey();
  
  if (!CONFIG.apiKey) {
    throw new Error('NUTRIENT_DWS_API_KEY not set. Set env var or configure in mcporter.');
  }
  
  const {
    input,
    output,
    template = 'report',
    theme = 'light',
    title,
    subtitle,
    author,
    date = new Date().toLocaleDateString('en-US', { 
      year: 'numeric', month: 'long', day: 'numeric' 
    }),
    outputHtml = false
  } = options;
  
  // Read input
  let markdown;
  if (fs.existsSync(input)) {
    markdown = fs.readFileSync(input, 'utf8');
  } else {
    markdown = input;
  }
  
  // Parse frontmatter
  const { meta, content } = parseFrontmatter(markdown);
  
  // Merge options (CLI overrides frontmatter)
  const data = {
    title: title || meta.title || 'Report',
    subtitle: subtitle || meta.subtitle || '',
    author: author || meta.author || '',
    date: date,
    content: markdownToHtml(content)
  };
  
  // Determine template and theme
  // Priority: CLI option > frontmatter > default
  // Note: CLI args are passed explicitly, so they should override frontmatter
  const templateName = template || meta.template || 'report';
  const themeName = theme || meta.theme || 'light';
  
  // Load and populate template
  const { template: tpl, styles } = loadTemplate(templateName, themeName);
  const html = populateTemplate(tpl, styles, data);
  
  // Determine output path
  const outputPath = output || input.replace(/\.md$/, '.pdf');
  
  // Optionally save HTML
  if (outputHtml) {
    const htmlOutputPath = outputPath.replace(/\.pdf$/, '.html');
    fs.writeFileSync(htmlOutputPath, html);
    console.log(`✓ HTML: ${htmlOutputPath}`);
  }
  
  // Generate PDF
  try {
    await generatePdfApi(html, outputPath);
  } catch (e) {
    generatePdfCurl(html, outputPath);
  }
  
  console.log(`✓ PDF: ${outputPath}`);
  return { html, pdf: outputPath };
}

// CLI
async function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('--help') || args.length === 0) {
    console.log(`
elegant-reports - Generate Nordic-style PDF reports

Usage:
  node generate.js <input.md> [output.pdf] [options]

Templates:
${Object.entries(TEMPLATES).map(([k, v]) => `  ${k.padEnd(14)} ${v.description}`).join('\n')}

Options:
  --template <name>   Template: ${Object.keys(TEMPLATES).join(', ')} (default: report)
  --theme <mode>      Theme: light, dark (default: light)
  --title <string>    Override document title
  --subtitle <string> Add subtitle
  --author <string>   Author name
  --date <string>     Override date
  --output-html       Also output HTML file
  --list              List available templates

Frontmatter:
  Add YAML frontmatter to your markdown:
  ---
  title: My Report
  subtitle: Analysis
  template: report
  theme: dark
  ---

Examples:
  node generate.js report.md
  node generate.js data.md output.pdf --template presentation
  node generate.js notes.md --template report --theme dark
`);
    process.exit(0);
  }
  
  if (args.includes('--list')) {
    console.log('\nAvailable templates:\n');
    Object.entries(TEMPLATES).forEach(([name, config]) => {
      console.log(`  ${name}`);
      console.log(`    ${config.description}`);
      console.log(`    Themes: ${Object.keys(config.themes).join(', ')}`);
      console.log();
    });
    process.exit(0);
  }
  
  // Parse arguments
  const input = args[0];
  let output = args[1]?.startsWith('--') ? undefined : args[1];
  
  const getArg = (flag) => {
    const idx = args.indexOf(flag);
    return idx !== -1 ? args[idx + 1] : undefined;
  };
  
  const options = {
    input,
    output,
    template: getArg('--template'),
    theme: getArg('--theme'),
    title: getArg('--title'),
    subtitle: getArg('--subtitle'),
    author: getArg('--author'),
    date: getArg('--date'),
    outputHtml: args.includes('--output-html')
  };
  
  try {
    await generateReport(options);
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

// Export for programmatic use
module.exports = { generateReport, TEMPLATES, loadTemplate, populateTemplate };

// Run CLI
if (require.main === module) {
  main();
}
