#!/usr/bin/env python3
"""Validate or execute the prospective multimodal product grounding pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import time
import tracemalloc
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

import pymupdf

from src.digital_twin.evaluation.multimodal_metrics import score_multimodal_ranking
from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed
from src.digital_twin.evaluation.multimodal_retrieval import (
    bbox_iou,
    query_has_retrieved_terms,
    unsafe_retrieval_instruction,
)
from src.digital_twin.grounding import (
    ApprovalDecision,
    ApprovalRecord,
    BM25Retriever,
    EmptySourceError,
    LocalDocumentParser,
    LocalRegionCropStore,
    ModalityAwareRegionRetriever,
    OCRTextRegion,
    PageBoundedHeadingParagraphChunker,
    RegionAwareChunker,
    SourcePermissions,
    source_artifact_from_path,
)
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSTRUMENT = (
    ROOT
    / "research/05_evaluation/instruments/"
    "multimodal_product_grounding_v2_development_1_0_1.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "reports/generated/"
    "multimodal-product-grounding-v2-development-attempt-003/"
    "result.json"
)
RUN_ID = "multimodal-product-grounding-v2-development-attempt-003"
RETRIEVAL_REPEATS = 100
ANSWERABLE_SLICES = {"table", "diagram", "equation", "scan", "screenshot", "mixed"}


class InstrumentOCRProvider:
    implementation_id = "instrument-authored-ocr"
    version = "1.0.0"

    def __init__(self, regions: list[dict[str, Any]]) -> None:
        self.regions = regions
        self.call_count = 0

    def recognize(
        self,
        page_image: bytes,
        *,
        page_number: int,
        image_width: int,
        image_height: int,
    ) -> list[OCRTextRegion]:
        if not page_image or page_number < 1 or image_width < 1 or image_height < 1:
            raise ValueError("invalid rendered page supplied to synthetic OCR")
        self.call_count += 1
        return [
            OCRTextRegion(
                text=str(region["text"]),
                bounding_box=tuple(float(value) for value in region["bbox"]),
                confidence=float(region["confidence"]),
                reading_order=index,
            )
            for index, region in enumerate(self.regions)
        ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=DEFAULT_INSTRUMENT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def load_and_validate(path: Path) -> dict[str, Any]:
    instrument = json.loads(path.read_text(encoding="utf-8"))
    if "base_instrument" in instrument:
        base_path = ROOT / str(instrument["base_instrument"])
        if _sha256(base_path) != instrument.get("base_sha256"):
            raise ValueError("correction overlay base SHA-256 mismatch")
        dataset = json.loads(base_path.read_text(encoding="utf-8"))
        dataset["dataset_id"] = instrument["dataset_id"]
        replacements = instrument.get("gold_bbox_replacements", {})
        cases_by_id = {case["case_id"]: case for case in dataset["cases"]}
        if set(replacements) - set(cases_by_id):
            raise ValueError("correction overlay references an unknown case")
        for case_id, boxes in replacements.items():
            cases_by_id[case_id]["gold_bboxes"] = boxes
        dataset["correction_overlay"] = str(path.relative_to(ROOT))
        dataset["correction_reason"] = instrument.get("change_reason", "")
    else:
        dataset = instrument
    required = {
        "schema_version",
        "dataset_id",
        "split",
        "permission",
        "historical_heldout_read",
        "coordinate_format",
        "assets",
        "cases",
    }
    missing = required - set(dataset)
    if missing:
        raise ValueError(f"instrument is missing fields: {', '.join(sorted(missing))}")
    if dataset["split"] != "development":
        raise ValueError("only the new development split is permitted")
    if dataset["historical_heldout_read"] is not False:
        raise ValueError("historical held-out closure must be explicit")
    if dataset["coordinate_format"] != "normalized-x0-y0-x1-y1":
        raise ValueError("unsupported coordinate format")

    assets = dataset["assets"]
    cases = dataset["cases"]
    asset_ids = [str(asset["asset_id"]) for asset in assets]
    case_ids = [str(case["case_id"]) for case in cases]
    if len(asset_ids) != len(set(asset_ids)) or len(case_ids) != len(set(case_ids)):
        raise ValueError("asset and case identifiers must be unique")
    known_assets = set(asset_ids)
    known_courses = {str(asset["course_id"]) for asset in assets}
    for case in cases:
        if case["expected_action"] not in {"retrieve", "abstain", "refuse"}:
            raise ValueError(f"invalid expected action in {case['case_id']}")
        expected_asset = case["expected_asset_id"]
        if case["expected_action"] == "retrieve" and expected_asset not in known_assets:
            raise ValueError(f"answerable case has unknown asset: {case['case_id']}")
        if case["expected_action"] != "retrieve" and expected_asset is not None:
            raise ValueError(f"non-retrieval case declares evidence: {case['case_id']}")
        if case["course_id"] not in known_courses:
            raise ValueError(f"case has unknown course: {case['case_id']}")
        for bbox in case["gold_bboxes"]:
            if len(bbox) != 4:
                raise ValueError(f"invalid bbox length in {case['case_id']}")
            x0, y0, x1, y1 = (float(value) for value in bbox)
            if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
                raise ValueError(f"invalid normalized bbox in {case['case_id']}")
    slices = Counter(str(case["slice"]) for case in cases)
    required_slices = ANSWERABLE_SLICES | {
        "text_control",
        "no_evidence",
        "integrity",
        "isolation",
    }
    if required_slices - set(slices):
        raise ValueError("instrument does not cover every frozen slice")
    return dataset


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _code_revision() -> tuple[str, bool]:
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


def _write_asset(path: Path, asset: dict[str, Any]) -> None:
    builder = str(asset["builder"])
    pdf = pymupdf.open()
    page = pdf.new_page(width=612, height=792)
    if builder == "table":
        _draw_table(page)
    elif builder == "diagram":
        _draw_diagram(page)
    elif builder == "equation":
        page.insert_text((72, 105), "L_total = L_retrieval + L_generation", fontsize=18)
        page.insert_text((72, 205), "Q = N / T", fontsize=18)
        page.insert_text((72, 280), "Latency and throughput use separate units.")
    elif builder in {"scan", "screenshot"}:
        raster = _rasterized_text_card(
            [str(region["text"]) for region in asset.get("ocr_regions", [])]
        )
        page.insert_image(page.rect, stream=raster)
    elif builder == "mixed":
        page.insert_text((72, 65), "Mixed-layout release evaluation", fontsize=16)
        raster = _rasterized_text_card(
            [str(region["text"]) for region in asset.get("ocr_regions", [])]
        )
        page.insert_image(pymupdf.Rect(45, 120, 567, 650), stream=raster)
    elif builder == "text":
        for index, line in enumerate(asset.get("lines", [])):
            page.insert_text((72, 90 + index * 48), str(line), fontsize=12)
    else:
        pdf.close()
        raise ValueError(f"unknown asset builder: {builder}")
    pdf.save(path, no_new_id=True)
    pdf.close()


def _draw_table(page: pymupdf.Page) -> None:
    xs = [60, 220, 380, 540]
    ys = [80, 120, 160, 200]
    for x in xs:
        page.draw_line((x, ys[0]), (x, ys[-1]), color=(0, 0, 0))
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y), color=(0, 0, 0))
    rows = [
        ["Method", "Complete@3", "Recall@5"],
        ["Region-aware", "0.84", "0.93"],
        ["Page text", "0.61", "0.74"],
    ]
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            page.insert_text(
                (xs[column_index] + 5, ys[row_index] + 25),
                value,
                fontsize=10,
            )


def _draw_diagram(page: pymupdf.Page) -> None:
    boxes = [
        (pymupdf.Rect(70, 120, 200, 220), "Input PDF"),
        (pymupdf.Rect(240, 120, 370, 220), "Region parser"),
        (pymupdf.Rect(410, 120, 540, 220), "Search index"),
    ]
    for rect, label in boxes:
        page.draw_rect(rect, color=(0, 0, 0))
        page.insert_text((rect.x0 + 18, rect.y0 + 55), label, fontsize=11)
    page.draw_line((200, 170), (240, 170), color=(0, 0, 0))
    page.draw_line((370, 170), (410, 170), color=(0, 0, 0))
    page.insert_text((72, 285), "Reading order follows the arrows from left to right.")


def _rasterized_text_card(lines: list[str]) -> bytes:
    source = pymupdf.open()
    page = source.new_page(width=900, height=600)
    page.draw_rect(page.rect, color=(0.2, 0.2, 0.2), fill=(1, 1, 1))
    for index, line in enumerate(lines):
        page.insert_textbox(
            pymupdf.Rect(70, 80 + index * 190, 830, 230 + index * 190),
            line,
            fontsize=24,
        )
    rendered = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), alpha=False).tobytes("png")
    source.close()
    return rendered


def _approved_source(path: Path, asset: dict[str, Any]) -> tuple[Any, ApprovalRecord]:
    source = source_artifact_from_path(
        path,
        artifact_id=str(asset["asset_id"]),
        title=str(asset["title"]),
        version=1,
        source_label=SourceLabel.COURSE_APPROVED,
        provider_role="synthetic-professor",
    )
    approval = ApprovalRecord(
        id=f"approval-{asset['asset_id']}",
        source_artifact_id=source.id,
        source_version=1,
        decision=ApprovalDecision.APPROVED,
        permissions=SourcePermissions(
            processing_allowed=True,
            tutoring_allowed=True,
            display_allowed=True,
        ),
        reviewer_id="synthetic-professor",
        reviewer_role="professor",
        reviewed_at=datetime(2026, 8, 18, tzinfo=UTC),
        notes="Public-synthetic development instrument.",
    )
    return source, approval


def _build_candidates(
    dataset: dict[str, Any], root: Path
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    candidate_chunks: dict[str, dict[str, list[Any]]] = {
        "R0-text-page": {},
        "R3-region-routed-compact": {},
    }
    operational: dict[str, Any] = {
        "R0-text-page": {"offline_ms": [], "failures": [], "ocr_calls": 0},
        "R3-region-routed-compact": {
            "offline_ms": [],
            "failures": [],
            "ocr_calls": 0,
        },
    }
    tracemalloc.start()
    for asset in dataset["assets"]:
        path = root / f"{asset['asset_id']}.pdf"
        _write_asset(path, asset)
        source, approval = _approved_source(path, asset)
        course_id = str(asset["course_id"])

        started = time.perf_counter()
        try:
            baseline_bundle = LocalDocumentParser().parse(path, source, approval)
            baseline_chunks = PageBoundedHeadingParagraphChunker().chunk(
                baseline_bundle.document
            )
        except EmptySourceError as exc:
            baseline_chunks = []
            operational["R0-text-page"]["failures"].append(
                {"asset_id": asset["asset_id"], "failure": str(exc)}
            )
        operational["R0-text-page"]["offline_ms"].append(
            (time.perf_counter() - started) * 1000
        )
        candidate_chunks["R0-text-page"].setdefault(course_id, []).extend(
            _bind_asset(chunk, asset) for chunk in baseline_chunks
        )

        ocr_provider = (
            InstrumentOCRProvider(asset.get("ocr_regions", []))
            if asset.get("ocr_regions")
            else None
        )
        started = time.perf_counter()
        try:
            region_bundle = LocalDocumentParser(
                region_store=LocalRegionCropStore(root / "crops" / asset["asset_id"]),
                ocr_provider=ocr_provider,
            ).parse(path, source, approval)
            region_chunks = RegionAwareChunker().chunk(region_bundle)
        except Exception as exc:
            operational["R3-region-routed-compact"]["failures"].append(
                {"asset_id": asset["asset_id"], "failure": str(exc)}
            )
            region_chunks = []
        operational["R3-region-routed-compact"]["offline_ms"].append(
            (time.perf_counter() - started) * 1000
        )
        if ocr_provider is not None:
            operational["R3-region-routed-compact"]["ocr_calls"] += (
                ocr_provider.call_count
            )
        candidate_chunks["R3-region-routed-compact"].setdefault(
            course_id, []
        ).extend(
            _bind_asset(chunk, asset) for chunk in region_chunks
        )

    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    crop_bytes = sum(path.stat().st_size for path in (root / "crops").rglob("*.png"))
    retrievers = {
        "R0-text-page": {
            course: BM25Retriever(chunks)
            for course, chunks in candidate_chunks["R0-text-page"].items()
            if chunks
        },
        "R3-region-routed-compact": {
            course: ModalityAwareRegionRetriever(chunks)
            for course, chunks in candidate_chunks[
                "R3-region-routed-compact"
            ].items()
            if chunks
        },
    }
    for candidate, values in operational.items():
        timings = values.pop("offline_ms")
        values.update(
            {
                "asset_count": len(dataset["assets"]),
                "chunk_count": sum(
                    len(chunks) for chunks in candidate_chunks[candidate].values()
                ),
                "offline_mean_ms": mean(timings),
                "offline_p95_ms": _percentile(timings, 0.95),
                "peak_memory_bytes_shared_run": peak_bytes,
                "crop_bytes": (
                    crop_bytes if candidate == "R3-region-routed-compact" else 0
                ),
            }
        )
    return retrievers, operational


def _bind_asset(chunk: Any, asset: dict[str, Any]) -> Any:
    return chunk.model_copy(
        update={
            "metadata": {
                **chunk.metadata,
                "asset_id": str(asset["asset_id"]),
                "course_id": str(asset["course_id"]),
            }
        },
        deep=True,
    )


def _query_once(query: str, retriever: Any) -> tuple[str, list[Any]]:
    if unsafe_retrieval_instruction(query):
        return "refuse", []
    hits = retriever.retrieve(query, limit=10) if retriever else []
    action = (
        "retrieve"
        if query_has_retrieved_terms(query, [hit.chunk.text for hit in hits[:3]])
        else "abstain"
    )
    return action, hits


def _evaluate_candidate(
    candidate: str,
    retrievers: dict[str, Any],
    dataset: dict[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for case in dataset["cases"]:
        query = str(case["query"])
        course_id = str(case["course_id"])
        retriever = retrievers.get(course_id)
        _query_once(query, retriever)
        action = "abstain"
        hits = []
        case_latencies = []
        for repeat in range(RETRIEVAL_REPEATS):
            started = time.perf_counter()
            repeated_action, repeated_hits = _query_once(query, retriever)
            case_latencies.append((time.perf_counter() - started) * 1000)
            if repeat == 0:
                action = repeated_action
                hits = repeated_hits
        latency_ms = _percentile(case_latencies, 0.95)
        latencies.extend(case_latencies)
        hit_rows = [_hit_row(hit) for hit in hits]

        metrics = None
        expected_asset = case["expected_asset_id"]
        if expected_asset is not None:
            metrics = score_multimodal_ranking(
                hit_rows,
                expected_asset_id=str(expected_asset),
                gold_bboxes=[_xyxy_to_xywh(box) for box in case["gold_bboxes"]],
                region_iou_threshold=0.1,
            )
        fact_support = _facts_supported(case["expected_facts"], hits[:3])
        lineage_valid = _lineage_valid(hits, expected_asset)
        top1_iou = _top1_iou(hit_rows, expected_asset, case["gold_bboxes"])
        rows.append(
            {
                "case_id": case["case_id"],
                "slice": case["slice"],
                "expected_action": case["expected_action"],
                "actual_action": action,
                "action_correct": action == case["expected_action"],
                "fact_support": fact_support,
                "citation_lineage_valid": lineage_valid,
                "top1_region_iou": top1_iou,
                "metrics": metrics.as_dict() if metrics is not None else None,
                "latency_ms": latency_ms,
                "hits": hit_rows,
            }
        )

    visual = [row for row in rows if row["slice"] in ANSWERABLE_SLICES]
    tables = [row for row in rows if row["slice"] == "table"]
    text_controls = [row for row in rows if row["slice"] == "text_control"]
    no_evidence = [row for row in rows if row["slice"] == "no_evidence"]
    isolation = [row for row in rows if row["slice"] == "isolation"]
    integrity = [row for row in rows if row["slice"] == "integrity"]
    metrics = {
        "visual_complete_evidence_at_3": mean(
            row["metrics"]["complete_evidence_success_at_3"] for row in visual
        ),
        "visual_atomic_recall_at_5": mean(
            row["metrics"]["atomic_evidence_recall_at_5"] for row in visual
        ),
        "visual_region_ndcg_at_10": mean(
            row["metrics"]["region_ndcg_at_10"] for row in visual
        ),
        "visual_top1_localization_iou": mean(
            row["top1_region_iou"] for row in visual
        ),
        "table_relationship_accuracy": mean(row["fact_support"] for row in tables),
        "unsupported_description_rate": 0.0,
        "no_evidence_false_positive_rate": mean(
            row["actual_action"] == "retrieve" for row in no_evidence
        ),
        "isolation_accuracy": mean(row["action_correct"] for row in isolation),
        "integrity_accuracy": mean(row["action_correct"] for row in integrity),
        "answerable_action_accuracy": mean(
            row["action_correct"] for row in visual
        ),
        "text_control_complete_at_3": mean(
            row["metrics"]["complete_evidence_success_at_3"]
            for row in text_controls
        ),
        "text_control_atomic_recall_at_5": mean(
            row["metrics"]["atomic_evidence_recall_at_5"]
            for row in text_controls
        ),
        "citation_lineage_accuracy": mean(
            row["citation_lineage_valid"] for row in visual
        ),
        "online_vision_calls": 0,
        "retrieval_p50_ms": _percentile(latencies, 0.5),
        "retrieval_p95_ms": _percentile(latencies, 0.95),
    }
    return {
        "candidate": candidate,
        "metrics": metrics,
        "intervals": {
            "visual_complete_evidence_at_3_wilson95": _wilson_interval(
                sum(
                    row["metrics"]["complete_evidence_success_at_3"]
                    for row in visual
                ),
                len(visual),
            ),
            "table_relationship_accuracy_wilson95": _wilson_interval(
                sum(row["fact_support"] for row in tables), len(tables)
            ),
        },
        "rows": rows,
    }


def _hit_row(hit: Any) -> dict[str, Any]:
    chunk = hit.chunk
    bbox = (
        _xyxy_to_xywh(chunk.bounding_box)
        if chunk.bounding_box is not None
        else (0.0, 0.0, 1.0, 1.0)
    )
    return {
        "record_id": chunk.id,
        "asset_id": chunk.metadata["asset_id"],
        "course_id": chunk.metadata["course_id"],
        "bbox": list(bbox),
        "kind": chunk.region_kind.value if chunk.region_kind else "page-text",
        "score": hit.relevance_score,
        "raw_score": hit.raw_score,
        "region_id": chunk.region_id,
    }


def _facts_supported(expected_facts: list[str], hits: list[Any]) -> bool:
    evidence = "\n".join(hit.chunk.text for hit in hits).casefold()
    return all(str(fact).casefold() in evidence for fact in expected_facts)


def _lineage_valid(hits: list[Any], expected_asset: str | None) -> bool:
    if expected_asset is None:
        return True
    relevant = [
        hit.chunk
        for hit in hits[:5]
        if hit.chunk.metadata.get("asset_id") == expected_asset
    ]
    if not relevant:
        return False
    return all(
        chunk.source_artifact_id
        and chunk.source_version >= 1
        and chunk.source_checksum
        and chunk.page_start
        and chunk.region_id
        and chunk.bounding_box
        and chunk.crop_ref
        and chunk.display_allowed
        and chunk.metadata.get("description_is_authoritative") == "false"
        for chunk in relevant
    )


def _top1_iou(
    hits: list[dict[str, Any]],
    expected_asset: str | None,
    gold_boxes: list[list[float]],
) -> float:
    if not hits or expected_asset is None or not gold_boxes:
        return 0.0
    top = hits[0]
    if top["asset_id"] != expected_asset:
        return 0.0
    return max(
        bbox_iou(tuple(top["bbox"]), _xyxy_to_xywh(box)) for box in gold_boxes
    )


def _xyxy_to_xywh(box: Any) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = (float(value) for value in box)
    return x0, y0, x1 - x0, y1 - y0


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _wilson_interval(successes: int, total: int) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    z = 1.959963984540054
    estimate = successes / total
    denominator = 1 + z * z / total
    center = (estimate + z * z / (2 * total)) / denominator
    radius = (
        z
        * math.sqrt(
            estimate * (1 - estimate) / total + z * z / (4 * total * total)
        )
        / denominator
    )
    return [max(0.0, center - radius), min(1.0, center + radius)]


def _gate_results(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name = {candidate["candidate"]: candidate["metrics"] for candidate in candidates}
    control = by_name["R0-text-page"]
    region = by_name["R3-region-routed-compact"]
    gates = [
        ("visual_complete_evidence_at_3", region["visual_complete_evidence_at_3"] >= 0.8 and region["visual_complete_evidence_at_3"] >= control["visual_complete_evidence_at_3"]),
        ("visual_atomic_recall_at_5", region["visual_atomic_recall_at_5"] >= 0.9 and region["visual_atomic_recall_at_5"] >= control["visual_atomic_recall_at_5"]),
        ("visual_region_ndcg_at_10", region["visual_region_ndcg_at_10"] > control["visual_region_ndcg_at_10"]),
        ("visual_top1_localization_iou", region["visual_top1_localization_iou"] >= 0.7),
        ("table_relationship_accuracy", region["table_relationship_accuracy"] >= 0.9),
        ("unsupported_description_rate", region["unsupported_description_rate"] == 0),
        ("no_evidence_false_positive_rate", region["no_evidence_false_positive_rate"] <= 0.05),
        ("isolation_accuracy", region["isolation_accuracy"] == 1),
        ("text_control_no_regression", region["text_control_complete_at_3"] >= control["text_control_complete_at_3"] and region["text_control_atomic_recall_at_5"] >= control["text_control_atomic_recall_at_5"]),
        ("citation_lineage_accuracy", region["citation_lineage_accuracy"] == 1),
        ("online_vision_calls", region["online_vision_calls"] == 0),
        ("answerable_action_accuracy", region["answerable_action_accuracy"] == 1),
        ("integrity_accuracy", region["integrity_accuracy"] == 1),
        ("retrieval_p95", region["retrieval_p95_ms"] <= control["retrieval_p95_ms"] * 1.2),
    ]
    return [{"gate": name, "passed": passed} for name, passed in gates]


def main() -> int:
    args = parse_args()
    if args.execute:
        require_pre_evaluation_operation_allowed("method_evaluation_execution")
    try:
        dataset = load_and_validate(args.instrument)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(
            f"multimodal product grounding validation failed: {error}",
            file=sys.stderr,
        )
        return 1

    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "valid",
                    "dataset_id": dataset["dataset_id"],
                    "assets": len(dataset["assets"]),
                    "cases": len(dataset["cases"]),
                    "historical_heldout_read": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    try:
        with tempfile.TemporaryDirectory(prefix="multimodal-product-grounding-") as tmp:
            retrievers, operational = _build_candidates(dataset, Path(tmp))
            candidates = [
                _evaluate_candidate(candidate, candidate_retrievers, dataset)
                for candidate, candidate_retrievers in retrievers.items()
            ]
        revision, dirty = _code_revision()
        gates = _gate_results(candidates)
        status = "development_complete"
        decision = "go-deeper" if all(gate["passed"] for gate in gates) else "refine"
        result = {
            "schema_version": 1,
            "run_id": RUN_ID,
            "status": status,
            "decision": decision,
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "code_revision": revision,
            "working_tree_dirty": dirty,
            "instrument_path": str(args.instrument.relative_to(ROOT)),
            "instrument_sha256": _sha256(args.instrument),
            "dataset_id": dataset["dataset_id"],
            "case_count": len(dataset["cases"]),
            "asset_count": len(dataset["assets"]),
            "historical_heldout_read": False,
            "external_provider_called": False,
            "paid_provider_called": False,
            "heavyweight_online_vision_calls": 0,
            "candidate_versions": {
                "R0-text-page": "page-bounded-heading-paragraph+bm25-v1",
                "R3-region-routed-compact": "region-aware-local-v3+compact-modality-bm25-v1",
                "ocr": "instrument-authored-ocr-1.0.0",
                "description_provider": None,
            },
            "operational": operational,
            "retrieval_timing_repeats_per_case": RETRIEVAL_REPEATS,
            "gates": gates,
            "candidates": candidates,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception as error:
        print(f"multimodal product grounding execution failed: {error}")
        return 1

    print(
        json.dumps(
            {
                "status": result["status"],
                "decision": result["decision"],
                "historical_heldout_read": False,
                "gates": result["gates"],
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
