# AFQC-101 source-aligned wording attempt 002

## Outcome

`completed-go-deeper`. The corrected transport completed all 50 calls and
produced a unique, truth-preserving public question package for all 500 cases.

## Results

- 148 questions use GPT-5.4 nano wording accepted by the separate GPT-5.6
  Terra semantic review and deterministic checks.
- 352 questions use an explicitly labelled, context-complete deterministic
  fallback.
- Zero normalized duplicates and zero mutations to actions, answers, claims,
  evidence, citations, source versions, or lineage.
- Two malformed author batches were quarantined: one duplicate-ID batch and
  one mismatched-ID-set batch. Their cases used deterministic fallbacks.
- 50/50 provider calls completed with zero retry or identity drift: 131,524
  input tokens, 87,049 output tokens, USD 0.8352885, and 23.760 seconds maximum
  observed latency.

## Interpretation

The package is suitable for the fresh retrieval confirmation because every
case remains bound to deterministic source truth and every rejected model
output has an inspectable fallback. The 70.4% fallback share is a limitation:
this stage establishes semantic safety and uniqueness, not natural-language
quality at population scale.

The next automatic stage is the preregistered multi-method retrieval
confirmation. No product, final 10,000-case, private-data, or human-participant
execution occurred here.

The unrestricted provider ledger remains ignored. The sanitized machine record
is [academic-factual-qa-source-aligned-wording-002.json](records/academic-factual-qa-source-aligned-wording-002.json).
