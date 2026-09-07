# Evaluation explanations for first-time readers

Date: 6 September 2026. Scope: report prose and mathematical notation only.
No evaluation was rerun and no application behavior or recorded metric changed.

The report now defines a case, control, candidate, gate and synthetic history
before presenting results. Section 5.2 explains denominators and binary case
scores; later equations introduce revision and longitudinal comparisons locally.

| Explanation | Scoring and evidence source |
| --- | --- |
| Grounded success: 506/800 = 63.25%; boundary-action accuracy: 192/200 = 96% | `src/digital_twin/evaluation/factual_qa_scoring.py`, `research/05_evaluation/records/final-cross-method-factual-confirmation-001.json` |
| Complete evidence among the first three retrieval results | The same scorer's lineage matching and complete-evidence aggregation; required references are indexed items |
| Source-family confidence interval | The same scorer's `source_family_bootstrap_interval`: resample equally weighted family means, 10,000 replicates |
| Preservation 56/56 and repair 47/56 for each candidate | The fresh v14 and v16 independent factual revision control records, retained in the detailed trial appendix |
| Mean paired mastery difference 0.0324 across 36 matched pairs | `src/digital_twin/evaluation/hidden_state_metrics.py`, `src/digital_twin/evaluation/autonomy_learning_scoring.py`, `research/05_evaluation/governed-full-autonomy-v2-1-multi-concept-confirmation-025-results.md` |

The 96% measure checks the selected action, not every boundary safety property.
Grounded success is a conjunctive mechanical proxy, not unrestricted semantic
or human grading. Retrieval completeness can pass when the delivered answer
omits facts. Repair rates have separate adequate/defective denominators and do
not override critical-error gates. The interval accounts for source-family
clustering; it is not evidence of generalization to real students.

The simulation's mastery difference equals 3.24 percentage points on its
zero-to-one scale, computed from unrounded paired values. AUROC is explained
as ranking later correct attempts above incorrect attempts using the preceding
state estimate; its reported value averages eligible histories. Wasted-delivery
rates average histories and use simulated mastery/receptiveness, not human
judgments. Neither measure establishes observed student learning.

## Verification

The revised main report compiles to 17 pages: 11 main text/declaration, two
references and four appendices. Evaluation pages were rendered and visually
inspected. Formula arithmetic, bibliography and reference consistency, PDF text
bounds and compiler diagnostics were checked. The detailed companion, trial
index and recorded experiment results were not altered. Local before/after
artifacts and verification output are in
`reports/generated/evaluation-reader-revision-20260906/`.
