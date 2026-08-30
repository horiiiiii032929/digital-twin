# API-first retrieval decision

Status: accepted prospective direction on 2026-08-30

Decision owner: researcher

Scope: issue #127 and the factual-evaluation successor after
`course-digital-twin-evaluation-program-001`

## Decision

Move active machine-learning inference for retrieval to direct first-party APIs.
Do not run another local embedding or reranking model on the development Mac.

This is an **API-first inference** decision, not an API-owned truth or storage
decision. The repository remains authoritative for:

- approved source registration and version hashes;
- deterministic chunking and canonical character/region coordinates;
- BM25 and method fusion;
- persisted vector snapshots and immutable index manifests;
- source-range citation mapping;
- evidence, action, claim, and policy gates;
- public-question/hidden-gold separation and scoring.

The first prospective embedding candidates are direct OpenAI
`text-embedding-3-small` and `text-embedding-3-large`. Neither is selected for
the product until the finite development comparison passes. The historical
local Qwen3 result and artifacts remain immutable evidence but leave the active
execution path.

## Why this changes now

AFQC-094 established an operational, not a quality, failure. Local Qwen3
materialization stalled on Apple MPS; the one allowed CPU/float16 correction
then exceeded the practical memory envelope before any provider or product
case ran. Repeating local batching changes would extend the same operational
loop without answering the academic retrieval question.

The pinned public source plan contains 2,100 source clusters and 1,440,383
characters. Using the repository's conservative one-token-per-three-characters
reservation gives about 480,128 embedding input tokens. At the prices verified
on 2026-08-30, one complete corpus materialization is approximately USD 0.010
with `text-embedding-3-small` or USD 0.063 with
`text-embedding-3-large`. Their native float32 vector payloads for 2,100
clusters are only about 12.3 MiB and 24.6 MiB respectively. API embeddings
therefore remove the local model-memory blocker at negligible retrieval cost.

Official OpenAI documentation states that the small model costs USD 0.02 per
million input tokens and the large model costs USD 0.13 per million; the large
model is described as the more capable embedding model. The Embeddings API
accepts arrays, returns the model identity and token usage, limits each input to
8,192 tokens, and limits a request to 300,000 total input tokens. Version 3
models support an explicit output-dimension parameter. OpenAI embeddings are
unit-normalized, so dot-product search gives the same ranking as cosine
similarity.

Sources:

