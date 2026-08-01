#!/usr/bin/env python3
"""Compare multimodal V0-V2 on sealed development without reading held-out."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from scripts.validate_multimodal_retrieval_dataset import ROOT, validate_dataset
from src.digital_twin.evaluation.multimodal_benchmark import (
    load_sealed_development,
    sha256_file,
)
from src.digital_twin.evaluation.multimodal_retrieval import (
    bbox_iou,
    build_course_retrievers,
    query_has_retrieved_terms,
    unique_asset_hits,
    unsafe_retrieval_instruction,
)


SEALED_ROOT = ROOT / "data/processed/multimodal_retrieval_v1/sealed_v1"
DEFAULT_SEAL = SEALED_ROOT / "seal.json"
DEFAULT_LEDGER = SEALED_ROOT / "heldout_once_ledger.json"
DEFAULT_REPRESENTATIONS = (
    ROOT
    / "data/processed/multimodal_retrieval_v1/"
    "development_artifacts_v1/representations.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "experiments/runs/multimodal_retrieval_v1_development_attempt_001/result.json"
)
RUN_ID = "multimodal-retrieval-v1-development-attempt-001"
CANDIDATES = ("V0", "V1", "V2")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument(
        "--representations", type=Path, default=DEFAULT_REPRESENTATIONS
    )
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


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def asset_course_map(dataset: dict[str, Any]) -> dict[str, str]:
    return {
        asset["asset_id"]: asset["course_id"]
        for asset in dataset["source_assets"]
    }


def gold_bbox(case: dict[str, Any], assets: dict[str, dict[str, Any]]) -> tuple[float, ...]:
    regions = {
        region["region_id"]: region for region in assets[case["asset_id"]]["regions"]
    }
    return tuple(regions[case["gold_region_ids"][0]]["bbox"])


def evaluate_candidate(
    candidate: str,
    *,
    dataset: dict[str, Any],
    representation: dict[str, Any],
) -> dict[str, Any]:
    records = [
        record for asset in representation["assets"] for record in asset["records"][candidate]
    ]
    retrievers, records_by_id = build_course_retrievers(records)
    assets = {asset["asset_id"]: asset for asset in dataset["source_assets"]}
    courses = asset_course_map(dataset)
    rows = []
    latencies = []

    for case in dataset["cases"]:
        started = time.perf_counter()
        query = case["query"]
        if unsafe_retrieval_instruction(query):
            action = "refuse"
            hits = []
        else:
            course = courses[case["asset_id"]]
            hits = retrievers[course].retrieve(query, limit=10)
            top_texts = [hit.chunk.text for hit in hits[:3]]
            action = "retrieve" if query_has_retrieved_terms(query, top_texts) else "abstain"
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)

        raw_hit_rows = [
            {
                "record_id": hit.chunk.id,
                "asset_id": records_by_id[hit.chunk.id]["asset_id"],
                "bbox": records_by_id[hit.chunk.id]["bbox"],
                "kind": records_by_id[hit.chunk.id]["kind"],
                "score": hit.relevance_score,
                "raw_score": hit.raw_score,
            }
            for hit in hits
        ]
        asset_hits = unique_asset_hits(hits, records_by_id)
        page_rank = next(
            (
                index
                for index, hit in enumerate(asset_hits, start=1)
                if hit["asset_id"] == case["asset_id"]
            ),
            None,
        )
        region_iou_at_3 = 0.0
        region_iou_at_5 = 0.0
        region_ndcg_at_10 = 0.0
        if case["gold_region_ids"]:
            expected_bbox = gold_bbox(case, assets)
            relevances = []
            for index, hit in enumerate(raw_hit_rows, start=1):
                relevance = (
                    bbox_iou(tuple(hit["bbox"]), expected_bbox)
                    if hit["asset_id"] == case["asset_id"]
                    else 0.0
                )
                relevances.append(relevance)
                region_ndcg_at_10 += relevance / math.log2(index + 1)
            region_ndcg_at_10 = min(1.0, region_ndcg_at_10)
            region_iou_at_3 = max(relevances[:3], default=0.0)
            region_iou_at_5 = max(relevances[:5], default=0.0)

        row = {
            "case_id": case["case_id"],
            "slice": case["slice"],
            "modality": case["modality"],
            "expected_action": case["expected_action"],
            "actual_action": action,
            "action_correct": action == case["expected_action"],
            "page_rank": page_rank,
            "page_success_at_3": page_rank is not None and page_rank <= 3,
            "region_iou_at_3": region_iou_at_3,
            "region_iou_at_5": region_iou_at_5,
            "region_ndcg_at_10": region_ndcg_at_10,
            "complete_evidence_success_at_3": (
                page_rank is not None and page_rank <= 3 and region_iou_at_3 >= 0.1
            ),
            "atomic_evidence_recall_at_5": 1.0 if region_iou_at_5 >= 0.1 else 0.0,
            "latency_ms": latency_ms,
            "hits": raw_hit_rows,
        }
        rows.append(row)

    visual = [row for row in rows if row["slice"] == "visual_answerable"]
    controls = [row for row in rows if row["slice"] == "text_control"]
    no_evidence = [row for row in rows if row["slice"] == "no_evidence"]
    integrity = [row for row in rows if row["slice"] == "adversarial_integrity"]
    return {
        "candidate": candidate,
        "record_count": len(records),
        "metrics": {
            "visual_complete_evidence_success_at_3": mean(
                row["complete_evidence_success_at_3"] for row in visual
            ),
            "visual_atomic_evidence_recall_at_5": mean(
                row["atomic_evidence_recall_at_5"] for row in visual
            ),
            "visual_region_ndcg_at_10": mean(
                row["region_ndcg_at_10"] for row in visual
            ),
            "text_control_page_success_at_3": mean(
                row["page_success_at_3"] for row in controls
            ),
            "no_evidence_action_accuracy": mean(
                row["action_correct"] for row in no_evidence
            ),
            "integrity_action_accuracy": mean(
                row["action_correct"] for row in integrity
            ),
            "overall_action_accuracy": mean(row["action_correct"] for row in rows),
            "warm_latency_p50_ms": percentile(latencies, 0.5),
            "warm_latency_p95_ms": percentile(latencies, 0.95),
        },
        "failures": dict(
            sorted(
                Counter(
                    "ranking_or_region"
                    for row in visual
                    if not row["complete_evidence_success_at_3"]
                ).items()
            )
        ),
        "rows": rows,
    }


def main() -> int:
    args = parse_args()
    try:
        dataset, seal = load_sealed_development(
            root=ROOT, seal_path=args.seal, ledger_path=args.ledger
        )
        validate_dataset(dataset)
        representation = json.loads(args.representations.read_text(encoding="utf-8"))
        if representation["seal_id"] != seal["seal_id"]:
            raise ValueError("representation seal ID mismatch")
        if representation["development_sha256"] != seal["development_sha256"]:
            raise ValueError("representation development hash mismatch")
        if representation.get("heldout_read") is not False:
            raise ValueError("representation does not preserve held-out closure")
        revision, dirty = code_revision()
        candidates = [
            evaluate_candidate(name, dataset=dataset, representation=representation)
            for name in CANDIDATES
        ]
        output = {
            "schema_version": 1,
            "run_id": RUN_ID,
            "status": "development_complete",
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "code_revision": revision,
            "working_tree_dirty": dirty,
            "seal_id": seal["seal_id"],
            "development_sha256": seal["development_sha256"],
            "representation_path": str(args.representations.relative_to(ROOT)),
            "representation_sha256": sha256_file(args.representations),
            "candidate_versions": representation["candidate_versions"],
            "preprocessing": representation["operational"],
            "heldout_status": seal["heldout_status"],
            "heldout_read": False,
            "paid_provider_called": False,
            "external_provider_called": False,
            "case_count": len(dataset["cases"]),
            "candidates": candidates,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"multimodal development comparison failed: {error}")
        return 1

    print(
        json.dumps(
            {
                "status": output["status"],
                "run_id": RUN_ID,
                "heldout_read": False,
                "metrics": {
                    candidate["candidate"]: candidate["metrics"]
                    for candidate in candidates
                },
                "output": str(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
