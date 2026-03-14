#!/bin/bash
#
# update-readme.sh
# Regenerates the trust badge block and skill tables in README.md.
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
README="$REPO_ROOT/README.md"

MODE="write"
if [[ "${1:-}" == "--check" ]]; then
  MODE="check"
fi

encode_url() {
  python3 - "$1" <<'PY'
import sys
from urllib.parse import quote

print(quote(sys.argv[1], safe=""))
PY
}

existing_badge_version() {
  sed -n 's/.*[?&]v=\([^"&]*\).*/\1/p' "$README" | head -1
}

BADGE_VERSION="${BADGE_VERSION:-$(existing_badge_version)}"
BADGE_VERSION="${BADGE_VERSION:-$(date -u +%Y%m%d-%H%M%S)}"

extract_description() {
  skill_md="$1"

  python3 - "$skill_md" <<'PY'
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text()
lines = text.splitlines()

if not lines or lines[0].strip() != "---":
    print("")
    raise SystemExit(0)

frontmatter = []
for line in lines[1:]:
    if line.strip() == "---":
        break
    frontmatter.append(line.rstrip("\n"))

description = ""
i = 0
while i < len(frontmatter):
    line = frontmatter[i]
    if not line.startswith("description:"):
        i += 1
        continue

    value = line.split(":", 1)[1].strip()
    if not value or value[0] in ">|":
        parts = []
        i += 1
        while i < len(frontmatter):
            next_line = frontmatter[i]
            if re.match(r"^[A-Za-z0-9_-]+:", next_line):
                break
            if next_line.strip():
                parts.append(next_line.strip())
            i += 1
        description = " ".join(parts)
    else:
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        description = value
    break

description = re.sub(r"\s+", " ", description).strip()
description = description.replace("|", "&#124;")
print(description)
PY
}

badge_image_url() {
  target="$1"
  slug="${target//\//--}"
  json_url="https://jdrhyne.github.io/agent-skills/skills/${slug}.json"

  printf 'https://img.shields.io/endpoint?url=%s&label=&style=for-the-badge&v=%s' \
    "$(encode_url "$json_url")" \
    "$BADGE_VERSION"
}

repo_badge_url() {
  json_url="https://jdrhyne.github.io/agent-skills/repo-certified-pct.json"

  printf 'https://img.shields.io/endpoint?url=%s&cacheSeconds=300&style=for-the-badge&v=%s' \
    "$(encode_url "$json_url")" \
    "$BADGE_VERSION"
}

generate_trust_block() {
  cat <<EOF
<a href="https://agentverus.ai"><img src="$(repo_badge_url)" height="36"></a>

> Every skill in this repo is scanned by [**AgentVerus**](https://agentverus.ai) — an open-source security scanner that detects prompt injection, data exfiltration, and hidden threats in AI agent skill files. Live results are published from the latest scan run. [View full results →](https://jdrhyne.github.io/agent-skills/skills/index.json)
EOF
}

generate_table() {
  base_dir="$1"
  label="$2"

  cat <<EOF
| ${label} | Trust &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Description |
|-------|-------|-------------|
EOF

  for skill_dir in "$REPO_ROOT/$base_dir"/*/; do
    [ -d "$skill_dir" ] || continue
    [ -f "$skill_dir/SKILL.md" ] || continue

    entry_name="$(basename "$skill_dir")"

    target="$base_dir/$entry_name/SKILL.md"
    link="$base_dir/$entry_name/"
    description="$(extract_description "$skill_dir/SKILL.md")"
    description="${description:-No description provided.}"
    if [[ "$description" == *". "* ]]; then
      description="${description%%. *}."
    fi
    if [ "${#description}" -gt 140 ]; then
      description="${description:0:137}..."
    fi

    printf '| [`%s`](%s) | <img src="%s" width="200"> | %s |\n' \
      "$entry_name" \
      "$link" \
      "$(badge_image_url "$target")" \
      "$description"
  done
}

render_readme() {
  generated=0
  skip=0
  end_marker=""

  while IFS= read -r line; do
    case "$line" in
      "<!-- GENERATED_TRUST_BADGE_START -->")
        generated=$((generated + 1))
        echo "$line"
        generate_trust_block
        skip=1
        end_marker="<!-- GENERATED_TRUST_BADGE_END -->"
        continue
        ;;
      "<!-- GENERATED_SKILLS_TABLE_START -->")
        generated=$((generated + 1))
        echo "$line"
        generate_table "skills" "Skill"
        skip=1
        end_marker="<!-- GENERATED_SKILLS_TABLE_END -->"
        continue
        ;;
      "<!-- GENERATED_PROMPTS_TABLE_START -->")
        generated=$((generated + 1))
        echo "$line"
        generate_table "prompts" "Prompt"
        skip=1
        end_marker="<!-- GENERATED_PROMPTS_TABLE_END -->"
        continue
        ;;
      "<!-- GENERATED_CLAWDBOT_TABLE_START -->")
        generated=$((generated + 1))
        echo "$line"
        generate_table "clawdbot" "Skill"
        skip=1
        end_marker="<!-- GENERATED_CLAWDBOT_TABLE_END -->"
        continue
        ;;
      "<!-- GENERATED_CODEX_TABLE_START -->")
        generated=$((generated + 1))
        echo "$line"
        generate_table "codex" "Skill"
        skip=1
        end_marker="<!-- GENERATED_CODEX_TABLE_END -->"
        continue
        ;;
    esac

    if [ "$skip" -eq 1 ]; then
      if [ "$line" = "$end_marker" ]; then
        echo "$line"
        skip=0
        end_marker=""
      fi
      continue
    fi

    echo "$line"
  done < "$README"

  if [ "$generated" -lt 5 ]; then
    echo "Expected generated README markers were not found." >&2
    exit 1
  fi
}

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

render_readme > "$tmp_file"

if [ "$MODE" = "check" ]; then
  if ! cmp -s "$README" "$tmp_file"; then
    echo "README.md is out of date. Run scripts/update-readme.sh" >&2
    git --no-pager diff --no-index -- "$README" "$tmp_file" || true
    exit 1
  fi

  echo "README.md is up to date"
  exit 0
fi

mv "$tmp_file" "$README"
trap - EXIT

echo "✓ Updated README.md with generated trust sections (badge version: $BADGE_VERSION)"
