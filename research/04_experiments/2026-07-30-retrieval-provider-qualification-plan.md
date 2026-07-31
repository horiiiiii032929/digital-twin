# Retrieval provider qualification v1

Date: 2026-07-30

Status: local control completed; hosted candidate retired by the prospective
2026-07-31 deployability amendment; no held-out access permitted

This v1 plan is retained as historical evidence. The local half ran as planned.
Before the hosted half ran, the project removed hosted-provider comparison as
a selection requirement because the final research question is M0-M3 method
quality under a local deployment boundary. See
[`2026-07-31-local-retrieval-deployability-plan.md`](2026-07-31-local-retrieval-deployability-plan.md).

## Decision question

Which one embedding and reranking provider configuration is sufficiently
accurate, reproducible, private, affordable, and operationally reliable to
freeze for the final M0-M3 cross-course retrieval comparison?

This qualification chooses provider bindings only. It does not select the
retrieval method or change the active component profile.

## Data boundary

- Dataset: the 40-case development file from
  `cross-course-retrieval-v1-draft-6-seal`.
- Corpus: the 32 approved PDFs in `cross-course-portfolio-v2`.
- Held-out: the separately hashed 60-case file remains unopened. The
  development runner may read the seal and unopened ledger metadata, but it
  must never read the held-out file.
- External data: only approved course passages and development queries may be
  sent to the qualified hosted provider. No student data, credentials,
  solutions, answer keys, submissions, or excluded sources may leave the
  workstation.

## Control and candidate

### L0 local control

- Embedding: `Qwen/Qwen3-Embedding-0.6B`, pinned local revision
  `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`.
- Reranking: `Qwen/Qwen3-Reranker-0.6B`, pinned local revision
  `e61197ed45024b0ed8a2d74b80b4d909f1255473`.
- Execution: Apple MPS, float16, maximum length 2,048.
- External calls and cost: zero.

### H1 hosted candidate

- Embedding: Jina `jina-embeddings-v5-text-small`, dense 1,024-dimensional
  retrieval query/passage adapters.
- Reranking: Jina `jina-reranker-v3`.
- Endpoints: `https://api.jina.ai/v1/embeddings` and
  `https://api.jina.ai/v1/rerank`.
- Execution: hosted API with exact response model names, usage, request counts,
  and sanitized request failures recorded.
- Prospective maximum charged or conservatively accounted cost: USD 5.00. For
  pre-request enforcement, the runner applies a deliberately conservative USD
  1.00 per million estimated input tokens unless a lower provider-reported
  charge is durably available. It blocks a request before this accounting cap
  would be exceeded.

The hosted candidate uses a current text-focused embedding model rather than
the earlier unselected `jina-embeddings-v3` spike. Multimodal embedding is not
part of this text retrieval comparison.

Provider identities were checked against Jina's current
[Search Foundation API specification](https://api.jina.ai/redoc),
[embedding documentation](https://jina.ai/en-US/embeddings/), and
[reranker documentation](https://jina.ai/en-US/reranker/) on 2026-07-30.
Vendor benchmark claims do not contribute to the selection decision.

## Shared retrieval ladder

For each provider configuration, build a separate index per authorized course:

- M0: BM25, `k1=1.2`, `b=0.75`;
- M1: dense cosine retrieval;
- M2: M0 plus M1 reciprocal-rank fusion, `k=60`, first-stage depth 20; and
- M3: M2 candidate depth 40 plus the configured reranker.

Every stage receives only the selected course's approved chunks. Returned
chunks are checked against the same course scope; any mismatch fails the
configuration.

## Metrics and gates

Quality metrics on positive cases:

- complete-evidence success@3;
- atomic evidence Recall@1, Recall@3, and Recall@5;
- nDCG@10; and
- mean reciprocal rank.

Boundary diagnostics:

- no-evidence calibration accuracy;
- positive answer-rate calibration; and
- action accuracy, reported as development diagnostics only.

Operational measures:

- model/index construction time;
- retrieval p50 and p95 latency;
- request and retry counts;
- provider-reported or conservatively estimated input tokens;
- billed or estimated cost;
- peak local memory and local model-cache size where applicable; and
- categorized provider, data, ranking, isolation, and operational failures.

Hard gates:

- zero held-out file reads;
- zero course-isolation or permission violations;
- exact model/configuration identity recorded;
- complete, parseable output for all 40 development cases;
- no secret or private text in durable output;
- no request after the USD 5.00 cap would be exceeded; and
- one clean deterministic or cached reproduction before provider freeze.

## Decision rule

Quality decides whether a provider is useful; local hardware speed does not
decide retrieval quality. Prefer the simpler/local control when the hosted
candidate has no meaningful project-specific quality advantage. Advance H1
only when its development evidence is better enough to justify external-data,
cost, and operational complexity. If neither configuration completes or passes
hard gates, record `Refine` and freeze no final provider.

The selected binding, or explicit no-selection result, receives a registered
result and a versioned runtime freeze before issue #7 may open the one-time
held-out split.

## Refactor boundary

Before measurement:

1. preserve the existing provider-neutral retrieval protocols;
2. extract M0-M3 configuration and metrics from the pilot script;
3. add normalized provider identity, usage, cost-cap, and sanitized-failure
   records;
4. add a development loader that verifies the seal without reading held-out
   content;
5. keep local and hosted adapters behind the same interfaces; and
6. cover provider contracts, course isolation, budget blocking, hashes, and
   development-only access with synthetic tests.

Do not refactor onboarding, the frontend, authentication, persistence,
generation, historical results, or the sealed dataset.
