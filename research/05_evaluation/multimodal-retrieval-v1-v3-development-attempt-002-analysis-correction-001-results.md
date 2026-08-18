# Multimodal retrieval V3 development attempt 002 analysis correction 001

Result ID:
`multimodal-retrieval-v1-v3-development-attempt-002-analysis-correction-001`

Date: 2026-08-18

Status: Complete corrective analysis; no retrieval or model rerun

Decision: **Drop remains unchanged. Select no multimodal method and keep the
text-only rollback.**

## Correction

The issue hypothesis was not confirmed. The committed V3 runner and the
preserved per-case scores each use one pass over `raw_hit_rows`; the stored
scores match that single-pass legacy formula and do not match the alleged
nested-loop formula.

The audit found a different measurement defect. The historical region score
added discounted IoU once for every overlapping retrieval record. OCR, layout,
and description records could therefore add repeated gain for one gold region,
after which the unnormalized sum was capped at one. The value was not a valid
nDCG and could be inflated by duplicate representations.

The corrected evaluator uses:

- unique-asset page rank;
- one-to-one matching between retrieved and gold regions;
- mean assigned IoU for region IoU@3 and IoU@5;
- complete evidence@3 only when every gold region is matched and the page is
  in the top three;
- atomic recall@5 as matched gold regions divided by all declared gold
  regions; and
- nDCG@10 as maximum one-to-one discounted IoU divided by ideal DCG.

Each retrieved region and each gold region can contribute at most once.

## Corrected evidence

The audit reused the preserved nine-case rankings: three failed visual cases,
three text controls, one no-evidence case, and two integrity cases. It did not
rerun retrieval or load a model.

| Candidate | Complete evidence @3 | Atomic recall @5 | Historical region score | Corrected region nDCG @10 |
| --- | ---: | ---: | ---: | ---: |
| V2 lexical/layout/description | 1/3 | 2/3 | 0.212 | 0.0676 |
| V3 V2 + OpenCLIP RRF | 1/3 | 1/3 | 0.186 | 0.0756 |

The corrected diagnostic reverses the old nDCG ordering: V3 is slightly above
V2. This does not change the selection decision. V3 still ties complete
evidence, retrieves only 1/3 required regions at five versus V2's 2/3, and
requires the full vision model on the request path. Text-control page success
remains 3/3, no-evidence action accuracy 1/1, and integrity accuracy 2/2.

## Provenance and validity

- Source run:
  `multimodal-retrieval-v1-v3-development-attempt-002`.
- Source result SHA-256:
  `46568abbf374e42f873e1db96980651fc5e0ec20295e643cb6cf2300453ba361`.
- Source-reported revision:
  `4c3bd9942b9449332cb5622a3f57aca89d6a01e3`, dirty worktree.
- Correction code revision:
  `5ab7af45872b156f907c2808ede5f877b31cea28`, clean worktree.
- Ignored corrective aggregate:
  `reports/generated/multimodal-retrieval-v1-v3-development-attempt-002-analysis-correction-001.json`.
- Command: `npm run audit:multimodal-v3-result`.
- Model called: false.
- Held-out read: false; the 24-case held-out partition remains unopened.

The exact dirty source state of the historical run cannot be reconstructed.
The preserved rankings and values are sufficient to identify the legacy
formula and recompute the corrected metrics, but not to claim a clean original
execution revision. All scoped answerable cases have one gold region, so the
new multi-region matching behavior is covered by unit tests rather than this
historical sample. Latency, capacity, and cost were not remeasured.

## Profile and next baseline

The frozen `student-tutor-v1` profile remains unchanged and agrees with this
result: it selects no multimodal component, makes no image-only claim, and
retains text retrieval as the supported rollback. The historical result and
machine record remain intact; this correction supersedes only their region
metric interpretation.

The next prospective candidate in issue #86 must beat the trustworthy V2
baseline of 1/3 complete evidence@3, 2/3 atomic recall@5, and 0.0676 corrected
region nDCG@10 on the declared failed-slice scope, preserve all controls, avoid
an online vision tower, and use new evidence rather than tuning these cases.
