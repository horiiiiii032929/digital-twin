#!/usr/bin/env python3
"""Validate the sanitized cross-course portfolio inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT / "research/05_evaluation/cross_course_portfolio_v1.manifest.json"
)
EXPECTED_COURSES = {"IT5001", "IT5002", "IT5004", "IT5008"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_manifest() -> dict[str, Any]:
    try:
        return json.loads(MANIFEST_PATH.read_text())
    except FileNotFoundError as error:
        raise ValueError(f"missing manifest: {MANIFEST_PATH}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid manifest JSON: {error}") from error


def validate_internal(manifest: dict[str, Any]) -> dict[str, int]:
    require(
        manifest["portfolio_id"] == "cross-course-portfolio-v1",
        "unexpected portfolio ID",
    )
    require(
        manifest["status"] == "selected_inventory_boundary",
        "portfolio inventory must be selected",
    )
    require(
        not Path(manifest["source_root"]).is_absolute(),
        "source root must not disclose a workstation-specific path",
    )

    courses = manifest["courses"]
    course_ids = [course["course_id"] for course in courses]
    require(len(course_ids) == len(set(course_ids)), "duplicate course ID")
    require(set(course_ids) == EXPECTED_COURSES, "unexpected course portfolio")

    document_count = 0
    page_count = 0
    character_count = 0
    byte_count = 0
    hashes: set[str] = set()

    for course in courses:
        documents = course["documents"]
        require(
            course["document_count"] == len(documents),
            f"{course['course_id']} document count mismatch",
        )
        require(
            all(document["filename"].lower().endswith(".pdf") for document in documents),
            f"{course['course_id']} primary corpus must contain only PDFs",
        )
        require(
            len({document["filename"] for document in documents}) == len(documents),
            f"{course['course_id']} has duplicate filenames",
        )

        course_pages = sum(document["pages"] for document in documents)
        course_characters = sum(
            document["pdftotext_characters"] for document in documents
        )
        course_bytes = sum(document["bytes"] for document in documents)
        require(course["page_count"] == course_pages, "course page count mismatch")
        require(
            course["pdftotext_character_count"] == course_characters,
            "course character count mismatch",
        )
        require(course["byte_count"] == course_bytes, "course byte count mismatch")

        for document in documents:
            require(document["pages"] > 0, "primary PDF must have pages")
            require(
                document["pdftotext_characters"] > 0,
                "primary PDF must have selectable text",
            )
            require(document["sha256"] not in hashes, "duplicate primary document hash")
            hashes.add(document["sha256"])

        document_count += len(documents)
        page_count += course_pages
        character_count += course_characters
        byte_count += course_bytes

    summary = manifest["summary"]
    require(summary["course_count"] == len(courses), "summary course count mismatch")
    require(summary["document_count"] == document_count, "summary document count mismatch")
    require(summary["page_count"] == page_count, "summary page count mismatch")
    require(
        summary["pdftotext_character_count"] == character_count,
        "summary character count mismatch",
    )
    require(summary["byte_count"] == byte_count, "summary byte count mismatch")
    require(
        summary["exact_duplicate_primary_documents"] == 0,
        "primary corpus must contain no exact duplicates",
    )

    return {
        "courses": len(courses),
        "documents": document_count,
        "pages": page_count,
        "characters": character_count,
        "bytes": byte_count,
    }


def command_number(command: list[str], prefix: str | None = None) -> int:
    output = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if prefix is not None:
        line = next(
            (item for item in output.splitlines() if item.startswith(prefix)),
            None,
        )
        require(line is not None, f"missing {prefix!r} in command output")
        output = line.removeprefix(prefix)
    return int(output.strip())


def extracted_character_count(path: Path) -> int:
    output = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return len(output)


def validate_source(manifest: dict[str, Any], source_root: Path) -> None:
    require(source_root.is_dir(), f"source root does not exist: {source_root}")
    for course in manifest["courses"]:
        lecture_root = source_root / course["relative_root"]
        for document in course["documents"]:
            path = lecture_root / document["filename"]
            require(path.is_file(), f"missing source PDF: {path}")
            require(
                hashlib.sha256(path.read_bytes()).hexdigest() == document["sha256"],
                f"hash mismatch: {path}",
            )
            require(path.stat().st_size == document["bytes"], f"size mismatch: {path}")
            require(
                command_number(["pdfinfo", str(path)], "Pages:") == document["pages"],
                f"page count mismatch: {path}",
            )
            require(
                extracted_character_count(path)
                == document["pdftotext_characters"],
                f"text character count mismatch: {path}",
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-root",
        type=Path,
        help="Optional local academia_vault root for source hash/content verification.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = load_manifest()
        summary = validate_internal(manifest)
        if args.source_root is not None:
            validate_source(manifest, args.source_root)
    except (KeyError, TypeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"cross-course portfolio validation failed: {error}")
        return 1

    print(
        "cross-course portfolio validation passed: "
        f"{summary['courses']} courses, {summary['documents']} documents, "
        f"{summary['pages']} pages, source_checked={args.source_root is not None}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
