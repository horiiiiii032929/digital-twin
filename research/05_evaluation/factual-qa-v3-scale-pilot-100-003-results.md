# Factual-QA v3 scale pilot 100 attempt 003 results

## Technical summary

The paid confirmation completed safely with a **Keep** decision. All 100 model
question variants were accepted while deterministic code retained authority over
actions, answers, claims, citation quotes, and boundary lineage. All 100 cases
passed deterministic checks, all 80 answerable cases had valid and complete
citations, all 20 boundary actions were correct, and all 20 planted citation
mutations were rejected.

The independent reviewer accepted 99/100 cases. Its single rejection claimed a
citation omitted a trailing period even though the stored quote included that
period. Deterministic comparison, the bounded dispute review, and direct case
inspection all confirmed the case was valid. All predefined machine gates
passed.

## Run identity

- Result ID: `factual-qa-v3-scale-pilot-100-003`
- Execution revision: `f1301c029351296bafbef0464791b220cd2becbb`, clean worktree
- Date: 2026-08-22
- Instrument SHA-256: `ac210b0b34691abfe694c035d9ef1e6efd95d37eae9aa3eca2bdf40711242139`
- Truth artifact SHA-256: `1b4bd3febd79ce828300b42cc23b379de85f7bf92fa07fe8493f22d56e7f5c8c`
- Runner SHA-256: `1d59d608d6edc45b60c6ece6ac2b95d8d2e9af40bc1069ebeb9a55aa49358326`
- Ignored raw output: `reports/generated/factual-qa-v3-scale-pilot-100-003.json`, SHA-256 `55b690e9551fe20a8b46cecca6b290b4bcc70c1ae4cfdab3e677b2f3e51cceb4`
- Sanitized summary: [factual-qa-v3-scale-pilot-100-003-summary.json](judgments/factual-qa-v3-scale-pilot-100-003-summary.json)
- Priority cross-review: [factual-qa-v3-scale-pilot-100-003-priority-review-001.json](judgments/factual-qa-v3-scale-pilot-100-003-priority-review-001.json)
- Data boundary: deterministic synthetic-public only; zero private-data calls

## Results

| Metric | Result | Outcome |
| --- | ---: | --- |
| Provider responses | 223/223 | Pass |
| External cost | USD 0.085406 | Pass |
| Input / output tokens | 376,037 / 19,863 | Recorded |
| Token-limit violations | 0 | Pass |
| P95 latency | 1.95 seconds | Diagnostic |
| Accepted question variants | 100/100 | Pass |
| Deterministic-valid cases | 100/100 | Pass |
| Citation and target-claim validity | 80/80 answerable cases | Pass |
| Boundary action accuracy | 20/20 | Pass |
| Reviewer agreement | 99/100 | Pass |
| Mutation sensitivity | 20/20 | Pass |
| Unresolved disputes | 0/100 | Pass |
| Exact duplicate-question rate | 0/100 | Pass |
| Malformed outcomes | 0/221 bulk outcomes | Pass |
| Priority cross-review | 12/12 retained | Supports Keep |

The 223 calls were 101 DeepSeek V4 Flash author/canary calls, 121 Mistral
Small 4 review/canary/mutation calls, and one bounded DeepSeek V4 Pro dispute.
Exact model identities remained stable and the USD 3 emergency stop was never
approached.

## Direct cross-review

Codex directly inspected all 12 priority cases and retained all 12. The packet
contained the one model disagreement, five academic-integrity refusals, five
ambiguity clarifications, and one direct code-slice control. Actions, question
wording, answers, claims, and citations were mutually consistent in every case.
No case required user adjudication.

## Limitations

- The corpus is deterministic synthetic-public dummy material. This validates
  orchestration and truth preservation, not real-course factual coverage.
- The run tests question wording around deterministic answers; it does not test
  product retrieval, Professor Digital Twin fidelity, or student learning.
- Twelve near-duplicate template groups remain as a diagnostic of the
  deliberately structured corpus, although there were no exact duplicate
  questions.
- LiteLLM emitted repeated provider-help diagnostic lines to the local console.
  They contained no fixture or credential content and did not affect calls or
  accounting, but should be suppressed before a larger execution.

## Decision and next gate

**Keep the deterministic source-linked truth method.** Pilot 003 authorization
is revoked. The result supports designing a separately bound 1,000-case
checkpoint, but does not authorize that checkpoint or the remaining 9,000
cases. A 1,000-case execution must retain exact source lineage, advisory-only
model review, duplicate and template-diversity diagnostics, complete accounting,
fresh provider verification, and its own explicit authorization.
