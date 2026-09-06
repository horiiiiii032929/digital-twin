import json

import pytest

from scripts import run_asgi_tutoring_concurrency_development as runner
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmResponse


class MalformedContractClient:
    async def chat(self, messages, task):
        return LlmResponse(content="{}", provider_model=runner.MODEL, provider_revision="contract-only",
            usage=GenerationUsage(input_tokens=10, output_tokens=5, total_tokens=15, approximate_cost_usd=0.001))


@pytest.mark.asyncio
@pytest.mark.parametrize("students,turns", [(2, 2), (25, 4)])
@pytest.mark.parametrize("provider_concurrency", [1, 5])
async def test_actual_shared_service_route_contract_persists_responses_and_attribution(tmp_path, students, turns, provider_concurrency):
    result = await runner.run(tmp_path / "fresh", contract=True, students=students, turns=turns,
        injected_client=MalformedContractClient(), provider_max_concurrency=provider_concurrency)
    assert result.get("error") is None, result
    assert result["probe"]["request_count"] == students * turns
    assert result["probe"]["failure_count"] == 0
    assert result["persistence_counts_pass"]
    assert result["provider_attempts"] > 0
    assert all(call["case"].startswith("student-") and "-turn-" in call["case"] for call in result["provider_records"])
    assert result["quality_pass"] is None and result["deployment_qualified"] is False
    assert result["decision"] == "contract-only-not-capacity-evidence"
    rows = [json.loads(line) for line in (tmp_path / "fresh/responses.jsonl").read_text().splitlines()]
    assert len(rows) == students * turns
    assert all(row["response"]["tutor_message"]["content"] for row in rows)
    with pytest.raises(FileExistsError):
        await runner.run(tmp_path / "fresh", contract=True, students=2, turns=2)


@pytest.mark.asyncio
async def test_live_requires_exact_instrument_before_output_creation(tmp_path, monkeypatch):
    seen = []
    def deny(instrument, operation):
        seen.append((instrument, operation))
        raise PermissionError("not authorized")
    monkeypatch.setattr(runner, "require_bounded_pilot_operation_allowed", deny)
    with pytest.raises(PermissionError):
        await runner.run(tmp_path / "denied", contract=False)
    assert seen == [(runner.INSTRUMENT_ID, "external_model_evaluation")]
    assert not (tmp_path / "denied").exists()


@pytest.mark.asyncio
async def test_source_changes_invalidate_even_contract_execution(tmp_path, monkeypatch):
    versions = iter(({"source": "before"}, {"source": "after"}))
    monkeypatch.setattr(runner, "source_hashes", lambda: next(versions))
    result = await runner.run(tmp_path / "changed", contract=True, students=1, turns=1,
        injected_client=MalformedContractClient())
    assert result["decision"] == "invalid-source-change"
    assert result["source_unchanged"] is False


@pytest.mark.parametrize("students,turns", [(0, 1), (26, 4), (2, 0), (2, 5)])
def test_matrix_is_bounded(students, turns):
    with pytest.raises(ValueError):
        runner.validate(students, turns)
