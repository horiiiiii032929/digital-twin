import copy
import hashlib

import pytest

from scripts.run_autonomous_tutoring_r1_local_confirmation import (
    DEFAULT_OUTPUT,
    EXECUTED_INSTRUMENT_SHA256,
    PROFILE_PATH,
    LocalR1ConfirmationError,
    _load,
    _validate_published_result,
    build_trajectories,
    validate,
)


def test_local_r1_confirmation_contract_is_finite_and_balanced() -> None:
    trajectories = build_trajectories()

    assert len(trajectories) == 50
    assert len({row["source_namespace"] for row in trajectories}) == 50
    assert {row["category"] for row in trajectories} == {
        "direct-question",
        "repeated-confusion",
        "partial-attempt",
        "misconception",
        "ambiguity",
        "no-evidence",
        "academic-integrity",
        "course-boundary",
        "provider-failure",
        "restart-consistency",
    }
    assert all(len(row["turns"]) == 4 for row in trajectories)


def test_local_r1_confirmation_validates_without_provider_calls() -> None:
    result = validate()

    assert result["trajectory_count"] == 50
    assert result["turn_count_per_condition"] == 200
    assert result["selected_model"] == "deterministic/v1"
    assert result["provider_calls"] == 0
    assert result["cost_usd"] == 0


def test_local_r1_confirmation_rejects_drifted_standard_record() -> None:
    result = copy.deepcopy(_load(DEFAULT_OUTPUT))
    result["decision"]["selected_implementation_id"] = (
        "deterministic-grounded-assistant-t0"
    )

    with pytest.raises(LocalR1ConfirmationError, match="decision drifted"):
        _validate_published_result(
            result,
            profile_sha256=hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest(),
            instrument_sha256=EXECUTED_INSTRUMENT_SHA256,
        )
