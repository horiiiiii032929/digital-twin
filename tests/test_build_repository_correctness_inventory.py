from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_repository_correctness_inventory import (
    build_inventory,
    require_complete_inventory,
)


def write(root: Path, relative_path: str, content: str = "fixture") -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_inventory_accounts_for_execution_files_and_ignores_prose(tmp_path: Path) -> None:
    paths = [
        "src/pkg/core.py",
        "services/api/main.py",
        "apps/web/src/App.tsx",
        "apps/web/package.json",
        "scripts/historical.py",
        "scripts/ocr.swift",
        "tests/test_core.py",
        "compose.local-r1.yml",
        ".github/workflows/ci.yml",
        "research/05_evaluation/profiles/runtime.json",
        "reports/snapshot/query.sql",
        "uv.lock",
        "docs/readme.md",
    ]
    for path in paths:
        write(tmp_path, path)

    inventory = build_inventory(
        paths,
        {"historical:run": "python -m scripts.historical"},
        root=tmp_path,
    )
    by_path = {record["path"]: record for record in inventory["records"]}

    assert inventory["file_count"] == 12
    assert "docs/readme.md" not in by_path
    assert by_path["src/pkg/core.py"]["category"] == "active_runtime"
    assert by_path["scripts/historical.py"]["category"] == "historical_tooling"
    assert by_path["scripts/ocr.swift"]["category"] == "active_or_unclassified_tooling"
    assert by_path[".github/workflows/ci.yml"]["category"] == "ci_configuration"
    assert by_path["compose.local-r1.yml"]["category"] == "deployment_configuration"
    assert (
        by_path["research/05_evaluation/profiles/runtime.json"]["category"]
        == "evaluation_configuration"
    )
    assert by_path["reports/snapshot/query.sql"]["category"] == "report_artifact"
    assert all(record["audit_status"] == "pending" for record in by_path.values())


def test_inventory_digest_is_deterministic(tmp_path: Path) -> None:
    write(tmp_path, "src/a.py", "print('a')")
    write(tmp_path, "src/b.py", "print('b')")

    first = build_inventory(["src/b.py", "src/a.py"], {}, root=tmp_path)
    second = build_inventory(["src/a.py", "src/b.py"], {}, root=tmp_path)

    assert first == second
    json.dumps(first)


def test_inventory_applies_hash_bound_audit_disposition(tmp_path: Path) -> None:
    write(tmp_path, "src/a.py", "print('a')")
    pending = build_inventory(["src/a.py"], {}, root=tmp_path)
    source_hash = pending["records"][0]["sha256"]

    inventory = build_inventory(
        ["src/a.py"],
        {},
        root=tmp_path,
        audit_records=[
            {
                "path": "src/a.py",
                "sha256": source_hash,
                "audit_status": "audited",
                "disposition": "active_audited",
                "domain": "fixture",
                "reviewed_at": "2026-08-19",
                "reviewer": "test-reviewer",
                "evidence": "focused fixture review",
                "findings": [],
            }
        ],
    )

    assert inventory["audit_status_counts"] == {"audited": 1}
    assert inventory["records"][0]["disposition"] == "active_audited"


def test_inventory_rejects_stale_audit_hash(tmp_path: Path) -> None:
    write(tmp_path, "src/a.py", "print('a')")

    with pytest.raises(ValueError, match="audit hash is stale"):
        build_inventory(
            ["src/a.py"],
            {},
            root=tmp_path,
            audit_records=[
                {
                    "path": "src/a.py",
                    "sha256": "0" * 64,
                    "audit_status": "audited",
                    "disposition": "active_audited",
                    "domain": "fixture",
                    "reviewed_at": "2026-08-19",
                    "reviewer": "test-reviewer",
                    "evidence": "focused fixture review",
                    "findings": [],
                }
            ],
        )


def test_complete_gate_rejects_pending_inventory(tmp_path: Path) -> None:
    write(tmp_path, "src/a.py", "print('a')")
    inventory = build_inventory(["src/a.py"], {}, root=tmp_path)

    with pytest.raises(ValueError, match="1 pending"):
        require_complete_inventory(inventory)
