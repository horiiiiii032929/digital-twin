"""Offline representations for the multimodal retrieval V0-V2 ladder."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.retrieval import BM25Retriever, lexical_tokens


BBox = tuple[float, float, float, float]


def union_bbox(boxes: Iterable[BBox]) -> BBox:
    materialized = list(boxes)
    if not materialized:
        raise ValueError("at least one bounding box is required")
    left = min(box[0] for box in materialized)
    top = min(box[1] for box in materialized)
    right = max(box[0] + box[2] for box in materialized)
    bottom = max(box[1] + box[3] for box in materialized)
    return (left, top, right - left, bottom - top)


def spatial_label(bbox: BBox) -> str:
    x, y, width, height = bbox
    center_x = x + width / 2
    center_y = y + height / 2
    vertical = "top" if center_y < 1 / 3 else "bottom" if center_y > 2 / 3 else "middle"
    horizontal = (
        "left" if center_x < 1 / 3 else "right" if center_x > 2 / 3 else "center"
    )
    return f"{vertical}-{horizontal}"


def group_ocr_lines(
    lines: list[dict[str, Any]],
    *,
    maximum_lines: int = 6,
    vertical_gap: float = 0.035,
) -> list[dict[str, Any]]:
    """Combine reading-order OCR lines into bounded local text regions."""
    if maximum_lines < 1:
        raise ValueError("maximum_lines must be positive")
    ordered = sorted(lines, key=lambda line: (line["bbox"][1], line["bbox"][0]))
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_bottom = 0.0
    for line in ordered:
        top = float(line["bbox"][1])
        if current and (len(current) >= maximum_lines or top - current_bottom > vertical_gap):
            groups.append(current)
            current = []
        current.append(line)
        current_bottom = max(
            current_bottom if len(current) > 1 else 0.0,
            top + float(line["bbox"][3]),
        )
    if current:
        groups.append(current)

    blocks = []
    for index, group in enumerate(groups):
        bbox = union_bbox(tuple(float(value) for value in line["bbox"]) for line in group)
        blocks.append(
            {
                "block_id": f"ocr-block-{index:03d}",
                "text": "\n".join(line["text"] for line in group),
                "bbox": list(bbox),
                "spatial_label": spatial_label(bbox),
                "mean_confidence": sum(float(line["confidence"]) for line in group)
                / len(group),
                "line_count": len(group),
            }
        )
    return blocks


def description_text(description: dict[str, Any]) -> str:
    """Flatten a schema-constrained local vision description for lexical ranking."""
    parts: list[str] = []
    for key in (
        "visual_type",
        "description",
        "table_or_diagram_structure",
    ):
        value = description.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    for key in ("visible_labels", "relationships", "colors_and_symbols"):
        value = description.get(key)
        if isinstance(value, list):
            parts.extend(str(item).strip() for item in value if str(item).strip())
    return "\n".join(parts)


def build_candidate_records(
    asset: dict[str, Any],
    *,
    ocr_blocks: list[dict[str, Any]],
    description: dict[str, Any] | None,
) -> dict[str, list[dict[str, Any]]]:
    """Build the frozen V0-V2 records without using case queries or claims."""
    common = {
        "asset_id": asset["asset_id"],
        "course_id": asset["course_id"],
        "source_artifact_id": asset["source_artifact_id"],
        "source_document_sha256": asset["source_document_sha256"],
        "page": asset["page"],
        "permission": asset["permission"],
        "render_sha256": asset["sha256"],
    }
    page_record = {
        **common,
        "record_id": f"{asset['asset_id']}-page-text",
        "kind": "page_text",
        "bbox": [0.0, 0.0, 1.0, 1.0],
        "text": asset["surrounding_text"],
        "authoritative": True,
    }
    v1_ocr = [
        {
            **common,
            "record_id": f"{asset['asset_id']}-{block['block_id']}",
            "kind": "ocr_block",
            "bbox": block["bbox"],
            "text": block["text"],
            "authoritative": False,
            "ocr_confidence": block["mean_confidence"],
        }
        for block in ocr_blocks
    ]
    v2_layout = [
        {
            **record,
            "record_id": record["record_id"].replace("ocr-block", "layout-block"),
            "kind": "layout_block",
            "text": (
                f"{block['spatial_label']} page region. "
                f"Reading-order text:\n{block['text']}"
            ),
        }
        for record, block in zip(v1_ocr, ocr_blocks, strict=True)
    ]
    v2_description: list[dict[str, Any]] = []
    if description is not None:
        flattened = description_text(description)
        if flattened:
            v2_description.append(
                {
                    **common,
                    "record_id": f"{asset['asset_id']}-local-vision-description",
                    "kind": "vision_description",
                    "bbox": [0.0, 0.0, 1.0, 1.0],
                    "text": flattened,
                    "authoritative": False,
                    "review_status": "unreviewed-ranking-metadata",
                }
            )
    return {
        "V0": [page_record],
        "V1": [page_record, *v1_ocr],
        "V2": [page_record, *v1_ocr, *v2_layout, *v2_description],
    }


def bbox_iou(left: BBox, right: BBox) -> float:
    left_x, left_y, left_width, left_height = left
    right_x, right_y, right_width, right_height = right
    intersection_width = max(
        0.0,
        min(left_x + left_width, right_x + right_width) - max(left_x, right_x),
    )
    intersection_height = max(
        0.0,
        min(left_y + left_height, right_y + right_height) - max(left_y, right_y),
    )
    intersection = intersection_width * intersection_height
    union = left_width * left_height + right_width * right_height - intersection
    return intersection / union if union else 0.0


def build_course_retrievers(
    records: list[dict[str, Any]],
) -> tuple[dict[str, BM25Retriever], dict[str, dict[str, Any]]]:
    """Build course-isolated BM25 indexes over one frozen candidate representation."""
    records_by_id = {record["record_id"]: record for record in records}
    if len(records_by_id) != len(records):
        raise ValueError("candidate representation contains duplicate record IDs")
    by_course: dict[str, list[DocumentChunk]] = {}
    for ordinal, record in enumerate(records):
        by_course.setdefault(record["course_id"], []).append(
            DocumentChunk(
                id=record["record_id"],
                document_id=record["asset_id"],
                text=record["text"],
                ordinal=ordinal,
                source_artifact_id=record["source_artifact_id"],
                content_hash=record["render_sha256"],
                locator=f"page:{record['page']}",
                page_start=record["page"],
                page_end=record["page"],
                retrieval_allowed=record["permission"]
                == "course-approved-local-only",
                metadata={"asset_id": record["asset_id"]},
            )
        )
    return (
        {course: BM25Retriever(chunks) for course, chunks in by_course.items()},
        records_by_id,
    )


def unique_asset_hits(
    hits: list[RetrievalHit], records_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result = []
    for hit in hits:
        record = records_by_id[hit.chunk.id]
        if record["asset_id"] in seen:
            continue
        seen.add(record["asset_id"])
        result.append(
            {
                "record_id": record["record_id"],
                "asset_id": record["asset_id"],
                "bbox": record["bbox"],
                "kind": record["kind"],
                "score": hit.relevance_score,
                "raw_score": hit.raw_score,
            }
        )
    return result


def unsafe_retrieval_instruction(query: str) -> bool:
    normalized = " ".join(query.casefold().split())
    indicators = (
        "ignore course scope",
        "override the source permission",
        "private evidence from another course",
        "without professor approval",
    )
    return any(indicator in normalized for indicator in indicators)


def query_has_retrieved_terms(query: str, hit_texts: list[str]) -> bool:
    """Conservative lexical evidence check used only for abstention behavior."""
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "for",
        "in",
        "is",
        "of",
        "on",
        "the",
        "to",
        "what",
        "which",
    }
    query_terms = {
        term for term in lexical_tokens(query) if term not in stopwords and len(term) > 2
    }
    retrieved_terms = set(lexical_tokens("\n".join(hit_texts)))
    required = min(2, len(query_terms))
    return required > 0 and len(query_terms & retrieved_terms) >= required
