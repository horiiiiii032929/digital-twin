# Cross-course benchmark v1 QC amendment

Date: 2026-07-28

Status: prospective amendment before draft-2 construction

## Trigger

Automated and assistant QC of draft 1 found:

- 70/100 cases labelled direct, 2 paraphrase, 3 multi-step, and 25 boundary;
- the 15 cross-course-confusion cases reused answerable gold chunks, leaving
  only 60 unique chunks across 75 positive cases;
- three no-evidence cases were trivially outside the course domains; and
- several claims were supported by the full chunk but not by the selected
  quote, while a smaller set contained a claim/evidence mismatch.

Draft 1 remains private and traceable. It is not eligible for evaluation.

## Amended construction

Keep the 100-case and 40/60 development/held-out-draft totals:

- 50 single-evidence answerable cases;
- 10 multi-evidence answerable cases, requiring two page-local chunks;
- 15 no-evidence cases, with at least 12 course-adjacent hard negatives;
- 15 cross-course-confusion cases whose target chunks are not reused by the
  answerable slice; and
- 10 adversarial/integrity cases.

Positive difficulty targets are 34 direct, 31 paraphrase, and 10 multi-step
cases. Fifteen of the direct/paraphrase cases are separately marked as
cross-course confusion and require semantic discrimination. The label
definitions are:

- `direct`: one explicit fact with substantial query/evidence vocabulary;
- `paraphrase`: one explicit fact expressed with materially different wording;
- `multi_step`: two required claims supported by two distinct gold chunks.

## Additional hard gates

- At least 70 unique gold chunks across 75 positive cases.
- No gold chunk is reused across answerable and confusion slices.
- Every multi-step case has exactly two required claims and two distinct gold
  chunks.
- Every selected supporting quote directly supports its aligned claim.
- At least 12/15 no-evidence cases are course-adjacent rather than trivially
  out of domain.
- Any content change resets prior researcher and second-review approval.

The local drafting model remains an authoring aid only. Draft 2 still requires
researcher verification of all cases and independent review of at least 20.
