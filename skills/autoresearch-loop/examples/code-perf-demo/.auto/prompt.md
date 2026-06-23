# Autoresearch: speed up analyze() (top-10 word frequencies + checksum)

## Objective
Minimize wall-time of analyze() in solution.js over a fixed 40k-word input.

## Metrics
- Primary: ms (lower better) — median of 7 timed runs from bench.js
- Guardrail: test.js must pass (independent reference oracle); a keep is blocked on failure.

## How to run
`./.auto/measure.sh` → METRIC ms=<median>. `./.auto/checks.sh` → correctness.

## Files in scope
- solution.js — the only file to optimize.
## Off limits
- bench.js, test.js, gen.js (changing the harness/oracle would game the metric).

## What's been tried
(updated as we go)
