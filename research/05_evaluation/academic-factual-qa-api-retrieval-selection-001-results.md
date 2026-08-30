# API-first retrieval selection result

## Outcome

`completed-refine`. No retrieval method is selected, and the 500+100 and sealed
10,000+1,000 product evaluations remain closed.

The result is valid for a development method decision. All public rankings were
durable before hidden gold opened. The run used 83 provider calls, zero retries,
USD 0.0593379, and no private data.

## Headline comparison

| Method | Complete evidence@3 | Evidence Recall@5 | Boundary accuracy | p95 latency |
| --- | ---: | ---: | ---: | ---: |
| M0 BM25 | 36.6% | 40.6% | 96.9% | 3.9 ms |
| M1 small dense | 33.6% | 36.4% | 96.9% | 57.8 ms |
| M2 small hybrid | 38.3% | 43.2% | 96.9% | 54.2 ms |
| M3 large dense | 32.3% | 36.8% | 96.9% | 108.0 ms |
| M4 large hybrid | **38.7%** | **44.7%** | 96.9% | 102.2 ms |
| M5 large hybrid + hierarchy | 38.3% | 44.0% | 96.9% | 128.9 ms |
| M6 M5 + nano reranking | Invalid method output | Invalid method output | — | — |

The frozen gates were 90% complete evidence@3, 95% Evidence Recall@5, 98%
boundary accuracy, zero severe releases, and p95 below two seconds. M4 was best
descriptively but failed by a wide margin. Every M0–M5 method had two boundary
errors, including one severe unsupported release on an ambiguous question.

## Slice diagnosis

M4 complete evidence@3 / Recall@5 was:

- computer networking: 52.5% / 59.0%;
- data structures: 54.7% / 59.4%;
- operating systems: 33.9% / 39.3%;
- Python: 9.3% / 16.7%;
- multi-evidence: 80.0% / 93.3%;
- code, equation, and table slices: 0% / 0%.

Direct inspection shows that some failed questions use deictic fragments or
weak lexical anchors such as single variables or phrases detached from their
source context. The result therefore supports a joint source-registration,
structured-content, and reference-question diagnosis. It does not support
simply swapping to another embedding model.

## Operational notes

- Small and large indexes each materialized 2,100 source vectors and 300 query
  vectors through exact first-party OpenAI identities.
- A first materialization interruption exposed an item-only batching defect.
  Six completed batches were preserved; the harness then enforced both the
  frozen 64-item and 50,000-estimated-token limits and resumed atomically.
- M6 made one exact GPT-5.4 nano call. The response contained all case IDs but
  incomplete candidate chunk-ID sets. It was rejected, preserved, not retried,
  and M6 was marked failed/non-selectable without discarding M0–M5.
- Total reported cost was USD 0.0593379, safely below the USD 2 stop.
- The unrestricted ledgers and rankings remain ignored; their hashes are bound
  in the machine-readable record.

## Limitations

- This is a 300-case development result, not the professor-requested sealed
  10,000-case result.
- The development cases are now known and may be used only for diagnosis, not a
  fresh confirmatory claim.
- Public open educational sources do not establish performance on private
  course materials, true visual evidence, or professor-specific behavior.
- No independent external human annotation was used.

## Decision

Select no API retrieval method and revoke the one-time authority. Preserve the
qualified local R1 and every historical result. The next step is one
method-level redesign that jointly fixes canonical structured-source indexing,
context-complete reference questions, and retrieval matching, followed by a
fresh source-disjoint confirmation tranche. Do not open 500+100 or 10,000+1,000
until that successor passes.
