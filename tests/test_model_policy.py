import json
from pathlib import Path

import pytest

from scripts.run_factual_qa_quality_pilot import OllamaJsonTransport
from src.digital_twin.model_policy import (
    LOCAL_GENERAL_MODEL,
    OPENROUTER_DEEPSEEK_MODEL,
    OPENROUTER_INDEPENDENT_REVIEW_MODEL,
    ModelPolicyError,
    controlled_openrouter_provider_options,
    require_model_allowed,
    require_registered_current_model,
)


@pytest.mark.parametrize(
    "model",
    (
        "gemma3:4b",
        "ollama/gemma3:4b",
        "google/gemma-3-27b",
        "qwen3:4b",
        "ollama/qwen3:4b",
        "huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0",
        "qwen3.5:4b",
        "ollama/qwen3.5:4b",
        "claude-sonnet-5",
        "anthropic/claude-sonnet-5",
    ),
)
def test_model_policy_rejects_gemma_and_retired_general_reviewers(model):
    with pytest.raises(ModelPolicyError):
        require_model_allowed(model)


@pytest.mark.parametrize(
    "model",
    (
        "deepseek-v4-flash",
        "deepseek/deepseek-v4-pro",
        LOCAL_GENERAL_MODEL,
        OPENROUTER_DEEPSEEK_MODEL,
        OPENROUTER_INDEPENDENT_REVIEW_MODEL,
        "Qwen/Qwen3-Embedding-0.6B",
        "Qwen/Qwen3-Reranker-0.6B",
        "jina-embeddings-v5-text-small",
        "jina-reranker-v3",
    ),
)
def test_registered_current_models_are_accepted(model):
    assert require_registered_current_model(model) == model


def test_retired_factual_qa_instrument_cannot_construct_local_transport():
    with pytest.raises(ModelPolicyError, match="retired general model"):
        OllamaJsonTransport(
            {
                "model": "qwen3:4b",
                "model_digest": "historical",
                "temperature": 0,
                "seed": 1,
                "max_output_tokens": 1,
                "timeout_seconds": 1,
            },
            url="http://127.0.0.1:11434/api/generate",
        )


def test_controlled_openrouter_policy_is_strict_and_returned_by_value():
    options = controlled_openrouter_provider_options()

    assert options == {
        "extra_body": {
            "provider": {
                "allow_fallbacks": False,
                "require_parameters": True,
                "data_collection": "deny",
                "zdr": True,
            }
        }
    }
    options["extra_body"]["provider"]["allow_fallbacks"] = True
    assert controlled_openrouter_provider_options()["extra_body"]["provider"][
        "allow_fallbacks"
    ] is False


def test_package_commands_cannot_execute_retired_models():
    root = Path(__file__).resolve().parents[1]
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    rendered = "\n".join(
        f"{name} {command}" for name, command in package["scripts"].items()
    ).casefold()

    assert "gemma" not in rendered
    assert "claude" not in rendered
    assert "--model qwen3:4b" not in rendered
    assert "--model qwen3.5:4b" not in rendered
    assert "huihui_ai/qwen3-abliterated" not in rendered
