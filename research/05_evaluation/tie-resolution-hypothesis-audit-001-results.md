# Tie-resolution hypothesis audit

## Outcome

**No change shipped.** Three mechanisms for resolving the 187 genuine coverage
ties were measured before any was built. All three were discarded on the
measurement.

This is a negative result recorded so the ties are not re-attacked from the
same angles.

## What remains unresolved

The shipped `dominance-scoped-ambiguity-safe-v3` resolves the refusals whose
leader strictly dominates. What it still refuses are 187 targets where two or
more regions tie exactly on coverage and state different canonical claims.

Retrieval is sound: the gold region sits inside the tied leader set in **184 of
187**. The question is only which of the tied regions to answer from.

## Hypothesis 1 — a secondary measure breaks the tie

| Measure | Isolates gold | Still tied | **Picks a wrong region** |
| --- | --- | --- | --- |
| Shortest claim | 105 (57.1%) | 18 | **61** |
| Coverage density | 105 (57.1%) | 18 | **61** |
| Token density | 102 (55.4%) | 32 | 50 |
| Term proximity | 37 (20.1%) | 93 | 54 |
| Public title anchor | 0 (0.0%) | 184 | 0 |

**Discarded.** The best measure is right 57% of the time and picks a wrong
region in 61 cases. The gate currently refuses those; the change would make it
answer them from the wrong evidence. Severe unsupported releases fell from 478
to 4 under the current posture, and a 57%-accurate tiebreaker spends that.

## Hypothesis 2 — coarse targets manufacture the ties

Target term count correlates with tie width, and single-term targets are half
the problem:

| Target terms | Tie targets | Mean tied candidates |
| --- | --- | --- |
| **1** | **91** | **2.86** |
| 2 | 83 | 2.30 |
| 3 | 13 | 2.15 |

The questions do carry more. Across the 91 single-term targets the question
drops 2 to 7 additional concept terms — most often 4 — before the target is
formed. `What fact does "Addition" state about search x?` yields the target
`search x`, whose only surviving concept term is `search`, while the question
itself names `addition`.

So the information exists and is unused. **Confirmed as a real property**, and
it motivated hypothesis 3.

## Hypothesis 3 — the public title anchor supplies the missing discrimination

`_has_public_title_anchor` already decides whether a question explicitly names a
region's title, and the atom-line gates already consult it. The uniqueness
analyzer the shipped gate uses does not.

| Outcome on the 187 tie targets | Count |
| --- | --- |
| Anchor narrows the tie | **0 (0.0%)** |
| Every tied leader is equally anchored | 123 (65.8%) |
| No tied leader is anchored at all | 64 (34.2%) |

**Discarded.** The tied regions are different sentences inside the *same*
titled section, so the title matches all of them or none. It cannot discriminate
within a section, which is exactly where these ties live.

## What this rules out

Any tiebreaker built from the question and the candidate text alone. The tied
candidates are equally covered, equally titled, and differ only in what they
assert. Distinguishing them needs information neither the question nor the
passage currently carries — the learner's intent, or a source-side relation the
corpus does not encode.

Refusing here is the designed behaviour, and these measurements are the reason
to keep it rather than an admission that it was not examined.

## Method

Every measurement ran before any implementation, on the 500-case development
corpus at region granularity, with zero provider calls and no code change. The
sealed package was not read, rerun, or rescored.

## Limitations

Development-split evidence. Public synthetic sources only. The measurements
bound what these three mechanisms can do on this corpus; they do not prove no
mechanism exists.
