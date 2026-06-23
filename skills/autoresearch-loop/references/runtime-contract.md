# Runtime contract — `.auto/` layout + the `arl` CLI

Ported from pi-autoresearch (MIT). Claude Code has no Pi-style extension/tool system, so pi's `run_experiment`/`log_experiment` tools are reimplemented as a dependency-free Node CLI (`scripts/arl.mjs`) the agent calls via Bash. The file conventions and the METRIC/MAD mechanics match upstream exactly.

## `.auto/` session layout (at the working-dir root)

| File | Purpose | Written by |
|------|---------|-----------|
| `.auto/prompt.md` | Objective, metrics, files in scope, off-limits, constraints, "what's been tried". A fresh agent reads this to resume. (= our CHARTER) | agent (Phase 0) |
| `.auto/measure.sh` | Trial harness. `set -euo pipefail`; emits `METRIC name=value` stdout lines. | agent / domain adapter |
| `.auto/checks.sh` | Optional guardrail backpressure (tests/lint/types). Runs after a passing benchmark; failure blocks a keep. | agent (only if constraints require) |
| `.auto/log.jsonl` | Append-only result log; survives context resets. | `arl` |
| `.auto/state.json` | Session config (name, metric, unit, direction, segment). | `arl init` |
| `.auto/ideas.md` | Hypothesis backlog. | agent |

## The METRIC contract (exact)

`measure.sh` writes lines matching `^METRIC\s+([\w.µ]+)=(\S+)$`. The primary metric name must match `arl init --metric`. Secondary metrics are tracked as tradeoff monitors. For fast noisy benchmarks (<5s), run the workload several times inside `measure.sh` and emit the **median** — this makes the confidence score reliable from the start.

## MAD confidence (exact)

After ≥3 runs in the current segment, `arl log` reports `confidence = |best_kept − baseline| / MAD`, where MAD is the Median Absolute Deviation of the segment's metric values (a robust noise floor). `≥2.0×` green (likely real), `1.0–2.0×` yellow, `<1.0×` red (within noise — re-run before trusting). Advisory only; never auto-discards. Returns n/a with <3 points or zero measurable noise.

## `arl` commands

```bash
arl init  --name "<session>" --metric <name> [--unit ms] [--direction lower|higher]
arl run   [--timeout 600] [--checks-timeout 300]   # runs measure.sh, parses METRIC, then checks.sh
arl log   --status keep|discard|crash|checks_failed [--metric <X>] --desc "..." \
          [--asi key=value ...] [--cost-unit tokens --cost 14200] [--force]
arl status
```

- `arl run` persists the parsed primary metric + checks result to `.auto/last.json`, so **`arl log` does not need `--metric`** — it defaults to the last run (pass `--metric` only to override). This avoids running the benchmark twice per trial.
- `keep` → `git add -A && git commit` (advances baseline). **Refused** if the last run failed checks (override with `--force`) — the guardrail can't be silently bypassed.
- `discard`/`crash`/`checks_failed` → reverts tracked code via `git checkout/clean -- . :(exclude).auto`, **preserving `.auto/`** so the log and prompt survive.
- `--asi` (agent self-insight) records *what was learned*, not what was done — the only thing that survives a discard's revert. Annotate failures heavily.
- `--cost` extends pi's schema with our cost-per-trial tracking (improvement-per-cost).

## measure.sh template

```bash
#!/bin/bash
set -euo pipefail
# Fast pre-check (syntax/types) — fail in <1s before the expensive workload.
# Run the workload; for fast noisy benchmarks, repeat N times and emit the median.
result=$(run_the_workload)
echo "METRIC primary_name=$result"
# echo "METRIC secondary_name=$other"   # tradeoff monitors
```

## checks.sh template (only when correctness must hold)

```bash
#!/bin/bash
set -euo pipefail
# Suppress success noise; surface only errors (last 80 lines are fed back).
run_tests   2>&1 | tail -50
run_typecheck 2>&1 | grep -i error || true
```
