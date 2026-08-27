import litellm
import pytest

from services.llm import LiteLlmClient
from src.digital_twin.llm import (
    LlmAuthenticationError,
    LlmIdentityDriftError,
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
            "model": "deepseek-v4-flash",
            "system_fingerprint": "fp-synthetic-v1",
            "choices": [{"message": {"content": '{"answer":"ok"}'}}],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 3,
                "total_tokens": 15,
            },
        }

    client = LiteLlmClient(
        "deepseek/deepseek-v4-flash",
        completion=completion,
        cost_calculator=lambda **kwargs: 0.002,
    )

    response = await client.chat(
        [LlmMessage(role="user", content="Synthetic prompt")],
        task="grounded_tutor_answer",
    )

    assert response.provider_model == "deepseek-v4-flash"
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
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": '{"answer":"ok"}'}}],
        }

    client = LiteLlmClient(
        "deepseek/deepseek-v4-flash",
        response_format={"type": "json_object"},
        completion=completion,
    )

    await client.chat([LlmMessage(role="user", content="test")], task="test")

    assert captured["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_litellm_adapter_accepts_per_call_strict_json_schema_override():
    captured = {}

    async def completion(**kwargs):
        captured.update(kwargs)
        return {
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": '{"answer":"ok"}'}}],
        }

    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "synthetic_answer",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["answer"],
                "properties": {"answer": {"type": "string"}},
            },
        },
    }
    client = LiteLlmClient(
        "deepseek/deepseek-v4-flash",
        response_format={"type": "json_object"},
        completion=completion,
    )

    await client.chat(
        [LlmMessage(role="user", content="test")],
        task="test",
        response_format=schema,
    )

    assert captured["response_format"] == schema


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


@pytest.mark.parametrize(
    "arguments",
    (
        {"timeout_seconds": float("nan")},
        {"temperature": float("nan")},
        {"max_output_tokens": True},
    ),
)
def test_litellm_adapter_rejects_non_finite_or_boolean_limits(arguments):
    with pytest.raises(ValueError):
        LiteLlmClient("deepseek/deepseek-v4-flash", **arguments)


@pytest.mark.parametrize(
    "field",
    ("temperature", "max_completion_tokens", "stream", "tools", "tool_choice"),
)
def test_litellm_adapter_rejects_protected_behavior_overrides(field):
    with pytest.raises(ValueError, match="protected fields"):
        LiteLlmClient(
            "deepseek/deepseek-v4-flash",
            provider_options={field: "synthetic-override"},
        )


@pytest.mark.parametrize("model", ("gemma3:4b", "ollama/gemma3:4b", "qwen3:4b"))
def test_litellm_adapter_blocks_prohibited_or_retired_models(model):
    with pytest.raises(ModelPolicyError):
        LiteLlmClient(model)


@pytest.mark.asyncio
async def test_litellm_adapter_rejects_empty_provider_content():
    async def completion(**kwargs):
        return {"model": "deepseek-v4-flash", "choices": []}

    client = LiteLlmClient("deepseek/deepseek-v4-flash", completion=completion)

    with pytest.raises(LlmMalformedResponseError):
        await client.chat([LlmMessage(role="user", content="test")], task="test")


@pytest.mark.asyncio
async def test_litellm_adapter_rejects_invalid_usage_values():
    async def completion(**kwargs):
        return {
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "valid content"}}],
            "usage": {"prompt_tokens": -1},
        }

    client = LiteLlmClient("deepseek/deepseek-v4-flash", completion=completion)

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

    client = LiteLlmClient("deepseek/deepseek-v4-flash", completion=completion)

    with pytest.raises(domain_error) as raised:
        await client.chat([LlmMessage(role="user", content="test")], task="test")

    assert "secret" not in str(raised.value)


@pytest.mark.asyncio
async def test_litellm_adapter_rejects_boolean_usage_and_multiple_choices():
    async def boolean_usage(**kwargs):
        del kwargs
        return {
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": "valid"}}],
            "usage": {"prompt_tokens": True},
        }

    client = LiteLlmClient(
        "deepseek/deepseek-v4-flash",
        completion=boolean_usage,
    )
    with pytest.raises(LlmMalformedResponseError):
        await client.chat([LlmMessage(role="user", content="test")], task="test")

    async def multiple_choices(**kwargs):
        del kwargs
        return {
            "model": "deepseek-v4-flash",
            "choices": [
                {"message": {"content": "first"}},
                {"message": {"content": "second"}},
            ],
        }

    client = LiteLlmClient(
        "deepseek/deepseek-v4-flash",
        completion=multiple_choices,
    )
    with pytest.raises(LlmMalformedResponseError):
        await client.chat([LlmMessage(role="user", content="test")], task="test")


def test_litellm_adapter_rejects_unregistered_model_before_provider_setup():
    with pytest.raises(ModelPolicyError, match="not registered"):
        LiteLlmClient("provider/model-v1")


@pytest.mark.asyncio
async def test_litellm_adapter_rejects_model_or_revision_drift():
    async def completion(**kwargs):
        del kwargs
        return {
            "model": "deepseek-v4-pro",
            "system_fingerprint": "unexpected",
            "choices": [{"message": {"content": "valid"}}],
        }

    client = LiteLlmClient(
        "deepseek/deepseek-v4-flash",
        expected_provider_model="deepseek-v4-flash",
        expected_provider_revision="expected",
        completion=completion,
    )

    with pytest.raises(LlmIdentityDriftError) as captured:
        await client.chat([LlmMessage(role="user", content="test")], task="test")
    assert captured.value.provider_model == "deepseek-v4-pro"
    assert captured.value.provider_revision == "unexpected"
