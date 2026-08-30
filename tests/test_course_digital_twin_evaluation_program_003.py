from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts import course_digital_twin_evaluation_live_stages as live_stages
from scripts import run_course_digital_twin_evaluation_program as runner
from src.digital_twin.evaluation.finite_program import load_program_manifest
from src.digital_twin.evaluation.finite_program_runner import StageExecutionContext
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "course_digital_twin_evaluation_program_003.json"
)


def test_api_first_successor_is_one_authorized_finite_program() -> None:
    manifest = load_program_manifest(INSTRUMENT)

    assert manifest.program_id == "course-digital-twin-evaluation-program-003"
    assert manifest.status == "frozen-authorized"
    assert manifest.automatic_stage_progression is True
    assert manifest.provider_execution_authorized is True
    assert manifest.paid_execution_authorized is True
    assert manifest.total_budget_usd == 50
    assert manifest.retrieval_embedding is not None
    assert manifest.retrieval_embedding.model == "text-embedding-3-small"
    assert (
        manifest.retrieval_embedding.artifact_instrument_id
        == "course-digital-twin-evaluation-program-002"
    )
    assert manifest.retrieval_embedding.artifact_root_path == (
        "reports/generated/course-digital-twin-evaluation-program-002/"
        "stages/_shared-api-retrieval-index-v2"
    )
    for operation in (
        "dataset_generation",
        "external_model_evaluation",
        "method_evaluation_execution",
    ):
        require_bounded_pilot_operation_allowed(manifest.program_id, operation)


def test_api_first_successor_validates_without_local_qwen() -> None:
    result = runner.validate(INSTRUMENT)

    assert result["program_id"] == "course-digital-twin-evaluation-program-003"
    assert result["status"] == "passed-build-only"
    assert result["final_case_target"] == 10_000


def test_adapter_smoke_persists_then_scores_without_network() -> None:
    result = runner.smoke(INSTRUMENT)

    assert result == {
        "program_id": "course-digital-twin-evaluation-program-003",
        "status": "passed-network-free-smoke",
        "response_count": 1,
        "scored_case_count": 1,
        "provider_calls": 0,
        "network_calls": 0,
        "gold_loaded_after_response_persistence": True,
    }


def test_failure_accounting_includes_embedding_batches(tmp_path: Path) -> None:
    manifest = load_program_manifest(INSTRUMENT)
    stage = manifest.stages[0]
    output_root = tmp_path / "stage"
    output_root.mkdir()
    ledger = sqlite3.connect(output_root / "embedding.sqlite3")
    ledger.execute("CREATE TABLE batches (cost_usd REAL NOT NULL)")
    ledger.executemany("INSERT INTO batches VALUES (?)", [(0.01,), (0.02,)])
    ledger.commit()
    ledger.close()
    context = StageExecutionContext(
        root=ROOT,
        manifest=manifest,
        output_root=output_root,
        stage=stage.name,
        resume=False,
        remaining_stage_budget_usd=stage.budget_usd,
        remaining_program_budget_usd=manifest.total_budget_usd,
        recorded_stage_provider_calls=0,
        recorded_stage_cost_usd=0,
    )

    assert live_stages._observed_usage(context) == (2, 0.03)
