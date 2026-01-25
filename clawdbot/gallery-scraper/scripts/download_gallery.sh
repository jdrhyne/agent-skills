#!/bin/bash
# Gallery bulk downloader with Referer support
# Usage: ./download_gallery.sh <urls_file> <output_dir> <referer_domain>
#
# Example:
#   ./download_gallery.sh urls.txt ~/Downloads/my_gallery "https://example.com/"

set -e

URLS_FILE="${1:?Usage: $0 <urls_file> <output_dir> <referer_domain>}"
OUTPUT_DIR="${2:?Missing output directory}"
REFERER="${3:?Missing referer domain (e.g., https://example.com/)}"
PARALLEL="${4:-8}"  # Default 8 parallel downloads

# Validate inputs
if [ ! -f "$URLS_FILE" ]; then
    echo "Error: URLs file not found: $URLS_FILE"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# Count URLs
TOTAL=$(wc -l < "$URLS_FILE" | tr -d ' ')
echo "Downloading $TOTAL images to $OUTPUT_DIR"
echo "Referer: $REFERER"
echo "Parallel downloads: $PARALLEL"
echo ""

# Download with progress
COUNT=0
while IFS= read -r url || [ -n "$url" ]; do
    [ -z "$url" ] && continue
    
    filename=$(basename "$url" | cut -d'?' -f1)  # Remove query params
    
    # Skip if already downloaded
    if [ -f "$filename" ]; then
        echo "Skip (exists): $filename"
        continue
    fi
    
    curl -s -H "Referer: $REFERER" -o "$filename" "$url" &
    COUNT=$((COUNT + 1))
    
    # Progress every 10 files
    if [ $((COUNT % 10)) -eq 0 ]; then
        echo "Progress: $COUNT / $TOTAL"
    fi
    
    # Limit parallel downloads
    while [ $(jobs -r | wc -l) -ge "$PARALLEL" ]; do
        wait -n 2>/dev/null || true
    done
done < "$URLS_FILE"

# Wait for remaining downloads
wait

# Summary
DOWNLOADED=$(ls -1 2>/dev/null | wc -l | tr -d ' ')
SIZE=$(du -sh . 2>/dev/null | cut -f1)
echo ""
echo "=== Complete ==="
echo "Files: $DOWNLOADED"
echo "Size: $SIZE"
echo "Location: $OUTPUT_DIR"
