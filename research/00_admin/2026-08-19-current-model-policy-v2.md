# Current model execution policy v2

Date: 2026-08-19

Policy ID: `current-model-policy-2026-08-19-v2`

Status: Active; supersedes v1 prospectively

## Decision

Gemma and Claude are prohibited from every new execution in this repository.
Historical results that used either family remain immutable evidence, but their
old executable commands are disabled. The retired local `qwen3:4b`,
Qwen3-derived general reviewers, and `qwen3.5:4b` are also prohibited for new
work.

Direct DeepSeek remains the selected product and bounded-evaluation transport.
OpenRouter is registered only as an optional gateway for exact, controlled
candidate routes. It does not replace direct DeepSeek until a project-specific
evaluation demonstrates equivalent or better quality, reproducibility,
privacy, latency, and cost.

## Current bindings

| Role | Exact model | Status and action |
|---|---|---|
| Product grounded generator | `deepseek-v4-flash` | Keep the selected direct-DeepSeek binding and deterministic rollback. |
| Dataset author and bounded primary evaluator | `deepseek-v4-pro` | Keep for already authorized workflows; evaluator reliability still requires calibration. |
| Local general and multimodal screening | `qwen3.5:9b-q4_K_M`, Ollama manifest digest `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7` | Prospective only. Use for low-cost screening and offline sensitivity checks after a role-specific quality gate; never as sole acceptance judge. |
| OpenRouter DeepSeek transport | `openrouter/deepseek/deepseek-v4-flash-0731` | Prospective gateway route. Keep direct DeepSeek selected while existing provider credit remains. |
| OpenRouter independent multimodal reviewer | `openrouter/mistralai/mistral-small-2603` | Prospective cross-family reviewer; not selected until the #87/public-probe instrument passes. |
| Selected text embedding | `Qwen/Qwen3-Embedding-0.6B` at revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3` | Keep the project-selected exact implementation. |
| Prospective text reranker | `Qwen/Qwen3-Reranker-0.6B` | Evaluated but not selected. |
| Prospective hosted text embedding | `jina-embeddings-v5-text-small`, API release `2026-02-18` | Registered candidate only. |
| Prospective hosted text reranker | `jina-reranker-v3`, API release `2025-10-01` | Registered candidate only. |

The 9B Q4_K_M artifact occupies 6.6 GB and shares text and image capabilities.
It is feasible on the 16 GiB M1 Pro development machine when run sequentially
with bounded context. The advertised maximum context is not a local operating
target: use one loaded model, `OLLAMA_NUM_PARALLEL=1`, and an 8K initial context
unless an instrument justifies more memory.

## Controlled OpenRouter boundary

Every prospective OpenRouter request must use:

- one exact, versioned model slug rather than a floating alias;
- `allow_fallbacks=false` so a failed model is visible instead of substituted;
- `require_parameters=true` so requested structured-output controls are not
  silently ignored;
- `data_collection=deny` and `zdr=true`;
- environment-owned `OPENROUTER_API_KEY`, with no credential in code, prompts,
  result records, or provider options; and
- response provenance, token usage, latency, and cost in the run artifact.

OpenRouter BYOK can use an existing DeepSeek provider key. This is an account
configuration action, not a repository action. If enabled, restrict the key to
the intended model and choose the account option that prevents fallback to
shared OpenRouter capacity. The repository will not copy or upload the existing
DeepSeek credential without explicit researcher authorization.

## Enforcement

- `require_model_allowed` rejects Gemma, Claude, and retired general-Qwen
  identities before provider or Ollama I/O.
- `LiteLlmClient` inherits the central guard for direct and OpenRouter calls.
- Package commands expose no prohibited model.
- Historical Claude code remains only for result provenance and is blocked by
  the current guard.
- `npm run verify:model-policy` checks exact identities, the pinned local
  manifest digest, strict OpenRouter options, guarded historical entrypoints,
  and this record without calling a model.
- A current registration establishes identity and transport policy only. Model
  quality and role selection require a separate prospective evaluation.

## Primary-source verification

- [Qwen3.5 9B Q4_K_M Ollama artifact](https://ollama.com/library/qwen3.5:9b-q4_K_M)
- [Ollama structured outputs](https://ollama.com/blog/structured-outputs)
- [OpenRouter provider routing controls](https://openrouter.ai/docs/guides/routing/provider-selection)
- [OpenRouter BYOK](https://openrouter.ai/docs/guides/overview/auth/byok)
- [LiteLLM OpenRouter provider](https://docs.litellm.ai/docs/providers/openrouter)
- [DeepSeek model list](https://api-docs.deepseek.com/api/list-models/)
- [Qwen3 Embedding official repository](https://github.com/QwenLM/Qwen3-Embedding)
- [Jina model catalog](https://jina.ai/models/)
