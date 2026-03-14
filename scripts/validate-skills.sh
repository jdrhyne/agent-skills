#!/bin/bash
#
# validate-skills.sh
# Validates all SKILL.md files across skills/, clawdbot/, codex/, prompts/
#

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_DIRS=("skills" "clawdbot" "codex" "prompts")

errors=0
warnings=0

echo "Validating SKILL.md files"
echo "================================"

for rel in "${TARGET_DIRS[@]}"; do
  BASE_DIR="$REPO_ROOT/$rel"
  [ -d "$BASE_DIR" ] || continue

  echo ""
  echo "Directory: $BASE_DIR"

  for skill_dir in "$BASE_DIR"/*/; do
    [ -d "$skill_dir" ] || continue

    skill_name="$(basename "$skill_dir")"
    skill_md="$skill_dir/SKILL.md"

    echo ""
    echo "Checking: $rel/$skill_name"

    # Check SKILL.md exists
    if [ ! -f "$skill_md" ]; then
      echo "  ✗ ERROR: Missing SKILL.md"
      ((errors++))
      continue
    fi

    # Check frontmatter exists
    if ! head -1 "$skill_md" | grep -q "^---$"; then
      echo "  ✗ ERROR: Missing frontmatter (should start with ---)"
      ((errors++))
      continue
    fi

    # Check name field
    if ! grep -q "^name:" "$skill_md"; then
      echo "  ⚠ WARNING: Missing 'name:' in frontmatter"
      ((warnings++))
    else
      echo "  ✓ Has name field"
    fi

    # Check description field
    if ! grep -q "^description:" "$skill_md"; then
      echo "  ⚠ WARNING: Missing 'description:' in frontmatter"
      ((warnings++))
    else
      echo "  ✓ Has description field"
    fi

    # Check closing frontmatter
    if ! awk '/^---$/{count++} count==2{found=1; exit} END{exit !found}' "$skill_md"; then
      echo "  ✗ ERROR: Frontmatter not closed (missing second ---)"
      ((errors++))
    else
      echo "  ✓ Frontmatter properly closed"
    fi
  done
done

echo ""
echo "================================"
echo "Results: $errors errors, $warnings warnings"

if [ $errors -gt 0 ]; then
  exit 1
fi
