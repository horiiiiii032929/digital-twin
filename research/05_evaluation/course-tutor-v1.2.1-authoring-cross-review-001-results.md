# Course-tutor v1.2.1 authoring cross-review results

Result ID: `course-tutor-v1.2.1-authoring-cross-review-001`

Date: 2026-08-12

Status: Superseded after a deeper independent audit; held-out tutor outputs
remained unopened.

Supersession notice: the `133 clear / 19 uncertain` conclusion below is
historical and must not be used for approval. The later registered
[`course-tutor-v1.2.3-authoring-cross-review-002`](course-tutor-v1.2.3-authoring-cross-review-002-results.md)
found material defects in draft 002, preserved it privately, and replaced it
with draft 004.

Decision: Drop private authoring draft 001, preserve its unfavorable findings,
and advance corrected draft 002 to independent human review. This result does
not approve or seal the dataset.

## Decision question

Is the 48-case development plus 104-case held-out authoring draft internally
coherent enough to begin independent human review, and which cases remain
genuinely uncertain after deterministic and LLM-assisted cross-review?

The prediction was that the existing hash-valid draft would need only isolated
claim or wording corrections. The prediction failed: the first draft contained
systematic scenario-generation, lineage, and semantic evidence defects.

## Inputs and boundary

- Baseline: private `course-tutor-v1.2-review-draft-001`.
- Candidate: private `course-tutor-v1.2-review-draft-002`, dataset version
  `course-tutor-v1.2.1`.
- Development cases: 48.
- Held-out authoring cases: 104.
- Scenarios: 19 cases each for direct, paraphrase, misconception,
  multi-evidence, ambiguity, no-evidence, assessed-work, and
  permission/version.
- Corpus: approved private `it5002-lectures-v1@1.0.0`, processed locally.
- Permission: local source processing and approved external provider use under
  the existing professor-fidelity authorization.
- Code base revision: `4c4afe42b9258fc8bd1498745ec14bbb5821eaa6`, with the
  authoring-repair changes dirty during the recorded advisory run.
- Random seed: not applicable; the build and checks are deterministic.
- Held-out tutor outputs, the blinded condition mapping, and any held-out
  execution ledger were not opened or created.

The corrected hash boundary is:

| Split | Dataset SHA-256 | Conditions SHA-256 |
| --- | --- | --- |
| Development | `6844c64edd386639ce8aeddc6612dc09fbadee07a0dc6c3418bdffc029093c53` | `57725f16d1b17c452a88ea1f896b34a62f487a4f094293abf29be51ea1434951` |
| Held-out | `61504ab65efaeb99a3cd395a611c254e9e3433a09c0c48c59254b4776776d8b4` | `23c471f7a890edd91222221ef2f94e0696e630edee33dbc3cc31ade790e4cfa2` |

## Method

The cross-review combined:

1. JSON Schema, count, condition, claim-link, evidence-hash, permission,
   sufficiency, and corpus-identity validation;
2. duplicate-question, lineage-parent, multi-evidence cardinality,
   rejected-template, and ambiguity lecture-to-source checks;
3. semantic review of question authenticity, expected action, claim atomicity,
   exact passage support, and split suitability; and
4. local TF-IDF nearest-passage diagnostics for every no-evidence case.

The review is explicitly labeled `codex_assisted: true` and
`human_review: false`. It is advisory triage, not the independent human
certification required by the seal.

## Baseline finding and correction

Draft 001 had 43 advisory-clear cases, 19 uncertain no-evidence cases, and 90
case-level issues before considering its dataset-wide lineage defect. The main
failure classes were:

- all 152 transformations received unique family IDs even when they reused one
  source family;
- all 19 misconception cases negated the true claim instead of presenting a
  plausible false belief;
- all 19 paraphrases added a wrapper while retaining the source query;
- all 19 ambiguity cases were highly templated and named a lecture that did not
  match their attached evidence;
- all six development multi-evidence cases paired unrelated claims; and
- multiple positive cases inherited semantically wrong claim-to-page links
  from the already-invalid rapid retrieval instrument.

Draft 002 treats the rapid instrument only as an inventory. Every positive
question, atomic claim, and approved lecture page is explicitly curated. It
also shares lineage families across transformations, records parent cases,
uses authentic misconceptions and paraphrases, authors genuine multi-evidence
tasks, and gives ambiguity cases distinct source-consistent wording.

## Candidate result

| Advisory disposition | Cases | Share |
| --- | ---: | ---: |
| Clear for independent human confirmation | 133 | 87.5% |
| Uncertain and requiring focused human corpus review | 19 | 12.5% |
| Unresolved LLM-detected issue | 0 | 0.0% |

All 19 uncertain cases are no-evidence cases. Their lexical nearest neighbors
were weak and did not establish an answer, but corpus-wide semantic absence
cannot be conclusively certified by an LLM. The ignored private focus packet
lists those cases and their nearest approved passage identities for human
inspection.

The candidate also has zero exact duplicate questions, zero question pairs at
or above 0.90 normalized sequence similarity, zero synthetic cases without a
parent source, and zero uses of either rejected scenario template.

## Limitations and human gate

- This is a single-LLM semantic review and can share systematic blind spots
  with the authoring repair.
- Lexical diagnostics can miss conceptual support expressed with different
  vocabulary.
- The 133 clear dispositions narrow attention but do not waive independent
  review of all 152 cases.
- A reviewer using the Codex advisory cannot certify the official review as
  `codex_assisted: false` unless they independently inspect and decide every
  required check.

The private machine advisory, rejected-draft record, and 19-case focus packet
are under `reports/generated/course-tutor-v1.2-llm-cross-review/`. The official
unmodified human template and full packets are under
`reports/generated/course-tutor-v1.2-authoring-review/`. Both paths are ignored
and contain no committed course wording.

## Reproduction

```bash
npm run build:course-tutor-splits
npm run prepare:course-tutor-authoring-review
npm run cross-review:course-tutor-authoring
```

The build and advisory commands refuse to overwrite prior artifacts. Preserve
or move an existing private draft before intentionally creating another
authoring revision.
