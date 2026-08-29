# ClawHub skill refresh wave plan

This plan implements the 2026-08-29 review of Jonathan Rhyne's public ClawHub skills sourced from this repository. It reuses the shared `planner-orchestrator`, `contract-architect`, `implementation-worker`, and `critic-reviewer` roles without repo-specific variants.

Registry publication, visibility changes, deletion, merging, and transfer are outside implementation scope until Jonathan approves the final release gate.

## Waves

| Wave | Tasks | Gate |
| --- | --- | --- |
| AS-W0 | AS-T1 | Sources and public versions are mapped; no unresolved ownership ambiguity. |
| AS-W1 | AS-T2, AS-T3, AS-T4 | P0 credential, excessive-agency, and deprecation findings pass critic review. |
| AS-W2 | AS-T5, AS-T6, AS-T7 | Portability, privacy, destructive-action, and ambiguity tests pass. |
| AS-W3 | AS-T8, AS-T9, AS-T10 | Provider contracts and progressive-disclosure checks pass. |
| AS-W4 | AS-T11 | Release manifest and provenance workflow are dry-run safe. |
| AS-W5 | AS-T12 | Full validation is green and every registry mutation remains approval-gated. |

## Execution ledger

| Task | Status | Owner | Evidence / blocker |
| --- | --- | --- | --- |
| AS-T1 | completed | planner-orchestrator | Canonical source is `jdrhyne/agent-skills` at `a4d31ad`; public versions and verification decisions are recorded in `docs/clawhub-release/public-baseline.json`. |
| AS-T2 | completed | implementation-worker | Read-only routing, credential safety, bounded mutation previews, provider-aware analysis, and 9 offline tests are implemented. |
| AS-T3 | completed | implementation-worker | Capability discovery, bounded batch approval, untrusted-content handling, package cleanup, and 9 offline tests are implemented. |
| AS-T4 | completed | contract-architect | Source removal is preserved and the approval-gated hide/deprecation record is in `docs/clawhub-release/sysadmin-toolbox.md`. |
| AS-T5 | completed | implementation-worker | Stable IDs, structured-field-only monotonic ID recovery, exact literal matching, atomic mode-600 writes, locking, backups, confirmations, and 11 shell cases pass. |
| AS-T6 | completed | implementation-worker | Gong credential isolation, exact company-local midnight provenance, official nested response schemas, strict pagination, bounds, signal-safe cleanup, and 29 tests pass; Nudocs exact-identity data/action gates and 8 contract tests pass. |
| AS-T7 | completed | implementation-worker | Current-thread-first recovery, approval-gated external sources, untrusted-content handling, conflict evidence, consent-gated persistence, and 9 routing tests pass. |
| AS-T8 | completed | implementation-worker | Protected loopback OAuth, current GSC/GA4 contracts, strict state-specific freshness and finite metrics, exact compatibility/metadata schemas, bounded pagination/retries, quotas/CSV output, and 9 GSC plus 10 GA4 tests pass. |
| AS-T9 | completed | implementation-worker | Canonical OpenClaw metadata, plugin 0.1.1 and ten-tool routing, protected secret guidance, per-call DWS estimate/confirmation gates, and 11 contract tests pass without a live tool call. |
| AS-T10 | completed | implementation-worker | Current/manual evidence defaults, opt-in bounded history, untrusted-input handling, evidence/counterevidence/uncertainty, non-diagnostic language, native scheduling consent, and 10 tests pass. |
| AS-T11 | completed | contract-architect | Release metadata, exact catalog and baseline binding, duplicate-key rejection, ordered ignore profiles, and pinned ClawHub 0.23.3 packager-negation regression checks pass 46 adversarial tests. |
| AS-T12 | completed | critic-reviewer | Independent final critic found no remaining P0/P1 issues: 46 release tests, 104 package Python tests, 11 Todo cases, exact manifest/baseline/ignore attacks, pinned ClawHub 0.23.3 packaging, repository validation, generated README, compilation, shell, data parsing, and diff gates pass. Merge, authentication, metered DWS requests, and registry mutations remain unexecuted. |

## Validation policy

- Use the repository's real `./scripts/validate-skills.sh` entrypoint.
- Add deterministic, offline fixtures for helpers and routing/safety behavior.
- Treat scanner timeouts or missing external credentials as not-run, never as passes.
- Do not invoke live provider writes or credit-consuming Nutrient operations.
- Do not publish, hide, delete, merge, or transfer a ClawHub listing during implementation.
