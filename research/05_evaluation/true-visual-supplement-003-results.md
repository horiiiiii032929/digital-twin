# True-visual supplement 003

## Decision

`completed-refine`. Do not select the visual-description retrieval candidate.
Retain the text/OCR fallback and preserve this result without tuning or rerunning
the same 60 cases.

## Result

The bounded run processed 30 public or deterministic-synthetic visual assets:
10 tables, 10 equations, and 10 diagrams. Each asset had one answerable and one
boundary case. GPT-5.4 nano produced one question-independent structured
description per asset.

| Measure | Result | Frozen gate | Pass |
| --- | ---: | ---: | :---: |
| Complete visual evidence@3 | 27/30 (90.0%) | at least 90.0% | Yes |
| Visual-fact-complete cases | 19/30 | at least 29/30 | No |
| Mean visual-fact recall | 73.22% | at least 96.67% | No |
| Mean visual-fact precision proxy | 35.04% | at least 90.0% | No |
| Reference-unmatched description segments | 219 | 0 | No |
| Boundary-policy accuracy | 30/30 (100%) | 100% | Yes |
| Boundary answer releases | 0 | 0 | Yes |
| Original-region lineage | 30/30 (100%) | 100% | Yes |

All 30 exact-model calls completed with zero retries or failures. The run used
54,749 input tokens and 11,610 output tokens, cost USD 0.0254623, and had a
maximum observed call latency of 6.67 seconds. Six exact duplicate semantic-list
values across three assets were removed under the preregistered normalization
rule and remained accounted for.

## Interpretation

The candidate was operationally stable and preserved its source-image and
region authority. Boundary behavior also remained fail closed. Quality was not
strong enough for selection: three answerable assets were missing from the top
three, and only 19 descriptions recovered at least 90% of the corresponding
canonical answer. The weakest descriptive slice was diagrams; tables and
equations were substantially better in this small development set.

The frozen precision and unsupported-segment calculations compare every
transcription/entity/relationship segment against the tokens in a single
canonical answer. That answer is sufficient for the question but is not an
exhaustive annotation of everything visibly true in the asset. Consequently,
the 219 count means “not supported by the frozen reference list”; it must not be
reported as 219 independently verified hallucinations. This measurement
limitation does not reverse `Refine`, because retrieval and recall gates also
failed.

## Boundaries

- This is a development supplement, not representative multimodal evidence.
- It does not exercise the complete student product response path.
- The assets are public or synthetic; private course and student data were not
  used.
- No visual implementation is added to the selected release profile.
- Raw provider output remains ignored. The durable record binds its hashes,
  accounting, configuration, and aggregate metrics.
- The one-time provider authorization is revoked.
