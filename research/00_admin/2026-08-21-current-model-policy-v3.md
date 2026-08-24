# Current model execution policy v3

Date: 2026-08-21

Policy ID: `current-model-policy-2026-08-21-v3`

Status: Active; supersedes v2 prospectively

## Decision

Preserve the v2 prohibitions on Gemma, Claude, retired local Qwen models, and
silent provider fallback. Direct DeepSeek remains the selected product and
bounded-authoring transport. Mistral Small 4 remains the qualified advisory
reviewer after `factual-qa-v3-reviewer-qualification-006` passed all gates.
Its exact first-party OpenRouter binding failed operationally for
evidence-sufficiency review 004 and is not retried there. Stable Gemini 3.7
Flash is registered prospectively for review 005, but remains unselected and
provider-unauthorized. Review 006 preserves that unexecuted build and
prospectively selects snapshot-pinned GPT-5.4 mini as the single next reviewer
candidate; it also remains provider-unauthorized.

Qualification 007 did not select hosted `openrouter/qwen/qwen3.7-plus`: it
failed completion, specificity, sensitivity, malformed-response, latency, and
cost gates. Its one-time authorization is revoked. This result does not
authorize the 100, 1,000, or 10,000-case stages.

## Current bindings

| Role | Exact model | Status and action |
|---|---|---|
| Product grounded generator | `deepseek-v4-flash` | Selected with deterministic rollback. |
| Dataset author and bounded dispute evaluator | `deepseek-v4-pro` | Selected only for already authorized bounded workflows. |
| Independent reviewer fallback | `openrouter/mistralai/mistral-small-2603` | Qualified advisory fallback from run 006. |
| Rejected independent reviewer candidate | `openrouter/qwen/qwen3.7-plus` | Qualification 007 failed six gates; do not bind it into the 100-case stage. |
| Evidence-sufficiency reviewer candidate | `openrouter/google/gemini-3.7-flash` through exact `google-ai-studio` routing | Stable cross-family candidate for review 005; build-only and provider-unauthorized. |
| Current evidence-sufficiency reviewer candidate | `openrouter/openai/gpt-5.4-mini` through exact `openai` routing | Snapshot-pinned review 006 candidate; build-only and provider-unauthorized. Review 005 is preserved but will not be executed or used as fallback. |
| Local general screening | `qwen3.5:9b-q4_K_M` at digest `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7` | Prospective only; not used by the factual-QA scale pipeline. |
| OpenRouter DeepSeek transport | `openrouter/deepseek/deepseek-v4-flash-0731` | Prospective gateway; direct DeepSeek remains selected. |
| Selected text embedding | `Qwen/Qwen3-Embedding-0.6B` | Keep the project-selected retrieval implementation. |
| Prospective text reranker | `Qwen/Qwen3-Reranker-0.6B` | Evaluated, not selected. |
| Prospective hosted retrieval | `jina-embeddings-v5-text-small`; `jina-reranker-v3` | Registered candidates only. |

## Qwen3.7 Plus qualification boundary

- Purpose: determine whether it can replace Mistral Small 4 as the independent
  factual-QA reviewer at acceptable quality, latency, and cost.
- Dataset: 24 new synthetic-public clean/defect pairs across six citation and
  binding mutation classes; no reused run-006 instances.
- Route: exact `openrouter/qwen/qwen3.7-plus`, no fallback, required parameters,
  provider collection allowed only for these synthetic fixtures.
- Bound: one canary plus 48 reviews, zero retries, USD 0.10 hard stop, durable
  eight-call checkpoints.
- Authority: deterministic validity is ground truth. Qwen's verdict is
  advisory and cannot repair a deterministic failure.
- Decision: **Drop for this role.** Qualification 007 failed six frozen gates;
  retain Mistral Small 4 without model shopping.
- Operational finding: the route returned up to 2,172 billed output tokens even
  though 650 were requested. The prospective reservation therefore understated
  actual cost and the run reached USD 0.128239 against a USD 0.10 gate. Harden
  paid-run cost enforcement before authorizing the 100-case stage.

## Price basis

The qualification freezes $0.32 per million input tokens and $1.28 per million
output tokens, matching the OpenRouter Qwen3.7 Plus route observed on
2026-08-21. Pricing must be checked again before a larger paid stage.

## Controlled OpenRouter boundary

All prospective OpenRouter calls require an exact model slug,
`allow_fallbacks=false`, `require_parameters=true`, environment-owned
credentials, response provenance, complete token/latency/cost accounting, and
fail-closed model identity checks. Synthetic qualification data may be retained
by the named provider under the researcher's evaluation-phase authorization;
private course, instructor, student, product, and credential data remain
prohibited.

Review 005 additionally pins the Google AI Studio endpoint, disables every
fallback, requires strict structured output, records the dated backend identity
`google/gemini-3.7-flash-20260813`, and permits only the synthetic-public review
packet. Its maximum 13-call reservation is USD 0.39 under the USD 0.50 ceiling.

Review 006 pins the OpenAI standard endpoint and dated backend identity
`openai/gpt-5.4-mini-20260317`. It requires strict structured output, seed `0`,
reasoning effort `none`, and no fallback. It omits `temperature` because the
current endpoint does not advertise that parameter. The maximum 13-call
reservation is USD 0.429 under the unchanged USD 0.50 ceiling. This binding is
prospective and does not claim reviewer quality before the frozen sensitivity
call.

## Primary-source verification

- [Alibaba Cloud current Qwen models](https://www.alibabacloud.com/help/en/model-studio/models)
- [Alibaba Cloud Qwen pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing)
- [OpenRouter Qwen3.7 Plus route](https://openrouter.ai/qwen/qwen3.7-plus-20260602)
- [OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Google stable Gemini models](https://ai.google.dev/gemini-api/docs/models)
- [Google Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [OpenAI GPT-5.4 mini specification](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
