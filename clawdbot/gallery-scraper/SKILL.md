---
name: gallery-scraper
description: Bulk download images from login-protected gallery websites using browser automation. Use when asked to scrape, download, or save images from gallery pages that require authentication, extract full-size images from thumbnails, or batch download from multi-page galleries.
---

# Gallery Scraper

Bulk download images from authenticated gallery websites via browser relay.

## Prerequisites

- User must have Chrome with Clawdbot Browser Relay extension
- User must be logged into the target site
- User must attach the browser tab (click relay toolbar button, badge ON)

## Workflow

### 1. Attach Browser Tab

Ask user to:
1. Log into the gallery site in Chrome
2. Navigate to the target gallery/profile page
3. Click the Clawdbot Browser Relay toolbar button (badge shows ON)

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
