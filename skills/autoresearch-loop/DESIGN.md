# autoresearch-loop — Design

A domain-agnostic generalization of Andrej Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) loop: point an agent at a goal, have it *discover* what to measure, then run a keep-or-revert improvement loop that adapts its statistics and guardrails to the domain — code generation, performance auditing, bug finding, ad optimization, or anything else reducible to an artifact + a measurable objective + a trial.

## What Karpathy's autoresearch is (the seed)

`karpathy/autoresearch` (released 2026-03-07): `program.md` instructs an agent; the agent edits `train.py` (mutable artifact), runs a **5-minute** training trial, reads `val_bpb` (validation bits per byte; lower is better), **keeps the change if the metric improved, reverts if not, and repeats** (~12 trials/hr, ~100/night). `prepare.py` stays fixed. Tracking is implicit in git.

Three things are hardcoded there that we must make first-class and pluggable:

1. **The metric is hand-chosen** (`val_bpb`). We add a **metric-discovery** phase that proposes candidate metrics from a project/goal/context.
2. **The artifact + trial harness are ML-specific** (`train.py`, a GPU run). We add a **domain-adapter contract** so the same loop drives code, audits, bug hunts, or ad campaigns.
3. **Keep/revert is implicit and assumes a fast, low-noise, deterministic metric.** We add an explicit **ledger** and make the **accept/reject statistics adapt to the domain** (instant deterministic metric vs. noisy, delayed, expensive metric).

## Core abstraction: the AutoResearch Triple (+1)

Every domain instance is defined by:

