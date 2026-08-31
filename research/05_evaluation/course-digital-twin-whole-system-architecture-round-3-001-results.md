# Whole-system architecture round 3 results

## Outcome

**Completed Refine.** The one permitted Round 3 execution completed over all
481 cases from the untouched third development fold. All candidate responses
were persisted before hidden gold was opened. There were no provider calls,
tokens, paid cost, operational failures, severe unsupported releases, or
boundary errors.

No architecture passed every frozen hard gate.

| Architecture | Grounded factual success | Answerable action | Boundary action | Evidence@3 | Recall@5 | Severe releases |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Typed-target control | 91.64% | 97.91% | 100% | 98.69% | 98.69% | 0 |
| Source-range candidate set | 89.82% | 98.96% | 100% | 99.74% | 99.74% | 0 |
| Source-range plus ambiguity clarification | 79.90% | 84.86% | 100% | 99.74% | 99.74% | 0 |

The typed-target control was the strongest Round 3 condition, but it remained
below the 95% grounded-success, 98% claim-precision, 95% claim-recall, 98%
citation-precision, 95% citation-recall, and 100% source-version gates. Its
source-family bootstrap interval was 89.35%–95.27%.

## Failure analysis

The typed-target control had 32 answerable failures:

- 8 used an incorrect non-answer action;
- 28 lacked complete canonical citation lineage;
- 30 omitted at least one canonical answer span;
- 5 did not retrieve all canonical evidence within the first five results;
- failures concentrated in definition/explanation and paraphrased questions
  (13 each), with two direct, two multi-evidence, and two structured-code cases.

The non-strict source-range candidate improved retrieval coverage but selected
the wrong repeated source region often enough to increase answerable failures
from 32 to 39. The strict ambiguity candidate treated many single-token but
answerable targets as ambiguous, increasing answerable failures to 77. This is
evidence that stronger source scoping alone is insufficient; semantic target
resolution and calibrated clarification must be designed jointly.

Four control cases exposed a scorer serialization limitation: semantically
equivalent RST roles appeared as both `:rfc:1939` and ``:rfc:`1939```.
Counting those four as a disclosed best-case sensitivity raises grounded
success only to 92.69%, still below the frozen 95% gate. The primary result is
not rewritten.

## Decision

Record **Refine** and select no release architecture. The typed-target method
is retained only as the strongest diagnostic control. The fresh 1,000-case
confirmation, known 10,000-case regression, 820-case autonomy evaluation, and
downstream profile/learning proxies remain unopened because the prerequisite
architecture gate did not pass.

A successor must use fresh development evidence and compare a coherent
semantic-target resolver against this typed-target control. It must not tune or
rescore the three opened folds as if they were fresh confirmation data.

## Reproducibility and limitations

- Execution revision: `a3fe4fc2c57d91c86f71a5102eefa371dfb84303`.
- Raw result SHA-256: `1826e0d6825271c3ca78cf68619f4e0c2342b0f73b0bd1cea993e26ebc8a60aa`.
- Response SHA-256 values: control `29c679d0ee8e06a1f4e3335f48428a16144423f969fff0a2506668ba39184700`, source-range `f6a74704018d030511236ee71c0d1c349a676ecf22cab4d7a643f1b73dd38708`, ambiguity-aware `c015f5d8d27511d7c15236cae7c63e87d6e96e8de3427a9279f57d6c963c2a5c`.
- Generated per-case responses remain ignored; the aggregate record is
  committed.
- This network-free extractive comparison does not estimate provider
  generation, professor fidelity, real usability, or student learning.
- There were no real-human participants or human judgments.
