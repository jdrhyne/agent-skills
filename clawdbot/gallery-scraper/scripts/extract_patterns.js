/**
 * Gallery URL Extraction Patterns
 * Run in browser console or via browser automation evaluate
 * 
 * Usage: Copy the appropriate function and run via browser.act evaluate
 */

// Auto-detect gallery pattern
function detectGalleryPattern() {
  const patterns = [
    { name: 'data-max', selector: 'img[data-max]', attr: 'data-max' },
    { name: 'data-src', selector: 'img[data-src]', attr: 'data-src' },
    { name: 'data-full', selector: 'img[data-full]', attr: 'data-full' },
    { name: 'data-original', selector: 'img[data-original]', attr: 'data-original' },
    { name: 'data-lazy', selector: 'img[data-lazy-src]', attr: 'data-lazy-src' },
    { name: 'srcset', selector: 'img[srcset]', attr: 'srcset' },
    { name: 'lightbox', selector: 'a[data-lightbox] img', attr: 'src' },
    { name: 'gallery-item', selector: '.gallery-item img, .photo-item img', attr: 'src' },
  ];

  for (const p of patterns) {
    const els = document.querySelectorAll(p.selector);
    if (els.length > 0) {
      const sample = els[0];
      return {
        pattern: p.name,
        selector: p.selector,
        attribute: p.attr,
        count: els.length,
        sampleUrl: sample.getAttribute(p.attr) || sample.src,
        sampleHtml: sample.outerHTML.substring(0, 300)
      };
    }
  }
  
  // Fallback: all images
  const allImgs = document.querySelectorAll('img');
  return {
    pattern: 'fallback',
    selector: 'img',
    attribute: 'src',
    count: allImgs.length,
    note: 'No specific pattern found, using all images'
  };
}

// Extract URLs using detected pattern
function extractUrls(selector, attribute) {
  return Array.from(document.querySelectorAll(selector))
    .map(el => el.getAttribute(attribute) || el.src)
    .filter(url => url && url.startsWith('http'));
}

// Extract with thumbnail→full conversion
function extractWithConversion(selector, thumbPath, fullPath) {
  return Array.from(document.querySelectorAll(selector))
    .map(el => (el.src || el.getAttribute('data-src') || '').replace(thumbPath, fullPath))
    .filter(url => url && url.startsWith('http'));
}

// Find pagination links
function findPagination() {
  const selectors = [
    '.pagination a',
    '.pager a', 
    '[class*="page-"] a',
    'a[href*="page="]',
    'a[href*="_page="]',
    '.page-numbers a'
  ];
  
  const links = [];
  for (const sel of selectors) {
    const els = document.querySelectorAll(sel);
    if (els.length > 0) {
      els.forEach(el => {
        links.push({ text: el.textContent.trim(), href: el.href });
      });
      return { selector: sel, links };
    }
  }
  return { selector: null, links: [] };
}

// Find gallery/album links on a profile page
function findGalleryLinks() {
  const selectors = [
    'a[href*="/gallery/"]',
    'a[href*="/album/"]',
    'a[href*="/galleries/"]',
    '.gallery-link',
    '.album-link'
  ];
  
  for (const sel of selectors) {
    const els = document.querySelectorAll(sel);
    if (els.length > 0) {
      return {
        selector: sel,
        count: els.length,
        urls: [...new Set(Array.from(els).map(a => a.href))]
      };
    }
  }
  return { selector: null, count: 0, urls: [] };
}

// Export for use
if (typeof module !== 'undefined') {
  module.exports = {
    detectGalleryPattern,
    extractUrls,
    extractWithConversion,
    findPagination,
    findGalleryLinks
  };
}
