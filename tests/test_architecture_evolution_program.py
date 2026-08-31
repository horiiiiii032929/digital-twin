import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.validate_whole_system_architecture_program import validate_program
from src.digital_twin.evaluation import (
    ArchitectureEvolutionProgramV1,
    ArchitectureEvolutionRunRecordV1,
    OperationalAccountingV1,
    load_evaluation_record,
)


ROOT = Path(__file__).resolve().parents[1]
PROGRAM_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "course_digital_twin_whole_system_architecture_evolution_001.json"
)


def _program_payload() -> dict[str, object]:
    return json.loads(PROGRAM_PATH.read_text(encoding="utf-8"))


def test_whole_system_program_covers_all_planes_and_validates_bindings():
    program, summary = validate_program(PROGRAM_PATH)

    assert len(program.architecture_planes) == 13
    assert [item.round_number for item in program.rounds] == [1, 2, 3]
    assert summary["status"] == "passed"
    assert summary["human_participants_required"] is False
    assert summary["provider_execution_authorized"] is False


def test_program_rejects_reusing_a_development_fold():
    payload = _program_payload()
    payload["rounds"][1]["development_tranche_id"] = payload["rounds"][0][
        "development_tranche_id"
    ]

    with pytest.raises(ValidationError, match="distinct development tranches"):
        ArchitectureEvolutionProgramV1.model_validate(payload)


def test_program_rejects_opening_fresh_confirmation_for_development():
    payload = _program_payload()
    payload["rounds"][2]["development_tranche_id"] = (
        "whole-system-fresh-confirmation-1000"
    )

    with pytest.raises(ValidationError, match="bind development tranches"):
        ArchitectureEvolutionProgramV1.model_validate(payload)


def test_zero_call_accounting_rejects_unreported_provider_activity():
    with pytest.raises(ValidationError, match="zero-call runs"):
        OperationalAccountingV1(
            provider_calls=0,
            input_tokens=1,
            output_tokens=0,
            reported_cost_usd=0,
            malformed_responses=0,
            provider_failures=0,
            p95_latency_ms=0,
        )


def test_passing_run_cannot_select_a_failed_candidate():
    record_path = ROOT / (
        "research/05_evaluation/records/"
        "course-digital-twin-whole-system-architecture-evolution-001-build.json"
    )
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    payload["candidates"][0]["hard_gates"][0]["passed"] = False

    with pytest.raises(ValidationError, match="failed a hard gate"):
        ArchitectureEvolutionRunRecordV1.model_validate(payload)


def test_generic_evaluation_loader_supports_architecture_records():
    record_path = ROOT / (
        "research/05_evaluation/records/"
        "course-digital-twin-whole-system-architecture-evolution-001-build.json"
    )

    record = load_evaluation_record(record_path)

    assert isinstance(record, ArchitectureEvolutionRunRecordV1)
    assert record.operational.provider_calls == 0
    assert record.decision.outcome.value == "go-deeper"
