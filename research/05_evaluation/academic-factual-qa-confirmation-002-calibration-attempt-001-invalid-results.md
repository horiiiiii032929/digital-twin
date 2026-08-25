# Academic factual-QA confirmation 002 calibration — attempt 001

Result ID: `academic-factual-qa-confirmation-002-calibration-attempt-001-invalid`

Decision: **Invalid execution / Refine harness**

The clean, frozen calibration started from revision `042c6fd`. The isolated
`gpt-5.6-sol` reviewer completed all 40 blinded controls and passed action
accuracy, mutation sensitivity, specificity, and citation-defect sensitivity
at 1.00. The first four-item Mistral Small 4 batch then terminated at the
strict transport/parser boundary. Zero retries were attempted, no DeepSeek
inference was started, and the 200 confirmation cases remained unopened.

This is not a reviewer-quality or method result. The ledger records one failed
provider call and one malformed-response outcome, but the attempt is invalid
because it retained only the exception class. HTTP/provider error detail,
request identity, returned usage, and cost were not available after failure.
The ledger's reported USD 0 therefore means **unaccounted**, not verified
zero spend.

The ignored atomic ledger is recorded at
`reports/generated/academic-factual-qa-confirmation-002-panel-ledger.json`
with SHA-256
`c9ca95267379e5c0cd52c946ffb9e09c2c4af05e3d2d6077f05bbb5d67b34718`.
The ignored Codex calibration artifact has SHA-256
`66fef07f72c25c0b49e2ef658792ca7be238dc8349da33376e40a0acefa94593`.
Neither artifact contains private course or student data.

Correction: revoke attempt 001, preserve its artifacts, add sanitized provider
error and usage accounting plus an exclusive successor output, and require a
new bounded authorization before one corrective calibration attempt. Do not
tune reviewers or infer factual-QA quality from this run.
