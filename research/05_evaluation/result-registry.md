# Evaluation result registry

This is the durable index of every named evaluation run that informs a
component, configuration, or product decision. Failed, inconclusive, and
invalid results remain visible. Routine CI verification is not a separate
research result unless its measurements are used as decision evidence.

| Result ID | Date | Component | Dataset / corpus | Status | Decision | Summary | Machine record | Reproduction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ingestion-v1-clean` | 2026-07-14 | Parser and chunker | Five-source synthetic ingestion corpus | Completed | Keep parser; refine chunk settings | [Results](ingestion-v1-results.md) | Not applicable: single-baseline verification | `npm run verify:ingestion` |
| `retrieval-v1-clean` | 2026-07-15 | Retriever | `retrieval-v1` / `synthetic-browser-security-v1` | Completed | Keep BM25 v1 | [Results](retrieval-v1-results.md) | [Record](records/retrieval-v1.json) | `npm run verify:retrieval` |
| `retrieval-v2-clean` | 2026-07-15 | Retriever | `retrieval-v2-test` / `synthetic-web-security-v2` | Inconclusive | Refine; no replacement | [Results](retrieval-v2-results.md) | [Record](records/retrieval-v2.json) | `npm run benchmark:retrieval` |

## Rules

- Add the row when a named run is created, then update its status without
  reusing the ID for different inputs or configurations.
- Give corrected reruns new IDs and link both directions; never delete the
  invalid or unfavorable predecessor.
- Keep exact per-case output in the generated artifact named by the result
  summary. Commit only synthetic or sanitized durable evidence.
- Register a grouped repeated-trial result only when the individual seeds,
  outputs, and aggregation method remain traceable.
