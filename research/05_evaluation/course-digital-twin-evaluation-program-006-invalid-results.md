# Finite evaluation program 006 invalid result

## Outcome

Program 006 is `invalid-execution`; it is not a product-quality result. The
question-targeted candidate durably persisted all 500 responses and the paired
control durably persisted all 100 responses. Three control provider calls
returned non-completed Responses API results. The adapter preserved those
cases as explicit operational failures, but its completion check then treated
more than one failed call as corruption of the whole execution.

The subsequent automatic correction did not make another provider call. It
recomputed provider sub-budgets from the remaining stage budget, which changed
the immutable provider-ledger binding and failed closed on resume. These are
two demonstrated harness defects:

- per-case provider failures were persisted correctly but classified as an
  invalid whole-run condition instead of being measured by completion and
  malformed-response gates;
- a resume changed frozen provider budget bindings.

Hidden gold was never opened, no deterministic product score was calculated,
and the sealed 10,000+1,000 evaluation remained unopened. No factual quality
claim follows from program 006.

## Accounting and isolation

- Retrieval: 15 calls, USD 0.00057488, `completed-keep`.
- Candidate: 400/400 provider calls completed; 500/500 responses persisted;
  USD 1.3915925.
- Control: 94 calls completed and three failed; 100/100 responses persisted;
  USD 0.1187445.
- Total: 512 provider calls/batches and USD 1.51091188.
- Provider retries: zero.
- Private data: none.
- Hidden-gold scoring: not opened.
- Final 10,000+1,000 product stage: not opened.

The three provider failures were
`academic-action-router-dev-0055-q1`,
`academic-action-router-dev-0055-q4`, and
`academic-action-router-dev-0096-q4`. Each was retained as an explicit
operational-failure response rather than omitted.

## Decision

Preserve program 006 as immutable invalid evidence and revoke its authority.
Program 007 is the single harness-only successor. It keeps the same cases,
method, prompts, model identities, gold, quality gates, and stage budgets. It
changes only execution semantics: persisted provider failures are scored as
cases, and provider-ledger ceilings remain frozen during resume.

Program 007 still stops on gold leakage, identity drift, ledger corruption,
privacy/security failure, or the global USD 50 ceiling. It advances between
valid stages automatically and does not introduce another approval loop.

## Limitations

- Program 006 cannot estimate product quality because hidden gold never
  opened.
- The 500 development questions are now a known set; program 007 is a
  method-confirmation checkpoint, not a new held-out claim.
- The cumulative spend for programs 005 and 006 is USD 2.36616881 and remains
  part of the global program accounting.
