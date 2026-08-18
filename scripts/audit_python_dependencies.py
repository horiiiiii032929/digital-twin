#!/usr/bin/env python3
"""Audit the complete Python lock and enforce reviewed vulnerability policy."""

from __future__ import annotations

import json
import subprocess
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = (
    ROOT
    / "research/05_evaluation/instruments/dependency_vulnerability_exceptions_v1.json"
)

FindingKey = tuple[str, str, str, tuple[str, ...]]


def finding_key(
    package: str, version: str, advisory_id: str, fix_versions: list[str]
) -> FindingKey:
    return (
        package.lower(),
        version,
        advisory_id,
        tuple(sorted(fix_versions)),
    )


def audit_findings(report: dict[str, Any]) -> Counter[FindingKey]:
    findings: Counter[FindingKey] = Counter()
    for dependency in report.get("dependencies", []):
        for vulnerability in dependency.get("vulns", []):
            findings[
                finding_key(
                    dependency["name"],
                    dependency["version"],
                    vulnerability["id"],
                    vulnerability.get("fix_versions", []),
                )
            ] += 1
    return findings


def policy_findings(policy: dict[str, Any]) -> Counter[FindingKey]:
    findings: Counter[FindingKey] = Counter()
    for exception in policy.get("exceptions", []):
        findings[
            finding_key(
                exception["package"],
                exception["version"],
                exception["advisory_id"],
                exception.get("fix_versions", []),
            )
        ] += 1
    return findings


def serialize_counter(findings: Counter[FindingKey]) -> list[dict[str, Any]]:
    return [
        {
            "package": package,
            "version": version,
            "advisory_id": advisory_id,
            "fix_versions": list(fix_versions),
            "occurrences": occurrences,
        }
        for (package, version, advisory_id, fix_versions), occurrences in sorted(
            findings.items()
        )
    ]


def evaluate_policy(
    report: dict[str, Any],
    policy: dict[str, Any],
    *,
    today: date | None = None,
) -> dict[str, Any]:
    observed = audit_findings(report)
    reviewed = policy_findings(policy)
    unexpected = observed - reviewed
    stale = reviewed - observed
    review_by = date.fromisoformat(policy["review_by"])
    expired = review_by < (today or date.today())
    status = "passed" if not observed else "passed-with-reviewed-exceptions"
    if unexpected or stale or expired:
        status = "failed"
    return {
        "status": status,
        "policy_id": policy.get("policy_id"),
        "review_by": review_by.isoformat(),
        "policy_expired": expired,
        "finding_count": sum(observed.values()),
        "reviewed_exception_count": sum((observed & reviewed).values()),
        "unexpected_findings": serialize_counter(unexpected),
        "stale_exceptions": serialize_counter(stale),
    }


def main() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="digital-twin-python-audit-") as temp:
        temp_path = Path(temp)
        requirements = temp_path / "requirements.txt"
        report_path = temp_path / "pip-audit.json"
        subprocess.run(
            [
                "uv",
                "export",
                "--locked",
                "--all-extras",
                "--all-groups",
                "--no-emit-project",
                "--no-hashes",
                "--quiet",
                "--output-file",
                str(requirements),
            ],
            cwd=ROOT,
            check=True,
        )
        audit = subprocess.run(
            [
                "pip-audit",
                "--requirement",
                str(requirements),
                "--no-deps",
                "--disable-pip",
                "--progress-spinner",
                "off",
                "--format",
                "json",
                "--output",
                str(report_path),
            ],
            cwd=ROOT,
            check=False,
        )
        if audit.returncode not in (0, 1):
            raise SystemExit(f"pip-audit failed with exit code {audit.returncode}")
        report = json.loads(report_path.read_text(encoding="utf-8"))

    result = evaluate_policy(report, policy)
    print(json.dumps(result, indent=2))
    if result["status"] == "failed":
        raise SystemExit("Python dependency audit policy failed")


if __name__ == "__main__":
    main()
