#!/usr/bin/env python3
"""Compare V2 and conditional V3 on failed development slices and controls."""

from __future__ import annotations

import argparse
import json
import math
import os
import resource
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from scripts.build_multimodal_visual_embeddings import (
    MODEL_NAME,
    MODEL_WEIGHT_SHA256,
    PRETRAINED_TAG,
    verified_weight_path,
)
from scripts.run_multimodal_retrieval_development import percentile
from scripts.validate_multimodal_retrieval_dataset import ROOT, validate_dataset
from src.digital_twin.evaluation.multimodal_benchmark import (
    load_sealed_development,
    sha256_file,
)
from src.digital_twin.evaluation.multimodal_retrieval import (
    bbox_iou,
    build_course_retrievers,
    query_has_retrieved_terms,
    reciprocal_rank_fuse_regions,
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
DEFAULT_EMBEDDINGS = (
    ROOT
    / "data/processed/multimodal_retrieval_v1/"
    "development_artifacts_v1/visual_embeddings.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "experiments/runs/"
    "multimodal_retrieval_v1_v3_development_attempt_002/result.json"
)
RUN_ID = "multimodal-retrieval-v1-v3-development-attempt-002"
FAILED_MODALITIES = {"table", "scanned_page"}
QUERY_PREFIX = "study material relevant to:"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument(
        "--representations", type=Path, default=DEFAULT_REPRESENTATIONS
    )
    parser.add_argument("--embeddings", type=Path, default=DEFAULT_EMBEDDINGS)
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


def scoped_cases(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        case
        for case in dataset["cases"]
        if case["slice"] != "visual_answerable"
        or case["modality"] in FAILED_MODALITIES
    ]


def gold_bbox(case: dict[str, Any], assets: dict[str, dict[str, Any]]) -> tuple[float, ...]:
    regions = {
        region["region_id"]: region for region in assets[case["asset_id"]]["regions"]
    }
    return tuple(regions[case["gold_region_ids"][0]]["bbox"])


def hit_rows_from_lexical(hits: list[Any], records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "record_id": hit.chunk.id,
            "asset_id": records[hit.chunk.id]["asset_id"],
            "bbox": records[hit.chunk.id]["bbox"],
            "kind": records[hit.chunk.id]["kind"],
            "score": hit.relevance_score,
            "raw_score": hit.raw_score,
            "channels": ["lexical"],
        }
        for hit in hits
    ]


