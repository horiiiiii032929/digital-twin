# Course-tutor hybrid authoring review v1 attempt 001 invalid results

Result ID: `course-tutor-hybrid-authoring-review-v1-attempt-001-invalid`

Date: 2026-08-14

Status: Invalid and stopped prospectively; 172/456 attempt records preserved;
no human packet, seal, held-out ledger, or tutor output created.

Decision: Refine the review instrument. Preserve this attempt, disable Qwen
thinking explicitly, add a public transport preflight, reduce the random
baseline to 16 while requiring a human census of all 19 no-evidence cases, and
rerun under a new frozen v2 plan.

## Boundary and bindings

- Plan: `course-tutor-hybrid-authoring-review-v1`.
- Candidate: unchanged private `course-tutor-v1.2.3` draft 004.
- Development dataset/conditions SHA-256:
  `a582ea6806846ceda919a956946edbcbeae7692c5ee199d20d4e9e46a745d018` /
  `b370fd01be047da78435a6cacac874850a6c32a116747714bdfae690cdfddbda`.
- Held-out dataset/conditions SHA-256:
  `c0aad4979e25de24cb8d0a99f876a47576a534d65257123f95b4edfcb3f000a2` /
  `3e855d5f92c903630400d9a2d171e1e29a58b3cb772dbfdc60384ea2dc928bf6`.
- Clean code revision:
  `51c7b0ab0c93862f34b9a046cf398194618bbc36`.
- External provider calls: 0.
- Private checkpoint SHA-256:
  `433abf46b88a171fc7e077dbf4df9ea66c46558551e32e035ce78b278bf70ce8`.

The ignored checkpoint remains under
`reports/generated/course-tutor-v1.2.3-hybrid-authoring-review-v1-attempt-001-invalid/checkpoint.json`.
It contains private case-level decisions and must not be committed or shown to
the future independent reviewer.

## Observed result

| Reviewer | Attempt records | Valid approve | Valid revise | Invalid |
| --- | ---: | ---: | ---: | ---: |
| Local Gemma 3 4B | 152 | 126 | 26 | 0 |
| Local Qwen 3 4B | 20 | 0 | 0 | 20 |
| Qwen 3 derivative | 0 | 0 | 0 | 0 |
| **Total** | **172** | **126** | **26** | **20** |

Gemma revised all 19 no-evidence cases, five assessed-work cases, one ambiguity
case, and one permission/version case. Only five of its 26 revisions overlapped
the frozen baseline, producing a 53-case human lower bound before Qwen errors.

Qwen 3 then returned an empty response for 20 consecutive schema-constrained
requests. Every attempt was recorded as invalid with no retry. Combining the
frozen baseline, Gemma revisions, and those invalid records produced a
66-case minimum human set. Because 66 exceeded the prospective ceiling of 48,
the run was stopped before wasting the remaining local compute.

## Failure classification

- Model/transport: Qwen 3 used implicit thinking mode until its output budget
  ended, leaving the structured response empty. A local public synthetic probe
  after the stop confirmed that top-level `think: false` returns valid JSON for
  both Qwen bindings.
- Instrument/workload: the 32-case random baseline plus mandatory practical
  escalation left too little room for the inherent no-evidence limitation.
  Gemma revisions alone forced 53 human cases.
- Dataset: this attempt does not establish a dataset defect. No human audit was
  run and the committee was incomplete.
- Privacy: all course text stayed local; no external provider was called.
- Held-out execution: authoring labels were read locally, but no tutor output,
  blinded mapping, seal, or held-out ledger was created.

## Limitations

- This is a stopped instrument result, not an authoring-quality estimate.
- Only Gemma completed all cases; Qwen produced 20 invalid records and the
  third reviewer did not start.
- Gemma's revisions remain private triage evidence and cannot be presented as
  confirmed case defects.
- No human approval, professor validation, component selection, or
  professor-fidelity effect is established.

## Replacement

The prospective replacement is
[`course-tutor-hybrid-authoring-review-v2`](../04_experiments/2026-08-14-course-tutor-hybrid-authoring-review-v2-plan.md).
V2 keeps the candidate and model digests fixed, adds explicit non-thinking
transport and public preflights, uses a 16-case scenario-by-split baseline,
and independently human-reviews all 19 no-evidence cases. The hard human cap
remains 48.
