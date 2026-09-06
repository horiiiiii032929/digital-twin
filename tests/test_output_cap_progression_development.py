import json

import pytest

from scripts import run_output_cap_progression_development as packet
from scripts.run_final_profile_longitudinal import RecordedRunClient, MODEL
from services.llm import OpenAiResponsesClient
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmMalformedResponseError, LlmResponse


class FakeClient:
    def __init__(self, cap):
        self.cap = cap

    async def chat(self, messages, task):
        if task != "question_specific_profile_tutoring":
            raise LlmMalformedResponseError(stage="contract-planner", usage=GenerationUsage(approximate_cost_usd=0))
        p = json.loads(messages[-1].content)
        source = p["evidence"][0]
        return LlmResponse(provider_model=MODEL, usage=GenerationUsage(input_tokens=10, output_tokens=20,
            total_tokens=30, approximate_cost_usd=.0001), content=json.dumps({
                "boundary": "answerable", "aspects": [{"requirement": "course rule", "supported": True,
                    "spans": [{"citation_id": source["citation_id"], "text": source["text"]}]}],
                "teaching_move": "explain", "question_focus": "", "hint_span": None}))


def test_predeclared_matrix_has_three_repeats_and_matched_stimuli():
    assert len(packet.dataset()) == 48
    assert sum(len(r["situation"]["prompts"]) for r in packet.dataset()) == 192
    assert {r["cap"] for r in packet.dataset()} == {500, 1500}
    for seed in packet.SEEDS:
        for case in packet.SITUATIONS:
            matching = [r for r in packet.dataset() if r["seed"] == seed and r["situation"]["id"] == case["id"]]
            assert len(matching) == 2 and matching[0]["situation"] == matching[1]["situation"]


def test_recorded_request_uses_explicit_output_cap_for_serialization_and_reservation(tmp_path):
    control = RecordedRunClient(FakeClient(500), tmp_path / "control.jsonl", maximum_calls=2,
        maximum_cost_usd=.04, reservation_usd=.02, network_mode="contract")
    candidate = RecordedRunClient(FakeClient(1500), tmp_path / "candidate.jsonl", maximum_calls=2,
        maximum_cost_usd=.04, reservation_usd=.02, network_mode="contract", max_output_tokens=1500)
    assert control.serializer.max_output_tokens == 500
    assert candidate.serializer.max_output_tokens == 1500
    assert OpenAiResponsesClient(MODEL).max_output_tokens != 1500
    with pytest.raises(ValueError, match="output caps must match"):
        RecordedRunClient(OpenAiResponsesClient(MODEL, max_output_tokens=1500), tmp_path / "mismatch.jsonl",
            maximum_calls=2, maximum_cost_usd=.04, reservation_usd=.02, network_mode="contract")


@pytest.mark.asyncio
async def test_actual_service_paired_contract_retains_restarts_lineage_and_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(packet, "SEEDS", (7301,))
    monkeypatch.setattr(packet, "SITUATIONS", packet.SITUATIONS[:1])
    result = await packet.run(tmp_path / "paired", transport_factory=FakeClient)
    assert result["decision"] == "contract-only"
    assert result["source_files_unchanged"]
    assert len(result["histories"]) == 2
    assert all(r["completed"] and r["turns"] == 4 and r["restarts"] == 1 for r in result["histories"])
    assert all(r["citation_lineage_violations"] == 0 for r in result["histories"])
    assert all(r["initial_messages_equal"] for r in result["initial_pairs"])
    assert not result["default_or_selected_profile_changed"]
    for cap in packet.CAPS:
        records = [json.loads(line) for line in (tmp_path / "paired" / f"provider-{cap}.jsonl").read_text().splitlines()]
        assert all(r["requested_model"] == MODEL for r in records if r["status"] == "started")
    with pytest.raises(FileExistsError):
        await packet.run(tmp_path / "paired", transport_factory=FakeClient)
