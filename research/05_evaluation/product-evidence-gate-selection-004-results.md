# Dominance-scoped ambiguity gate, scored under the corrected contract

## Outcome

**Promote.** `dominance-scoped-ambiguity-safe-v3` clears every condition the
rule fixed before execution, so it becomes the product's evidence gate once a
fresh local HTTPS release qualification passes.

| Arm | Gate | Fully grounded factual success | Severe unsupported releases | Operational failures |
| --- | --- | --- | --- | --- |
| Incumbent | `question-targeted-ambiguity-safe-v2` | 36.80% | 0 | 0 |
| **Candidate** | `dominance-scoped-ambiguity-safe-v3` | **50.00%** | 0 | 0 |

Severe unsupported releases not worse: **passed**. Operational failures not
worse: **passed**. Grounded success strictly better: **passed**, by 13.2 points.

## What changed since selection 003, and what did not

The responses are byte-identical. Selection 004 re-scores selection 003's own
ledgers. The only difference is the measurement contract.

Selection 003 recorded 16.00% for both arms and did not promote. **That verdict
is not amended.** It was correct under the contract in force at the time, and
the two readings both stay on the record.

`evidence-range-match-correction-001` was pre-registered separately, with its
adoption conditions fixed in advance: identical decisions on every pair present
in the sealed package, and identical suite results before and after. Both hold —
the suites return 50 failures, 561 passes and 22 errors either way.

## The defect that was corrected

`evidence_ranges_overlap` never consulted the canonical character range once
either side carried a region identity:

```python
if observed.region_id is not None or expected.region_id is not None:
    return observed.region_id == expected.region_id
```

A citation agreeing with the gold reference on source artifact, version, sha256
and character range scored a miss whenever exactly one of the two declared a
region. Supplying more provenance than the gold declares made a correct citation
score *worse* than supplying less, which is wrong regardless of what it
measures. Region identities now decide only when both sides declare one.

The development gold declares a region on 176 of its 456 evidence references, so
280 were structurally unmatchable by a product citing real regions. The sealed
package declares one on all 9,000, which is why its 25.38% was never affected.

## Disclosure

The defect was found while investigating this candidate, which benefits from the
correction. It was not sought in order to promote it, but it was found in the
course of trying to, and that ordering is recorded here and in the correction's
own instrument rather than omitted. The correction stands on its own terms: it
is wrong independent of any result, and it moves no recorded result.

## What the gate actually does

Measured on 263 ambiguous targets before any code was written:

- **76 have a strictly dominant leader, and in all 76 that leader is the gold
  region.** Zero wrong leaders. These are the refusals the gate resolves, and
  they need no tie broken.
- **187 are genuine ties, left refused on purpose.** Gold sits inside the tied
  set in 184, so retrieval is sound, but the best available tiebreaker isolates
  it in 105 and picks a wrong region in 61. Buying those with unsupported
  releases is the trade the sealed benchmark already priced at 478 down to 4.

On the 500-case corpus this moves 69 answerable cases from `clarify` to
`answer`, with action accuracy 1.000 and answer-span recall 0.9710.

## Method

`AmbiguitySafeEvidenceGateV1` keeps its behaviour under its own implementation
id. The successor adds one class attribute and one analyzer argument defaulting
to off. Registered scoring was reused unchanged apart from the separately
registered contract correction. No sealed or hidden-gold package was read,
rerun, or rescored.

## Limitations

Development-split evidence selects a method; it is not a generalization claim.
The product retrieves through a dense published index while this comparison
retrieves locally. Public synthetic sources only. No professor fidelity,
student usability, or learning-outcome claim.

## Decision

Promote `dominance-scoped-ambiguity-safe-v3`, conditional on a fresh local
HTTPS release qualification as the registered rule requires. Until that passes,
the shipped gate remains `question-targeted-ambiguity-safe-v2`.
