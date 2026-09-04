# Wrong-region selection audit

## Outcome

**No change shipped.** The second-largest remaining loss bucket was located,
decomposed, and one candidate mechanism was measured and discarded before
implementation.

## The bucket

Under the shipped `dominance-scoped-ambiguity-safe-v3`, the 500-case
development corpus decomposes as:

| Bucket | Cases |
| --- | --- |
| Answerable refused as `clarify` | 183 |
| **Fully grounded** | **170** |
| **Answered, evidence incomplete** | **44** |
| Boundary handled correctly | 80 |
| Boundary `clarify` → `abstain` | 13 |
| Boundary `abstain` → `clarify` | 7 |
| Answered, claim mismatch | 3 |

The 183 refusals are closed by `tie-resolution-hypothesis-audit-001`. The 44
were never examined.

## What the 44 actually are

Every one cites exactly one region against exactly one gold reference, and
citation recall is 0.0 on all 44. That signature usually means a structural
mismatch, so it was checked first — and this time it is not one.

| Cause | Cases |
| --- | --- |
| Right document, wrong region (adjacent or nearby span) | 42 |
| Different document entirely | 2 |

For example, gold cites `protocols/tcp.rst [55857, 55930]` and the system cites
`[55931, 55996]` — the very next region. These are **genuine selection errors**:
the source, version and checksum are right and the sentence is wrong.

## Where the gold region is lost

| Stage | Count |
| --- | --- |
| Gold region retrieved | **41 / 44** |
| Dropped by scoping | 0 |
| **Fell below the 0.5 coverage threshold** | **31** |
| Cleared the threshold but was outranked | **0** |

Retrieval is sound again. The gold region is present in 41 of 44 cases, and in
**zero** cases does it clear the threshold and then lose on rank. The ranking is
not choosing badly; the threshold is removing the right answer before ranking
sees it.

## Hypothesis — lower the coverage threshold

| Threshold | Single-leader targets | Leader is gold | **Leader is wrong** | Boundary cases entered | Precision |
| --- | --- | --- | --- | --- | --- |
| 0.50 (shipped) | 238 | 231 | 2 | 5 | 0.991 |
| 0.40 | 238 | 231 | 2 | 5 | 0.991 |
| 0.34 | 238 | 231 | 2 | 5 | 0.991 |
| 0.25 | 243 | 231 | **4** | **8** | 0.983 |

**Discarded.** Between 0.50 and 0.34 nothing moves at all. At 0.25 the gold
count is unchanged while wrong leaders double and boundary-case entries rise by
three — strictly worse on both axes.

The 31 sub-threshold cases do not become single leaders when admitted. Another
candidate already leads them, so the threshold was never what excluded the right
answer from winning; it only excluded it from being counted.

## What this locates

The loss is upstream of the gate. `_coverage` scores the gold region below a
competitor on 31 of 44 questions the system answers wrongly, and lowering the
bar admits the gold region without promoting it. Any fix has to change how
regions are scored against a target, not which of the scored regions are
eligible.

That is the same conclusion `tie-resolution-hypothesis-audit-001` reached from
the other side: the measure itself, not its threshold and not its tiebreak, is
what limits grounding here.

## Method

All measurements ran before any implementation, on the 500-case development
corpus at region granularity, with zero provider calls and no code change. The
sealed package was not read, rerun, or rescored.

## Limitations

Development-split evidence. Public synthetic sources only. This bounds one
mechanism on this corpus; it does not prove no fix exists.
