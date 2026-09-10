# Reviewer calibration002

Decision: **Refine evidence contract; retain invalid run**.

Version002 failed12 numeric-evidence validations and one evidence-list length check. The prospective plan was extended during execution, so the source-change gate also failed. Raw data and source archive are preserved; no product promotion.

- Controls: 51/64 matched;32 unique repeated twice.
- Provider: gpt-5.4-mini-2026-03-17, low reasoning,1800-token output cap, concurrency4, no retries.
- Cost: US$0.146058; 64 calls; unknown-cost calls 0.
- Elapsed: 60.67s. Process memory not separately measured.
- In-run source unchanged: False. Revision `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty archived working tree.
- Product decisions: none. No human review, real learning or usability claim.

[Machine record](records/post-report-blind-review-002-mini-calibration-live-001.json) contains configuration, hashes, per-case ratings
and failures. Original outputs: `reports/generated/post-report-blind-review-002-mini-calibration-live-001`. Reproduce with
`uv run python -m scripts.run_post_report_blind_review --execute --model mini --version 2 --calibration-only --output-dir reports/generated/<fresh-id>`;
reserve US$1.92 against the cumulative US$30 budget before execution. Prior source
versions are archived for exact reconstruction. No semantic thresholds or gold
labels were revised after a result.
