# Open 10,000 factual-QA reviewer calibration 004 — build

Result ID: `academic-factual-qa-open-10000-reviewer-calibration-004-build`

Decision: **Go Deeper to one separately authorized 40-control calibration**

Revision `cb2781f` implements the method-level successor to the two invalid
checkpoint-003 attempts. GPT-5.4 now returns only the atomic action,
answerability, claim-support, citation-support, ambiguity, boundary, evidence,
and normalized defect judgments. The provider schema no longer contains
`case_semantically_valid`; the harness derives that value as true if and only if
the normalized defect set is empty.

The immutable 40-control packet, hidden labels, four quality thresholds, exact
`gpt-5.4-2026-03-05` identity, direct Responses API, `store: false`, zero
retries, ten-call maximum, and USD 3 stop are unchanged. No vote from attempts
001 or 002 is imported, and their invalid ledgers remain preserved.

Network-free pass, quality-failure, and malformed-output simulations all reach
their expected terminal states. Focused tests verify that the provider cannot
return the harness-owned overall-validity field, the deterministic derivation
is stable, configuration changes do not leak into the historical runner, and
the build-only preflight remains blocked by the repository freeze and false
authorization flags.

This build supplies no reviewer-quality or Digital Twin product result. It made
zero provider calls, opened no hidden label, and cannot progress into wording,
the 500 candidate cases, 100 controls, or the final 10,000 cases. Paid execution
requires a fresh metadata check, a clean live preflight, and explicit authority
for calibration 004 only.
