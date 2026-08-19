from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from scripts.inspect_factual_qa_v3_archives import inspect_archives


def target(relative_path: str) -> dict[str, str]:
    return {"source_id": "archive-a", "relative_path": relative_path}


def test_archive_inventory_classifies_entries_and_duplicates(tmp_path: Path) -> None:
    archive_path = tmp_path / "course.zip"
    duplicate = b"duplicate"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("diagram.drawio", "<mxfile />")
        archive.writestr("copy.md", duplicate)
        archive.writestr("answer-key.md", "secret")
        archive.writestr("._diagram", b"\x00\x05\x16\x07Mac OS X metadata")

    entries, summary = inspect_archives(
        tmp_path,
        [target("course.zip")],
        {hashlib.sha256(duplicate).hexdigest()},
    )

    assert summary["archive_safety_gate"] is True
    assert summary["entry_count"] == 4
    assert {entry["source_role"] for entry in entries} == {
        "review_or_conversion_required",
        "excluded_duplicate_generated_tool_state",
        "excluded_integrity_or_privacy",
    }


def test_archive_inventory_rejects_path_traversal(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escape.md", "unsafe")

    entries, summary = inspect_archives(tmp_path, [target("unsafe.zip")], set())

    assert entries == []
    assert summary["unsafe_path_count"] == 1
    assert summary["archive_safety_gate"] is False
