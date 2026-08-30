# Nonhuman visual supplement attempt 002 — invalid execution

The final corrective visual attempt completed all 30 exact-model calls with zero retries. It used 54,749 input tokens and 12,014 output tokens at a reported cost of USD 0.0259673.

Deterministic post-validation found repeated values in uniqueness-constrained semantic lists for three assets. Because that contract was frozen before execution, the responses were not normalized after seeing them and retrieval quality was not scored.

## Decision

Stop the visual branch. Attempt 002 is `invalid-execution`, not an unfavorable visual-quality estimate, and there will be no third attempt in this program.

This result has no effect on the main text/OCR factual evaluation. The 30-asset/60-case visual supplement is a separate system-path check and could only ever support `Go Deeper`, not a general multimodal product claim.
