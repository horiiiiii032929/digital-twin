from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from scripts import course_digital_twin_evaluation_live_stages as live_stages
from scripts import run_course_digital_twin_evaluation_program as runner
from src.digital_twin.evaluation.finite_program import ProgramError, load_program_manifest
from src.digital_twin.evaluation.finite_program_runner import StageExecutionContext
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "course_digital_twin_evaluation_program_004.json"
)


def test_stable_successor_is_terminal_and_authority_is_revoked() -> None:
    manifest = load_program_manifest(INSTRUMENT)

    assert manifest.program_id == "course-digital-twin-evaluation-program-004"
    assert manifest.status == "completed"
    assert manifest.automatic_stage_progression is True
    assert manifest.provider_execution_authorized is False
    assert manifest.paid_execution_authorized is False
    assert manifest.total_budget_usd == 50
    assert manifest.retrieval_embedding is not None
    assert manifest.retrieval_embedding.model == "text-embedding-3-small"
    assert manifest.retrieval_nano_reranking_enabled is False
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
        try:
            require_bounded_pilot_operation_allowed(manifest.program_id, operation)
        except Exception as error:
            assert "not a bounded authorization" in str(error)
        else:
            raise AssertionError("terminal program retained execution authority")


def test_stable_successor_is_reclassified_when_gold_cannot_match_corpus() -> None:
    with pytest.raises(
        ProgramError,
        match="development gold is not exactly matchable by the runtime corpus",
    ):
        runner.validate(INSTRUMENT)


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
