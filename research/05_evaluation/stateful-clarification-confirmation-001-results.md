# Stateful clarification confirmation 001

## Decision

`completed-keep` for the bounded clarification mechanism. When the selected
evidence gate found a genuine tie between source interpretations, one
persistent, source-bound student choice recovered grounded answers without
relaxing the existing evidence gate.

R1.1 remains the rollback until this exact revision passes local HTTPS
requalification. The result does not change the known 10,000+1,000 grounding
decision.

## Results

| Measure | Result |
| --- | ---: |
| Cases | 200 |
| Answerable cases | 160 |
| Candidate grounded completion | 100% |
| Fail-closed control grounded completion | 25% |
| Paired completion delta | +75 percentage points |
| Unambiguous control success | 100% |
| Clarification resolution accuracy | 100% |
| Boundary safety | 100% |
| Invalid-reply safety | 100% |
| Source-version validity | 100% |
| Restart / idempotency consistency | 100% / 100% |
| Unsupported or wrong-scope releases | 0 |
| Duplicate deliveries | 0 |
| Clarification-turn ceiling violations | 0 |
| Provider calls / cost | 0 / USD 0 |

The run used the actual `StudentTutoringService`, SQLite clarification
lifecycle, selected evidence-gate lineage, restart path, and student-facing
resolution contract. It executed from clean revision
`b68318380600509424864e5763cdce5d544c8bd4` and satisfied every preregistered
gate.

## Interpretation

This result addresses the measured failure mode rather than lowering the
grounding threshold. A tied source set remains non-answerable until the student
selects one displayed, authorized interpretation. The selected source is then
revalidated against release, artifact, version, checksum, region, and claim
lineage before generation. Free text that does not exactly resolve an option
remains safely pending.

## Limitations

- The sources and student choices were public-synthetic; real students may not
  choose the intended interpretation at the same rate.
- The run establishes mechanism correctness, grounding, persistence, and
  safety, not learning improvement or real-professor fidelity.
- The immutable known 10,000+1,000 benchmark was not read, rerun, or rescored.
