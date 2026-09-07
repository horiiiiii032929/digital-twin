# Final factual confirmation: analysis correction 001

## Decision and scope

Retain **Refine**. This is a reporting correction on revision
`5bb3d632e6b586e458751b61b22791347d80ea5d` with local documentation changes,
not a new experiment, model run, or rescore. The original
[record](records/final-cross-method-factual-confirmation-001.json) and
[result](final-cross-method-factual-confirmation-001-results.md) remain immutable.

## Source-version denominator

The frozen `score_response` implementation in
`src/digital_twin/evaluation/factual_qa_scoring.py` uses `all(...)` over citations.
An empty list is therefore vacuously valid. The researcher's handoff identifies
two such answerable responses in the BM25 dominance arm.

| Interpretation | Numerator / denominator | Percentage |
| --- | ---: | ---: |
| Recorded source-version validity | 717/800 | 89.625% |
| Sensitivity: no citations count as failure | 715/800 | 89.375% |
| Conditional validity among citation-bearing responses | 715/798 | 89.60% |

The latter two rows are transparent denominator arithmetic, not replacement
scores. Read-only inspection confirmed 798 citation-bearing responses in the
selected arm and verified all 1,000 stored payload hashes. Hidden gold was not
opened to reclassify cases. The 717 numerator is derived from the committed
0.89625 aggregate and 800 answerable cases; the two-case classification is
attributed to the handoff rather than claimed as a fresh independent audit.

The fully grounded predicate separately requires the correct answer action,
complete claims and citations, and no operational failure. Empty citations
cannot pass those answerable-case requirements. Fully grounded success remains
506/800 (63.25%); ranking, the failed gate, and Refine remain unchanged. The
frozen scoring code is retained for historical reproducibility. Any future
instrument must explicitly separate citation presence from citation validity.

## Severe-release metric boundary

The frozen scorer defines `severe_unsupported_release` as an `answer` action
on a case whose expected action is not `answer`. Its zero count therefore
means zero answer releases on the evaluated boundary cases; it is not a count
of every unsupported or incorrectly cited claim on answerable cases. Report
it alongside the strict 63.25% fully grounded rate.

## Evidence retention checkpoint

As checked locally on 2026-09-05:

- Factual confirmation: all five response databases remain locally inspectable;
  the aggregate result is available in the committed record.
- Visual confirmation 002: the local result and response ledger match the
  hashes already recorded in its committed record.
- Autonomy confirmation 024 and local qualification 010: their raw generated
  artifacts were not found in the local generated-evidence tree. Current report
  claims rely on committed aggregate records and artifact hashes. This is a
  retention limitation, not independent verification of the missing raw data.

Ignored filenames, contents, and new raw hashes are not published here. The
inventory retains aggregate-only reporting for local generated evidence. Hashes
identify original artifacts but cannot reconstruct missing per-case evidence.

## Verification and reproduction

Reproduce the displayed sensitivity using `(717 - 2) / 800` and
`(717 - 2) / (800 - 2)`, without loading either consumed evaluation dataset.
Focused flow-contract, release-profile, checkpoint-restart, and inventory
tests passed 17/17 on 2026-09-05 (five dependency deprecation warnings).
Command: `uv run pytest tests/test_build_final_report_evidence_inventory.py tests/test_final_local_release_profile.py tests/test_factual_qa_flow_contract.py tests/digital_twin/test_governed_autonomy.py::test_t1_v2_resumes_after_node_failure_without_duplicate_generation -q`.
Refresh with `uv run python -m scripts.build_final_report_evidence_inventory`.
No consumed 1,000-case or known 10,000-case data is tuned, rerun, or rescored.

[Machine-readable correction](records/final-cross-method-factual-confirmation-001-analysis-correction-001.json)
