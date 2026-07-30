# Cross-course retrieval benchmark v1 draft status

Date: 2026-07-30

Status: private draft 6 passes structural, source, quote, hash, and assistant
three-angle QC; it remains under researcher review and is not approved, sealed,
or eligible for final retrieval evaluation

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

## Data-quality finding

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

Draft 6 currently has 40/100 researcher-verified and 0/100 independently
reviewed cases. This completes researcher verification of the full development
split: 35 positive cases plus five separately assessed boundary cases. The
three development no-evidence cases received recorded whole-corpus searches
over all 32 approved PDFs. The ten integrity/refusal cases remain useful
system-policy tests but will not be aggregated into retrieval-ranking quality
metrics.

The 60 held-out-draft labels remain available for researcher authoring review,
but no retrieval candidate has loaded or scored them. Twelve held-out
no-evidence cases still require recorded whole-corpus verification.

## Next gate

Earlier drafts and checklists remain under ignored private storage. The current
review package is
`data/processed/cross_course_retrieval_v1/review/researcher_review_draft_6.md`.
After 100/100 researcher semantic verification, obtain an independent review
of at least 20 cases. Only then may the held-out cases be sealed.

Validate the private draft with:

```bash
uv run python -m scripts.validate_cross_course_benchmark \
  --dataset data/processed/cross_course_retrieval_v1/cross_course_retrieval_v1_draft_6.json \
  --expected-cases 100
```

The validator reporting `passed` means structural and evidence identity checks
passed. It does not mean the semantic labels are approved.
