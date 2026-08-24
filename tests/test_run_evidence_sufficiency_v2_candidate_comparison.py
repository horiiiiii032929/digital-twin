from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.run_evidence_sufficiency_v2_candidate_comparison import (
    CandidateComparisonError,
    DEFAULT_INSTRUMENT,
    preflight,
    simulate,
    validate_instrument,
)


def write_instrument(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "instrument.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_candidate_comparison_is_frozen_and_ready_for_one_local_run() -> None:
    instrument = validate_instrument()

    result = preflight(instrument)

    assert result["status"] == "ready"
    assert result["blockers"] == []
    assert result["decision_split_opened"] is False
    assert result["model_loaded"] is False
    assert result["provider_calls"] == 0
    assert result["paid_cost_usd"] == 0


def test_network_free_simulation_does_not_open_decision_data_or_load_models() -> None:
    result = simulate(validate_instrument())

    assert result["status"] == "passed-network-free-simulation"
    assert result["empty_evidence_rejected"] is True
    assert result["decision_split_opened"] is False
    assert result["model_loaded"] is False
    assert result["provider_calls"] == 0


def test_any_hit_cannot_become_selectable(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    payload["candidates"][0]["selectable"] = True

    with pytest.raises(CandidateComparisonError, match="AnyHit"):
        validate_instrument(write_instrument(tmp_path, payload))


def test_local_authorities_must_move_together_in_a_frozen_status(
    tmp_path: Path,
) -> None:
    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    payload["execution_safety"]["candidate_execution_authorized"] = False

    with pytest.raises(CandidateComparisonError, match="authorities disagree"):
        validate_instrument(write_instrument(tmp_path, payload))

    authorized = copy.deepcopy(payload)
    authorized["execution_safety"]["local_model_execution_authorized"] = False
    authorized["execution_safety"]["decision_split_execution_authorized"] = False
    with pytest.raises(CandidateComparisonError, match="status and local authority"):
        validate_instrument(write_instrument(tmp_path, authorized))


def test_model_revision_and_hard_gates_are_immutable(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    payload["candidates"][2]["model"]["revision"] = "latest"
    with pytest.raises(CandidateComparisonError, match="model binding"):
        validate_instrument(write_instrument(tmp_path, payload))

    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    payload["hard_gates"]["false_answer_count_max"] = 1
    with pytest.raises(CandidateComparisonError, match="hard gates"):
        validate_instrument(write_instrument(tmp_path, payload))
