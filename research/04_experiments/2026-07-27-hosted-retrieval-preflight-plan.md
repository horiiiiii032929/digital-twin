# Hosted retrieval development preflight

Date: 2026-07-27

Status: frozen before provider calls

## Decision question

Does a hosted semantic retrieval pipeline preserve the development quality
signal observed with local Qwen3 while avoiding the local-MPS latency failure?

This preflight is not a held-out experiment and cannot select the final
retriever. It qualifies the provider integration, measures development-only
quality and operational behavior, and determines whether authoring a new sealed
dataset is justified.

## Conditions

| ID | Method | Purpose |
| --- | --- | --- |
| H0 | Heading-aware BM25 | Local control and rollback |
| H1 | Jina v3 dense retrieval | Hosted semantic first stage |
| H2 | BM25 + Jina dense reciprocal-rank fusion | Hybrid candidate retrieval |
| H3 | H2 candidates reranked by Jina reranker v3 | Hosted quality candidate |

All conditions use the same structured chunks and the same top-three evidence
scoring. H0 makes no provider request. H1-H3 use
`jina-embeddings-v3`; H3 uses `jina-reranker-v3`.

## Data and claims

- Corpus: all 13 PDFs in `it5002-lectures-v1`.
- Development set: the existing 13 answerable and 13 no-evidence cases.
- No-evidence thresholds are fitted and checked on development data, so their
  development accuracy is a calibration diagnostic rather than generalization
  evidence.
- The retired 59-case split must not be rerun or used for this candidate.
- Final confirmation requires a new prospectively sealed dataset.

## Metrics

- complete-evidence success@3, with raw numerator and denominator;
- gold-claim context coverage@3;
- development no-evidence calibration accuracy;
- paired H3-H0 wins and regressions;
- document-index build time;
- per-condition p50 and p95 query latency;
- provider requests, input tokens, approximate cost, and errors.

Quality and operations are reported separately. Local hardware is not a
retrieval-quality gate. The hosted candidate advances only if it improves
complete-evidence success without new provenance or permission failures and has
plausible hosted latency and cost.

## Provider and budget gates

- External transmission requires the exact authorization recorded in
  `research/00_admin/2026-07-27-it5002-jina-provider-boundary.md`.
- The key is read only from `JINA_API_KEY` and never accepted as a CLI argument.
- Every run requires explicit `--allow-external-provider`.
- The default maximum estimated cost is USD 1.00.
- A conservative token estimate blocks a request before the cap can be
  exceeded.
- Provider errors must not include request text or credentials in logs.
- Raw provider payloads and course text must not enter Git.

## Execution order

1. Run the offline dry-run and repository checks.
2. Configure `JINA_API_KEY` locally.
3. Run the 26-case development preflight once the dry-run estimate is accepted.
4. Inspect failures and provider usage.
5. Decide whether to keep, refine, go deeper, or drop the hosted candidate.
6. Only after that decision, create and independently review a new sealed set.
