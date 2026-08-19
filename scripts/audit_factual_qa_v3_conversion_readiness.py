#!/usr/bin/env python3
"""Audit private factual-QA sources for integrity and local conversion readiness."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
import tomllib
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pymupdf as fitz
from PIL import Image


fitz.TOOLS.mupdf_display_errors(False)
fitz.TOOLS.mupdf_display_warnings(False)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data/interim/factual_qa_v3/source_dispositions_v3.json"
DEFAULT_PRIVATE_OUTPUT = ROOT / "data/interim/factual_qa_v3/conversion_readiness_v3.json"
DEFAULT_SUMMARY_OUTPUT = ROOT / "reports/generated/factual-qa-v3-conversion-readiness-v3.json"


READY_STATUSES = {
    "ready_local_text",
    "ready_local_structured",
    "ready_local_pdf_text",
    "ready_local_visual",
}
INTEGRITY_FAILURES = {
    "missing_source",
    "not_regular_file",
    "symlink_source",
    "path_escape",
    "hash_mismatch",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def decode_nonempty(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text


def probe_conversion(path: Path, format_group: str) -> tuple[str, dict[str, int]]:
    metrics: dict[str, int] = {}
    try:
        if path.stat().st_size == 0:
            return "empty_source", metrics
        if format_group in {"code", "text", "typeset_source"}:
            text = decode_nonempty(path)
            if not text.strip():
                return "empty_source", metrics
            metrics["character_count"] = len(text)
            return "ready_local_text", metrics
        if format_group == "structured_text":
            text = decode_nonempty(path)
            suffix = path.suffix.lower()
            if suffix == ".json":
                try:
                    json.loads(text)
                except json.JSONDecodeError:
                    metrics["structured_parse_fallback"] = 1
                    metrics["character_count"] = len(text)
                    return "ready_local_text", metrics
            elif suffix == ".toml":
                tomllib.loads(text)
            metrics["character_count"] = len(text)
            return "ready_local_structured", metrics
        if format_group == "structured_table":
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.reader(handle))
            if not rows:
                return "empty_source", metrics
            metrics["row_count"] = len(rows)
            metrics["max_column_count"] = max(len(row) for row in rows)
            return "ready_local_structured", metrics
        if format_group == "notebook":
            payload = json.loads(path.read_text(encoding="utf-8"))
            cells = payload.get("cells")
            if not isinstance(cells, list):
                return "invalid_source", metrics
            metrics["cell_count"] = len(cells)
            return "ready_local_structured", metrics
        if format_group == "diagram":
            root = ElementTree.parse(path).getroot()
            metrics["xml_node_count"] = sum(1 for _ in root.iter())
            return "ready_local_structured", metrics
        if format_group == "pdf":
            with fitz.open(path) as document:
                if document.page_count == 0:
                    return "empty_source", metrics
                text_chars = sum(len(page.get_text()) for page in document)
                metrics["page_count"] = document.page_count
                metrics["extracted_character_count"] = text_chars
            if text_chars == 0:
                return "needs_ocr", metrics
            return "ready_local_pdf_text", metrics
        if format_group == "raster_image":
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                metrics["width"] = image.width
                metrics["height"] = image.height
            return "ready_local_visual", metrics
        if format_group == "vector_image" and path.suffix.lower() == ".eps":
            completed = subprocess.run(
                ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
            return ("ready_local_visual" if completed.returncode == 0 else "needs_vector_conversion"), metrics
        if format_group == "office_document":
            if path.suffix.lower() == ".docx":
                with zipfile.ZipFile(path) as archive:
                    if "word/document.xml" not in archive.namelist():
                        return "invalid_source", metrics
            if path.suffix.lower() == ".pages":
                with zipfile.ZipFile(path) as archive:
                    previews = [
                        name
                        for name in archive.namelist()
                        if name.lower().endswith((".png", ".jpg", ".jpeg"))
                    ]
                    if previews:
                        with Image.open(io.BytesIO(archive.read(previews[0]))) as image:
                            image.verify()
                        metrics["preview_count"] = len(previews)
                        return "ready_local_visual", metrics
            completed = subprocess.run(
                ["textutil", "-convert", "txt", "-stdout", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode == 0 and completed.stdout.strip():
                metrics["character_count"] = len(completed.stdout)
                return "ready_local_text", metrics
            return "needs_office_conversion", metrics
        if format_group == "other":
            suffix = path.suffix.lower()
            if suffix in {".bst", ".cls"} or not suffix:
                text = decode_nonempty(path)
                if not text.strip():
                    return "empty_source", metrics
                metrics["character_count"] = len(text)
                return "ready_local_text", metrics
            if suffix == ".ico":
                with Image.open(path) as image:
                    image.verify()
                return "ready_local_visual", metrics
        return "unsupported_format", metrics
    except UnicodeDecodeError:
        return "needs_encoding_conversion", metrics
    except (csv.Error, fitz.FileDataError, json.JSONDecodeError, OSError, tomllib.TOMLDecodeError, ValueError, zipfile.BadZipFile, ElementTree.ParseError):
        return "invalid_source", metrics


def audit_manifest(manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    source_root = Path(manifest["source_root"]).resolve()
    pending = [item for item in manifest["dispositions"] if item["requires_explicit_review"]]
    records: list[dict[str, Any]] = []
    for item in pending:
        source_path = source_root / item["relative_path"]
        status: str
        metrics: dict[str, int] = {}
        if source_path.is_symlink():
            status = "symlink_source"
        else:
            resolved = source_path.resolve()
            if not resolved.is_relative_to(source_root):
                status = "path_escape"
            elif not resolved.exists():
                status = "missing_source"
            elif not resolved.is_file():
                status = "not_regular_file"
            elif sha256_file(resolved) != item["sha256"]:
                status = "hash_mismatch"
            else:
                status, metrics = probe_conversion(resolved, item["format_group"])
        records.append(
            {
                "source_id": item["source_id"],
                "relative_path": item["relative_path"],
                "sha256": item["sha256"],
                "course_id": item["course_id"],
                "format_group": item["format_group"],
                "conversion_status": status,
                "metrics": metrics,
            }
        )

    status_counts = Counter(record["conversion_status"] for record in records)
    by_format: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        by_format[record["format_group"]][record["conversion_status"]] += 1
    record_sha = canonical_sha256(records)
    now = datetime.now(UTC).isoformat()
    private = {
        "schema_version": 1,
        "audit_id": "factual-qa-v3-conversion-readiness-v3",
        "generated_at": now,
        "source_disposition_manifest_id": manifest["manifest_id"],
        "source_disposition_sha256": manifest["disposition_sha256"],
        "source_root": str(source_root),
        "record_sha256": record_sha,
        "records": records,
    }
    summary = {
        "schema_version": 1,
        "audit_id": private["audit_id"],
        "generated_at": now,
        "source_disposition_manifest_id": manifest["manifest_id"],
        "source_disposition_sha256": manifest["disposition_sha256"],
        "record_sha256": record_sha,
        "source_count": len(records),
        "status_counts": dict(sorted(status_counts.items())),
        "status_by_format": {
            key: dict(sorted(value.items())) for key, value in sorted(by_format.items())
        },
        "integrity_gate": not bool(set(status_counts) & INTEGRITY_FAILURES),
        "local_conversion_gate": set(status_counts) <= READY_STATUSES,
        "contains_private_paths": False,
        "contains_source_content": False,
        "external_provider_calls": 0,
        "model_calls": 0,
        "cost_usd": 0,
    }
    return private, summary


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--private-output", type=Path, default=DEFAULT_PRIVATE_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text())
    private, summary = audit_manifest(manifest)
    write_json(args.private_output, private)
    write_json(args.summary_output, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
