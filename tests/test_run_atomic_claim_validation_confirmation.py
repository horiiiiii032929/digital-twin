from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.run_atomic_claim_validation_confirmation import (
    AtomicClaimConfirmationError,
    DEFAULT_INSTRUMENT,
    preflight,
    simulate,
    validate_instrument,
)


def _write_instrument(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "instrument.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_confirmation_is_completed_and_blocked_after_revocation() -> None:
    instrument = validate_instrument()

    result = preflight(instrument)

    assert result["status"] == "blocked-not-authorized"
    assert {
        "candidate-execution-authorized-false",
        "local-model-execution-authorized-false",
        "confirmation-split-execution-authorized-false",
    }.issubset(result["blockers"])
    assert set(result["blockers"]) <= {
        "candidate-execution-authorized-false",
        "local-model-execution-authorized-false",
        "confirmation-split-execution-authorized-false",
        "stale-model-metadata",
    }
    assert result["confirmation_split_opened"] is False
    assert result["model_loaded"] is False
    assert result["provider_calls"] == 0
    assert result["paid_cost_usd"] == 0


def test_network_free_simulation_checks_release_reject_and_lineage() -> None:
    result = simulate(validate_instrument())

    assert result["status"] == "passed-network-free-simulation"
    assert result["supported_claim_released"] is True
    assert result["unsupported_claim_rejected"] is True
    assert result["unknown_lineage_rejected"] is True
    assert result["confirmation_split_opened"] is False
    assert result["model_loaded"] is False


def test_authorities_must_move_together_with_frozen_status(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    payload["execution_safety"]["candidate_execution_authorized"] = True
    with pytest.raises(AtomicClaimConfirmationError, match="authorities disagree"):
        validate_instrument(_write_instrument(tmp_path, payload))

    authorized = copy.deepcopy(payload)
    authorized["execution_safety"]["local_model_execution_authorized"] = True
    authorized["execution_safety"]["confirmation_split_execution_authorized"] = True
    with pytest.raises(AtomicClaimConfirmationError, match="status and local authority"):
        validate_instrument(_write_instrument(tmp_path, authorized))


def test_model_revision_thresholds_and_gates_are_frozen(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    payload["candidates"][1]["model"]["revision"] = "main"
    with pytest.raises(AtomicClaimConfirmationError, match="model binding"):
        validate_instrument(_write_instrument(tmp_path, payload))

    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    payload["thresholds"]["minimum_entailment"] = 0.5
    with pytest.raises(AtomicClaimConfirmationError, match="thresholds"):
        validate_instrument(_write_instrument(tmp_path, payload))

    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    payload["hard_gates"]["false_release_count_max"] = 1
    with pytest.raises(AtomicClaimConfirmationError, match="hard gates"):
        validate_instrument(_write_instrument(tmp_path, payload))


def test_product_binding_and_external_execution_cannot_be_enabled(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    payload["execution_safety"]["product_binding_authorized"] = True
    with pytest.raises(AtomicClaimConfirmationError, match="safety boundary"):
        validate_instrument(_write_instrument(tmp_path, payload))

    payload = json.loads(DEFAULT_INSTRUMENT.read_text(encoding="utf-8"))
    payload["execution_safety"]["paid_execution_authorized"] = True
    with pytest.raises(AtomicClaimConfirmationError, match="safety boundary"):
        validate_instrument(_write_instrument(tmp_path, payload))
