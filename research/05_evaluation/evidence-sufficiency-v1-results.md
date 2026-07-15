# Evidence sufficiency v1 results

## Run identity

- Result ID: `evidence-sufficiency-v1-clean`
- Component: retriever evidence-sufficiency boundary
- Status: inconclusive
- Date and owner: 2026-07-15, Digital Twin project
- Code revision: `edee299607910b781cbbbdfa3cec6621289b48cb`
- Working tree: clean
- Reproduction: `npm run benchmark:evidence-sufficiency`
- Runtime: Python 3.12.13, FastEmbed 0.8.0, and local
  `BAAI/bge-small-en-v1.5`
- Generated artifact: `reports/generated/evidence-sufficiency-v1.json`
  (ignored)
- Predecessor: `retrieval-v2-clean`
- Paid API calls: zero

## Decision context

The experiment asked whether an explicit, swappable gate could stop weak
vocabulary-sharing out-of-domain retrieval before generation without hiding
ranking failures or refusing too many answerable questions. All candidates used
the same BM25 v1 ranker (`k1=1.2`, `b=0.75`) and returned only its evidence.

The pre-run prediction was that absolute score would be brittle, lexical
coverage would trade abstention against paraphrases, and independent semantic
agreement would provide the best balance while still risking nearby-domain and
multi-evidence failures. Metrics, gates, and selection order were frozen in
[`the experiment plan`](../04_experiments/2026-07-15-evidence-sufficiency-v1-plan.md)
before the held-out run.

## Data and sample size

- Corpus: `synthetic-web-security-v2`, 40 chunks from 16 sources; 38 active and
  eligible chunks
- Calibration: 30 new cases, comprising 18 answerable and 12 vocabulary-sharing
  no-evidence queries
- Held-out: 50 newly frozen cases, comprising 32 answerable and 18 no-evidence
  queries
- Held-out answerable slices: 5 exact, 8 paraphrase, 6 multi-evidence, 4
  distractor, 5 ambiguous, and 4 permission/version
- Permission and sensitivity: synthetic-only; one prohibited chunk and one
  superseded source version remain in the corpus to exercise filtering
- Exclusions: private course material, multilingual queries, figures, tables,
  cross-encoders, rerankers, and live LLM judgments

The 18 held-out negatives make each false answer visible as 5.56 percentage
points. This is appropriate for rejecting obviously unsafe baseline gates, but
too small for a narrow production confidence interval. Raw counts and slices
therefore carry more weight than asymptotic uncertainty claims.

## Exact calibrated configurations

| Candidate family | Frozen configuration | Calibration answerable recall | Calibration no-evidence | False answers | Eligible |
| --- | --- | ---: | ---: | ---: | --- |
| Minimum raw score | BM25 raw score ≥ 5.0 | 1.000 | 0.417 | 7/12 | No |
| Lexical coverage | ≥0.40 coverage, ≥1 matching term, top 3 hits | 1.000 | 0.750 | 3/12 | No |
| Semantic agreement | BGE-small normalized score ≥0.85, top 5, no source-overlap requirement | 0.944 | 0.917 | 1/12 | No |

No candidate satisfied the calibration requirement of zero false answers and
answerable recall at least 0.90. The best measured configuration from each
family was still frozen and evaluated so failed approaches remain comparable.
Calibration failure remained a test hard-gate failure and could not be repaired
by accidental held-out performance.

## Held-out aggregate results

| Candidate | Answerable recall | No-evidence accuracy | Balanced accuracy | False answer | False abstention | Recall@3 | nDCG@3 | Conditional Recall@3 | Gate latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Any-hit control | 0.969 | 0.000 | 0.484 | 18/18 | 1/32 | 0.812 | 0.776 | 0.839 | 0.001 ms |
| Semantic agreement | 0.750 | 0.722 | 0.736 | 5/18 | 8/32 | 0.641 | 0.635 | 0.854 | 5.745 ms |
| Minimum raw score | 0.844 | 0.278 | 0.561 | 13/18 | 5/32 | 0.719 | 0.709 | 0.852 | 0.002 ms |
| Lexical coverage | 0.781 | 0.222 | 0.502 | 14/18 | 7/32 | 0.656 | 0.642 | 0.840 | 0.016 ms |

The conditional Recall@3 values look better because abstention removes many
hard cases from the denominator. The unconditional columns correctly expose
the resulting loss and are the selection metrics.

## Important slices

