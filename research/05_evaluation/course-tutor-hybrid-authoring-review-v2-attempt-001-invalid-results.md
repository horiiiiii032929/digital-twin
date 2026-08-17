# Course-tutor hybrid authoring review v2 attempt 001 invalid results

Result ID: `course-tutor-hybrid-authoring-review-v2-attempt-001-invalid`

Date: 2026-08-14

Status: Invalid and stopped; 146/456 attempt records preserved; no human
packet, seal, held-out ledger, blinded mapping, or tutor output created.

Decision: Drop Gemma from this authoring-review workflow. Preserve this
incomplete attempt without treating its decisions as authoring-quality
evidence, authorize the official DeepSeek API for the bounded judge role, and
rerun prospectively under v3 with DeepSeek V4 Pro plus the two frozen local
Qwen reviewers.

## Boundary and bindings

- Plan: `course-tutor-hybrid-authoring-review-v2`.
- Candidate: unchanged private `course-tutor-v1.2.3` draft 004.
- Development dataset/conditions SHA-256:
  `a582ea6806846ceda919a956946edbcbeae7692c5ee199d20d4e9e46a745d018` /
  `b370fd01be047da78435a6cacac874850a6c32a116747714bdfae690cdfddbda`.
- Held-out dataset/conditions SHA-256:
  `c0aad4979e25de24cb8d0a99f876a47576a534d65257123f95b4edfcb3f000a2` /
  `3e855d5f92c903630400d9a2d171e1e29a58b3cb772dbfdc60384ea2dc928bf6`.
- Clean code revision:
  `5babaf3144fd50955e01c83724286d84159a8922`.
- External provider calls: 0.
- Private checkpoint SHA-256:
  `98c8db268f0151c63a055e20c3923c58bed5095315268c476d2426a8e218e1b1`.

The ignored checkpoint remains under
`reports/generated/course-tutor-v1.2.3-hybrid-authoring-review-v2-attempt-001-invalid/checkpoint.json`.
It contains private case-level decisions and must not be committed or shown to
the future independent human reviewer.

## Observed result

| Reviewer | Attempt records | Valid approve | Valid revise | Invalid |
| --- | ---: | ---: | ---: | ---: |
| Local Gemma 3 4B | 146 | 123 | 22 | 1 |
| Local Qwen 3 4B | 0 | 0 | 0 | 0 |
| Qwen 3 derivative | 0 | 0 | 0 | 0 |
| **Total** | **146** | **123** | **22** | **1** |

All 19 no-evidence cases received revise decisions. Two assessed-work cases
and one ambiguity case also received revise decisions; one further ambiguity
response was invalid. The run had not reached the last six
permission/version cases when it was stopped. It consumed 229,771 local input
tokens, 18,792 local output tokens, and 1,459.318 seconds of measured reviewer
latency.

## Failure classification

- Governance/model selection: after inspecting progress, the repository owner
  explicitly excluded Gemma and required the newest proper DeepSeek model.
- Protocol: the frozen v2 committee therefore became ineligible before it was
  complete. Adding DeepSeek mid-run would have mixed protocols and invalidated
  traceability, so the process was stopped instead.
- Model: one Gemma response failed the exact JSON decision contract. The other
  145 responses were schema-valid, but no decision was human-adjudicated.
- Dataset: this attempt does not establish a dataset defect. The committee was
  incomplete and no independent-human audit occurred.
- Privacy: all case review remained local and no external provider was called.
- Held-out execution: authoring labels were read locally, but no tutor output,
  blinded mapping, seal, or held-out ledger was created.

## Limitations

- This is a stopped reviewer-selection result, not an authoring-quality
  estimate or proof that a specific Gemma verdict was right or wrong.
- Only one of three planned reviewers started, so agreement and disagreement
  metrics do not exist.
- The preserved private decisions cannot be reused in v3 or shown to the
  future independent human reviewer.
- No human approval, professor validation, component selection, or
  professor-fidelity effect is established.

## Replacement

The prospective replacement is
[`course-tutor-hybrid-authoring-review-v3`](../04_experiments/2026-08-14-course-tutor-hybrid-authoring-review-v3-plan.md).
V3 keeps the candidate and bounded human-audit rule fixed, removes Gemma, and
adds the official DeepSeek V4 Pro API as the stronger independent reviewer
under a new explicit authorization, call limit, cost ceiling, transport
preflight, and provider-revision binding.
