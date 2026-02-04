---
name: oft
description: "Generate 'Out for Today' standup messages for #ai-team Slack channel. Produce formatted OFT summaries from raw work context, agent session logs, or conversation history."
metadata: {"clawdbot":{"emoji":"📋"}}
---

# OFT — Out for Today Generator

Generate end-of-day standup messages formatted for Nutrient's #ai-team Slack channel.

## When to Use

When asked to write an OFT, "out for today", daily standup, or end-of-day summary.

## Format Rules

Follow this exact Slack formatting:

```
*Out For Today*
• [Main work item] — outcome/status. PR/link if applicable
    ◦ Sub-detail or finding
    ◦ Sub-detail or finding
• [Second work item] — what happened
• [Blocker or next step, if any]
```

### Style Guide (from real channel examples)

1. **Header**: `*Out For Today*` (bold, title case) — on its own line
2. **Top-level bullets**: `•` — one per major work stream or topic
3. **Sub-bullets**: `◦` indented with 4 spaces — for details, findings, sub-tasks
4. **Links**: Inline GitHub PRs as `[#50170](url)` or named links `[PR](url)`
5. **Slack thread refs**: Link to relevant Slack discussions when applicable
6. **Tone**: Concise, technical, signal-over-noise. Say what happened and why it matters.
7. **Group by project**: If working on multiple projects, use bold subheadings:
   ```
   *Out For Today*

   *Project Name*
       • Work item for this project
           ◦ Detail
       • Another item
   
   *Other Project*
       • Work item
   ```

### What Makes a Good OFT

- **Outcomes over activity** — "Merged PR for state machine with full test coverage" > "Worked on code"
- **Decisions and findings** — "GPT-5-mini gives best answers but Claude Haiku better at tool use"  
- **Blockers and dependencies** — "Waiting on X for review" or "Dropped Y because Z"
- **Links** — Always link PRs, issues, Slack threads, docs when relevant
- **In progress** — Mark clearly: "In progress — support tool approval flow"

### What to Avoid

- Vague activity logs ("Had meetings", "Did some work")
- Excessive detail on trivial tasks
- Missing context — assume the reader knows the projects but not your specific day

## Generating from Agent Sessions

When generating an OFT from conversation history or agent logs:

1. **Scan for concrete outputs**: PRs created/reviewed, issues resolved, analyses delivered, decisions made
2. **Extract key findings**: Data insights, technical discoveries, recommendations given
3. **Note collaborations**: Who you worked with, what was discussed
4. **Identify blockers**: What's waiting on someone else, what got dropped and why
5. **Prioritize**: Lead with the most impactful/interesting items

## Example Output

```
*Out For Today*
• Analyzed least-clicked Web SDK guides using GA4 data (last 12 months). Bottom 10 guides all ~70% below average pageviews. Full report shared in #clawdbots thread.
    ◦ Set up GA4 Data API access for future analytics queries
    ◦ Top guide (/viewer/) gets 60x more traffic than bottom guides
• Investigated Hotjar integration for click heatmaps
    ◦ No public API available — browser-only dashboard
    ◦ Heatmaps just set up today by Aish, need time to accumulate data
• Helped set up Nuri permissions for new team members in #clawdbots
```
