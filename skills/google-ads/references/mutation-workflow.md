# Google Ads Mutation Workflow

Read this file only after the user explicitly requests an account change and the current state has been retrieved. Do not load or apply it for audits, recommendations, forecasts, or “what should I change?” questions.

The user's initial request establishes intent. Approval occurs only after the exact bounded diff below is displayed.

## Stop Conditions

Do not mutate when any of these are missing or ambiguous:

- authenticated account identity and customer ID;
- manager-account context, if applicable;
- exact entity IDs and entity types;
- current values read immediately before the proposal;
- requested new values and effective scope;
- validation result;
- explicit approval for the displayed preview;
- a reliable post-write readback path.

Never broaden a change from a sample, recommendation, similarly named entity, campaign family, or manager account.

## Batch Bound

One approval batch may contain at most 25 exact entities, or a lower provider limit when the selected operation requires one. Split larger requests into independently previewed and approved batches. Execute one call or batch at a time, read every changed entity back before continuing, and stop all remaining batches on any failure, partial failure, unexpected current value, account-context change, or other state drift.

## Required Preview

Display this structure before seeking approval:

```text
Account identity: <display name>
Customer ID: <redacted except final four digits in chat>
Manager context: <manager ID or none>
Change type: <pause|enable|budget|bid|targeting|conversion|other>
Entities: <count and exact resource IDs>
Before → after: <one row per entity and field>
Effective timing: <immediate or specified schedule>
Expected impact: <bounded explanation>
Validation method: <API validate_only | browser preflight only>
Rollback: <exact reverse operation, if available>
Notifications/data effects: <known external effects>
```

Then ask for explicit approval of that exact account, entity set, and before/after diff. A reply that changes scope invalidates the preview; fetch state and preview again. Never treat approval of one batch as approval of a later batch.

## API Sequence

1. Split the requested entity set into batches of at most 25 exact entities, or the lower provider limit.
2. Re-read account identity, entity IDs, and current field values immediately before validating each batch.
3. Construct the smallest possible operations with explicit update masks.
4. Submit the request with `validate_only=True` when the service supports it.
5. If the service does not support validation-only, state that limitation and do not represent a local syntax check as server validation.
6. Resolve every validation error and rebuild the preview if any effective value changes.
7. Obtain action-time approval for this batch after successful validation.
8. Execute this batch once. Use `partial_failure=True` only when the method supports it and partial success is acceptable for the approved entity set.
9. Parse partial-failure details per entity. Never report the entire batch as successful when any operation failed.
10. Record the safe request ID and returned resource names.
11. Query every affected resource and compare persisted values with the approved diff.
12. Stop all remaining batches on failure, partial failure, unknown readback, or state drift. Otherwise, preview and obtain separate approval for the next batch.

For unsupported partial failure, preserve all-or-nothing semantics and report the request failure without retrying non-idempotent creates. Retry only documented transient failures, with bounded backoff, after determining that retry cannot duplicate or broaden the change.

## Browser Sequence

1. Split the requested entity set into batches of at most 25 exact entities, or a lower UI/provider limit.
2. Keep the attached session user-attended.
3. Re-confirm the visible account and affected rows immediately before each batch preview.
4. Record `validation method: browser preflight only`; the UI does not provide API `validate_only`.
5. Verify the target controls are enabled and the proposed value satisfies visible constraints.
6. Obtain action-time approval for this exact batch preview.
7. Re-identify each control by its current accessible name and surrounding entity identity.
8. Apply only the approved changes. Stop on an unexpected dialog, extra selected entity, changed current value, or account switch.
9. Refresh or reopen the affected view and read every changed value back.
10. Stop all remaining batches on failure, unknown readback, or state drift. Otherwise, preview and obtain separate approval for the next batch.

Never use coordinates, remembered row positions, or stale selectors for a write.

## Result Report

Report one status per approved entity:

| Entity ID | Approved before → after | Validation | Execution | Post-write readback |
|---|---|---|---|---|

Use only these execution states: `verified`, `failed`, `partial failure`, or `unknown`. “Submitted” is not “verified.” If readback disagrees or cannot be completed, report `unknown`, stop further writes, and provide the safest recovery or rollback option.
