#!/usr/bin/env python3
"""Validate historical and current deployable-product foundation freezes."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROFILE_ROOT = ROOT / "research/05_evaluation/profiles"
MANIFEST_PATHS = (
    PROFILE_ROOT / "deployable-product-foundation-freeze-v1.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v2.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v3.json",
    PROFILE_ROOT / "deployable-product-foundation-freeze-v4.json",
)
EXPECTED_EXTERNAL_GATES = {
    "public-dns-and-certificate",
    "clean-host-restore",
    "staging-workflow-walkthrough",
}
FREEZE_SPECS: dict[str, dict[str, Any]] = {
    "deployable-product-foundation-freeze-v1": {
        "status": "go-deeper-external-rehearsal-pending",
        "run_id": "deployable-product-foundation-v1-development-001",
        "candidate_id": "A1-single-node-staging",
        "local_fields": {
            "passed": 41,
            "total": 41,
            "external_provider_calls": 0,
            "private_data_used": False,
        },
        "local_label": "41/41",
        "summary_marker": "41/41 frozen local checks",
        "build_fields": {
            "status": "blocked-registry-resolution",
            "compose_graph_validated": True,
            "image_build_claimed": False,
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run verify:deployable-freeze",
        },
        "artifact_count": 30,
        "require_current_match": False,
    },
    "deployable-product-foundation-freeze-v2": {
        "status": "go-deeper-public-host-rehearsal-pending",
        "run_id": "deployable-product-foundation-v2-container-001",
        "candidate_id": "A1-single-node-staging-v2",
        "local_fields": {
            "in_process_passed": 41,
            "in_process_total": 41,
            "live_https_passed": 25,
            "live_https_total": 25,
            "container_build_passed": True,
            "clean_restore_passed": True,
            "external_provider_calls": 0,
            "private_data_used": False,
        },
        "local_label": "25/25-live-https",
        "summary_marker": "25/25 live HTTPS checks",
        "build_fields": {
            "status": "passed",
            "compose_graph_validated": True,
            "image_build_claimed": True,
            "api_image_sha256": (
                "f879ae4cb275174b9b233a5a7276a6510cec3453dc16a83f40f3891fbe3bde42"
            ),
            "web_image_sha256": (
                "cb87eb79cdbbda694c864b220f76ae008446535a0308b3f068103d555976a582"
            ),
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
        },
        "artifact_count": 37,
        "require_current_match": False,
    },
    "deployable-product-foundation-freeze-v3": {
        "status": "go-deeper-public-host-rehearsal-pending",
        "run_id": "deployable-product-foundation-v3-model-policy-001",
        "candidate_id": "A1-single-node-staging-v3-model-policy",
        "local_fields": {
            "model_policy_focused_passed": 95,
            "model_policy_focused_total": 95,
            "in_process_passed": 41,
            "in_process_total": 41,
            "live_https_passed": 25,
            "live_https_total": 25,
            "container_build_passed": True,
            "clean_restore_passed": True,
            "external_provider_calls": 0,
            "private_data_used": False,
        },
        "local_label": "95/95-policy-and-25/25-live-https",
        "summary_marker": "95/95 focused policy",
        "build_fields": {
            "status": "passed",
            "compose_graph_validated": True,
            "image_build_claimed": True,
            "api_image_sha256": (
                "1de9c871a1b24a84528449ef422e105fc274dd751a81d6bed8f698e0df6c9f36"
            ),
            "web_image_sha256": (
                "4dc17ed8463da0427ab4e74c463b0c7680a09c64345327684036a6a0948bd11b"
            ),
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run staging:build",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
            "npm run verify:model-policy",
        },
        "artifact_count": 46,
        "require_current_match": False,
    },
    "deployable-product-foundation-freeze-v4": {
        "status": "go-deeper-public-host-rehearsal-pending",
        "run_id": "deployable-product-foundation-v4-provider-registry-001",
        "candidate_id": "A1-single-node-staging-v4-provider-registry",
        "local_fields": {
            "model_policy_focused_passed": 107,
            "model_policy_focused_total": 107,
            "in_process_passed": 41,
            "in_process_total": 41,
            "live_https_passed": 30,
            "live_https_total": 30,
            "container_build_passed": True,
            "clean_restore_passed": True,
            "external_provider_calls": 0,
            "private_data_used": False,
        },
        "local_label": "107/107-policy-provider-and-30/30-live-https",
        "summary_marker": "107/107 focused",
        "build_fields": {
            "status": "passed",
            "compose_graph_validated": True,
            "image_build_claimed": True,
            "api_image_sha256": (
                "cedb76c79c563200aae4802544eb5d0616157f14ac23da63a8717f9db4e1a440"
            ),
            "web_image_sha256": (
                "e4f4a60903544afab70e93287c8add40499805cc088d28eaf605318642a24917"
            ),
        },
        "commands": {
            "npm run check",
            "npm run audit:dependencies",
            "npm run verify:deployable-foundation",
            "npm run benchmark:deployable-foundation-development",
            "npm run staging:build",
            "npm run verify:staging-https",
            "npm run verify:deployable-freeze",
            "npm run verify:model-policy",
        },
        "artifact_count": 53,
        "require_current_match": False,
    },
}


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _revision_file(root: Path, revision: str, relative_path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{revision}:{relative_path}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def _is_ancestor(root: Path, revision: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", revision, "HEAD"],
            cwd=root,
            check=False,
        ).returncode
        == 0
    )


def _current_file(root: Path, relative_path: str) -> Path:
    candidate_path = Path(relative_path)
    if candidate_path.is_absolute() or ".." in candidate_path.parts:
        raise ValueError("freeze paths must remain repository-relative")
    current = root / candidate_path
    if not current.is_file():
        raise ValueError(f"bound artifact is missing: {relative_path}")
    return current


def _revision_json(root: Path, revision: str, relative_path: str) -> dict[str, Any]:
    return json.loads(_revision_file(root, revision, relative_path))


def validate_deployable_freeze(
    manifest: dict[str, Any], *, root: Path
) -> dict[str, Any]:
    freeze_id = manifest.get("freeze_id", "")
    spec = FREEZE_SPECS.get(freeze_id)
    if spec is None:
        raise ValueError("unexpected deployable freeze identifier")
    if manifest.get("status") != spec["status"]:
        raise ValueError("deployable freeze status drifted")
    if manifest.get("run_id") != spec["run_id"]:
        raise ValueError("deployable freeze run identity drifted")
    if manifest.get("decision") != "go-deeper":
        raise ValueError("deployable freeze decision drifted")
    if manifest.get("candidate_id") != spec["candidate_id"]:
        raise ValueError("deployable freeze candidate drifted")

    revision = manifest.get("evidence_revision", "")
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or not _is_ancestor(root, revision):
        raise ValueError("evidence revision is not an ancestor of HEAD")
    if manifest.get("private_or_heldout_data_read") is not False:
        raise ValueError("deployable freeze cannot read private or held-out data")
    if manifest.get("external_model_called") is not False:
        raise ValueError("deployable freeze cannot call an external model")

    local_gates = manifest.get("local_gates", {})
    if any(
        local_gates.get(field) != expected
        for field, expected in spec["local_fields"].items()
    ):
        raise ValueError("local gate count or data boundary drifted")

    if freeze_id in {
        "deployable-product-foundation-freeze-v3",
        "deployable-product-foundation-freeze-v4",
    }:
        expected_model_policy = {
            "policy_id": "current-model-policy-2026-08-19",
            "gemma_execution_allowed": False,
            "retired_general_qwen_execution_allowed": False,
            "local_general_model": "qwen3.5:4b",
            "local_general_model_digest": (
                "2a654d98e6fba55d452b7043684e9b57"
                "a947e393bbffa62485a7aac05ee4eefd"
            ),
            "model_called_during_policy_validation": False,
        }
        if freeze_id == "deployable-product-foundation-freeze-v4":
            expected_model_policy["registered_hosted_retrieval_models"] = [
                "jina-embeddings-v5-text-small",
                "jina-reranker-v3",
            ]
        if manifest.get("model_policy") != expected_model_policy:
            raise ValueError("current model policy freeze binding drifted")

    external = manifest.get("external_gates", [])
    gate_ids = [gate.get("id") for gate in external]
    if len(gate_ids) != len(set(gate_ids)) or set(gate_ids) != EXPECTED_EXTERNAL_GATES:
        raise ValueError("external gate inventory is incomplete or duplicated")
    if any(gate.get("status") != "pending" for gate in external):
        raise ValueError("external gate cannot pass without a new freeze")

    build = manifest.get("container_build", {})
    if any(
        build.get(field) != expected
        for field, expected in spec["build_fields"].items()
    ):
        raise ValueError("container-build evidence drifted")

    bindings = manifest.get("artifact_bindings", [])
    binding_paths = [binding.get("path") for binding in bindings]
    if (
        len(binding_paths) != len(set(binding_paths))
        or len(binding_paths) != spec["artifact_count"]
    ):
        raise ValueError("artifact binding inventory is incomplete or duplicated")
    for binding in bindings:
        relative_path = binding["path"]
        expected = binding.get("sha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"invalid artifact hash: {relative_path}")
        if _sha256(_revision_file(root, revision, relative_path)) != expected:
            raise ValueError(f"revision artifact hash mismatch: {relative_path}")
        if spec["require_current_match"] and (
            _sha256(_current_file(root, relative_path).read_bytes()) != expected
        ):
            raise ValueError(f"current artifact drifted from freeze: {relative_path}")

    record_path = f"research/05_evaluation/records/{spec['run_id']}.json"
    record = _revision_json(root, revision, record_path)
    if (
        record.get("run_id") != manifest["run_id"]
        or record.get("decision", {}).get("outcome") != "go-deeper"
        or record.get("decision", {}).get("selected_implementation_id")
        != manifest["candidate_id"].lower()
    ):
        raise ValueError("registered decision does not match the deployment freeze")
    summary_path = f"research/05_evaluation/{spec['run_id']}-results.md"
    summary = _revision_file(root, revision, summary_path).decode("utf-8")
    if spec["summary_marker"] not in summary:
        raise ValueError("human-readable result does not preserve the local gate count")

    if set(manifest.get("reproduction_commands", [])) != spec["commands"]:
        raise ValueError("deployable freeze reproduction commands drifted")
    package_scripts = json.loads((root / "package.json").read_text(encoding="utf-8"))[
        "scripts"
    ]
    if package_scripts.get("verify:deployable-freeze") != (
        "uv run python -m scripts.validate_deployable_foundation_freeze"
    ):
        raise ValueError("deployable freeze command is not registered")
    if "npm run verify:deployable-freeze" not in package_scripts.get("check", ""):
        raise ValueError("deployable freeze is absent from the full check")
    if freeze_id != "deployable-product-foundation-freeze-v1" and package_scripts.get("verify:staging-https") != (
        "uv run python -m scripts.verify_https_staging"
    ):
        raise ValueError("live HTTPS verification command is not registered")
    if not manifest.get("rollback") or not manifest.get("change_control"):
        raise ValueError("deployable freeze must preserve rollback and change control")

    return {
        "status": "passed",
        "freeze_id": freeze_id,
        "evidence_revision": revision,
        "decision": manifest["decision"],
        "local_gates": spec["local_label"],
        "external_gates_pending": len(external),
        "artifact_bindings": len(bindings),
        "current_match_required": spec["require_current_match"],
        "private_or_heldout_data_read": False,
        "external_model_called": False,
    }


def main() -> None:
    results = [
        validate_deployable_freeze(
            json.loads(manifest_path.read_text(encoding="utf-8")),
            root=ROOT,
        )
        for manifest_path in MANIFEST_PATHS
    ]
    print(json.dumps({"status": "passed", "freezes": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
