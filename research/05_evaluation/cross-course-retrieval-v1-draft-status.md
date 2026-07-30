# Cross-course retrieval benchmark v1 draft status

Date: 2026-07-30

Status: private draft 6 was sealed on 2026-07-30 after complete researcher
review and a blinded local-model second-review sample; no final retrieval
candidate has accessed the held-out split

## Construction checkpoint

Draft 1 produced 100 private cases from the approved four-course portfolio:

| Slice | Cases |
| --- | ---: |
| Answerable | 60 |
| No-evidence | 15 |
| Cross-course confusion | 15 |
| Adversarial / integrity | 10 |
| **Total** | **100** |

The split is 40 development and 60 held-out drafts. The 75 positive cases have
page-local evidence. Automated validation passed the JSON Schema, exact
allocation, unique ID and query, action/evidence consistency, source manifest,
document hash, page, chunk hash, exact quote, and visual-dependency checks.
No private course text is included in this status document.

## Initial data-quality finding

Draft 1 is not research-grade evaluation data:

- 15/100 cases are researcher verified;
- 0/100 cases are independently second reviewed;
- difficulty labels are 70 direct, 2 paraphrase, 3 multi-step, and 25 boundary;
- no-evidence labels still require whole-corpus researcher searches; and
- exact-quote validity does not prove that a chunk fully supports the generated
  claim.

The direct-question concentration is a construction bias and must be corrected
during review. The benchmark must not be used to claim method quality yet.

## Draft 2 QC outcome

The prospective
[QC amendment](../04_experiments/2026-07-28-cross-course-benchmark-v1-qc-amendment.md)
produced a separate 100-case machine draft:

- 34 direct, 31 paraphrase, 10 two-chunk multi-step, and 25 boundary cases;
- 82 unique gold chunks across 75 positive cases;
- zero answerable/confusion gold-chunk overlap; and
- complete schema, allocation, manifest, document, page, chunk, quote, and
  hash validation.

Assistant semantic QC nevertheless flagged 32/100 cases for at least one
claim/evidence mismatch, artificial multi-topic pairing, duplicate gold pair,
administrative source, or weak/trivial question. Draft 2 therefore failed the
semantic authoring gate. No draft-1 approval was transferred.

## Draft 5 local-QC checkpoint

All course material remained local. Drafts 3 through 5:

- rewrote or replaced the 32 draft-2 failures;
- corrected five defects found by a second full semantic sweep;
- removed the final repeated gold chunk;
- retained 34 direct, 31 paraphrase, 10 multi-step, and 25 boundary cases;
- use 85 distinct gold chunks for 75 positive cases, with zero reuse;
- retain 15 course-adjacent no-evidence cases whose top-three local BM25
  matches did not support the requested facts; and
- pass schema, allocation, query uniqueness, course-ID exclusion, source,
  document, page, chunk, exact-quote, multi-step, and hash validation.

Draft 5 has 0/100 researcher-verified and 0/100 independently reviewed cases.
Assistant QC makes it eligible for researcher review, not retrieval
evaluation.

## Draft 6 three-angle review and repair

Assistant QC inspected all 100 case records and visually checked all 85
original PDF pages cited as positive gold evidence from three angles:

- semantic agreement among query, required claim, and evidence;
- retrieval fairness and naturalness; and
- text, chart, table, equation, diagram, handwriting, and layout dependence.

The review identified 12 positive cases with incomplete claims, overstated
questions, missing conditions, or weak wording. All 12 were repaired through a
hash-bound draft-5-to-draft-6 QC patch. Draft 6 passes the private validator
against the canonical source corpus.

The visual audit found no image-only gold claim. One ordered diagram was
layout-sensitive, but the frozen parser output and gold chunk preserve its
required sequence. Image-only or spatial-only questions remain reserved for a
separate future multimodal evaluation.

## Final researcher review

All 100 cases are researcher verified:

- all 75 positive cases were checked for question, claim, and exact-evidence
  agreement;
- all 15 no-evidence cases received recorded whole-corpus searches over the 32
  approved PDFs;
- all 15 cross-course-confusion cases were checked for course scope and
  plausible distractors; and
- all 10 integrity/refusal cases were checked as a separate policy suite and
  remain excluded from retrieval-ranking aggregates.

Every lecture source is tagged with course, release, source, and permission
scope. Retrieval must apply those filters before ranking or reranking. Missing
scope fails closed, and any unauthorized candidate chunk fails the isolation
gate.

## Blinded local-model second review

The prospective second-review plan selected 20 positive cases by fixed hash:
five per course, comprising three answerable and two cross-course-confusion
cases per course. The prompt omitted prior decisions, notes, rankings, metrics,
and split-level results.

The different local reviewer model accepted 19 cases and rejected one. The
original rejection is preserved. Researcher adjudication retained
`ccr1-cs5421-05` because the rejection's explanation contradicted the stated
functional dependency: two records with the same determining position and
different salaries are a violation. All 20 sampled cases now carry a
second-review record.

This is a blinded local-model second review, not independent human review,
professor validation, or evidence of student usability. It covers positive
evidence labels only. Boundary cases received separate researcher checks.
Details are recorded in
[the result summary](cross-course-benchmark-model-second-review-v1-results.md).

## Seal

The private validator passed on 2026-07-30:

| Gate | Result |
| --- | ---: |
| Structural, source, quote, and hash validation | Pass |
| Researcher verified | 100/100 |
| Blinded local-model second reviewed | 20/100 |
| Whole-corpus checked no-evidence cases | 15/15 |
| Retrieval candidate access to held-out cases | 0 |
| Sealed development cases | 40 |
| Sealed held-out cases | 60 |
| Held-out ledger | Unopened; zero attempts |

Earlier drafts, raw decisions, adjudication, and checklists remain in ignored
private storage. The final review package is
`data/processed/cross_course_retrieval_v1/review/researcher_review_draft_6.md`.
The sealed package is under
`data/processed/cross_course_retrieval_v1/sealed_v1/`.

| Artifact | SHA-256 |
| --- | --- |
| Development split | `e3749c3ee831dcf4c06f3b33cb94f21fe758eaec36e627d034715d4ca0cdd863` |
| Held-out split | `1b909cab6a1c89db57d7675caabd7e0ab87148353c3054e9fd6a947436fe8ac5` |
| Initial held-out ledger | `06d90ed7ecbe2047ceb0484a0926808fcd77fb4fda48e35a825cb9b98014d225` |

The held-out file is private with owner-only permissions. The ledger records
`unopened`, zero attempts, and no access authorization. File permissions and a
ledger are procedural safeguards, not proof that manual access is impossible.
Any unrecorded content inspection invalidates the final evaluation.

The next research gate is development-only comparison of the frozen candidate
methods. Candidate implementations, provider/model revisions, thresholds,
metrics, analysis, code hash, and an endurance preflight must be frozen before
the one-time runner may open the held-out split.

Validate the private draft with:

```bash
uv run python -m scripts.validate_cross_course_benchmark \
  --dataset data/processed/cross_course_retrieval_v1/cross_course_retrieval_v1_draft_6.json \
  --source-root /Users/hikaru/Documents/academia_vault \
  --expected-cases 100
```

The validator reporting `passed` establishes the recorded structural and
evidence-identity gates. Semantic approval additionally depends on the
researcher and second-review records described above.
