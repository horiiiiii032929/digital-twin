#!/usr/bin/env python3
"""Audit parser and chunker candidates on the private cross-course portfolio."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

import pymupdf

from src.digital_twin.grounding import (
    ApprovalDecision,
    ApprovalRecord,
    HeadingParagraphChunker,
    LocalDocumentParser,
    PageBoundedHeadingParagraphChunker,
    SourcePermissions,
    SourceSensitivity,
    source_artifact_from_path,
)
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT / "research/05_evaluation/cross_course_portfolio_v2.manifest.json"
)
RUN_ID = "cross-course-ingestion-v1"
MAX_CHARS = 1200
OVERLAP_CHARS = 160
TINY_CHARS = 80


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "ACADEMIA_VAULT_ROOT",
                Path.home() / "Documents" / "academia_vault",
            )
        ),
        help=(
            "Canonical local academia_vault root. Defaults to "
            "ACADEMIA_VAULT_ROOT or ~/Documents/academia_vault."
        ),
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def percentile(values: list[float], quantile: float) -> float:
    require(bool(values), "cannot calculate percentile of an empty list")
    ordered = sorted(values)
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_state() -> dict[str, Any]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {"revision": revision, "dirty": bool(status.strip())}


def normalized_text_hash(text: str) -> str:
    normalized = " ".join(re.findall(r"[a-z0-9]+", text.casefold()))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def approval_for(path: Path, artifact_id: str, title: str) -> tuple[Any, Any]:
    source = source_artifact_from_path(
        path,
        artifact_id=artifact_id,
        title=title,
        version=1,
        source_label=SourceLabel.COURSE_APPROVED,
        provider_role="professor",
        sensitivity=SourceSensitivity.STANDARD,
    )
    approval = ApprovalRecord(
        id=f"approval-{artifact_id}",
        source_artifact_id=artifact_id,
        source_version=1,
        decision=ApprovalDecision.APPROVED,
        permissions=SourcePermissions(
            processing_allowed=True,
            tutoring_allowed=True,
            display_allowed=False,
        ),
        reviewer_id="source-holder",
        reviewer_role="professor",
        reviewed_at=datetime(2026, 7, 27, tzinfo=UTC),
        restrictions=[
            "research evaluation only",
            "source text and figures remain outside Git",
        ],
    )
    return source, approval


def chunk_profile(chunks: list[DocumentChunk]) -> dict[str, Any]:
    normalized_hashes = [normalized_text_hash(chunk.text) for chunk in chunks]
    hash_counts = Counter(normalized_hashes)
    duplicate_occurrences = sum(count - 1 for count in hash_counts.values())
    cross_page = sum(chunk.page_start != chunk.page_end for chunk in chunks)
    provenance_complete = sum(
        bool(
            chunk.source_artifact_id
            and chunk.source_version == 1
            and chunk.locator
            and chunk.page_start
            and chunk.page_end
            and chunk.content_hash
            and chunk.retrieval_allowed
        )
        for chunk in chunks
    )
    return {
        "chunks": len(chunks),
        "cross_page_chunks": cross_page,
        "empty_chunks": sum(not chunk.text.strip() for chunk in chunks),
        "oversized_chunks": sum(len(chunk.text) > MAX_CHARS for chunk in chunks),
        "tiny_chunks": sum(len(chunk.text) < TINY_CHARS for chunk in chunks),
        "provenance_complete_chunks": provenance_complete,
        "unique_chunk_ids": len({chunk.id for chunk in chunks}),
        "normalized_duplicate_occurrences": duplicate_occurrences,
        "maximum_characters": max((len(chunk.text) for chunk in chunks), default=0),
    }


def aggregate_candidate(
    records: list[dict[str, Any]],
    candidate: str,
) -> dict[str, Any]:
    keys = (
        "chunks",
        "cross_page_chunks",
        "empty_chunks",
        "oversized_chunks",
        "tiny_chunks",
        "provenance_complete_chunks",
        "normalized_duplicate_occurrences",
    )
    result = {
        key: sum(record["candidates"][candidate][key] for record in records)
        for key in keys
    }
    ids = [
        chunk_id
        for record in records
        for chunk_id in record["candidate_chunk_ids"][candidate]
    ]
    result["unique_chunk_ids"] = len(set(ids))
    result["maximum_characters"] = max(
        record["candidates"][candidate]["maximum_characters"]
        for record in records
    )
    result["tiny_chunk_rate"] = result["tiny_chunks"] / result["chunks"]
    result["normalized_duplicate_rate"] = (
        result["normalized_duplicate_occurrences"] / result["chunks"]
    )
    result["provenance_complete_rate"] = (
        result["provenance_complete_chunks"] / result["chunks"]
    )
    result["hard_gates_passed"] = all(
        (
            result["cross_page_chunks"] == 0,
            result["empty_chunks"] == 0,
            result["oversized_chunks"] == 0,
            result["unique_chunk_ids"] == result["chunks"],
            result["provenance_complete_chunks"] == result["chunks"],
        )
    )
    return result


def run_audit(source_root: Path, manifest_path: Path) -> dict[str, Any]:
    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    parser = LocalDocumentParser()
    chunkers = {
        "document_wide": HeadingParagraphChunker(
            max_chars=MAX_CHARS,
            overlap_chars=OVERLAP_CHARS,
        ),
        "page_bounded": PageBoundedHeadingParagraphChunker(
            max_chars=MAX_CHARS,
            overlap_chars=OVERLAP_CHARS,
        ),
    }
    records: list[dict[str, Any]] = []
    parse_latencies: list[float] = []
    chunk_latencies: dict[str, list[float]] = defaultdict(list)
    course_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "documents": 0,
            "pages": 0,
            "text_pages": 0,
            "segments": 0,
            "figures": 0,
        }
    )
    figure_pages: dict[tuple[str, str, int], int] = Counter()

    for course in manifest["courses"]:
        course_id = course["course_id"]
        for document_record in course["documents"]:
            relative_path = Path(course["relative_root"]) / document_record["filename"]
            path = source_root / relative_path
            require(path.is_file(), f"missing source: {relative_path}")
            require(
                sha256_file(path) == document_record["sha256"],
                f"manifest hash mismatch: {relative_path}",
            )
            artifact_id = (
                f"{course_id.casefold()}-"
                f"{hashlib.sha256(str(relative_path).encode()).hexdigest()[:16]}"
            )
            source, approval = approval_for(
                path,
                artifact_id,
                f"{course_id} lecture material",
            )

            started = time.perf_counter()
            first = parser.parse(path, source, approval)
            parse_latencies.append((time.perf_counter() - started) * 1000)
            second = parser.parse(path, source, approval)
            require(first.document == second.document, f"unstable parse: {relative_path}")
            require(
                [figure.id for figure in first.figures]
                == [figure.id for figure in second.figures],
                f"unstable figure IDs: {relative_path}",
            )

            candidates: dict[str, dict[str, Any]] = {}
            candidate_chunk_ids: dict[str, list[str]] = {}
            for candidate, chunker in chunkers.items():
                started = time.perf_counter()
                first_chunks = chunker.chunk(first.document)
                chunk_latencies[candidate].append(
                    (time.perf_counter() - started) * 1000
                )
                second_chunks = chunker.chunk(second.document)
                require(
                    [chunk.id for chunk in first_chunks]
                    == [chunk.id for chunk in second_chunks],
                    f"unstable {candidate} chunks: {relative_path}",
                )
                candidates[candidate] = chunk_profile(first_chunks)
                candidate_chunk_ids[candidate] = [
                    chunk.id for chunk in first_chunks
                ]

            pages_with_text = {
                segment.page
                for segment in first.document.segments
                if segment.page is not None
            }
            course_summary = course_counts[course_id]
            course_summary["documents"] += 1
            course_summary["pages"] += document_record["pages"]
            course_summary["text_pages"] += len(pages_with_text)
            course_summary["segments"] += len(first.document.segments)
            course_summary["figures"] += len(first.figures)
            for figure in first.figures:
                figure_pages[(course_id, artifact_id, figure.page)] += 1

            records.append(
                {
                    "course_id": course_id,
                    "source_artifact_id": artifact_id,
                    "relative_path": str(relative_path),
                    "manifest_pages": document_record["pages"],
                    "text_pages": len(pages_with_text),
                    "segments": len(first.document.segments),
                    "figures": len(first.figures),
                    "parse_stable": True,
                    "candidates": candidates,
                    "candidate_chunk_ids": candidate_chunk_ids,
                }
            )

    require(len(records) == manifest["summary"]["document_count"], "document mismatch")
    candidate_summary = {
        candidate: aggregate_candidate(records, candidate) for candidate in chunkers
    }
    course_summary = []
    for course_id, counts in sorted(course_counts.items()):
        course_records = [item for item in records if item["course_id"] == course_id]
        course_summary.append(
            {
                "course_id": course_id,
                **counts,
                "text_page_coverage": counts["text_pages"] / counts["pages"],
                "document_wide_chunks": sum(
                    item["candidates"]["document_wide"]["chunks"]
                    for item in course_records
                ),
                "document_wide_cross_page_chunks": sum(
                    item["candidates"]["document_wide"]["cross_page_chunks"]
                    for item in course_records
                ),
                "page_bounded_chunks": sum(
                    item["candidates"]["page_bounded"]["chunks"]
                    for item in course_records
                ),
                "page_bounded_tiny_chunks": sum(
                    item["candidates"]["page_bounded"]["tiny_chunks"]
                    for item in course_records
                ),
            }
        )

    top_figure_pages = [
        {
            "course_id": course_id,
            "source_artifact_id": artifact_id,
            "page": page,
            "figure_count": count,
        }
        for (course_id, artifact_id, page), count in sorted(
            figure_pages.items(),
            key=lambda item: (-item[1], *item[0]),
        )[:20]
    ]
    result = {
        "run_id": RUN_ID,
        "status": (
            "completed"
            if candidate_summary["page_bounded"]["hard_gates_passed"]
            else "failed"
        ),
        "run_date": "2026-07-28",
        "code": git_state(),
        "corpus": {
            "portfolio_id": manifest["portfolio_id"],
            "manifest_path": str(manifest_path.relative_to(ROOT)),
            "document_count": len(records),
            "page_count": sum(item["manifest_pages"] for item in records),
            "course_count": len(course_counts),
            "permission_record": manifest["permission_record"],
        },
        "configuration": {
            "parser": "pymupdf-document-parser@v1",
            "max_chars": MAX_CHARS,
            "overlap_chars": OVERLAP_CHARS,
            "tiny_chunk_threshold": TINY_CHARS,
            "repeats": 2,
        },
        "integrity": {
            "manifest_hash_matches": len(records),
            "parse_successes": len(records),
            "stable_parse_documents": sum(item["parse_stable"] for item in records),
        },
        "candidates": candidate_summary,
        "courses": course_summary,
        "operations": {
            "parse_document_median_ms": median(parse_latencies),
            "parse_document_p95_ms": percentile(parse_latencies, 0.95),
            "chunk_document_median_ms": {
                candidate: median(values)
                for candidate, values in chunk_latencies.items()
            },
            "chunk_document_p95_ms": {
                candidate: percentile(values, 0.95)
                for candidate, values in chunk_latencies.items()
            },
            "provider_calls": 0,
            "cost_usd": 0,
        },
        "visual_sampling_candidates": top_figure_pages,
        "documents": [
            {
                key: value
                for key, value in record.items()
                if key != "candidate_chunk_ids"
            }
            for record in records
        ],
        "decision": (
            "keep_page_bounded"
            if candidate_summary["page_bounded"]["hard_gates_passed"]
            else "refine"
        ),
        "limitations": [
            "No retrieval queries were run.",
            "Text extraction cannot represent every diagram or spatial relationship.",
            "Normalized duplicate text is a boilerplate diagnostic, not semantic deduplication.",
        ],
    }
    return result


def main() -> int:
    args = parse_args()
    try:
        result = run_audit(args.source_root, args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"cross-course ingestion audit failed: {error}")
        return 1

    serialized = f"{json.dumps(result, indent=2, sort_keys=True)}\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
