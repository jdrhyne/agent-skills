# Domain Adapter Contract

A domain adapter binds the generic autoresearch loop to a real measurement surface. It is a short declarative spec (markdown with the fields below). The loop reads it in Phase 0 and uses it throughout.

## Required fields

- **name** — short slug (e.g. `code-perf-audit`).
- **when-to-use** — the kind of project/goal this fits.
- **artifact** — what the loop is allowed to mutate, and how to select the specific instance (e.g. "the hottest module by profiler output"; "the campaign named in the goal"). Must name what is OFF-limits to mutate.
- **candidate-metrics** — a menu of objectives the FRAME phase can pick from. For each: name, measurement command/procedure, "better" direction, measurement cost, and noise/latency class (`instant-deterministic` | `fast-low-noise` | `slow-noisy` | `delayed-expensive`).
- **guardrails** — metrics/invariants that must hold for any keep (e.g. "tests pass", "lint+types clean", "spend ≤ cap", "downstream conversion not regressed beyond X").
- **trial-harness** — the exact procedure to apply a candidate change and return the metrics. Should call existing tools/skills/CLIs, not reinvent measurement.
- **accept-reject** — `deterministic-delta` | `significance-test` | `bandit`, plus parameters (min effect size, min sample, confidence, spend cap).
- **revert** — how to roll back a discarded change; note any irreversibility caveats.
- **goodhart-guards** — domain-specific gaming risks and how the Phase-3 critic detects them (holdout, invariant checks, downstream metric).
- **trial-budget-default** — starting wall-clock and/or cost budget per trial, and rough trials-per-window expectation.

## Authoring rules
- Prefer **existing measurement tools**. The adapter is glue; the metric command should be something already trusted (a benchmark harness, a test runner, an attribution query).
- Be explicit about **noise/latency class** — it determines the accept/reject strategy and whether many-fast-sequential or few-long-concurrent trials are appropriate.
- Always declare at least one **guardrail**. An objective with no guardrail is a Goodhart trap.
- State the **unit of cost** (tokens, GPU-minutes, ad-spend dollars) so the ledger can track improvement-per-cost.
