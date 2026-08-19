#!/usr/bin/env python3
"""Resolve conversion exceptions into the private factual-QA v3 manifest."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DISPOSITIONS = ROOT / "data/interim/factual_qa_v3/source_dispositions_v3.json"
READINESS = ROOT / "data/interim/factual_qa_v3/conversion_readiness_v3.json"
OCR = ROOT / "data/interim/factual_qa_v3/ocr_remediation_v1.json"
ARCHIVE = ROOT / "data/interim/factual_qa_v3/archive_inventory_v1.json"
PRIVATE_OUTPUT = ROOT / "data/interim/factual_qa_v3/source_dispositions_v4.json"
SUMMARY_OUTPUT = ROOT / "reports/generated/factual-qa-v3-conversion-final-v1.json"
READY = {
    "ready_local_text",
    "ready_local_structured",
    "ready_local_pdf_text",
    "ready_local_visual",
}


def finalize(
    dispositions: dict[str, Any],
    readiness: dict[str, Any],
    ocr: dict[str, Any],
    archive: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    readiness_by_id = {record["source_id"]: record for record in readiness["records"]}
    ocr_ready = {
        record["source_id"] for record in ocr["records"] if record["status"] == "ocr_ready"
    }
    archive_resolved = (
        archive["entries"]
        and all(
            entry["source_role"] == "excluded_duplicate_generated_tool_state"
            for entry in archive["entries"]
        )
    )
    records: list[dict[str, Any]] = []
    for original in dispositions["dispositions"]:
        record = dict(original)
        conversion_status = "not_applicable"
        if original["requires_explicit_review"]:
            probe = readiness_by_id[original["source_id"]]
            conversion_status = probe["conversion_status"]
            if conversion_status in READY:
                pass
            elif conversion_status == "needs_ocr" and original["source_id"] in ocr_ready:
                conversion_status = "ready_local_ocr"
            elif conversion_status == "empty_source":
                record["source_role"] = "excluded_duplicate_generated_tool_state"
                record["disposition_reason"] = "whitespace-only source contains no evidence"
                record["requires_explicit_review"] = False
                conversion_status = "excluded_empty"
            elif conversion_status == "unsupported_format" and original["format_group"] == "archive" and archive_resolved:
                record["source_role"] = "excluded_duplicate_generated_tool_state"
                record["disposition_reason"] = "archive contains only existing duplicates and AppleDouble metadata"
                record["requires_explicit_review"] = False
                conversion_status = "excluded_redundant_archive"
        record["conversion_status"] = conversion_status
        records.append(record)

    unresolved = [
        record
        for record in records
        if record["requires_explicit_review"]
        and record["conversion_status"] not in READY | {"ready_local_ocr"}
    ]
    role_counts = Counter(record["source_role"] for record in records)
    conversion_counts = Counter(record["conversion_status"] for record in records)
    manifest_sha = hashlib.sha256(
        json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    now = datetime.now(UTC).isoformat()
    private = {
        "schema_version": 1,
        "manifest_id": "factual-qa-v3-source-dispositions-v4-conversion-resolved",
        "generated_at": now,
        "predecessor_manifest_id": dispositions["manifest_id"],
        "conversion_record_sha256": readiness["record_sha256"],
        "ocr_record_sha256": ocr["record_sha256"],
        "archive_record_sha256": archive["record_sha256"],
        "source_root": dispositions["source_root"],
        "manifest_sha256": manifest_sha,
        "dispositions": records,
    }
    summary = {
        "schema_version": 1,
        "manifest_id": private["manifest_id"],
        "generated_at": now,
        "manifest_sha256": manifest_sha,
        "source_count": len(records),
        "source_role_counts": dict(sorted(role_counts.items())),
        "conversion_status_counts": dict(sorted(conversion_counts.items())),
        "semantic_role_review_count": role_counts["review_or_conversion_required"],
        "unresolved_conversion_count": len(unresolved),
        "conversion_gate": len(unresolved) == 0,
        "contains_private_paths": False,
        "contains_source_content": False,
        "external_provider_calls": 0,
        "model_calls": 0,
        "cost_usd": 0,
    }
    return private, summary


def main() -> int:
    private, summary = finalize(
        json.loads(DISPOSITIONS.read_text()),
        json.loads(READINESS.read_text()),
        json.loads(OCR.read_text()),
        json.loads(ARCHIVE.read_text()),
    )
    PRIVATE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE_OUTPUT.write_text(json.dumps(private, indent=2, sort_keys=True) + "\n")
    SUMMARY_OUTPUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
