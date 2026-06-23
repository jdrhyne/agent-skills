# Adapter: google-ads

The hard case that proves the loop generalizes past Karpathy's fast, deterministic, free metric. Ad trials are **delayed, noisy, and cost real money** — naive keep-if-better chases noise and burns budget.

- **name:** google-ads
- **when-to-use:** optimizing a Google Ads account/campaign toward a business objective (lower CPA, higher ROAS, more qualified leads).
- **artifact:** the named campaign's mutable levers — keywords, negative keywords, bids/bid strategy, ad copy/assets, audiences, budgets. OFF-limits: account-level billing, conversion-tracking config (changing how the metric is measured mid-run invalidates comparisons), anything touching the attribution pipeline.
- **candidate-metrics:**
  - CPA (cost per acquisition) — measured via the attribution-aware conversion query over a window; lower better; **delayed-expensive**.
  - ROAS (revenue / spend) — same source; higher better; **delayed-expensive**.
  - Qualified-lead rate (Lead→Opp, not raw form-fills) — guards against optimizing junk leads; **delayed-expensive**. (The Nutrient project's attribution leak lives exactly here — GCLID dropping Lead→Opp; prefer a metric measured as close to revenue as attribution allows.)
- **guardrails:** spend ≤ daily/period cap; minimum conversion volume reached before any verdict (no calling a winner on 3 conversions); downstream qualified-lead rate not regressed while a top-of-funnel metric (CTR/CPC) improves (Goodhart: clickbait lifts CTR, kills quality).
- **trial-harness:** apply the change to ONE campaign (or one arm of an experiment/draft); let it run a **minimum window** (days, until volume + significance gate met); pull metrics from the measurement query, NOT the Ads UI's last-click default. Prefer Google Ads **experiments/drafts** so a control arm runs concurrently.
- **accept-reject:** `significance-test` or `bandit` — never deterministic-delta. Require a minimum sample (conversions, not clicks) and a confidence threshold before keep/discard; otherwise `inconclusive` → keep running. Account for seasonality by comparing against a concurrent control, not last week.
- **revert:** restore the prior campaign state from the pre-trial snapshot. Caveat: bid-strategy changes trigger a **learning phase** — reverting isn't instantaneous; the algorithm re-learns. Budget for this; don't thrash bid strategies.
- **goodhart-guards:** holdout = the concurrent control arm; the Phase-3 critic checks that primary-metric wins are matched by stable-or-better **downstream** quality (qualified leads / revenue), not just cheaper clicks.
- **trial-budget-default:** one change per campaign at a time; trial window = max(7 days, time-to-minimum-volume); few concurrent trials, not hundreds. Cost unit = ad-spend dollars + tokens.

## Why this can't be Karpathy's naive loop
Karpathy gets ~100 trials/night because his metric is instant, deterministic, and free. Here a single trial takes a week and costs money, the metric is noisy and attribution-lossy, and "revert" has hysteresis. The loop's *structure* (propose → trial → keep/revert → ledger) holds; its *statistics, concurrency, and budget* are completely different — which is exactly what the adapter layer exists to absorb.
