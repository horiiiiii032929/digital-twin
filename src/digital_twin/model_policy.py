"""Repository-wide execution policy for model identities.

Historical records may name retired models, but executable transports must call
``require_model_allowed`` before sending a request.  Selection remains an
evaluation decision; this module only prevents prohibited or retired models
from being called accidentally.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


POLICY_ID = "current-model-policy-2026-08-21-v3"
LOCAL_GENERAL_MODEL = "qwen3.5:9b-q4_K_M"
LOCAL_GENERAL_MODEL_DIGEST = (
    "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
)
OPENROUTER_DEEPSEEK_MODEL = "openrouter/deepseek/deepseek-v4-flash-0731"
OPENROUTER_INDEPENDENT_REVIEW_MODEL = "openrouter/mistralai/mistral-small-2603"
OPENROUTER_QWEN_REVIEW_MODEL = "openrouter/qwen/qwen3.7-plus"
OPENROUTER_GEMINI_REVIEW_MODEL = "openrouter/google/gemini-3.7-flash"
OPENROUTER_GPT_MINI_REVIEW_MODEL = "openrouter/openai/gpt-5.4-mini"
_OPENROUTER_PROVIDER_OPTIONS: dict[str, Any] = {
    "extra_body": {
        "provider": {
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": "deny",
            "zdr": True,
        }
    }
}


class ModelPolicyError(ValueError):
    """Raised before a prohibited or retired model can be called."""


@dataclass(frozen=True)
class CurrentModelBinding:
    role: str
    provider_model: str
    status: str


CURRENT_MODEL_BINDINGS = (
    CurrentModelBinding(
        role="product-generator",
        provider_model="deepseek-v4-flash",
        status="selected",
    ),
    CurrentModelBinding(
        role="author-and-primary-evaluator",
        provider_model="deepseek-v4-pro",
        status="selected-for-bounded-workflows",
    ),
    CurrentModelBinding(
        role="local-general-sensitivity-reviewer",
        provider_model=LOCAL_GENERAL_MODEL,
        status="prospective-not-selected",
    ),
    CurrentModelBinding(
        role="openrouter-deepseek-transport",
        provider_model=OPENROUTER_DEEPSEEK_MODEL,
        status="prospective-not-selected-retain-direct-deepseek",
    ),
    CurrentModelBinding(
        role="multimodal-independent-reviewer",
        provider_model=OPENROUTER_INDEPENDENT_REVIEW_MODEL,
        status="qualified-advisory-fallback",
    ),
    CurrentModelBinding(
        role="factual-qa-independent-reviewer-candidate",
        provider_model=OPENROUTER_QWEN_REVIEW_MODEL,
        status="qualification-failed-not-selected",
    ),
    CurrentModelBinding(
        role="evidence-sufficiency-independent-reviewer-candidate",
        provider_model=OPENROUTER_GEMINI_REVIEW_MODEL,
        status="preserved-unexecuted-build-not-current",
    ),
    CurrentModelBinding(
        role="evidence-sufficiency-independent-reviewer-candidate",
        provider_model=OPENROUTER_GPT_MINI_REVIEW_MODEL,
        status="frozen-for-one-bounded-review",
    ),
    CurrentModelBinding(
        role="selected-text-embedding",
        provider_model="Qwen/Qwen3-Embedding-0.6B",
        status="selected",
    ),
    CurrentModelBinding(
        role="prospective-text-reranker",
        provider_model="Qwen/Qwen3-Reranker-0.6B",
        status="evaluated-not-selected",
    ),
    CurrentModelBinding(
        role="prospective-hosted-text-embedding",
        provider_model="jina-embeddings-v5-text-small",
        status="current-candidate-not-selected",
    ),
    CurrentModelBinding(
        role="prospective-hosted-text-reranker",
        provider_model="jina-reranker-v3",
        status="current-candidate-not-selected",
    ),
)

CURRENT_MODEL_IDS = frozenset(
    {binding.provider_model.casefold() for binding in CURRENT_MODEL_BINDINGS}
    | {
        "deepseek/deepseek-v4-flash",
        "deepseek/deepseek-v4-pro",
        "deepseek/deepseek-v4-flash-0731",
        "mistralai/mistral-small-2603",
        "qwen/qwen3.7-plus",
        "google/gemini-3.7-flash",
        "openai/gpt-5.4-mini",
        f"ollama/{LOCAL_GENERAL_MODEL}",
    }
)

RETIRED_GENERAL_MODEL_IDS = frozenset(
    {
        "qwen3:4b",
        "ollama/qwen3:4b",
        "huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0",
        "ollama/huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0",
        "qwen3.5:4b",
        "ollama/qwen3.5:4b",
    }
)


def require_model_allowed(model: str) -> str:
    """Return a normalized model identity or fail before provider execution."""

    normalized = model.strip()
    if not normalized:
        raise ModelPolicyError("model must not be empty")
    folded = normalized.casefold()
    if "gemma" in folded:
        raise ModelPolicyError(
            f"{POLICY_ID} prohibits every Gemma model from execution"
        )
    if "claude" in folded or folded.startswith("anthropic/"):
        raise ModelPolicyError(
            f"{POLICY_ID} prohibits every Claude model from execution"
        )
    if folded in RETIRED_GENERAL_MODEL_IDS:
        raise ModelPolicyError(
            f"{POLICY_ID} retired general model {normalized}; use "
            f"{LOCAL_GENERAL_MODEL} only in a new prospective instrument"
        )
    return normalized


def controlled_openrouter_provider_options() -> dict[str, Any]:
    """Return the frozen OpenRouter routing boundary without credentials."""

    return deepcopy(_OPENROUTER_PROVIDER_OPTIONS)


def require_registered_current_model(model: str) -> str:
    """Require an exact model identity recorded in the current model registry."""

    normalized = require_model_allowed(model)
    if normalized.casefold() not in CURRENT_MODEL_IDS:
        raise ModelPolicyError(
            f"{normalized} is not registered by {POLICY_ID}; verify and record "
            "the exact provider identity before execution"
        )
    return normalized
