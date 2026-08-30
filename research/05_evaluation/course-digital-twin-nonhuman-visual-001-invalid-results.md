# Nonhuman visual supplement attempt 001 — invalid execution

Attempt 001 produced no visual-quality result. The preflight passed and the first public synthetic table image was transmitted, but OpenAI rejected the response schema before inference because `uniqueItems` is unsupported by the selected structured-output subset.

The ledger records one failed request, zero completed responses, zero reported tokens, zero cost, and no private or participant data. This is an operational schema defect, not evidence that the visual method is good or poor.

## Decision

Refine once by removing only the unsupported provider-side keyword while preserving deterministic uniqueness validation. Attempt 002 keeps the same 30 assets, 60 cases, model, questions, gold, lineage checks, gates, and budget. A further operational failure stops the visual branch.

The visual supplement remains separate from the main text/OCR factual evaluation and cannot block or substantiate the R1 text-first product claim.
