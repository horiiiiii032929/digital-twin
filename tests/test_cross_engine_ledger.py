from __future__ import annotations

from pathlib import Path

import pytest

from src.digital_twin.evaluation import (
    CROSS_ENGINE_STAGES,
    CrossEngineLedgerError,
    CrossEngineProgramLedgerV1,
)


def _ledger(path: Path, *, resume: bool = False, budget: float = 1.0):
    return CrossEngineProgramLedgerV1(
        path,
        program_id="program-010",
        binding={"instrument": "hash", "models": ["e0", "e1"]},
        maximum_cost_usd=budget,
        resume=resume,
    )


def test_ledger_is_exclusive_ordered_and_resume_bound(tmp_path: Path) -> None:
    path = tmp_path / "ledger.sqlite3"
    ledger = _ledger(path)
    with pytest.raises(CrossEngineLedgerError, match="order"):
        ledger.begin_stage(CROSS_ENGINE_STAGES[1])
    ledger.begin_stage(CROSS_ENGINE_STAGES[0])
    ledger.record_case(
        stage_id=CROSS_ENGINE_STAGES[0],
        engine_id="e0",
        condition_id="t0",
        case_id="case-1",
        response={"action": "answer"},
        score={"pass": True},
        cost_usd=0,
    )
    ledger.complete_stage(
        CROSS_ENGINE_STAGES[0], result={"pass": True}, decision="passed"
    )
    ledger.close()

    resumed = _ledger(path, resume=True)
    assert resumed.snapshot()["case_count"] == 1
    resumed.begin_stage(CROSS_ENGINE_STAGES[1])
    resumed.close()


def test_ledger_rejects_duplicate_case_and_budget_overshoot(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path / "ledger.sqlite3", budget=0.1)
    stage = CROSS_ENGINE_STAGES[0]
    ledger.begin_stage(stage)
    arguments = {
        "stage_id": stage,
        "engine_id": "e1",
        "condition_id": "t1",
        "case_id": "case-1",
        "response": {"action": "answer"},
        "score": {"pass": True},
        "cost_usd": 0.05,
    }
    ledger.record_case(**arguments)
    with pytest.raises(Exception):
        ledger.record_case(**arguments)
    with pytest.raises(CrossEngineLedgerError, match="cost stop"):
        ledger.record_case(**{**arguments, "case_id": "case-2", "cost_usd": 0.06})
    ledger.close()


def test_valid_quality_failure_is_terminal_and_preserved(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path / "ledger.sqlite3")
    stage = CROSS_ENGINE_STAGES[0]
    ledger.begin_stage(stage)
    ledger.complete_stage(
        stage,
        result={"failed_gate": "grounding"},
        decision="quality-failed",
    )

    assert ledger.snapshot()["program_status"] == "quality-failed"
    with pytest.raises(CrossEngineLedgerError, match="terminal"):
        ledger.begin_stage(CROSS_ENGINE_STAGES[1])
    ledger.close()
