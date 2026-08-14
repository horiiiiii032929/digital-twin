# Generator qualification v2 action-analysis correction plan

Date frozen: 2026-08-14

Status: prospectively frozen no-model correction

## Trigger and boundary

The V4 Pro development run recorded two ambiguity-action failures. Direct
inspection showed that `gqv1-dev-005` ends with “Which meaning are you asking
about?”, but the frozen classifier recognized “which context” and related
phrases only. `gqv1-dev-045` lists both meanings without asking a question and
must remain `answer`.

This correction reads only the exact ignored public-synthetic run with SHA-256
`7e5e703373cd52c106d21a0336d93ebd67f2406e179145d2e4f0ba0eac15a27b` and
the unchanged development dataset. It makes no model/provider call, does not
read held-out data, and does not overwrite the original 46/48 result.

## Frozen change and prediction

For ambiguity cases only, classify a response as `clarify` when it contains an
explicit question mark plus one of `which meaning`, `which one`, or `do you
mean`, in addition to the existing markers. Require the scenario to remain
ambiguity so ordinary follow-up questions in other scenarios cannot change
action labels.

Prediction: exactly `gqv1-dev-005` changes from `answer` to `clarify`; corrected
deterministic all-check passes become 47/48. `gqv1-dev-045` remains the sole
failure. Any other action change invalidates this correction.

## Command

```bash
npm run analyze:generator-qualification-v4-pro-action-correction
```
