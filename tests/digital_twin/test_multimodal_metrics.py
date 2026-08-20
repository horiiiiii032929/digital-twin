from __future__ import annotations

import math

import pytest

from src.digital_twin.evaluation.multimodal_metrics import (
    gold_bboxes_for_case,
    score_multimodal_ranking,
)


def hit(
    record_id: str,
    asset_id: str,
    bbox: tuple[float, float, float, float],
) -> dict[str, object]:
    return {"record_id": record_id, "asset_id": asset_id, "bbox": list(bbox)}


def test_page_rank_counts_unique_assets_not_duplicate_regions() -> None:
    hits = [
        hit("a-1", "asset-a", (0.0, 0.0, 0.2, 0.2)),
        hit("a-2", "asset-a", (0.5, 0.5, 0.2, 0.2)),
        hit("b-1", "asset-b", (0.1, 0.1, 0.2, 0.2)),
    ]

    metrics = score_multimodal_ranking(
        hits,
        expected_asset_id="asset-b",
        gold_bboxes=[(0.1, 0.1, 0.2, 0.2)],
    )

    assert metrics.page_rank == 2
    assert metrics.page_success_at_3 is True


def test_complete_evidence_requires_every_gold_region_in_top_three() -> None:
    hits = [
        hit("first", "asset-a", (0.0, 0.0, 0.2, 0.2)),
        hit("other", "asset-b", (0.0, 0.0, 1.0, 1.0)),
        hit("other-2", "asset-c", (0.0, 0.0, 1.0, 1.0)),
        hit("second", "asset-a", (0.7, 0.7, 0.2, 0.2)),
    ]

    metrics = score_multimodal_ranking(
        hits,
        expected_asset_id="asset-a",
        gold_bboxes=[(0.0, 0.0, 0.2, 0.2), (0.7, 0.7, 0.2, 0.2)],
    )

    assert metrics.matched_gold_regions_at_3 == 1
    assert metrics.complete_evidence_success_at_3 is False
    assert metrics.matched_gold_regions_at_5 == 2
    assert metrics.atomic_evidence_recall_at_5 == 1.0


def test_atomic_recall_uses_gold_region_denominator() -> None:
    metrics = score_multimodal_ranking(
        [hit("first", "asset-a", (0.0, 0.0, 0.2, 0.2))],
        expected_asset_id="asset-a",
        gold_bboxes=[(0.0, 0.0, 0.2, 0.2), (0.7, 0.7, 0.2, 0.2)],
    )

    assert metrics.matched_gold_regions_at_5 == 1
    assert metrics.gold_region_count == 2
    assert metrics.atomic_evidence_recall_at_5 == 0.5


def test_region_ndcg_does_not_add_duplicate_gain_for_one_gold_region() -> None:
    gold = (0.0, 0.0, 0.5, 1.0)
    duplicate = (0.0, 0.0, 1.0, 1.0)
    assert score_multimodal_ranking(
        [
            hit("ocr", "asset-a", duplicate),
            hit("layout", "asset-a", duplicate),
        ],
        expected_asset_id="asset-a",
        gold_bboxes=[gold],
    ).region_ndcg_at_10 == pytest.approx(0.5)


def test_region_ndcg_discounts_late_localization() -> None:
    exact = (0.2, 0.2, 0.3, 0.3)
    metrics = score_multimodal_ranking(
        [
            hit("wrong", "asset-b", (0.0, 0.0, 1.0, 1.0)),
            hit("exact", "asset-a", exact),
        ],
        expected_asset_id="asset-a",
        gold_bboxes=[exact],
    )

    assert metrics.region_ndcg_at_10 == pytest.approx(1 / math.log2(3))


def test_region_metrics_use_one_to_one_gold_assignment() -> None:
    first = (0.0, 0.0, 0.4, 0.4)
    second = (0.6, 0.6, 0.4, 0.4)
    metrics = score_multimodal_ranking(
        [
            hit("first", "asset-a", first),
            hit("first-duplicate", "asset-a", first),
        ],
        expected_asset_id="asset-a",
        gold_bboxes=[first, second],
    )

    assert metrics.matched_gold_regions_at_3 == 1
    assert metrics.atomic_evidence_recall_at_5 == 0.5
    assert metrics.complete_evidence_success_at_3 is False


def test_region_ndcg_normalizes_perfect_multi_region_ranking() -> None:
    first = (0.0, 0.0, 0.4, 0.4)
    second = (0.6, 0.6, 0.4, 0.4)
    metrics = score_multimodal_ranking(
        [
            hit("first", "asset-a", first),
            hit("second", "asset-a", second),
        ],
        expected_asset_id="asset-a",
        gold_bboxes=[first, second],
    )

    assert metrics.region_ndcg_at_10 == pytest.approx(1.0)


def test_no_gold_regions_have_explicit_zero_denominator_metrics() -> None:
    metrics = score_multimodal_ranking(
        [hit("page", "asset-a", (0.0, 0.0, 1.0, 1.0))],
        expected_asset_id="asset-a",
        gold_bboxes=[],
    )

    assert metrics.page_success_at_3 is True
    assert metrics.gold_region_count == 0
    assert metrics.atomic_evidence_recall_at_5 == 0.0
    assert metrics.complete_evidence_success_at_3 is False
    assert metrics.region_ndcg_at_10 == 0.0


def test_gold_bbox_resolution_rejects_unknown_region() -> None:
    case = {"asset_id": "asset-a", "gold_region_ids": ["missing"]}
    assets = {
        "asset-a": {"regions": [{"region_id": "known", "bbox": [0.1, 0.1, 0.2, 0.2]}]}
    }

    with pytest.raises(ValueError, match="unknown gold regions"):
        gold_bboxes_for_case(case, assets)


def test_metric_rejects_duplicate_gold_regions_and_nonfinite_threshold() -> None:
    assets = {
        "asset-a": {"regions": [{"region_id": "known", "bbox": [0.1, 0.1, 0.2, 0.2]}]}
    }
    with pytest.raises(ValueError, match="gold region IDs must be unique"):
        gold_bboxes_for_case(
            {"asset_id": "asset-a", "gold_region_ids": ["known", "known"]},
            assets,
        )
    with pytest.raises(ValueError, match="between zero and one"):
        score_multimodal_ranking(
            [],
            expected_asset_id="asset-a",
            gold_bboxes=[],
            region_iou_threshold=float("nan"),
        )
