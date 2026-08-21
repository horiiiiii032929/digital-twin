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
V6_MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/profiles/deployable-product-foundation-freeze-v6.json"
)
V7_MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/profiles/deployable-product-foundation-freeze-v7.json"
)
V8_MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/profiles/deployable-product-foundation-freeze-v8.json"
)
V9_MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/profiles/deployable-product-foundation-freeze-v9.json"
)
V10_MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/profiles/deployable-product-foundation-freeze-v10.json"
)
V11_MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/profiles/deployable-product-foundation-freeze-v11.json"
)
V12_MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/profiles/deployable-product-foundation-freeze-v12.json"
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


def _v6_manifest() -> dict:
    return json.loads(V6_MANIFEST_PATH.read_text(encoding="utf-8"))


def _v7_manifest() -> dict:
    return json.loads(V7_MANIFEST_PATH.read_text(encoding="utf-8"))


def _v8_manifest() -> dict:
    return json.loads(V8_MANIFEST_PATH.read_text(encoding="utf-8"))


def _v9_manifest() -> dict:
    return json.loads(V9_MANIFEST_PATH.read_text(encoding="utf-8"))


def _v10_manifest() -> dict:
    return json.loads(V10_MANIFEST_PATH.read_text(encoding="utf-8"))


def _v11_manifest() -> dict:
    return json.loads(V11_MANIFEST_PATH.read_text(encoding="utf-8"))


def _v12_manifest() -> dict:
    return json.loads(V12_MANIFEST_PATH.read_text(encoding="utf-8"))


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