| Candidate | Exact accepted | Paraphrase accepted | Multi-evidence accepted | Ambiguous accepted | Permission/version accepted | No-evidence rejected |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Any-hit control | 5/5 | 8/8 | 6/6 | 4/5 | 4/4 | 0/18 |
| Semantic agreement | 5/5 | 6/8 | 5/6 | 3/5 | 2/4 | 13/18 |
| Minimum raw score | 5/5 | 8/8 | 6/6 | 2/5 | 2/4 | 5/18 |
| Lexical coverage | 5/5 | 4/8 | 5/6 | 4/5 | 3/4 | 4/18 |

## Hard gates

Every candidate preserved permission and active-version filtering with zero
safety violations. Every learned candidate failed calibration eligibility,
held-out zero-false-answer behavior, no-evidence accuracy 1.00, answerable recall
0.90, balanced accuracy 0.95, and the 95% unconditional ranking non-regression
requirements. Semantic agreement also exceeded the predeclared 1 ms added gate
latency limit. No candidate is eligible.

## Operational results

- Any-hit, raw-score, and lexical gates added less than 0.02 ms mean latency.
- Warm-cache semantic agreement added 5.745 ms mean latency, excluding primary
  BM25 retrieval.
- The local BGE-small model reused the ignored approximately 134 MB cache from
  retrieval v2.
- Model cold-start and native ONNX resident memory were not measured in this
  run; no provider, token, or monetary cost was incurred.

## Failures and surprises

The any-hit control answered all 18 vocabulary-sharing negatives. This proves
that “BM25 returned something” is not an evidence-sufficiency rule. It also
abstained on `es-test-amb-03` because BM25 itself found no lexical hit, showing
that a downstream gate cannot repair missing ranking evidence.

Semantic agreement was strongest but still accepted five out-of-domain cases:
CPU cache, legal authorization, hotel sessions, banking transactions, and
private-key diary language. It also rejected eight answerable questions,
especially paraphrase, ambiguous, and permission/version cases. These are
open-set domain-confusion failures rather than permission leaks.

Raw BM25 score was not a probability across queries. Several negatives scored
higher than valid ambiguous or policy questions because they combined multiple
rare corpus terms. Lexical coverage failed for the same reason and rejected
valid paraphrases with deliberately different wording.

## Validity review

- Calibration/test separation: preserved
- Retrieval-v2 held-out set used for tuning: no
- Threshold changed after held-out inspection: no
- Source judgments unresolved: none
- Data or evaluator defect found: post-run review found an operator-precedence
  bug in the optional `require_source_overlap=true` predicate. The clean test
  candidate used `false`, so its metrics and decision are unaffected; only the
  unused overlap-true calibration rows are invalid. Commit after the result adds
  a regression test and fixes the predicate.
- Run invalidated: no
- Synthetic/private boundary violated: no

The 1 ms gate-latency limit was too strict for an embedding candidate, although
semantic agreement also failed every important quality requirement. This gate
therefore did not change the decision and should be revised prospectively, not
retroactively, in a successor plan.

Some calibration configurations tied on every quality metric, leaving a single
micro-latency measurement as the final tie-break. Repeated calibration can pick
a behaviorally equivalent tied configuration because micro-timing is noisy.
The clean artifact freezes the exact evaluated choices, all tied families were
ineligible, and no selection depends on the tie. The post-run implementation
uses a deterministic configuration tie-break; a successor should measure
latency through repeated trials rather than use it to break a quality tie.

## Decision

**Refine; select no evidence-sufficiency implementation.** Keep BM25 v1 with
explicit any-hit behavior only as the rollback/control path, not as safe input
to live end-to-end generation. The experimental system profile does not change.
Issue #25 remains blocked from making a grounded end-to-end claim.

## Limitations and follow-up

- Synthetic labels were written by one evaluator and need independent review.
- The corpus is small, English-only, text-only, and from one technical domain.
- Only one embedding model and no cross-encoder, NLI verifier, trained
  answerability classifier, query router, or LLM evidence judge was tested.
- A successor should treat this as open-set answerability classification,
  compare a cross-encoder relevance verifier and a calibrated classifier, use a
  prospectively appropriate semantic latency budget, and add more unrelated
  domains plus near-domain negatives.
- Live generator quality can still be evaluated with controlled oracle evidence,
  but retrieved evidence must not drive a product smoke demo until a successor
  gate passes.

## Learning notes

Ranking and evidence sufficiency are different questions. Ranking asks which
available chunks are most relevant; sufficiency asks whether any available
chunk supports answering at all. BM25 scores and cosine similarity order
candidates but are not calibrated answerability probabilities. A threshold can
therefore improve apparent precision while silently refusing hard valid cases.
Always report false answers, false abstentions, and unconditional ranking
quality together.
