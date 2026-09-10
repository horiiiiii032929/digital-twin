# Reviewer calibration003

Decision: **Keep instrument003 for bounded synthetic comparison; no product selection**.

Version003 permits exact canonical JSON scalar evidence in addition to source-local string excerpts, retains all semantic consistency checks, and explicitly limits evidence to five items. All64 expected control decisions passed with valid evidence and no in-run source drift. This qualifies the instrument only for the bounded synthetic comparison, not the product or real educational outcomes.

- Controls: 64/64 matched;32 unique repeated twice.
- Provider: gpt-5.4-mini-2026-03-17, low reasoning,1800-token output cap, concurrency4, no retries.
- Cost: US$0.146613; 64 calls; unknown-cost calls 0.
- Elapsed: 48.92s. Process memory not separately measured.
- In-run source unchanged: True. Revision `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty archived working tree.
- Product decisions: none. No human review, real learning or usability claim.

[Machine record](records/post-report-blind-review-003-mini-calibration-live-001.json) contains configuration, hashes, per-case ratings
and failures. Original outputs: `reports/generated/post-report-blind-review-003-mini-calibration-live-001`. Reproduce with
`uv run python -m scripts.run_post_report_blind_review --execute --model mini --version 3 --calibration-only --output-dir reports/generated/<fresh-id>`;
reserve US$1.92 against the cumulative US$30 budget before execution. Prior source
versions are archived for exact reconstruction. No semantic thresholds or gold
labels were revised after a result.
