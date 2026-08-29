# Product checkpoint 007 — attempt 001

Result ID: `academic-factual-qa-open-10000-development-product-checkpoint-007-attempt-001-invalid`

Decision: **Invalid execution / apply the sole harness-only correction**

The authorized checkpoint started from clean revision `2b8851c`. Its committed
top-level preflight was ready. The nested candidate-stage preflight nevertheless
stopped before case 1 because it still compared the checkpoint's frozen
`openai-gpt-5.4-mini-live-extractive-boundary` generator identity with the
historical product runner's `openai-gpt-5.4-mini-live-atomic` constant.

This is a harness-binding mismatch, not a product-quality result. No provider or
response ledger was created, so provider calls, responses, tokens, and cost are
all zero. Hidden gold remained sealed; control, scoring, advisory, and final
stages did not open. The final 10,000-case execution remained unauthorized.

The ignored terminal state is preserved as
`academic-factual-qa-open-10000-development-product-checkpoint-007-attempt-001-invalid-state.json`
with SHA-256
`43451b78d65b5173f57a8ee39769e8bc530dae5d5ebed0e95175276fe7f7efbd`.

AFQC-076 binds only the nested preflight to the generator identity already
frozen in checkpoint 007's two system manifests. It does not change any case,
gold label, source, wording, retrieval artifact, prompt, product method, model,
budget, or quality gate. The corrective execution uses fresh exclusive outputs.
A further harness correction is not authorized.
