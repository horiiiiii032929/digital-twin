# Product evidence gate selection

## Outcome

The product **keeps `structured-lexical-v1`**. The v4 gate that corpus
confirmation 028 recorded Keep for is recorded as **implemented but
unpromoted**, the disposition issue #8 already uses for #155.

The decision rule was committed before any arm ran.

## Result

500 development cases, committed gold, everything held fixed except the
evidence gate. Provider calls 0, cost USD 0.

| Arm | Gate | Fully grounded factual success | Severe unsupported releases | Operational failures |
| --- | --- | --- | --- | --- |
| Incumbent | `structured-lexical-v1` | **16.20%** | 0 | 0 |
| Candidate | `dominance-scoped-source-semantic-evidence-atoms-v4` | 12.60% | 0 | 0 |
| Reference | `pedagogy-aware-source-semantic-evidence-atoms-v3` | 12.60% | 0 | 0 |

Pre-registered checks:

- severe unsupported releases not worse: **passed**
- operational failures not worse: **passed**
- fully grounded factual success strictly better: **failed**

All three arms score `completed-refine`; none clears the registered release
gates on this corpus.

## Why this instrument existed

Confirmation 028 recorded Keep for the v4 gate against its v3 predecessor, and
it was tempting to read that as authority to ship v4. But the product ships
neither v3 nor v4: `services/api/app/config.py` offers only `unselected`,
`structured-lexical-v1`, `ambiguity-safe-structured-lexical-v1`, and
`question-targeted-ambiguity-safe-v2`, and `deploy/local-r1.env.example`
selects the first of those. The evaluated line had never been compared with the
line that actually ships.

Promoting on 028 alone would have made the product worse, from 16.20% to
12.60%.

## The finding this produced

**v4 and v3 score identically at 12.60%.** The defect v4 corrects -- a gate
that refuses whenever any weaker competitor exists, even when the leading
source dominates -- does not bind on this corpus at all.

That is the second instance tonight of the same structural error, caught before
it reached a decision rather than after:

1. Confirmation 024 selected an architecture whose distinguishing branch its
   own cases could not exercise, because every release published one paragraph.
   The sealed 10,000-case regression exposed it.
2. Confirmation 028's Keep covers the governed autonomy contract, not factual
   grounding usefulness. Reading it as authority to change the product's gate
   would have decided on an axis it never measured. This instrument exposed it.

The lesson generalizes: a Keep is evidence about the thing that was varied, and
about nothing else.

## Method

Registered scoring is reused unchanged from
`scripts/score_academic_factual_qa_open_10000.py`. This instrument selected no
threshold of its own and added none after seeing results. Each arm ran once.
The development split is where methods are selected; no sealed or hidden-gold
package was read, opened, rerun, or rescored.

Development cluster corpora do not carry the region lineage the semantic atom
line needs, so a normalizer derives it from the cluster record itself -- the
cluster span is the citable region. It defers to any lineage a corpus already
supplies, so the sealed `chunks` format is unaffected.

## Limitations

Development-split evidence selects a method; it is not a generalization claim.
The product retrieves with a dense published index while this comparison
retrieves locally, so a promotion would have carried a transfer assumption --
one more reason the negative result is the safe one here. Public synthetic
sources only. No professor fidelity, student usability, or learning-outcome
claim.

## Decision

Keep `structured-lexical-v1` in the product. Record
`dominance-scoped-source-semantic-evidence-atoms-v4` as implemented, confirmed
for the governed autonomy contract by 028, and unpromoted for factual
grounding. Any future promotion needs evidence on the axis being changed.
