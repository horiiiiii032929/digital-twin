from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.validate_evidence_sufficiency_v2 import (
    DEFAULT_INSTRUMENT,
    EvidenceSufficiencyV2ValidationError,
    preflight,
    validate_instrument,
)


def write_instrument(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "instrument.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_build_only_instrument_is_valid_and_preflight_fails_closed() -> None:
    instrument = validate_instrument()

    result = preflight(instrument)

    assert result["status"] == "blocked-dataset-not-frozen"
    assert result["provider_calls"] == 0
    assert result["private_data_read"] is False
    assert result["decision_split_opened"] is False
    assert set(result["blockers"]) == {
        "decision-dataset-not-frozen",
        "candidate-model-not-bound",
        "calibration-not-authorized",
        "decision-split-not-authorized",
    }


def test_any_hit_and_consumed_data_cannot_become_selection_evidence(
    tmp_path: Path,
) -> None:
    instrument = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    changed = copy.deepcopy(instrument)
    changed["candidate_families"][0]["selectable"] = True
    with pytest.raises(EvidenceSufficiencyV2ValidationError, match="AnyHit"):
        validate_instrument(write_instrument(tmp_path, changed))

    changed = copy.deepcopy(instrument)
    changed["historical_development_data"]["selection_eligible"] = True
    with pytest.raises(EvidenceSufficiencyV2ValidationError, match="consumed"):
        validate_instrument(write_instrument(tmp_path, changed))


def test_build_only_instrument_cannot_self_authorize_or_claim_release(
    tmp_path: Path,
) -> None:
    instrument = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    changed = copy.deepcopy(instrument)
    changed["execution_safety"]["provider_execution_authorized"] = True
    with pytest.raises(EvidenceSufficiencyV2ValidationError, match="safety"):
        validate_instrument(write_instrument(tmp_path, changed))

    changed = copy.deepcopy(instrument)
    changed["decision_rule"]["authorize_release"] = True
    with pytest.raises(EvidenceSufficiencyV2ValidationError, match="release"):
        validate_instrument(write_instrument(tmp_path, changed))


def test_academic_integrity_remains_a_separate_policy_boundary(
    tmp_path: Path,
) -> None:
    instrument = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    instrument["boundary_ownership"][
        "academic_integrity_is_answerability_label"
    ] = True

    with pytest.raises(EvidenceSufficiencyV2ValidationError, match="integrity"):
        validate_instrument(write_instrument(tmp_path, instrument))
