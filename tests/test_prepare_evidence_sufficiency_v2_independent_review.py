from __future__ import annotations

import copy
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from scripts.prepare_evidence_sufficiency_v2_independent_review import (
    DEFECT_CLASSES,
    IndependentReviewError,
    _canonical_sha256,
    build_review_packet,
    load_instrument,
    main,
    preflight,
    simulated_judgments,
    validate_judgments,
    validate_review_packet,
)
from src.digital_twin.repository_freeze import RepositoryFreezeError


@pytest.fixture(scope="module")
def instrument() -> dict:
    return load_instrument()


@pytest.fixture(scope="module")
def packet(instrument: dict) -> dict:
    return build_review_packet(instrument)


def _rehash(packet: dict) -> None:
    core = {key: value for key, value in packet.items() if key != "content_sha256"}
    packet["content_sha256"] = _canonical_sha256(core)


def test_packet_is_exactly_bound_batched_and_byte_stable(
    packet: dict,
    instrument: dict,
) -> None:
    repeated = build_review_packet(instrument)
    summary = validate_review_packet(packet, instrument)
    review_items = [
        item for batch in packet["review_batches"] for item in batch["items"]
    ]

    assert packet["content_sha256"] == repeated["content_sha256"]
    assert packet["content_sha256"] == instrument["review_packet"][
        "expected_content_sha256"
    ]
    assert len(packet["source_catalog"]) == 40
    assert len(packet["review_batches"]) == 12
    assert all(len(batch["items"]) == 10 for batch in packet["review_batches"])
    assert len(review_items) == len({item["item_id"] for item in review_items}) == 120
    assert summary["status"] == "validated-build-only"
    assert summary["provider_or_model_calls"] == 0
    assert summary["private_data_read"] is False
    assert summary["candidate_evaluation_opened"] is False


def test_reviewer_items_exclude_internal_dataset_and_answer_key_fields(
    packet: dict,
) -> None:
    reviewer_items = packet["sensitivity_items"] + [
        item for batch in packet["review_batches"] for item in batch["items"]
    ]

    for item in reviewer_items:
        assert "slice" not in item
        assert "review_status" not in item
        assert "expected_verdict" not in item
        assert "defect_class" not in item


def test_sensitivity_packet_has_six_clean_and_six_distinct_defects(
    packet: dict,
) -> None:
    scoring_key = packet["sensitivity_scoring_key"]
    verdict_counts = Counter(value["expected_verdict"] for value in scoring_key.values())
    defect_classes = {
        value["defect_class"]
        for value in scoring_key.values()
        if value["expected_verdict"] == "revise"
    }

    assert verdict_counts == Counter({"approve": 6, "revise": 6})
    assert defect_classes == DEFECT_CLASSES


def test_every_sensitivity_defect_changes_its_base_proposal(packet: dict) -> None:
    review_items = {
        item["item_id"]: item
        for batch in packet["review_batches"]
        for item in batch["items"]
    }

    for item in packet["sensitivity_items"]:
        key = packet["sensitivity_scoring_key"][item["item_id"]]
        if key["expected_verdict"] == "approve":
            continue
        base = review_items[item["base_case_id"]]
        compared = copy.deepcopy(item)
        compared.pop("item_id")
        compared.pop("base_case_id")
        assert compared != base


@pytest.mark.parametrize("mutation", ["review-item", "source", "answer-leak"])
def test_packet_validator_rejects_semantic_drift(
    packet: dict,
    instrument: dict,
    mutation: str,
) -> None:
    changed = copy.deepcopy(packet)
    if mutation == "review-item":
        changed["review_batches"][0]["items"][0]["question"] = "Changed question"
        pattern = "authoritative draft truth"
    elif mutation == "source":
        changed["source_catalog"][0]["content"] = "Changed source"
        pattern = "source catalog"
    else:
        changed["sensitivity_items"][0]["expected_verdict"] = "approve"
        pattern = "answer leaked"
    _rehash(changed)
    changed_instrument = copy.deepcopy(instrument)
    changed_instrument["review_packet"]["expected_content_sha256"] = changed[
        "content_sha256"
    ]

    with pytest.raises(IndependentReviewError, match=pattern):
        validate_review_packet(changed, changed_instrument)


