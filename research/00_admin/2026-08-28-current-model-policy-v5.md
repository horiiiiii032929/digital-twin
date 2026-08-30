# Current model policy v9

Status: local R1 retained; API-first retrieval selection completed Refine and
provider execution revoked
Verified: 2026-08-30 (Asia/Singapore)

## Decision

The prospective R1 release and flow-independent factual-QA checkpoint use only
direct OpenAI Responses API calls:

- high-volume product generation: `gpt-5.4-mini-2026-03-17`;
- routine structured advisory review: `gpt-5.4-nano-2026-03-17`;
- at most 12 critical source-truth escalations: `gpt-5.4-2026-03-05`.

These are separate OpenAI model snapshots, not independent provider families.
Deterministic source-linked truth remains authoritative. Model reviews are
advisory, cannot change benchmark truth or scores, and unresolved critical
ambiguity is reserved for researcher review.

DeepSeek, Gemini, Mistral, OpenRouter, Codex review, and local general models
remain visible only in immutable historical evidence or separately closed
experiments. They cannot be selected by the active R1 evaluation checkpoint.

The AFQC-095 retrieval successor additionally registered direct OpenAI
`text-embedding-3-small` and `text-embedding-3-large`. AFQC-100 evaluated their
dense and BM25-hybrid configurations on 300 development cases; none passed and
neither model is selected as a release component. Historical local Qwen3
remains reproducible control evidence, while the active local R1 is unchanged.

## Provider boundary

- Endpoint: `https://api.openai.com/v1/responses`.
- Embedding endpoint: `https://api.openai.com/v1/embeddings`.
- Credential: repository-ignored `OPENAI_API_KEY` only.
- Exact dated snapshot identity is required in every response.
- Structured output is strict and server-owned.
- `store` is always `false`; background mode, tools, provider routing, and
  fallback are disabled.
- Product, routine review, and critical escalation use separate call and cost
  ledgers. Checkpoint 005 has zero retries and a USD 8 aggregate emergency stop.
- Every paid run requires model/pricing/retention metadata verified within 24
  hours, a clean worktree, a fresh exclusive ledger, and separate authority.
- Embedding requests are limited locally to 64 inputs and 50,000 estimated
  tokens, require exact returned model identity and dimensions, and persist
  each completed vector batch before continuing.

The API is not used for training by default. Standard abuse-monitoring logs may
retain customer content for up to 30 days unless an approved retention control
applies. R1 therefore remains public/synthetic-source-only until the production
privacy review explicitly permits another data boundary.

## Sources checked

- [GPT-5.4 mini model](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
- [GPT-5.4 nano model](https://developers.openai.com/api/docs/models/gpt-5.4-nano)
- [GPT-5.4 model](https://developers.openai.com/api/docs/models/gpt-5.4)
- [OpenAI API data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint)
- [Create embeddings API](https://developers.openai.com/api/reference/resources/embeddings/methods/create)
- [text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small)
- [text-embedding-3-large](https://developers.openai.com/api/docs/models/text-embedding-3-large)

Any model, price, API behavior, or retention change creates a new prospective
binding. Historical evidence is never rewritten.
