#!/usr/bin/env node
const { TEMPLATES, loadTemplate, populateTemplate } = require('../generate.js');

const rendered = [];
for (const [name, config] of Object.entries(TEMPLATES)) {
  for (const theme of Object.keys(config.themes)) {
    const { template, styles } = loadTemplate(name, theme);
    const html = populateTemplate(template, styles, {
      title: 'Smoke Test Title',
      subtitle: 'Smoke Test Subtitle',
      author: 'CI',
      date: '2026-03-26',
      content: '<p>Smoke test body</p>'
    });

    if (!html.includes('Smoke Test Title')) {
      throw new Error(`Template ${name}/${theme} did not render title`);
    }
    if (!html.toLowerCase().includes('<html') || !html.toLowerCase().includes('</html>')) {
      throw new Error(`Template ${name}/${theme} did not render a full HTML document`);
    }
    if (html.includes('{{title}}') || html.includes('{{styles}}')) {
      throw new Error(`Template ${name}/${theme} left core placeholders unreplaced`);
    }
    rendered.push(`${name}:${theme}`);
  }
}

console.log(`Smoke test passed for ${rendered.length} template/theme combinations.`);
console.log(rendered.join('\n'));
