import httpx
import pytest

from services.llm.openai_responses_client import OpenAiResponsesClient
from src.digital_twin.llm import (
    LlmAuthenticationError,
    LlmIdentityDriftError,
    LlmMessage,
)


MODEL = "gpt-5.4-mini-2026-03-17"


def _response(*, model: str = MODEL, text: str) -> httpx.Response:
    return httpx.Response(
        200,
        request=httpx.Request("POST", OpenAiResponsesClient.API_URL),
        json={
            "status": "completed",
            "model": model,
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": text}],
                }
            ],
            "usage": {"input_tokens": 12, "output_tokens": 5},
        },
    )


@pytest.mark.asyncio
async def test_openai_responses_client_uses_snapshot_strict_schema_and_no_storage(
    monkeypatch,
):
    captured = {}

    async def post(**kwargs):
        captured.update(kwargs)
        return _response(text='{"answer":"Grounded answer.","citation_ids":["S1"]}')

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    client = OpenAiResponsesClient(MODEL, post=post)

    result = await client.chat(
        [LlmMessage(role="user", content="Use approved source S1.")],
        task="grounded_tutor_answer",
    )

    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["json"]["model"] == MODEL
    assert captured["json"]["store"] is False
    assert captured["json"]["text"]["format"]["type"] == "json_schema"
    assert captured["json"]["text"]["format"]["strict"] is True
    assert "synthetic-test-key" not in str(captured["json"])
    assert result.provider_model == MODEL
    assert result.provider_revision == MODEL
    assert result.usage.approximate_cost_usd == pytest.approx(0.0000315)


@pytest.mark.asyncio
async def test_openai_responses_client_uses_atomic_claim_schema(monkeypatch):
    captured = {}

    async def post(**kwargs):
        captured.update(kwargs)
        return _response(
            text=(
                '{"claims":[{"claim_id":"claim-1","text":"Fact.",'
                '"citation_ids":["S1"]}]}'
            )
        )

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    client = OpenAiResponsesClient(MODEL, post=post)

    await client.chat(
        [LlmMessage(role="user", content="Return atomic claims.")],
        task="grounded_tutor_atomic_claims",
    )

    properties = captured["json"]["text"]["format"]["schema"]["properties"]
    assert "claims" in properties


@pytest.mark.asyncio
async def test_openai_responses_client_uses_bounded_autonomy_plan_schema(monkeypatch):
    captured = {}

    async def post(**kwargs):
        captured.update(kwargs)
        return _response(
            model="gpt-5.6-terra",
            text=(
                '{"action":"no-action","reason_code":"not-needed",'
                '"stop_condition":"Stop without delivery."}'
            ),
        )

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    client = OpenAiResponsesClient("gpt-5.6-terra", post=post)

    result = await client.chat(
        [LlmMessage(role="user", content="Plan one bounded tutoring event.")],
        task="autonomous_tutoring_plan",
    )

    payload = captured["json"]
    assert payload["model"] == "gpt-5.6-terra"
    assert payload["store"] is False
    assert payload["text"]["format"]["strict"] is True
    assert "allowed_actions" not in payload["text"]["format"]["schema"]["properties"]
    assert result.provider_model == "gpt-5.6-terra"


@pytest.mark.asyncio
async def test_openai_responses_client_uses_reactive_semantic_plan_schema(monkeypatch):
    captured = {}

    async def post(**kwargs):
        captured.update(kwargs)
        return _response(
            model="gpt-5.6-terra",
            text=(
                '{"proposed_intent":"give_hint",'
                '"concept_ids":["cache-coherence"],'
                '"hypothesis_kind":null,"hypothesis_concept_id":null,'
                '"hypothesis_confidence":0,"reason_code":"bounded-hint"}'
            ),
        )

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    client = OpenAiResponsesClient("gpt-5.6-terra", post=post)

    result = await client.chat(
        [LlmMessage(role="user", content="Plan one complex student turn.")],
        task="reactive_tutoring_plan",
    )

    schema = captured["json"]["text"]["format"]["schema"]
    assert "proposed_intent" in schema["properties"]
    assert set(schema["required"]) == set(schema["properties"])
    assert "default" not in schema["properties"]["schema_version"]
    assert schema["properties"]["schema_version"]["enum"] == ["2.1.0"]
    assert "maximum" not in schema["properties"]["hypothesis_confidence"]
    assert result.provider_model == "gpt-5.6-terra"


@pytest.mark.asyncio
async def test_openai_responses_client_fails_closed_on_identity_drift(monkeypatch):
    async def post(**kwargs):
        del kwargs
        return _response(
            model="gpt-5.4-mini",
            text='{"answer":"Grounded answer.","citation_ids":["S1"]}',
        )

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    client = OpenAiResponsesClient(MODEL, post=post)

    with pytest.raises(LlmIdentityDriftError):
        await client.chat(
            [LlmMessage(role="user", content="Question")],
            task="grounded_tutor_answer",
        )


@pytest.mark.asyncio
async def test_openai_responses_client_requires_environment_owned_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = OpenAiResponsesClient(MODEL)

    with pytest.raises(LlmAuthenticationError):
        await client.chat(
            [LlmMessage(role="user", content="Question")],
            task="grounded_tutor_answer",
        )
