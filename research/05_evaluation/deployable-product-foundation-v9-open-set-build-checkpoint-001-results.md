# Deployable product foundation V9 open-set build checkpoint

## Run identity

- Result ID: `deployable-product-foundation-v9-open-set-build-checkpoint-001`
- Component: evidence-sufficiency release boundary and deployment packaging
- Status: valid build-only checkpoint
- Date: 2026-08-21
- Implementation revision: `df093d8c6bffa93577a5210c5beb57ccd973a6c1`
- Working tree at focused verification: clean after the implementation commit
- Data: 80 consumed v1 cases referenced as development-only; no new decision
  split exists or was opened
- Provider/model calls: zero
- Private or held-out data read: no
- Cost: USD 0

## Decision context

V8 proved that the exact then-current containers and operational entrypoints
worked, but real publication correctly failed closed because evidence
sufficiency had no selected implementation. V9 asks only whether a safer,
provider-neutral successor boundary can be built without weakening that refusal.
It does not evaluate or select a semantic model.

## Build result

- The new gate separates semantic support scoring from the deterministic final
  answer/abstain policy.
- Direct support, completeness, contradiction, ambiguity, and exact supporting
  hit IDs are independent signals.
- Missing evidence, verifier exceptions, unknown hit IDs, malformed signals,
  incomplete support, contradiction, and excessive ambiguity fail closed.
- AnyHit remains an unselectable historical control.
- Academic-integrity refusal remains owned by deterministic tutor policy rather
  than being mislabeled as evidence sufficiency.
- The v2 instrument validates as build-only. Its preflight reports
  `blocked-dataset-not-frozen` with no calls or private reads.
- The focused implementation and instrument suite passed 29/29 tests.

## Gates

| Gate | Result |
| --- | --- |
| Provider-neutral final decision | Pass |
| Unknown evidence lineage fails closed | Pass |
| Verifier failure is redacted and fails closed | Pass |
| Consumed v1 data cannot select v2 | Pass |
| AnyHit cannot become selectable | Pass |
| Academic integrity remains a separate policy boundary | Pass |
| New 120-case decision set frozen and reviewed | Pending |
| Exact candidate and fresh provider/model metadata bound | Pending |
| Calibration or decision execution authorized | Pending |
| Product evidence-sufficiency method selected | Pending |
| Current source revision rebuilt and publication completed | Pending |

## Decision

**Refine; keep publication fail closed and select no release candidate.** The
method boundary is safer and ready for dataset authoring, but no decision set,
candidate model, threshold calibration, or selection evidence exists. V8 image
health remains historical evidence only because the current source tree has
changed and has not been rebuilt.

## Next step

Author and independently review the new 120-case source-linked decision set,
then bind exact current candidates in a separate checkpoint. Paid, provider,
private-source, and one-time decision execution still require explicit
authorization. Only a passing selected method can reopen current-image HTTPS
publication and subsequent host rehearsal.
