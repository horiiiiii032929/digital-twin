#!/usr/bin/env python3
"""Validate the versioned technical evidence freeze and its bound artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from src.digital_twin.evaluation import ComponentStatus, load_release_profile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT
    / "research/05_evaluation/profiles/technical-evidence-freeze-v1.json"
)
EXPECTED_BOUNDARIES = {
    "cross-course-retrieval": "pass-experimental",
    "professor-fidelity": "fail-refine-paused",
    "pedagogy": "unresolved",
    "synthetic-journeys": "pass-bounded",
    "isolation": "pass-bounded",
    "recovery": "partial",
    "capacity": "not-established",
    "cost": "partial",
    "local-deployment-packaging": "not-established",
}
EXPECTED_CLAIMS = {
    "C01": "supported-bounded",
    "C02": "supported",
    "C03": "supported-experimental",
    "C04": "supported",
    "C05": "supported-bounded",
    "C06": "supported-bounded",
    "C07": "supported-negative-result",
    "C08": "demonstration-verified-not-research-claim",
    "U01": "unsupported-refine-paused",
    "U02": "unsupported",
    "U03": "unsupported-text-only-rollback",
    "U04": "unsupported",
    "U05": "unsupported",
    "U06": "unsupported",
    "U07": "rejected-wording",
}
REGISTRY_PATH = "research/05_evaluation/result-registry.md"
REGISTRY_ROW_PATTERN = re.compile(r"^\| `([^`]+)` \|.*$", re.MULTILINE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def registered_result_ids(root: Path) -> set[str]:
    text = (root / "research/05_evaluation/result-registry.md").read_text(
        encoding="utf-8"
    )
    return set(re.findall(r"^\| `([^`]+)` \|", text, flags=re.MULTILINE))


def validate_registry_extension(frozen_text: str, current_text: str) -> None:
    """Allow new registry rows while preserving every frozen row exactly."""

    def rows(text: str) -> dict[str, str]:
        matches = REGISTRY_ROW_PATTERN.findall(text)
        if len(matches) != len(set(matches)):
            raise ValueError("evaluation registry contains duplicate result IDs")
        return {
            match.group(1): match.group(0)
            for match in REGISTRY_ROW_PATTERN.finditer(text)
        }

    frozen_rows = rows(frozen_text)
    current_rows = rows(current_text)
    changed = [
        result_id
        for result_id, frozen_row in frozen_rows.items()
        if current_rows.get(result_id) != frozen_row
    ]
    if changed:
        raise ValueError(
            "frozen evaluation registry rows drifted: " + ", ".join(changed)
        )


def frozen_repository_file(
    root: Path, revision: str, relative_path: str
) -> bytes:
    """Read one tracked file from the freeze's recorded evidence revision."""
    return subprocess.run(
        ["git", "show", f"{revision}:{relative_path}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def validate_freeze(manifest: dict[str, Any], *, root: Path) -> dict[str, Any]:
    if manifest.get("freeze_id") != "technical-evidence-freeze-v1":
        raise ValueError("unexpected technical freeze identifier")
    if manifest.get("status") != "frozen-experimental-not-release-candidate":
        raise ValueError("technical freeze must remain experimental")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("evidence_base_revision", "")):
        raise ValueError("evidence base revision must be a full Git revision")
    if manifest.get("private_or_heldout_data_read") is not False:
        raise ValueError("freeze validation cannot read private or held-out data")
    if manifest.get("external_model_called") is not False:
        raise ValueError("freeze validation cannot call an external model")

    artifact_paths: set[str] = set()
    for binding in manifest.get("artifact_bindings", []):
        relative_path = binding["path"]
        if relative_path in artifact_paths:
            raise ValueError(f"duplicate freeze artifact binding: {relative_path}")
        artifact_paths.add(relative_path)
        path = _repository_file(root, relative_path)
        if relative_path == REGISTRY_PATH:
            frozen_bytes = frozen_repository_file(
                root,
                manifest["evidence_base_revision"],
                relative_path,
            )
            if hashlib.sha256(frozen_bytes).hexdigest() != binding["sha256"]:
                raise ValueError(f"freeze artifact hash mismatch: {relative_path}")
            validate_registry_extension(
                frozen_bytes.decode("utf-8"),
                path.read_text(encoding="utf-8"),
            )
        elif sha256(path) != binding["sha256"]:
            raise ValueError(f"freeze artifact hash mismatch: {relative_path}")

    profile_contract = manifest["profile"]
    profile = load_release_profile(_repository_file(root, profile_contract["path"]))
    counts = {
        status.value: sum(entry.status == status for entry in profile.components)
        for status in ComponentStatus
    }
    if profile.stage.value != "experimental":
        raise ValueError("frozen profile must remain experimental")
    if (
        profile.profile_id != profile_contract["profile_id"]
        or profile.profile_version != profile_contract["profile_version"]
        or profile.stage.value != profile_contract["stage"]
        or counts["selected"] != profile_contract["selected_components"]
        or counts["pending"] != profile_contract["pending_components"]
        or counts["disabled"] != profile_contract["disabled_components"]
    ):
        raise ValueError("frozen profile identity or status counts drifted")

    required_entries = {
        entry.component.value: entry
        for entry in profile.components
        if entry.status in {ComponentStatus.SELECTED, ComponentStatus.DISABLED}
    }
    frozen_entries = {
        entry["component"]: entry for entry in manifest.get("component_evidence", [])
    }
    if len(frozen_entries) != len(manifest.get("component_evidence", [])):
        raise ValueError("component evidence inventory contains duplicates")
    if set(required_entries) != set(frozen_entries):
        raise ValueError("selected/disabled component freeze coverage is incomplete")

    registry_ids = registered_result_ids(root)
    for component, profile_entry in required_entries.items():
        frozen_entry = frozen_entries[component]
        if frozen_entry["status"] != profile_entry.status.value:
            raise ValueError(f"component status drifted: {component}")
        if not profile_entry.result_ids:
            raise ValueError(f"selected/disabled component has no result: {component}")
        if frozen_entry["result_ids"] != profile_entry.result_ids:
            raise ValueError(f"component result links drifted: {component}")
        unknown = set(profile_entry.result_ids) - registry_ids
        if unknown:
            raise ValueError(f"component references unregistered results: {component}")

    claims = manifest.get("claims", [])
    claim_ids = [claim["claim_id"] for claim in claims]
    if len(claim_ids) != len(set(claim_ids)) or set(claim_ids) != set(EXPECTED_CLAIMS):
        raise ValueError("technical freeze claim inventory is incomplete or duplicated")
    for claim in claims:
        unknown = set(claim.get("result_ids", [])) - registry_ids
        if unknown:
            raise ValueError(f"claim references unregistered results: {claim['claim_id']}")
        if claim["status"] != EXPECTED_CLAIMS[claim["claim_id"]]:
            raise ValueError(f"frozen claim status drifted: {claim['claim_id']}")

    claim_matrix = (
        root / "reports/claim-to-evidence-matrix.md"
    ).read_text(encoding="utf-8")
    matrix_ids = set(
        re.findall(r"^\| `(C\d{2}|U\d{2})` \|", claim_matrix, re.MULTILINE)
    )
    if matrix_ids != set(EXPECTED_CLAIMS):
        raise ValueError("claim matrix does not match the frozen claim inventory")

    boundaries = manifest.get("required_boundaries", [])
    boundary_names = [boundary["boundary"] for boundary in boundaries]
    if len(boundary_names) != len(set(boundary_names)) or set(
        boundary_names
    ) != set(EXPECTED_BOUNDARIES):
        raise ValueError("required technical boundary inventory is incomplete")
    for boundary in boundaries:
        if boundary["disposition"] != EXPECTED_BOUNDARIES[boundary["boundary"]]:
            raise ValueError(f"technical boundary disposition drifted: {boundary['boundary']}")

    professor_policy = json.loads(
        (
            root
            / "research/05_evaluation/instruments/professor_fidelity_execution_policy_v1.json"
        ).read_text(encoding="utf-8")
    )
    if (
        professor_policy.get("status") != "paused"
        or professor_policy["splits"]["development"]["authorized"] is not False
        or professor_policy["splits"]["heldout"]["authorized"] is not False
    ):
        raise ValueError("professor-fidelity execution boundary is no longer paused")

    required_commands = {
        "uv sync --locked --dev",
        "npm ci",
        "npm run audit:dependencies",
        "npm run verify:technical-freeze",
        "npm run check",
    }
    if set(manifest.get("reproduction_commands", [])) != required_commands:
        raise ValueError("technical freeze reproduction commands drifted")
    package_scripts = json.loads(
        (root / "package.json").read_text(encoding="utf-8")
    )["scripts"]
    if package_scripts.get("verify:technical-freeze") != (
        "uv run python -m scripts.validate_technical_freeze"
    ) or "npm run verify:technical-freeze" not in package_scripts.get("check", ""):
        raise ValueError("technical freeze command is absent from the required checks")
    if not manifest.get("rollbacks") or not manifest.get("change_control"):
        raise ValueError("technical freeze must preserve rollback and change control")

    demo_qa = manifest.get("demo_qa", {})
    if (
        demo_qa.get("status") != "passed-after-same-origin-api-repair"
        or demo_qa.get("desktop_console_errors") != 0
        or demo_qa.get("mobile_console_errors") != 0
        or demo_qa.get("professor_report_console_errors") != 0
        or demo_qa.get("research_claim") is not False
    ):
        raise ValueError("rendered demo QA boundary drifted")

    return {
        "status": "passed",
        "freeze_id": manifest["freeze_id"],
        "profile": f"{profile.profile_id}@{profile.profile_version}",
        "profile_stage": profile.stage.value,
        "component_status_counts": counts,
        "registered_component_links": len(required_entries),
        "claims": len(claims),
        "required_boundaries": len(boundaries),
        "artifact_bindings": len(artifact_paths),
        "private_or_heldout_data_read": False,
        "external_model_called": False,
    }


def _repository_file(root: Path, relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("freeze paths must remain relative to the repository")
    resolved = root / path
    if not resolved.is_file():
        raise ValueError(f"freeze artifact does not exist: {relative_path}")
    return resolved


def main() -> None:
    manifest = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    print(json.dumps(validate_freeze(manifest, root=ROOT), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
