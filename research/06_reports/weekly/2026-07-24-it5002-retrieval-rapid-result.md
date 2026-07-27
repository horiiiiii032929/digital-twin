# Professor update: IT5002 retrieval screening

Date: 2026-07-24

Status: ready to send as an honest negative operational result; do not describe
it as a completed held-out quality comparison

## Suggested message

Professor,

I ran a prospectively frozen retrieval screening over all 13 IT5002 lectures.
The experiment compared fixed-window BM25, heading-aware BM25, Qwen3 dense
retrieval, hybrid fusion, contextual retrieval, and Qwen3 reranking. The
primary planned contrast was the Qwen3 reranker against heading-aware BM25.

The development result showed a strong quality direction:

| Method | Complete evidence@3 | No-evidence accuracy | Warm p95 |
| --- | ---: | ---: | ---: |
| Heading-aware BM25 | 3/13 | 13/13 | 64 ms |
| Qwen3 dense | 9/13 | 13/13 | 16.7 s |
| Qwen3 contextual reranker | 10/13 | 13/13 | 64.8 s |

However, the learned configuration failed the predeclared five-second latency
gate by about thirteen times. The one-time 59-case held-out process then
terminated after 29 cases under severe local memory pressure and wrote no final
artifact. I have registered that run as invalid and will not reconstruct,
rerun, or selectively report partial held-out quality.

My decision is therefore to drop this specific local MPS Qwen3 configuration,
retain heading-aware BM25 as the deployable rollback, and test a
latency-bounded dense or quantized alternative only after adding atomic
per-case persistence and a clean endurance preflight. The observed development
gain is a reason to investigate efficient semantic retrieval, not evidence
that the current method is selected or state of the art.

My question for your critique is: is the trade-off between complete evidence
retrieval and deployable latency a sufficiently meaningful central technical
problem for the report, or would you prioritize the returned-context
sufficiency failure boundary instead?

## Claim boundary

This checkpoint supports:

- a large development-only semantic-retrieval signal;
- rejection of the current local Qwen3 deployment configuration;
- retention of fast BM25 as rollback; and
- a concrete evaluation-tooling correction before the next sealed run.

It does not support:

- held-out superiority;
- a selected final RAG method;
- NotebookLM equivalence;
- SOTA, usability, learning-effectiveness, or production-readiness claims.

Detailed evidence:
[`it5002-retrieval-rapid-v1-results.md`](../../05_evaluation/it5002-retrieval-rapid-v1-results.md).
