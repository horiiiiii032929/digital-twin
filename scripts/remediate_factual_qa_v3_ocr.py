#!/usr/bin/env python3
"""Run local Apple Vision OCR for factual-QA v3 scanned-PDF exceptions."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
DISPOSITIONS = ROOT / "data/interim/factual_qa_v3/source_dispositions_v3.json"
READINESS = ROOT / "data/interim/factual_qa_v3/conversion_readiness_v3.json"
SWIFT_SOURCE = ROOT / "scripts/apple_vision_ocr.swift"
PRIVATE_OUTPUT = ROOT / "data/interim/factual_qa_v3/ocr_remediation_v1.json"
SUMMARY_OUTPUT = ROOT / "reports/generated/factual-qa-v3-ocr-remediation-v1.json"

pymupdf.TOOLS.mupdf_display_errors(False)
pymupdf.TOOLS.mupdf_display_warnings(False)


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_result(
    expected: dict[str, tuple[str, int]], payload: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    records: list[dict[str, Any]] = []
    for ocr_record in payload.get("records", []):
        source_id, page_number = expected[ocr_record["path"]]
        lines = ocr_record.get("lines", [])
        character_count = sum(len(line.get("text", "")) for line in lines)
        records.append(
            {
                "source_id": source_id,
                "page_number": page_number,
                "status": "ocr_ready" if character_count > 0 else "ocr_empty",
                "width": ocr_record["width"],
                "height": ocr_record["height"],
                "line_count": len(lines),
                "character_count": character_count,
                "lines": lines,
            }
        )
    records.sort(key=lambda item: (item["source_id"], item["page_number"]))
    return records, dict(sorted(Counter(item["status"] for item in records).items()))


def main() -> int:
    dispositions = json.loads(DISPOSITIONS.read_text())
    readiness = json.loads(READINESS.read_text())
    source_root = Path(dispositions["source_root"])
    targets = [
        record for record in readiness["records"] if record["conversion_status"] == "needs_ocr"
    ]
    with tempfile.TemporaryDirectory(prefix="factual-qa-v3-ocr-") as temp_name:
        temp = Path(temp_name)
        binary = temp / "apple_vision_ocr"
        subprocess.run(
            ["swiftc", str(SWIFT_SOURCE), "-o", str(binary)],
            check=True,
            capture_output=True,
            text=True,
        )
        expected: dict[str, tuple[str, int]] = {}
        images: list[Path] = []
        for source_index, target in enumerate(targets):
            with pymupdf.open(source_root / target["relative_path"]) as document:
                for page_index, page in enumerate(document):
                    image_path = temp / f"source-{source_index:03d}-page-{page_index + 1:04d}.png"
                    page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False).save(image_path)
                    expected[str(image_path)] = (target["source_id"], page_index + 1)
                    images.append(image_path)
        completed = subprocess.run(
            [str(binary), *(str(path) for path in images)],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        records, status_counts = build_result(expected, payload)

    now = datetime.now(UTC).isoformat()
    record_sha = canonical_sha256(records)
    private = {
        "schema_version": 1,
        "run_id": "factual-qa-v3-ocr-remediation-v1",
        "generated_at": now,
        "conversion_record_sha256": readiness["record_sha256"],
        "engine": payload["engine"],
        "recognition_level": payload["recognitionLevel"],
        "uses_language_correction": payload["usesLanguageCorrection"],
        "record_sha256": record_sha,
        "records": records,
    }
    summary = {
        "schema_version": 1,
        "run_id": private["run_id"],
        "generated_at": now,
        "conversion_record_sha256": readiness["record_sha256"],
        "engine": payload["engine"],
        "source_count": len(targets),
        "page_count": len(records),
        "status_counts": status_counts,
        "record_sha256": record_sha,
        "ocr_gate": status_counts == {"ocr_ready": len(records)} and len(records) > 0,
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
