from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.academic_factual_qa_pilot_data import (
    build_development_dataset,
    canonical_sha256,
    validate_development_dataset,
)
from scripts.run_academic_factual_qa_end_to_end_pilot import (
    DEFAULT_INSTRUMENT,
    ProductCaseInput,
    preflight,
    simulate,
    validate_build,
    validate_instrument,
)
from src.digital_twin.repository_freeze import FREEZE_ID


ROOT = Path(__file__).resolve().parents[1]


def test_development_dataset_is_stable_diverse_and_explicitly_not_gold() -> None:
    first = build_development_dataset()
    second = build_development_dataset()

    assert first == second
    assert first["content_sha256"] == (
        "09b684cc2efaad32936fdd6d6222c539501c4b1b38ab1f5228a9949de0cbf18b"
    )
    payload = {key: value for key, value in first.items() if key != "content_sha256"}
    assert canonical_sha256(payload) == first["content_sha256"]
    result = validate_development_dataset(payload)
    assert result == {
        "dataset_id": "academic-factual-qa-end-to-end-pilot-001-development",
        "status": "passed",
        "source_count": 32,
        "case_count": 160,
        "course_count": 8,
        "cluster_count": 80,
        "largest_cluster": 3,
        "exact_normalized_duplicate_count": 0,
        "action_counts": {
            "answer": 80,
            "clarify-request": 16,
            "no-evidence": 40,
            "redirect-graded-work": 24,
        },
        "slice_counts": {
            "academic-integrity": 24,
            "ambiguous": 16,
            "cross-course": 16,
            "direct": 32,
            "multi-source": 16,
            "no-evidence": 24,
            "paraphrase": 32,
        },
        "independent_gold": False,
        "private_data": False,
    }


def test_system_input_schema_rejects_every_gold_field() -> None:
    valid = {
        "case_id": "case-1",
        "client_request_id": "request-1",
        "course_id": "course-1",
        "question": "What does the approved source say?",
    }
    ProductCaseInput.model_validate(valid)

    for gold_field in (
        "expected_action",
        "expected_claims",
        "required_source_ids",
        "rationale",
        "slice",
    ):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ProductCaseInput.model_validate({**valid, gold_field: "forbidden"})


def test_instrument_is_build_only_and_preflight_is_blocked() -> None:
    instrument = validate_instrument(DEFAULT_INSTRUMENT)
    build = validate_build(instrument)
    readiness = preflight(instrument)

    assert build["status"] == "validated-build-only"
    assert build["dataset"]["case_count"] == 160
    assert build["future_candidate_status"] == (
        "not-product-integrated-not-executable"
    )
    assert readiness["status"] == "blocked-not-authorized"
    assert readiness["provider_calls"] == 0
    assert readiness["independent_gold_opened"] is False


def test_network_free_simulation_exercises_real_t0_service_without_selection() -> None:
    result = asyncio.run(simulate(validate_instrument(DEFAULT_INSTRUMENT)))
    by_condition = {
        summary["condition_id"]: summary
        for summary in result["condition_summaries"]
    }

    assert result["status"] == "passed-network-free-harness-simulation"
    assert result["case_count"] == 160
    assert len(result["case_results"]) == 320
    assert result["gold_field_count_in_system_input"] == 0
    assert result["provider_calls"] == result["input_tokens"] == 0
    assert result["output_tokens"] == result["paid_cost_usd"] == 0
    assert result["private_data_read"] is False
    assert result["independent_gold_claimed"] is False
    assert result["method_selected"] is False

    fail_closed = by_condition["T0-FAIL-CLOSED-CONTROL"]
    any_hit = by_condition["T0-ANY-HIT-CONTROL"]
    assert fail_closed["unsupported_release_rate"]["estimate"] == 0
    assert fail_closed["supported_answer_retention"]["estimate"] == 0
    assert any_hit["supported_answer_retention"]["estimate"] == 1
    assert any_hit["unsupported_release_rate"]["estimate"] > 0
    assert any_hit["failure_counts"]["incomplete_expected_claims"] == 16
    assert any_hit["failure_counts"]["incomplete_citations"] == 16
    assert all(
        summary["persistence_consistency_rate"] == 1
        and summary["provider_calls"] == 0
        and summary["method_selected"] is False
        for summary in by_condition.values()
    )


def test_development_execution_fails_before_evaluation() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_academic_factual_qa_end_to_end_pilot",
            "--execute-development",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert FREEZE_ID in result.stdout + result.stderr
