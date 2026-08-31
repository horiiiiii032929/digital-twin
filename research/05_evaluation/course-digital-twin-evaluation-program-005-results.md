# Finite evaluation program 005 result

## Outcome

Program 005 is a valid `completed-refine` development result. All 452 required
references passed the matchability gate and retrieval passed, but the actual T0
product failed the preregistered 500-case quality gates. The sealed
10,000+1,000 stages were not opened.

The candidate reached 95.0% all-evidence@3 and 97.5% Evidence Recall@5, so
retrieval was not the primary failure. Fully grounded factual success was
51.75%; answerable action accuracy was 70.5%; boundary accuracy was 75.0%;
claim precision/recall were 52.75%/52.75%; and citation precision/recall were
61.75%/61.75%. Nine severe unsupported releases occurred. In the paired
100-case subset, boundary safety was 70.0% for the candidate and 90.0% for the
control; the supported-answer retention lower confidence bound was -15 points.

## Diagnosis and finite successor

The failure is downstream of retrieval. The router identified ambiguity but
the product did not emit `clarify`, while the generator could still abstain or
select incomplete claims after adequate evidence was retrieved. Program 006 is
one method-level successor: code owns action and policy, and GPT-5.4 may only
select one or two exact supported claim spans with original citations. This is
a known-development-set correction; the sealed final set remains untouched.

## Independent supplements

- True visual reached 16/30 complete evidence@3, 74.99% atomic Recall@5, zero
  boundary releases, and 30/30 original-region lineage. Nine descriptions
  contained unsupported details, so visual remains `Go Deeper`.
- Synthetic C0-C2 completed all 36 calls. It used a synthetic profile and is
  not professor-fidelity evidence.

## Accounting and limitations

- 649 calls/batches and USD 0.85525693 total.
- Public licensed sources and synthetic profiles only; no private/student data.
- GPT-5.4 nano advisory review was non-authoritative and was not independent
  human annotation.
- The development set is now known and cannot support a fresh confirmatory
  claim.

## Decision

Record `Refine`, revoke program 005 authority, and permit only program 006's
finite method-level correction. A valid program 006 development failure stops
the factual branch; a pass may open the untouched 10,000+1,000 stages
automatically under the existing program authority.
