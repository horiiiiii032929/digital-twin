# Open 10,000 factual-QA development checkpoint 003 — attempt 001

Result ID: `academic-factual-qa-open-10000-development-checkpoint-003-attempt-001-invalid`

Decision: **Invalid execution / correct the reviewer schema contract**

The authorized run started from clean revision `b076e32`. GPT-5.4 completed
the first four-control calibration batch with the exact
`gpt-5.4-2026-03-05` identity. The ledger records one call, 2,147 input tokens,
530 output tokens, 5.973 seconds latency, and USD 0.0133175 reported cost.

The response satisfied the provider-side JSON schema, but used detailed defect
labels such as `invalid-visible-source-id` and `unsupported-claim`. The local
post-parser accepted only the normalized labels `action`, `ambiguity`,
`boundary`, `citation`, and `claim`. Because the provider schema had failed to
declare that enum, the two validation layers contradicted each other and the
runner stopped after the first completed call.

This is a harness defect, not a reviewer-quality result. No hidden labels were
opened, no wording or product call occurred, and the 500 candidate, 100 control,
and final 10,000 cases remained closed. The invalid ledger is preserved at
`reports/generated/academic-factual-qa-open-10000-openai-reviewer-calibration-001.sqlite3`
with SHA-256
`8407e95ca41f995034bcdca62cf43bb6c67f79bf0417e94c7fcf3a6192252d20`.

The prospective correction constrains the provider schema and prompt to the
same five normalized labels and uses a fresh calibration and checkpoint ledger.
No provider retry or result overwrite is permitted.
