from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import prepare_academic_factual_qa_open_development_003 as packages
from scripts import run_academic_factual_qa_open_development_checkpoint_003 as checkpoint
from scripts import run_academic_factual_qa_open_product_003 as product
from scripts import run_academic_factual_qa_open_wording_v3 as wording
from scripts import run_academic_factual_qa_openai_reviewer_calibration as calibration
from scripts import score_academic_factual_qa_open_development_003 as scoring
from scripts.run_academic_factual_qa_panel_review_v2 import _ideal_vote, _truth_maps
from src.digital_twin.evaluation.provider_json import DirectProviderJsonTransport


def test_openai_checkpoint_freezes_exact_models_and_zero_retries() -> None:
    result = checkpoint.validate()
    assert result["status"] == "passed-build-only"
    assert result["maximum_calls"] == 660
    assert result["maximum_cost_usd"] == 18.0
    binding = calibration._binding()
    assert set(binding["providers"]) == {"high-volume-generator", "semantic-reviewer"}
    assert binding["providers"]["high-volume-generator"]["provider_model"] == (
        "gpt-5.4-mini-2026-03-17"
    )
    assert binding["providers"]["semantic-reviewer"]["provider_model"] == (
        "gpt-5.4-2026-03-05"
    )
    assert all(
        row["provider"] == "openai"
        and row["maximum_transport_retries"] == 0
        and row["first_party_endpoint"] is True
        for row in binding["providers"].values()
    )


def test_calibration_packet_is_blinded_and_balanced() -> None:
    packet = calibration._packet()
    serialized = json.dumps(packet["items"], sort_keys=True)
    assert len(packet["items"]) == 40
    assert "expected_review" not in serialized
    assert "planted_mutation" not in serialized
    assert "is_clean" not in serialized
    result = calibration.validate()
    assert result["clean_control_count"] == 20
    assert result["corrupted_control_count"] == 20
    assert result["expected_labels_visible_to_provider"] is False
    assert result["prior_provider_votes_imported"] is False


def test_calibration_payload_is_direct_strict_and_non_stored() -> None:
    packet = calibration._packet()
    binding = calibration._binding()["providers"]["semantic-reviewer"]
    transport = DirectProviderJsonTransport(binding)
    system, prompt = calibration._prompt(
        packet["items"][:4], packet["reviewer_instructions"]
    )
    payload = transport._payload(
        system=system,
        prompt=prompt,
        task="test-calibration",
        schema=calibration._vote_schema(4),
    )
    assert payload["model"] == "gpt-5.4-2026-03-05"
    assert payload["store"] is False
    assert payload["text"]["format"]["strict"] is True
    assert "uniqueItems" not in json.dumps(payload)
    assert "openrouter" not in json.dumps(payload).casefold()
    defect_schema = payload["text"]["format"]["schema"]["properties"]["votes"][
        "items"
    ]["properties"]["defect_types"]["items"]
    assert set(defect_schema["enum"]) == {
        "action",
        "ambiguity",
        "boundary",
        "citation",
        "claim",
    }


def test_calibration_parser_rejects_missing_and_reordered_votes() -> None:
    packet = calibration._packet()
    _, truth = _truth_maps()
    items = packet["items"][:4]
    votes = [_ideal_vote(row, truth[row["review_item_id"]]) for row in items]
    assert len(calibration._parse_votes({"votes": votes}, items)) == 4
    malformed = deepcopy(votes)
    malformed[0].pop("citation_support")
    with pytest.raises(Exception):
        calibration._parse_votes({"votes": malformed}, items)
    duplicated = deepcopy(votes)
    duplicated[0]["evidence_ids"] = ["duplicate", "duplicate"]
    with pytest.raises(Exception):
        calibration._parse_votes({"votes": duplicated}, items)
    with pytest.raises(Exception):
        calibration._parse_votes({"votes": list(reversed(votes))}, items)
    contradictory = deepcopy(votes)
    contradictory[0]["question_answerable_from_supplied_sources"] = not contradictory[
        0
    ]["question_answerable_from_supplied_sources"]
    with pytest.raises(Exception, match="answerability and action conflict"):
        calibration._parse_votes({"votes": contradictory}, items)


def test_calibration_simulations_distinguish_quality_from_execution() -> None:
    assert calibration.simulate(scenario="pass")["status"] == "completed-go-deeper"
    assert calibration.simulate(scenario="quality-failure")["status"] == (
        "completed-refine"
    )
    assert calibration.simulate(scenario="malformed")["status"] == (
        "invalid-execution"
    )


