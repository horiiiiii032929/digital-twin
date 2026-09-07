import json

import pytest

from scripts import run_operational_dialogue_development as packet
from src.digital_twin.generation.question_specific import TASK
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmMalformedResponseError, LlmResponse


class SyntheticQuestionClient:
    async def chat(self, messages, task):
        if task != TASK:
            raise LlmMalformedResponseError(stage="operational-contract", usage=GenerationUsage(approximate_cost_usd=0))
        request = json.loads(messages[-1].content)
        source = request["evidence"][0]
        return LlmResponse(provider_model="gpt-5.6-luna", usage=GenerationUsage(approximate_cost_usd=0),
            content=json.dumps({"boundary": "answerable", "aspects": [{"requirement": "protocol behavior",
                "supported": True, "spans": [{"citation_id": source["citation_id"], "text": source["text"]}]}],
                "teaching_move": "ask", "question_focus": request["question"][:80]}))


def test_matrix_covers_every_cell_and_disclaims_learning():
    design = packet.manifest()
    assert len(design["histories"]) == 24
    assert len({row["persona"] for row in design["histories"]}) == 6
    assert len({row["profile"] for row in design["histories"]}) == 2
    assert len({row["condition"] for row in design["histories"]}) == 2
    assert not design["mastery_or_learning_effect_measured"]
    assert not design["intervention_utility_gap_closed"]


def test_question_and_abstention_are_not_treated_as_explanations():
    assert packet.classify_turn("question") == "elicitation"
    assert packet.classify_turn("no-evidence") == "boundary-response"
    assert packet.classify_turn("answer") == "factual-answer-needs-quality-review"


@pytest.mark.asyncio
async def test_actual_questions_receive_only_one_bounded_synthetic_reply(tmp_path, monkeypatch):
    monkeypatch.setattr(packet, "_draw", lambda *args: 0.0)
    spec = next(row for row in packet.matrix() if row["condition"] == "t1-v2-reactive")
    output = tmp_path / "fresh-operational-contract"
    result = await packet.run_history(output, spec, planner_client=SyntheticQuestionClient(), days=2)
    assert result["decision"] == "contract-operational-history-only"
    assert result["counters"]["restart_count"] == 1
    assert result["counters"]["question_replies"] == 2
    assert result["counters"]["turns"] == 4
    turns = [json.loads(line) for line in (output / "turns.jsonl").read_text().splitlines()]
    assert len(turns) == 4
    assert {row["reason"] for row in turns} == {"scheduled-question", "question-reply"}
    assert all(row["classification"] == "elicitation" for row in turns)
    assert not result["learning_effect_measured"]
    with pytest.raises(FileExistsError):
        await packet.run_history(output, spec, planner_client=SyntheticQuestionClient(), days=2)


def test_operational_dialogue_authorization_is_exact_and_external_only():
    from src.digital_twin.repository_freeze import (
        BOUNDED_PILOT_AUTHORIZATIONS, RepositoryFreezeError, require_bounded_pilot_operation_allowed,
    )
    assert BOUNDED_PILOT_AUTHORIZATIONS[packet.INSTRUMENT_ID] == ("external_model_evaluation",)
    require_bounded_pilot_operation_allowed(packet.INSTRUMENT_ID, "external_model_evaluation")
    with pytest.raises(RepositoryFreezeError):
        require_bounded_pilot_operation_allowed(packet.INSTRUMENT_ID, "heldout_execution")
    with pytest.raises(RepositoryFreezeError):
        require_bounded_pilot_operation_allowed(packet.INSTRUMENT_ID + "-unregistered", "external_model_evaluation")


@pytest.mark.asyncio
async def test_pilot_has_global_ceiling_and_correct_case_attribution(tmp_path):
    result = await packet.run_pilot(tmp_path / "pilot", transport=SyntheticQuestionClient())
    assert result["decision"] == "contract-only"
    assert len(result["histories"]) == 2
    assert result["provider_attempts"] <= 80
    assert not result["release_qualified"]
    ledger = [json.loads(line) for line in (tmp_path / "pilot/provider.jsonl").read_text().splitlines()]
    cases = {row["case"] for row in ledger if row["status"] == "started"}
    assert cases == {row["history"]["id"] for row in result["histories"]}
    assert all(row["decision"] != "failed-operational-history" for row in result["histories"])


