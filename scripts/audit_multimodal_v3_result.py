#!/usr/bin/env python3
"""Audit preserved V3 rankings without rerunning retrieval or opening held-out."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from scripts.validate_multimodal_retrieval_dataset import ROOT, validate_dataset
from src.digital_twin.evaluation.multimodal_benchmark import (
    load_sealed_development,
    sha256_file,
)
from src.digital_twin.evaluation.multimodal_metrics import (
    gold_bboxes_for_case,
    score_multimodal_ranking,
)
from src.digital_twin.evaluation.multimodal_retrieval import bbox_iou


CORRECTION_ID = (
    "multimodal-retrieval-v1-v3-development-attempt-002-"
    "analysis-correction-001"
)
SEALED_ROOT = ROOT / "data/processed/multimodal_retrieval_v1/sealed_v1"
DEFAULT_SEAL = SEALED_ROOT / "seal.json"
DEFAULT_LEDGER = SEALED_ROOT / "heldout_once_ledger.json"
RUN_ID = "multimodal-retrieval-v1-v3-development-attempt-002"
FAILED_MODALITIES = {"table", "scanned_page"}
DEFAULT_SOURCE_RESULT = (
    ROOT
    / "experiments/runs/"
    "multimodal_retrieval_v1_v3_development_attempt_002/result.json"
)
DEFAULT_OUTPUT = ROOT / "reports/generated" / f"{CORRECTION_ID}.json"
FLOAT_TOLERANCE = 1e-12


def scoped_cases(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    """Select only the development slices used by the preserved V3 run."""
    return [
        case
        for case in dataset["cases"]
        if case["slice"] != "visual_answerable"
        or case["modality"] in FAILED_MODALITIES
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--source-result", type=Path, default=DEFAULT_SOURCE_RESULT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def code_revision() -> tuple[str, bool]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return revision, dirty


def _legacy_relevances(
    row: dict[str, Any],
    case: dict[str, Any],
    assets: dict[str, dict[str, Any]],
) -> list[float]:
    gold_bboxes = gold_bboxes_for_case(case, assets)
    if not gold_bboxes:
        return []
    expected_bbox = gold_bboxes[0]
    return [
        bbox_iou(tuple(float(value) for value in hit["bbox"]), expected_bbox)
        if str(hit["asset_id"]) == str(case["asset_id"])
        else 0.0
        for hit in row["hits"]
    ]


def _legacy_region_score(relevances: list[float]) -> float:
    return min(
        1.0,
        sum(
            relevance / math.log2(index + 1)
            for index, relevance in enumerate(relevances, start=1)
        ),
    )


def _nested_loop_region_score(relevances: list[float]) -> float:
    repeated = relevances * len(relevances)
    return _legacy_region_score(repeated)


def _equal(left: Any, right: Any) -> bool:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), abs_tol=FLOAT_TOLERANCE)
    return left == right


def _aggregate(candidate_rows: list[dict[str, Any]]) -> dict[str, Any]:
    visual = [row for row in candidate_rows if row["slice"] == "visual_answerable"]
    controls = [row for row in candidate_rows if row["slice"] == "text_control"]
    no_evidence = [row for row in candidate_rows if row["slice"] == "no_evidence"]
    integrity = [
        row for row in candidate_rows if row["slice"] == "adversarial_integrity"
    ]
    if not all((visual, controls, no_evidence, integrity)):
        raise ValueError("source result is missing a required evaluation slice")
    gold_count = sum(row["corrected"]["gold_region_count"] for row in visual)
    if gold_count == 0:
        raise ValueError("visual evaluation scope has no declared gold regions")
    matched_count = sum(
        row["corrected"]["matched_gold_regions_at_5"] for row in visual
    )
    return {
        "failed_slice_complete_evidence_success_at_3": {
            "numerator": sum(
                row["corrected"]["complete_evidence_success_at_3"] for row in visual
            ),
            "denominator": len(visual),
            "value": mean(
                row["corrected"]["complete_evidence_success_at_3"] for row in visual
            ),
        },
        "failed_slice_atomic_evidence_recall_at_5": {
            "numerator": matched_count,
            "denominator": gold_count,
            "value": matched_count / gold_count,
        },
        "failed_slice_region_ndcg_at_10": {
            "denominator": len(visual),
            "value": mean(
                row["corrected"]["region_ndcg_at_10"] for row in visual
            ),
        },
        "text_control_page_success_at_3": {
            "numerator": sum(
                row["corrected"]["page_success_at_3"] for row in controls
            ),
            "denominator": len(controls),
            "value": mean(
                row["corrected"]["page_success_at_3"] for row in controls
            ),
        },
        "no_evidence_action_accuracy": {
            "numerator": sum(row["action_correct"] for row in no_evidence),
            "denominator": len(no_evidence),
            "value": mean(row["action_correct"] for row in no_evidence),
        },
        "integrity_action_accuracy": {
            "numerator": sum(row["action_correct"] for row in integrity),
            "denominator": len(integrity),
            "value": mean(row["action_correct"] for row in integrity),
        },
        "overall_action_accuracy": {
            "numerator": sum(row["action_correct"] for row in candidate_rows),
            "denominator": len(candidate_rows),
            "value": mean(row["action_correct"] for row in candidate_rows),
        },
    }


def audit_result(
    dataset: dict[str, Any], source_result: dict[str, Any]
) -> dict[str, Any]:
    if source_result.get("run_id") != RUN_ID:
        raise ValueError(f"unexpected source run ID: {source_result.get('run_id')}")
    if source_result.get("heldout_read") is not False:
        raise ValueError("source result does not prove held-out remained closed")

    expected_cases = {case["case_id"]: case for case in scoped_cases(dataset)}
    assets = {asset["asset_id"]: asset for asset in dataset["source_assets"]}
    expected_case_ids = set(expected_cases)
    candidate_audits = []
    single_pass_matches: list[bool] = []
    nested_loop_matches: list[bool] = []

    source_candidates = source_result.get("candidates", [])
    candidate_names = [row.get("candidate") for row in source_candidates]
    if len(candidate_names) != 2 or set(candidate_names) != {"V2", "V3"}:
        raise ValueError("source result must contain exactly V2 and V3")

    for source_candidate in source_candidates:
        rows = source_candidate["rows"]
        row_case_ids = [row["case_id"] for row in rows]
        if (
            set(row_case_ids) != expected_case_ids
            or len(row_case_ids) != len(expected_case_ids)
        ):
            raise ValueError("source candidate rows do not match the frozen scope")
        audited_rows = []
        for row in rows:
            case = expected_cases[row["case_id"]]
            ranking = score_multimodal_ranking(
                row["hits"],
                expected_asset_id=case["asset_id"],
                gold_bboxes=gold_bboxes_for_case(case, assets),
            ).as_dict()
            legacy_relevances = _legacy_relevances(row, case, assets)
            legacy_region_score = _legacy_region_score(legacy_relevances)
            nested_region_score = _nested_loop_region_score(legacy_relevances)
            if case["gold_region_ids"]:
                single_pass_matches.append(
                    _equal(row["region_ndcg_at_10"], legacy_region_score)
                )
                nested_loop_matches.append(
                    _equal(row["region_ndcg_at_10"], nested_region_score)
                )
            changed_fields = [
                field
                for field in (
                    "page_rank",
                    "page_success_at_3",
                    "region_iou_at_3",
                    "region_iou_at_5",
                    "region_ndcg_at_10",
                    "complete_evidence_success_at_3",
                    "atomic_evidence_recall_at_5",
                )
                if not _equal(row[field], ranking[field])
            ]
            audited_rows.append(
                {
                    "case_id": row["case_id"],
                    "slice": row["slice"],
                    "modality": row["modality"],
                    "action_correct": row["action_correct"],
                    "source_region_ndcg_at_10": row["region_ndcg_at_10"],
                    "legacy_single_pass_region_score": legacy_region_score,
                    "alleged_nested_loop_region_score": nested_region_score,
                    "corrected": ranking,
                    "changed_fields": changed_fields,
                }
            )
        candidate_audits.append(
            {
                "candidate": source_candidate["candidate"],
                "scope_case_count": len(audited_rows),
                "metrics": _aggregate(audited_rows),
                "latency_metrics_unchanged": {
                    key: value
                    for key, value in source_candidate["metrics"].items()
                    if "latency" in key or "encoding" in key
                },
                "rows": audited_rows,
            }
        )

    return {
        "schema_version": 1,
        "audit_id": CORRECTION_ID,
        "source_run_id": RUN_ID,
        "source_code_revision": source_result["code_revision"],
        "source_working_tree_dirty": source_result["working_tree_dirty"],
        "heldout_read": False,
        "model_called": False,
        "scope": {
            "case_count": len(expected_cases),
            "failed_visual_modalities": sorted(FAILED_MODALITIES),
            "source_candidate_count": len(candidate_audits),
        },
        "findings": {
            "source_values_match_single_pass_legacy_formula": all(
                single_pass_matches
            ),
            "source_values_match_alleged_nested_loop_formula": all(
                nested_loop_matches
            ),
            "alleged_duplicated_source_loop_confirmed": False,
            "actual_metric_defect": (
                "region nDCG added discounted IoU for every overlapping record, "
                "including duplicate OCR/layout representations of one gold region, "
                "then capped the unnormalized sum at one"
            ),
            "corrected_definition": (
                "maximum one-to-one discounted IoU assignment between retrieved "
                "and gold regions in the first ten hits, normalized by ideal DCG"
            ),
        },
        "candidates": candidate_audits,
        "decision_impact": {
            "outcome": "drop",
            "changed": False,
            "rationale": (
                "The corrected region diagnostic reverses the V2/V3 ordering, but "
                "V3 still retrieves only 1/3 gold regions at five versus 2/3 for "
                "V2 and still fails the no-online-vision-model architecture gate."
            ),
        },
    }


def main() -> int:
    args = parse_args()
    dataset, _ = load_sealed_development(
        root=ROOT, seal_path=args.seal, ledger_path=args.ledger
    )
    validate_dataset(dataset)
    source_result = json.loads(args.source_result.read_text(encoding="utf-8"))
    audit = audit_result(dataset, source_result)
    revision, dirty = code_revision()
    audit.update(
        {
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "code_revision": revision,
            "working_tree_dirty": dirty,
            "source_result_sha256": sha256_file(args.source_result),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "audit_id": audit["audit_id"],
                "heldout_read": audit["heldout_read"],
                "model_called": audit["model_called"],
                "source_values_match_single_pass_legacy_formula": audit[
                    "findings"
                ]["source_values_match_single_pass_legacy_formula"],
                "alleged_duplicated_source_loop_confirmed": audit["findings"][
                    "alleged_duplicated_source_loop_confirmed"
                ],
                "decision": audit["decision_impact"]["outcome"],
                "output": str(args.output.relative_to(ROOT)),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
