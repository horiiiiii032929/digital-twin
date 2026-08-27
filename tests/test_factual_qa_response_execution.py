from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationResponseV1,
    EvaluationSplit,
    SystemUnderTestManifestV1,
)
from src.digital_twin.evaluation.factual_qa_execution import (
    FactualQaExecutionError,
    ResponseLedgerV1,
    canonical_json_sha256,
    execute_cases,
)


def _cases() -> list[EvaluationCaseV1]:
    return [
        EvaluationCaseV1(
            case_id=f"case-{index}",
            cluster_id=f"cluster-{index}",
            source_family_id=f"family-{index}",
            course_id="course-001",
            question=f"Question {index}?",
            split=EvaluationSplit.DEVELOPMENT,
            slice="direct-factual",
            author_family="fixture",
        )
        for index in range(3)
    ]


def _manifest() -> SystemUnderTestManifestV1:
    return SystemUnderTestManifestV1(
        flow_id="simulated-t0",
        adapter_version="v1",
        code_revision="abcdef0",
        profile_sha256="a" * 64,
        retriever="simulated",
        generator="simulated",
        policy="simulated",
        evidence_gate="simulated",
    )


class _SimulatedInterruption(BaseException):
    pass


class _Adapter:
    flow_id = "simulated-t0"
    adapter_version = "v1"

    def __init__(self, *, interrupt_at: str | None = None) -> None:
        self.interrupt_at = interrupt_at
        self.calls: list[str] = []

    async def evaluate(self, case: EvaluationCaseV1) -> EvaluationResponseV1:
        self.calls.append(case.case_id)
        if case.case_id == self.interrupt_at:
            raise _SimulatedInterruption
        return EvaluationResponseV1(
            case_id=case.case_id,
            flow_id=self.flow_id,
            action=EvaluationAction.ABSTAIN,
            answer="No approved evidence.",
            operational_status="completed",
        )


def _ledger(path: Path, *, resume: bool) -> ResponseLedgerV1:
    return ResponseLedgerV1(
        path,
        cases_sha256=canonical_json_sha256(
            [row.model_dump(mode="json") for row in _cases()]
        ),
        system_manifest_sha256=canonical_json_sha256(
            _manifest().model_dump(mode="json")
        ),
        run_configuration_sha256="b" * 64,
        resume=resume,
    )


@pytest.mark.asyncio
async def test_response_execution_is_atomic_and_complete(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path / "responses.sqlite3", resume=False)
    try:
        snapshot = await execute_cases(
            cases=_cases(), adapter=_Adapter(), manifest=_manifest(), ledger=ledger
        )
        assert snapshot["status"] == "completed"
        assert snapshot["response_count"] == 3
    finally:
        ledger.close()


@pytest.mark.asyncio
async def test_interrupted_execution_resumes_without_duplicate_calls(tmp_path: Path) -> None:
    path = tmp_path / "responses.sqlite3"
    first = _ledger(path, resume=False)
    with pytest.raises(_SimulatedInterruption):
        await execute_cases(
            cases=_cases(),
            adapter=_Adapter(interrupt_at="case-1"),
            manifest=_manifest(),
            ledger=first,
        )
    assert first.snapshot()["response_count"] == 1
    first.close()

    resumed = _ledger(path, resume=True)
    adapter = _Adapter()
    try:
        snapshot = await execute_cases(
            cases=_cases(), adapter=adapter, manifest=_manifest(), ledger=resumed
        )
        assert snapshot["status"] == "completed"
        assert adapter.calls == ["case-1", "case-2"]
    finally:
        resumed.close()


def test_existing_output_and_resume_drift_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "responses.sqlite3"
    ledger = _ledger(path, resume=False)
    ledger.close()
    with pytest.raises(FactualQaExecutionError, match="already exists"):
        _ledger(path, resume=False)
    with pytest.raises(FactualQaExecutionError, match="binding drifted"):
        ResponseLedgerV1(
            path,
            cases_sha256="c" * 64,
            system_manifest_sha256=canonical_json_sha256(
                _manifest().model_dump(mode="json")
            ),
            run_configuration_sha256="b" * 64,
            resume=True,
        )


def test_response_execution_module_has_no_gold_or_scorer_import() -> None:
    source = Path(
        "src/digital_twin/evaluation/factual_qa_execution.py"
    ).read_text(encoding="utf-8")
    assert "EvaluationGoldV1" not in source
    assert "factual_qa_scoring" not in source
