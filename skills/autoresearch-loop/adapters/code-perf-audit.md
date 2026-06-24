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

## Pitfalls & techniques (validated on two real runs: `mapFormattingWithDiff` 7.5× win, and a DWS markdown path that was a correct *no-win* / re-scope)

These cost real iterations on live runs; treat them as first-class steps, not afterthoughts. Note both outcomes are successes: the loop is working when it lands a verified win **and** when it cheaply proves a target has no in-scope headroom and re-scopes.

- **Profile before optimizing — do not trust the assumed hot path.** On the live run the agent guessed the bottleneck wrong *twice* (an "O(n²)" null-fill that was actually O(n) due to in-place mutation; then a transposition matcher that was real O(n²) but only ~5% of runtime). A 1-shot profile (time the suspected sub-parts, or time a dependency call in isolation) locates the real cost. Add a `profile` step to Phase 1: before proposing changes, measure where the time actually goes.
- **The benchmark must stress the IN-SCOPE artifact, not a dependency.** The first workload made the function 97% `fast-diff` (a library, out of scope) — so no in-scope change could move the metric. Verify the split: if a dependency dominates, either the goal is "replace/avoid the dependency" (re-scope) or the workload is wrong. The fix was choosing a workload (large document + tiny edit) where the in-scope code dominates and the dependency is trimmed to ~0.
- **Managed code in front of a native/FFI/engine/network call is almost always bound by the thing it wraps — confirm there is in-scope headroom *before* running the loop.** Second confirmation, on a real DWS path (Elixir `MarkdownConverter.convert/2` over the MDEx Rust NIF): a one-shot profile showed the in-scope Elixir was **0.4–3.8% of wall-time** (and ~2% of BEAM reductions); the comrak Rust NIF was everything else. No in-scope change could produce a meaningful win, and the loop's correct output was a **true negative** — "this target is NIF-bound, re-scope." This is the general rule: when a thin managed layer (Elixir/Ruby/Python/JS) wraps native code (Rust/C NIF, WASM), an external engine (Document Engine, a DB), or the network, the wrapped thing dominates. The in-scope levers are usually *choose/configure the engine* or *avoid the call*, not micro-optimize the wrapper. Spend one profiling run to measure the managed-vs-native split; if native dominates, say so and re-scope rather than shipping a sub-noise edit dressed up as perf. (The loop's profile-first guard caught two would-be false wins here: a <1% wall-time edit and a ~2% reductions edit.)
- **Input regime determines the bottleneck.** Same function, two regimes: heavy-edit → diff-bound (no in-scope win); large-doc-small-edit → allocation-bound (7.5× in-scope win). Phase 0 should pick the regime that matches the real goal (here: reformat-on-keystroke in a large doc) — the metric is only as meaningful as the workload representing it.
- **Differential testing is the strongest oracle, and works when the project's test harness can't run.** When the repo's own test suite wouldn't execute (a `vitest` version/config skew), correctness was proven by extracting the original function and comparing old-vs-new output on 600 randomized inputs (ascii, multibyte, surrogate pairs, multi-segment, revisions, every edit shape) — byte-identical. Prefer this for pure functions: it needs no test framework and catches any behavioral drift. Still run the authoritative suite in CI before merge.
