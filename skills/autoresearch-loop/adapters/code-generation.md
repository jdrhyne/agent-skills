# Adapter: code-generation

Optimize a generation pipeline (prompt, spec, few-shot set, decoding params, or scaffolding) toward an **eval pass-rate** on a held-out test set. The metric is moderately fast and near-deterministic if generation temperature is fixed — close to the code-perf case, but with a sharper Goodhart risk (the optimizer can overfit the visible eval).

- **name:** code-generation
- **when-to-use:** improving how an agent/model generates code against a measurable benchmark (e.g. a suite of programming tasks with unit tests).
- **artifact:** the mutable generation inputs — the prompt/system message, few-shot examples, the spec, or pipeline config. OFF-limits: the eval tasks and their tests (editing them is the textbook Goodhart cheat), and the holdout split.
- **candidate-metrics:**
  - pass@1 on the **visible** eval set (fraction of tasks whose generated code passes its tests; higher better) — `fast-low-noise` if temperature is fixed/seeded; otherwise `slow-noisy` and needs multiple samples.
  - pass@k (allow k attempts) — higher better; more expensive.
  - tokens-per-solve / cost — secondary tradeoff monitor (a pass-rate win that triples cost may not be worth it).
- **guardrails:** generated code must run in a sandbox (no network/file escapes); a **holdout** eval split the optimizer never sees must not regress while the visible set improves (the anti-overfit guard); lint/type-check on generated code.
- **trial-harness:** `measure.sh` runs the generator over the eval set, executes each task's tests, and emits `METRIC passrate=<0..1>` plus `METRIC holdout=<0..1>` and `METRIC tokens=<n>`. Fix the seed/temperature so the metric is comparable across trials.
- **accept-reject:** `deterministic-delta` (fixed seed) gated by MAD confidence; if sampling is stochastic, `significance-test` over multiple seeds. A visible-set gain that **regresses the holdout** is a discard (overfitting), even if pass@1 went up.
- **revert:** git revert of the prompt/spec/config (clean).
- **goodhart-guards:** the holdout split is the primary guard; the Phase-3 critic compares visible-vs-holdout trajectories — divergence (visible ↑, holdout flat/↓) means the optimizer is memorizing the visible tasks, not generalizing. Treat as gaming: revert and tighten.
- **trial-budget-default:** one eval-set pass per trial; cost unit = tokens (can be significant). Fewer trials than code-perf because each pass invokes the model many times.

## Why the holdout matters here specifically
Unlike code-perf (where the benchmark input is fixed and the oracle is independent), a generation prompt can be tuned to the *exact* visible tasks — raising pass@1 while learning nothing transferable. The holdout is the only thing that distinguishes real improvement from memorization, which is why it's a hard guardrail, not an optional metric.
