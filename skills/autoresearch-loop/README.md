# autoresearch-loop

A domain-agnostic, metric-driven improvement loop — a generalization of [Andrej Karpathy's autoresearch](https://github.com/karpathy/autoresearch) that **discovers what to measure** for a project/goal, then runs a disciplined *propose → trial → keep-or-revert* loop, keeping an explicit ledger of what was tried, kept, discarded, and implemented.

## What it adds over Karpathy's autoresearch

Karpathy's loop hardcodes three things; this generalizes each:

1. **Metric discovery** — his metric (`val_bpb`) is hand-picked; here a FRAME phase proposes candidate metrics from the project/goal/context.
2. **Domain adapters** — his artifact+metric+trial triple is ML-training-specific; here pluggable adapters cover code perf-auditing, codegen, bug-finding, and ad optimization.
3. **Adaptive statistics** — his keep-if-better assumes a fast, free, deterministic metric; here the accept/reject strategy adapts per domain (MAD confidence for fast metrics; significance/bandit for noisy, delayed, expensive ones like ads).

It **ports the proven mechanics** of [pi-autoresearch](https://github.com/davebcn87/pi-autoresearch) (MIT) — the `METRIC name=value` contract, Median-Absolute-Deviation confidence scoring, the `.auto/` session layout, git keep/revert, and `checks.sh` guardrails — reimplemented Claude-native as the dependency-free `arl` CLI (`scripts/arl.mjs`).

## Layout

```
SKILL.md                     orchestrator (Phases 0–3: frame → baseline → loop → adapt)
DESIGN.md                    architecture + per-domain tensions + prior-art decision
scripts/arl.mjs              the runtime CLI (run/log/status/finalize)
references/
  runtime-contract.md        .auto/ layout, METRIC contract, MAD scoring, arl commands
  domain-adapter-contract.md how to define a new domain adapter
  journal-schema.md          ledger record formats
adapters/
  code-perf-audit.md         fast deterministic metric (validated live)
  code-generation.md         eval pass-rate with a holdout anti-overfit guard
  bug-finding.md             findings-accumulation variant (append-on-verify)
  google-ads.md              noisy/delayed/expensive metric (significance/bandit)
examples/code-perf-demo/     a real run: 16.28 → 2.77 ms (5.9×). See RESULTS.md.
```

## Quickstart

```bash
arl() { node /path/to/autoresearch-loop/scripts/arl.mjs "$@"; }   # or put arl.mjs on PATH

# In the project you're optimizing, after writing .auto/measure.sh (+ optional .auto/checks.sh):
arl init --name "speed up X" --metric ms --direction lower
arl run                                   # runs measure.sh + checks.sh, parses METRIC
arl log --status keep --desc "first idea" # --metric defaults from the last run; keep auto-commits
# ...propose, run, log keep/discard until the stop condition...
arl status                                # baseline → best, MAD confidence
arl finalize                              # writes .auto/RESULTS.md (durable implemented-improvements report)
```

A `discard`/`crash`/`checks_failed` auto-reverts the code while preserving `.auto/`. A `keep` is refused if the last run failed checks (use `--force` to override). See `references/runtime-contract.md` for the full contract.

## Provenance

Inspired by Karpathy's autoresearch; mechanics ported from pi-autoresearch (MIT). This repo is original work; only conventions and algorithms (the `METRIC` contract, the MAD formula) were adopted.
