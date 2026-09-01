# Source-semantic-atom failure-validity audit result

## Decision

`Refine / No Release remains`. The frozen 98% claim/citation and 100%
source-version gates are not shown to be too strict. The 16 failures expose a
dual defect: the reference package labelled non-unique questions as answerable,
and the product answered those questions instead of clarifying.

The original 500-case result, metrics, gates, and `completed-refine` decision
remain immutable. This audit is an analysis correction and does not rescore the
official result.

## Audit scope and method

The audit recomputed all 500 scores from the immutable response package and
recovered exactly the original 16 failed answerable cases. For every case it
then verified deterministically that:

- the designated gold range was present in the first three retrieved ranges;
- every selected claim was an exact canonical rendering of its cited approved
  source range;
- at least two distinct retrieved source ranges plausibly matched the public
  wording.

Codex then reviewed the public question and the cited source alternatives case
by case using a frozen four-way relationship taxonomy. This was an LLM-assisted
semantic audit, not independent external-human annotation. No provider API was
called and no private or final data was used.

## Findings

| Finding | Cases | Interpretation |
| --- | ---: | --- |
| Gold range retrieved in top three | 16/16 | Corpus recall was not the failure |
| Selected claim exactly source-supported | 16/16 | The responses did not invent these claims |
| Public question did not uniquely identify its gold atom | 16/16 | The answerable reference label was invalid for release scoring |
| Correct safe action was `clarify` | 16/16 | The product ambiguity router also failed |
| Evaluator-only false positive | 0/16 | Accepting alternate citations alone would hide the unsafe action |

The selected-answer relationships were nine alternative-supported, three
partial-supported, three conflicting-supported, and one unrelated-supported.
Representative questions used low-information targets such as `If you`,
`letters`, `h1 h2`, `minutes prepare`, and duplicated `minutes prepare` targets.

## Diagnostic sensitivity

If the 16 cases are descriptively relabelled from `answer` to `clarify`, while
leaving the persisted product responses unchanged, overall action accuracy is
96.8% and boundary action accuracy is 100/116 = 86.21%. These values are
diagnostic only; they do not replace the official metrics. They show that the
original 100% boundary score was optimistic rather than that the 98% precision
gate was unfairly strict.

## Required correction

The next version must change both sides before using fresh evidence:

1. Reference construction must reject non-unique wording before sealing,
   permit multiple source ranges only when each independently answers the
   question, and include planted ambiguity controls.
2. The product must return `clarify` when multiple plausible atoms remain or
   the evidence margin does not establish a unique target; it must not generate
   an answer first and repair afterward.
3. A new evaluator must be calibrated on clean, alternate-valid, partial,
   conflicting, and ambiguous controls before a new source-disjoint comparison.

The known 500 cases may be used only as regression diagnostics. The release
decision remains No Release, and the fresh 1,000, known 10,000+1,000 rerun, and
provider-backed 820-case autonomy stages remain closed.

## Limits

The semantic uniqueness judgements were produced by Codex in the current
session and were not independently annotated by an external human. This audit
tests validity of the observed failures; it does not establish professor
fidelity, real-student usability, learning improvement, or autonomous release
quality.
