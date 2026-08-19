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
V2_MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/profiles/deployable-product-foundation-freeze-v2.json"
)
V3_MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/profiles/deployable-product-foundation-freeze-v3.json"
)
V4_MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/profiles/deployable-product-foundation-freeze-v4.json"
)
V5_MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/profiles/deployable-product-foundation-freeze-v5.json"
)


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _v2_manifest() -> dict:
    return json.loads(V2_MANIFEST_PATH.read_text(encoding="utf-8"))


def _v3_manifest() -> dict:
    return json.loads(V3_MANIFEST_PATH.read_text(encoding="utf-8"))


def _v4_manifest() -> dict:
    return json.loads(V4_MANIFEST_PATH.read_text(encoding="utf-8"))


def _v5_manifest() -> dict:
    return json.loads(V5_MANIFEST_PATH.read_text(encoding="utf-8"))


def test_current_deployable_foundation_freeze_validates() -> None:
    result = validate_deployable_freeze(_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "go-deeper"
    assert result["local_gates"] == "41/41"
    assert result["external_gates_pending"] == 3
    assert result["artifact_bindings"] == 30
    assert result["current_match_required"] is False


def test_historical_container_qualified_freeze_validates() -> None:
    result = validate_deployable_freeze(_v2_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "go-deeper"
    assert result["local_gates"] == "25/25-live-https"
    assert result["external_gates_pending"] == 3
    assert result["artifact_bindings"] == 37
    assert result["current_match_required"] is False


def test_historical_model_policy_container_freeze_validates() -> None:
    result = validate_deployable_freeze(_v3_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "go-deeper"
    assert result["local_gates"] == "95/95-policy-and-25/25-live-https"
    assert result["external_gates_pending"] == 3
    assert result["artifact_bindings"] == 46
    assert result["current_match_required"] is False


def test_historical_provider_registry_container_freeze_validates() -> None:
    result = validate_deployable_freeze(_v4_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "go-deeper"
    assert result["local_gates"] == "107/107-policy-provider-and-30/30-live-https"
    assert result["external_gates_pending"] == 3
    assert result["artifact_bindings"] == 53
    assert result["current_match_required"] is False


def test_current_local_multimodel_policy_container_freeze_validates() -> None:
    result = validate_deployable_freeze(_v5_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "go-deeper"
    assert result["local_gates"] == (
        "113/113-policy-provider-and-30/30-live-https"
    )
    assert result["external_gates_pending"] == 3
    assert result["artifact_bindings"] == 67
    assert result["current_match_required"] is True


def test_container_qualified_freeze_rejects_image_identity_drift() -> None:
    manifest = _v2_manifest()
    manifest["container_build"]["web_image_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="container-build evidence drifted"):
        validate_deployable_freeze(manifest, root=ROOT)


def test_model_policy_freeze_rejects_model_binding_drift() -> None:
    manifest = _v5_manifest()
    manifest["model_policy"]["gemma_execution_allowed"] = True

    with pytest.raises(ValueError, match="model policy freeze binding drifted"):
        validate_deployable_freeze(manifest, root=ROOT)


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
