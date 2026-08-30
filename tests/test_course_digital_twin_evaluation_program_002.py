from __future__ import annotations

from pathlib import Path

from scripts import run_course_digital_twin_evaluation_program as runner
from src.digital_twin.evaluation.finite_program import load_program_manifest
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "course_digital_twin_evaluation_program_002.json"
)


def test_api_first_successor_is_one_authorized_finite_program() -> None:
    manifest = load_program_manifest(INSTRUMENT)

    assert manifest.program_id == "course-digital-twin-evaluation-program-002"
    assert manifest.status == "frozen-authorized"
    assert manifest.automatic_stage_progression is True
    assert manifest.provider_execution_authorized is True
    assert manifest.paid_execution_authorized is True
    assert manifest.total_budget_usd == 50
    assert manifest.retrieval_embedding is not None
    assert manifest.retrieval_embedding.model == "text-embedding-3-small"
    for operation in (
        "dataset_generation",
        "external_model_evaluation",
        "method_evaluation_execution",
    ):
        require_bounded_pilot_operation_allowed(manifest.program_id, operation)


def test_api_first_successor_validates_without_local_qwen() -> None:
    result = runner.validate(INSTRUMENT)

    assert result["program_id"] == "course-digital-twin-evaluation-program-002"
    assert result["status"] == "passed-build-only"
    assert result["final_case_target"] == 10_000


def test_adapter_smoke_persists_then_scores_without_network() -> None:
    result = runner.smoke(INSTRUMENT)

    assert result == {
        "program_id": "course-digital-twin-evaluation-program-002",
        "status": "passed-network-free-smoke",
        "response_count": 1,
        "scored_case_count": 1,
        "provider_calls": 0,
        "network_calls": 0,
        "gold_loaded_after_response_persistence": True,
    }
