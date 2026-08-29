# Product checkpoint 006 — attempt 001

Result ID: `academic-factual-qa-open-10000-development-product-checkpoint-006-attempt-001-invalid`

Decision: **Invalid execution / apply the sole harness-only correction**

The authorized checkpoint started from clean revision `c0efd8c`. Its committed
top-level live preflight was ready, including the exact four immutable Qwen3
indexes and OpenAI binding. The nested candidate-stage preflight nevertheless
stopped before case 1 because the checkpoint instrument still labelled its
already reviewed allocation `frozen-build-only` rather than `frozen-approved`.

This is a harness-state mismatch, not a product-quality result. No provider
ledger or response ledger was created, so provider calls, responses, tokens,
and cost are all zero. Hidden gold remained sealed; control, scoring, advisory,
and final stages did not open. The final 10,000-case execution remained
unauthorized.

The ignored terminal state is preserved as
`academic-factual-qa-open-10000-development-product-checkpoint-006-attempt-001-state.json`
with SHA-256
`d0d00dfd57c962bc0d8fa200b562444bc3bc2629b0d166295bd055472d963091`.

AFQC-071 changes only the prospective allocation-state marker to
`frozen-approved`. It does not change any case, gold label, source, wording,
retrieval artifact, product method, model binding, budget, or quality gate. The
corrective execution uses fresh exclusive outputs. A further harness correction
is not authorized.
