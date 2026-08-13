# Course-tutor hybrid authoring review v1 plan

Plan ID: `course-tutor-hybrid-authoring-review-v1`

Date frozen: 2026-08-13

Status: prospective; no ensemble judgments or human sample decisions have been
run under this protocol.

## Decision question

Can the 152-case private course-tutor authoring draft be qualified with a
reproducible local multi-model review plus a bounded independent-human audit,
without claiming that every case received human approval and without opening
held-out tutor outputs?

The previous requirement for one human to inspect all 152 cases is dropped as
operationally unrealistic and vulnerable to checklist fatigue. Its historical
result remains preserved. This protocol replaces only the authoring-review
gate; it does not change the later development, blinded response review, or
one-time held-out execution gates.

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
- No tutor outputs, blinded condition mapping, seal, or held-out execution
  ledger may be opened or created during this review.
- No external provider calls are allowed. The existing DeepSeek authorization
  explicitly excludes judge use.

## Reviewers

Every case is reviewed independently by these frozen local Ollama bindings:

| Reviewer | Family | Model digest |
| --- | --- | --- |
| `local-gemma3-4b-reviewer-v1` | Gemma 3 | `a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a` |
| `local-qwen3-4b-reviewer-v1` | Qwen 3 | `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` |
| `local-huihui-qwen3-4b-reviewer-v1` | Qwen 3 derivative | `f5046078f1f6b4dc2ad23265d7d9e616aeb77088bc9092623b2f3f056f7b19d4` |

The committee contains three distinct model artifacts but only two base-model
families. Agreement is therefore triage evidence, not independent proof. The
human audit is retained to detect correlated model error.

## Six authoring checks

Each reviewer returns one frozen-schema decision for every case:

1. question authentic and synthetic;
2. expected behavior correct;
3. claims atomic and correct;
4. evidence supports claims;
5. permission and version correct; and
6. split assignment acceptable.

An `approve` verdict is valid only when all six booleans are true. Malformed,
missing, or internally inconsistent output is an invalid model decision and
automatically requires human adjudication.

For no-evidence cases, reviewers receive the student question and the eight
nearest approved corpus passages from a deterministic local lexical search.
This cannot prove corpus-wide semantic absence and remains an explicit
limitation. For multi-evidence cases, reviewers receive every authored claim
and passage and must judge both support and necessity.

## Human sample contract

Sample seed: `course-tutor-hybrid-human-sample-v1`

Before reading ensemble verdicts, select two stable-hash cases from each
scenario-by-split stratum. Eight scenarios across development and held-out
produce a 32-case baseline: 16 development and 16 held-out cases.

The required human set is the union of:

- the frozen 32-case baseline;
- every case with reviewer disagreement;
- every case receiving at least one `revise` verdict; and
- every case with an invalid or missing model decision.

The human packet must hide all model verdicts and reasons. The reviewer records
all six checks, an approve/revise decision, notes, identity, role, timezone-aware
timestamp, and confirmation that model decisions were not inspected.

## Stop and escalation rules

- All 456 model decisions must be present.
- Zero external calls are permitted.
- If more than 48 cases require human review, stop and refine the model-review
  instrument instead of transferring an unbounded workload to the human.
- If any human-audited case fails any check, do not seal. Revise the candidate,
  preserve the unfavorable result, rerun the full ensemble on a new version,
  and create a fresh seeded audit.
- Cases outside the human set qualify only through unanimous three-model
  approval.
- All required human cases must receive six true checks and `approve`.
- GitHub Support must confirm removal of the superseded public commit before
  the privacy boundary can close or a seal can be created.

With zero failures in a 32-case random sample, the simple rule-of-three upper
95% bound is approximately 9.4%. This is not a guarantee that all unsampled
cases are defect-free. The report must describe the result as local multi-model
cross-review with targeted independent-human validation, never full human
approval or professor validation.

## Measurements

- valid model decisions and failures by reviewer;
- unanimous approvals, unanimous revisions, and disagreements;
- per-check pass rates and scenario/split slices;
- baseline, escalated, and total required-human counts;
- local latency and token counts where Ollama reports them;
- human defects by check and scenario;
- sample coverage and rule-of-three uncertainty; and
- exact model, prompt, seed, dataset, conditions, code revision, and dirty
  state bindings.

## Reproducibility sequence

1. Build and validate the unchanged draft.
2. Run the frozen three-model local ensemble over all 152 cases.
3. Generate the blinded 32-plus-escalations human packet and template.
4. Complete the independent-human sample without opening model verdicts.
5. Validate the ensemble and human review together.
6. After GitHub purge confirmation, create the immutable seal.
7. Run development only; held-out tutor outputs remain unopened until every
   later prospective gate passes.
