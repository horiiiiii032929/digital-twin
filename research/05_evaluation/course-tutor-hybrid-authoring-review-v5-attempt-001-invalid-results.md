# Course-tutor hybrid authoring review v5 attempt 001 invalid results

Result ID: `course-tutor-hybrid-authoring-review-v5-attempt-001-invalid`

Date: 2026-08-14

Status: Invalid and stopped after 64/456 private decisions when the frozen
DeepSeek-stage human lower bound reached 49, above the maximum of 48. No local
private judgment, human packet, seal, held-out execution ledger, blinded tutor
condition mapping, or tutor output was created.

Decision: Keep the newest official DeepSeek V4 Pro binding, direct official API
transport, public stress gate, bounded repair, and two-family quorum. Refine the
review prompt prospectively to state the repository's frozen `dev`/`test`
family-token aliases for `development`/`heldout`, increase the output allowance
above 4,096 tokens, and record finish reason plus reasoning-token usage. Do not
reuse any v5 judgment.

## Boundary and bindings

- Plan: `course-tutor-hybrid-authoring-review-v5`.
- Candidate: unchanged private `course-tutor-v1.2.3` draft 004.
- Candidate hashes: unchanged from v4.
- Clean code revision:
  `7969e62a7706380de19802021a67b2b5df8be031`.
- Provider/model: official DeepSeek API / `deepseek-v4-pro`, documented
  `DeepSeek-V4-Pro-0813`, thinking effort `high`.
- Returned fingerprint:
  `a307abda487cd1b463329ccb945ce396`.
- External requests: 83 completed calls: ten public probes and 73 private
  attempts across 64 cases.
- Known total usage: 114,469 input tokens, 186,293 output tokens, and USD
  0.211868925 conservative cost.
- Private checkpoint SHA-256:
  `6f9346dae8ecb53874c52be77579d5fcd73c984fb56bc29d9dab7e70f86702ee`.

The ignored checkpoint remains under
`reports/generated/course-tutor-v1.2.3-hybrid-authoring-review-v5-attempt-001-invalid/checkpoint.json`.
It is private, cannot be reused in a replacement run, and cannot be shown to a
future blinded human reviewer.

## Observed result

- DeepSeek public stress probes: 10/10 valid with one stable fingerprint.
- Local public preflights: 2/2 valid with the frozen Qwen-family digests.
- Completed private decisions: 64; 45 approve, 15 revise, and four invalid.
- Underlying private attempts: 73; five empty first responses were repaired to
  valid decisions, while four cases remained invalid after two empty responses.
- All 13 empty responses used exactly the configured 4,096 output tokens. The
  run did not retain finish reason or reasoning-token detail, so output-limit
  truncation is strongly indicated but not directly proven.
- Development: 48 completed; 42 approve, three revise, and three invalid.
- Held-out authoring: first 16 completed; three approve, 12 revise, and one
  invalid. Held-out tutor execution remained unopened.
- Human lower bound at stop: 49, above the frozen maximum of 48.
- Gemma private or public calls: zero.

## Cross-check and failure classification

- Evaluation instrument: all 12 completed held-out revisions failed the split
  check because `split=heldout` was paired with the repository's canonical
  split-specific `-test-` family token. Every associated reason mentioned both
  `test` and `heldout`; the prompt did not declare that alias. Static split
  isolation had already passed. These are instrument-induced false positives,
  not demonstrated cross-split leakage.
- Candidate quality: the three development revisions failed claim atomicity.
  They remain genuine targeted concerns and must not be erased by the prompt
  correction.
- Model/transport: the exact official model and fingerprint remained stable.
  Empty JSON content was the only attempt failure class.
- Operational: the 4,096-token ceiling was reached on every empty response.
  The official model supports a substantially larger output allowance, so a
  prospective increase is justified while retaining the USD 2 cost stop.
- Human-review design: 19 DeepSeek escalations combined with the frozen
  33-case mandatory set to produce 49 unique cases. Removing the 12 alias false
  positives would have left the lower bound below the ceiling, but the frozen
  v5 result cannot be corrected retrospectively.
- Privacy: only prospectively authorized private course fields were sent. No
  real student data, tutor output, other model verdict, or human decision was
  sent.

## Limitations

- The local private reviewers never started, so no committee result exists.
- No human adjudication occurred.
- The first 16 held-out authoring cases are not representative of all held-out
  scenarios.
- The output-limit diagnosis lacks recorded finish reasons and reasoning-token
  counts.
- This attempt establishes neither authoring approval nor professor validation.

## Replacement requirements

Any v6 replacement must be frozen before calls and must:

1. retain `deepseek-v4-pro`, high thinking, the stable-identity gate, the two
   local Qwen-family reviewers, the same private authorization, and no Gemma;
2. declare that `dev` and `test` are the canonical family-token aliases for
   `development` and `heldout`, without weakening static split-isolation checks;
3. increase `max_tokens` prospectively and record finish reason and reasoning
   tokens for every completed response;
4. retain the 48-case human ceiling and USD 2 cost stop; and
5. reuse no model judgment from v1 through v5.