- [OpenAI embeddings guide](https://developers.openai.com/api/docs/guides/embeddings)
- [Create embeddings API](https://developers.openai.com/api/reference/python/resources/embeddings/methods/create)
- [text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small)
- [text-embedding-3-large](https://developers.openai.com/api/docs/models/text-embedding-3-large)

## Registration and materialization contract

The active implementation must register an embedding candidate before it can
be called:

1. Add the exact provider/model ID, requested dimensions, endpoint, verified
   price, verification time, retention statement, and status
   `prospective-not-selected` to the model policy and a versioned candidate
   manifest.
2. Freeze deterministic source text and canonical lineage first. The API never
   creates chunk IDs, source ranges, permissions, or citation truth.
3. Send ordered source texts through the direct `/v1/embeddings` endpoint in
   bounded synchronous batches. Start with 64 inputs and a 50,000-token local
   ceiling per request, below the provider maxima.
4. Match returned embeddings by response index, require the exact returned
   model ID, exact vector count and dimension, finite values, and complete
   usage accounting.
5. Atomically checkpoint each completed batch by source-set hash, model ID,
   dimensions, request range, response hash, vector hash, tokens, latency, and
   cost. A resume may only continue when every binding still matches.
6. Normalize defensively, write the final `dense.f32`, BM25 data, chunks,
   metadata, and manifest through the existing immutable index lifecycle, then
   verify every file hash before publishing the binding pointer.
7. At query time, embed only the question through the same registered model;
   perform dense scoring, BM25, fusion, hierarchy, evidence checks, and
   citation mapping in deterministic repository code.

```text
approved source + canonical range
              |
              v
deterministic registration + content hash
              |
              v
OpenAI Embeddings API (bounded batches)
              |
              v
atomic vector ledger -> immutable local dense/BM25 index
                                      |
question -> API query embedding ------+
                                      v
local ranking/fusion -> evidence gate -> grounded generator
                                      |
                                      v
canonical source-range citations and hidden-gold scoring
```

## Why not use a managed vector store as the academic authority

OpenAI vector stores can automatically chunk, embed, index, filter, and perform
hybrid search. They are useful product infrastructure and support static
chunking plus configurable ranking. They are not selected for the primary
academic comparison because the managed service does not expose the complete
vector/index artifact needed for byte-stable reproduction, and its returned
chunks still need mapping to our canonical ranges. Vector-store objects also
retain application state until deleted, whereas direct `/v1/embeddings` has no
application-state retention under the standard endpoint table.

Managed vector search may be evaluated later as a separately manifested
engineering candidate. It cannot own source truth, hidden gold, or citation
validity.

Sources:

- [OpenAI retrieval and vector stores](https://developers.openai.com/api/docs/guides/retrieval)
- [Vector-store search API](https://developers.openai.com/api/reference/python/resources/vector_stores/methods/search)
- [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data)

## Synchronous versus Batch API

The Batch API supports `/v1/embeddings`, offers a 50% discount, accepts up to
50,000 embedding inputs per batch, and has a stated turnaround of up to 24
hours. The one-time corpus cost here is already measured in cents, while speed,
atomic diagnostics, and immediate progression are more important. Therefore:

- use synchronous bounded embedding batches for the next qualification;
- keep Batch API as an optional reproducible bulk-regeneration path;
- delete any uploaded batch files after reconciliation if Batch is later used.

Source: [OpenAI Batch API](https://developers.openai.com/api/docs/guides/batch)

## Finite method comparison

The next 300-case development decision compares methods, not model brands:

| ID | Method | Purpose |
| --- | --- | --- |
| M0 | BM25 | Deterministic lexical control and rollback |
| M1 | `text-embedding-3-small` dense | Lowest-cost API dense candidate |
| M2 | BM25 + small dense RRF | Low-cost hybrid candidate |
| M3 | `text-embedding-3-large` dense | Higher-capability dense candidate |
| M4 | BM25 + large dense RRF | Higher-capability hybrid candidate |
| M5 | Large-model hybrid + deterministic section/adjacent expansion | Pre-frozen structured hierarchical candidate |
| M6 | M5 + bounded GPT-5.4 nano reranking on eligible difficult cases | Optional API reranking candidate |

Every method receives the same question-only inputs, source corpus, canonical
range scoring, and preregistered gates. M5 is bound prospectively to M4 rather
than selected after scoring, and every M0–M6 ranking must be durable before
hidden gold opens. This avoids adapting a candidate to the same cases used to
measure it. Prefer the simpler deterministic candidate when it is within two
percentage points of the best result. If no method passes, stop for one
method-level decision; do not tune and rerun the same 300 cases.

## Privacy and authority boundary

Only the pinned public, open-licensed evaluation sources may be embedded in
this checkpoint. OpenAI states that API data is not used to train models unless
the customer opts in. Standard `/v1/embeddings` has no application-state
retention but may have abuse-monitoring retention for up to 30 days; managed
vector stores retain application state until deletion. Academia Vault,
professor-private materials, student records, and production interactions stay
outside this decision.

This decision authorizes build-only implementation and documentation. It does
not authorize an embedding API call, the 300-case comparison, 500+100 product
execution, or the sealed 10,000+1,000 run.

## Recorded outcome

The separately authorized comparison completed as
`academic-factual-qa-api-retrieval-selection-001` with a valid `Refine`
decision. M4, BM25 plus `text-embedding-3-large`, was best descriptively at
38.7% complete evidence@3 and 44.7% Evidence Recall@5; boundary accuracy was
96.9% with one severe unsupported ambiguity release. M6 failed its semantic
output contract and was not selectable. The execution used 83 exact provider
calls, zero retries, USD 0.0593379, and no private data. No method was selected
and the one-time authority was revoked.

The cross-method pattern and zero-result structured slices do not justify
another embedding-model swap. The prospective successor must treat source
registration, structured code/equation/table representation, context-complete
reference questions, and retrieval matching as one method decision, then use a
fresh source-disjoint confirmation tranche.

## Consequences

- The local R1 and all historical results remain unchanged.
- Active retrieval work no longer depends on Torch, MPS, or a local embedding
  model.
- `OPENAI_API_KEY` is the only prospective model credential for this path.
- Embedding model aliases have no dated snapshot in the current model pages;
  reproducibility therefore also binds the returned model ID, verified date,
  vector hashes, source hash, dimensions, pricing, and code revision.
- BM25 remains a no-provider fallback and an explicit scientific control.
- A passing retrieval comparison is still required before product or final
  factual evaluation resumes.
