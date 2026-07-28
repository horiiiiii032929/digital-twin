# Cross-course retrieval benchmark v1 draft status

Date: 2026-07-28

Status: draft 1 retained for traceability; draft 2 passed structural validation
but failed assistant semantic QC; neither is approved, sealed, or eligible for
retrieval evaluation

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

## Next gate

Earlier drafts and checklists remain under ignored private storage. The current
review package is
`data/processed/cross_course_retrieval_v1/review/researcher_review_draft_5.md`.
After 100/100 researcher semantic verification, obtain an independent review
of at least 20 cases. Only then may the held-out cases be sealed.

Validate the private draft with:

```bash
uv run python -m scripts.validate_cross_course_benchmark \
  --expected-cases 100
```

The validator reporting `passed` means structural and evidence identity checks
passed. It does not mean the semantic labels are approved.
