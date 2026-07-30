# Evaluation result: cross-course-benchmark-model-second-review-v1

## Run identity

- Component: cross-course retrieval benchmark label quality
- Status: completed with one adjudicated disagreement
- Date and owner: 2026-07-30, project researcher
- Code revision at run: `df1acfda89e4934e27db9d4fb4e14f749340d351`
- Working tree: dirty with task implementation and unrelated user-owned files;
  private source data and raw results remained ignored
- Plan:
  [`2026-07-30-cross-course-benchmark-second-review-plan.md`](../04_experiments/2026-07-30-cross-course-benchmark-second-review-plan.md)
- Reproduction: private local run using
  `python -m scripts.second_review_cross_course_benchmark`, followed by
  `python -m scripts.apply_cross_course_second_review`

## Decision context

The decision question was whether a fixed sample of at least 20
researcher-verified positive cases could pass blinded semantic review before
the private held-out split was sealed. This was a dataset-quality gate, not a
retrieval-method comparison.

The primary wording model was local `gemma3:4b`. The blinded reviewer was the
different local model
`huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0`, digest
`f5046078f1f6`. No private course text was sent to an external provider.

## Dataset and sample

- Dataset: private `cross-course-retrieval-v1-draft-6`
- Pre-review dataset SHA-256:
  `d8744c69b94cbd7f85dcb74cc8cc306c81839dc474a901b2625136fa642f0fe4`
- Sample seed and prompt version: `cross-course-second-review-v1`
- Sample: 20 positive cases selected before reviewer output by fixed SHA-256
  ordering
- Allocation: five cases per course across four courses; within each course,
  three answerable and two cross-course-confusion cases

The reviewer saw only the question, expected action, required claims, exact
supporting evidence, and visual-dependency flag. Prior review decisions, notes,
retrieval outputs, metrics, and split-level results were omitted.

## Results

| Outcome | Cases | Rate |
| --- | ---: | ---: |
| Accepted by local-model reviewer | 19 | 95% |
| Rejected by local-model reviewer | 1 | 5% |
| Parseable structured decisions | 20 | 100% |
| Retained after explicit adjudication | 20 | 100% |

The only rejection was `ccr1-cs5421-05`. It is preserved in the ignored raw
result. The reviewer said two managers with different salaries did not violate
`position -> salary`, while also stating that the dependency requires one
salary for a given role. The researcher explicitly adjudicated this as an
internally inconsistent reviewer-reasoning error and retained the case.

No confidence interval is reported. The fixed, balanced QC sample was designed
to expose label defects, not to estimate a population agreement rate.

## Operational record

| Measure | Result |
| --- | ---: |
| Prompt tokens | 5,798 |
| Output tokens | 1,614 |
| Summed local request time | 118.5 seconds |
| External provider calls | 0 |
| External API cost | USD 0 |

Latency is reported for reproducibility only and was not a quality criterion.

## Gates

| Gate | Result |
| --- | --- |
| Exactly 20 fixed sampled cases | Pass |
| Five cases from each target course | Pass |
| Every output parseable and schema-valid | Pass |
| Original rejection preserved | Pass |
| Substantive disagreement adjudicated before sealing | Pass |
| Private data remains local and ignored | Pass |

## Decision

Outcome: **Keep and approve for sealing**.

Draft 6 retains all 100 researcher-verified cases. The 20 sampled positive
cases carry second-review records, including the preserved rejection and
explicit adjudication. No retrieval implementation is selected by this result,
and no held-out retrieval evaluation has been run.

## Limitations

- This is local-model agreement, not independent human or professor review.
- The sample covers positive answerable and cross-course-confusion labels.
- No-evidence and integrity cases were verified separately by the researcher.
- Agreement does not validate student usability, professor fidelity, learning
  effectiveness, multimodal evidence, or retrieval quality.
- The reviewed dataset includes private course material and therefore remains
  outside version control.

The next step is to seal the approved dataset, record immutable hashes and the
development/held-out boundary, and create a one-time held-out ledger before the
final retrieval comparison.
