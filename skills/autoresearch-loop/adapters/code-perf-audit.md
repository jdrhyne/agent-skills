# Adapter: code-perf-audit

The easy, Karpathy-like case: a fast, near-deterministic, free metric where MAD confidence applies directly and you can run many sequential trials. **Validated end-to-end** by the demo in `examples/code-perf-demo/` (16.28ms → 2.77ms, 5.9× faster, 3 keeps + 1 auto-reverted discard, 19× confidence).

- **name:** code-perf-audit
- **when-to-use:** speeding up a hot path / module with a benchmarkable workload and a correctness oracle.
- **artifact:** the in-scope source file(s) named in `.auto/prompt.md`. OFF-limits: the benchmark and the test oracle themselves (editing them games the metric — a Goodhart trap).
- **candidate-metrics:**
  - wall-time of the workload (ms/µs, lower better) — `fast-low-noise`. Default primary.
  - throughput (ops/s, higher better) — `fast-low-noise`.
  - allocations / peak memory — `fast-low-noise`, useful as a secondary tradeoff monitor.
- **guardrails:** an independent correctness oracle (`checks.sh` running a reference implementation or the project's test suite) must pass; a keep is blocked on failure. Optionally lint/types.
- **trial-harness:** `measure.sh` runs the workload and emits `METRIC name=value`. For sub-5s benchmarks, run the workload N times **inside** the script and emit the **median** so the noise floor is stable from run 1 (the demo uses 7 runs, drops a warmup, reports the median).
- **accept-reject:** `deterministic-delta` gated by **MAD confidence**. Keep on a real improvement; treat `<1.0×` confidence as within-noise and re-run before trusting; equal/worse → discard.
- **revert:** `git checkout`/`clean` of the in-scope code (handled by `arl log --status discard`, which preserves `.auto/`). Clean and instantaneous — no hysteresis.
- **goodhart-guards:** the independent oracle (a reference impl the optimizer can't see or edit) is the main guard; Phase-3 critic checks that keeps didn't special-case the benchmark's fixed input.
- **trial-budget-default:** seconds per trial; many sequential trials are fine. Cost unit = tokens (compute is negligible).

## What the live test proved
- The `arl` loop drives real code: keeps auto-commit and stack (Map count → regex tokenize compounded to 5.9×); a discard (`toLowerCase` cache that regressed to 4.19ms) auto-reverted the file to the prior best while the ledger persisted.
- MAD confidence tracked correctly across trials (n/a → 11× → 19× green) on real measured numbers.
- The independent oracle held the line — every kept change had to remain correct.