def test_wording_and_runtime_packages_preserve_case_pairing() -> None:
    assert wording.validate()["status"] == "passed-build-only"
    source = json.loads(
        (
            packages.DATASET_ROOT
            / "academic_factual_qa_open_10000_v1_development_cases_002.json"
        ).read_text(encoding="utf-8")
    )
    built = packages.build_packages(
        {
            "instrument_id": packages.INSTRUMENT_ID,
            "status": "completed-go-deeper",
            "cases": source["cases"],
        }
    )
    assert built["candidate_cases"]["dataset_id"] == built["candidate_gold"][
        "dataset_id"
    ]
    assert built["candidate_cases"]["split"] == built["candidate_gold"]["split"]
    assert built["control_cases"]["dataset_id"] == built["control_gold"][
        "dataset_id"
    ]
    assert built["control_cases"]["split"] == built["control_gold"]["split"]
    assert built["candidate_cases"]["case_count"] == 500
    assert built["control_cases"]["case_count"] == 100


def test_product_response_runner_has_no_gold_or_scorer_dependency() -> None:
    source = Path(product.__file__).read_text(encoding="utf-8")
    assert "score_academic" not in source
    assert "GOLD" not in source
    result = product.validate()
    assert result["hidden_gold_module_imported"] is False
    assert result["reference_answers_loaded"] is False


def test_scoring_checks_both_ledgers_before_loading_gold(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events: list[str] = []

    monkeypatch.setattr(scoring, "require_bounded_pilot_operation_allowed", lambda *a: None)
    monkeypatch.setattr(
        scoring,
        "_require_complete",
        lambda path, count: events.append(f"complete:{count}"),
    )
    monkeypatch.setattr(scoring, "CANDIDATE_RESULT", tmp_path / "candidate.json")
    monkeypatch.setattr(scoring, "PAIRED_RESULT", tmp_path / "paired.json")

    def fake_score_packages(**_: object) -> dict[str, object]:
        events.append("gold-score")
        return {"status": "completed-keep", "gate_results": {}, "case_scores": []}

    monkeypatch.setattr(scoring.scorer, "score_packages", fake_score_packages)
    monkeypatch.setattr(
        scoring.scorer,
        "paired_comparison",
        lambda *a, **k: {
            "status": "completed-keep",
            "decision": "Keep",
            "failed_gates": [],
            "paired_case_count": 100,
        },
    )
    result = scoring.score()
    assert result["status"] == "completed-keep"
    assert events[:2] == ["complete:500", "complete:100"]
    assert events[2:] == ["gold-score", "gold-score"]


@pytest.mark.parametrize(
    ("scenario", "status", "completed"),
    [
        ("pass", "completed-keep", 5),
        ("calibration-failure", "completed-refine", 1),
        ("wording-failure", "completed-refine", 2),
        ("product-failure", "completed-refine", 5),
    ],
)
def test_combined_simulation_stops_at_the_correct_stage(
    scenario: str, status: str, completed: int
) -> None:
    result = checkpoint.simulate(scenario=scenario)
    assert result["status"] == status
    assert len(result["completed_stages"]) == completed
    assert result["provider_calls"] == 0


def test_combined_preflight_fails_closed_after_authorization_revocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(checkpoint, "_repo_dirty", lambda: False)
    monkeypatch.setattr(checkpoint, "validate", lambda **_: {"status": "passed"})
    result = checkpoint.preflight()
    assert result["status"] == "blocked-not-authorized"
    assert "instrument-paid-execution-authorized-false" in result["blockers"]
    assert "freeze-external_model_evaluation-authorization-missing" in result[
        "blockers"
    ]
    assert result["provider_calls"] == 0


def test_resume_state_is_bound_to_instrument_binding_and_revision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(checkpoint, "STATE_PATH", state_path)
    monkeypatch.setattr(checkpoint, "_repo_revision", lambda: "revision")
    instrument = {"content_sha256": "instrument"}
    binding = {"content_sha256": "binding"}
    state = checkpoint._initial_state(instrument, binding)
    checkpoint._write_state(state, exclusive=True)
    assert checkpoint._resume_state(instrument, binding)["status"] == "running"
    with pytest.raises(checkpoint.DevelopmentCheckpointError, match="binding drifted"):
        checkpoint._resume_state(instrument, {"content_sha256": "changed"})
