from __future__ import annotations

import math

import pytest

from scripts.audit_multimodal_v3_result import audit_result
from src.digital_twin.evaluation.multimodal_metrics import score_multimodal_ranking


GOLD = (0.0, 0.0, 0.5, 1.0)
DUPLICATE = (0.0, 0.0, 1.0, 1.0)


def _hits() -> list[dict[str, object]]:
    return [
        {"record_id": "ocr", "asset_id": "asset-a", "bbox": list(DUPLICATE)},
        {
            "record_id": "layout",
            "asset_id": "asset-a",
            "bbox": list(DUPLICATE),
        },
    ]


def _source_row(
    case_id: str,
    slice_name: str,
    *,
    gold: bool,
    action_correct: bool = True,
) -> dict[str, object]:
    hits = _hits() if slice_name not in {"no_evidence", "adversarial_integrity"} else []
    ranking = score_multimodal_ranking(
        hits,
        expected_asset_id="asset-a",
        gold_bboxes=[GOLD] if gold else [],
    ).as_dict()
    legacy_ndcg = (
        0.5 + 0.5 / math.log2(3)
        if gold and hits
        else 0.0
    )
    return {
        "case_id": case_id,
        "slice": slice_name,
        "modality": "table" if slice_name == "visual_answerable" else "mixed",
        "action_correct": action_correct,
        **ranking,
        "region_ndcg_at_10": legacy_ndcg,
        "hits": hits,
    }


def test_audit_identifies_duplicate_gain_not_duplicated_source_loop() -> None:
    dataset = {
        "source_assets": [
            {
                "asset_id": "asset-a",
                "regions": [{"region_id": "gold", "bbox": list(GOLD)}],
            }
        ],
        "cases": [
            {
                "case_id": "visual",
                "slice": "visual_answerable",
                "modality": "table",
                "asset_id": "asset-a",
                "gold_region_ids": ["gold"],
            },
            {
                "case_id": "control",
                "slice": "text_control",
                "modality": "mixed",
                "asset_id": "asset-a",
                "gold_region_ids": ["gold"],
            },
            {
                "case_id": "none",
                "slice": "no_evidence",
                "modality": "mixed",
                "asset_id": "asset-a",
                "gold_region_ids": [],
            },
            {
                "case_id": "integrity",
                "slice": "adversarial_integrity",
                "modality": "mixed",
                "asset_id": "asset-a",
                "gold_region_ids": [],
            },
        ],
    }
    rows = [
        _source_row("visual", "visual_answerable", gold=True),
        _source_row("control", "text_control", gold=True),
        _source_row("none", "no_evidence", gold=False),
        _source_row("integrity", "adversarial_integrity", gold=False),
    ]
    source_result = {
        "run_id": "multimodal-retrieval-v1-v3-development-attempt-002",
        "code_revision": "abcdef1",
        "working_tree_dirty": True,
        "heldout_read": False,
        "candidates": [
            {"candidate": "V2", "rows": rows, "metrics": {}},
            {"candidate": "V3", "rows": rows, "metrics": {}},
        ],
    }

    audit = audit_result(dataset, source_result)

    assert audit["findings"]["source_values_match_single_pass_legacy_formula"]
    assert not audit["findings"]["source_values_match_alleged_nested_loop_formula"]
    assert not audit["findings"]["alleged_duplicated_source_loop_confirmed"]
    corrected = audit["candidates"][0]["metrics"]
    assert corrected["failed_slice_region_ndcg_at_10"]["value"] == pytest.approx(
        0.5
    )
    assert corrected["failed_slice_complete_evidence_success_at_3"][
        "denominator"
    ] == 1
    assert corrected["failed_slice_atomic_evidence_recall_at_5"] == {
        "numerator": 1,
        "denominator": 1,
        "value": 1.0,
    }
    assert audit["decision_impact"]["outcome"] == "drop"
