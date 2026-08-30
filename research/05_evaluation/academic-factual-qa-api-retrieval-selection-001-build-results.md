# API-first retrieval selection build result

## Outcome

`Go Deeper` to one separately authorized execution of
`academic-factual-qa-api-retrieval-selection-001`.

This checkpoint removes the local model-memory blocker and freezes the next
retrieval decision. It is build-only evidence: no embedding, reranking, product,
private-data, or final-set provider call was made, and no retrieval method was
selected.

## Frozen comparison

The untouched 300-case development tranche will compare seven methods over the
same 2,100 pinned public source clusters:

- M0: BM25 control.
- M1/M2: OpenAI small dense and hybrid retrieval.
- M3/M4: OpenAI large dense and hybrid retrieval.
- M5: the prospectively fixed large-hybrid base plus deterministic hierarchy.
- M6: M5 plus GPT-5.4 nano reranking for at most 40% of difficult queries.

Deterministic code retains source registration, BM25, immutable artifact
creation, citation lineage, hidden gold, metrics, and the final Keep/Refine
decision. API models supply only vectors or bounded reranking scores.

## Memory and correctness boundaries

- Embeddings are requested in batches of at most 64 and written transactionally
  to SQLite before the batch vector objects are released.
- Final dense artifacts are streamed in source order; the implementation never
  builds a full Python vector list for the corpus.
- Every checkpoint is bound to source, release, profile, chunker, model,
  dimension, price, metadata, retention, and ranking configuration hashes.
- Resume rejects binding drift, duplicate or reordered provider indices,
  dimension changes, non-finite vectors, and corrupted artifacts.
- All rankings must be durable before hidden gold can be opened.
- Provider execution, paid execution, 500+100 product evaluation, and the sealed
  10,000+1,000 evaluation remain unauthorized.

## Verification

- Three network-free terminal simulations pass: complete pass, valid quality
  failure, and identity drift.
- The complete repository gate passes 1,248 Python tests and 47 frontend tests,
  frontend lint, and the production build.
- Repository correctness is 717/717 audited files with zero pending findings.
- Execution-freeze coverage is 105/105 protected entrypoints.
- Markdown links, model policy, instrument hashes, source split, gold-opening
  order, interruption/resume, budget, and exact-identity guards pass.
- Provider calls, tokens, cost, private data, and final responses are all zero.

## Limitations

- This result does not measure Evidence Recall@5, all-evidence@3, boundary
  accuracy, latency, or comparative cost; those belong to the paid execution.
- Both embedding candidates are prospective and not selected in the active
  release profile.
- The public benchmark does not establish performance on private course
  materials or true visual evidence.

## Decision

Keep the local Qwen3 result as historical control and keep the qualified local
R1 unchanged. Proceed once with the frozen API-first comparison after a clean
preflight and separate authorization. A passing result may select a retrieval
method and reopen the 500+100 product checkpoint; a valid failure stops for one
method-level decision.
