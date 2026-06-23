# Adapter: bug-finding

The framing-bender. Unlike the perf/codegen adapters, the artifact here is **not mutated code** — it's an accumulating findings ledger. "Keep" means a candidate bug survived verification and is novel; "discard" means it was refuted or a duplicate. This shows the loop structure (propose → trial → keep/discard → ledger) generalizes past Karpathy's mutate-and-measure shape.

- **name:** bug-finding
- **when-to-use:** sweeping a codebase for real bugs, accumulating a verified, deduplicated list.
- **artifact:** the **findings ledger** (`.auto/bugs.jsonl`), not the source. Optionally the *finder strategy* (prompt/heuristics) can be the mutated artifact in an optimizer framing — but the default is accumulation.
- **candidate-metrics:**
  - cumulative **verified** bugs (higher better) — the primary objective; counts only post-verification, deduplicated finds. `fast-low-noise` per round but the metric is monotonic, not a delta.
  - **precision** = verified / candidates (higher better) — the guardrail-as-metric; a finder that floods false positives is worse than a quiet one.
  - cost per verified bug (lower better) — the efficiency monitor.
- **guardrails:** **no false positives.** A candidate is only counted after independent adversarial verification confirms it (ideally majority of N skeptics prompted to *refute* it). Severity/repro must be stated. Precision must stay above a floor or the round is rejected and the finder retuned.
- **trial-harness:** one trial = a **finder pass** over a target slice (by file, by subsystem, by bug-class) → candidate bugs → **adversarial verify** each (independent agent(s) trying to refute) → dedup against `.auto/bugs.jsonl`. `measure.sh` emits `METRIC verified_bugs=<round_count>` and `METRIC precision=<0..1>`.
- **accept-reject:** per-candidate, not per-code-change. Confirmed + novel → append to `bugs.jsonl` (the "keep"). Refuted or duplicate → drop with the reason (the "discard"). Loop-level stop = **loop-until-dry**: K consecutive rounds adding zero novel verified bugs.
- **revert:** none — nothing in the source is mutated, so there is no code to roll back. A "discard" simply doesn't append to the ledger. (This is why the adapter overrides arl's git keep/revert: `arl` is for mutate-and-measure domains; bug-finding uses the findings-accumulation variant and records to `bugs.jsonl` directly.)
- **goodhart-guards:** the adversarial verifier is the core guard against the finder gaming "bug count" with plausible-but-fake reports. The Phase-3 critic samples kept bugs and re-verifies; a drop in true precision means the verifier is too lax — tighten it (more skeptics, require a reproduction).
- **trial-budget-default:** per finder pass; multi-modal sweeps (different finders blind to each other) raise recall. Cost unit = tokens. Stop on loop-until-dry, not a fixed count.

## Why this isn't Karpathy's loop verbatim
There is no scalar like `val_bpb` to monotonically minimize by editing one file — the "improvement" is *more verified knowledge*, and the failure mode is false confidence, not slowness. So the accept/reject moves from "is the metric better?" to "did this candidate survive independent refutation and is it new?", and the guardrail (precision) is load-bearing rather than secondary. The ledger and loop-until-dry stop condition carry over unchanged; the keep/revert mechanics are replaced by append-on-verify.
