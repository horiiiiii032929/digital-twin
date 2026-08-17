# Course-tutor hybrid authoring review v5 plan

Plan ID: `course-tutor-hybrid-authoring-review-v5`

Date frozen: 2026-08-14

Status: prospective; frozen before any v5 provider or private model call.

## Decision question

Can the unchanged 152-case private course-tutor draft complete the v4
cross-provider review after correcting transient API-error classification,
while retaining the newest DeepSeek V4 Pro model and a maximum 48-case human
packet?

V1 through v4 remain invalid and preserved. No prior judgment is reused.

## Candidate and immutable boundary

- Candidate: private draft 004, version `course-tutor-v1.2.3`.
- Development dataset/conditions SHA-256:
  `a582ea6806846ceda919a956946edbcbeae7692c5ee199d20d4e9e46a745d018` /
  `b370fd01be047da78435a6cacac874850a6c32a116747714bdfae690cdfddbda`.
- Held-out dataset/conditions SHA-256:
  `c0aad4979e25de24cb8d0a99f876a47576a534d65257123f95b4edfcb3f000a2` /
  `3e855d5f92c903630400d9a2d171e1e29a58b3cb772dbfdc60384ea2dc928bf6`.
- Cases: 48 development and 104 held-out authoring cases; 19 in each of
  eight scenarios.
- No tutor output, hidden condition mapping, seal, or held-out execution
  ledger may be created or opened.
- Gemma is excluded and cannot be used as a fallback.

The authorized external payload and exclusions are unchanged from v4. The
permission continuation is recorded in
`research/03_data/academics-source-permission.md`. No real student/participant
data, solutions, graded answers, credentials, environment values, tutor
outputs, other model verdicts, or human decisions are sent.

## Frozen committee

| Reviewer | Model/family | Revision/digest | Mode |
| --- | --- | --- | --- |
| `deepseek-v4-pro-reviewer-v5` | Official `deepseek-v4-pro` / DeepSeek V4 | Documented `DeepSeek-V4-Pro-0813`; bind one stress-probe fingerprint | thinking `high` |
| `local-qwen3-4b-reviewer-v5` | `qwen3:4b` / Qwen 3 | `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` | thinking disabled |
| `local-huihui-qwen3-4b-reviewer-v5` | `huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0` / Qwen derivative | `f5046078f1f6b4dc2ad23265d7d9e616aeb77088bc9092623b2f3f056f7b19d4` | thinking disabled |

DeepSeek uses the official OpenAI-compatible Chat Completions endpoint through
the current OpenAI Python client with SDK retries disabled, strict JSON mode,
4,096 maximum output tokens, a non-personal `user_id`, and a 300-second request
timeout. Official model, thinking, JSON, and pricing references remain:
<https://api-docs.deepseek.com/updates/>,
<https://api-docs.deepseek.com/guides/thinking_mode/>,
<https://api-docs.deepseek.com/guides/json_mode/>, and
<https://api-docs.deepseek.com/quick_start/pricing/>.

## Public transport gate

Before private data, DeepSeek must complete ten public synthetic probes. At
least nine must return valid exact-schema decisions; every completed response
must return `deepseek-v4-pro` and one unchanged non-empty fingerprint. Both
local models must pass one public exact-schema probe with their frozen digest.
Authentication/configuration/model/fingerprint failure or a failed stress gate
stops the run.

## Private attempt rule

Each private DeepSeek case receives at most two attempts. A valid approve or
revise is final. One second attempt is allowed only after:

- empty content;
- malformed or schema-invalid JSON;
- `APITimeoutError`; or
- `APIConnectionError` without an authentication/configuration response.

Authentication, permission, bad-request/configuration, model mismatch,
fingerprint omission, and fingerprint drift are hard stops. Every attempt is
checkpointed before another request. If both allowed attempts fail, the final
case is invalid and enters the human set. Ten probes plus 304 private attempts
produce a hard maximum of 314 requests. Conservative cumulative cost must stay
below USD 2.

## Review and two-family quorum

The exact v4 prompt and six checks remain fixed: authentic synthetic question,
correct expected behavior, atomic/correct claims, supporting evidence,
permission/version correctness, and acceptable split assignment. Approve is
valid only with six true checks. Scenario-specific no-evidence,
assessed-work, ambiguity, and multi-evidence rules are unchanged.

Outside the human set, a case requires both:

- valid DeepSeek approve; and
- at least one valid local Qwen-family approve.

A single local artifact dissent does not override approval from both base
families. DeepSeek non-approval or the absence of every local approval
escalates. All three records and every dissent remain inspectable.

## Human audit and stop rules

Sample seed: `course-tutor-hybrid-human-sample-v5`

The blinded human set is the union of:

- one stable case from every scenario-by-split stratum (16 cases);
- all 19 no-evidence cases;
- every DeepSeek revise/invalid/missing case; and
- every case without at least one valid local approve.

The baseline and no-evidence census overlap in two cases, producing a 33-case
minimum. The maximum is 48. The runner stops immediately if the DeepSeek-stage
lower bound or final union exceeds 48. The human packet hides selection reasons
and all model decisions/reasons and requires all six checks, decision, notes,
identity/role, timezone-aware timestamp, and blinding confirmation.

Qualification requires the public gate, all 456 final decision records, every
underlying attempt, stable DeepSeek identity, request/cost compliance, the
two-family quorum outside the human set, and human approval of every selected
case. GitHub Support must also confirm removal of public commit `02dbf8d`
before sealing.

The allowed claim remains: cross-provider, two-family model review with
targeted independent-human validation. It is not full human or professor
approval.

## Measurements and reproduction

Record public-probe validity; attempt/retry status and failure class; model,
fingerprint, token, latency, and cost traces; final decisions by reviewer,
scenario, and split; two-family approval and dissent; human selection reasons;
code revision/dirty state; candidate hashes; and unopened tutor-output
boundaries.

Run sequence:

1. validate authorization, hashes, schemas, corpus permissions, and split
   isolation;
2. run ten DeepSeek and two local public probes;
3. run all 456 decisions with per-attempt checkpoints and one bounded repair;
4. apply the two-family quorum and render the blinded packet only if at most
   48 cases remain;
5. stop for the independent human audit;
6. validate model and human records together; and
7. seal only after the GitHub purge confirmation, leaving tutor held-out
   outputs unopened until later gates authorize execution.
