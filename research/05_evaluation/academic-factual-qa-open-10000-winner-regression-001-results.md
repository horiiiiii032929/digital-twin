# Winner regression on the known 10,000+1,000 benchmark

## Outcome

The confirmation-024 selected system was bound to the sealed Program 011
10,000+1,000 package and run once as a **known-benchmark regression**. It
records **No Release**: 11 of 16 registered gates failed and the frozen scorer
returned `completed-refine`.

This is regression evidence for the selected architecture on a package that
Program 011 already consumed. It is not fresh generalization evidence, and a
pass here would not have been either.

## What the run measured

| Measure | Selected candidate (V3 gate) | Any-hit control | Program 011 T0 |
| --- | --- | --- | --- |
| Fully grounded factual success | 25.38% | 20.80% | 44.16% |
| Severe unsupported releases | **4** | 0 | **478** |
| Operational failures | 0 | 0 | 594 |
| Provider calls | 0 | 0 | 11,354 |
| Cost | USD 0 | USD 0 | USD 39.14 |

Candidate cases: 10,000 (8,000 answerable, 2,000 boundary) across 523 source
families. Control: the frozen 1,000-case paired subset. Zero exact duplicates,
zero malformed outputs, p95 case latency 0.154 ms.

Paired comparison over the 1,000-case subset:

- `supported_answer_retention_lower_95`: **passed**. Estimate +20.45 points,
  95% interval +16.98 to +23.99.
- `boundary_safety_not_worse`: **failed**. Candidate 0.520 against control
  1.000.

The control's perfect boundary safety comes from an any-hit gate that answers
almost nothing at a boundary; its grounded success is lower than the
candidate's. Usefulness favours the candidate, boundary safety favours the
control, and neither dominates.

## Failed gates

`action_accuracy_overall`, `action_accuracy_answerable`,
`boundary_action_accuracy`, `fully_grounded_factual_success`,
`atomic_claim_precision`, `atomic_claim_recall`, `citation_precision`,
`citation_recall`, `source_family_lower_95`, `source_version_validity`,
`zero_severe_unsupported_releases`.

Passed: `canonical_all_evidence_at_3`, `evidence_recall_at_5`,
`malformed_output`, `provider_completion`, `zero_exact_duplicates`.

## Decisive finding

The architecture's failure mode inverted rather than improved. Program 011's T0
released 478 severe unsupported answers and failed 594 cases operationally. The
selected system releases 4 and fails 0, a 99.2% reduction in severe unsupported
release. It pays for that by answering 16.7% of cases and asking the learner to
clarify 69.7% of them.

The clarify rate is not a retrieval failure. On a 100-case probe the target
source cluster is in the top five for 94 cases and ranked first for 84, and the
gate still returns `clarify` on 69 of those. The cause is
`SourceSemanticEvidenceAtomGateV3.assess`: it compares canonical claim classes
across every atom that clears the target's coverage threshold while selecting
only the top-ranked atom, and `normalize_claim_class` is the token set of the
claim text, so two distinct regions almost always carry distinct classes. At
product corpus scale the contest reduces to "two or more regions cleared the
threshold" and fails closed.

Confirmation 024 could not have detected this. Every case it ran published a
release holding exactly one approved chunk
(`governed_full_autonomy_v2_1_actual_product_runtime._install_release` set
`"chunks": [chunk]`), and with one atom the branch cannot fire. Its Keep
decision therefore carries no evidence about the behaviour that distinguishes
the selected grounding architecture.

Both regimes are pinned in
`tests/test_academic_factual_qa_open_10000_winner_gate_regime.py`.

## Method and custody

The sealed package is referenced read-only from the Program 011 output and
verified through a two-level hash chain rooted in git: the committed record's
`ignored_artifacts.construction_result_sha256` verifies
`construction-result.json`, whose `packages` block verifies all five sealed
files. Product execution received course ID and question only. Hidden gold
opened only after both response ledgers reported `completed` with matching
counts, enforced by the frozen scorer's own durability check.

Retrieval is BM25 over immutable atom projections, so the run required no
embedder and no query-vector cache and reached no provider. Each case ran in
its own conversation: T1-v2 keeps a learner belief state, so the course-scoped
conversations Program 011 could safely share under stateless T0 would have made
every case depend on the ones before it. A course-scoped partial ledger
produced before that correction was discarded rather than scored.

Registered thresholds were not changed. Scoring reuses
`score_academic_factual_qa_open_10000.score_packages` and `paired_comparison`
unchanged; this instrument selects no threshold of its own.

- Response ledger SHA-256: `6a80d7f26e4f1b2363bf9bfd69e12aeacc0340e9a2d299c228a71422d832c2ac`
- Hidden gold SHA-256: `540ff6d5071ca1e25b3a07e0cc7d569af7d698cfbe740be29348e018da589380`
- Pairing manifest SHA-256: `979315f203212cc602ff933224022dbc4b34584f4eb66a1a6506805836e7379c`
- Construction result SHA-256: `9c18a734eb17279b3750665a975913557166729d0f0ee354f62a5b1f7d48f205`

## Decision

Record **No Release** on this evidence. Do not rerun or rescore the sealed
package: the distribution of its question wording is now known, so any
correction measured against it would be adaptive rather than independent.

Open one method-level successor,
`SourceSemanticEvidenceAtomGateV4`, which fails closed on a genuine tie
between equally dominant atoms instead of on the presence of weaker ones, and
confirm it on a fresh package whose releases publish a whole corpus. That is
`governed-full-autonomy-v2-1-corpus-confirmation-027`.

## Limitations

Sources and questions are public, synthetic, and drawn from a package this
project has already consumed once. Deterministic source truth controlled every
score; there was no independent external human annotation. The result
establishes nothing about real professor fidelity, real student usability, or
learning outcomes.
