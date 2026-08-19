from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

from scripts.audit_factual_qa_v3_conversion_readiness import audit_manifest


def disposition(root: Path, relative: str, format_group: str) -> dict[str, object]:
    path = root / relative
    return {
        "source_id": relative,
        "relative_path": relative,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "course_id": "TEST",
        "format_group": format_group,
        "requires_explicit_review": True,
    }


def manifest(root: Path, items: list[dict[str, object]]) -> dict[str, object]:
    return {
        "manifest_id": "fixture-v2",
        "disposition_sha256": "fixture-sha",
        "source_root": str(root),
        "dispositions": items,
    }


def test_audit_accepts_local_text_structured_and_visual_sources(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text("Evidence text")
    (tmp_path / "data.json").write_text(json.dumps({"fact": 1}))
    image = Image.new("RGB", (4, 3), "white")
    image.save(tmp_path / "figure.png")
    items = [
        disposition(tmp_path, "note.md", "text"),
        disposition(tmp_path, "data.json", "structured_text"),
        disposition(tmp_path, "figure.png", "raster_image"),
    ]

    private, summary = audit_manifest(manifest(tmp_path, items))

    assert summary["integrity_gate"] is True
    assert summary["local_conversion_gate"] is True
    assert summary["contains_private_paths"] is False
    assert {item["conversion_status"] for item in private["records"]} == {
        "ready_local_text",
        "ready_local_structured",
        "ready_local_visual",
    }


def test_hash_drift_fails_integrity_gate(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    path.write_text("before")
    item = disposition(tmp_path, "note.md", "text")
    path.write_text("after")

    _, summary = audit_manifest(manifest(tmp_path, [item]))

    assert summary["integrity_gate"] is False
    assert summary["status_counts"] == {"hash_mismatch": 1}


def test_empty_and_unsupported_sources_fail_conversion_gate(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").write_text("")
    (tmp_path / "archive.zip").write_bytes(b"not inspected")
    items = [
        disposition(tmp_path, "empty.txt", "text"),
        disposition(tmp_path, "archive.zip", "archive"),
    ]

    _, summary = audit_manifest(manifest(tmp_path, items))

    assert summary["integrity_gate"] is True
    assert summary["local_conversion_gate"] is False
    assert summary["status_counts"] == {"empty_source": 1, "unsupported_format": 1}
