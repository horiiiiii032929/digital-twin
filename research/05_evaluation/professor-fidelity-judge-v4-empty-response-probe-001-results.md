# Professor-fidelity judge v4 empty-response probe 001 results

Result ID: `professor-fidelity-judge-v4-empty-response-probe-001`

Date: 2026-08-14

Status: Passed

Decision: Keep the v4 empty-response display and permit separately identified
primary anchor attempt 002. This does not validate the full judge or replace a
human reference.

## Binding and boundary

- Contract: `per-dimension-pairwise-v4-empty-response-display`.
- Displayed response: `[EMPTY RESPONSE]` derived from a public-synthetic empty
  answer.
- Judge: official `deepseek-v4-pro`, high thinking, JSON mode, no retry.
- Exact fingerprint:
  `a307abda487cd1b463329ccb945ce396`.
- Clean code revision:
  `1841b292db213a11e0e6e44ca10017a9f7c0bbe4`.
- Private, course, development, and held-out text used: zero.
- Ignored raw SHA-256:
  `c7650bbeb4fbf659c63193e6635c6c143d0606bceccd79cb5f178bc3e5d31430`.

## Result

The one-call gate returned a schema-valid `fail` for `actionability` and quoted
the exact literal `[EMPTY RESPONSE]`. The model and fingerprint matched the
frozen binding, finish reason was `stop`, and there was no retry.

- Input/output/reasoning tokens: 1,077 / 696 / 571.
- Conservative cost: USD 0.001074015 against a USD 0.25 stop.
- Latency: 8.622985 seconds.

## Additional audit before binding

A no-content inspection of the 25 valid calls checkpointed by invalid primary
attempt 001 tested 174 evidence quotes against their displayed source
responses. Of those, 173 were literal matches and one differed only by
punctuation; there were no pairwise mismatches. Contract v4 therefore stores
literal source spans and permits only a unique punctuation/whitespace/case
alignment, recording the original and aligned quote. Missing, semantic, or
ambiguous fuzzy matches fail closed.

## Limitations

This is one targeted public probe, not a full sensitivity suite. It addresses
the representability defect that invalidated attempt 001 and checks the exact
current provider identity. It does not establish judge agreement, pedagogical
validity, professor approval, or permission to run development or held-out.