- **Artifact** — the mutable thing a hypothesis edits (a hot module, a codegen prompt, a fuzz target, a campaign's keywords/bids/copy).
- **Objective** — one primary scalar metric with a known "better" direction, plus **guardrail metrics** that must not regress. Must be measurable repeatably within a trial budget.
- **Trial harness** — a procedure that applies a candidate change and returns the metric(s): a benchmark run, a test-suite pass-rate, an adversarial-verification pass, a measurement query over an ads window.
- **(+1) Metric discovery** — the meta-step Karpathy skips: given `{project, goal, context}`, propose candidate objectives, how to measure each, the trial budget, and the guardrails. Output is a **CHARTER**.

## The loop (generalized)

```
Phase 0 — FRAME (metric discovery)
  Read project/goal/context → propose candidate metrics → pick a primary
  objective, guardrail metrics, trial budget, and a stop condition.
  Write CHARTER.md. (This is the step that makes it adapt to a new domain.)

Phase 1 — BASELINE
  Measure the current metric(s) with the trial harness. Record in the ledger
  as experiment 0. If the metric can't be measured cheaply and repeatably,
  STOP and report — a loop with no trustworthy metric is worse than no loop.

Phase 2 — LOOP (until stop condition: budget, plateau, or target hit)
  a. Read the artifact + the ledger (what's been tried, what's exhausted).
  b. Propose ONE targeted hypothesis — the smallest change most likely to
     move the primary metric, drawn from a maintained backlog.
  c. Apply it on a throwaway snapshot (git branch / config copy).
  d. Run the trial harness within the time budget → extract metric(s).
  e. DECIDE with domain-appropriate statistics (see "Accept/reject" below),
     subject to guardrails (never accept a primary win that regresses a guardrail).
  f. KEEP → advance baseline, append to IMPLEMENTED.md.
     DISCARD → revert, record why (so the line isn't retried).
  g. Append the trial to JOURNAL; prune exhausted hypothesis families.

Phase 3 — ADAPT (periodic meta-review, every N trials)
  Review the journal: kill dead-end hypothesis families, raise/lower the trial
  budget, and run the Goodhart check — is the metric being gamed rather than
  genuinely improved? If so, tighten guardrails or refine the metric.
```

## What must adapt per domain (the hard parts)

These are the reasons this is not just "run Karpathy's loop on other stuff." Each domain adapter must declare how it handles them.

### 1. Metric latency, noise, and cost differ by orders of magnitude
- **Code perf / codegen / bug-finding:** the metric is fast (seconds–minutes), near-deterministic, and cheap → Karpathy's naive "keep if better" is fine, run many trials.
- **Google Ads:** the metric (CPA, ROAS, conversion rate) is **delayed (days), noisy (seasonality, auction dynamics), and expensive (real spend)**. Naive keep-if-better will chase noise and burn budget. The adapter must use **sequential/significance testing or a bandit**, a minimum sample/volume gate before a verdict, and a spend cap. Trials are concurrent and long, not 700/night.

The loop's accept/reject step is therefore pluggable: `deterministic-delta`, `significance-test`, or `bandit`.

### 2. Goodhart's law — the metric gets gamed
A code agent told to maximize "tests pass" can delete failing tests; "benchmark throughput" can special-case the benchmark's inputs; an ads agent maximizing CTR can chase clickbait that kills downstream conversion. Mitigations baked into the contract:
- **Guardrail metrics** that must not regress (tests-still-present-and-pass, lint/types, holdout eval, downstream conversion/quality).
- A **periodic Goodhart critic** (Phase 3) that inspects accepted changes for gaming.
- A **holdout** where applicable (eval set the optimizer can't see; an ads holdout audience).

### 3. The real objective is improvement-per-cost
Every trial costs tokens / compute / ad-spend. The ledger tracks **cost per trial**; the stop condition and hypothesis prioritization optimize metric-gain-per-cost, not raw metric.

### 4. Reversibility
Code: git revert is clean. Ads: "revert" means restoring the prior campaign state — the adapter must snapshot enough to roll back, and some changes have lingering effects (learning phases). Adapters declare a `revert` procedure and any irreversibility caveats.

## Artifacts the loop maintains (the explicit ledger)

Per run, under a `runs/<id>/` directory:

- **CHARTER.md** — objective, guardrails, trial budget, stop condition, domain adapter, Goodhart guards. The frozen frame for the run.
- **JOURNAL.jsonl** — append-only, one record per trial: `{id, hypothesis, change_summary, metric_before, metric_after, guardrails, decision, reason, cost, ts}`.
- **BACKLOG.md** — live hypothesis queue; families get pruned as they're exhausted.
- **IMPLEMENTED.md** — accepted improvements, human-readable, with the metric delta each bought. This is the durable answer to "implement the suggested benefits."
- **BASELINE** — pointer (git ref or snapshot path) to the current best artifact state.

## Domain adapters (the pluggable surface)

An adapter is a small declarative spec (see `references/domain-adapter-contract.md`) providing: artifact selector, candidate-metric menu, measurement command(s), trial harness, accept/reject strategy, guardrails, and revert procedure. Planned reference adapters:

- `adapters/code-perf-audit.md` — optimize a hot path; metric = benchmark time/throughput; guardrail = tests pass; deterministic-delta.
- `adapters/bug-finding.md` — metric = verified bugs per cost (precision-gated); harness = finder + adversarial verify; guardrail = no false positives.
- `adapters/code-generation.md` — metric = eval pass-rate on a held-out test set; guardrail = lint/types; holdout to resist gaming.
- `adapters/google-ads.md` — metric = CPA/ROAS (attribution-aware); significance-test or bandit; spend cap; holdout audience; long concurrent trials. (Connects to the Nutrient paid-ads measurement work.)

## Prior art: pi-autoresearch (borrow mechanics, not the fork)

[`davebcn87/pi-autoresearch`](https://github.com/davebcn87/pi-autoresearch) (MIT, ~7.1k stars, v1.6.0, active) is the most mature implementation of the Karpathy loop. It is a **Pi extension**, so its tool-registration and dashboard layer is harness-coupled and not directly portable to Claude — but its file conventions and several mechanics are proven and worth adopting wholesale into our Claude-native skill.

**Adopt (port into our skill / ledger):**
- **`METRIC name=value` stdout contract** — the trial harness emits metrics as parseable stdout lines. Make this the measurement interface (replaces prose-defined metrics).
- **MAD confidence scoring** — after ≥3 runs, compute the Median Absolute Deviation of the metric as a noise floor; `confidence = |best_improvement| / MAD` (green ≥2×, yellow 1–2×, red <1×). This is our default accept/reject for the `fast-low-noise` class — sharper than a vague significance test.
- **`.auto/`-style session layout + log.jsonl resumption** — append-only log that survives context resets; on idle/compaction, re-read the charter + log tail + git history before continuing. Fold into our JOURNAL.
- **git-commit-per-experiment** and **finalize → group accepted wins into review branches** — clean keep/revert and a real last-mile for code domains.
- **`checks.sh` backpressure** — guardrail checks (tests/lint/types) that block a keep on failure. Maps to our guardrails.
- **Optional hooks** (anti-thrash, idea rotation) — nice-to-have later.

**Do NOT adopt / keep as our differentiators (pi-autoresearch lacks these):**
- **Metric discovery (Phase 0 FRAME)** — pi-autoresearch is fixed-metric (asks the user upfront). Our discovery phase is the headline ask.
- **Per-domain accept/reject beyond MAD** — pi-autoresearch's noise model assumes cheap re-runs; it targets fast local code metrics only. Our `significance-test`/`bandit` strategies + the google-ads adapter handle delayed/expensive/noisy metrics it can't.
- **Cost-per-trial ledger and the Goodhart critic** — not present upstream.

Decision (2026-06-22): build Claude-native, port the five mechanics above, keep our differentiators. Do not fork the TS extension.

## Relationship to existing tooling

This orchestrates, it doesn't reinvent: trial harnesses call existing skills/CLIs (e.g. a `benchmark` skill for code perf, the ads measurement queries for ads). The loop is the meta-layer; adapters bind it to real measurement tools already in the environment.

## Open design questions (to resolve in later iterations)

1. Single-process (this agent self-paces the loop) vs. fleet (spawn N blind trial-runner subprocesses à la Karpathy's parallel agents)? Start single-process; design the adapter so a runner script can fan out later.
2. How much of Phase 0 metric-discovery is agentic vs. a fixed per-domain menu? Lean agentic with a menu as a prior.
3. Where does this live as a shippable skill — `~/.claude/skills/`, the authored skills repo, or a standalone CLI? Decide after a live test.
