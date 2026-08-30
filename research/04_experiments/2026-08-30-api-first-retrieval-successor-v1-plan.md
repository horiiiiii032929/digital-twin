# API-first retrieval successor v1 plan

Status: prospective build-only plan

Decision: AFQC-095

Parent issue: #127

## Decision question

Can direct API embeddings remove the local resource blocker while improving
the actual project retrieval gates enough to reopen the 500+100 and sealed
10,000+1,000 product evaluations?

## Prediction

At least one hybrid API method will improve canonical evidence coverage over
BM25 without a local model-memory dependency. The larger embedding model may
improve difficult semantic retrieval, but the smaller model may be selected if
quality is within two percentage points because it is cheaper and produces a
smaller index.

## Build-only work

1. Add a direct OpenAI embedding adapter behind `TextEmbedder`.
2. Generalize `RetrievalIndexBindingV1` into a prospective version that does
   not hard-code Qwen3 and binds provider, model, returned identity,
   dimensions, price verification, batch policy, and vector hashes.
3. Add atomic per-batch materialization and resume without retaining all
   provider vectors in Python object graphs.
4. Register small and large OpenAI embedding candidates as prospective and
   preserve Qwen3 as historical selected evidence only.
5. Add retrieval methods M0-M6 from the API-first decision memo.
6. Add no-call simulation, stale metadata, wrong identity, malformed vector,
   duplicate/missing index, budget, interruption/resume, and corruption tests.
7. Freeze a new instrument and stop before provider execution.

## Execution sequence after separate authorization

1. Recheck model availability, exact returned identity behavior, price, limits,
   and retention within 24 hours.
2. Materialize both API vector sets over the same 2,100 public source clusters.
3. Run the untouched 300 development retrieval cases across M0-M6.
4. Apply the existing gates: complete evidence@3 at least 90%, Evidence
   Recall@5 at least 95%, boundary accuracy at least 98%, zero source/course/
   version violations, zero severe releases, and retrieval p95 at most two
   seconds excluding one-time materialization.
5. Select one method using quality first, then simplicity, latency, index size,
   and cost. A method within two percentage points of the best quality result
   wins when it is simpler or cheaper.
6. Publish every method and slice result. Stop if none passes.
7. Only a pass may prepare one 500+100 product checkpoint. Only its pass may
   prepare the sealed 10,000+1,000 run under new authority.

## Cost and operational bounds

- Public source material only.
- Direct `/v1/embeddings`; no managed vector store in the selecting run.
- Initial materialization batch: at most 64 inputs and 50,000 estimated tokens.
- Zero semantic retries. One transport retry per failed batch, globally capped
  at two, with every original failure preserved.
- Expected two-model corpus embedding cost: under USD 0.10 at prices verified
  on 2026-08-30; prospective emergency ceiling: USD 1.
- Reranking, if M6 is included, receives its own call and cost accounting under
  the existing evaluation-program budget rules.

## Stop rules

- Identity drift, source/hash mismatch, gold leakage, private data, corrupted
  checkpoint, or budget exhaustion: `invalid-execution` and stop.
- A valid resource or quality failure: `completed-refine` and stop.
- All gates pass: `completed-keep`, revoke authority, and prepare the separate
  500+100 checkpoint.
- No second embedding-provider search or prompt-tuning loop follows a valid
  result on these 300 cases.
