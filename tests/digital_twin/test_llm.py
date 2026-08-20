import pytest
from pydantic import ValidationError

from src.digital_twin.llm import FixtureLlmClient, LlmMessage


@pytest.mark.asyncio
async def test_fixture_llm_returns_task_specific_response():
    client = FixtureLlmClient()

    response = await client.chat(
        messages=[LlmMessage(role="user", content="Extract a tutor policy.")],
        task="policy_extraction",
    )

    assert (
        response.content
        == "fixture response for policy_extraction: Extract a tutor policy."
    )
    assert response.provider_model == "fixture/v1"
    assert response.usage.total_tokens == 0


@pytest.mark.asyncio
async def test_fixture_llm_joins_messages_in_order():
    client = FixtureLlmClient()

    response = await client.chat(
        messages=[
            LlmMessage(role="system", content="Use policy notes."),
            LlmMessage(role="user", content="Extract a tutor policy."),
        ],
        task="policy_extraction",
    )

    assert (
        response.content
        == "fixture response for policy_extraction: Use policy notes. Extract a tutor policy."
    )


def test_llm_message_rejects_blank_content() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        LlmMessage(role="user", content="   ")


@pytest.mark.asyncio
async def test_fixture_llm_rejects_unsafe_task_metadata() -> None:
    with pytest.raises(ValueError, match="machine identifier"):
        await FixtureLlmClient().chat(
            [LlmMessage(role="user", content="Synthetic")],
            task="student private question",
        )
