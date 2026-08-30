from __future__ import annotations

from pathlib import Path

import pytest

from scripts.course_digital_twin_program_factual import _advisory_case_ids
from scripts.course_digital_twin_program_release import _prioritized_concerns
from src.digital_twin.evaluation.finite_program import (
    PROGRAM_ID,
    ProgramError,
    ProgramLedgerV1,
    ProgramStageName,
    ProgramStageStatus,
    load_program_manifest,
)
from src.digital_twin.evaluation.finite_program_runner import (
    FiniteProgramRunner,
    build_stage_result,
)
from src.digital_twin.repository_freeze import (
    RepositoryFreezeError,
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "course_digital_twin_evaluation_program_001.json"
)


def _manifest():
    return load_program_manifest(INSTRUMENT)


def _executors(manifest, *, failing_stage=None, invalid_twice=False):
    attempts: dict[ProgramStageName, int] = {}

    def executor(context):
        attempts[context.stage] = attempts.get(context.stage, 0) + 1
        if invalid_twice and context.stage == ProgramStageName.RETRIEVAL_DECISION:
            status = ProgramStageStatus.INVALID_EXECUTION
        elif context.stage == failing_stage:
            status = ProgramStageStatus.COMPLETED_REFINE
        elif context.stage in {
            ProgramStageName.TRUE_VISUAL,
            ProgramStageName.SYNTHETIC_PROFILE,
        }:
            status = ProgramStageStatus.COMPLETED_GO_DEEPER
        else:
            status = ProgramStageStatus.COMPLETED_KEEP
        return build_stage_result(
            manifest=manifest,
            stage=context.stage,
            status=status,
            provider_calls=0,
            cost_usd=0,
        )

    return {row.name: executor for row in manifest.stages}, attempts


def test_manifest_is_finite_hash_bound_and_authorized() -> None:
    manifest = _manifest()

    assert manifest.program_id == PROGRAM_ID
    assert manifest.total_budget_usd == 50
    assert sum(row.budget_usd for row in manifest.stages) == 50
    assert sum(row.projected_p99_cost_usd for row in manifest.stages) == pytest.approx(
        44.6
    )
    assert all(
        row.projected_p99_cost_usd <= row.budget_usd for row in manifest.stages
    )
    assert manifest.stage(ProgramStageName.RELEASE_REGRESSION).budget_usd == 0
    assert manifest.stage(ProgramStageName.REPORTING).budget_usd == 2
    assert manifest.provider_execution_authorized is True
    assert manifest.paid_execution_authorized is True
    for operation in (
        "dataset_generation",
        "external_model_evaluation",
        "local_model_evaluation",
        "method_evaluation_execution",
    ):
        require_bounded_pilot_operation_allowed(PROGRAM_ID, operation)


def test_full_pass_advances_once_and_completes(tmp_path: Path) -> None:
    manifest = _manifest()
    ledger = ProgramLedgerV1(
        tmp_path / "program.sqlite3",
        manifest=manifest,
        code_revision="a" * 40,
        resume=False,
    )
    executors, attempts = _executors(manifest)
    runner = FiniteProgramRunner(
        root=ROOT,
        output_root=tmp_path / "stages",
        manifest=manifest,
        ledger=ledger,
        executors=executors,
    )

    snapshot = runner.run(resume=False)

    assert snapshot["metadata"]["status"] == "completed"
    assert all(count == 1 for count in attempts.values())
    assert len(attempts) == 9
    ledger.close()


def test_factual_failure_stops_scaling_but_keeps_independent_tracks(
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    ledger = ProgramLedgerV1(
        tmp_path / "program.sqlite3",
        manifest=manifest,
        code_revision="b" * 40,
        resume=False,
    )
    executors, attempts = _executors(
        manifest, failing_stage=ProgramStageName.RETRIEVAL_DECISION
    )
    snapshot = FiniteProgramRunner(
        root=ROOT,
        output_root=tmp_path / "stages",
        manifest=manifest,
        ledger=ledger,
        executors=executors,
    ).run(resume=False)

    by_name = {row["name"]: row["status"] for row in snapshot["stages"]}
    assert by_name[ProgramStageName.PRODUCT_DEVELOPMENT.value] == (
        ProgramStageStatus.SKIPPED_DEPENDENCY.value
    )
    assert ProgramStageName.TRUE_VISUAL in attempts
    assert ProgramStageName.SYNTHETIC_PROFILE in attempts
    assert ProgramStageName.REPORTING in attempts
    assert ProgramStageName.FINAL_PRODUCT not in attempts
    ledger.close()


def test_second_invalid_execution_terminates_without_loop(tmp_path: Path) -> None:
    manifest = _manifest()
    ledger = ProgramLedgerV1(
        tmp_path / "program.sqlite3",
        manifest=manifest,
        code_revision="c" * 40,
        resume=False,
    )
    executors, attempts = _executors(manifest, invalid_twice=True)
    snapshot = FiniteProgramRunner(
        root=ROOT,
        output_root=tmp_path / "stages",
        manifest=manifest,
        ledger=ledger,
        executors=executors,
    ).run(resume=False)

    assert snapshot["metadata"]["status"] == "terminated"
    assert attempts[ProgramStageName.RETRIEVAL_DECISION] == 2
    ledger.close()


def test_ledger_rejects_resume_drift_and_stage_budget_overshoot(tmp_path: Path) -> None:
    manifest = _manifest()
    path = tmp_path / "program.sqlite3"
    ledger = ProgramLedgerV1(
        path, manifest=manifest, code_revision="d" * 40, resume=False
    )
    ledger.start_stage(ProgramStageName.RETRIEVAL_DECISION)
    with pytest.raises(ProgramError, match="cost ceiling"):
        ledger.record_usage(
            ProgramStageName.RETRIEVAL_DECISION,
            provider_calls=1,
            cost_usd=2.01,
        )
    ledger.close()
    with pytest.raises(ProgramError, match="resume binding drifted"):
        ProgramLedgerV1(
            path, manifest=manifest, code_revision="e" * 40, resume=True
        )


def test_advisory_selection_is_seeded_and_always_contains_failures() -> None:
    scores = [
        {
            "case_id": f"case-{index:03d}",
            "answerable": True,
            "fully_grounded_success": index >= 5,
            "boundary_safe": False,
        }
        for index in range(500)
    ]

    first = _advisory_case_ids(
        {"case_scores": scores},
        final=False,
        paired_case_ids=set(),
    )
    second = _advisory_case_ids(
        {"case_scores": scores},
        final=False,
        paired_case_ids=set(),
    )

    assert first == second
    assert len(first) == 55
    assert {f"case-{index:03d}" for index in range(5)} <= set(first)


def test_critical_review_prioritizes_severe_and_invalid_source_findings() -> None:
    product = {
        "advisory_review": {
            "source_truth_concern_case_ids": ["ordinary", "version", "severe"]
        },
        "candidate": {
            "case_scores": [
                {
                    "case_id": "ordinary",
                    "severe_unsupported_release": False,
                    "source_version_valid": True,
                    "action_correct": False,
                },
                {
                    "case_id": "version",
                    "severe_unsupported_release": False,
                    "source_version_valid": False,
                    "action_correct": True,
                },
                {
                    "case_id": "severe",
                    "severe_unsupported_release": True,
                    "source_version_valid": True,
                    "action_correct": False,
                },
            ]
        },
    }

    assert _prioritized_concerns(product) == ["severe", "version", "ordinary"]
