"""Shared local-only utilities for the IT5002 rapid retrieval experiment."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pymupdf
from pydantic import BaseModel, Field, model_validator

from src.digital_twin.grounding import (
    CourseDocument,
    DocumentChunk,
    DocumentSegment,
    HeadingParagraphChunker,
    SourcePermissions,
)
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "research" / "05_evaluation" / "it5002_lectures_v1.manifest.json"
SOURCE_ROOT = ROOT / "data" / "raw" / "course_materials" / "it5002_full" / "lecture"
RAPID_ROOT = ROOT / "data" / "processed" / "it5002_retrieval_rapid_v1"
DEVELOPMENT_PATH = RAPID_ROOT / "development.json"
HELDOUT_PATH = RAPID_ROOT / "heldout.json"
SEAL_PATH = RAPID_ROOT / "seal.json"
LOCAL_RUN_ROOT = ROOT / "experiments" / "runs" / "it5002_retrieval_rapid_v1"

QUERY_INSTRUCTION = (
    "Given a student question about the approved IT5002 course, retrieve "
    "passages that together contain all evidence needed to answer accurately "
    "and safely."
)


class EvidenceUnit(BaseModel):
    evidence_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    page: int = Field(ge=1)
    chunk_id: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class RapidRetrievalCase(BaseModel):
    case_id: str = Field(min_length=1)
    family_id: str = Field(min_length=1)
    split: str = Field(pattern=r"^(development|heldout)$")
    scenario: str = Field(min_length=1)
    lecture_id: str | None = None
    query: str = Field(min_length=12, max_length=500)
    expected_action: str = Field(pattern=r"^(answer|abstain)$")
    claims: list[str] = Field(default_factory=list)
    required_evidence: list[EvidenceUnit] = Field(default_factory=list)
    no_evidence_category: str | None = None
    author_model: str = Field(min_length=1)
    reviewer_model: str = Field(min_length=1)
    reviewer_valid: bool

    @model_validator(mode="after")
    def evidence_matches_action(self) -> "RapidRetrievalCase":
        if self.expected_action == "answer":
            if not self.claims or not self.required_evidence:
                raise ValueError("answer cases require claims and evidence")
            if self.no_evidence_category is not None:
                raise ValueError("answer cases cannot have a no-evidence category")
        else:
            if self.claims or self.required_evidence:
                raise ValueError("abstain cases cannot have positive evidence")
            if self.no_evidence_category is None:
                raise ValueError("abstain cases require a no-evidence category")
        return self


class RapidRetrievalDataset(BaseModel):
    dataset_id: str = "it5002-retrieval-rapid-v1"
    split: str = Field(pattern=r"^(development|heldout)$")
    corpus_id: str = "it5002-lectures-v1"
    cases: list[RapidRetrievalCase]

    @model_validator(mode="after")
    def unique_case_and_family_ids(self) -> "RapidRetrievalDataset":
        case_ids = [case.case_id for case in self.cases]
        family_ids = [case.family_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("case IDs must be unique")
        if len(family_ids) != len(set(family_ids)):
            raise ValueError("case family IDs must be unique")
        if any(case.split != self.split for case in self.cases):
            raise ValueError("case split differs from dataset split")
        return self


class CourseCorpus(BaseModel):
    manifest: dict[str, Any]
    documents: list[CourseDocument]
    fixed_chunks: list[DocumentChunk]
    structured_chunks: list[DocumentChunk]
    contextual_chunks: list[DocumentChunk]

    model_config = {"arbitrary_types_allowed": True}


def load_course_corpus() -> CourseCorpus:
    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    documents: list[CourseDocument] = []
    fixed_chunks: list[DocumentChunk] = []
    structured_chunks: list[DocumentChunk] = []
    contextual_chunks: list[DocumentChunk] = []
    chunker = HeadingParagraphChunker(max_chars=1200, overlap_chars=160)

    for record in manifest["documents"]:
        path = SOURCE_ROOT / record["filename"]
        if sha256_file(path) != record["sha256"]:
            raise ValueError(f"source hash mismatch: {record['document_id']}")
        document = _parse_research_document(path, record)
        documents.append(document)
        fixed_chunks.extend(_fixed_window_chunks(document))
        document_chunks = _page_bounded_heading_chunks(document, chunker)
        structured = [
            _enrich_structured_chunk(chunk, document) for chunk in document_chunks
        ]
        structured_chunks.extend(structured)
        contextual_chunks.extend(_contextual_chunk(chunk) for chunk in structured)

    _require_unique_chunk_ids(fixed_chunks, "fixed")
    _require_unique_chunk_ids(structured_chunks, "structured")
    _require_unique_chunk_ids(contextual_chunks, "contextual")
    return CourseCorpus(
        manifest=manifest,
        documents=documents,
        fixed_chunks=fixed_chunks,
        structured_chunks=structured_chunks,
        contextual_chunks=contextual_chunks,
    )


def _page_bounded_heading_chunks(
    document: CourseDocument,
    chunker: HeadingParagraphChunker,
) -> list[DocumentChunk]:
    """Apply heading/paragraph chunking without mixing separate lecture slides."""

    segments_by_page: dict[int, list[DocumentSegment]] = {}
    for segment in document.segments:
        if segment.page is not None:
            segments_by_page.setdefault(segment.page, []).append(segment)

    chunks: list[DocumentChunk] = []
    ordinal = 0
    for page, segments in sorted(segments_by_page.items()):
        page_text = "\n\n".join(segment.text for segment in segments)
        page_document = document.model_copy(
            update={
                "text": page_text,
                "segments": segments,
                "locator": f"page {page}",
            }
        )
        for provisional in chunker.chunk(page_document):
            content_hash = provisional.content_hash or sha256_text(provisional.text)
            identity = (
                f"{document.id}\x1f{ordinal}\x1f{provisional.locator}\x1f{content_hash}"
            )
            chunks.append(
                provisional.model_copy(
                    update={
                        "id": f"chunk-{sha256_text(identity)[:24]}",
                        "ordinal": ordinal,
                    }
                )
            )
            ordinal += 1
    return chunks


def load_dataset(path: Path) -> RapidRetrievalDataset:
    return RapidRetrievalDataset.model_validate_json(path.read_text(encoding="utf-8"))


def dump_private_json(path: Path, payload: BaseModel | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, BaseModel):
        value = payload.model_dump(mode="json")
    else:
        value = payload
    path.write_text(
        f"{json.dumps(value, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalized_tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def _parse_research_document(
    path: Path,
    record: dict[str, Any],
) -> CourseDocument:
    with pymupdf.open(path) as pdf:
        blocks_by_page: list[list[tuple[str, float, bool]]] = []
        font_weights: Counter[float] = Counter()
        for page in pdf:
            page_blocks: list[tuple[str, float, bool]] = []
            for block in page.get_text("dict", sort=True)["blocks"]:
                if block.get("type") != 0:
                    continue
                spans = [
                    span
                    for line in block.get("lines", [])
                    for span in line.get("spans", [])
                    if _normalize_text(span.get("text", ""))
                ]
                text = _normalize_text(" ".join(span.get("text", "") for span in spans))
                if not text:
                    continue
                maximum_size = max(float(span.get("size", 0)) for span in spans)
                bold = any("bold" in span.get("font", "").casefold() for span in spans)
                page_blocks.append((text, maximum_size, bold))
                for span in spans:
                    font_weights[round(float(span.get("size", 0)), 1)] += len(
                        span.get("text", "")
                    )
            blocks_by_page.append(page_blocks)

    body_size = font_weights.most_common(1)[0][0] if font_weights else 10.0
    segments: list[DocumentSegment] = []
    current_heading = record["filename"].removesuffix(".pdf").replace("_", " ")
    for page_number, page_blocks in enumerate(blocks_by_page, start=1):
        for block_number, (text, maximum_size, bold) in enumerate(
            page_blocks,
            start=1,
        ):
            heading = len(text) <= 160 and (
                maximum_size >= body_size * 1.18
                or (bold and maximum_size >= body_size and len(text) <= 90)
            )
            if heading:
                current_heading = text
            segments.append(
                DocumentSegment(
                    text=text,
                    locator=f"page {page_number}, text block {block_number}",
                    heading_path=[current_heading],
                    page=page_number,
                )
            )

    text = "\n\n".join(segment.text for segment in segments)
    return CourseDocument(
        id=record["document_id"],
        title=record["filename"].removesuffix(".pdf").replace("_", " "),
        text=text,
        source_label=SourceLabel.SYSTEM_SUGGESTED_TRUSTED,
        source_artifact_id=record["document_id"],
        source_version=1,
        content_hash=sha256_text(text),
        locator=f"local-source://{record['document_id']}/{record['filename']}",
        permissions=SourcePermissions(
            processing_allowed=True,
            tutoring_allowed=True,
            display_allowed=False,
        ),
        segments=segments,
        metadata={
            "course_id": "IT5002",
            "lecture_id": record["document_id"],
            "research_permission": "user-authorized-local-evaluation",
            "student_release": "pending-professor-or-institution-authorization",
            "source_sha256": record["sha256"],
        },
    )


def _fixed_window_chunks(document: CourseDocument) -> list[DocumentChunk]:
    page_texts: dict[int, list[str]] = {}
    for segment in document.segments:
        if segment.page is not None:
            page_texts.setdefault(segment.page, []).append(segment.text)
    text_parts: list[str] = []
    spans: list[tuple[int, int, int]] = []
    cursor = 0
    for page, parts in sorted(page_texts.items()):
        page_text = "\n\n".join(parts)
        if text_parts:
            cursor += 2
        start = cursor
        text_parts.append(page_text)
        cursor += len(page_text)
        spans.append((page, start, cursor))
    text = "\n\n".join(text_parts)

    chunks: list[DocumentChunk] = []
    step = 1200 - 160
    for ordinal, start in enumerate(range(0, len(text), step)):
        end = min(len(text), start + 1200)
        window = text[start:end].strip()
        if not window:
            continue
        pages = [
            page
            for page, page_start, page_end in spans
            if page_start < end and page_end > start
        ]
        content_hash = sha256_text(window)
        identity = f"{document.id}\x1f{ordinal}\x1f{start}\x1f{content_hash}"
        chunk_id = f"fixed-{sha256_text(identity)[:24]}"
        chunks.append(
            DocumentChunk(
                id=chunk_id,
                document_id=document.id,
                text=window,
                ordinal=ordinal,
                source_artifact_id=document.source_artifact_id,
                source_version=1,
                source_label=document.source_label,
                content_hash=content_hash,
                locator=f"pages {min(pages)}-{max(pages)}",
                page_start=min(pages),
                page_end=max(pages),
                retrieval_allowed=True,
                metadata={
                    **document.metadata,
                    "title": document.title,
                    "representation": "fixed-window-1200-160",
                },
            )
        )
        if end == len(text):
            break
    return chunks


def _enrich_structured_chunk(
    chunk: DocumentChunk,
    document: CourseDocument,
) -> DocumentChunk:
    headings = [
        segment.heading_path[-1]
        for segment in document.segments
        if segment.page is not None
        and chunk.page_start is not None
        and chunk.page_end is not None
        and chunk.page_start <= segment.page <= chunk.page_end
        and segment.heading_path
    ]
    heading = headings[0] if headings else document.title
    return chunk.model_copy(
        update={
            "metadata": {
                **chunk.metadata,
                "course_id": "IT5002",
                "lecture_id": document.id,
                "lecture_title": document.title,
                "heading_path": heading,
                "representation": "heading-paragraph-1200-160",
            }
        }
    )


def _contextual_chunk(chunk: DocumentChunk) -> DocumentChunk:
    metadata = chunk.metadata
    context = "\n".join(
        [
            f"Course: {metadata['course_id']}",
            f"Lecture: {metadata['lecture_id']} — {metadata['lecture_title']}",
            f"Section: {metadata['heading_path']}",
            f"Locator: {chunk.locator}",
        ]
    )
    indexed_text = f"{context}\n\n{chunk.text}"
    return chunk.model_copy(
        update={
            "text": indexed_text,
            "content_hash": sha256_text(indexed_text),
            "metadata": {
                **metadata,
                "original_content_hash": chunk.content_hash or "",
                "representation": "deterministic-context-heading-1200-160",
            },
        }
    )


def _require_unique_chunk_ids(chunks: list[DocumentChunk], label: str) -> None:
    identifiers = [chunk.id for chunk in chunks]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f"duplicate {label} chunk IDs")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return ordered[index]
