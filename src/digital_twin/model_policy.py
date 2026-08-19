"""Repository-wide execution policy for model identities.

Historical records may name retired models, but executable transports must call
``require_model_allowed`` before sending a request.  Selection remains an
evaluation decision; this module only prevents prohibited or retired models
from being called accidentally.
"""

from __future__ import annotations

from dataclasses import dataclass


POLICY_ID = "current-model-policy-2026-08-19"
LOCAL_GENERAL_MODEL = "qwen3.5:4b"
LOCAL_GENERAL_MODEL_DIGEST = (
    "2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd"
)


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
        role="multimodal-independent-reviewer",
        provider_model="claude-sonnet-5",
        status="approved-private-review-option",
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
)

CURRENT_MODEL_IDS = frozenset(
    {
        binding.provider_model.casefold() for binding in CURRENT_MODEL_BINDINGS
    }
    | {
        "deepseek/deepseek-v4-flash",
        "deepseek/deepseek-v4-pro",
        "ollama/qwen3.5:4b",
    }
)

RETIRED_GENERAL_MODEL_IDS = frozenset(
    {
        "qwen3:4b",
        "ollama/qwen3:4b",
        "huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0",
        "ollama/huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0",
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
    if folded in RETIRED_GENERAL_MODEL_IDS:
        raise ModelPolicyError(
            f"{POLICY_ID} retired general model {normalized}; use "
            f"{LOCAL_GENERAL_MODEL} only in a new prospective instrument"
        )
    return normalized


def require_registered_current_model(model: str) -> str:
    """Require an exact model identity recorded in the current model registry."""

    normalized = require_model_allowed(model)
    if normalized.casefold() not in CURRENT_MODEL_IDS:
        raise ModelPolicyError(
            f"{normalized} is not registered by {POLICY_ID}; verify and record "
            "the exact provider identity before execution"
        )
    return normalized
