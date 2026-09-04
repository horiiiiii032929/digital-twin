# Product evidence gate selection at region granularity

## Outcome

The product **keeps `question-targeted-ambiguity-safe-v2`**. The successor gate
that corpus confirmation 028 recorded Keep for stays **implemented but
unpromoted**.

The decision rule was committed before any arm ran.

## Result

500 development cases, committed gold, a corpus re-materialized at the
granularity the gold cites: 344 registered regions covering **344 of 344** gold
evidence spans exactly. Everything except the evidence gate held fixed.
Provider calls 0, cost USD 0.

| Arm | Gate | Fully grounded factual success | Severe unsupported releases | Operational failures |
| --- | --- | --- | --- | --- |
| **Incumbent** | `question-targeted-ambiguity-safe-v2` | **16.00%** | 0 | 0 |
| Template default | `structured-lexical-v1` | 16.20% | 0 | 0 |
| Candidate | `dominance-scoped-source-semantic-evidence-atoms-v4` | 9.40% | 0 | 0 |
| Reference | `pedagogy-aware-source-semantic-evidence-atoms-v3` | 9.40% | 0 | 0 |

Pre-registered checks: severe unsupported releases not worse **passed**,
operational failures not worse **passed**, fully grounded factual success
strictly better **failed**.

## What fixing the granularity changed, and what it did not

Selection 001 ran the same four gates on the cluster-granularity corpus and
reached the same decision. Correcting the granularity did not overturn the
result; it widened the gap and removed the doubt about the figures.

| | Selection 001 (cluster) | Selection 002 (region) |
| --- | --- | --- |
| Incumbent | 15.80% | 16.00% |
| Candidate | 12.60% | 9.40% |
| Gap | 3.20 points | **6.60 points** |

Two of the three refusal mechanisms 001 observed were artifacts of the cluster
corpus and are gone: 47 multi-evidence abstentions, which could not resolve
because one cluster supplies one atom, and 52 structured-support abstentions.
Multi-evidence resolution rose from 1 case to 22.

What replaced them is the mechanism the sealed benchmark already found. At
region granularity the incumbent answers 148 of 400 answerable cases and
clarifies 252. The sealed 10,000-case regression measured the v3 gate at 69.7%
clarify on a region corpus; this is the same over-refusal, and the cluster
corpus had been masking it.

## The finding

**The candidate and the predecessor it corrects are identical at 9.40%, exactly
as they were at 12.60% on the cluster corpus.**

Two independent corpora, two granularities, and the dominance-scoping
correction moves nothing either time. The defect it fixes is real — it is
pinned by `tests/test_source_semantic_evidence_atom_gate_v4.py` and it fires on
the sealed benchmark — but it is not what limits grounding here.

So confirmation 028's Keep remains what it always was: evidence about the
governed autonomy contract, on the axis it varied, and about nothing else. A
verdict covers its variable.

## Method

Registered scoring reused unchanged from
`scripts/score_academic_factual_qa_open_10000.py`. This instrument selected no
threshold and added none after seeing results. Each arm ran once. The corpus
was re-materialized from the same committed clusters through
`registered_source_chunks`, the mechanism that produced the sealed package's
region corpus; no source was added and no provider was called. The incumbent's
action split was observed during diagnosis and is recorded in the instrument as
not blind.

No sealed or hidden-gold package was read, opened, rerun, or rescored.

## Limitations

Development-split evidence selects a method; it is not a generalization claim.
The product retrieves with a dense published index while this comparison
retrieves locally. Public synthetic sources only. No professor fidelity,
student usability, or learning-outcome claim.

## Decision

Keep `question-targeted-ambiguity-safe-v2` in the product. No re-qualification
is required: the gate that release qualification 003 ran is the gate this
selection confirms, so the shipped release stands.
