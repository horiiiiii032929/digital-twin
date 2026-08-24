from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.validate_evidence_sufficiency_v2_decision_freeze import validate_freeze


ROOT = Path(__file__).resolve().parents[1]
FREEZE = (
    ROOT
    / "research/05_evaluation/instruments/evidence_sufficiency_v2_decision_freeze_001.json"
)


def test_current_decision_freeze_passes_without_opening_data() -> None:
    result = validate_freeze()

    assert result["status"] == "passed"
    assert result["case_count"] == 120
    assert result["human_confirmations"] == 4
    assert result["opened_for_candidate_evaluation"] is False
    assert result["provider_or_model_calls"] == 0
    assert result["private_data_read"] is False


@pytest.mark.parametrize(
    ("path", "value", "pattern"),
    [
        (("dataset", "opened_for_candidate_evaluation"), True, "unopened"),
        (("execution_safety", "candidate_evaluation_authorized"), True, "authority"),
        (("execution_safety", "automatic_selection"), True, "authority"),
    ],
)
def test_decision_freeze_rejects_opened_authority(
    tmp_path: Path,
    path: tuple[str, str],
    value: bool,
    pattern: str,
) -> None:
    payload = json.loads(FREEZE.read_text(encoding="utf-8"))
    changed = copy.deepcopy(payload)
    changed[path[0]][path[1]] = value
    candidate = tmp_path / "freeze.json"
    candidate.write_text(json.dumps(changed), encoding="utf-8")

    with pytest.raises(ValueError, match=pattern):
        validate_freeze(candidate)
