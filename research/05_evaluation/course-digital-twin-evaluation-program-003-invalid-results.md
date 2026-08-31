# API-first finite program 003 invalid result

## Outcome

`course-digital-twin-evaluation-program-003` reused the immutable program-002
document indexes and corrected the cached-query binding. All 500 query vectors
completed in eight batches. The first optional GPT-5.4 nano reranking request
then returned a non-completed Responses API result. The automatic correction
reproduced the same operational stop from the interrupted ledger.

The run made nine calls and cost USD 0.00016134. It produced no retrieval
quality estimate, product response, hidden-gold score, or final-set access.

## Decision

Classify the run as operationally invalid. Exclude the unstable optional nano
candidate prospectively and compare only BM25, API hybrid, and deterministic
hierarchical retrieval under unchanged cases, truth, and quality gates.

## Limitations

- The provider transport did not persist the full incomplete response, so the
  provider-side incomplete reason is unavailable.
- The nano failure is operational evidence, not a quality estimate.
- Raw provider and vector artifacts remain local and ignored.
