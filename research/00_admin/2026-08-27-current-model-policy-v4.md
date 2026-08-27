# Current model policy v4

Status: prospective R1, build-only, provider execution unauthorized
Verified: 2026-08-27 (Asia/Singapore)

## Decision

The prospective R1 release and flow-independent factual-QA evaluation use only
direct OpenAI Responses API calls:

- high-volume wording and product generation:
  `gpt-5.4-mini-2026-03-17`;
- advisory semantic review: `gpt-5.4-2026-03-05`.

These are separate OpenAI model snapshots, not independent provider families.
Deterministic source-linked truth remains authoritative. Codex audits every
deterministic failure, every reviewer disagreement, and a seeded passing sample.

DeepSeek, Gemini, Mistral, OpenRouter, and local general models remain visible in
immutable historical instruments and results. They cannot be selected by the
prospective R1 profile or the active OpenAI evaluation checkpoint.

## Provider boundary

- Endpoint: `https://api.openai.com/v1/responses`.
- Credential: repository-ignored `OPENAI_API_KEY` only.
- Exact snapshot identity is required in every response.
- Structured output is strict and server-owned.
- `store` is always `false`; background mode, tools, provider routing, and
  fallback are disabled.
- There are no automatic retries in product execution. Evaluation retry and
  budget limits must be frozen explicitly before authorization.
- Every paid run requires model/pricing/retention metadata verified within 24
  hours, a clean worktree, a fresh exclusive ledger, and separate authority.

The API is not used for training by default. Standard abuse-monitoring logs may
retain customer content for up to 30 days unless an approved retention control
applies. R1 therefore remains public/synthetic-source-only until the production
privacy review explicitly permits another data boundary.

## Sources checked

- [GPT-5.4 mini model](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
- [GPT-5.4 model](https://developers.openai.com/api/docs/models/gpt-5.4)
- [OpenAI API data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint)

Any model, price, API behavior, or retention change creates a new prospective
binding. Historical evidence is never rewritten.
