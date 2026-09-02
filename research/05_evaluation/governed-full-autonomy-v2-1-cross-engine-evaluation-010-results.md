# Cross-engine full-autonomy evaluation 010

## Decision

**Refine / no release.** No engine passed the combined factual-grounding and
full-autonomy gates. The fresh sealed 1,000-case confirmation, known
10,000+1,000 regression, proxy synthesis, and local release qualification were
not opened. The one-time paid authority is revoked.

## Execution

- Revision: `8786375bd4e20357c098abcc1eac58bebadba2b0`
- Scope: six engines × 500 factual candidate + 100 paired control cases, then
  six engines × 820 actual-product autonomy cases
- Durable cases: 8,520
- Provider calls: 22,348 (4,096 failed, including 3,083 malformed responses)
- Tokens: 10,925,698 input / 2,105,815 output
- Cost: USD 12.538784948
- Provider-call p95 latency: 4,669.325 ms
- Private data and human participants: none

## Headline results

| Engine | Factual fully grounded | Boundary safety | Autonomy safe grounded | Autonomy result |
| --- | ---: | ---: | ---: | --- |
| E0 deterministic | 60.0% | 100% | 100% | Pass |
| E1 GPT-5.4 nano | 36.75% | 100% | 96.707% | Fail |
| E2 GPT-5.6 Luna | 46.75% | 100% | 96.098% | Fail |
| E3 GPT-5.4 mini | 49.0% | 100% | 100% | Pass |
| E4 DeepSeek V4 Flash | 44.5% | 100% | 36.585% | Fail |
| E5 Terra planner + GPT-5.4 mini | 50.5% | 100% | 99.878% | Fail by one case |

Every factual condition failed the frozen 95% fully grounded gate and the
claim/citation precision and recall gates. Every condition retained 100%
boundary safety and source-version validity with zero severe unsupported
releases.

## Causal interpretation

The factual failure contains two separable causes.

1. A shared product-integration defect caused exactly 100/500 cases in every
   engine to return `HierarchicalRetrievalError: precomputed retrieval lacks
   active case binding`. The failures covered all four answerable questions in
   25 clusters. This is a common runtime/context binding defect, not an
   engine-quality difference.
2. The defect does not explain the complete gap. Even if those 100 cases are
   removed from the denominator, the best condition remains far below the 95%
   fully grounded requirement, and claim/citation quality remains inadequate.
   This is a genuine evidence-to-answer method failure.

The autonomy architecture itself is substantially stronger. E3 passed all
820 deterministic autonomy gates, including authority, citation lineage,
eligibility, state/action/delivery reconciliation, restart, transition, goal
termination, and safe grounded autonomous success. E5 missed the exact primary
gate by one case. E4 exposed a separate DeepSeek planner-contract incompatibility
that produced repeated configuration failures and safe fallback.

## Decision and limitation

Retain T0/E0 as rollback and E3 as the strongest provider-backed autonomy
candidate, but do not select or deploy an LLM-backed release. The successor
must fix shared retrieval case binding and redesign evidence-to-answer
generation on fresh development data. Attempt 002 must not be tuned or rerun.

This public-synthetic, model-assisted evaluation supports claims about system
grounding, policy, persistence, and simulated autonomy only. It does not prove
real-professor fidelity, real-student usability, or real learning improvement.
Raw ledgers remain ignored; their hashes are bound in the machine record.
