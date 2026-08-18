import copy
import json
from pathlib import Path

import pytest

from scripts.validate_deployable_foundation_freeze import validate_deployable_freeze


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/profiles/deployable-product-foundation-freeze-v1.json"
)


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_current_deployable_foundation_freeze_validates() -> None:
    result = validate_deployable_freeze(_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "go-deeper"
    assert result["local_gates"] == "41/41"
    assert result["external_gates_pending"] == 3
    assert result["artifact_bindings"] == 30


def test_deployable_freeze_rejects_bound_artifact_hash_drift() -> None:
    manifest = _manifest()
    manifest["artifact_bindings"][0]["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="revision artifact hash mismatch"):
        validate_deployable_freeze(manifest, root=ROOT)


def test_deployable_freeze_rejects_external_gate_promotion() -> None:
    manifest = _manifest()
    manifest["external_gates"][0]["status"] = "passed"

    with pytest.raises(ValueError, match="cannot pass without a new freeze"):
        validate_deployable_freeze(manifest, root=ROOT)


def test_deployable_freeze_rejects_duplicate_external_gate() -> None:
    manifest = _manifest()
    manifest["external_gates"].append(copy.deepcopy(manifest["external_gates"][0]))

    with pytest.raises(ValueError, match="incomplete or duplicated"):
        validate_deployable_freeze(manifest, root=ROOT)