def test_historical_local_multimodel_policy_container_freeze_validates() -> None:
    result = validate_deployable_freeze(_v5_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "go-deeper"
    assert result["local_gates"] == (
        "113/113-policy-provider-and-30/30-live-https"
    )
    assert result["external_gates_pending"] == 3
    assert result["artifact_bindings"] == 67
    assert result["current_match_required"] is False


def test_current_stable_boundary_container_freeze_validates() -> None:
    result = validate_deployable_freeze(_v6_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "go-deeper"
    assert result["local_gates"] == (
        "113/113-policy-provider-and-30/30-live-https"
    )
    assert result["external_gates_pending"] == 3
    assert result["artifact_bindings"] == 67
    assert result["current_match_bindings"] == 45
    assert result["current_match_required"] is True
    assert result["current_match_enforced"] is False
    assert result["current_match_status"] == (
        "suspended-by-repository-correctness-audit"
    )
    assert result["release_claim_authorized"] is False


def test_post_correctness_current_tree_freeze_validates_without_image_claim() -> None:
    result = validate_deployable_freeze(_v7_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "go-deeper"
    assert result["local_gates"] == "42/42-current-in-process-container-pending"
    assert result["external_gates_pending"] == 4
    assert result["artifact_bindings"] == 31
    assert result["tree_bindings"] == 14
    assert result["file_bindings"] == 17
    assert result["current_match_required"] is False
    assert result["current_match_status"] == "historical-superseded"
    assert result["container_build_status"] == "blocked-local-docker-runtime"
    assert result["image_build_claimed"] is False
    assert result["release_claim_authorized"] is False


def test_current_image_refine_freeze_validates_without_release_claim() -> None:
    result = validate_deployable_freeze(_v8_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "refine"
    assert result["local_gates"] == (
        "current-images-healthy-publication-fail-closed"
    )
    assert result["external_gates_pending"] == 4
    assert result["artifact_bindings"] == 31
    assert result["tree_bindings"] == 14
    assert result["file_bindings"] == 17
    assert result["current_match_required"] is False
    assert result["current_match_status"] == "historical-superseded"
    assert result["container_build_status"] == (
        "passed-current-images-product-publication-blocked"
    )
    assert result["image_build_claimed"] is True
    assert result["release_claim_authorized"] is False


def test_current_open_set_build_freeze_validates_without_image_or_release_claim() -> None:
    result = validate_deployable_freeze(_v9_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "refine"
    assert result["local_gates"] == "29/29-open-set-build-only"
    assert result["external_gates_pending"] == 4
    assert result["artifact_bindings"] == 33
    assert result["tree_bindings"] == 14
    assert result["file_bindings"] == 19
    assert result["current_match_required"] is False
    assert result["current_match_status"] == "historical-superseded"
    assert result["container_build_status"] == (
        "current-source-images-unbuilt-v8-images-historical"
    )
    assert result["image_build_claimed"] is False
    assert result["release_claim_authorized"] is False


def test_current_malformed_output_correction_freeze_validates() -> None:
    result = validate_deployable_freeze(_v10_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "refine"
    assert result["local_gates"] == "30/30-open-set-build-only"
    assert result["artifact_bindings"] == 33
    assert result["current_match_required"] is False
    assert result["current_match_status"] == "historical-superseded"
    assert result["image_build_claimed"] is False
    assert result["release_claim_authorized"] is False


def test_current_decision_draft_freeze_validates_without_execution_claim() -> None:
    result = validate_deployable_freeze(_v11_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "refine"
    assert result["local_gates"] == "41/41-decision-draft-build-only"
    assert result["artifact_bindings"] == 36
    assert result["tree_bindings"] == 14
    assert result["file_bindings"] == 22
    assert result["current_match_required"] is False
    assert result["current_match_status"] == "historical-superseded"
    assert result["image_build_claimed"] is False
    assert result["release_claim_authorized"] is False


def test_current_review_workflow_freeze_validates_without_execution_claim() -> None:
    result = validate_deployable_freeze(_v12_manifest(), root=ROOT)

    assert result["status"] == "passed"
    assert result["decision"] == "refine"
    assert result["local_gates"] == "35/35-review-workflow-build-only"
    assert result["artifact_bindings"] == 40
    assert result["tree_bindings"] == 14
    assert result["file_bindings"] == 26
    assert result["current_match_required"] is True
    assert result["current_match_status"] == "enforced"
    assert result["image_build_claimed"] is False
    assert result["release_claim_authorized"] is False


def test_stable_boundary_excludes_append_only_registry_from_current_match() -> None:
    manifest = _v6_manifest()
    bindings = {item["path"]: item for item in manifest["artifact_bindings"]}

    assert bindings["research/05_evaluation/result-registry.md"][
        "current_match_required"
    ] is False
    assert bindings["compose.staging.yml"]["current_match_required"] is True


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


def test_v7_freeze_rejects_tree_identity_drift() -> None:
    manifest = _v7_manifest()
    manifest["tree_bindings"][0]["git_tree_sha1"] = "0" * 40

    with pytest.raises(ValueError, match="revision tree identity mismatch"):
        validate_deployable_freeze(manifest, root=ROOT)


def test_v7_freeze_rejects_unearned_image_or_release_claim() -> None:
    image_manifest = _v7_manifest()
    image_manifest["container_build"]["image_build_claimed"] = True

    with pytest.raises(ValueError, match="container-build evidence drifted"):
        validate_deployable_freeze(image_manifest, root=ROOT)

    release_manifest = _v7_manifest()
    release_manifest["release_claim_authorized"] = True

    with pytest.raises(ValueError, match="cannot authorize a release claim"):
        validate_deployable_freeze(release_manifest, root=ROOT)


def test_v8_freeze_rejects_release_claim_or_selected_candidate() -> None:
    release_manifest = _v8_manifest()
    release_manifest["release_claim_authorized"] = True

    with pytest.raises(ValueError, match="cannot authorize a release claim"):
        validate_deployable_freeze(release_manifest, root=ROOT)

    decision_manifest = _v8_manifest()
    decision_manifest["decision"] = "go-deeper"

    with pytest.raises(ValueError, match="decision drifted"):
        validate_deployable_freeze(decision_manifest, root=ROOT)


def test_v10_freeze_rejects_image_release_or_selection_claim() -> None:
    image_manifest = _v10_manifest()
    image_manifest["container_build"]["image_build_claimed"] = True
    with pytest.raises(ValueError, match="container-build evidence drifted"):
        validate_deployable_freeze(image_manifest, root=ROOT)

    release_manifest = _v10_manifest()
    release_manifest["release_claim_authorized"] = True
    with pytest.raises(ValueError, match="cannot authorize a release claim"):
        validate_deployable_freeze(release_manifest, root=ROOT)

    selected_manifest = _v10_manifest()
    selected_manifest["local_gates"]["evidence_sufficiency_selected"] = True
    with pytest.raises(ValueError, match="local gate count"):
        validate_deployable_freeze(selected_manifest, root=ROOT)


def test_v11_freeze_rejects_review_freeze_execution_or_release_claims() -> None:
    reviewed_manifest = _v11_manifest()
    reviewed_manifest["local_gates"]["independent_review_completed"] = True
    with pytest.raises(ValueError, match="local gate count"):
        validate_deployable_freeze(reviewed_manifest, root=ROOT)

    frozen_manifest = _v11_manifest()
    frozen_manifest["local_gates"]["decision_dataset_frozen"] = True
    with pytest.raises(ValueError, match="local gate count"):
        validate_deployable_freeze(frozen_manifest, root=ROOT)

    release_manifest = _v11_manifest()
    release_manifest["release_claim_authorized"] = True
    with pytest.raises(ValueError, match="cannot authorize a release claim"):
        validate_deployable_freeze(release_manifest, root=ROOT)


def test_v12_freeze_rejects_review_freeze_selection_or_release_claims() -> None:
    reviewed_manifest = _v12_manifest()
    reviewed_manifest["local_gates"]["independent_review_completed"] = True
    with pytest.raises(ValueError, match="local gate count"):
        validate_deployable_freeze(reviewed_manifest, root=ROOT)

    frozen_manifest = _v12_manifest()
    frozen_manifest["local_gates"]["decision_dataset_frozen"] = True
    with pytest.raises(ValueError, match="local gate count"):
        validate_deployable_freeze(frozen_manifest, root=ROOT)

    selected_manifest = _v12_manifest()
    selected_manifest["local_gates"]["evidence_sufficiency_selected"] = True
    with pytest.raises(ValueError, match="local gate count"):
        validate_deployable_freeze(selected_manifest, root=ROOT)

    release_manifest = _v12_manifest()
    release_manifest["release_claim_authorized"] = True
    with pytest.raises(ValueError, match="cannot authorize a release claim"):
        validate_deployable_freeze(release_manifest, root=ROOT)
