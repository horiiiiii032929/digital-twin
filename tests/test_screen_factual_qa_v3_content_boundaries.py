from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.screen_factual_qa_v3_content_boundaries import screen_records


def source(root: Path, name: str, content: str, format_group: str = "text") -> dict:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return {
        "source_id": name,
        "relative_path": name,
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
        "format_group": format_group,
        "course_id": "TEST1000",
        "requires_explicit_review": True,
    }


def test_screen_routes_sensitive_signals_without_assigning_final_roles(
    tmp_path: Path,
) -> None:
    manifest = {
        "manifest_id": "source-roles",
        "record_sha256": "roles",
        "source_root": str(tmp_path),
        "dispositions": [
            source(tmp_path, "notes.txt", "Lecture notes about trees."),
            source(tmp_path, "submission.txt", "Student ID: A1234567. Final answer below."),
            source(tmp_path, "config.py", "api_key = 'synthetic-placeholder'", "code"),
        ],
    }

    private, summary = screen_records(manifest)
    by_id = {record["source_id"]: record for record in private["records"]}

    assert summary["candidate_count"] == 3
    assert summary["physical_integrity_gate"] is True
    assert summary["semantic_eligibility_gate"] is False
    assert summary["contains_paths"] is False
    assert by_id["notes.txt"]["recommended_review_route"] == "semantic_role_review"
    assert by_id["submission.txt"]["recommended_review_route"] == (
        "privacy_or_integrity_review"
    )
    assert by_id["config.py"]["recommended_review_route"] == (
        "mandatory_exclusion_review"
    )
    assert all(record["final_source_role"] is None for record in private["records"])


def test_screen_fails_physical_gate_on_hash_drift(tmp_path: Path) -> None:
    record = source(tmp_path, "notes.txt", "original")
    (tmp_path / "notes.txt").write_text("changed")
    manifest = {
        "manifest_id": "source-roles",
        "record_sha256": "roles",
        "source_root": str(tmp_path),
        "dispositions": [record],
    }

    private, summary = screen_records(manifest)

    assert summary["physical_integrity_gate"] is False
    assert private["records"][0]["extraction_status"] == "missing_or_hash_mismatch"
