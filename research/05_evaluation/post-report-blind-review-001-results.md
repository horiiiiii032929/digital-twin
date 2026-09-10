# Post-report common model review 001

Decision: **Refine the reviewer/output-evidence contract; retain product ratings as diagnostics only. Neither strict calibration passes, so this review does not promote a candidate.** Both old and improved outputs were reviewed using exactly the same two judges, sources, rubric and repetition schedule. Prior Sol scores were not mixed into these scores.

| Reviewer | Strict calibration | Raw label/axis match (post-hoc) | Valid repeated product overall agreement | Calls | Cost |
| --- | --- | --- | --- | --- | --- |
| Nano | 47/64 | 52/64 | 101/152 | 368 | US$0.206416 |
| Mini | 42/64 | 64/64 | 80/152 | 368 | US$0.834465 |

The original gate requires every expected calibration axis and valid response-only excerpts in both repeats. Mini's64/64 raw label matches do not erase excerpt violations; Nano also incorrectly rejected some valid citations. A representative Mini failure correctly identified a wrong source version but put `"version": 999` in the field reserved for exact response-text excerpts. Other examples quoted the source rather than the delivered answer. These are reviewer-contract failures, not automatically factual errors in the product. Nano additionally demanded chunk metadata on some offset-based calibration citations. No threshold or prompt was changed after seeing these results.

All152 product outputs were retained, including withheld replies and the failed004 integration. Each judge rated every output twice:608 total product ratings plus128 calibration ratings. Counts by original run and arm are in the records; runs with different code epochs are not pooled as one causal comparison. Between judges, 187 of304 paired rating slots had valid ratings from both; 145 of those agreed on the overall label. Invalid ratings remain explicit rather than becoming votes. No confidence interval treating repeated ratings as independent learners is reported.

[Full Nano record](records/post-report-blind-review-001-nano-live-001.json) and [full Mini record](records/post-report-blind-review-001-mini-live-001.json) include exact prompts, snapshots, hashes, cost, strict and post-hoc diagnostics, and disagreement slots. Every provider response had known cost; source snapshots were unchanged. Nano took 226.0s, Mini 226.1s. Process memory was not separately sampled for this API-bound instrument and is not inferred from token use.

Data are synthetic exposed development from12 prior runs, with32 existing assistant-authored controls. Both reviewers belong to the same provider family, so agreement is not independent human truth. This model-only review fulfils the requested finite comparison method but does not establish real learning benefit, human usability or the product quality threshold. No additional expensive model or repeated judge-search run follows this failure. Existing selected release remains the fallback; V19 stays explicit experimental, and its integration success is not V18/V19 semantic qualification.

Reproduce with `uv run python -m scripts.run_post_report_blind_review --execute --model nano --output-dir reports/generated/<fresh-run-id>` and `--model mini` for the second arm. Check the shared US$30 ledger first. Actual artifacts are `reports/generated/post-report-blind-review-001-nano-live-001` and `reports/generated/post-report-blind-review-001-mini-live-001`, at revision `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d` with a dirty but archived working tree.
