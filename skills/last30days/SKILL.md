---
name: last30days
description: Research what communities have been saying about a topic over the last 30 days across Reddit, X, Hacker News, Stack Overflow, Dev.to, and Lobsters. Use when the user wants recent sentiment, discussion themes, comparisons, or prompting techniques grounded in current community conversations.
---

# last30days - Community Research Skill

Research what people are saying about a topic across Reddit, X, Hacker News, and developer communities from the last 30 days.

## Description

Triggers on: "what's trending", "what are people saying about", "research", "last 30 days", "community sentiment", "what's new with", "recent discussions"

This skill searches multiple community platforms to surface real conversations, opinions, and sentiment about any topic. It combines engagement-weighted social signals with technical community discussions.

## Source Tiers

### Tier 1: High-Signal (Engagement-Weighted)
- **Reddit** — Via OpenAI API with web search (requires OPENAI_API_KEY)
- **X/Twitter** — Via xAI Grok API (requires XAI_API_KEY)  
- **Hacker News** — Free Algolia API, always available

### Tier 2: Developer Communities
- **Stack Overflow** — Free API, technical Q&A
- **Dev.to** — Free API, developer blog posts
- **Lobsters** — Free, curated tech discussions

### Tier 3: Web Fallback
- **General web search** — Via web_fetch tool

## Configuration

Credentials stored at: `~/.config/last30days/.env`

```bash
# Optional - enables Reddit search
OPENAI_API_KEY=sk-...

# Optional - enables X/Twitter search
XAI_API_KEY=xai-...

# HN, Stack Overflow, Dev.to, Lobsters need NO API keys
```

## Research Flow

### Step 1: Parse Intent

Extract from user query:
- **Topic**: Main subject to research
- **Query type**: general sentiment | tool comparison | "how to" | trending | prompting
- **Time range**: Default 30 days, can be adjusted

### Step 2: Search Tier 1 Sources (Parallel)

Run these in parallel using exec tool:

```bash
# Reddit + X (if API keys available)
cd ~/clawd-nuri-internal/skills/last30days
python3 scripts/last30days.py "TOPIC" --emit=json

# Hacker News (always available)
python3 scripts/hn_search.py "TOPIC" --days 30 --limit 30
```

### Step 3: Search Tier 2 Sources

```bash
cd ~/clawd-nuri-internal/skills/last30days
./scripts/community_search.sh "TOPIC" all
```

### Step 4: Web Fallback (if needed)

Use web_fetch for additional sources if Tier 1/2 results are sparse:
- Blog posts
- News articles
- Documentation
- Tutorial sites

### Step 5: Synthesize Results

Weight sources by engagement quality:

| Source | Weight | Reasoning |
|--------|--------|-----------|
| Reddit (high upvotes) | 1.0 | Strong community validation |
| X (high engagement) | 0.9 | Real-time pulse |
| Hacker News | 0.85 | Tech-savvy audience |
| Stack Overflow | 0.7 | Technical depth |
| Dev.to | 0.6 | Developer perspective |
| Lobsters | 0.6 | Curated tech |
| Web (general) | 0.4 | No engagement signal |

### Step 6: Present Findings

Structure output as:

```markdown
## Research: [TOPIC] (Last 30 Days)

### Key Themes
1. [Theme with source citations]
2. [Theme with source citations]

### Sentiment Summary
- Overall: [Positive/Neutral/Negative/Mixed]
- Common praise: [...]
- Common criticism: [...]

### Top Discussions

**Reddit** (X posts, Y total upvotes)
- [Title](url) — X upvotes, Y comments — key insight

**X/Twitter** (X posts)
- [Key tweet summary](url) — engagement stats

**Hacker News** (X posts, Y total points)
- [Title](url) — X points, Y comments — key insight

**Stack Overflow** (X questions)
- [Common problem pattern]

### Emerging Patterns
- [Pattern 1]
- [Pattern 2]
```

### Step 7: Generate Prompting Query (If Applicable)

If user asked about prompting/techniques, generate a copy-paste prompt:

```markdown
## Suggested Prompt (Copy-Paste Ready)

Based on community insights, here's an optimized prompt for [TOPIC]:

---
[Generated prompt incorporating community best practices]
---
```

## Example Usage

**User**: "What are people saying about Cursor IDE in the last 30 days?"

**Flow**:
1. Parse: topic="Cursor IDE", type="sentiment/opinions"
2. Run Reddit/X search (if keys available)
3. Run HN search: `python3 scripts/hn_search.py "Cursor IDE" --days 30`
4. Run community search: `./scripts/community_search.sh "Cursor IDE" all`
5. Synthesize across sources
6. Present with engagement stats

**User**: "Research Claude vs GPT-4 for coding"

**Flow**:
1. Parse: topic="Claude vs GPT-4 coding", type="comparison"
2. Search all sources
3. Weight comparative discussions higher
4. Present pros/cons from each platform

**User**: "What's the best way to prompt for code review?"

**Flow**:
1. Parse: topic="code review prompts", type="prompting/how-to"
2. Search all sources
3. Extract specific techniques mentioned
4. Generate optimized prompt from community insights

## Script Reference

### last30days.py (Reddit + X)
```bash
python3 scripts/last30days.py "topic" [options]

Options:
  --mock          Use fixtures (testing)
  --emit=MODE     compact|json|md|context|path
  --sources=MODE  auto|reddit|x|both
  --quick         Fewer results, faster
  --deep          More comprehensive
  --include-web   Add web search
```

### hn_search.py (Hacker News)
```bash
python3 scripts/hn_search.py "topic" [options]

Options:
  --days N        Days to look back (default: 30)
  --limit N       Max results (default: 50)
```

### community_search.sh (SO, Dev.to, Lobsters)
```bash
./scripts/community_search.sh "topic" [source]

Sources: stackoverflow, devto, lobsters, all
```

## Error Handling

- **No API keys**: Fall back to HN + Tier 2 sources (still useful!)
- **API errors**: Log error, continue with available sources
- **No results**: Suggest broader topic or different time range
- **Rate limits**: Wait and retry, or use cached results

## Notes

- HN, SO, Dev.to, Lobsters are FREE and always available
- Even without OpenAI/xAI keys, this skill provides valuable research
- Reddit/X add engagement weighting that improves signal quality
- Always cite sources with links for user verification
