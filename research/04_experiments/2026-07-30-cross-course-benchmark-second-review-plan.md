# Cross-course benchmark second-review plan

Date: 2026-07-30

Status: completed as planned; result registered as
`cross-course-benchmark-model-second-review-v1`

## Decision question

Do at least 20 researcher-verified positive benchmark cases receive a blinded
second semantic review without exposing retrieval outputs or the original
review decision?

## Independence boundary

- Primary wording author: local `gemma3:4b`.
- Researcher review: Hikaru Horinouchi, assisted by source, fairness, and visual
  QC.
- Second reviewer: local
  `huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0`, exact local digest
  recorded at run time.
- No external provider or private-data transfer is permitted.
- The second-review prompt omits the primary reviewer, review status, notes,
  retrieval rankings, development metrics, and split-level results.

This is an independent local-model review, not independent human review or
professor validation.

## Frozen sample

Select exactly five positive cases per target course using a fixed SHA-256
ordering:

- three `answerable` cases; and
- two `cross_course_confusion` cases.

This yields 20 cases across IT5002, CS5421, IT5100B, and IT5100E. The sample is
selected from case metadata before any second-review output is observed.

## Review questions

For each sampled case, the reviewer independently judges:

1. whether the expected action is appropriate;
2. whether every required claim is supported by the supplied exact evidence;
3. whether the evidence is complete for the question;
4. whether the question is natural and answerable as written;
5. whether printed text is sufficient without visual inference; and
6. whether the case is fair for retrieval comparison.

The reviewer returns structured JSON with one boolean per check, an overall
`accept` or `reject` decision, and a short reason.

## Gates and handling

- Require 20/20 parseable decisions.
- Mark a case second-reviewed only when every check passes.
- Preserve every rejection or malformed output; do not silently retry it into
  approval.
- Any substantive rejection blocks sealing until adjudicated and versioned.
- Record dataset hash, model name and digest, prompt version, seed, case IDs,
  raw structured decisions, durations, and token counts in ignored private
  output.

## Limitations

The model review covers positive evidence labels. It does not independently
prove whole-corpus absence for no-evidence cases or validate policy authority
for integrity cases. Those boundary labels received separate researcher review
and remain explicit limitations. Model agreement is not evidence of human
usability, professor fidelity, or learning effectiveness.
