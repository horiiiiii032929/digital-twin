# Action-router product checkpoint — attempt 001

Result ID: `academic-factual-qa-action-router-product-checkpoint-001-attempt-001-invalid`

Decision: **Invalid execution / sole harness-only correction**

The authorized checkpoint started from clean revision `f9f2827`. It stopped
before provider I/O because the frozen OpenAI embedding batch size was 128,
while `OpenAITextEmbedder` enforces a maximum of 64. No output directory,
response ledger, hidden-gold score, provider response, token, or cost was
created.

This is an operational harness defect and supports no product-quality
interpretation. The public cases, hidden gold, retrieval method, action router,
prompt, generation model, quality gates, 620-call limit, and USD 8 emergency
ceiling remain unchanged.

The one preregistered harness correction sets the embedding batch size to 64.
At 300 source atoms plus 500 query vectors split by course, the corrected
configuration remains within the frozen 20 embedding-call ceiling. Attempt 002
is the final permitted execution attempt; another invalid execution stops the
checkpoint.
