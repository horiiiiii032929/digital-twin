# Course-tutor hybrid authoring review v3 plan

Plan ID: `course-tutor-hybrid-authoring-review-v3`

Date frozen: 2026-08-14

Status: prospective; frozen before any v3 model preflight or private case
judgment.

## Decision question

Can the unchanged 152-case private course-tutor draft be qualified through a
cross-provider three-model review led by the newest official DeepSeek V4 Pro
model and a bounded independent-human audit, with Gemma excluded?

V1 and v2 remain invalid preserved attempts. Their judgments are not reused,
and this plan does not reinterpret them or authorize tutor-output generation.

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
- Gemma is excluded from the v3 committee and cannot be used as a fallback.

## Authorization and external-data boundary

The repository owner explicitly authorized this DeepSeek judge use on
2026-08-14. The bounded amendment is recorded in
`research/03_data/academics-source-permission.md`.

DeepSeek receives only the synthetic student question/state, authored expected
behavior, atomic claims, exact approved evidence passages and metadata, and,
for no-evidence cases, eight deterministic nearest approved passages. No real
student data, participant data, solutions, credentials, environment values,
tutor outputs, hidden condition mapping, model verdict from another reviewer,
or human decision is sent.

The official endpoint is `https://api.deepseek.com`. The run uses a
non-personal `user_id`, permits at most 153 external requests (one public
synthetic preflight plus 152 private case judgments), and has a cumulative USD
2 hard stop. There are no retries. Each response records input/output tokens,
latency, approximate cost, returned model, and returned system fingerprint.

DeepSeek's retention/training boundary remains a known limitation: the project
has no provider-specific no-training agreement. Authorization is limited to
this authoring review and does not permit general judging, student-facing use,
public deployment, or professor-approval claims.

## Frozen reviewers and transport

| Reviewer | Model binding | Family | Revision/digest | Thinking |
| --- | --- | --- | --- | --- |
| `deepseek-v4-pro-reviewer-v3` | LiteLLM `deepseek/deepseek-v4-pro`; provider `deepseek-v4-pro` | DeepSeek V4 | Official documented `DeepSeek-V4-Pro-0813`; bind the non-empty preflight system fingerprint for all private calls | enabled, `high` |
| `local-qwen3-4b-reviewer-v3` | `qwen3:4b` | Qwen 3 | `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` | disabled |
| `local-huihui-qwen3-4b-reviewer-v3` | `huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0` | Qwen 3 derivative | `f5046078f1f6b4dc2ad23265d7d9e616aeb77088bc9092623b2f3f056f7b19d4` | disabled |

DeepSeek's official changelog names `deepseek-v4-pro` as the current GA model
and its model table identifies the served revision as `DeepSeek-V4-Pro-0813`:
<https://api-docs.deepseek.com/updates/> and
<https://api-docs.deepseek.com/quick_start/pricing/>. The OpenAI-compatible
request enables thinking with effort `high`, uses JSON mode, and omits sampling
parameters that thinking mode ignores. The prompt contains the word JSON and
an exact schema example as required by the official JSON-output guide:
<https://api-docs.deepseek.com/guides/thinking_mode/> and
<https://api-docs.deepseek.com/guides/json_mode/>.

Before private requests, each binding must pass one public synthetic transport
preflight with the exact six-check JSON schema. DeepSeek's preflight must return
`deepseek-v4-pro` and a non-empty system fingerprint; that fingerprint becomes
the immutable private-run binding. Any failed preflight stops the run. Private
calls receive no retries; empty, malformed, mismatched-model, or
mismatched-fingerprint responses remain invalid. Any external cost at or above
USD 2 stops further requests and invalidates the incomplete run.

The three reviewers represent only two base-model families because both local
reviewers are Qwen-related. Agreement is triage evidence, not independent
proof, and the human audit remains mandatory.

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
from the same deterministic lexical search used in v2. The model's check is
bounded: none of those supplied passages may directly answer the question.
The reviewer must not fail solely because eight lexical neighbors cannot prove
corpus-wide semantic absence. All 19 no-evidence cases are independently human
reviewed regardless of model verdict.

For multi-evidence cases, every claim and exact passage is supplied. Evidence
support passes only when each passage supports its mapped claim and both are
necessary for the complete expected answer.

## Human audit contract

Sample seed: `course-tutor-hybrid-human-sample-v3`

Before reading v3 model verdicts, select one stable-hash case from each
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
- DeepSeek must have exactly one preflight and 152 no-retry private judgments,
  with one unchanged returned model and fingerprint.
- External cost must remain below USD 2.
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

The allowed claim is: cross-provider multi-model review with targeted
independent-human validation. Full human approval and professor validation are
not allowed claims.

## Measurements

- transport-preflight validity and latency by reviewer;
- all private valid/invalid decisions and latency/token counts by reviewer;
- DeepSeek returned model, fingerprint, token use, request count, and cost;
- unanimous approvals/revisions and disagreements;
- per-check, split, and scenario slices;
- baseline, no-evidence census, escalated, and total human counts;
- human defects by check, split, and scenario;
- exact model, digest or provider revision, thinking mode, prompt, seed,
  dataset, conditions, code revision, and dirty state; and
- unopened-held-out boundary confirmation.

## Reproducibility sequence

1. Validate unchanged draft hashes, schemas, permission amendment, and split
   isolation.
2. Verify local model digests and run all three public synthetic preflights.
3. Bind the DeepSeek preflight fingerprint and run all 456 private decisions
   without retries.
4. Generate the blinded 16-plus-no-evidence-plus-escalations human packet.
5. Complete the independent-human audit without inspecting model records.
6. Validate ensemble and human decisions together.
7. After GitHub purge confirmation, create the immutable seal.
8. Run development only; keep held-out tutor outputs unopened until every later
   prospective gate passes.
