# Source-semantic evidence-atom comparison result

## Decision

`Refine / No Release`. The source-side semantic-atom candidate is the strongest
fresh development method so far, but it did not pass every frozen release gate.
Keep it only as development evidence; retain `typed-target-evidence-v1` as the
operational rollback. Do not open the fresh 1,000-case confirmation, known
10,000+1,000 regression, or provider-backed 820-case autonomy evaluation.

## Result

The network-free comparison executed once from clean revision `354c745` on 500
new cases across 100 source-range-disjoint clusters. Both conditions persisted
all responses before hidden gold opened. There were no provider calls, tokens,
paid cost, private data, operational failures, or severe unsupported releases.

| Metric | Typed-target baseline | Source-semantic atoms | Gate |
| --- | ---: | ---: | ---: |
| Fully grounded factual success | 95.25% | **96.0%** | 95% |
| Source-family lower 95% bound | 92.75% | **93.5%** | 93% final diagnostic |
| Answerable action accuracy | 99.5% | **100%** | 95% |
| Boundary action accuracy | 100% | 100% | 98% |
| Atomic-claim precision / recall | 95.38% / 95.38% | **96.13% / 96.13%** | 98% / 95% |
| Citation precision / recall | 95.38% / 95.38% | **96.13% / 96.13%** | 98% / 95% |
| All-evidence@3 / Recall@5 | 99.5% / 99.75% | **100% / 100%** | 90% / 95% |
| Source-version validity | **100%** | 99.75% | 100% |
| p95 retrieval/assembly latency | **1.35 ms** | 4.56 ms | descriptive |

The candidate improved fully grounded success from the prior fresh comparison's
91.0% baseline and the rejected semantic-target candidate's 81.0% to 96.0%.
It also retrieved every required range in the first three results. Nevertheless,
16/400 answerable cases selected a neighboring semantic atom during evidence
assembly. Those errors made claim and citation precision 1.875 percentage
points short of the frozen gate. One wrong-atom citation also failed the exact
source-version/hash validity gate.

## Causal audit

This is a valid method failure, not a harness or transport failure. The required
atom was present in the top three for every failed case, but the gate chose a
nearby atom with overlapping low-information terms. Representative collisions
include `u.left` versus `u.right`, two `removeFixup` statements, two `letters`
code lines, and neighboring scheduling facts. The remaining defect is therefore
top-k atom disambiguation and authoritative target selection, not corpus recall,
boundary routing, provider reliability, or source registration.

## Release implication

- Do not tune or rerun this candidate on the now-known 500 cases.
- Do not promote it from development evidence to the product profile.
- Do not open fresh final or autonomy evaluation stages whose prerequisite is a
  grounding `Keep`.
- Keep the deterministic fail-closed local R1 available as a software demo, but
  make a formal **No Release** decision for the autonomous LLM-backed R1.
- A future research successor must change the method at the evidence-selection
  boundary and use new source-disjoint evidence; it is not part of this finite
  release decision.

## Limits

This comparison uses public open educational sources and extractive,
provider-free generation to isolate grounding architecture. It does not prove
professor fidelity, real-student usability, learning improvement, true visual
reasoning, or provider-backed autonomous behavior.
