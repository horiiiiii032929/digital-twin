from __future__ import annotations

import hashlib
import json
import zipfile
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


def test_malformed_json_falls_back_to_local_text(tmp_path: Path) -> None:
    (tmp_path / "notes.json").write_text("not valid JSON but readable notes")
    item = disposition(tmp_path, "notes.json", "structured_text")

    private, summary = audit_manifest(manifest(tmp_path, [item]))

    assert summary["local_conversion_gate"] is True
    assert private["records"][0]["conversion_status"] == "ready_local_text"
    assert private["records"][0]["metrics"]["structured_parse_fallback"] == 1


def test_tex_support_and_extensionless_text_use_local_text_path(tmp_path: Path) -> None:
    (tmp_path / "references.bst").write_text("ENTRY { author } {} {}")
    (tmp_path / "README").write_text("Course instructions")
    items = [
        disposition(tmp_path, "references.bst", "other"),
        disposition(tmp_path, "README", "other"),
    ]

    _, summary = audit_manifest(manifest(tmp_path, items))

    assert summary["local_conversion_gate"] is True
    assert summary["status_counts"] == {"ready_local_text": 2}


def test_pages_preview_uses_local_visual_path(tmp_path: Path) -> None:
    preview = tmp_path / "preview.png"
    Image.new("RGB", (5, 4), "white").save(preview)
    pages = tmp_path / "notes.pages"
    with zipfile.ZipFile(pages, "w") as archive:
        archive.write(preview, "QuickLook/Thumbnail.png")

    private, summary = audit_manifest(
        manifest(tmp_path, [disposition(tmp_path, "notes.pages", "office_document")])
    )

    assert summary["local_conversion_gate"] is True
    assert private["records"][0]["conversion_status"] == "ready_local_visual"
