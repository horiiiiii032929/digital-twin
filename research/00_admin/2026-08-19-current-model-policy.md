# Current model execution policy

Date: 2026-08-19  
Policy ID: `current-model-policy-2026-08-19`  
Status: Active

## Decision

Gemma is prohibited from every new execution in this repository. Historical
Gemma inputs and results remain immutable research evidence, but their old
commands and provider paths are disabled. The same prospective-execution rule
applies to the retired local `qwen3:4b` and Qwen3-derived general reviewers.

“Current” means current for the component's task, with an exact model identity
and a recorded provider or artifact revision. It does not mean silently
replacing an evaluated component with the newest general model. A new model can
replace a selected component only through a new versioned evaluation.

## Current bindings

| Role | Exact model | Status and action |
|---|---|---|
| Product grounded generator | `deepseek-v4-flash` | Keep the selected binding. It is a current DeepSeek API model and remains covered by the held-out generator result. |
| Dataset author and bounded primary evaluator | `deepseek-v4-pro` | Keep for already authorized workflows. Evaluator reliability remains a separate calibration question. |
| Local general sensitivity reviewer | `qwen3.5:4b`, digest `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd` | New prospective binding only. Do not inherit decisions made by `qwen3:4b`. |
| Private multimodal independent reviewer | `claude-sonnet-5` | Keep as an optional governed review path. Anthropic identifies it as a current pinned model. |
| Selected text embedding | `Qwen/Qwen3-Embedding-0.6B` at revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3` | Keep. Qwen3 Embedding is the current task-specific Qwen embedding/ranking series, and this exact implementation is project-selected. |
| Prospective reranker | `Qwen/Qwen3-Reranker-0.6B` | Evaluated but not selected. It remains a current task-specific candidate, not an active product component. |

The 16 GiB development machine cannot practically run the current Qwen3.6
27B/35B local artifacts. `qwen3.5:4b` is therefore the newest size-compatible
official Qwen general and vision-language model for local diagnostic work. It
is not automatically selected for answer generation, judging, or multimodal
retrieval; each use needs a new instrument and its own quality gates.

## Historical and control models

- Gemma models: prohibited from execution; retain only their unfavorable and
  historical records.
- `qwen3:4b` and `huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0`:
  prohibited from new execution; retain old review records and invalid results.
- `BAAI/bge-small-en-v1.5`: a deterministic historical retrieval control, not
  the selected retriever and not a claim of current best performance.
- `ViT-B-32-quickgelu`: an evaluated visual-embedding control in an unselected
  multimodal method. A newer production visual method must be introduced as a
  prospective candidate rather than relabeling this result.

## Enforcement

- Model transports call `require_model_allowed` before provider or Ollama I/O.
- `LiteLlmClient` rejects Gemma and retired general Qwen identities centrally.
- Package commands cannot expose Gemma or an executable retired-Qwen binding.
- `npm run verify:model-policy` validates the selected product profile, current
  judge candidates, exact local digest, guarded historical entrypoints, and
  documentation without calling a model.
- Model freshness must be checked before each new named evaluation and at least
  once per release cycle. Floating `latest` aliases are not accepted as durable
  evidence.

## Primary-source verification

- [DeepSeek model list](https://api-docs.deepseek.com/api/list-models/)
- [DeepSeek V4 release](https://api-docs.deepseek.com/news/news260424/)
- [Qwen3.5 4B Ollama artifact and capabilities](https://ollama.com/library/qwen3.5%3A4b)
- [Qwen3 Embedding official repository](https://github.com/QwenLM/Qwen3-Embedding)
- [Anthropic current model overview](https://platform.claude.com/docs/en/about-claude/models/overview)
