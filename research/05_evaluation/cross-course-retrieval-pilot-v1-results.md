# Cross-course retrieval pilot v1 results

Date: 2026-07-28

Run ID: `cross-course-retrieval-pilot-v1-development-attempt-002`

Decision: **Refine; advance hybrid fusion to the verified evaluation, select no
production method**

## Scope and validity

This is a local-only development pilot over 40 cases from private
`cross-course-retrieval-v1` draft 5 and the approved four-course corpus. The
runtime loaded 35 positive and five boundary cases. It did not load or score
any of the 60 `heldout_draft` cases and did not call an external provider.

At run time, only 1/100 cases was researcher-verified and 0/100 was
independently reviewed. Results are therefore preliminary engineering and
method-development evidence. They cannot select the production retriever or
support a held-out generalization claim.

The private source result is retained at
`experiments/runs/cross_course_retrieval_pilot_v1/development_result.json`,
SHA-256
`7fc20b73b38540be46e9bc6f31a6e938fd452045697afd19c2759e0ea9de1b09`.
The run used Git revision
`d6b89abffd841d5de5b9bf414ebd0eaf3efcd529` with a dirty tree containing
the prospective pilot implementation. The run recorded its implementation-tree
hash internally. Private queries, rankings, and lecture text remain ignored.

## Configuration

Every method searched only the course context authorized for that case:

- M0: BM25, `k1=1.2`, `b=0.75`;
- M1: local `Qwen/Qwen3-Embedding-0.6B` dense retrieval;
- M2: M0 and M1 top-20 reciprocal-rank fusion, `k=60`; and
- M3: M2 top-40 candidates reranked by local
  `Qwen/Qwen3-Reranker-0.6B`.

The Qwen revisions, instruction, MPS/float16 configuration, batch size, model
limits, dataset hash, and source hashes are recorded in the private result.

## Development quality

Ranking metrics use unthresholded lists and 35 positive cases. Bootstrap
intervals use 20,000 seeded case-level resamples.

| Method | Complete evidence @3 | 95% bootstrap CI | Evidence Recall @5 | nDCG @10 | MRR |
| --- | ---: | ---: | ---: | ---: | ---: |
| M0 BM25 | 65.7% | 48.6–80.0% | 84.6% | 0.766 | 0.725 |
| M1 Qwen3 dense | 74.3% | 60.0–88.6% | 87.2% | 0.837 | 0.805 |
| M2 BM25 + dense RRF | 80.0% | 65.7–91.4% | 89.7% | 0.842 | 0.795 |
| M3 hybrid + reranker | 82.9% | 68.6–94.3% | 92.3% | 0.876 | 0.864 |

All four methods recorded zero course-isolation violations.

## Paired comparisons

| Comparison | Complete-evidence difference | 95% paired bootstrap CI | Wins / losses / ties | Exact two-sided sign test |
| --- | ---: | ---: | ---: | ---: |
| M2 versus M0 | +14.3 pp | +2.9 to +25.7 pp | 5 / 0 / 30 | 0.0625 |
| M3 versus M0 | +17.1 pp | +5.7 to +31.4 pp | 6 / 0 / 29 | 0.03125 |
| M3 versus M2 | +2.9 pp | 0.0 to +8.6 pp | 1 / 0 / 34 | 1.0000 |

Hybrid fusion produced five of the six complete-evidence improvements over
BM25. Reranking added one further success and did not resolve the remaining
four CS5421 and two IT5100B failures. This makes M2 the higher-value next
research candidate even though M3 has the largest descriptive score.

## Boundary and operational evidence

The five boundary cases were assigned prospectively and deterministically
across course contexts. All methods achieved 5/5 abstention after thresholds
were set just above their maximum boundary score, but these thresholds were
calibrated and measured on the same five cases. That result is not a
generalization estimate.

The fixed execution order warmed shared dense-query execution, contaminating
cross-method latency comparisons. Latency is therefore retained only as
descriptive operational evidence. M3's local median was approximately 108
seconds per query, showing that this exact local reranker configuration is not
deployment-ready, but hardware timing is not used as the retrieval-quality
gate. External-provider cost was USD 0.

## Failures and limitations

- Attempt 001 failed after 32/40 cases because null boundary targets were not
  routed into a course context. It is separately registered as invalid.
- The dataset was drafted and semantically QC'd with model assistance; only one
  case had researcher verification at run time.
- The five boundary cases are a calibration sample, not adequate evidence for
  real-world abstention accuracy.
- Model-authored wording may favor semantic retrieval.
- The paired sample is small; the M2-versus-M0 sign test is not below 0.05 even
  though its seeded bootstrap interval is positive.
- Fixed-order latency is not a clean hardware comparison.
- No held-out result exists.

## Decision

**Refine.** Keep BM25 as the deployed rollback control. Carry M2 hybrid fusion
into the fully researcher-verified comparison because it supplies most of the
observed completeness gain. Retain M3 as an ablation, not the default
candidate. Do not update the component profile until all 100 cases are
researcher-verified, at least 20 receive independent review, and a prospective
sealed evaluation is completed.
