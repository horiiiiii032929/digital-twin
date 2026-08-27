# Academic factual-QA confirmation 002 calibration — attempt 002

Result ID: `academic-factual-qa-confirmation-002-calibration-attempt-002-invalid`

Decision: **Invalid execution / Redesign reviewer method**

The clean, frozen corrective calibration started from revision `d79bda5`. It
reused the immutable isolated-Codex artifact that had completed all 40 blinded
controls and passed action accuracy, mutation sensitivity, specificity, and
citation-defect sensitivity at 1.00. The first four-item Mistral Small 4 batch
then returned HTTP 400 before any provider vote was accepted. Zero retries were
attempted, DeepSeek was not called, and the 200 confirmation cases remained
unopened.

This is an operationally invalid execution, not a reviewer-quality, factual-QA,
or product result. The corrected ledger preserves the HTTP status, sanitized
provider category, latency, affected item IDs, and the fact that usage and cost
were unavailable on the provider error path. Its reported USD 0 therefore means
**unavailable provider accounting**, not verified zero spend.

The ignored exclusive ledger is recorded at
`reports/generated/academic-factual-qa-confirmation-002-calibration-attempt-002-ledger.json`
with SHA-256
`988c216ea5ce2958f225f031f2eb5c9723b826b151e290b59b28571fdc8fe53a`.
The reused ignored Codex calibration artifact has SHA-256
`66fef07f72c25c0b49e2ef658792ca7be238dc8349da33376e40a0acefa94593`.
Neither artifact contains private course or student data.

Attempt 002 confirms that the exact Mistral route is operationally unsuitable
for this frozen structured-review protocol after two independent one-call
terminations. Revoke all execution authority and redesign the reviewer method
before any new calibration. Do not retry Mistral automatically, substitute a
reviewer silently, open the 200-case panel, or infer product quality from this
attempt.
