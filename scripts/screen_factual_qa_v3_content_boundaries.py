#!/usr/bin/env python3
"""Screen private factual-QA candidates for content-boundary review signals."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data/interim/factual_qa_v3/source_roles_v2.json"
DEFAULT_PRIVATE_OUTPUT = (
    ROOT / "data/interim/factual_qa_v3/content_boundary_screen_v1.json"
)
DEFAULT_SUMMARY_OUTPUT = (
    ROOT / "reports/generated/factual-qa-v3-content-boundary-screen-v1.json"
)

TEXT_FORMATS = {
    "code",
    "diagram",
    "notebook",
    "structured_table",
    "structured_text",
    "text",
    "typeset_source",
    "vector_image",
}
SIGNAL_PATTERNS = {
    "credential_or_private_key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
        r"\b(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]",
        re.IGNORECASE,
    ),
    "identity_or_student_record": re.compile(
        r"\b(?:student|participant)\s+(?:name|id|number)\s*[:=]|"
        r"\b[A-Z]\d{7}[A-Z]?\b|"
        r"\b[A-Z0-9._%+-]+@U\.NUS\.EDU\b",
        re.IGNORECASE,
    ),
    "completed_or_graded_work": re.compile(
        r"\b(?:submitted\s+by|marks?\s+awarded|graded\s+by|my\s+answer|"
        r"final\s+answer|answer\s+key|model\s+answer|official\s+solution)\b",
        re.IGNORECASE,
    ),
    "answer_or_solution_material": re.compile(
        r"\b(?:solutions?|answers?)\s*(?:manual|sheet|key|provided|below|above)\b|"
        r"\b(?:worked|sample)\s+solutions?\b",
        re.IGNORECASE,
    ),
    "assessment_instruction": re.compile(
        r"\b(?:assignment|exam|quiz|midterm|final|tutorial|project|rubric)\b",
        re.IGNORECASE,
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _decode_text(data: bytes) -> str | None:
    if b"\x00" in data[:4096]:
        return None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def extract_text(path: Path, format_group: str) -> tuple[str, str]:
    if format_group == "pdf":
        with pymupdf.open(path) as document:
            return "\n".join(page.get_text() for page in document), "pdf_text"
    if format_group == "office_document" and path.suffix.casefold() == ".docx":
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
        return re.sub(r"<[^>]+>", " ", xml), "docx_xml"
    if format_group in TEXT_FORMATS or format_group == "other":
        decoded = _decode_text(path.read_bytes())
        if decoded is None:
            return "", "binary_or_visual_review_required"
        return decoded, "direct_text"
    return "", "visual_review_required"


def screen_records(
    manifest: dict[str, Any],
    *,
    source_root: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = source_root or Path(manifest["source_root"])
    records: list[dict[str, Any]] = []
    for source in manifest["dispositions"]:
        if not source["requires_explicit_review"]:
            continue
        path = root / source["relative_path"]
        exists = path.is_file() and not path.is_symlink()
        hash_matches = exists and sha256_file(path) == source["sha256"]
        extraction_status = "missing_or_hash_mismatch"
        text = ""
        if hash_matches:
            try:
                text, extraction_status = extract_text(path, source["format_group"])
            except (OSError, RuntimeError, ValueError, KeyError, zipfile.BadZipFile):
                extraction_status = "local_extraction_error"
        signal_counts = {
            name: len(pattern.findall(text)) for name, pattern in SIGNAL_PATTERNS.items()
        }
        if signal_counts["credential_or_private_key"]:
            route = "mandatory_exclusion_review"
        elif (
            signal_counts["identity_or_student_record"]
            or signal_counts["completed_or_graded_work"]
            or signal_counts["answer_or_solution_material"]
        ):
            route = "privacy_or_integrity_review"
        elif extraction_status in {
            "binary_or_visual_review_required",
            "visual_review_required",
            "local_extraction_error",
            "missing_or_hash_mismatch",
        }:
            route = "manual_or_visual_boundary_review"
        else:
            route = "semantic_role_review"
        records.append(
            {
                "source_id": source["source_id"],
                "sha256": source["sha256"],
                "relative_path": source["relative_path"],
                "format_group": source["format_group"],
                "course_id": source["course_id"],
                "exists": exists,
                "hash_matches": hash_matches,
                "extraction_status": extraction_status,
                "extracted_character_count": len(text),
                "signal_counts": signal_counts,
                "recommended_review_route": route,
                "final_source_role": None,
            }
        )

    record_sha = hashlib.sha256(
        json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    extraction_counts = Counter(record["extraction_status"] for record in records)
    route_counts = Counter(record["recommended_review_route"] for record in records)
    signal_file_counts = {
        name: sum(record["signal_counts"][name] > 0 for record in records)
        for name in SIGNAL_PATTERNS
    }
    complete = all(record["exists"] and record["hash_matches"] for record in records)
    now = datetime.now(UTC).isoformat()
    private = {
        "schema_version": 1,
        "screen_id": "factual-qa-v3-content-boundary-screen-v1",
        "generated_at": now,
        "source_manifest_id": manifest["manifest_id"],
        "source_manifest_record_sha256": manifest["record_sha256"],
        "source_root": str(root),
        "record_sha256": record_sha,
        "records": records,
    }
    summary = {
        "schema_version": 1,
        "screen_id": private["screen_id"],
        "generated_at": now,
        "source_manifest_id": manifest["manifest_id"],
        "source_manifest_record_sha256": manifest["record_sha256"],
        "record_sha256": record_sha,
        "candidate_count": len(records),
        "extraction_status_counts": dict(sorted(extraction_counts.items())),
        "review_route_counts": dict(sorted(route_counts.items())),
        "signal_file_counts": dict(sorted(signal_file_counts.items())),
        "physical_integrity_gate": complete,
        "content_screening_complete": complete,
        "semantic_eligibility_gate": False,
        "contains_paths": False,
        "contains_source_content": False,
        "final_roles_assigned": 0,
        "external_provider_calls": 0,
        "model_calls": 0,
        "cost_usd": 0,
    }
    return private, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--private-output", type=Path, default=DEFAULT_PRIVATE_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text())
    private, summary = screen_records(manifest)
    args.private_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.private_output.write_text(json.dumps(private, indent=2, sort_keys=True) + "\n")
    args.summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["physical_integrity_gate"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
