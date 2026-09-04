# Tie-set citation hypothesis audit

## Outcome

**No change shipped, and the grounding line of work is closed at its measured
floor.** This is the fourth consecutive audit to name a mechanism, measure the
correction before building it, and discard it. Unlike the first three it fails
on two independent grounds, and the second of them is structural.

## The hypothesis

Three audits established that the tie cannot be broken from public inputs. This
one asked a different question: does it need to be broken at all? If the gold
region sits inside the tied leader set, citing *every* tied leader with each
statement attributed to its own region would carry the gold reference without
asserting either rival as the single fact.

## What the ties actually look like

| Measure | Value |
| --- | --- |
| Cases containing at least one tie | 192 |
| Answerable cases containing a tie | 185 |
| Answerable cases where **every** tie covers gold | **181** |
| Boundary cases containing a tie | 7 |
| Mean tied leaders per tie | 2.61 |
| Largest tie | 5 |
| Ties whose leaders agree | **2** |
| Ties whose leaders disagree | **194** |

The retrieval premise holds: in 181 of 185 answerable cases every tie in the
case contains the gold region, and ties are small.

## Why it fails anyway

### It scores zero

`fully_grounded` requires `citation_precision == 1.0`
(`src/digital_twin/evaluation/factual_qa_scoring.py:186`), and citation
precision is matched citations over *emitted* citations. Emitting 2.61 regions
against a gold that declares one gives a precision near 0.38. Every one of the
181 cases would gain complete evidence and lose full grounding in the same
move. The measured gain is **zero cases**, before any safety question is asked.

### It releases contradictions

194 of the 196 tied leader sets contain candidates asserting different things
about the same target. Only 2 agree. Releasing the set as one answer is
releasing a contradiction as a fact, which is the exact failure the gate was
built to prevent and the one the sealed benchmark priced at 478 severe
unsupported releases before the gate existed.

The two failures are independent. Fixing the scoring objection would not touch
the safety objection, and no attribution wording removes it: a learner asking
one question and receiving two incompatible answers has not been answered.

## The floor, stated

| Audit | Direction | Verdict |
| --- | --- | --- |
| `tie-resolution-hypothesis-audit-001` | Break the tie | Best tiebreaker wrong in 61 of 184 |
| `wrong-region-selection-audit-001` | Admit more candidates | 0.34 moves nothing; 0.25 doubles errors |
| `coverage-measure-hypothesis-audit-001` | Score candidates differently | Three definitions within five decisions |
| `tie-set-citation-hypothesis-audit-001` | Do not choose at all | Zero gain; 194 of 196 ties disagree |

Four audits, four directions, one floor. In roughly 185 targets the gold region
is retrieved, admitted and ranked first, tied with a neighbour that says
something else, and nothing in a public question distinguishes them. The
remaining refusals are a measured property of the task under the information
available, not a defect in the gate.

## What this closes and what it does not

Closed: the grounding-selection line of work on this corpus. Further gain
requires an input the system does not have — a disambiguating signal from the
learner, or an answer key that declares which of two equally covering passages
it meant.

Not closed, and deliberately left as stated remainder: 13 boundary cases that
clarify where they should abstain, 7 that abstain where they should clarify,
and 3 claim mismatches. Twenty-three cases, 4.6% of the corpus. Even perfect
handling of all of them would move fully grounded success from 50.0% to 54.6%,
and none of them is a grounding-selection question.

## Method

Zero provider calls. Zero cost. The sealed package was not read, rerun or
rescored. The measurement simulated over the 500-case development region corpus
with the shipped adapter, retriever, generator, policy and gate; the scoring
objection was established by reading the contract, not by running against it.
