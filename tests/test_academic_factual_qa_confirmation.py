from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.validate_academic_factual_qa_confirmation import (
    ConfirmationProtocolError,
    DEFAULT_INSTRUMENT,
    preflight,
    validate_instrument,
    zero_event_upper_bound,
)


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "instrument.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_confirmation_protocol_is_frozen_but_execution_is_blocked() -> None:
    instrument = validate_instrument()
    result = preflight(instrument)

    assert result == {
        "instrument_id": "academic-factual-qa-confirmation-001",
        "status": "blocked-build-only",
        "blockers": [
            "source-manifest-not-bound",
            "independent-reference-labels-incomplete",
            "product-revision-and-profile-not-frozen",
            "confirmation-execution-authorized-false",
        ],
        "planned_case_count": 200,
        "planned_cluster_count": 100,
        "provider_calls": 0,
        "private_data_read": False,
        "source_manifest_opened": False,
        "reference_labels_opened": False,
    }


def test_sampling_has_one_answerable_and_boundary_case_per_cluster() -> None:
    sampling = validate_instrument()["sampling_plan"]

    assert sum(sampling["answerable_strata"].values()) == 100
    assert sum(sampling["boundary_strata"].values()) == 100
    assert sampling["cluster_count"] * sampling["cases_per_cluster"] == 200
    assert sampling["course_count"] * sampling["clusters_per_course"] == 100


def test_zero_event_bounds_are_precision_claims_not_zero_risk() -> None:
    assert zero_event_upper_bound(100) == pytest.approx(0.029513, abs=5e-7)
    assert zero_event_upper_bound(300) == pytest.approx(0.009936, abs=5e-7)
    assert zero_event_upper_bound(300) < zero_event_upper_bound(100)


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        ("sampling_plan", "confirmation_case_count", 100, "confirmation size"),
        ("source_contract", "academia_vault_opening_authorized", True, "private source"),
        ("reference_label_contract", "llm_review_is_authoritative", True, "LLM review"),
        ("reference_label_contract", "author_may_validate_own_case", True, "self-validation"),
        ("system_freeze", "provider_or_model_bound", True, "provider"),
        ("execution_safety", "confirmation_execution_authorized", True, "execution authorities"),
    ],
)
def test_protocol_drift_fails_closed(
    tmp_path: Path,
    section: str,
    field: str,
    value: object,
    message: str,
) -> None:
    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated[section][field] = value

    with pytest.raises(ConfirmationProtocolError, match=message):
        validate_instrument(_write(tmp_path, mutated))


def test_every_preregistered_decision_has_durable_memory() -> None:
    instrument = validate_instrument()

    assert instrument["decision_memory_ids"] == [
        "AFQC-001",
        "AFQC-002",
        "AFQC-003",
        "AFQC-004",
        "AFQC-005",
        "AFQC-006",
    ]
