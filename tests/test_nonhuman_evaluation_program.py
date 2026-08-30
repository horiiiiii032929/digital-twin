from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.repository_freeze import (
    RepositoryFreezeError,
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research/05_evaluation/instruments/course_digital_twin_nonhuman_evaluation_program_002.json"
PROGRAM_ID = "course-digital-twin-nonhuman-evaluation-program-002"


def test_nonhuman_program_has_one_authority_and_finite_budget() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    expected = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )

    assert payload["content_sha256"] == expected
    assert payload["status"] == "frozen-authorized"
    assert payload["provider_execution_authorized"] is True
    assert payload["paid_execution_authorized"] is True
    assert payload["stage_by_stage_user_approval_required"] is False
    assert payload["global_budget_usd"] == 50.0
    assert sum(stage["budget_usd"] for stage in payload["stages"]) == 50.0
    assert [stage["order"] for stage in payload["stages"]] == list(range(1, 10))
    assert payload["human_participant_execution_authorized"] is False


def test_completed_program_authority_is_revoked() -> None:
    for operation in (
        "dataset_generation",
        "external_model_evaluation",
        "heldout_execution",
        "method_evaluation_execution",
    ):
        with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
            require_bounded_pilot_operation_allowed(PROGRAM_ID, operation)
