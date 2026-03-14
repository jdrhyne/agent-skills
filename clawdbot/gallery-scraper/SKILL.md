---
name: gallery-scraper
description: Bulk download images from login-protected gallery websites using browser automation. Use when asked to scrape, download, or save images from gallery pages that require authentication, extract full-size images from thumbnails, or batch download from multi-page galleries.
---

# Gallery Scraper

Bulk download images from authenticated gallery websites via browser relay.

## Prerequisites

- User must have Chrome with OpenClaw Browser Relay extension
- User must be logged into the target site
- User must attach the browser tab (click relay toolbar button, badge ON)

## Workflow

### 1. Attach Browser Tab

Ask user to:
1. Log into the gallery site in Chrome
2. Navigate to the target gallery/profile page
3. Click the OpenClaw Browser Relay toolbar button (badge shows ON)

### 2. Discover Image URL Pattern

Most gallery sites store full-size URLs in data attributes. Common patterns:

```javascript
// Extract via browser evaluate
() => {
  // Try common patterns
  const patterns = [
    'img[data-max]',           // data-max attribute
    'img[data-src]',           // lazy-load pattern
    'img[data-full]',          // full-size pattern
    'a[data-lightbox] img',    // lightbox galleries
    '.gallery-item img'        // generic gallery
  ];
  
  for (const sel of patterns) {
    const imgs = document.querySelectorAll(sel);
    if (imgs.length > 0) {
      return {
        selector: sel,
        count: imgs.length,
        sample: imgs[0].outerHTML.substring(0, 200)
      };
    }
  }
  return null;
}
```

### 3. Extract Full-Size URLs

Once pattern identified, extract all URLs:

```javascript
// For data-max pattern (common)
() => Array.from(document.querySelectorAll('img[data-max]'))
  .map(img => img.dataset.max)

// For thumbnail→full conversion (replace path segment)
() => Array.from(document.querySelectorAll('.gallery img'))
  .map(img => img.src.replace('/thumb/', '/full/'))
```

### 4. Handle Pagination

Check for multiple pages:

```javascript
() => {
  const pagination = document.querySelectorAll('.pagination a, [class*="page"] a');
  return Array.from(pagination).map(a => ({text: a.textContent, href: a.href}));
}
```

Navigate to each page and collect URLs.

### 4b. Batch scrape multiple galleries (iframe trick)

When you need multiple galleries quickly and can’t automate CDP, you can load each gallery in a hidden iframe and extract `data-max` URLs:

```javascript
async () => {
  const urls = [
    'https://site.example/galleries/view/123',
    'https://site.example/galleries/view/456'
  ];
  const results = [];
  for (const url of urls) {
    const iframe = document.createElement('iframe');
    iframe.style.position = 'fixed';
    iframe.style.left = '-9999px';
    iframe.style.width = '800px';
    iframe.style.height = '600px';
    iframe.src = url;
    document.body.appendChild(iframe);
    await new Promise((resolve, reject) => {
      const t = setTimeout(() => reject(new Error('timeout load')), 20000);
      iframe.onload = () => { clearTimeout(t); resolve(); };
    });
    const doc = iframe.contentDocument;
    const start = Date.now();
    let imgs = [];
    while (Date.now() - start < 20000) {
      imgs = Array.from(doc.querySelectorAll('img[data-max]')).map(i => i.dataset.max);
      if (imgs.length) break;
      await new Promise(r => setTimeout(r, 500));
    }
    results.push({ id: url.split('/').pop(), urls: imgs });
    iframe.remove();
  }
  return results;
}
```

### 5. Check CDN Access

Test if CDN requires authentication or just Referer:

```bash
# Test direct access
curl -I "CDN_URL" 2>/dev/null | head -3

# Test with Referer
curl -I -H "Referer: https://SITE_DOMAIN/" "CDN_URL" 2>/dev/null | head -3
```

### 6. Bulk Download

Save URLs to file, then parallel download:

```bash
# Create output directory
mkdir -p ~/Downloads/gallery_name

# Download with Referer header (parallel)
cd ~/Downloads/gallery_name
while IFS= read -r url; do
  filename=$(basename "$url")
  curl -s -H "Referer: https://SITE_DOMAIN/" -o "$filename" "$url" &
  [ $(jobs -r | wc -l) -ge 8 ] && wait -n
done < urls.txt
wait
```

**Python ThreadPool fallback (avoids shell quoting + wait -n issues):**

```python
import os
import requests
from concurrent.futures import ThreadPoolExecutor

outdir = os.path.expanduser('~/Downloads/gallery_name')
os.makedirs(outdir, exist_ok=True)
headers = {'Referer': 'https://SITE_DOMAIN/', 'User-Agent': 'Mozilla/5.0'}

with open('urls.txt') as f:
    urls = [line.strip() for line in f if line.strip()]

def download(url):
    filename = os.path.join(outdir, os.path.basename(url))
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        return
    r = requests.get(url, headers=headers, timeout=60)
    r.raise_for_status()
    with open(filename, 'wb') as f:
        f.write(r.content)

with ThreadPoolExecutor(max_workers=8) as ex:
    for url in urls:
        ex.submit(download, url)
```

## Handling Lock Buttons

Some galleries have "lock" buttons to reveal hidden content. Look for:

```javascript
// Find lock/unlock buttons
() => {
  const locks = document.querySelectorAll(
    '[class*="lock"], [class*="unlock"], ' +
    'button[title*="lock"], .premium-unlock'
  );
  return Array.from(locks).map(el => ({
    tag: el.tagName,
    class: el.className,
    text: el.innerText?.substring(0, 30)
  }));
}
```

Click each lock button before extracting URLs.

## Output Organization

Optionally organize by gallery:

```bash
# Extract gallery ID from URL
gallery_id=$(echo "$url" | grep -oE 'gallery/[0-9]+' | cut -d/ -f2)
mkdir -p "gallery_${gallery_id}"
```

## Troubleshooting

- **403 Forbidden**: Add Referer header or extract cookies from browser
- **Rate limited**: Reduce parallel downloads, add delays
- **Missing images**: Check for JavaScript-loaded content, may need scroll injection
- **Login required for CDN**: Extract session cookies via `document.cookie`
