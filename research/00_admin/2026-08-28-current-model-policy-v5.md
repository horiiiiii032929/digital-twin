# Current model policy v5

Status: prospective R1, build-only, provider execution unauthorized  
Verified: 2026-08-28 (Asia/Singapore)

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

## Provider boundary

- Endpoint: `https://api.openai.com/v1/responses`.
- Credential: repository-ignored `OPENAI_API_KEY` only.
- Exact dated snapshot identity is required in every response.
- Structured output is strict and server-owned.
- `store` is always `false`; background mode, tools, provider routing, and
  fallback are disabled.
- Product, routine review, and critical escalation use separate call and cost
  ledgers. Checkpoint 005 has zero retries and a USD 8 aggregate emergency stop.
- Every paid run requires model/pricing/retention metadata verified within 24
  hours, a clean worktree, a fresh exclusive ledger, and separate authority.

The API is not used for training by default. Standard abuse-monitoring logs may
retain customer content for up to 30 days unless an approved retention control
applies. R1 therefore remains public/synthetic-source-only until the production
privacy review explicitly permits another data boundary.

## Sources checked

- [GPT-5.4 mini model](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
- [GPT-5.4 nano model](https://developers.openai.com/api/docs/models/gpt-5.4-nano)
- [GPT-5.4 model](https://developers.openai.com/api/docs/models/gpt-5.4)
- [OpenAI API data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint)

Any model, price, API behavior, or retention change creates a new prospective
binding. Historical evidence is never rewritten.
