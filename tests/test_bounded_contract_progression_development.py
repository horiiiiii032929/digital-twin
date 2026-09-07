import json

import pytest

from scripts import run_bounded_contract_progression_development as packet
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmMalformedResponseError, LlmResponse


class FakeClient:
    def __init__(self, version):
        self.version = version

    async def chat(self, messages, task):
        if task != "question_specific_profile_tutoring":
            raise LlmMalformedResponseError(stage="contract-plan", usage=GenerationUsage(approximate_cost_usd=0))
        payload = json.loads(messages[-1].content)
        assert ("response_contract" in payload) == (self.version in {"v3", "v4"})
        source = payload["evidence"][0]
        return LlmResponse(provider_model="gpt-5.6-luna", usage=GenerationUsage(input_tokens=10,
            output_tokens=10, total_tokens=20, approximate_cost_usd=.0001), content=json.dumps({
                "boundary": "answerable", "aspects": [{"requirement": "approved rule", "supported": True,
                    "spans": [{"citation_id": source["citation_id"], "text": source["text"]}]}],
                "teaching_move": "explain", "hint_span": None, "question_focus": ""}))


def test_fixed_cap_versions_and_fresh_situations_are_explicit():
    assert len(packet.dataset()) == 36
    assert sum(len(s["situation"]["prompts"]) for s in packet.dataset()) == 72
    assert {s["situation"]["id"] for s in packet.dataset()} >= {"five-related-details", "separate-nine-details", "supported-and-absent"}


@pytest.mark.asyncio
async def test_actual_factory_optin_keeps_v2_control_and_persists_v3_after_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(packet, "SEEDS", (7401,))
    monkeypatch.setattr(packet, "SITUATIONS", packet.SITUATIONS[-3:-2])
    result = await packet.run(tmp_path / "contracts", transport_factory=FakeClient)
    assert result["decision"] == "contract-only" and result["source_files_unchanged"]
    assert len(result["histories"]) == 2
    assert all(h["completed"] and h["restarts"] == 1 for h in result["histories"])
    for path in (tmp_path / "contracts").glob("*/turns.jsonl"):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            assert row["turn"]["tutor_message"]["trace"]["prompt_version"] == f"question-specific-profile-grounded-{row['version']}"


def test_genuine_switch_packet_has_attempt_then_distinct_new_concept():
    rows = packet.dataset(concept_switch=True)
    assert len(rows) == 6
    assert sum(len(row["situation"]["prompts"]) for row in rows) == 18
    for row in rows:
        prompts = row["situation"]["prompts"]
        assert "amber" in prompts[0] and "My attempt:" in prompts[1]
        assert "cobalt" not in prompts[1]
        assert "New topic:" in prompts[2] and "cobalt" in prompts[2]
        assert row["situation"]["profile"] == "socratic"


@pytest.mark.asyncio
async def test_switch_supplement_counts_three_actual_turns_and_tight_bounds(tmp_path, monkeypatch):
    monkeypatch.setattr(packet, "SEEDS", (7401,))
    result = await packet.run(tmp_path / "switch", transport_factory=FakeClient, concept_switch=True)
    assert all(h["completed"] and h["turns"] == 3 for h in result["histories"])
    manifest = json.loads((tmp_path / "switch" / "manifest.json").read_text())
    assert manifest["maximum_total_calls"] == 40
    assert manifest["maximum_total_reserved_usd"] == .8
    assert manifest["supplement"] == "genuine-concept-switch"


@pytest.mark.asyncio
async def test_restart_count_tracks_actual_branch_in_mixed_length_packet(tmp_path, monkeypatch):
    monkeypatch.setattr(packet, "SEEDS", (7401,))
    monkeypatch.setattr(packet, "REFERENT_SITUATIONS", packet.REFERENT_SITUATIONS[:2])
    result = await packet.run(tmp_path / "referents", transport_factory=FakeClient, named_referents=True)
    assert len(result["histories"]) == 4
    for history in result["histories"]:
        assert history["completed"]
        assert history["restarts"] == (1 if history["turns"] == 2 else 0)
    assert sum(h["restarts"] for h in result["histories"]) == 2
