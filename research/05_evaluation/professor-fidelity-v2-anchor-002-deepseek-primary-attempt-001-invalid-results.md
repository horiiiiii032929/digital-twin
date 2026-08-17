# Professor-fidelity v2 anchor 002 DeepSeek primary attempt 001 invalid results

Result ID: `professor-fidelity-v2-anchor-002-deepseek-primary-attempt-001-invalid`

Date: 2026-08-14

Status: Invalid and stopped; rerun prohibited

Decision: Refine the judge interface prospectively, preserve this attempt, and
start a separately identified attempt only after a public empty-response probe
passes.

## Run identity and boundary

- Source run: `professor-fidelity-v2-anchor-002` at clean revision
  `b19ade38407bb0b3187a307068f6a833693f679d`.
- Source result SHA-256:
  `6290755a44848a6c8a2239a4cee5d09e02c8f7007f2620a0f1c1a05df28a8cf1`.
- Judge: official `deepseek-v4-pro`, high thinking, JSON mode, no retry.
- Expected and observed checkpoint fingerprint:
  `a307abda487cd1b463329ccb945ce396`.
- Data: the separately sealed 12-case anchor only; no development or held-out
  split was opened.
- Gemma and Qwen calls: zero.

## Observed result

The runner completed and checkpointed 5/12 cases and 25/100 permitted calls.
Those 25 calls used one exact model and fingerprint and recorded USD
0.09396261 conservative cost, 38,198 input tokens, 88,904 output tokens, and
74,941 reasoning tokens. During case 6, a subsequent single-response judgment
failed the frozen output validator with `single-response judgment is invalid`.
The runner stopped immediately and did not write a final judgment result.

The ignored checkpoint SHA-256 is
`c3ecfffb307192b7e680e478b78701e328a5abe0dd2f37a742b4e1d4f26397b3`.
It contains private anchor material and is not committed. The failing response
was not checkpointed, so its exact call usage and invalid field must not be
invented.

## Diagnosis and repair boundary

Case 6 is a no-evidence case and includes one generated condition with an empty
answer. The v3 judge contract simultaneously required a non-empty exact quote
for every judgment and passed empty answers to the judge unchanged. That is a
deterministic interface defect that can make a valid failure judgment
unrepresentable. Because the failing response was not retained, this is a
supported hypothesis rather than a claim about the exact failed field.

The prospective v4 repair displays empty answers as the explicit literal
`[EMPTY RESPONSE]` for judging only and machine-checks that every evidence quote
is an exact substring of the displayed response. It does not change the source
generator output, rubric, labels, case ordering, model, or human-review gate.

Attempt 001 must not be resumed or rerun. A new attempt 002 may begin only from
a clean revision after the public-synthetic empty-response probe passes.
