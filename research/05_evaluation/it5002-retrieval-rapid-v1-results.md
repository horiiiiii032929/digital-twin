# IT5002 retrieval rapid v1 results

## Run identity

- Component: retrieval, chunk context, fusion, reranking, and bounded query
  decomposition
- Status: invalid held-out run; completed development calibration
- Date and owner: 2026-07-24, project researcher
- Code revision: `1e168ded1f5d6f04ae10a9d9b2fc987c819b98e8`
- Working tree: dirty from separately retained, non-implementation report
  changes; the frozen implementation tree hash was
  `e487096ed4f1c3551f3f2a25a2c86e290f905bc0b0d6be6027ffbf53eb48d2ba`
- Development command:
  `uv run python -m scripts.run_it5002_retrieval_rapid --phase development`
- Held-out command:
  `uv run python -m scripts.run_it5002_retrieval_rapid --phase heldout
  --confirm-heldout-once`
- Private artifacts:
  `experiments/runs/it5002_retrieval_rapid_v1/development_result.json`,
  `runtime_freeze.json`, and `heldout_once_ledger.json`
- Predecessor: `retrieval-v2-clean`
- Superseding result: none

## Decision context

The primary question was whether contextual hybrid Qwen3 reranking, R5,
improved complete course evidence over heading-aware BM25, R1, enough to
justify a larger confirmatory study and provisional end-to-end integration.
R0-R5 were frozen for all cases, R6 was limited to the multi-evidence slice,
and O1 was an oracle ceiling. R5 versus R1 was the only primary contrast.

The prediction was that R5 would add at least four complete-evidence successes
without reducing no-evidence accuracy. `Keep` and SOTA claims were unavailable
at this checkpoint. R1 remained the rollback under every outcome.

## Data and sample size

- Dataset: private `it5002-retrieval-rapid-v1`
- Corpus: 13 approved IT5002 lecture PDFs, 508 pages
- Development: 26 cases, comprising 13 answerable cases and 13 no-evidence
  cases
- Sealed held-out: 59 cases, comprising 39 answerable cases and 20 no-evidence
  cases
- Held-out SHA-256:
  `3ed3a8148255f0296c534b08e7cf8655a04cd5c34f87fcb0eb2cb6e45113629d`
- Development SHA-256:
  `123c25c9c3e12dfacf085c2cc3be08093f56a7434965a3addcccdbe8a69e77a1`
- Construction review: every lecture represented, reviewer pass rate 100%,
  no duplicate normalized queries, no cross-split family overlap, and maximum
  cross-query token Jaccard 0.7333
- Permission: course material stayed in ignored local storage; committed
  evidence contains hashes, counts, and configuration but no lecture or query
  text

The rapid sample was designed for coverage and large directional effects, not
precise final selection. Development values below are calibration evidence and
must not be reported as held-out performance.

## Exact configuration

- Embedding: `Qwen/Qwen3-Embedding-0.6B`, revision
  `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`
- Reranker: `Qwen/Qwen3-Reranker-0.6B`, revision
  `e61197ed45024b0ed8a2d74b80b4d909f1255473`
- Decomposer: Ollama `gemma3:4b`, digest `a2af6cc3eb7f`, seed 5002,
  temperature 0, one round, two to three subqueries
- Device and precision: Apple MPS, float16
- Embedding and reranker batch size: 8
- Maximum model input length: 2048
- First-stage candidate depth: 20 per retriever
- RRF constant: 60
- Returned K: 5; scored K: 3
- Python 3.12.13; NumPy 2.5.1; PyMuPDF 1.28.0; PyTorch 2.9.1;
  Transformers 4.57.6; Sentence Transformers 5.2.0

Per-condition thresholds were calibrated once on development and frozen:
R0 16.08369, R1 18.75639, R2 0.80337, R3 0.79024, R4 0.85373, and R5
0.99268.

## Development calibration results

| Condition | Complete evidence@3 | Claim coverage@3 | No-evidence accuracy | Warm p50 | Warm p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| R0 fixed-window BM25 | 3/13 | 3/13 | 13/13 | 18.6 ms | 75.0 ms |
| R1 heading-aware BM25 | 3/13 | 3/13 | 13/13 | 16.9 ms | 64.2 ms |
| R2 Qwen3 dense | 9/13 | 9/13 | 13/13 | 9.34 s | 16.74 s |
| R3 BM25+dense RRF | 9/13 | 9/13 | 13/13 | 9.36 s | 16.76 s |
| R4 contextual hybrid | 2/13 | 2/13 | 13/13 | 9.35 s | 16.75 s |
| R5 Qwen3 reranker | 10/13 | 10/13 | 13/13 | 49.98 s | 64.82 s |

