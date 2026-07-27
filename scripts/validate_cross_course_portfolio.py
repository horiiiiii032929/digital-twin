#!/usr/bin/env python3
"""Validate active and historical sanitized cross-course portfolio inventories."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "research/05_evaluation"
V1_MANIFEST_PATH = MANIFEST_DIR / "cross_course_portfolio_v1.manifest.json"
V2_MANIFEST_PATH = MANIFEST_DIR / "cross_course_portfolio_v2.manifest.json"
V1_EXPECTED_COURSES = {"IT5001", "IT5002", "IT5004", "IT5008"}
V2_EXPECTED_COURSES = {"IT5002", "CS5421", "IT5100B", "IT5100E"}
CANONICAL_CANDIDATES = {
    "IT5001",
    "IT5002",
    "IT5004",
    "IT5008",
    "CS5421",
    "IT5003",
    "IT5007",
    "IT5100B",
    "IT5100E",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as error:
        raise ValueError(f"missing manifest: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid manifest JSON: {error}") from error


def validate_internal(
    manifest: dict[str, Any],
    *,
    portfolio_id: str,
    expected_courses: set[str],
    expected_status: str,
) -> dict[str, int]:
    require(
        manifest["portfolio_id"] == portfolio_id,
        "unexpected portfolio ID",
    )
    require(
        manifest["status"] == expected_status,
        f"{portfolio_id} has unexpected status",
    )
    require(
        not Path(manifest["source_root"]).is_absolute(),
        "source root must not disclose a workstation-specific path",
    )

    courses = manifest["courses"]
    course_ids = [course["course_id"] for course in courses]
    require(len(course_ids) == len(set(course_ids)), "duplicate course ID")
    require(set(course_ids) == expected_courses, "unexpected course portfolio")

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
        require(
            all(
                not Path(document["filename"]).is_absolute()
                and ".." not in Path(document["filename"]).parts
                for document in documents
            ),
            f"{course['course_id']} has an unsafe document path",
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


def validate_v2_inventory(manifest: dict[str, Any]) -> None:
    candidates = manifest["canonical_candidate_inventory"]
    candidate_ids = [candidate["course_id"] for candidate in candidates]
    require(
        len(candidate_ids) == len(set(candidate_ids)),
        "duplicate canonical candidate course ID",
    )
    require(
        set(candidate_ids) == CANONICAL_CANDIDATES,
        "canonical candidate inventory must contain all nine courses",
    )
    kept = {
        candidate["course_id"]
        for candidate in candidates
        if candidate["decision"] == "keep"
    }
    require(kept == V2_EXPECTED_COURSES, "candidate decisions and v2 courses differ")
    require(
        all(
            candidate["decision"] in {"keep", "defer"}
            for candidate in candidates
        ),
        "unexpected canonical candidate decision",
    )


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
        v1_manifest = load_manifest(V1_MANIFEST_PATH)
        validate_internal(
            v1_manifest,
            portfolio_id="cross-course-portfolio-v1",
            expected_courses=V1_EXPECTED_COURSES,
            expected_status="superseded_partial_source_snapshot",
        )
        manifest = load_manifest(V2_MANIFEST_PATH)
        summary = validate_internal(
            manifest,
            portfolio_id="cross-course-portfolio-v2",
            expected_courses=V2_EXPECTED_COURSES,
            expected_status="selected_inventory_boundary",
        )
        validate_v2_inventory(manifest)
        if args.source_root is not None:
            validate_source(manifest, args.source_root)
    except (KeyError, TypeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"cross-course portfolio validation failed: {error}")
        return 1

    print(
        "cross-course portfolio validation passed: active v2 has "
        f"{summary['courses']} courses, {summary['documents']} documents, "
        f"{summary['pages']} pages; historical v1 is superseded; "
        f"source_checked={args.source_root is not None}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
