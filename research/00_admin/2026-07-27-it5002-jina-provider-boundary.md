# IT5002 Jina retrieval-evaluation boundary

Date: 2026-07-27

Status: user authorized; retrieval evaluation only

The project owner authorized the 13 IT5002 lecture PDFs to be processed by the
Jina Search Foundation embedding and reranking endpoints for this retrieval
evaluation. This decision changes only the external-provider boundary recorded
in `it5002-lectures-v1`; it does not authorize student-facing release, student
data, assessment material, answer files, or general-purpose generation.

## Approved boundary

- Provider: Jina Search Foundation API.
- Endpoints: `/v1/embeddings` and `/v1/rerank`.
- Models: `jina-embeddings-v3` and `jina-reranker-v3`.
- Data: the 13 inventoried lecture PDFs, derived chunks, and researcher-authored
  retrieval questions.
- Purpose: development preflight and a later prospectively frozen retrieval
  comparison.
- Excluded: tutorials, assessments, solutions, student records, conversations,
  secrets, and generated tutoring answers.
- Repository boundary: source text, queries, provider payloads, and raw
  per-case outputs remain ignored and local.
- Cost boundary: each executable run must declare and enforce a cost cap before
  transmitting any content.

The provider states in its
[embedding documentation](https://jina.ai/en-US/embeddings/) and
[reranking documentation](https://jina.ai/en-US/reranker/) that API request
inputs and outputs are not used to train its models. The public documentation
does not by itself establish a
project-specific zero-retention or processing-location guarantee, so retention,
regional processing, and institutional policy remain limitations.

This authorization may be revoked by changing the corpus manifest before a
later run. Student-facing use still requires a separate professor or
institutional decision.
