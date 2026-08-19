import litellm
import pytest

from services.llm import LiteLlmClient
from src.digital_twin.llm import (
    LlmAuthenticationError,
    LlmMalformedResponseError,
    LlmMessage,
    LlmTimeoutError,
)
from src.digital_twin.model_policy import ModelPolicyError


@pytest.mark.asyncio
async def test_litellm_adapter_records_usage_cost_and_keeps_credentials_external():
    captured = {}

    async def completion(**kwargs):
        captured.update(kwargs)
        return {
            "model": "provider/model-v1",
            "system_fingerprint": "fp-synthetic-v1",
            "choices": [{"message": {"content": '{"answer":"ok"}'}}],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 3,
                "total_tokens": 15,
            },
        }

    client = LiteLlmClient(
        "provider/model-v1",
        completion=completion,
        cost_calculator=lambda **kwargs: 0.002,
    )

    response = await client.chat(
        [LlmMessage(role="user", content="Synthetic prompt")],
        task="grounded_tutor_answer",
    )

    assert response.provider_model == "provider/model-v1"
    assert response.provider_revision == "fp-synthetic-v1"
    assert response.usage.total_tokens == 15
    assert response.usage.approximate_cost_usd == 0.002
    assert captured["metadata"] == {"task": "grounded_tutor_answer"}
    assert "api_key" not in captured


@pytest.mark.asyncio
async def test_litellm_adapter_requests_json_mode_only_when_configured():
    captured = {}

    async def completion(**kwargs):
        captured.update(kwargs)
        return {
            "model": "local/model",
            "choices": [{"message": {"content": '{"answer":"ok"}'}}],
        }

    client = LiteLlmClient(
        "local/model",
        response_format={"type": "json_object"},
        completion=completion,
    )

    await client.chat([LlmMessage(role="user", content="test")], task="test")

    assert captured["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_litellm_adapter_can_omit_temperature_for_thinking_models():
    captured = {}

    async def completion(**kwargs):
        captured.update(kwargs)
        return {
            "model": "deepseek-v4-pro",
            "choices": [{"message": {"content": '{"answer":"ok"}'}}],
        }

    client = LiteLlmClient(
        "deepseek/deepseek-v4-pro",
        temperature=None,
        completion=completion,
    )

    await client.chat([LlmMessage(role="user", content="test")], task="test")

    assert "temperature" not in captured


@pytest.mark.asyncio
async def test_litellm_adapter_passes_frozen_provider_options_without_credentials():
    captured = {}

    async def completion(**kwargs):
        captured.update(kwargs)
        return {
            "model": "deepseek-v4-flash",
            "system_fingerprint": "fp-v4-flash-synthetic",
            "choices": [{"message": {"content": '{"answer":"ok"}'}}],
        }

    client = LiteLlmClient(
        "deepseek/deepseek-v4-flash",
        response_format={"type": "json_object"},
        provider_options={"extra_body": {"thinking": {"type": "disabled"}}},
        completion=completion,
    )

    response = await client.chat(
        [LlmMessage(role="user", content="synthetic")],
        task="generator_qualification",
    )

    assert captured["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "api_key" not in captured
    assert response.provider_revision == "fp-v4-flash-synthetic"


def test_litellm_adapter_rejects_provider_option_credential_override():
    with pytest.raises(ValueError, match="protected fields"):
        LiteLlmClient(
            "deepseek/deepseek-v4-flash",
            provider_options={"api_key": "must-not-be-accepted"},
        )


@pytest.mark.parametrize("model", ("gemma3:4b", "ollama/gemma3:4b", "qwen3:4b"))
def test_litellm_adapter_blocks_prohibited_or_retired_models(model):
    with pytest.raises(ModelPolicyError):
        LiteLlmClient(model)


@pytest.mark.asyncio
async def test_litellm_adapter_rejects_empty_provider_content():
    async def completion(**kwargs):
        return {"model": "provider/model-v1", "choices": []}

    client = LiteLlmClient("provider/model-v1", completion=completion)

    with pytest.raises(LlmMalformedResponseError):
        await client.chat([LlmMessage(role="user", content="test")], task="test")


@pytest.mark.asyncio
async def test_litellm_adapter_rejects_invalid_usage_values():
    async def completion(**kwargs):
        return {
            "model": "provider/model-v1",
            "choices": [{"message": {"content": "valid content"}}],
            "usage": {"prompt_tokens": -1},
        }

    client = LiteLlmClient("provider/model-v1", completion=completion)

    with pytest.raises(LlmMalformedResponseError):
        await client.chat([LlmMessage(role="user", content="test")], task="test")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_error", "domain_error"),
    [
        (
            litellm.Timeout("secret", "model", "provider"),
            LlmTimeoutError,
        ),
        (
            litellm.AuthenticationError("secret", "provider", "model"),
            LlmAuthenticationError,
        ),
    ],
)
async def test_litellm_adapter_maps_provider_errors_without_copying_messages(
    provider_error,
    domain_error,
):
    async def completion(**kwargs):
        raise provider_error

    client = LiteLlmClient("provider/model-v1", completion=completion)

    with pytest.raises(domain_error) as raised:
        await client.chat([LlmMessage(role="user", content="test")], task="test")

    assert "secret" not in str(raised.value)
