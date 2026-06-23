# Ledger Schema

All run state lives under `runs/<id>/`.

## JOURNAL.jsonl (append-only, one object per trial)

```json
{
  "id": 7,
  "ts": "2026-06-22T21:10:00Z",
  "hypothesis": "Cache the parsed font index across export calls",
  "change_summary": "memoize loadFontIndex() in export path",
  "metric_before": {"primary": 1.80, "unit": "s/op"},
  "metric_after":  {"primary": 1.62, "unit": "s/op"},
  "guardrails": {"tests_pass": true, "lint_clean": true},
  "decision": "keep",
  "reason": "10% faster, guardrails green, exceeds min effect size",
  "cost": {"unit": "tokens", "amount": 14200},
  "baseline_ref": "git:abc1234"
}
```

`decision` ∈ `keep | discard | inconclusive`. `inconclusive` (noisy domains) means the trial didn't reach significance — the hypothesis returns to the backlog with accumulated evidence, not discarded.

## CHARTER.md (frozen at FRAME)
Objective, guardrails, trial budget, stop condition, adapter name, accept/reject strategy + params, Goodhart guards, cost unit.

## BACKLOG.md
Live hypothesis queue grouped by family. Mark families `active | exhausted | parked`. Exhausted families are never re-proposed.

## IMPLEMENTED.md
Human-readable list of kept changes, each with: hypothesis, the metric delta it bought, the cost, and the commit/snapshot ref. This is the durable deliverable.

## BASELINE
A single line: the git ref or snapshot path of the current best artifact state. Advanced only on a `keep`.
