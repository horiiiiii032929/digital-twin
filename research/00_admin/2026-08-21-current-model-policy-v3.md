# Current model execution policy v3

Date: 2026-08-21

Policy ID: `current-model-policy-2026-08-21-v3`

Status: Active; supersedes v2 prospectively

## Decision

Preserve the v2 prohibitions on Gemma, Claude, retired local Qwen models, and
silent provider fallback. Direct DeepSeek remains the selected product and
bounded-authoring transport. Mistral Small 4 remains the qualified advisory
reviewer after `factual-qa-v3-reviewer-qualification-006` passed all gates.

Register exact hosted `openrouter/qwen/qwen3.7-plus` only as a prospective
factual-QA reviewer candidate. Registration permits a bounded synthetic-public
qualification; it does not select Qwen3.7 Plus or authorize the 100, 1,000, or
10,000-case stages.

## Current bindings

| Role | Exact model | Status and action |
|---|---|---|
| Product grounded generator | `deepseek-v4-flash` | Selected with deterministic rollback. |
| Dataset author and bounded dispute evaluator | `deepseek-v4-pro` | Selected only for already authorized bounded workflows. |
| Independent reviewer fallback | `openrouter/mistralai/mistral-small-2603` | Qualified advisory fallback from run 006. |
| Independent reviewer candidate | `openrouter/qwen/qwen3.7-plus` | Run one new 24-pair qualification under a USD 0.10 hard stop before any role selection. |
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
- Decision: select the candidate only if every frozen quality and cost gate
  passes. Otherwise retain Mistral Small 4 without model shopping.

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

## Primary-source verification

- [Alibaba Cloud current Qwen models](https://www.alibabacloud.com/help/en/model-studio/models)
- [Alibaba Cloud Qwen pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing)
- [OpenRouter Qwen3.7 Plus route](https://openrouter.ai/qwen/qwen3.7-plus-20260602)
- [OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)
