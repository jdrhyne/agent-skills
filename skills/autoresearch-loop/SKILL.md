---
name: autoresearch-loop
description: "Domain-agnostic metric-driven improvement loop, generalizing Karpathy's autoresearch. Use when you want an agent to discover what to measure for a project/goal, then run a keep-or-revert experiment loop that proposes changes, measures them against an objective, keeps wins, discards regressions, and records implemented improvements. Adapts to code perf-auditing, codegen, bug-finding, ad optimization, or any artifact + measurable objective + trial. Trigger: 'autoresearch this', 'find and implement improvements to X', 'discover metrics and optimize'."
---

# autoresearch-loop

Generalize Karpathy's autoresearch into a domain-adaptive improvement loop. The agent **discovers what to measure**, then runs a disciplined **propose → trial → keep-or-revert** loop, maintaining an explicit ledger of what was tried, kept, discarded, and implemented.

Read `DESIGN.md` once at the start of a run for the full architecture and the domain-specific tensions (metric latency/noise/cost, Goodhart gaming, cost-per-trial, reversibility). The phases below are the operating procedure.

**Runtime:** the loop's mechanics (run a trial, parse the metric, score confidence, keep/commit or discard/revert) are handled by the `arl` CLI over a `.auto/` session folder — a Claude-native port of pi-autoresearch's tools. Read `references/runtime-contract.md` for the `.auto/` layout, the `METRIC name=value` contract, MAD confidence scoring, and the `arl init|run|log|status` commands. Invoke it as `node scripts/arl.mjs <cmd>` (or `arl` if on PATH).

## When NOT to run
- There is no metric that can be measured **repeatably and cheaply enough** within a trial budget. A loop with no trustworthy metric chases noise — stop and say so.
- The change surface is irreversible or unsafe to mutate experimentally (production data, customer-facing irreversible actions) without an explicit revert procedure in the adapter.

## Phase 0 — FRAME (metric discovery)

Given `{project, goal, context}` — follow the procedure in `references/metric-discovery.md` (restate the goal as an outcome → enumerate candidates on the proxy→outcome spectrum → score on six axes → choose primary + guardrails + strategy → red-team for gaming). In brief:
1. Identify or select a **domain adapter** (`adapters/*.md`). If none fits, draft an inline adapter following `references/domain-adapter-contract.md`.
2. Propose **candidate metrics** (the adapter's menu is a *prior*, not the answer — reason from the goal). Score each on measurability, latency, noise, alignment, gameability, and cost. Prefer alignment over convenience for the primary.
3. Pick ONE **primary objective**, a set of **guardrail metrics** that must not regress, a **trial budget** (wall-clock and/or cost per trial), and a **stop condition** (budget exhausted, plateau over K trials, or target hit).
4. Choose the **accept/reject strategy** for this domain: `deterministic-delta` (fast, low-noise), `significance-test`, or `bandit` (noisy/delayed/expensive — e.g. ads).
5. Name the **Goodhart guards** (guardrail metrics, holdout, periodic critic).
6. Write `runs/<id>/CHARTER.md`. Confirm it with the user before spending real budget if trials cost money or touch production.

## Phase 1 — BASELINE
Write `.auto/measure.sh` (and `.auto/checks.sh` if guardrails require it). `arl init` with the primary metric + direction, run the baseline (`arl run`), and record it (`arl log --status keep --metric <baseline> --desc baseline`). If the baseline can't be measured cleanly and repeatably, stop (see "When NOT to run").

**Before proposing any change, profile where the cost actually is, and confirm the benchmark stresses the IN-SCOPE artifact — not a dependency, a native/FFI call, an external engine, the network, or unrelated code.** (Validated the hard way on two live runs: once the assumed hot path was wrong twice and 97% of time was in an out-of-scope library; once the in-scope managed code was only 0.4–3.8% of wall-time because a Rust NIF dominated — the correct loop output there was a *true negative*, "re-scope," not a sub-noise edit. See `adapters/code-perf-audit.md` → Pitfalls.) Spend one profiling run on the managed-vs-native/dependency split; a loop that optimizes code which isn't the bottleneck produces confident, useless churn — and proving "no in-scope headroom" cheaply is itself a successful outcome.

## Phase 2 — LOOP (until stop condition)
Each iteration:
1. Read the artifact, `.auto/prompt.md`, the `.auto/log.jsonl` tail, and `.auto/ideas.md` — never re-propose an exhausted line.
2. Propose **one** hypothesis: the smallest change most likely to move the primary metric. Pull from `.auto/ideas.md`; append newly-imagined ideas there.
3. Apply it directly to the in-scope files (a discard reverts code via git; `.auto/` is preserved).
4. `arl run` — runs the trial harness, parses `METRIC` lines, runs guardrail `checks.sh`.
5. **Decide** with the charter's accept/reject strategy. For `fast-low-noise` domains, watch the MAD confidence score (`<1.0×` = within noise, re-run before trusting). For `delayed-expensive` domains (ads), do NOT trust a single trial — reach the adapter's minimum sample and use significance/bandit logic. A primary win that regresses any guardrail is a **discard**.
6. `arl log --status keep|discard|... --metric <value> --desc "..." --asi <learning>`. Keep auto-commits and advances the baseline; discard auto-reverts the code. Record cost with `--cost`.
7. Annotate every run's `--asi` with what was *learned* (survives a discard's revert); prune exhausted ideas.

Respect concurrency reality: deterministic domains can run many fast sequential trials; noisy/delayed domains (ads) run few long concurrent trials and must reach a minimum sample before any verdict.

## Phase 3 — ADAPT (every N trials)
- Prune dead-end hypothesis families.
- Re-tune the trial budget (raise if trials are cheap and informative; lower if wasteful).
- **Goodhart check:** inspect recent keeps — is the metric genuinely better, or gamed (tests deleted, benchmark special-cased, holdout diverging from training metric, downstream conversion dropping while CTR rises)? If gamed, tighten guardrails or refine the metric, and revert the gamed keep.
- **Proxy-degeneracy check:** if a cheap proxy metric can be *structurally degenerate* for some task shapes (e.g. a routing score that is always 0 when landing == target), it will under-measure or mislead — and it can "pass" real defects a behavioral check would catch. When a cheap and a behavioral oracle both exist, iterate on the cheap one but **decide keeps with the behavioral oracle**. Validated on a real run where the content score read a genuine fix as +2.15 while the browser-flow oracle measured +28.68 and also caught three broken links the content score missed. See `adapters/web-onboarding.md`.

## Output
At any stop, report (`arl status` summarizes most of it): metric baseline → current with the delta and confidence, the kept improvements (each with its delta and cost), what was tried and discarded with the `--asi` reasons from `.auto/log.jsonl`, the remaining promising ideas, and total cost. The durable record is `.auto/` plus the git history of kept commits.

## Reference files
- `DESIGN.md` — architecture, per-domain design tensions, and the pi-autoresearch prior-art decision (read once per run).
- `references/metric-discovery.md` — the Phase 0 procedure: deriving + scoring + red-teaming the metric.
- `references/runtime-contract.md` — the `.auto/` layout, `METRIC` contract, MAD confidence, and `arl` commands.
- `references/domain-adapter-contract.md` — how to define a new domain adapter.
- `references/journal-schema.md` — the ledger record formats.
- `adapters/*.md` — concrete domain adapters (code-perf-audit, bug-finding, code-generation, google-ads, web-onboarding).
