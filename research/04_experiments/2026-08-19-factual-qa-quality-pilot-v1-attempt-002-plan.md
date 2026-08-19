# Source-linked factual-QA quality pilot v1 attempt 002

Date: 2026-08-19

Issue: #87

Status: frozen pending execution

## Predecessor diagnosis

Attempt 001 is preserved as invalid for method qualification. It produced
24/24 author outputs, but all seven boundary cases had empty user-visible
answers. Only 18/24 primary reviews were valid because thinking-mode empty
responses and contradictory review JSON interacted with a double-counted call
counter. The complete artifact was written before a final relative-path display
error returned exit code 1.

The attempt-001 result is not rerun and its thresholds are not relaxed.

## Fixed decision question

Does the corrected source-constrained generation and fail-closed cross-review
method produce a trustworthy 24-case factual-QA pilot that is ready for a
six-case stratified human audit?

This remains a method-improvement exercise, not a model comparison. A failed
gate produces another **Refine** decision.

## Prospective method changes

The corpus, 24 blueprints, slices, source hashes, model families, cost cap,
quality thresholds, and human-audit requirement remain unchanged. Attempt 002
changes only the failure-owning method boundaries:

1. The author prompt requires a non-empty user-visible response for every
   `abstain`, `clarify`, and `refuse` case and supplies action-specific response
   requirements.
2. DeepSeek V4 Flash cross-review runs in non-thinking, temperature-zero JSON
   mode to avoid reasoning-only/empty final content.
3. Each model attempt increments its call counter exactly once, before the
   transport call.
4. A review whose stated verdict contradicts its dimensions is preserved and
   normalized to a fail-closed rejection instead of being discarded.
5. Raw review JSON is retained for every returned response, including invalid
   contracts.
6. Output paths are resolved before the non-overwriting artifact is written and
   summarized.
7. Qwen remains diagnostic only. Its disagreements receive human-audit
   priority but cannot accept or reject a case.

## Frozen configuration and gates

- Author: DeepSeek V4 Pro, non-thinking, temperature 0.
- Primary review: DeepSeek V4 Flash, non-thinking, temperature 0.
- Independent sensitivity: local `qwen3:4b`, digest `359d7dd4bcda`.
- Gemma: excluded.
- Calls: at most 24 per role, sequential, zero retries.
- External cost stop: USD 1.00.
- Machine gates: unchanged from attempt 001, including 100% deterministic
  provenance and primary-review completion, at least 80% retention, no more
  than 20% quarantine, and zero cross-course leakage.
- Scale: never authorized by machine output; six-case human audit still must
  pass.

## Reproduction commands

```bash
uv run python -m scripts.run_factual_qa_quality_pilot \
  --instrument research/05_evaluation/instruments/factual_qa_quality_pilot_v1_attempt_002.json
uv run python -m scripts.run_factual_qa_quality_pilot --execute \
  --allow-external-provider \
  --instrument research/05_evaluation/instruments/factual_qa_quality_pilot_v1_attempt_002.json \
  --output reports/generated/factual-qa-quality-pilot-v1-attempt-002.json
```

## Decision

Pending. Go Deeper means only that the six-case audit may begin. Keep and scale
remain unavailable until that audit passes.
