from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.validate_academic_factual_qa_confirmation_v2 import (
    DEFAULT_INSTRUMENT,
    LlmPanelProtocolError,
    preflight,
    validate_instrument,
)


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "instrument.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_llm_panel_protocol_is_frozen_but_execution_is_blocked() -> None:
    result = preflight(validate_instrument())

    assert result == {
        "instrument_id": "academic-factual-qa-confirmation-002",
        "status": "blocked-build-only",
        "blockers": [
            "reviewer-bindings-not-fresh",
            "product-revision-and-profile-not-frozen",
            "reviewer-bindings-not-frozen",
            "calibration-execution-authorized-false",
            "codex-review-authorized-false",
            "provider-review-authorized-false",
            "confirmation-execution-authorized-false",
        ],
        "planned_case_count": 200,
        "planned_cluster_count": 100,
        "planned_reviewer_count": 3,
        "planned_reviewer_judgments": 600,
        "planned_calibration_judgments": 120,
        "maximum_researcher_packet_case_count": 60,
        "provider_calls": 0,
        "private_data_read": False,
        "source_manifest_opened": True,
        "reviewer_outputs_opened": False,
    }


def test_three_distinct_reviewer_families_cover_every_case() -> None:
    panel = validate_instrument()["reviewer_panel_contract"]

    assert [row["model_family"] for row in panel["reviewers"]] == [
        "openai",
        "mistral",
        "deepseek",
    ]
    assert all(row["planned_case_count"] == 200 for row in panel["reviewers"])
    assert panel["all_reviewers_cover_all_cases"] is True


def test_model_votes_cannot_replace_deterministic_truth() -> None:
    instrument = validate_instrument()
    truth = instrument["truth_authority_contract"]
    panel = instrument["reviewer_panel_contract"]
    audit = instrument["consensus_and_researcher_audit"]

    assert truth["llm_may_create_authoritative_truth"] is False
    assert truth["llm_may_mutate_authoritative_truth"] is False
    assert panel["reviewer_votes_are_ground_truth"] is False
    assert audit["majority_vote_is_authoritative"] is False
    assert audit["automatic_semantic_acceptance_requires_unanimity"] is True


def test_researcher_packet_is_bounded_to_sixty_cases() -> None:
    audit = validate_instrument()["consensus_and_researcher_audit"]

    assert audit["maximum_disagreement_cases_before_panel_failure"] == 40
    assert audit["fixed_unanimous_audit_case_count"] == 20
    assert audit["maximum_researcher_packet_case_count"] == 60


def test_historical_human_review_protocol_remains_preserved() -> None:
    instrument = validate_instrument()

    assert instrument["predecessor"]["instrument_id"] == (
        "academic-factual-qa-confirmation-001"
    )
    assert instrument["predecessor"]["disposition"] == (
        "superseded-before-source-opening-or-execution"
    )


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        ("scope", "independent_human_ground_truth_claim", True, "human ground-truth"),
        ("truth_authority_contract", "llm_may_create_authoritative_truth", True, "create truth"),
        ("truth_authority_contract", "model_question_paraphrase_allowed", True, "paraphrasing"),
        ("reviewer_panel_contract", "panel_size", 2, "panel size"),
        ("consensus_and_researcher_audit", "majority_vote_is_authoritative", True, "majority vote"),
        ("execution_safety", "provider_review_authorized", True, "execution authorities"),
    ],
)
def test_protocol_drift_fails_closed(
    tmp_path: Path,
    section: str,
    field: str,
    value: object,
    message: str,
) -> None:
    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated[section][field] = value

    with pytest.raises(LlmPanelProtocolError, match=message):
        validate_instrument(_write(tmp_path, mutated))


def test_reviewer_family_reuse_fails_closed(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["reviewer_panel_contract"]["reviewers"][2]["model_family"] = "mistral"

    with pytest.raises(LlmPanelProtocolError, match="model-family diversity"):
        validate_instrument(_write(tmp_path, mutated))


def test_unfresh_bindings_remain_visible_preflight_blocker() -> None:
    instrument = validate_instrument()

    assert all(
        row["binding_fresh"] is False
        for row in instrument["reviewer_panel_contract"]["reviewers"]
    )
    assert "reviewer-bindings-not-fresh" in preflight(instrument)["blockers"]
