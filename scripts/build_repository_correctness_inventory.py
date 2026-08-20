#!/usr/bin/env python3
"""Inventory every tracked executable or execution-affecting repository file."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT
    / "research/05_evaluation/instruments/repository_correctness_inventory_v1.json"
)
DEFAULT_AUDIT = (
    ROOT
    / "research/05_evaluation/instruments/repository_correctness_audit_v1.json"
)

AUDIT_STATUSES = {"audited", "finding_open"}
FINAL_DISPOSITIONS = {
    "active_audited",
    "historical_guarded",
    "refactor_required",
    "remove",
}

CODE_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".jsx",
    ".mjs",
    ".py",
    ".sh",
    ".sql",
    ".swift",
    ".ts",
    ".tsx",
}
EXECUTION_CONFIG_NAMES = {
    ".dockerignore",
    ".env.example",
    ".gitignore",
    ".node-version",
    ".python-version",
    "compose.staging.yml",
    "package-lock.json",
    "package.json",
    "pyproject.toml",
    "uv.lock",
}
EXECUTION_CONFIG_PREFIXES = (
    ".github/workflows/",
    "deploy/",
)
EXECUTION_CONFIG_SUFFIXES = {
    ".json",
    ".toml",
    ".yaml",
    ".yml",
}
META_INVENTORY_PATHS = {
    "research/05_evaluation/instruments/repository_correctness_audit_v1.json",
    "research/05_evaluation/instruments/repository_correctness_inventory_v1.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repository_paths(root: Path = ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return sorted(
        path
        for path in result.stdout.decode().split("\0")
        if path and (root / path).is_file()
    )


def is_execution_file(path: str) -> bool:
    candidate = Path(path)
    if path in META_INVENTORY_PATHS:
        return False
    if candidate.suffix.casefold() in CODE_SUFFIXES:
        return True
    if candidate.name.startswith("Dockerfile"):
        return True
    if path in EXECUTION_CONFIG_NAMES:
        return True
    if candidate.name in {"package.json", ".oxlintrc.json"}:
        return True
    if candidate.name.startswith("tsconfig") and candidate.suffix == ".json":
        return True
    if path.endswith(".ipynb"):
        return True
    if path.startswith("deploy/"):
        return True
    if path.startswith(
        (
            "research/05_evaluation/instruments/",
            "research/05_evaluation/profiles/",
        )
    ):
        return True
    if path.startswith("research/05_evaluation/") and candidate.name.endswith(
        (".schema.json", ".manifest.json", "_freeze.json")
    ):
        return True
    return path.startswith(EXECUTION_CONFIG_PREFIXES) and (
        candidate.suffix.casefold() in EXECUTION_CONFIG_SUFFIXES
        or candidate.name.startswith("Dockerfile")
    )


def script_command_names(path: str, commands: dict[str, str]) -> list[str]:
    module = path.removesuffix(".py").replace("/", ".")
    filename = Path(path).name
    return sorted(
        name
        for name, command in commands.items()
        if module in command or filename in command
    )


def classify(path: str, commands: dict[str, str]) -> tuple[str, str, list[str]]:
    command_names: list[str] = []
    if path.startswith("tests/"):
        return "verification", "medium", command_names
    if path.startswith(("src/", "services/")):
        return "active_runtime", "high", command_names
    if path.startswith("apps/"):
        return "active_frontend", "high", command_names
    if path.startswith("scripts/"):
        command_names = script_command_names(path, commands)
        if command_names and all(name.startswith("historical:") for name in command_names):
            return "historical_tooling", "high", command_names
        if command_names and all(
            name.startswith(("historical:", "deferred:")) for name in command_names
        ):
            return "deferred_tooling", "high", command_names
        return "active_or_unclassified_tooling", "high", command_names
    if path.startswith("reports/"):
        return "report_artifact", "medium", command_names
    if path.startswith(
        (
            "research/05_evaluation/instruments/",
            "research/05_evaluation/profiles/",
        )
    ) or path.startswith("research/05_evaluation/"):
        return "evaluation_configuration", "high", command_names
    if path.endswith(".ipynb"):
        return "executable_notebook", "high", command_names
    if path.startswith(".github/workflows/"):
        return "ci_configuration", "high", command_names
    if path.startswith("deploy/") or path.startswith("compose"):
        return "deployment_configuration", "high", command_names
    if path.endswith(".sql"):
        return "runtime_migration", "high", command_names
    return "execution_configuration", "medium", command_names


def build_inventory(
    paths: Iterable[str],
    commands: dict[str, str],
    *,
    root: Path = ROOT,
    audit_records: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in sorted(set(paths)):
        if not is_execution_file(path):
            continue
        category, risk, command_names = classify(path, commands)
        records.append(
            {
                "path": path,
                "sha256": sha256_file(root / path),
                "category": category,
                "risk": risk,
                "package_commands": command_names,
                "audit_status": "pending",
                "disposition": "review_required",
            }
        )

    records_by_path = {record["path"]: record for record in records}
    seen_audit_paths: set[str] = set()
    for audit in audit_records:
        path = audit.get("path")
        if not isinstance(path, str) or path not in records_by_path:
            raise ValueError(f"audit record references unknown execution file: {path!r}")
        if path in seen_audit_paths:
            raise ValueError(f"duplicate audit record: {path}")
        seen_audit_paths.add(path)
        record = records_by_path[path]
        if audit.get("sha256") != record["sha256"]:
            raise ValueError(f"audit hash is stale for {path}")
        status = audit.get("audit_status")
        disposition = audit.get("disposition")
        if status not in AUDIT_STATUSES:
            raise ValueError(f"invalid audit status for {path}: {status!r}")
        if disposition not in FINAL_DISPOSITIONS:
            raise ValueError(f"invalid disposition for {path}: {disposition!r}")
        if status == "audited" and disposition not in {
            "active_audited",
            "historical_guarded",
        }:
            raise ValueError(f"audited file has unresolved disposition: {path}")
        if status == "finding_open" and disposition not in {
            "refactor_required",
            "remove",
        }:
            raise ValueError(f"open finding lacks a corrective disposition: {path}")
        required_text = ("domain", "reviewed_at", "reviewer", "evidence")
        for field in required_text:
            if not isinstance(audit.get(field), str) or not audit[field].strip():
                raise ValueError(f"audit record for {path} lacks {field}")
        findings = audit.get("findings")
        if not isinstance(findings, list) or any(
            not isinstance(item, str) or not item.strip() for item in findings
        ):
            raise ValueError(f"audit findings must be a string list for {path}")
        if status == "audited" and findings:
            raise ValueError(f"audited file retains unresolved findings: {path}")
        if status == "finding_open" and not findings:
            raise ValueError(f"open finding record has no findings: {path}")
        record.update(
            {
                "audit_status": status,
                "disposition": disposition,
                "audit": {
                    "domain": audit["domain"],
                    "reviewed_at": audit["reviewed_at"],
                    "reviewer": audit["reviewer"],
                    "evidence": audit["evidence"],
                    "findings": findings,
                },
            }
        )

    record_digest = hashlib.sha256(
        json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schema_version": 1,
        "inventory_id": "repository-correctness-inventory-v1",
        "scope": "all tracked executable and execution-affecting files",
        "record_sha256": record_digest,
        "file_count": len(records),
        "category_counts": dict(sorted(Counter(r["category"] for r in records).items())),
        "risk_counts": dict(sorted(Counter(r["risk"] for r in records).items())),
        "audit_status_counts": dict(
            sorted(Counter(r["audit_status"] for r in records).items())
        ),
        "model_or_provider_called": False,
        "private_or_heldout_data_read": False,
        "records": records,
    }


def load_package_commands(root: Path = ROOT) -> dict[str, str]:
    package = json.loads((root / "package.json").read_text())
    return package.get("scripts", {})


def load_audit_records(path: Path = DEFAULT_AUDIT) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    value = json.loads(path.read_text())
    if value.get("schema_version") != 1:
        raise ValueError("repository correctness audit schema version must be 1")
    if value.get("inventory_id") != "repository-correctness-inventory-v1":
        raise ValueError("repository correctness audit inventory ID mismatch")
    records = value.get("records")
    if not isinstance(records, list):
        raise ValueError("repository correctness audit records must be a list")
    return records


def require_complete_inventory(inventory: dict[str, Any]) -> None:
    pending = inventory["audit_status_counts"].get("pending", 0)
    open_findings = inventory["audit_status_counts"].get("finding_open", 0)
    if pending or open_findings:
        raise ValueError(
            "repository correctness audit is incomplete: "
            f"{pending} pending, {open_findings} finding_open"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare the current inventory with the existing output without writing.",
    )
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Fail unless every inventoried file has a resolved audit record.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = build_inventory(
        repository_paths(),
        load_package_commands(),
        audit_records=load_audit_records(args.audit),
    )
    if args.require_complete:
        require_complete_inventory(inventory)
    if args.check:
        if not args.output.exists():
            raise SystemExit(f"missing repository correctness inventory: {args.output}")
        existing = json.loads(args.output.read_text())
        if existing != inventory:
            raise SystemExit("repository correctness inventory is stale")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "inventory_id": inventory["inventory_id"],
                "file_count": inventory["file_count"],
                "category_counts": inventory["category_counts"],
                "audit_status_counts": inventory["audit_status_counts"],
                "status": "inventory-current" if args.check else "inventory-written",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
