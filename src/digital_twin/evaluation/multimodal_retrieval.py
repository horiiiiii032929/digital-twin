"""Offline representations and ranking for the multimodal V0-V3 ladder."""

from __future__ import annotations

from collections.abc import Iterable
import math
from typing import Any

from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.retrieval import BM25Retriever, lexical_tokens


BBox = tuple[float, float, float, float]


def validated_bbox(bbox: Iterable[float]) -> BBox:
    """Validate an x/y/width/height box in normalized page coordinates."""

    try:
        values = tuple(float(value) for value in bbox)
    except (TypeError, ValueError) as error:
        raise ValueError("bounding box must contain four numeric values") from error
    if len(values) != 4:
        raise ValueError("bounding box must contain four numeric values")
    x, y, width, height = values
    if any(not math.isfinite(value) for value in values):
        raise ValueError("bounding box values must be finite")
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        raise ValueError("bounding box must be normalized x/y/width/height")
    return x, y, width, height


def contextual_crop_bbox(
    bbox: BBox,
    *,
    padding: float = 0.03,
    minimum_width: float = 0.25,
    minimum_height: float = 0.20,
) -> BBox:
    """Expand a normalized region deterministically while staying page-local."""
    x, y, width, height = validated_bbox(bbox)
    if not math.isfinite(padding) or padding < 0:
        raise ValueError("padding must be finite and non-negative")
    if (
        not math.isfinite(minimum_width)
        or not 0 < minimum_width <= 1
        or not math.isfinite(minimum_height)
        or not 0 < minimum_height <= 1
    ):
        raise ValueError("minimum crop dimensions must be between zero and one")
    target_width = min(1.0, max(width + 2 * padding, minimum_width))
    target_height = min(1.0, max(height + 2 * padding, minimum_height))
    center_x = x + width / 2
    center_y = y + height / 2
    left = min(max(0.0, center_x - target_width / 2), 1.0 - target_width)
    top = min(max(0.0, center_y - target_height / 2), 1.0 - target_height)
    return (left, top, target_width, target_height)


def normalized_crop_pixels(
    bbox: BBox, *, image_width: int, image_height: int
) -> tuple[int, int, int, int]:
    """Convert a normalized top-left box to a non-empty pixel crop."""
    if (
        isinstance(image_width, bool)
        or not isinstance(image_width, int)
        or isinstance(image_height, bool)
        or not isinstance(image_height, int)
        or image_width < 1
        or image_height < 1
    ):
        raise ValueError("image dimensions must be positive")
    x, y, width, height = validated_bbox(bbox)
    left = max(0, min(image_width - 1, math.floor(x * image_width)))
    top = max(0, min(image_height - 1, math.floor(y * image_height)))
    right = max(left + 1, min(image_width, math.ceil((x + width) * image_width)))
    bottom = max(top + 1, min(image_height, math.ceil((y + height) * image_height)))
    return (left, top, right, bottom)


def region_key(asset_id: str, bbox: Iterable[float]) -> str:
    """Create a stable key that merges OCR/layout records for one region."""
    coordinates = ",".join(f"{value:.6f}" for value in validated_bbox(bbox))
    return f"{asset_id}:{coordinates}"


