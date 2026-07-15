import litellm
import pytest

from services.llm import LiteLlmClient
from src.digital_twin.llm import (
    LlmAuthenticationError,
    LlmMalformedResponseError,
    LlmMessage,
    LlmTimeoutError,
)


@pytest.mark.asyncio
async def test_litellm_adapter_records_usage_cost_and_keeps_credentials_external():
    captured = {}

    async def completion(**kwargs):
        captured.update(kwargs)
        return {
            "model": "provider/model-v1",
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
    assert response.usage.total_tokens == 15
    assert response.usage.approximate_cost_usd == 0.002
    assert captured["metadata"] == {"task": "grounded_tutor_answer"}
    assert "api_key" not in captured


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