@pytest.mark.asyncio
async def test_progression_pilot_retains_all_four_histories_and_topic_reset(tmp_path):
    result = await packet.run_progression_pilot(tmp_path / "progression", transport=SyntheticQuestionClient())
    assert result["decision"] == "contract-only"
    assert result["source_files_unchanged"]
    assert len(result["histories"]) == 4
    assert all(row["completed"] and row["turns"] == 4 and row["restarts"] == 1 for row in result["histories"])
    assert result["provider_attempts"] <= 100
    ledger = [json.loads(line) for line in (tmp_path / "progression/provider.jsonl").read_text().splitlines()]
    assert len({row["case"] for row in ledger if row["status"] == "started"}) == 4
    assert any("never reveal" in step.lower() for step in packet.progression_specs()[-1]["profile"]["help_ladder"])
    for turns in (tmp_path / "progression").glob("*/turns.jsonl"):
        rows = [json.loads(line) for line in turns.read_text().splitlines()]
        assert "different question" in rows[-1]["student"]


@pytest.mark.asyncio
async def test_full_history_records_withdrawal_and_restored_consent(tmp_path):
    spec = next(row for row in packet.matrix() if row["condition"] == "t1-v2-reactive")
    output = tmp_path / "consent-history"
    result = await packet.run_history(output, spec, planner_client=SyntheticQuestionClient(), days=30)
    preferences = [json.loads(line) for line in (output / "consent.jsonl").read_text().splitlines()]
    assert [(row["day"], row["preference"]["enabled"]) for row in preferences] == [(10, False), (20, True)]
    assert result["counters"]["restart_count"] == 1
    assert result["counters"]["consent_changes"] == 2
    assert result["counters"]["consent_violations"] == 0


def test_budget_chain_reports_observed_wrappers_and_unknown_clients():
    from services.llm.budget import BudgetedLlmClient
    inner = BudgetedLlmClient(SyntheticQuestionClient(), max_calls=10, max_cost_usd=1)
    outer = BudgetedLlmClient(inner, max_calls=10, max_cost_usd=1)
    snapshot = packet.budget_chain_snapshot(outer)
    assert snapshot["observable"] and len(snapshot["wrappers"]) == 2
    assert snapshot["any_cost_reporting_failed"] is False
    unknown = packet.budget_chain_snapshot(SyntheticQuestionClient())
    assert not unknown["observable"] and unknown["any_cost_reporting_failed"] is None


@pytest.mark.asyncio
async def test_explicit_compact_operational_configuration_rejects_cap_drift_and_survives_restart(tmp_path, monkeypatch):
    from scripts.run_final_profile_longitudinal import RecordedRunClient
    from tests.test_paired_pedagogy_development import InstructionalContractClient
    spec = next(row for row in packet.matrix() if row["condition"] == "t1-v2-reactive")
    wrong = RecordedRunClient(InstructionalContractClient("v8"), tmp_path / "wrong.jsonl",
        maximum_calls=20, maximum_cost_usd=1, network_mode="injected-contract", reservation_usd=.025)
    with pytest.raises(ValueError, match="matching recorded model and output cap"):
        await packet.run_history(tmp_path / "rejected", spec, planner_client=wrong, days=2, candidate="v8")
    assert not (tmp_path / "rejected").exists()
    client = RecordedRunClient(InstructionalContractClient("v8"), tmp_path / "calls.jsonl",
        maximum_calls=20, maximum_cost_usd=1, network_mode="injected-contract", reservation_usd=.025, max_output_tokens=3000)
    monkeypatch.setattr(packet, "_draw", lambda *args: 0.0)
    result = await packet.run_history(tmp_path / "accepted", spec, planner_client=client, days=2, candidate="v8")
    assert result["candidate_configuration"]["implementation_id"] == "question-specific-profile-grounded-v8"
    assert result["counters"]["restart_count"] == 1
    assert result["counters"]["turns"] == 2
    assert any(row["task"] == "question_specific_compact_instruction" for row in client.records)
    config = json.loads((tmp_path / "accepted/configuration.jsonl").read_text())
    assert config["candidate"] == "question-specific-profile-grounded-v8"