def reciprocal_rank_fuse_regions(
    lexical_hits: list[dict[str, Any]],
    visual_hits: list[dict[str, Any]],
    *,
    rank_constant: int = 60,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Fuse text and image rankings at region identity, not duplicate record ID."""
    if (
        isinstance(rank_constant, bool)
        or not isinstance(rank_constant, int)
        or isinstance(limit, bool)
        or not isinstance(limit, int)
        or rank_constant < 1
        or limit < 1
    ):
        raise ValueError("rank_constant and limit must be positive")
    scores: dict[str, float] = {}
    representatives: dict[str, dict[str, Any]] = {}
    channels: dict[str, set[str]] = {}
    for channel, hits in (("lexical", lexical_hits), ("visual", visual_hits)):
        seen: set[str] = set()
        for rank, hit in enumerate(hits, start=1):
            key = region_key(hit["asset_id"], hit["bbox"])
            if key in seen:
                continue
            seen.add(key)
            scores[key] = scores.get(key, 0.0) + 1 / (rank_constant + rank)
            channels.setdefault(key, set()).add(channel)
            current = representatives.get(key)
            if current is None or channel == "visual":
                representatives[key] = hit
    if not scores:
        return []
    maximum = max(scores.values())
    ordered = sorted(scores, key=lambda key: (-scores[key], key))[:limit]
    return [
        {
            **representatives[key],
            "score": scores[key] / maximum,
            "raw_score": scores[key],
            "channels": sorted(channels[key]),
        }
        for key in ordered
    ]


def union_bbox(boxes: Iterable[BBox]) -> BBox:
    materialized = [validated_bbox(box) for box in boxes]
    if not materialized:
        raise ValueError("at least one bounding box is required")
    left = min(box[0] for box in materialized)
    top = min(box[1] for box in materialized)
    right = max(box[0] + box[2] for box in materialized)
    bottom = max(box[1] + box[3] for box in materialized)
    return (left, top, right - left, bottom - top)


def spatial_label(bbox: BBox) -> str:
    x, y, width, height = validated_bbox(bbox)
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
    if (
        isinstance(maximum_lines, bool)
        or not isinstance(maximum_lines, int)
        or maximum_lines < 1
    ):
        raise ValueError("maximum_lines must be positive")
    if not math.isfinite(vertical_gap) or vertical_gap < 0:
        raise ValueError("vertical_gap must be finite and non-negative")
    for line in lines:
        validated_bbox(line["bbox"])
        confidence = float(line["confidence"])
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("OCR confidence must be between zero and one")
        if not str(line["text"]).strip():
            raise ValueError("OCR line text must not be blank")
    ordered = sorted(lines, key=lambda line: (line["bbox"][1], line["bbox"][0]))
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_bottom = 0.0
    for line in ordered:
        top = float(line["bbox"][1])
        if current and (
            len(current) >= maximum_lines or top - current_bottom > vertical_gap
        ):
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
        bbox = union_bbox(
            tuple(float(value) for value in line["bbox"]) for line in group
        )
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
    left_x, left_y, left_width, left_height = validated_bbox(left)
    right_x, right_y, right_width, right_height = validated_bbox(right)
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
        x, y, width, height = validated_bbox(record["bbox"])
        by_course.setdefault(record["course_id"], []).append(
            DocumentChunk(
                id=record["record_id"],
                document_id=record["asset_id"],
                text=record["text"],
                ordinal=ordinal,
                source_artifact_id=record["source_artifact_id"],
                locator=f"page:{record['page']}",
                page_start=record["page"],
                page_end=record["page"],
                bounding_box=(x, y, x + width, y + height),
                source_checksum=record["source_document_sha256"],
                region_checksum=record["render_sha256"],
                retrieval_allowed=record["permission"] == "course-approved-local-only",
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
        record = records_by_id.get(hit.chunk.id)
        if record is None:
            raise ValueError("retrieval hit references an unknown candidate record")
        x, y, width, height = validated_bbox(record["bbox"])
        if (
            hit.chunk.document_id != record["asset_id"]
            or hit.chunk.source_artifact_id != record["source_artifact_id"]
            or hit.chunk.page_start != record["page"]
            or hit.chunk.page_end != record["page"]
            or hit.chunk.bounding_box != (x, y, x + width, y + height)
            or hit.chunk.source_checksum != record["source_document_sha256"]
            or hit.chunk.region_checksum != record["render_sha256"]
        ):
            raise ValueError("retrieval hit lineage differs from candidate record")
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
        term
        for term in lexical_tokens(query)
        if term not in stopwords and len(term) > 2
    }
    retrieved_terms = set(lexical_tokens("\n".join(hit_texts)))
    required = min(2, len(query_terms))
    return required > 0 and len(query_terms & retrieved_terms) >= required