def test_network_free_simulation_covers_every_item_without_freezing(packet: dict) -> None:
    judgments = simulated_judgments(packet)
    result = validate_judgments(packet, judgments, simulation=True)

    assert len(judgments) == 132
    assert result["status"] == "simulation-passed-not-evidence"
    assert all(result["gates"].values())
    assert result["clean_specificity"] == 1.0
    assert result["defect_detection"] == 1.0
    assert result["review_case_coverage"] == 1.0
    assert result["priority_case_ids"] == []
    assert result["priority_packet_truncated"] is False
    assert result["provider_or_model_calls"] == 0
    assert result["freeze_eligible"] is False


@pytest.mark.parametrize("mutation", ["duplicate", "invalid-dimension", "missing"])
def test_judgment_validator_fails_closed(packet: dict, mutation: str) -> None:
    judgments = simulated_judgments(packet)
    if mutation == "duplicate":
        judgments.append(copy.deepcopy(judgments[0]))
    elif mutation == "invalid-dimension":
        judgments[0]["failed_dimensions"] = ["not-a-review-dimension"]
    else:
        judgments.pop()

    result = validate_judgments(packet, judgments, simulation=True)

    assert result["gates"]["response_contract_valid"] is False
    assert result["freeze_eligible"] is False


def test_preflight_reports_exact_build_only_blockers(instrument: dict) -> None:
    unauthorized = copy.deepcopy(instrument)
    unauthorized["status"] = "reviewer-bound-provider-unauthorized"
    unauthorized["execution_safety"]["provider_execution_authorized"] = False
    unauthorized["decision_rule"]["authorize_provider_execution"] = False
    verified_at = datetime.fromisoformat(
        unauthorized["execution_safety"]["reviewer_verified_at"]
    )
    result = preflight(unauthorized, now=verified_at + timedelta(hours=1))

    assert result == {
        "instrument_id": "evidence-sufficiency-v2-independent-review-002",
        "status": "blocked-not-authorized",
        "blockers": ["provider-review-not-authorized"],
        "provider_or_model_calls": 0,
        "private_data_read": False,
        "candidate_evaluation_opened": False,
    }


def test_active_instrument_preflight_is_authorized(instrument: dict) -> None:
    verified_at = datetime.fromisoformat(
        instrument["execution_safety"]["reviewer_verified_at"]
    )
    result = preflight(instrument, now=verified_at + timedelta(hours=1))

    assert result == {
        "instrument_id": "evidence-sufficiency-v2-independent-review-002",
        "status": "ready",
        "blockers": [],
        "provider_or_model_calls": 0,
        "private_data_read": False,
        "candidate_evaluation_opened": False,
    }


def test_historical_unbound_instrument_preserves_all_four_blockers() -> None:
    historical_path = (
        Path(__file__).resolve().parents[1]
        / "research/05_evaluation/instruments/evidence_sufficiency_v2_independent_review_001.json"
    )
    result = preflight(load_instrument(historical_path))

    assert result["blockers"] == [
        "independent-reviewer-not-bound",
        "reviewer-metadata-not-fresh",
        "review-cost-ceiling-not-frozen",
        "provider-review-not-authorized",
    ]


def test_bound_reviewer_metadata_expires_after_24_hours(instrument: dict) -> None:
    verified_at = datetime.fromisoformat(
        instrument["execution_safety"]["reviewer_verified_at"]
    )
    result = preflight(instrument, now=verified_at + timedelta(hours=24, seconds=1))

    assert result["blockers"] == ["reviewer-metadata-not-fresh"]


def test_write_mode_is_blocked_by_repository_execution_freeze(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    output = tmp_path / "must-not-exist.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepare_evidence_sufficiency_v2_independent_review",
            "--write",
            "--output",
            str(output),
        ],
    )

    with pytest.raises(RepositoryFreezeError, match="dataset_generation"):
        main()
    assert not output.exists()