R5 added seven development complete-evidence successes over R1, a large
directional quality signal. R4's regression shows that deterministic context
did not help by itself under the frozen decision score. Dense retrieval
provided most of the development improvement; reranking added one further
success over R2/R3.

No confidence interval or primary hypothesis test is reported for development
because it was used to calibrate thresholds and runtime. The predeclared paired
bootstrap and McNemar calculations required a complete held-out artifact and
therefore were not run.

## Held-out execution failure

The one-time ledger was created at `2026-07-23T16:39:53Z`. The process
completed 29 of the 59 standard R0-R5 cases. It was observed alive at
`2026-07-23T21:03:46Z` and absent at `2026-07-23T21:18:51Z`.

The ledger remained `started`, and no `heldout_result.json` was written.
Because the runner retained per-case values in memory until all standard, R6,
and O1 work completed, no partial quality metric can be recovered or reported.
R6 and O1 were not reached. The split is retired and must not be rerun.

The exact failure condition is premature process termination without retained
stderr or a macOS diagnostic report. During execution, Gemma initially
remained resident after decomposition preflight and the machine showed severe
unified-memory pressure, paging, alternating MPS waits, and multi-minute cases.
Those observations establish operational contamination, but they do not prove
that out-of-memory termination caused the final exit.

## Hard gates

| R5 gate | Result | Evidence |
| --- | --- | --- |
| Private text excluded from commits/logs | Pass | Only case counts were printed; private artifacts remain ignored |
| Provenance present | Pass on completed development artifact | Every returned development hit retained source, version, content hash, and page locator |
| No silent model fallback | Pass | Frozen local revisions and MPS device were bound before execution |
| Development no-evidence accuracy | Pass | 13/13; the held-out 19/20 gate is unavailable |
| Answerable non-regression | Directionally pass on development | 10/13 for R5 versus 3/13 for R1 |
| Warm p95 at most 5 seconds | **Fail** | Clean development R5 p95 was 64.82 seconds |
| Peak RSS at most 8 GiB | Pass but incomplete for unified GPU memory | `ru_maxrss` was 2.52 GiB |
| Cache at most 5 GiB | Pass | Combined model cache was 2.25 GiB |
| One complete sealed run | **Fail** | Process ended after 29/59 standard cases; no final artifact |

The latency failure alone disqualifies this R5 configuration from local
deployment. The incomplete held-out run invalidates any confirmatory quality
claim.

## Failure classification

- Operations: premature held-out process termination and catastrophic paging.
- Evaluation tooling: no per-case durable checkpoint and no retained stderr,
  so completed partial cases were lost.
- Model/runtime: Qwen3 embedding plus cross-encoder reranking was far above the
  target latency on a 16 GiB M1 Pro.
- Ranking: development misses remained for 3/13 R5 answerable cases.
- Context construction: R4 regressed to 2/13, so metadata context needs
  diagnosis before reuse.

No held-out case IDs, content, wins, or losses were inspected or reconstructed.

## Validity review

- Calibration/test separation preserved: yes; thresholds were frozen before
  held-out execution.
- Dataset integrity preserved: yes; hashes and disjoint families remained
  unchanged.
- Held-out metric reliability: unavailable because no final artifact exists.
- Run invalidated: yes.
- Reason: incomplete one-time execution with no durable per-case output.
- Corrected successor: none; a new sealed split and revised operational runner
  are required.

## Decision

- Outcome: **Drop** the current local MPS R5 configuration; held-out result
  status **Invalid**
- Selected implementation: none
- Profile change: none
- Retained fallback: R1 heading-aware BM25
- Rationale: R5 showed promising development quality but failed the 5-second
  p95 gate by about 13 times, and the sealed run did not complete.

## Limitations and follow-up

This result does not establish held-out retrieval quality, superiority to
NotebookLM, universal SOTA, answer-generation quality, learning effectiveness,
usability, or production readiness.

Before a successor confirmatory run:

1. persist each case atomically with a resumability policy defined before
   sealing;
2. retain stderr, exit code, system pressure, model residency, and per-stage
   timings;
3. isolate decomposition preflight from retrieval execution;
4. compare R1 with a latency-bounded dense or quantized reranking candidate;
5. require a clean synthetic endurance run before opening a new sealed split;
6. author a replacement held-out split rather than reuse this one.

## Learning note

A strong development quality gain is not enough to select a retriever. On the
actual target machine, the learned retrieval ladder made each query too slow
and then failed to finish the sealed study. Evaluability must include durable
case output and failure capture, while deployability gates must be applied
before celebrating ranking gains.
