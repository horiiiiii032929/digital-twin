# Independent reference-question validation build result

## Outcome

`Go Deeper` to one separately authorized reference-question validation run.
This is build-only evidence: it does not establish question quality, product
quality, or readiness for the sealed 10,000-case evaluation.

## Method correction

Checkpoint 007 is preserved as invalid-reference evidence after direct audit
confirmed two ambiguous questions. Its diagnostic product rates cannot support
an academic conclusion.

The successor changes the validation method rather than tuning those questions:

- GPT-5.4 mini authors a question from public source evidence, the intended
  action, and a deterministic target.
- GPT-5.4 reviews the question with the same public source but without the
  expected action, canonical answer, required spans, or author rationale.
- The reviewer must independently recover the action and exact answer spans.
- Deterministic code compares those recovered values with pinned gold and
  rejects ambiguity, mismatch, leakage, malformed output, and duplicates.
- Only complete five-question clusters may satisfy the exact course and
  modality quotas. No fallback or quota relaxation is allowed.

## Fresh validation pool

- 160 source-disjoint candidate clusters and 800 cases are constructed from
  fresh complete regions outside checkpoint 007 and the sealed final split.
- A passing run must select exactly 100 complete clusters and 500 cases.
- The frozen allocation is balanced across the four source families and the
  text, code, table, and equation modalities.
- The pool and allocation are byte-stable under the recorded source-plan hash.

## Bounded execution contract

- Forty author batches and forty target-blind reviewer batches.
- Maximum 80 direct OpenAI calls, zero retries, and a USD 12 emergency stop.
- Exact dated model identities, strict structured output, `store: false`,
  atomic SQLite checkpoints, and exclusive output creation.
- Product calls, hidden-gold product scoring, and the sealed 10,000-case split
  remain outside this checkpoint.

## Verification

- Six focused regression tests pass.
- The network-free simulation selects exactly 100 clusters and 500 cases from
  all 800 synthetic responses with no quota shortfall.
- Repository correctness covers all tracked execution-relevant files and the
  execution freeze protects every registered provider-capable entry point.
- No provider call, token use, paid cost, private-data read, or final-set access
  occurred.

## Next action

Request explicit authorization for
`academic-factual-qa-open-10000-reference-question-validation-001`.

A pass materializes a fresh 500-case reference-validated development package
and permits preparation—not automatic execution—of one new 500+100 product
confirmation. A valid quality failure is published and stops this method.
