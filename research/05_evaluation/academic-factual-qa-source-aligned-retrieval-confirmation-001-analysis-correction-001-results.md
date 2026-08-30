# Source-aligned retrieval confirmation 001 analysis correction

## Corrected interpretation

The frozen run remains a valid **Refine** result under its preregistered exact
region-ID rubric, but the original failure diagnosis overstated the retrieval
method defect. Cross-review and direct reproduction found that overlapping
parent and child regions make exact region identity an invalid proxy for
supporting-evidence presence in this package.

M2 scored 359/400 (89.75%) complete evidence@3 under the frozen exact-ID rule.
Of its 41 reported failures:

- 28 had a same-source top-three parent region containing the complete gold
  character range;
- 9 had a same-source top-three child region containing the exact canonical
  answer text;
- 4 were genuine top-three retrieval misses.

Parent containment alone gives a post-hoc diagnostic rate of 387/400 (96.75%).
Parent containment or answer-bearing child evidence gives 396/400 (99.00%).
These diagnostic rates are not a retroactive pass because their equivalence
rule was not preregistered.

## Root cause

`evidence_ranges_overlap` requires region-ID equality whenever either side has
a region ID. The source registration package emits overlapping parent and
child evidence regions, so semantically sufficient evidence can be rejected
when the retrieved region is a different nested unit. Preflight proved only
that every designated region existed somewhere in the corpus; it did not prove
that evidence atoms were non-overlapping or uniquely authoritative.

The one cross-course boundary mismatch remains unchanged: the deterministic
policy returned `clarify` where gold expected `abstain`, without releasing an
answer.

## Decision

Keep the original record unchanged as frozen-rubric Refine evidence. Do not
select M2 from post-hoc rescoring and do not lower the 90% gate.

The single finite successor is an atomic-M2 coverage-selection confirmation on
a new 100-cluster/500-case source-family-disjoint tranche:

1. freeze non-overlapping minimal evidence atoms as the only citable units;
2. retain parent context only as non-citable search metadata;
3. reject the package if an answer span maps to zero or multiple authoritative
   atoms;
4. retrieve a broader M2 pool and deterministically select three atoms using
   question-only term, identifier, and marginal-coverage signals;
5. compare against unchanged M2 and apply the existing 90%/95%/98%, latency,
   isolation, leakage, and severe-release gates.

The known 500 cases remain diagnostic only. One harness-only correction is
permitted on the fresh successor; a valid quality failure or second invalid
execution stops factual scaling.

## Evidence

- Original result:
  `academic-factual-qa-source-aligned-retrieval-confirmation-001`
- Original execution revision: `55837d0c371c52658b8d4e6d5b67fc3f31cd4c4b`
- Analysis revision: `712e0941b14112daca6daaa102ef859cc249fd69`
- Deterministic scorer:
  `src/digital_twin/evaluation/factual_qa_contract.py`
- Source registration:
  `src/digital_twin/grounding/source_registration.py`
