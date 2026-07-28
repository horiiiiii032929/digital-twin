# Cross-course retrieval benchmark v1 draft status

Date: 2026-07-28

Status: structurally valid researcher-review draft; not approved, sealed, or
eligible for retrieval evaluation

## Construction checkpoint

The local authoring pass produced 100 private cases from the approved
four-course portfolio:

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

This is not yet research-grade evaluation data:

- 15/100 cases are researcher verified;
- 0/100 cases are independently second reviewed;
- difficulty labels are 70 direct, 2 paraphrase, 3 multi-step, and 25 boundary;
- no-evidence labels still require whole-corpus researcher searches; and
- exact-quote validity does not prove that a chunk fully supports the generated
  claim.

The direct-question concentration is a construction bias and must be corrected
during review. The benchmark must not be used to claim method quality yet.

## Next gate

Use the ignored local review checklist at
`data/processed/cross_course_retrieval_v1/review/researcher_review.md`.
Accept, edit, or reject every case; explicitly verify evidence sufficiency,
visual independence, natural student wording, and negative answerability.
Replace weak cases in a new draft version, then obtain an independent review
of at least 20 cases. Only after those gates pass may the 60 held-out cases be
sealed.

Validate the private draft with:

```bash
uv run python -m scripts.validate_cross_course_benchmark \
  --expected-cases 100
```

The validator reporting `passed` means structural and evidence identity checks
passed. It does not mean the semantic labels are approved.
