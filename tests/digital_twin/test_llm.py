import pytest

from src.digital_twin.llm import FixtureLlmClient, LlmMessage


@pytest.mark.asyncio
async def test_fixture_llm_returns_task_specific_response():
    client = FixtureLlmClient()

    response = await client.chat(
        messages=[LlmMessage(role="user", content="Extract a tutor policy.")],
        task="policy_extraction",
    )

    assert response == "fixture response for policy_extraction: Extract a tutor policy."


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
        response
        == "fixture response for policy_extraction: Use policy notes. Extract a tutor policy."
    )
