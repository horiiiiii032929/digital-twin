# V10 eight-history operational comparison

**Decision: Refine.** All eight provider-backed histories completed 30 virtual days with verified durable-state restart comparisons. This is operational development evidence; V10's separately failed confirmation and profile ablation prohibit a factual-quality or release qualification.

## Design and provenance

Run `instructional-eight-history-operational-development-001-v10-live-001` follows [the prospective plan](../04_experiments/2026-09-06-final-candidate-eight-history-operational-plan.md). V4 versus V10, reactive versus autonomous, and fast versus low-receptivity actors give eight histories, one Socratic profile and seed 6209. Fresh synthetic protocol cards and direct approved-profile fixtures were used, not an ingestion study. Students, receptivity and elapsed time were simulated; tutoring, provider calls, persistence, scheduling and restart were actual. Both arms used Luna low and a 3,000-token cap. The frozen source archive, exact configuration, dirty state and revision are in the [record](records/instructional-eight-history-operational-development-001-v10-live-001.json); source hashes were unchanged.

## Outcomes

282 actual calls completed with zero provider failures and zero unknown-cost calls. Total reported cost was USD 0.1382264 (V4 0.0701924; V10 0.068034). Execution took 379.54 seconds with other evaluations/checks potentially co-resident. These times do not measure isolated capacity. Bounds were 5,000 calls/USD 125 total, 2,500/USD 62.5 per arm, and 600 calls/USD 100 per history; the arm cost limit dominates.

All eight restart comparisons matched persisted messages, learner/belief state, preferences and autonomous records. Sixteen consent changes were recorded with zero observed consent violations; lineage checks passed. These are checks of this execution, not duplicate-POST idempotency or human learning tests. All days 1–30 remain inspectable.

| History | Turns | Delivered actions | Outreach | Linked replies |
| --- | ---: | --- | ---: | ---: |
| v10-fast-learner-socratic-t1-v2-autonomous-6209 | 30 | question: 17, answer: 11, safe-graph-failure: 2 | 1 | 1 |
| v10-fast-learner-socratic-t1-v2-reactive-6209 | 28 | question: 16, answer: 12 | 0 | 0 |
| v10-low-receptivity-socratic-t1-v2-autonomous-6209 | 17 | question: 12, answer: 5 | 3 | 0 |
| v10-low-receptivity-socratic-t1-v2-reactive-6209 | 17 | question: 11, answer: 6 | 0 | 0 |
| v4-fast-learner-socratic-t1-v2-autonomous-6209 | 28 | question: 14, answer: 12, safe-graph-failure: 1, no-evidence: 1 | 1 | 1 |
| v4-fast-learner-socratic-t1-v2-reactive-6209 | 28 | question: 16, answer: 12 | 0 | 0 |
| v4-low-receptivity-socratic-t1-v2-autonomous-6209 | 16 | question: 9, answer: 7 | 3 | 0 |
| v4-low-receptivity-socratic-t1-v2-reactive-6209 | 16 | question: 10, answer: 6 | 0 | 0 |

180 turns included three local guarded failures: one V4 and two V10. Both V10 failures selected partial with no missing detail, triggering the retained `partial_without_missing_detail` contract; provider calls themselves completed. One V4 no-evidence turn also remains in the denominator.

## Outreach review and instrument correction

The [derived review](./instructional-eight-history-operational-development-001-v10-live-001-outreach-review.json) retains all eight outreach messages and both linked replies. The original raw output audit reported zero replies because it read `student_message.response_to_message_id`; actual outreach lineage is the separate `responding_to_delivered_message_id`. Matching that field to delivered IDs verifies two replies. The original summary is preserved unchanged, with its hash in the record.

All outreach quoted a complete approved protocol card after earlier correct synthetic attempts, with a generic contrast prompt. All eight deliveries occurred on days 2 or 3; no delivery after day-15 restart or day-20 consent restoration occurred. Consequently delivery during later active periods and intervention utility are not demonstrated. The fast actor's two replies repeated known card text; V4 asked another generic question, while V10 acknowledged correctness and requested a numerical example. Neither demonstrates that a student learned or that an outreach intervention was needed.

## Limitations and next decision

This small one-seed operational cohort is not a sample of real students. Operational completion does not establish pedagogical usefulness, privacy classification, semantic entailment, scalability or instructor fidelity. V10's independent entity-attribution and implication-direction failures remain binding adverse evidence. Keep the historical control and experimental status; assess the prospectively separate generator-model alternative before any fresh confirmation or real-course claim.

Raw artifacts: `reports/generated/instructional-eight-history-operational-development-001-v10-live-001`. Reproduce from the archived source/configuration using `uv run python -m scripts.run_instructional_operational_comparison --candidate v10 --live --output <fresh-directory>` with approved process credentials. No secrets are retained in this summary.
