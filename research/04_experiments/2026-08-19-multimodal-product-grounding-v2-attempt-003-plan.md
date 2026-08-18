# Multimodal product grounding V2 development attempt 003 plan

Date: 2026-08-19

Run ID: `multimodal-product-grounding-v2-development-attempt-003`

Status: frozen before attempt-003 implementation and measurement

## Predecessor

Attempt 002 passed all frozen quality, safety, text-control, and citation-lineage
gates on the 13 answerable visual cases. It failed only the p95 ratio gate:
0.079 ms versus 0.058 ms. Post-run inspection also found that the lexical
sufficiency action abstained on two equation cases even though their required
regions were retrieved.

## Decision question

Can a smaller deterministic route index and source-type search labels preserve
attempt-002 retrieval quality while passing the frozen latency ratio and a new
answerable-action integration gate?

## Frozen changes

1. Prefix equation chunks with deterministic type labels such as "equation",
   "formula", and "defined". These labels describe the parser's region kind;
   they do not add factual content or model-generated claims.
2. Route diagram questions containing order/index language directly to the
   diagram index.
3. Build the general index from page/text/OCR/caption regions only. Exclude
   table, diagram, figure, and equation duplicates because they retain their own
   routed indexes.
4. Build the table index from the table region and answer-bearing data cells;
   exclude header-only cells and duplicate row regions from query-time ranking.
   All original regions and crops remain stored and citable.
5. Remove the extra visual probe from the general route. OCR remains in the
   general index, so generic scanned-text questions retain coverage.
6. Stabilize timing with one untimed warm-up and 100 timed retrieval repeats per
   case and candidate. Quality is scored once from the first timed ranking;
   timing repeats do not alter rankings or labels.

No question, expected fact, evidence box, asset, threshold, or historical result
changes. No further repair is allowed after attempt-003 metrics are read.

## Data and boundaries

- Instrument: exact
  `multimodal-product-grounding-v2-development-1.0.1`, SHA-256
  `319691a4d08760c1dacf27f73d4024642538dd1b2fd3289e33b6dd9ff831e03b`.
- Cases/assets: unchanged 21 cases and nine public-synthetic PDFs.
- Historical 24-case multimodal held-out split: closed and unread.
- External providers, Gemma, and online vision inference: prohibited.

## Candidate and gates

The candidate is `R3-region-routed-compact`. Every parent V2 gate remains.
Attempt 003 adds:

- answerable retrieval-action accuracy: 13/13 (100%);
- integrity action accuracy: 2/2 (100%).

The relative p95 threshold remains candidate no more than 20% slower than the
control. Absolute p50/p95 are reported as context but do not replace the frozen
ratio.

## Prediction

The compact indexes will retain 13/13 complete evidence, recall, localization,
and lineage, resolve the two equation abstentions, and reduce warm query p95 to
within 20% of the page control. A full pass supports Go Deeper for real-corpus
and OCR-provider qualification, not production profile selection.

## Reproduction

```text
npm run verify:multimodal-product-grounding
npm run benchmark:multimodal-product-grounding-development
```

## Decision

Pending.
