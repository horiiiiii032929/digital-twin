#!/usr/bin/env python3
"""Inspect eligible archive containers without extracting private content."""

from __future__ import annotations

import hashlib
import json
import re
import stat
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DISPOSITIONS = ROOT / "data/interim/factual_qa_v3/source_dispositions_v3.json"
READINESS = ROOT / "data/interim/factual_qa_v3/conversion_readiness_v3.json"
PRIVATE_OUTPUT = ROOT / "data/interim/factual_qa_v3/archive_inventory_v1.json"
SUMMARY_OUTPUT = ROOT / "reports/generated/factual-qa-v3-archive-inventory-v1.json"
EXCLUSION_PATTERN = re.compile(
    r"solution|answer.?key|submission|graded|completed.?exam|completed.?quiz",
    re.IGNORECASE,
)
FORMAT_BY_SUFFIX = {
    ".drawio": "diagram",
    ".md": "text",
    ".png": "raster_image",
    ".jpg": "raster_image",
    ".jpeg": "raster_image",
    ".pdf": "pdf",
    ".csv": "structured_table",
    ".json": "structured_text",
}


def inspect_archives(
    source_root: Path,
    targets: list[dict[str, Any]],
    existing_hashes: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    unsafe = encrypted = symlinks = errors = 0
    for target in targets:
        archive_path = source_root / target["relative_path"]
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    inner = PurePosixPath(info.filename)
                    is_unsafe = inner.is_absolute() or ".." in inner.parts
                    is_encrypted = bool(info.flag_bits & 1)
                    mode = info.external_attr >> 16
                    is_symlink = stat.S_ISLNK(mode)
                    unsafe += int(is_unsafe)
                    encrypted += int(is_encrypted)
                    symlinks += int(is_symlink)
                    if is_unsafe or is_encrypted or is_symlink:
                        continue
                    content = archive.read(info)
                    content_hash = hashlib.sha256(content).hexdigest()
                    suffix = Path(info.filename).suffix.lower()
                    excluded = bool(EXCLUSION_PATTERN.search(info.filename))
                    duplicate = content_hash in existing_hashes
                    role = (
                        "excluded_integrity_or_privacy"
                        if excluded
                        else "excluded_duplicate_generated_tool_state"
                        if duplicate or content.startswith(b"\x00\x05\x16\x07")
                        else "review_or_conversion_required"
                    )
                    entries.append(
                        {
                            "archive_source_id": target["source_id"],
                            "inner_path": info.filename,
                            "sha256": content_hash,
                            "bytes": len(content),
                            "format_group": FORMAT_BY_SUFFIX.get(suffix, "other"),
                            "source_role": role,
                        }
                    )
                    existing_hashes.add(content_hash)
        except (OSError, zipfile.BadZipFile, RuntimeError):
            errors += 1
    role_counts = Counter(entry["source_role"] for entry in entries)
    format_counts = Counter(entry["format_group"] for entry in entries)
    summary = {
        "archive_count": len(targets),
        "entry_count": len(entries),
        "entry_bytes": sum(entry["bytes"] for entry in entries),
        "source_role_counts": dict(sorted(role_counts.items())),
        "format_counts": dict(sorted(format_counts.items())),
        "unsafe_path_count": unsafe,
        "encrypted_entry_count": encrypted,
        "symlink_entry_count": symlinks,
        "archive_error_count": errors,
        "archive_safety_gate": unsafe == encrypted == symlinks == errors == 0,
    }
    return entries, summary


def main() -> int:
    dispositions = json.loads(DISPOSITIONS.read_text())
    readiness = json.loads(READINESS.read_text())
    targets = [
        record
        for record in readiness["records"]
        if record["conversion_status"] == "unsupported_format"
        and record["format_group"] == "archive"
    ]
    entries, aggregate = inspect_archives(
        Path(dispositions["source_root"]),
        targets,
        {record["sha256"] for record in dispositions["dispositions"]},
    )
    record_sha = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    now = datetime.now(UTC).isoformat()
    private = {
        "schema_version": 1,
        "run_id": "factual-qa-v3-archive-inventory-v1",
        "generated_at": now,
        "conversion_record_sha256": readiness["record_sha256"],
        "record_sha256": record_sha,
        "entries": entries,
    }
    summary = {
        "schema_version": 1,
        "run_id": private["run_id"],
        "generated_at": now,
        "conversion_record_sha256": readiness["record_sha256"],
        "record_sha256": record_sha,
        **aggregate,
        "contains_private_paths": False,
        "contains_source_content": False,
        "external_provider_calls": 0,
        "model_calls": 0,
        "cost_usd": 0,
    }
    PRIVATE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE_OUTPUT.write_text(json.dumps(private, indent=2, sort_keys=True) + "\n")
    SUMMARY_OUTPUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
