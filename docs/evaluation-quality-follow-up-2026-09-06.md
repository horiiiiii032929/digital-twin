# Evaluation quality follow-up: completed calibration and uncertainty remedy

The new [registered diagnostic](../research/05_evaluation/evaluation-calibration-cluster-development-20260906-001-results.md) completes two previously missing checks: explicit adversarial calibration of the mechanical scorer and reproducible analysis using paired cases and whole-history/course clusters. It changes no tutor implementation or old score.

## What is now established

The scorer reliably catches the selected structural failures, but all four selected substantive defects—unsupported extra prose, contradiction, irrelevant elicitation, and paraphrased answer disclosure—still receive a mechanical pass. The new extraction-residue advisory flags those examples for review, while deliberately retaining its limitations: ordinary good prose also requires review, duplication can escape it, and malformed provenance still needs the original scorer. It is a warning against false assurance, not a semantic classifier.

The existing 44-case comparison contains 11 candidate-only mechanical passes and no incumbent-only passes, but only four synthetic course clusters. A seeded whole-course bootstrap and leave-one-course-out analysis now show how results depend on course composition. The full 24-history simulation is analyzed as 12 paired persona/profile contexts, not hundreds of independent students. Both analyses are reproducible and include unfavorable and uncertain findings.

## Quantity and quality by evidence family

| Evidence | Appropriate unit and established use | Remaining gap |
| --- | --- | --- |
| Natural question development | Authored question/source family; identifies retrieval and adequacy failures | Fresh representative final-candidate reevaluation; exact text checks do not establish semantic quality |
| Four mini-course live005 | 44 paired cases clustered in4 authored courses; mechanical composition comparison | Final v2 differs from v1; candidate needs representative reevaluation and semantic/instructor review |
| Finite Luna/Terra dialogue | Four matched histories per model,16 turns; targeted regression diagnosis | One unblinded reused realization per model; cannot rank general teaching quality |
| Full30-day operating simulation | 12 persona/profile pairs,24 histories,1 seed; persistence/delivery/failure behavior | Adaptive synthetic attendance and four rules do not measure learning or student utility |
| Ingestion/dashboard journeys | Distinct API/UI and negative-path scenarios | Functional checks do not evaluate ingestion fidelity over every approved format/course or insight usefulness |
| Concurrency comparison | Route requests, provider in-flight calls, and end-to-end histories distinguished | In-process synthetic identity and co-resident workloads do not qualify deployed auth or production capacity |
| Professor assessment packet | Reused examples for prospective instructor feedback | No actual human review completed; no instructor fidelity score |

These gaps should not be collapsed into a request for more of the same simulated turns. Fresh independent source/question families and appropriately calibrated judgments address quality; repeated seeds and workload contexts address operational robustness. Four approved heterogeneous courses in the quality plan remain a representative evaluation requirement. Existing permitted course portfolios and source approvals must not be described as absent: the missing step is a fresh evaluation of this candidate using the appropriate approved versions/splits and explicit external-provider permission scope.

## Completed checks and next evidence

Ten new deterministic tests cover adversarial calibration and cluster-analysis invariants. The named run preserves all input/code hashes, no-network status, original mechanical outcomes, and per-history denominators. Independent instructor assessment remains human-only. Any cross-model advisory judge should first be tested on all authored calibration defects without pruning, use blinded response labels, and report its own errors; it remains AI advice on reused development data, not independent human or held-out qualification.

## Subsequent live diagnostics

The [semantic reviewer transfer audit](../research/05_evaluation/completion-semantic-review-development-001-live-002-results.md)
passed 64 calibration judgments but found important errors on actual tutor
outputs, including missed premature disclosure. The judge is dropped as a
quality decision instrument; neither its raw acceptance counts nor mechanical
passes establish accuracy. A [blinded human packet](../research/05_evaluation/professor-review-quality-audit-20260906/README.md)
contains 22 responses with blank ratings; no human assessment has occurred.

The [bounded-contract comparison](../research/05_evaluation/bounded-contract-progression-development-001-live-001-results.md)
reduced schema failures from 14/36 to 0/36 at a fixed cap, and a
[named-referent comparison](../research/05_evaluation/bounded-contract-progression-development-001-referents-live-001-results.md)
recovered targeted blocked questions. These small synthetic development packets
support narrow opt-in fixes, not broad teaching qualification. The default
selected profile remains unchanged. A separate [usage-integrity repair](../research/05_evaluation/provider-usage-integrity-development-001-results.md)
prevents absent provider token counts being treated as known zero.

The combined ingestion/recovery and actual authenticated HTTPS load evidence is
recorded in the [operational audit](evaluation-mixed-source-and-load-audit-2026-09-06.md).
It supersedes the absence of such a joined development test, while retaining
limits on workload diversity, public deployment and long-term uptime.
