# Course-tutor hybrid authoring review v3 attempt 001 invalid results

Result ID: `course-tutor-hybrid-authoring-review-v3-attempt-001-invalid`

Date: 2026-08-14

Status: Invalid and stopped; 59/456 private decision records preserved; one
additional private request interrupted in flight; no human packet, seal,
held-out ledger, blinded mapping, or tutor output created.

Decision: Keep the current DeepSeek V4 Pro model choice, but refine its
transport and the correlated-committee escalation rule. Use DeepSeek's official
OpenAI-compatible client directly, stress-test JSON transport with public
synthetic probes, allow one transport-only retry for empty or malformed output,
and require approval from both base-model families outside the targeted human
set under a new prospective v4 plan.

## Boundary and bindings

- Plan: `course-tutor-hybrid-authoring-review-v3`.
- Candidate: unchanged private `course-tutor-v1.2.3` draft 004.
- Development dataset/conditions SHA-256:
  `a582ea6806846ceda919a956946edbcbeae7692c5ee199d20d4e9e46a745d018` /
  `b370fd01be047da78435a6cacac874850a6c32a116747714bdfae690cdfddbda`.
- Held-out dataset/conditions SHA-256:
  `c0aad4979e25de24cb8d0a99f876a47576a534d65257123f95b4edfcb3f000a2` /
  `3e855d5f92c903630400d9a2d171e1e29a58b3cb772dbfdc60384ea2dc928bf6`.
- Clean code revision:
  `d290f026f64082cf7020ba26f1f21cc68d586d25`.
- Provider/model: official DeepSeek API / `deepseek-v4-pro`, documented
  `DeepSeek-V4-Pro-0813`, thinking effort `high`.
- Returned fingerprint on every completed private response:
  `a307abda487cd1b463329ccb945ce396`.
- External requests attempted: 61 total: one completed public preflight, 59
  completed private decisions, and one interrupted private request whose usage
  and billing are unknown.
- Known completed-response usage: 79,628 input tokens, 97,401 output tokens,
  and USD 0.11937705 conservative cache-miss-priced cost. The interrupted
  request may add unrecorded provider usage.
- Private checkpoint SHA-256:
  `6dcaa10b67bd21fdcb65fdc53d27d9e75bca1c9c9353c90a9d775592e08d69d4`.

The ignored checkpoint remains under
`reports/generated/course-tutor-v1.2.3-hybrid-authoring-review-v3-attempt-001-invalid/checkpoint.json`.
It contains private case-level decisions and must not be committed, reused in
v4, or shown to the future independent human reviewer.

## Observed result

| Slice | Attempt records | Valid approve | Valid revise | Invalid |
| --- | ---: | ---: | ---: | ---: |
| Development | 48 | 41 | 2 | 5 |
| Held-out authoring labels reached before stop | 11 | 0 | 5 | 6 |
| **Total** | **59** | **41** | **7** | **11** |

Nine invalid records were empty-response failures surfaced as
`LlmMalformedResponseError`; two returned content that failed strict JSON
parsing. No retry was allowed under v3. The 18 revise/invalid cases combined
with the frozen baseline and all no-evidence cases produced a 49-case human
lower bound. Two escalations overlapped cases already selected by the baseline
or no-evidence census. Because 49 exceeded the hard limit of 48, the next
request was interrupted and the run stopped before either local reviewer
began.

All completed provider responses retained the same model and fingerprint. The
known cost remained far below the USD 2 cap. The result therefore does not show
model-alias drift, cost failure, credential failure, or use of Gemma.

## Failure classification

- Transport/model output: 11/59 private responses were empty or malformed
  under thinking-mode JSON output. DeepSeek's official JSON guide documents
  that empty JSON-mode content can occasionally occur.
- Instrument/workload: escalating every single artifact-level revise or
  invalid response was too sensitive for two correlated local Qwen artifacts
  plus one independent DeepSeek family. The lower bound crossed the frozen cap
  before cross-review could complete.
- Runtime: repeatedly opening an asynchronous LiteLLM call loop emitted a
  coroutine-cleanup warning. It did not change the stable provider fingerprint,
  but v4 removes this avoidable transport layer from the DeepSeek path.
- Dataset: five valid DeepSeek revise decisions occurred in the first 11
  held-out authoring cases, but this incomplete, unadjudicated run cannot
  establish defects or an authoring-quality rate.
- Privacy: only the prospectively authorized fields were sent. No real student
  data, tutor output, model verdict from another reviewer, or human decision was
  transferred.
- Held-out execution: authoring labels were reviewed, but no tutor output,
  blinded mapping, seal, or held-out ledger was created.

## Limitations

- This is a stopped instrument result, not authoring approval or a comparison
  of DeepSeek against Gemma.
- DeepSeek completed only 59/152 cases; neither local reviewer started.
- The interrupted request has no response trace, token count, or known cost.
- No human adjudication occurred, so revise decisions remain triage signals.
- No professor validation, component selection, or professor-fidelity effect
  is established.

## Replacement

The prospective replacement is
[`course-tutor-hybrid-authoring-review-v4`](../04_experiments/2026-08-14-course-tutor-hybrid-authoring-review-v4-plan.md).
V4 keeps DeepSeek V4 Pro and the unchanged candidate, replaces the DeepSeek
transport, adds a public stress gate and one malformed-output retry, and uses a
two-family approval quorum instead of escalating one dissent from either of the
two correlated Qwen artifacts.
