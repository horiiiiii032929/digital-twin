# Multimodal product grounding V2 development attempt 002 plan

Date: 2026-08-18

Run ID: `multimodal-product-grounding-v2-development-attempt-002`

Status: frozen before attempt-002 implementation and measurement

## Predecessor

Attempt 001 remains a completed Refine result. It improved atomic recall and
region nDCG but failed five gates. Its OCR adapter expected `bounding_box` while
the authored instrument used `bbox`; broad diagram/equation labels did not
match their deterministic rendered regions; table values lacked row/column
search context; and broad duplicate records crowded localized evidence.

## Decision question

Do the bounded, source-derived repairs below make the deterministic region
architecture good enough to retain as a product foundation without selecting
an OCR engine or vision-description model?

## Frozen changes

1. Map authored OCR `bbox` fields explicitly into provider-neutral
   `bounding_box` objects. Do not change OCR text or confidence labels.
2. Add source-derived table row and column headers to each cell's searchable
   representation while keeping the original cell crop and value authoritative.
3. Add deterministic query-modality routing over prebuilt BM25 indexes for
   table, diagram, equation, OCR/visual, and general text regions. No model call
   is allowed on the query path.
4. Suppress broad page/text duplicates only within routed visual indexes; keep
   the page-level index as the text fallback.
5. Apply the versioned `1.0.1` label correction overlay for the two diagram and
   two equation cases. The questions, answers, assets, OCR text, table labels,
   other boxes, slices, and gates remain unchanged.

No additional tuning is allowed after reading attempt-002 metrics. Any further
change requires attempt 003 and another prospective record.

## Data and separation

- Instrument: `multimodal-product-grounding-v2-development-1.0.1`.
- Base: exact `1.0.0` 21-case, nine-asset public-synthetic development set.
- Correction: only four rendered-geometry boxes, with the base SHA-256 bound in
  the overlay.
- Historical 24-case multimodal held-out split: remains closed and unread.
- External providers: prohibited.
- Gemma: prohibited.

## Candidates and gates

The control remains `R0-text-page`. The candidate becomes
`R2-region-routed-local`. Metrics, thresholds, text fallback, lineage gate,
latency gate, and decision rules are unchanged from the parent V2 plan.

The p95 ratio remains a hard gate even though attempt 001 showed sub-millisecond
timer noise. Both absolute latency and the frozen ratio will be reported; the
gate will not be relaxed after the run.

## Prediction

OCR slices should become retrievable, table value cells should enter the first
three ranks, and modality routing should improve complete@3, recall@5,
localization, and citation lineage while reducing the routed index size. The
small synthetic result can justify Go Deeper only; it cannot select a
production OCR or description model.

## Reproduction

```text
npm run verify:multimodal-product-grounding
npm run benchmark:multimodal-product-grounding-development
```

## Decision

Pending.
