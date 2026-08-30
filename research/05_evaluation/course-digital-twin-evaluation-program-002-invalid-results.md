# API-first finite program 002 invalid result

## Outcome

`course-digital-twin-evaluation-program-002` terminated as
`invalid-execution` in retrieval setup. Four public-course API embedding
indexes and 500 query vectors were materialized, but the cached query embedder
carried a 50,000-token request limit while the persisted index binding required
250,000. The exact binding check correctly stopped execution before retrieval
scoring.

The ignored ledgers contain 44 embedding batches and USD 0.00755274 reported
cost. No product response, hidden-gold score, final-set case, private source, or
human data was opened.

## Decision

Classify the run as operationally invalid and preserve the paid index artifacts
for a hash-bound harness-only successor. This result supports no retrieval or
product-quality conclusion.

## Limitations

- The program ledger initially omitted embedding-batch usage during exception
  accounting; the durable batch ledgers provide the corrected 44-call total.
- No factual, visual, profile, T0/T1, or 10,000-case claim follows from this run.
- Raw provider and vector artifacts remain local and ignored.
