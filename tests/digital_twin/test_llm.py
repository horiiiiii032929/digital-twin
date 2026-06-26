import pytest

from src.digital_twin.llm import FixtureLlmClient, LlmMessage


@pytest.mark.asyncio
async def test_fixture_llm_returns_task_specific_response():
    client = FixtureLlmClient()

    response = await client.chat(
        messages=[LlmMessage(role="user", content="Extract a tutor policy.")],
        task="policy_extraction",
    )

    assert "policy_extraction" in response
    assert "fixture" in response