def visual_hits(
    query_vector: list[float],
    vectors: list[dict[str, Any]],
    *,
    course_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    scored = []
    for record in vectors:
        if record["course_id"] != course_id:
            continue
        score = sum(
            left * right
            for left, right in zip(query_vector, record["embedding"], strict=True)
        )
        scored.append((score, record))
    scored.sort(key=lambda item: (-item[0], item[1]["record_id"]))
    return [
        {
            "record_id": record["record_id"],
            "asset_id": record["asset_id"],
            "bbox": record["bbox"],
            "crop_bbox": record["crop_bbox"],
            "kind": record["kind"],
            "score": (score + 1) / 2,
            "raw_score": score,
            "channels": ["visual"],
        }
        for score, record in scored[:limit]
    ]


def evaluate_candidate(
    candidate: str,
    *,
    cases: list[dict[str, Any]],
    dataset: dict[str, Any],
    representations: dict[str, Any],
    embedding_records: list[dict[str, Any]],
    encode_query: Any,
) -> dict[str, Any]:
    records = [
        record
        for asset in representations["assets"]
        for record in asset["records"]["V2"]
    ]
    retrievers, records_by_id = build_course_retrievers(records)
    assets = {asset["asset_id"]: asset for asset in dataset["source_assets"]}
    courses = {asset_id: asset["course_id"] for asset_id, asset in assets.items()}
    rows = []
    latencies = []
    query_encoding_latencies = []

    for case in cases:
        started = time.perf_counter()
        query = case["query"]
        if unsafe_retrieval_instruction(query):
            action = "refuse"
            raw_hit_rows: list[dict[str, Any]] = []
        else:
            course = courses[case["asset_id"]]
            lexical = retrievers[course].retrieve(query, limit=20)
            lexical_rows = hit_rows_from_lexical(lexical, records_by_id)
            if candidate == "V3":
                query_started = time.perf_counter()
                query_vector = encode_query(f"{QUERY_PREFIX} {query}")
                query_encoding_latencies.append(
                    (time.perf_counter() - query_started) * 1000
                )
                image_rows = visual_hits(
                    query_vector, embedding_records, course_id=course, limit=20
                )
                raw_hit_rows = reciprocal_rank_fuse_regions(
                    lexical_rows, image_rows, rank_constant=60, limit=10
                )
            else:
                raw_hit_rows = lexical_rows[:10]
            top_texts = [
                records_by_id[hit["record_id"]]["text"]
                for hit in raw_hit_rows[:3]
                if hit["record_id"] in records_by_id
            ]
            action = (
                "retrieve"
                if query_has_retrieved_terms(query, top_texts)
                else "abstain"
            )
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)

        asset_hits = []
        seen_assets: set[str] = set()
        for hit in raw_hit_rows:
            if hit["asset_id"] in seen_assets:
                continue
            seen_assets.add(hit["asset_id"])
            asset_hits.append(hit)
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
            relevances = [
                bbox_iou(tuple(hit["bbox"]), expected_bbox)
                if hit["asset_id"] == case["asset_id"]
                else 0.0
                for hit in raw_hit_rows
            ]
            region_iou_at_3 = max(relevances[:3], default=0.0)
            region_iou_at_5 = max(relevances[:5], default=0.0)
            region_ndcg_at_10 = min(
                1.0,
                sum(
                    relevance / math.log2(index + 1)
                    for index, relevance in enumerate(relevances, start=1)
                ),
            )
        rows.append(
            {
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
        )

    visual = [row for row in rows if row["slice"] == "visual_answerable"]
    controls = [row for row in rows if row["slice"] == "text_control"]
    no_evidence = [row for row in rows if row["slice"] == "no_evidence"]
    integrity = [row for row in rows if row["slice"] == "adversarial_integrity"]
    return {
        "candidate": candidate,
        "scope_case_count": len(rows),
        "metrics": {
            "failed_slice_complete_evidence_success_at_3": mean(
                row["complete_evidence_success_at_3"] for row in visual
            ),
            "failed_slice_atomic_evidence_recall_at_5": mean(
                row["atomic_evidence_recall_at_5"] for row in visual
            ),
            "failed_slice_region_ndcg_at_10": mean(
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
            "query_encoding_p50_ms": percentile(query_encoding_latencies, 0.5),
            "query_encoding_p95_ms": percentile(query_encoding_latencies, 0.95),
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
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        verified_weight_path()
        dataset, seal = load_sealed_development(
            root=ROOT, seal_path=args.seal, ledger_path=args.ledger
        )
        validate_dataset(dataset)
        representations = json.loads(args.representations.read_text(encoding="utf-8"))
        embeddings = json.loads(args.embeddings.read_text(encoding="utf-8"))
        for artifact in (representations, embeddings):
            if artifact["seal_id"] != seal["seal_id"]:
                raise ValueError("artifact seal ID mismatch")
            if artifact["development_sha256"] != seal["development_sha256"]:
                raise ValueError("artifact development hash mismatch")
            if artifact.get("heldout_read") is not False:
                raise ValueError("artifact does not preserve held-out closure")
        if embeddings["representations_sha256"] != sha256_file(args.representations):
            raise ValueError("visual embeddings are bound to another representation")
        if embeddings["provider"]["weight_sha256"] != MODEL_WEIGHT_SHA256:
            raise ValueError("visual embedding model hash mismatch")

        import open_clip
        import torch

        load_started = time.perf_counter()
        model = open_clip.create_model(
            MODEL_NAME, pretrained=PRETRAINED_TAG, device="cpu"
        )
        model.eval()
        tokenizer = open_clip.get_tokenizer(MODEL_NAME)
        model_load_seconds = time.perf_counter() - load_started

        def encode_query(text: str) -> list[float]:
            tokens = tokenizer([text])
            with torch.inference_mode():
                vector = model.encode_text(tokens)
                vector = vector / vector.norm(dim=-1, keepdim=True)
            return vector[0].float().tolist()

        encode_query(f"{QUERY_PREFIX} warmup")
        cases = scoped_cases(dataset)
        candidates = [
            evaluate_candidate(
                name,
                cases=cases,
                dataset=dataset,
                representations=representations,
                embedding_records=embeddings["vectors"],
                encode_query=encode_query,
            )
            for name in ("V2", "V3")
        ]
        revision, dirty = code_revision()
        output = {
            "schema_version": 1,
            "run_id": RUN_ID,
            "status": "development_complete",
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "code_revision": revision,
            "working_tree_dirty": dirty,
            "seal_id": seal["seal_id"],
            "development_sha256": seal["development_sha256"],
            "representations_sha256": sha256_file(args.representations),
            "visual_embeddings_sha256": sha256_file(args.embeddings),
            "candidate_versions": {
                "V2": representations["candidate_versions"]["V2"],
                "V3": embeddings["candidate_version"],
            },
            "scope": {
                "failed_visual_modalities": sorted(FAILED_MODALITIES),
                "fixed_controls": [
                    "text_control",
                    "no_evidence",
                    "adversarial_integrity",
                ],
                "case_count": len(cases),
            },
            "query_encoder": {
                "model": MODEL_NAME,
                "pretrained_tag": PRETRAINED_TAG,
                "weight_sha256": MODEL_WEIGHT_SHA256,
                "device": "cpu",
                "model_load_seconds": model_load_seconds,
                "model_parameters": sum(
                    parameter.numel() for parameter in model.parameters()
                ),
                "peak_rss_bytes": resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss,
            },
            "heldout_status": seal["heldout_status"],
            "heldout_read": False,
            "paid_provider_called": False,
            "external_provider_called": False,
            "candidates": candidates,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
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
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"multimodal V3 development comparison failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
