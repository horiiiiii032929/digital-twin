from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.prepare_academic_factual_qa_panel_review_v2 import (
    FORBIDDEN_PACKET_KEYS,
    PACKET_PATH,
    build_packet,
    validate_packet,
)
from scripts.run_academic_factual_qa_panel_review_v2 import (
    PanelReviewError,
    REVIEWER_IDS,
    aggregate_panel,
    append_vote,
    build_researcher_packet,
    build_simulated_ledger,
    initialize_ledger,
    preflight,
    simulate,
    validate_resume,
    validate_vote,
    write_ledger_atomic,
)


def _valid_vote(item_id: str) -> dict:
    return {
        "review_item_id": item_id,
        "case_semantically_valid": True,
        "expected_action": "answer",
        "question_answerable_from_supplied_sources": True,
        "atomic_claim_support": "fully-supported",
        "citation_support": "complete-valid",
        "boundary_reason": None,
        "ambiguity_detected": False,
        "evidence_ids": ["evidence-1"],
        "defect_types": [],
        "concise_rationale": "The visible source supports the candidate record.",
    }


def test_blinded_packet_is_reproducible_and_gold_free() -> None:
    packet = build_packet()
    validate_packet(packet)
    committed = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    assert packet == committed
    assert packet["calibration_item_count"] == 40
    assert packet["confirmation_item_count"] == 200
    serialized = json.dumps(packet, sort_keys=True)
    assert all(f'"{key}"' not in serialized for key in FORBIDDEN_PACKET_KEYS)
    assert [row["item_kind"] for row in packet["items"][:40]] == ["calibration"] * 40
    assert [row["item_kind"] for row in packet["items"][40:]] == ["confirmation"] * 200


def test_vote_parser_fails_closed_on_schema_identity_and_value_drift() -> None:
    vote = _valid_vote("review-1")
    assert validate_vote(vote, expected_item_id="review-1") == vote
    malformed = dict(vote)
    malformed.pop("citation_support")
    with pytest.raises(PanelReviewError, match="vote keys drifted"):
        validate_vote(malformed, expected_item_id="review-1")
    invalid_action = dict(vote, expected_action="release")
    with pytest.raises(PanelReviewError, match="invalid expected action"):
        validate_vote(invalid_action, expected_item_id="review-1")
    with pytest.raises(PanelReviewError, match="identity drifted"):
        validate_vote(vote, expected_item_id="review-2")


def test_atomic_ledger_is_exclusive_and_resume_bound(tmp_path: Path) -> None:
    ledger = initialize_ledger(
        packet_sha256="packet",
        instrument_sha256="instrument",
        reviewer_bindings_sha256="bindings",
        pricing_sha256="pricing",
    )
    vote = _valid_vote("review-1")
    append_vote(
        ledger,
        reviewer_id=REVIEWER_IDS[0],
        vote=vote,
        provider_call=False,
    )
    path = tmp_path / "ledger.json"
    write_ledger_atomic(path, ledger, exclusive=True)
    assert json.loads(path.read_text(encoding="utf-8")) == ledger
    with pytest.raises(PanelReviewError, match="already exists"):
        write_ledger_atomic(path, ledger, exclusive=True)
    validate_resume(
        ledger,
        packet_sha256="packet",
        instrument_sha256="instrument",
        reviewer_bindings_sha256="bindings",
        pricing_sha256="pricing",
    )
    with pytest.raises(PanelReviewError, match="pricing_sha256"):
        validate_resume(
            ledger,
            packet_sha256="packet",
            instrument_sha256="instrument",
            reviewer_bindings_sha256="bindings",
            pricing_sha256="changed",
        )


def test_ledger_preserves_accounting_and_rejects_duplicate_votes() -> None:
    ledger = initialize_ledger(
        packet_sha256="packet",
        instrument_sha256="instrument",
        reviewer_bindings_sha256="bindings",
        pricing_sha256="pricing",
    )
    vote = _valid_vote("review-1")
    append_vote(
        ledger,
        reviewer_id=REVIEWER_IDS[1],
        vote=vote,
        provider_call=True,
        input_tokens=120,
        output_tokens=30,
        reported_cost_usd=0.0015,
    )
    assert ledger["provider_calls"] == 1
    assert ledger["input_tokens"] == 120
    assert ledger["output_tokens"] == 30
    assert ledger["reported_cost_usd"] == 0.0015
    with pytest.raises(PanelReviewError, match="duplicate reviewer vote"):
        append_vote(
            ledger,
            reviewer_id=REVIEWER_IDS[1],
            vote=vote,
            provider_call=True,
        )


def test_clean_simulation_passes_calibration_and_bounds_audit() -> None:
    result = simulate("pass")
    assert result["status"] == "ready-researcher-audit"
    assert result["passing_reviewer_count"] == 3
    assert result["unanimous_case_count"] == 200
    assert result["disagreement_case_count"] == 0
    assert result["action_krippendorff_alpha"] == 1.0
    assert result["researcher_packet_case_count"] == 20
    assert result["researcher_packet_bounded"] is True
    assert result["provider_calls"] == 0
    assert result["automatic_product_promotion"] is False


def test_researcher_packet_preserves_votes_and_pending_dispositions() -> None:
    packet, ledger = build_simulated_ledger("pass")
    aggregate = aggregate_panel(ledger=ledger, packet=packet)
    researcher = build_researcher_packet(
        aggregate=aggregate,
        packet=packet,
        ledger=ledger,
    )
    assert researcher["case_count"] == 20
    assert researcher["maximum_case_count"] == 60
    assert researcher["researcher_is_independent_annotator"] is False
    assert all(len(row["reviewer_votes"]) == 3 for row in researcher["cases"])
    assert all(
        row["researcher_disposition"]["status"] == "pending"
        for row in researcher["cases"]
    )
    overflow_packet, overflow_ledger = build_simulated_ledger("disagreement-overflow")
    overflow = aggregate_panel(ledger=overflow_ledger, packet=overflow_packet)
    with pytest.raises(PanelReviewError, match="calibrated bounded panel"):
        build_researcher_packet(
            aggregate=overflow,
            packet=overflow_packet,
            ledger=overflow_ledger,
        )


def test_calibration_failure_removes_reviewer_vote_authority() -> None:
    result = simulate("calibration-failure")
    assert result["status"] == "panel-calibration-failed"
    assert result["passing_reviewer_count"] == 2
    assert result["calibration"][REVIEWER_IDS[0]]["passed"] is False


def test_more_than_forty_disagreements_fails_before_unbounded_audit() -> None:
    result = simulate("disagreement-overflow")
    assert result["status"] == "panel-disagreement-overflow"
    assert result["disagreement_case_count"] == 41
    assert result["researcher_packet_case_count"] == 61
    assert result["researcher_packet_bounded"] is False


def test_malformed_output_produces_invalid_execution() -> None:
    result = simulate("malformed")
    assert result["status"] == "invalid-execution"
    assert result["reason"] == "malformed-reviewer-output"
    assert result["malformed_response_count"] == 1


def test_preflight_reports_invalid_attempt_authority_revoked() -> None:
    result = preflight()
    assert result["status"] == "blocked-confirmation-not-authorized"
    assert set(result["blockers"]) == {
        "codex-review-not-authorized",
        "provider-review-not-authorized",
        "paid-execution-not-authorized",
        "confirmation-execution-not-authorized",
    }
    assert result["planned_review_items_per_reviewer"] == 240
    assert result["planned_provider_review_items"] == 480
    assert result["provider_calls"] == 0
