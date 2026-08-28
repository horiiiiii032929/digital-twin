# Product checkpoint 005 — attempt 001

Result ID: `academic-factual-qa-open-10000-development-product-checkpoint-005-attempt-001-invalid`

Decision: **Invalid execution / correct only the retrieval runtime invocation**

The authorized checkpoint started from clean revision `2a1215c`. It stopped in
the candidate stage before the first provider call because the package command
did not install the locked `retrieval-benchmark` optional dependency required
by the selected local Qwen3 embedding retriever.

This is an execution-environment defect, not a product-quality result. The
provider ledger contains zero calls, zero tokens, and zero cost. No product
response was persisted, hidden gold remained sealed, the control and advisory
stages did not open, and the final 10,000-case split remained unauthorized.

The ignored attempt artifacts are preserved with these hashes:

- terminal state: `39fdc2d8f2f0d2a95396e3bf1d7cfea1b3a515bdb8fac3c280b3e86717695da5`;
- zero-call provider ledger: `03e4038e0f092d49ca9132f9bf684e9694939ecebe301c92066d29257d8b5180`;
- initialized local product state: `002f8679f184c82265bf4f84380f16725eea06b974b3acd5b66d2bbad932392d`.

The single permitted harness-only correction adds the already locked
`retrieval-benchmark` extra to the preflight, execute, and resume commands. It
does not change the cases, wording, retriever, generator, evidence gate,
deterministic metrics, budget, or model bindings. The corrective attempt uses
fresh exclusive outputs and a new code revision.
