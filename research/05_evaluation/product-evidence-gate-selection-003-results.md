# Dominance-scoped ambiguity gate selection

## Outcome

Under the registered decision rule the candidate **is not promoted**: both arms
score 16.00% and the rule requires the candidate to be strictly better. The
product keeps `question-targeted-ambiguity-safe-v2`.

That verdict stands. What follows is why it is also not the whole story.

## Result under the registered rule

500 development cases at region granularity, gate as the only variable,
provider calls 0, cost USD 0.

| Arm | Gate | Fully grounded factual success | Severe unsupported releases | Operational failures |
| --- | --- | --- | --- | --- |
| Incumbent | `question-targeted-ambiguity-safe-v2` | 16.00% | 0 | 0 |
| Candidate | `dominance-scoped-ambiguity-safe-v3` | 16.00% | 0 | 0 |

## The candidate did change behaviour

69 answerable cases moved from `clarify` to `answer`. Action accuracy on those
69 is 1.000, answer-span recall is 0.9710 with 67 of 69 perfect, and their
citations match the gold spans exactly. Yet every citation and atomic-claim
score on those cases is 0.0000, and the grounded-success figure does not move.

The same signature appeared in selection 001 and was traced then to corpus
granularity. This time the corpus is right, so the signature points somewhere
else.

## Cause: the citation match short-circuits on region identity

`evidence_ranges_overlap` in `factual_qa_contract`:

```python
if observed.region_id is not None or expected.region_id is not None:
    return observed.region_id == expected.region_id
```

If **either** side carries a region identity, the canonical character range is
never consulted. The development gold declares `region_id` on 176 of its 456
evidence refs; the other 280 leave it null. A product citing a real region can
therefore never match those 280, even when the source artifact, version, sha256
and character range are identical.

| Gold package | Evidence refs | Declaring `region_id` |
| --- | --- | --- |
| Development | 456 | 176 (39%) |
| **Sealed 10,000-case** | 9,000 | **9,000 (100%)** |

**The sealed benchmark is unaffected.** Every one of its refs declares a region,
so its 25.38% was measured under matching conventions.

## What the correction is actually worth

Re-scoring both arms with the character range consulted when gold declares no
region:

| Arm | Registered scoring | Diagnostic re-score |
| --- | --- | --- |
| Incumbent | 16.00% | 36.80% |
| Candidate | 16.00% | **50.00%** |

The dominance-scoped gate is worth **+13.2 points**, with severe unsupported
releases and operational failures still at zero.

**This is a diagnostic and it does not promote anything.** The registered rule
requires registered scoring reused unchanged, and this measurement changed the
matcher. Promotion needs the contract defect handled on its own terms.

## Why the correction is narrow on purpose

Measured before any code was written, on 263 ambiguous targets:

- **76 have a strictly dominant leader, and in all 76 that leader is the gold
  region.** Zero wrong leaders. These are the refusals the candidate resolves.
- **187 are genuine ties.** Gold sits inside the tied leader set in 184, so
  retrieval is sound, but the best secondary tiebreaker isolates gold in only
  105 and picks a wrong region in 61. Resolving ties would buy coverage with
  unsupported releases, which the sealed benchmark already priced: severe
  unsupported releases fell from 478 to 4 under the current posture.

So the gate resolves what needs no tie broken and refuses the rest. That is a
measured boundary, not a limitation left unexplored.

## Method

`AmbiguitySafeEvidenceGateV1` keeps its behaviour under its own implementation
id; the grounding selection was run before and after the change and returned an
identical 12 failures and 135 passes. The successor adds one class attribute and
one optional analyzer argument defaulting to off. Registered scoring was reused
unchanged for the verdict. No sealed or hidden-gold package was read, rerun, or
rescored.

## Limitations

Development-split evidence selects a method; it is not a generalization claim.
The product retrieves through a dense published index while this comparison
retrieves locally. Public synthetic sources only. No professor fidelity,
student usability, or learning-outcome claim.

## Decision

Keep `question-targeted-ambiguity-safe-v2`. Record
`dominance-scoped-ambiguity-safe-v3` as implemented, measured, and unpromoted,
with the contract defect above as the named blocker rather than a quality
result.
