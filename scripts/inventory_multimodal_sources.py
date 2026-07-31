#!/usr/bin/env python3
"""Inventory multimodal study sources while keeping paths and content private."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = Path.home() / "Documents" / "academia_vault"
DEFAULT_PRIVATE_OUTPUT = (
    ROOT / "data/interim/multimodal_retrieval_v1/source_inventory_v1.json"
)
DEFAULT_SANITIZED_OUTPUT = (
    ROOT / "reports/generated/multimodal-source-inventory-v1.json"
)

FORMAT_GROUPS = {
    ".pdf": "pdf",
    ".drawio": "diagram",
    ".png": "raster_image",
    ".jpg": "raster_image",
    ".jpeg": "raster_image",
    ".eps": "vector_image",
    ".csv": "structured_table",
    ".ipynb": "notebook",
    ".tex": "typeset_source",
    ".docx": "office_document",
    ".pages": "office_document",
    ".md": "text",
    ".txt": "text",
    ".bib": "text",
    ".py": "code",
    ".sql": "code",
    ".tsx": "code",
    ".ts": "code",
    ".js": "code",
    ".mjs": "code",
    ".vue": "code",
    ".html": "code",
    ".css": "code",
    ".asm": "code",
    ".json": "structured_text",
    ".yaml": "structured_text",
    ".yml": "structured_text",
    ".toml": "structured_text",
}
MODALITY_CANDIDATES = {
    "pdf": ["diagram", "chart", "table", "equation", "screenshot", "scanned_page", "annotation", "photo", "text_control"],
    "diagram": ["diagram", "annotation"],
    "raster_image": ["diagram", "chart", "screenshot", "scanned_page", "annotation", "photo"],
    "vector_image": ["diagram", "chart", "equation"],
    "structured_table": ["table", "chart"],
    "notebook": ["chart", "table", "equation", "screenshot", "text_control"],
    "typeset_source": ["equation", "table", "text_control"],
    "office_document": ["diagram", "chart", "table", "equation", "screenshot", "photo", "text_control"],
    "text": ["text_control"],
    "code": ["text_control"],
    "structured_text": ["table", "text_control"],
}
GENERATED_PARTS = {
    ".git",
    ".idea",
    ".vscode",
    ".venv",
    "__pycache__",
    ".ipynb_checkpoints",
    "node_modules",
    "dist",
    "build",
}
GENERATED_SUFFIXES = {".pyc", ".lock", ".tsbuildinfo", ".code-workspace"}
ARCHIVE_SUFFIXES = {".zip", ".tar", ".gz", ".7z", ".rar"}
SENSITIVE_PATTERN = re.compile(
    r"(^|[^a-z0-9])(\.env|id_rsa|private[_-]?key|access[_-]?token|api[_-]?key|credential|secret)([^a-z0-9]|$)",
    re.IGNORECASE,
)
ASSESSMENT_PATTERN = re.compile(
    r"(^|[^a-z0-9])(answer|solution|submission|assignment|exam|quiz|midterm|final|grade|project|tutorial|homework)([^a-z0-9]|$)",
    re.IGNORECASE,
)
COURSE_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?:CS|IT)\d{4}[A-Z]?(?![A-Z0-9])",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--private-output", type=Path, default=DEFAULT_PRIVATE_OUTPUT)
    parser.add_argument("--sanitized-output", type=Path, default=DEFAULT_SANITIZED_OUTPUT)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def course_id(relative_path: Path) -> str:
    for part in relative_path.parts:
        match = COURSE_PATTERN.search(part)
        if match:
            return match.group(0).upper()
    return "unassigned"


def classify(relative_path: Path) -> tuple[str, str, str]:
    suffix = relative_path.suffix.casefold()
    parts = {part.casefold() for part in relative_path.parts[:-1]}
    normalized = "/".join(relative_path.parts).casefold()
    if parts & GENERATED_PARTS or suffix in GENERATED_SUFFIXES:
        return "generated", "excluded_generated", "generated or tool-state artifact"
    if SENSITIVE_PATTERN.search(normalized):
        return FORMAT_GROUPS.get(suffix, "other"), "excluded_sensitive", "credential or secret indicator"
    if suffix in ARCHIVE_SUFFIXES:
        return "archive", "review_required", "archive contents require separate inspection"
    group = FORMAT_GROUPS.get(suffix, "other")
    if ASSESSMENT_PATTERN.search(normalized):
        return group, "review_required", "assessment-like path requires content review"
    if group == "other":
        return group, "review_required", "unsupported or extensionless format"
    if course_id(relative_path) == "unassigned":
        return group, "review_required", "course scope is not inferable from path"
    return group, "eligible_candidate", "recognized course-scoped study format"


def iter_files(source_root: Path) -> Iterable[Path]:
    return sorted(
        path
        for path in source_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


def inventory_sources(source_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not source_root.is_dir():
        raise ValueError(f"source root is absent: {source_root}")
    records: list[dict[str, Any]] = []
    for path in iter_files(source_root):
        relative_path = path.relative_to(source_root)
        digest = sha256_file(path)
        group, eligibility, reason = classify(relative_path)
        source_identifier = hashlib.sha256(
            f"{relative_path.as_posix()}\0{digest}".encode("utf-8")
        ).hexdigest()[:24]
        records.append(
            {
                "source_id": f"vault-{source_identifier}",
                "relative_path": relative_path.as_posix(),
                "sha256": digest,
                "bytes": path.stat().st_size,
                "extension": relative_path.suffix.casefold() or "[none]",
                "format_group": group,
                "course_id": course_id(relative_path),
                "eligibility": eligibility,
                "eligibility_reason": reason,
                "modality_candidates": MODALITY_CANDIDATES.get(group, []),
            }
        )

    inventory_digest = hashlib.sha256(
        json.dumps(
            [
                {
                    "relative_path": record["relative_path"],
                    "sha256": record["sha256"],
                    "bytes": record["bytes"],
                }
                for record in records
            ],
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    generated_at = datetime.now(timezone.utc).isoformat()
    private = {
        "inventory_id": "academic-vault-multimodal-source-inventory-v1",
        "inventory_version": 1,
        "generated_at": generated_at,
        "source_root": str(source_root),
        "inventory_sha256": inventory_digest,
        "sources": records,
    }

    def counts(field: str) -> dict[str, int]:
        return dict(sorted(Counter(record[field] for record in records).items()))

    modalities = Counter(
        modality
        for record in records
        if record["eligibility"] == "eligible_candidate"
        for modality in record["modality_candidates"]
    )
    sanitized = {
        "inventory_id": private["inventory_id"],
        "inventory_version": 1,
        "generated_at": generated_at,
        "inventory_sha256": inventory_digest,
        "files": len(records),
        "bytes": sum(record["bytes"] for record in records),
        "counts_by_extension": counts("extension"),
        "counts_by_format_group": counts("format_group"),
        "counts_by_course": counts("course_id"),
        "counts_by_eligibility": counts("eligibility"),
        "eligible_modality_candidate_counts": dict(sorted(modalities.items())),
        "contains_paths": False,
        "contains_source_content": False,
    }
    return private, sanitized


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    try:
        private, sanitized = inventory_sources(args.source_root)
        write_json(args.private_output, private)
        write_json(args.sanitized_output, sanitized)
    except (OSError, ValueError) as error:
        print(f"multimodal source inventory failed: {error}")
        return 1
    print(json.dumps(sanitized, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
