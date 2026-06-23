# Metric discovery (Phase 0 FRAME)

The step Karpathy's autoresearch skips and pi-autoresearch hands to the user: given `{project, goal, context}`, *derive* what to optimize before optimizing it. A loop is only as good as its metric — a wrong or gameable metric makes the loop confidently produce the wrong thing. This is the procedure.

## 1. Restate the goal as an outcome
Write the true outcome the stakeholder wants in one sentence, in their terms — not a proxy. "Faster builds" → "developers wait less for CI." "Better ads" → "more qualified pipeline per dollar." The outcome is usually expensive or slow to measure directly; that tension is the whole problem.

## 2. Enumerate candidates along the proxy→outcome spectrum
List 4–8 measurable signals, from cheap leading proxies to the lagging true outcome:
- **Leading proxies** — cheap, fast, far from the goal (CTR, build seconds, lines changed).
- **Mid proxies** — moderate cost, closer (task-success in a test harness, p95 latency).
- **True outcome** — expensive/slow, what actually matters (qualified pipeline, retained users, bugs that reached production).

## 3. Score each candidate
Rate every candidate on six axes (high/med/low):

| Axis | Question |
|------|----------|
| Measurability | Can it be measured repeatably within a trial budget? |
| Latency | instant / fast / slow / delayed before a value exists |
| Noise | deterministic / low / high run-to-run |
| Alignment | how close to the true outcome (proxy distance)? |
| Gameability | how easily can the optimizer satisfy it *without* achieving the goal? |
| Cost | tokens / compute / dollars per measurement |

## 4. Choose primary + guardrails + strategy
- **Primary objective** = the most *aligned* candidate that is still measurable within budget. Prefer a mid proxy over a leading one even if it costs more — alignment beats convenience.
- **Guardrails** = cheap metrics that catch the primary's failure modes (the ones a naive maximizer would exploit). A guardrail need not be aligned; it needs to be a tripwire.
- **Accept/reject strategy** falls out of Latency × Noise: instant+deterministic → `deterministic-delta` (+ MAD confidence); fast+noisy → MAD with median-of-N trials; slow/delayed/expensive → `significance-test` or `bandit` with a minimum sample.

## 5. Red-team the chosen metric (the Goodhart pre-mortem)
Before committing, ask: **"If an adversary maximized this primary metric while ignoring my intent, what would they do?"** Each answer is a gaming path. Turn the most plausible ones into guardrails or a holdout. If you can't construct a guardrail for a serious gaming path, the metric is too weak — pick a more aligned primary. This step is mandatory; a metric with no named gaming path usually means you haven't thought hard enough, not that it's ungameable.

## Worked example — ambiguous goal: "make our docs site better"

1. **Outcome:** readers find the answer they came for, fast, without filing a support ticket.
2. **Candidates:** time-on-page; bounce rate; on-site search success rate; task-success in a 5-user usability test; support tickets tagged "docs"; scroll-depth.
3. **Score (abridged):** time-on-page — measurable/instant/noisy/**low alignment** (longer can mean confused *or* engaged) / **high gameability** (pad pages) / cheap. Task-success in a usability test — slow/low-noise if scripted/**high alignment**/low gameability/expensive. Support-tickets-deflected — delayed/noisy/**highest alignment**/low gameability/cheap-but-lagging.
4. **Choose:** primary = **scripted task-success rate** (most aligned that's still runnable per trial); guardrails = time-to-task-success (don't make success slower) and a content-accuracy check (don't delete hard sections to simplify). Strategy = slow/low-noise → small-sample significance, not single-trial.
5. **Red-team:** "maximize task-success" → the optimizer could overfit to the exact test tasks → guardrail = a **holdout** set of tasks it never sees; "shorten everything" → accuracy/coverage guardrail. Rejected time-on-page outright because no guardrail cleanly stops the pad-the-page gaming path.

The discipline that matters: **alignment over convenience for the primary, and every primary ships with at least one guardrail derived from its own red-team.**
