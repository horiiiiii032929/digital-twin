# Course-tutor hybrid authoring review v4 attempt 001 invalid results

Result ID: `course-tutor-hybrid-authoring-review-v4-attempt-001-invalid`

Date: 2026-08-14

Status: Invalid and stopped; 22 completed private decisions plus one
in-progress timed-out case preserved; no held-out authoring judgment, local
private judgment, human packet, seal, ledger, blinded mapping, or tutor output
created.

Decision: Keep DeepSeek V4 Pro, direct official API transport, the public stress
gate, malformed-output repair, and the two-family quorum. Correct the private
exception classification prospectively so one transient timeout or connection
failure may receive the same single bounded retry, while authentication,
configuration, model, and fingerprint failures remain hard stops.

## Boundary and bindings

- Plan: `course-tutor-hybrid-authoring-review-v4`.
- Candidate: unchanged private `course-tutor-v1.2.3` draft 004.
- Draft hashes: unchanged from v3.
- Clean code revision:
  `f3d9a3ef3dd64b4f3f0f0c4ed3f90cda7973cd88`.
- Provider/model: official DeepSeek API / `deepseek-v4-pro`, documented
  `DeepSeek-V4-Pro-0813`, thinking effort `high`.
- Returned fingerprint:
  `a307abda487cd1b463329ccb945ce396`.
- External requests attempted: 34 total: ten completed public probes, 23
  completed private responses, and one private timeout with unknown usage.
- Known completed-response usage: 35,435 input tokens, 47,678 output tokens,
  and USD 0.056894085 conservative cost. The timeout may add unrecorded usage.
- Private checkpoint SHA-256:
  `f8a3024856e36d2c67ded035e36f7c8cae5a3494f106b42bafd6aa82755efa56`.

The ignored checkpoint remains under
`reports/generated/course-tutor-v1.2.3-hybrid-authoring-review-v4-attempt-001-invalid/checkpoint.json`.
It is private, cannot be reused in v5, and cannot be shown to the future human
reviewer.

## Observed result

- DeepSeek public stress probes: 10/10 valid, one stable fingerprint.
- Local public preflights: 2/2 valid with frozen digests.
- Completed private decisions: 22/22 schema-valid; 20 approve and two revise.
- Underlying private attempts: 24; 22 valid responses, one empty-content
  response followed by a valid repair, and one API timeout.
- Current human lower bound at stop: 35, well below the ceiling of 48.
- Gemma calls: zero.

The direct official client eliminated the v3 async cleanup warning and reduced
malformed final decisions from 11/59 to 0/22. The single empty response was
preserved and repaired exactly as planned. The next case then raised
`APITimeoutError`. Although a timeout is neither authentication failure nor
model/fingerprint drift, the v4 implementation marked every OpenAI exception
as `hard_stop`, leaving that case explicitly `in_progress` and stopping the
run. This is an implementation result, not a model-quality failure.

## Failure classification

- Integration: provider exceptions were not separated into transient and hard
  configuration/identity classes.
- Operational: one private API request timed out; its provider-side usage and
  billing are unknown.
- Transport: direct JSON transport and one malformed-output repair otherwise
  behaved as predicted.
- Dataset/model: the 22 completed decisions and two revisions are not enough to
  estimate quality or establish defects.
- Privacy: the timeout carried only prospectively authorized fields. No real
  student data, tutor output, other model verdict, or human decision was sent.
- Held-out execution: no held-out authoring case or tutor output was reached.

## Limitations

- Neither local private reviewer started, and no committee result exists.
- No human adjudication occurred.
- The timeout has no response fingerprint, tokens, or known cost.
- This attempt establishes neither authoring approval nor professor validation.

## Replacement

The prospective replacement is
[`course-tutor-hybrid-authoring-review-v5`](../04_experiments/2026-08-14-course-tutor-hybrid-authoring-review-v5-plan.md).
V5 changes only transient provider-error classification and run identifiers;
the model, prompts, dataset, public stress gate, retry ceiling, two-family
quorum, privacy boundary, cost cap, and human cap remain fixed.
