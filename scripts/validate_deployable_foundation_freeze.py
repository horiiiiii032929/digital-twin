#!/usr/bin/env python3
"""Validate the prospective deployable-product foundation freeze."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/profiles/deployable-product-foundation-freeze-v1.json"
)
EXPECTED_EXTERNAL_GATES = {
    "public-dns-and-certificate",
    "clean-host-restore",
    "staging-workflow-walkthrough",
}
EXPECTED_COMMANDS = {
    "npm run check",
    "npm run audit:dependencies",
    "npm run verify:deployable-foundation",
    "npm run benchmark:deployable-foundation-development",
    "npm run verify:deployable-freeze",
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
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("freeze paths must remain repository-relative")
    current = root / path
    if not current.is_file():
        raise ValueError(f"bound artifact is missing: {relative_path}")
    return current


def validate_deployable_freeze(
    manifest: dict[str, Any], *, root: Path
) -> dict[str, Any]:
    if manifest.get("freeze_id") != "deployable-product-foundation-freeze-v1":
        raise ValueError("unexpected deployable freeze identifier")
    if manifest.get("status") != "go-deeper-external-rehearsal-pending":
        raise ValueError("deployable freeze status drifted")
    if manifest.get("run_id") != "deployable-product-foundation-v1-development-001":
        raise ValueError("deployable freeze run identity drifted")
    if manifest.get("decision") != "go-deeper":
        raise ValueError("deployable freeze decision drifted")
    if manifest.get("candidate_id") != "A1-single-node-staging":
        raise ValueError("deployable freeze candidate drifted")
    revision = manifest.get("evidence_revision", "")
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or not _is_ancestor(root, revision):
        raise ValueError("evidence revision is not an ancestor of HEAD")
    if manifest.get("private_or_heldout_data_read") is not False:
        raise ValueError("deployable freeze cannot read private or held-out data")
    if manifest.get("external_model_called") is not False:
        raise ValueError("deployable freeze cannot call an external model")

    gates = manifest.get("local_gates", {})
    if gates.get("passed") != 41 or gates.get("total") != 41:
        raise ValueError("local gate count drifted")
    if gates.get("external_provider_calls") != 0 or gates.get("private_data_used"):
        raise ValueError("local gate data boundary drifted")

    external = manifest.get("external_gates", [])
    gate_ids = [gate.get("id") for gate in external]
    if len(gate_ids) != len(set(gate_ids)) or set(gate_ids) != EXPECTED_EXTERNAL_GATES:
        raise ValueError("external gate inventory is incomplete or duplicated")
    if any(gate.get("status") != "pending" for gate in external):
        raise ValueError("external gate cannot pass without a new freeze")

    build = manifest.get("container_build", {})
    if (
        build.get("status") != "blocked-registry-resolution"
        or build.get("compose_graph_validated") is not True
        or build.get("image_build_claimed") is not False
    ):
        raise ValueError("container-build limitation drifted")

    bindings = manifest.get("artifact_bindings", [])
    paths = [binding.get("path") for binding in bindings]
    if len(paths) != len(set(paths)) or len(paths) < 25:
        raise ValueError("artifact binding inventory is incomplete or duplicated")
    for binding in bindings:
        relative_path = binding["path"]
        expected = binding.get("sha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"invalid artifact hash: {relative_path}")
        if _sha256(_revision_file(root, revision, relative_path)) != expected:
            raise ValueError(f"revision artifact hash mismatch: {relative_path}")
        if _sha256(_current_file(root, relative_path).read_bytes()) != expected:
            raise ValueError(f"current artifact drifted from freeze: {relative_path}")

    record = json.loads(
        _current_file(
            root,
            "research/05_evaluation/records/deployable-product-foundation-v1-development-001.json",
        ).read_text(encoding="utf-8")
    )
    if (
        record.get("run_id") != manifest["run_id"]
        or record.get("decision", {}).get("outcome") != "go-deeper"
        or record.get("decision", {}).get("selected_implementation_id")
        != manifest["candidate_id"].lower()
    ):
        raise ValueError("registered decision does not match the deployment freeze")
    summary = _current_file(
        root,
        "research/05_evaluation/deployable-product-foundation-v1-development-001-results.md",
    ).read_text(encoding="utf-8")
    if "41/41 frozen local checks" not in summary:
        raise ValueError("human-readable result does not preserve the local gate count")

    if set(manifest.get("reproduction_commands", [])) != EXPECTED_COMMANDS:
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
    if not manifest.get("rollback") or not manifest.get("change_control"):
        raise ValueError("deployable freeze must preserve rollback and change control")

    return {
        "status": "passed",
        "freeze_id": manifest["freeze_id"],
        "evidence_revision": revision,
        "decision": manifest["decision"],
        "local_gates": "41/41",
        "external_gates_pending": len(external),
        "artifact_bindings": len(bindings),
        "private_or_heldout_data_read": False,
        "external_model_called": False,
    }


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print(
        json.dumps(
            validate_deployable_freeze(manifest, root=ROOT),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
