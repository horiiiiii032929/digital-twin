# Generator qualification v3 P3 development plan

Date frozen: 2026-08-14

Status: prospectively frozen; public-synthetic development only

## Decision question

Can a narrow clarification-first revision to strict-evidence P2 remove the one
remaining V4 Pro ambiguity failure without regressing grounding, citations,
policy behavior, provider identity, latency, or cost on the unchanged 48-case
public-synthetic development set?

## Control, candidate, and prediction

- Control: V4 Pro/P2 development 001, original 46/48 and corrected 47/48 after
  the separately registered action-analysis correction.
- Candidate prompt: P3,
  `clarification-first-grounded-prompt-v4`.
- Only intended prompt change: when supplied evidence contains multiple
  meanings, do not explain either meaning yet; ask exactly one targeted
  question containing “Which meaning” and wait for the learner's choice.
- Generator: unchanged official `deepseek-v4-pro`, non-thinking JSON,
  temperature 0, one attempt, exact fingerprint
  `a307abda487cd1b463329ccb945ce396`.
- Dataset: unchanged 48-case public-synthetic development split, SHA-256
  `a57ffeb7618e300a1647d733d605461c948b6b84ba9a1f48af904a0f814156c4`.
- Prediction: 48/48 deterministic all-check passes, including 6/6 ambiguity,
  with no other scenario regression.

## Gates and limits

The candidate uses the same 30-second p95 floor, USD 1 run stop, cumulative USD
10 issue cap, exact provider identity, no retry, citation/source identity,
required/forbidden term, assessed-work, permission/version, and no-evidence
gates as V4 Pro/P2.

Any provider drift, incomplete attempt, nonzero private call, hard-gate failure,
scenario regression, or result other than 48/48 requires Refine. A pass permits
calibrated semantic review and bounded professor-fidelity anchor preparation
only. It cannot select the profile, open generator held-out, create the
professor-fidelity seal, or bypass the independent-human authoring audit.

Local Qwen is not accepted for citation clearance because its v2 reviewer
failed the missing-citation sensitivity probe. Gemma is prohibited.

## Command

```bash
npm run benchmark:generator-qualification-v4-pro-p3-development
```
