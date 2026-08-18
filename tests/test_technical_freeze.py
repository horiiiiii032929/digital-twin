import copy
import json
from pathlib import Path

import pytest

from scripts.validate_technical_freeze import (
    validate_freeze,
    validate_registry_extension,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT / "research/05_evaluation/profiles/technical-evidence-freeze-v1.json"
)


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_current_technical_freeze_validates() -> None:
    summary = validate_freeze(_manifest(), root=ROOT)

    assert summary["status"] == "passed"
    assert summary["profile_stage"] == "experimental"
    assert summary["registered_component_links"] == 7
    assert summary["claims"] == 15
    assert summary["required_boundaries"] == 9


def test_freeze_rejects_artifact_hash_drift() -> None:
    manifest = _manifest()
    manifest["artifact_bindings"][0]["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="hash mismatch"):
        validate_freeze(manifest, root=ROOT)


def test_freeze_rejects_missing_selected_component_evidence() -> None:
    manifest = _manifest()
    manifest["component_evidence"] = manifest["component_evidence"][:-1]

    with pytest.raises(ValueError, match="coverage is incomplete"):
        validate_freeze(manifest, root=ROOT)


def test_freeze_rejects_promoted_unsupported_claim() -> None:
    manifest = _manifest()
    unsupported = next(
        claim for claim in manifest["claims"] if claim["claim_id"] == "U05"
    )
    unsupported["status"] = "supported"

    with pytest.raises(ValueError, match="claim status drifted"):
        validate_freeze(manifest, root=ROOT)


def test_freeze_rejects_duplicate_claim_inventory() -> None:
    manifest = _manifest()
    manifest["claims"].append(copy.deepcopy(manifest["claims"][0]))

    with pytest.raises(ValueError, match="incomplete or duplicated"):
        validate_freeze(manifest, root=ROOT)


def test_freeze_rejects_capacity_promotion_without_new_freeze() -> None:
    manifest = _manifest()
    capacity = next(
        boundary
        for boundary in manifest["required_boundaries"]
        if boundary["boundary"] == "capacity"
    )
    capacity["disposition"] = "pass"

    with pytest.raises(ValueError, match="boundary disposition drifted"):
        validate_freeze(manifest, root=ROOT)


def test_freeze_registry_allows_new_result_rows() -> None:
    frozen = "| `result-a` | old evidence |\n"
    current = frozen + "| `result-b` | new evidence |\n"

    validate_registry_extension(frozen, current)


def test_freeze_registry_rejects_changed_historical_row() -> None:
    frozen = "| `result-a` | old evidence |\n"
    current = "| `result-a` | rewritten evidence |\n"

    with pytest.raises(ValueError, match="frozen evaluation registry rows drifted"):
        validate_registry_extension(frozen, current)
