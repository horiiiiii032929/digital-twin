# Evaluation result: evaluation-calibration-cluster-development-20260906-001

## Run identity and decision

Completed 2026-09-06, assistant-run no-network evaluation diagnostic. **Keep the explicit review-needed advisory; Refine semantic scoring.** No runtime/profile changes or original score replacements. Base revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty tree; exact script/input hashes in the [record](records/evaluation-calibration-cluster-development-20260906-001.json). Python/locked repository dependencies; standard-library resampling, no provider model.

Command: `uv run python -m scripts.evaluation_calibration_cluster_analysis --output-dir reports/generated/evaluation-calibration-cluster-development-20260906-001`. Use a new directory to reproduce; overwrite is rejected. Generated result: `reports/generated/evaluation-calibration-cluster-development-20260906-001/result.json`.

## Decision context and data

The [prospective plan](../04_experiments/2026-09-06-evaluator-calibration-and-cluster-analysis-plan.md) predicts that exact extraction checks will miss substantive defects and that pooled repeated events overstate the available independent evidence. Baseline is unchanged `score_case`; the additional advisory flags prose not covered by supplied quotations and explicitly requires review. It is not a semantic judge or a replacement gate.

Eleven authored mutations use the scheduler source in `cross-course-quality-development-v1`; all are synthetic development data, with no independent human validation. Quantitative analysis preserves live005's 44 paired cases from four authored mini-courses and the full simulation's 12 matched persona/profile pairs (24 histories). No held-out data were opened. No cases, negative scores, courses, or histories were excluded. Corpus hashes and all per-case mutation responses are retained.

## Calibration results and gates

| Mutation slice | Cases | Unchanged baseline | Advisory |
| --- | ---: | --- | --- |
| Clean exact answer | 1 | Pass | No additional review flag |
| Unsupported and contradictory added prose | 2 | Both pass incorrectly as a semantic-quality indicator | Both flagged for review |
| Missing requirement, bad source version, malformed citation, empty answer | 4 | All fail as required | Not a substitute: bad version/empty answer can be unflagged |
| Irrelevant question and paraphrased premature solution | 2 | Both pass despite substantive defects | Both flagged, without classifying their semantics |
| Generic question and duplicated exact text | 2 | Both pass | Generic text flagged; duplication escapes residue check |

The specified clean/malformed/missing gates passed; the expected blind spots remained visible. Ten tests passed, including constant-cluster and unequal nested-size invariants, paired discordance, invalid/duplicate pairing, nonfinite clusters, and mutation outcomes. There is no natural-language sensitivity/specificity estimate: these mutations were intentionally authored to probe particular weaknesses. The advisory also flags ordinary useful prose and cannot diagnose it. Keep both structural checks and explicit semantic-review status.

## Paired and clustered results

The original mechanical counts remain **28/44 incumbent and 39/44 candidate**: 28 both pass, 11 candidate-only, zero incumbent-only, five both fail. The +25 percentage-point difference is a mechanical development result, not a semantic accuracy gain. Course differences are scheduler +36.36 points, ledger +18.18, ecology +9.09, protocol +36.36.

A seed-620906, 10,000-draw percentile bootstrap resampling whole course clusters gives an exploratory +13.64 to +36.36 point interval. There are only four authored clusters; this interval is unstable and cannot substantiate cross-discipline or held-out generalization. Leave-one-course-out differences range +21.21 to +30.30 points. The record also retains ordinary Wilson intervals with an explicit independence-approximation label; these are not the primary inferential basis.

For the full simulation, equal-weight matched-history differences in guarded-failure fractions (autonomous minus reactive) average +0.59 percentage points. Resampling all 12 whole persona/profile pairs gives an exploratory interval of −1.57 to +2.63 points. These paired contexts share source rules and one seeded adaptive driver; this is not causal evidence about student outcomes, autonomous usefulness, or a population rate. The 484 tutor turns are not 484 independent subjects.

## Operational and validity review

Zero external calls, zero model tokens, USD0. No new latency or memory benchmark was conducted; this run analyzes frozen records and small fixtures. All output directories are exclusive, all original gold/records remain unchanged, and the new record preserves code and input hashes. This diagnostic is valid within its narrow declared scope, not independent confirmation. No implementation was promoted.

The practical lesson is to distinguish checkable source structure, meaningful teaching content, and the number of independent evaluation units. Increasing repeated turns does not fix a blind scorer or supply more courses. A calibrated advisory review and representative reevaluation of the final candidate remain necessary. Existing permissioned course assets are not assumed absent; the gap is their appropriate reuse in a fresh, representative candidate evaluation with verified version/split/permission bindings and human review where claimed.
