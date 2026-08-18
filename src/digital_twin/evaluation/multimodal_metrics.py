"""Deterministic ranking metrics for page- and region-grounded retrieval."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from src.digital_twin.evaluation.multimodal_retrieval import BBox, bbox_iou


@dataclass(frozen=True)
class MultimodalRankingMetrics:
    """One case's page, localization, and evidence-completeness metrics."""

    page_rank: int | None
    page_success_at_3: bool
    region_iou_at_3: float
    region_iou_at_5: float
    region_ndcg_at_10: float
    complete_evidence_success_at_3: bool
    atomic_evidence_recall_at_5: float
    matched_gold_regions_at_3: int
    matched_gold_regions_at_5: int
    gold_region_count: int

    def as_dict(self) -> dict[str, int | float | bool | None]:
        return asdict(self)


def gold_bboxes_for_case(
    case: dict[str, Any], assets: dict[str, dict[str, Any]]
) -> list[BBox]:
    """Resolve every declared gold region without reading non-development data."""
    asset_id = str(case["asset_id"])
    if asset_id not in assets:
        raise ValueError(f"case references unknown asset: {asset_id}")
    regions = {
        str(region["region_id"]): tuple(float(value) for value in region["bbox"])
        for region in assets[asset_id]["regions"]
    }
    gold_region_ids = [str(region_id) for region_id in case["gold_region_ids"]]
    missing = [region_id for region_id in gold_region_ids if region_id not in regions]
    if missing:
        raise ValueError(
            f"case references unknown gold regions for {asset_id}: {', '.join(missing)}"
        )
    return [regions[region_id] for region_id in gold_region_ids]


def _unique_asset_rank(hits: list[dict[str, Any]], expected_asset_id: str) -> int | None:
    seen: set[str] = set()
    rank = 0
    for hit in hits:
        asset_id = str(hit["asset_id"])
        if asset_id in seen:
            continue
        seen.add(asset_id)
        rank += 1
        if asset_id == expected_asset_id:
            return rank
    return None


def _iou_matrix(
    hits: list[dict[str, Any]],
    *,
    expected_asset_id: str,
    gold_bboxes: list[BBox],
    limit: int,
) -> list[list[float]]:
    return [
        (
            [
                bbox_iou(
                    tuple(float(value) for value in hit["bbox"]),
                    gold_bbox,
                )
                for gold_bbox in gold_bboxes
            ]
            if str(hit["asset_id"]) == expected_asset_id
            else [0.0 for _gold_bbox in gold_bboxes]
        )
        for hit in hits[:limit]
    ]


def _maximum_assignment_score(
    ious_by_hit: list[list[float]],
    *,
    gain: Callable[[float, int], float | bool],
) -> float:
    """Return the best one-hit-to-one-gold assignment score.

    The dynamic program prevents one broad region or duplicate representation
    from satisfying multiple gold regions. Unassigned hits and gold regions are
    allowed.
    """
    states = {0: 0.0}
    for rank, hit_ious in enumerate(ious_by_hit, start=1):
        updated = dict(states)
        for mask, score in states.items():
            for gold_index, iou in enumerate(hit_ious):
                bit = 1 << gold_index
                if mask & bit:
                    continue
                candidate = score + float(gain(iou, rank))
                if candidate > updated.get(mask | bit, float("-inf")):
                    updated[mask | bit] = candidate
        states = updated
    return max(states.values(), default=0.0)


def _assignment_metrics(
    hits: list[dict[str, Any]],
    *,
    expected_asset_id: str,
    gold_bboxes: list[BBox],
    limit: int,
    region_iou_threshold: float,
) -> tuple[float, int]:
    matrix = _iou_matrix(
        hits,
        expected_asset_id=expected_asset_id,
        gold_bboxes=gold_bboxes,
        limit=limit,
    )
    total_iou = _maximum_assignment_score(matrix, gain=lambda iou, _rank: iou)
    matched = _maximum_assignment_score(
        matrix,
        gain=lambda iou, _rank: iou >= region_iou_threshold,
    )
    return total_iou, int(matched)


def _region_ndcg_at_k(
    hits: list[dict[str, Any]],
    *,
    expected_asset_id: str,
    gold_bboxes: list[BBox],
    limit: int,
) -> float:
    """One-to-one discounted IoU gain normalized by ideal ranked evidence.

    Each hit and gold region contributes at most once, so duplicate OCR/layout
    records and broad regions cannot inflate the score. Perfectly localized,
    consecutively ranked evidence scores 1.0 for any number of gold regions.
    """
    if not gold_bboxes:
        return 0.0
    matrix = _iou_matrix(
        hits,
        expected_asset_id=expected_asset_id,
        gold_bboxes=gold_bboxes,
        limit=limit,
    )
    dcg = _maximum_assignment_score(
        matrix,
        gain=lambda iou, rank: iou / math.log2(rank + 1),
    )
    ideal_count = min(len(gold_bboxes), limit)
    ideal_dcg = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return dcg / ideal_dcg


def score_multimodal_ranking(
    hits: list[dict[str, Any]],
    *,
    expected_asset_id: str,
    gold_bboxes: list[BBox],
    region_iou_threshold: float = 0.1,
) -> MultimodalRankingMetrics:
    """Score one ranked list with explicit page and atomic-region denominators."""
    if not 0.0 <= region_iou_threshold <= 1.0:
        raise ValueError("region_iou_threshold must be between zero and one")

    page_rank = _unique_asset_rank(hits, expected_asset_id)
    page_success_at_3 = page_rank is not None and page_rank <= 3
    total_iou_at_3, matched_at_3 = _assignment_metrics(
        hits,
        expected_asset_id=expected_asset_id,
        gold_bboxes=gold_bboxes,
        limit=3,
        region_iou_threshold=region_iou_threshold,
    )
    total_iou_at_5, matched_at_5 = _assignment_metrics(
        hits,
        expected_asset_id=expected_asset_id,
        gold_bboxes=gold_bboxes,
        limit=5,
        region_iou_threshold=region_iou_threshold,
    )
    gold_count = len(gold_bboxes)

    return MultimodalRankingMetrics(
        page_rank=page_rank,
        page_success_at_3=page_success_at_3,
        region_iou_at_3=total_iou_at_3 / gold_count if gold_count else 0.0,
        region_iou_at_5=total_iou_at_5 / gold_count if gold_count else 0.0,
        region_ndcg_at_10=_region_ndcg_at_k(
            hits,
            expected_asset_id=expected_asset_id,
            gold_bboxes=gold_bboxes,
            limit=10,
        ),
        complete_evidence_success_at_3=(
            gold_count > 0 and page_success_at_3 and matched_at_3 == gold_count
        ),
        atomic_evidence_recall_at_5=(
            matched_at_5 / gold_count if gold_count else 0.0
        ),
        matched_gold_regions_at_3=matched_at_3,
        matched_gold_regions_at_5=matched_at_5,
        gold_region_count=gold_count,
    )
