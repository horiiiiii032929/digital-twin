# Advisory semantic reviewer calibration 001

Decision: **Refine calibration; tutor review blocked**. This is an unsuccessful
calibration run, preserved without replacing its expectations or retrying outputs.

## Design and operation

The [prospective plan](../04_experiments/2026-09-06-completion-semantic-review-plan.md)
froze eleven synthetic variants, two shuffled repetitions, Terra reasoning low,
1,500 output tokens, no retries, and a 120-call/USD 10 reservation ceiling.
Only synthetic data was sent, with `store=false`. No private course or student
data was used. Model/provider/account limitations are in the machine record.

All 22 actual calls returned valid structured output. Cost: USD 0.103932;
conservative reserved cost: USD 0.774152. The eight explicitly defective variants
were identified in both repetitions (16/16). The positive source-correct control
was accepted once and rejected once. The second judgment treated the missing
check-understanding question as a current-turn profile violation. The profile
specified an explanation/check sequence without an explicit per-turn obligation.

This exposes an ambiguous positive calibration label and reviewer disagreement;
it is not conclusive evidence that the rejection was wrong. Generic and duplicate
controls were advisory, as preregistered. The calibration gate failed and **zero
of the planned 88 tutor responses were judged**. Do not call 16/16 defect
recognition an independently qualified semantic scorer or real-instructor review.

## Remedy and evidence

A separately versioned successor will use four fictional courses, balanced
positive/negative controls and explicit current-turn profile requirements.
These remain authored development controls, not human-validated gold.

Raw attempts, outputs, frozen inputs, manifest, summary and source snapshot:
`reports/generated/completion-semantic-review-development-001-live-001/`.
The [machine record](records/completion-semantic-review-development-001-live-001.json)
retains exact hashes, revision/dirty state, usage, conditions and limitations.
The [review runner](../../scripts/run_completion_semantic_review.py) and tests
cover schema consistency, hidden labels, unsupported review excerpts, uncertain
verdicts and missing judgments. The run's exact source is archived because later
instrument corrections must not alter its reproducibility.
