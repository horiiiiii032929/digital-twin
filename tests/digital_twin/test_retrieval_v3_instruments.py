from __future__ import annotations

import copy

import pytest

from scripts.validate_retrieval_v3_instruments import (
    FREEZE_PATH,
    load_json,
    validate_freeze,
    validate_retrieval_v3_instruments,
)


def test_retrieval_v3_instruments_validate() -> None:
    result = validate_retrieval_v3_instruments()

    assert result == {
        "status": "passed",
        "example_cases": 1,
        "conditions": 8,
        "datasets": 2,
        "primary_metrics": 3,
        "hard_gates": 6,
        "rapid_heldout_cases": 59,
    }


def test_retrieval_v3_keeps_heldout_access_disabled() -> None:
    freeze = load_json(FREEZE_PATH)
    changed = copy.deepcopy(freeze)
    changed["heldout_access_allowed"] = True

    with pytest.raises(ValueError, match="held-out access"):
        validate_freeze(changed)


def test_notebooklm_cannot_select_internal_retriever() -> None:
    freeze = load_json(FREEZE_PATH)
    changed = copy.deepcopy(freeze)
    changed["black_box_reference"]["selection_eligible"] = True

    with pytest.raises(ValueError, match="NotebookLM cannot select"):
        validate_freeze(changed)


def test_retrieval_v3_rejects_duplicate_conditions() -> None:
    freeze = load_json(FREEZE_PATH)
    changed = copy.deepcopy(freeze)
    changed["conditions"].append(copy.deepcopy(changed["conditions"][0]))

    with pytest.raises(ValueError, match="duplicate condition ID"):
        validate_freeze(changed)


def test_rapid_checkpoint_cannot_select_keep() -> None:
    freeze = load_json(FREEZE_PATH)
    changed = copy.deepcopy(freeze)
    changed["rapid_checkpoint"]["decision"]["keep_available"] = True

    with pytest.raises(ValueError, match="cannot make a final selection"):
        validate_freeze(changed)
