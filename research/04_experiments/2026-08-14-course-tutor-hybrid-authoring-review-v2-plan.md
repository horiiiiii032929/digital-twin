# Course-tutor hybrid authoring review v2 plan

Plan ID: `course-tutor-hybrid-authoring-review-v2`

Date frozen: 2026-08-14

Status: invalid and stopped after 146/456 private judgments; superseded by
`course-tutor-hybrid-authoring-review-v3`. No human packet, seal, held-out
ledger, or tutor output was created.

The repository owner changed the eligible-reviewer requirement after the run
started and explicitly excluded Gemma. The process was stopped before the
second reviewer began, and its checkpoint was preserved as
`course-tutor-hybrid-authoring-review-v2-attempt-001-invalid`. DeepSeek was not
called and no provider was mixed into this frozen local protocol.

## Decision question

Can the unchanged 152-case private course-tutor draft be qualified through a
reproducible local three-model review and a bounded independent-human audit
after correcting the v1 transport and workload-design failures?

V1 remains an invalid preserved result. It stopped after 172/456 records when
the minimum required-human set reached 66, above its frozen ceiling of 48.
This plan changes reviewer transport and sampling only. It does not reinterpret
the v1 records, change the candidate, or authorize tutor-output generation.

## Candidate and boundary

- Candidate: private draft 004, version `course-tutor-v1.2.3`.
- Development dataset SHA-256:
  `a582ea6806846ceda919a956946edbcbeae7692c5ee199d20d4e9e46a745d018`.
- Development conditions SHA-256:
  `b370fd01be047da78435a6cacac874850a6c32a116747714bdfae690cdfddbda`.
- Held-out dataset SHA-256:
  `c0aad4979e25de24cb8d0a99f876a47576a534d65257123f95b4edfcb3f000a2`.
- Held-out conditions SHA-256:
  `3e855d5f92c903630400d9a2d171e1e29a58b3cb772dbfdc60384ea2dc928bf6`.
- Cases: 48 development and 104 held-out authoring cases, with 19 cases in
  each of eight scenarios.
- Private course text and per-case judgments remain ignored local artifacts.
- No tutor output, blinded condition mapping, seal, or held-out execution
  ledger may be opened or created.
- No external provider call is allowed. DeepSeek remains unauthorized for
  judge use.

## Frozen local reviewers and transport

| Reviewer | Model | Family | Digest | Thinking |
| --- | --- | --- | --- | --- |
| `local-gemma3-4b-reviewer-v2` | `gemma3:4b` | Gemma 3 | `a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a` | disabled |
| `local-qwen3-4b-reviewer-v2` | `qwen3:4b` | Qwen 3 | `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` | disabled |
| `local-huihui-qwen3-4b-reviewer-v2` | `huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0` | Qwen 3 derivative | `f5046078f1f6b4dc2ad23265d7d9e616aeb77088bc9092623b2f3f056f7b19d4` | disabled |

The Ollama request must set top-level `think: false`. Before any private case
request, every binding must pass one public synthetic transport preflight with
the exact six-check JSON schema. Any failed preflight stops the run. Private
case calls receive no retries; malformed or missing responses remain invalid.

Three artifacts still represent only two base-model families. Agreement is
triage evidence, not independent proof, and the human audit remains required.

## Six authoring checks

Every model returns approve/revise, all six booleans, and a concrete reason:

1. question authentic and synthetic;
2. expected behavior correct;
3. claims atomic and correct;
4. evidence supports claims;
5. permission and version correct; and
6. split assignment acceptable.

Approve is valid only when all six booleans are true. For ambiguity,
assessed-work, and no-evidence cases, intentionally absent positive factual
claims and authored evidence do not fail the claim/evidence checks by
themselves. The expected non-answer or bounded-support behavior must still be
correct.

Every no-evidence case receives the eight nearest approved corpus passages
from the same deterministic lexical search used in v1. The model's check is
bounded: none of those supplied passages may directly answer the question.
The reviewer must not fail solely because eight lexical neighbors cannot prove
corpus-wide semantic absence. All 19 no-evidence cases are independently human
reviewed regardless of model verdict.

For multi-evidence cases, every claim and exact passage is supplied. Evidence
support passes only when each passage supports its mapped claim and both are
necessary for the complete expected answer.

## Human audit contract

Sample seed: `course-tutor-hybrid-human-sample-v2`

Before reading v2 model verdicts, select one stable-hash case from each
scenario-by-split stratum. Eight scenarios across both splits produce a
16-case baseline: eight development and eight held-out cases.

The required human set is the union of:

- the frozen 16-case baseline;
- all 19 no-evidence cases;
- every case with reviewer disagreement;
- every case receiving at least one `revise` verdict; and
- every case with an invalid or missing model decision.

The baseline and no-evidence census overlap in two cases, so 33 cases require
human review before model escalations. The hard ceiling remains 48. If the
union exceeds 48, stop and refine again rather than transferring the workload.

The human packet hides baseline membership, escalation membership, all model
verdicts, and all model reasons. It contains only the selected cases and exact
review evidence. The template binds the hidden selection with a SHA-256
commitment. The reviewer records all six checks, approve/revise, notes,
identity, role, a timezone-aware timestamp, and confirmation that model
decisions were not inspected.

## Qualification and stop rules

- All three public transport preflights must pass.
- All 456 private reviewer-case records must be present.
- Zero external calls are permitted.
- The required human set must contain at most 48 cases.
- Every case outside the human set requires unanimous three-model approval.
- Every human-audited case requires six true checks and approve.
- Any human defect blocks sealing, requires a revised candidate, preserves the
  unfavorable result, and starts a fresh prospective review version.
- GitHub Support must confirm removal of superseded public commit `02dbf8d`
  before a seal can be created.

With zero failures in the 16-case random baseline, the simple rule-of-three
upper 95% bound is approximately 18.8%. That bound applies only to the random
baseline and is not a guarantee for unsampled cases. The all-19 no-evidence
census and model escalations are targeted coverage, not random-sample size.

The allowed claim remains: local multi-model cross-review with targeted
independent-human validation. Full human approval and professor validation are
not allowed claims.

## Measurements

- transport-preflight validity and latency by reviewer;
- all private valid/invalid decisions and latency/token counts by reviewer;
- unanimous approvals/revisions and disagreements;
- per-check, split, and scenario slices;
- baseline, no-evidence census, escalated, and total human counts;
- human defects by check, split, and scenario;
- exact model, digest, thinking mode, prompt, seed, dataset, conditions, code
  revision, and dirty state; and
- zero-external-call and unopened-held-out boundary confirmation.

## Reproducibility sequence

1. Validate unchanged draft hashes, schemas, permissions, and split isolation.
2. Verify local model digests and run all three public synthetic preflights.
3. Run all 456 private local decisions without retries.
4. Generate the blinded 16-plus-no-evidence-plus-escalations human packet.
5. Complete the independent-human audit without inspecting model records.
6. Validate ensemble and human decisions together.
7. After GitHub purge confirmation, create the immutable seal.
8. Run development only; keep held-out tutor outputs unopened until every later
   prospective gate passes.
