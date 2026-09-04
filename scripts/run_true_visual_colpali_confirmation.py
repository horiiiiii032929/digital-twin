#!/usr/bin/env python3
"""Validate, simulate, preflight, or run the ColPali-style visual successor."""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Awaitable, Callable
from xml.etree import ElementTree

from dotenv import load_dotenv

from scripts import build_true_visual_colpali_confirmation as builder
from src.digital_twin.evaluation.finite_program_io import atomic_write_json
from src.digital_twin.evaluation.provider_json import (
    ProviderCallLedgerV1,
    ProviderJsonError,
    ProviderJsonResponse,
    canonical_sha256,
)
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.retrieval import BM25Retriever
from src.digital_twin.grounding.visual_late_interaction import (
    JINA_EMBEDDING_ENDPOINT,
    JINA_INPUT_TOKEN_PRICE_USD,
    JINA_MAX_INPUT_BYTES,
    JINA_MAX_INPUT_TOKENS,
    JINA_VISUAL_MODEL,
    JinaVisualMultiVectorProvider,
    MultiVector,
    VisualEmbeddingResultV1,
    VisualLateInteractionIndexV1,
    VisualRegionEmbeddingV1,
)
from src.digital_twin.repository_freeze import (
    RepositoryFreezeError,
    require_bounded_pilot_operation_allowed,
)
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = ROOT / "research/05_evaluation/instruments/true_visual_colpali_confirmation_001.json"
DATASET_PATH = ROOT / "research/05_evaluation/datasets/true_visual_colpali_confirmation_001.json"
DEFAULT_OUTPUT_ROOT = ROOT / "reports/generated/true-visual-colpali-confirmation-001"
GENERATED_ROOT = (ROOT / "reports/generated").resolve()
RUN_ID = "true-visual-colpali-confirmation-001"


class TrueVisualColpaliError(RuntimeError):
    """Raised when the successor cannot produce interpretable evidence."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TrueVisualColpaliError(f"JSON root must be an object: {path.name}")
    return value


def _instrument() -> dict[str, Any]:
    value = _load(INSTRUMENT_PATH)
    binding = value.get("provider_binding", {})
    if (
        value.get("instrument_id") != RUN_ID
        or value.get("dataset_id") != builder.DATASET_ID
        or binding.get("provider") != "jina-ai-first-party"
        or binding.get("api_url") != JINA_EMBEDDING_ENDPOINT
        or binding.get("model") != JINA_VISUAL_MODEL
        or binding.get("task_query") != "retrieval.query"
        or binding.get("task_passage") != "retrieval.passage"
        or binding.get("return_multivector") is not True
        or binding.get("truncate") is not False
        or binding.get("maximum_calls") != 60
        or binding.get("maximum_transport_retries") != 0
        or float(binding.get("maximum_cost_usd", -1)) != 1.0
        or int(binding.get("maximum_input_bytes", -1)) != JINA_MAX_INPUT_BYTES
        or int(binding.get("maximum_input_tokens", -1)) != JINA_MAX_INPUT_TOKENS
        or float(binding.get("input_price_usd_per_token", -1))
        != JINA_INPUT_TOKEN_PRICE_USD
        or binding.get("metadata_schema_version") != "2026.07.27.1603"
        or value.get("private_data_authorized") is not False
    ):
        raise TrueVisualColpaliError("ColPali visual instrument drifted")
    return value


def _metadata_is_fresh(instrument: dict[str, Any]) -> bool:
    raw = instrument["provider_binding"].get("metadata_verified_at")
    if not isinstance(raw, str):
        return False
    try:
        verified = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    age = datetime.now(timezone.utc) - verified.astimezone(timezone.utc)
    return 0 <= age.total_seconds() <= 24 * 60 * 60


def _dataset() -> dict[str, Any]:
    value = _load(DATASET_PATH)
    builder.validate_dataset(value)
    if builder.build_dataset(write_assets=False) != value:
        raise TrueVisualColpaliError("visual dataset reconstruction drifted")
    return value


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def _git_clean() -> bool:
    return not subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def _render_path(asset: dict[str, Any]) -> Path:
    path = (ROOT / asset["render_path"]).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise TrueVisualColpaliError(f"visual render is missing: {asset['asset_id']}")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != asset["render_sha256"]:
        raise TrueVisualColpaliError(f"visual render hash drifted: {asset['asset_id']}")
    return path


def _visible_text_by_asset(dataset: dict[str, Any]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for index, asset in enumerate(dataset["assets"], start=1):
        if index <= 10:
            text = " ".join(value for row in builder.TABLES[index - 1].rows for value in row)
        elif index <= 20:
            text = builder.EQUATIONS[index - 11].display
        else:
            image = ROOT / asset["render_path"]
            svg = image.with_suffix(".svg")
            if not svg.is_file():
                raise TrueVisualColpaliError(f"born-digital control SVG is missing: {asset['asset_id']}")
            root = ElementTree.fromstring(svg.read_bytes())
            text = " ".join(" ".join(root.itertext()).split())
        if not text.strip():
            raise TrueVisualColpaliError(f"visible-text control is empty: {asset['asset_id']}")
        texts[asset["asset_id"]] = text
    return texts


def _control_rankings(dataset: dict[str, Any]) -> dict[str, list[str]]:
    visible = _visible_text_by_asset(dataset)
    by_course: dict[str, list[DocumentChunk]] = defaultdict(list)
    for index, asset in enumerate(dataset["assets"]):
        by_course[asset["course_id"]].append(
            DocumentChunk(
                id=asset["asset_id"],
                document_id=asset["source_artifact_id"],
                source_artifact_id=asset["source_artifact_id"],
                source_version=1,
                source_label=SourceLabel.COURSE_APPROVED,
                text=visible[asset["asset_id"]],
                ordinal=index,
                region_id=asset["region_lineage"][0]["region_id"],
                retrieval_allowed=True,
                display_allowed=True,
                metadata={"source_commit": asset["source_version"]},
            )
        )
    retrievers = {course: BM25Retriever(chunks) for course, chunks in by_course.items()}
    rankings: dict[str, list[str]] = {}
    for case in dataset["cases"]:
        if case["expected_action"] != "answer":
            continue
        hits = retrievers[case["course_id"]].retrieve(case["question"], limit=5)
        rankings[case["case_id"]] = [hit.chunk.id for hit in hits]
    return rankings


def _score_rankings(dataset: dict[str, Any], rankings: dict[str, list[str]]) -> dict[str, Any]:
    answerable = [case for case in dataset["cases"] if case["expected_action"] == "answer"]
    per_modality: dict[str, list[bool]] = defaultdict(list)
    at_3 = 0
    at_5 = 0
    for case in answerable:
        ranked = rankings.get(case["case_id"], [])
        required = case["required_asset_ids"][0]
        found_3 = required in ranked[:3]
        found_5 = required in ranked[:5]
        at_3 += found_3
        at_5 += found_5
        per_modality[case["modality"]].append(found_3)
    total = len(answerable)
    return {
        "answerable_cases": total,
        "complete_visual_evidence_at_3_count": at_3,
        "complete_visual_evidence_at_3": at_3 / total,
        "visual_evidence_recall_at_5_count": at_5,
        "visual_evidence_recall_at_5": at_5 / total,
        "per_modality_evidence_at_3": {
            modality: sum(values) / len(values) for modality, values in sorted(per_modality.items())
        },
    }


def _quality(
    dataset: dict[str, Any],
    candidate_rankings: dict[str, list[str]],
    candidate_lineage_valid: bool,
    instrument: dict[str, Any],
) -> dict[str, Any]:
    candidate = _score_rankings(dataset, candidate_rankings)
    control = _score_rankings(dataset, _control_rankings(dataset))
    gates = instrument["quality_gates"]
    diagram_delta = (
        candidate["per_modality_evidence_at_3"]["diagram"]
        - control["per_modality_evidence_at_3"]["diagram"]
    )
    passed = (
        candidate["complete_visual_evidence_at_3"] >= gates["candidate_complete_visual_evidence_at_3_min"]
        and candidate["visual_evidence_recall_at_5"] >= gates["candidate_visual_evidence_recall_at_5_min"]
        and min(candidate["per_modality_evidence_at_3"].values()) >= gates["candidate_per_modality_evidence_at_3_min"]
        and candidate_lineage_valid
        and diagram_delta >= gates["candidate_diagram_improvement_over_control_min"]
    )
    return {
        "status": "completed-go-deeper" if passed else "completed-refine",
        "decision": "Go Deeper" if passed else "Refine",
        "quality_gates_passed": passed,
        "candidate": candidate,
        "control": control,
        "candidate_diagram_improvement_over_control": diagram_delta,
        "candidate_original_region_lineage": 1.0 if candidate_lineage_valid else 0.0,
        "candidate_exact_course_isolation": 1.0,
        "boundary_evaluation_status": "deferred-to-actual-product-checkpoint",
        "boundary_provider_calls": 0,
    }


def _fake_vectors(index: int, *, dimensions: int = 30) -> MultiVector:
    row = tuple(1.0 if position == index else 0.0 for position in range(dimensions))
    return (row,)


def _candidate_rankings(
    dataset: dict[str, Any],
    image_vectors: dict[str, MultiVector],
    query_vectors: dict[str, MultiVector],
) -> tuple[dict[str, list[str]], bool]:
    records: list[VisualRegionEmbeddingV1] = []
    asset_by_id = {asset["asset_id"]: asset for asset in dataset["assets"]}
    for asset in dataset["assets"]:
        region = asset["region_lineage"][0]
        records.append(
            VisualRegionEmbeddingV1(
                record_id=region["region_id"],
                course_id=asset["course_id"],
                source_artifact_id=asset["source_artifact_id"],
                source_version=asset["source_version"],
                source_sha256=asset["source_sha256"],
                asset_id=asset["asset_id"],
                region_id=region["region_id"],
                render_sha256=asset["render_sha256"],
                bbox=tuple(region["bbox"]),
                modality=asset["modality"],
                vectors=image_vectors[asset["asset_id"]],
            )
        )
    index = VisualLateInteractionIndexV1(records)
    rankings: dict[str, list[str]] = {}
    lineage_valid = True
    for case in dataset["cases"]:
        if case["expected_action"] != "answer":
            continue
        hits = index.retrieve(course_id=case["course_id"], query_vectors=query_vectors[case["case_id"]], limit=5)
        rankings[case["case_id"]] = [hit["asset_id"] for hit in hits]
        required = case["required_asset_ids"][0]
        matched = next((hit for hit in hits if hit["asset_id"] == required), None)
        authority = asset_by_id[required]
        lineage_valid = lineage_valid and matched is not None and (
            matched["source_artifact_id"] == authority["source_artifact_id"]
            and matched["source_version"] == authority["source_version"]
            and matched["source_sha256"] == authority["source_sha256"]
            and matched["region_id"] == authority["region_lineage"][0]["region_id"]
            and matched["render_sha256"] == authority["render_sha256"]
        )
    return rankings, lineage_valid


def validate() -> dict[str, Any]:
    instrument = _instrument()
    dataset = _dataset()
    for asset in dataset["assets"]:
        _render_path(asset)
    provider = JinaVisualMultiVectorProvider(api_key="validation-only")
    query = provider.query_payload("Which node follows A?")
    image = provider.image_payload(b"\x89PNG\r\n\x1a\n", mime_type="image/png")
    if query["return_multivector"] is not True or image["task"] != "retrieval.passage":
        raise TrueVisualColpaliError("provider request contract drifted")
    return {
        "status": "passed-build-only",
        "run_id": RUN_ID,
        "assets": len(dataset["assets"]),
        "cases": len(dataset["cases"]),
        "instrument_sha256": canonical_sha256(instrument),
        "dataset_sha256": dataset["content_sha256"],
        "provider_calls": 0,
        "paid_execution_authorized": instrument["paid_execution_authorized"],
    }


def simulate() -> dict[str, Any]:
    instrument = _instrument()
    dataset = _dataset()
    image_vectors = {
        asset["asset_id"]: _fake_vectors(index)
        for index, asset in enumerate(dataset["assets"])
    }
    asset_position = {asset["asset_id"]: index for index, asset in enumerate(dataset["assets"])}
    query_vectors = {
        case["case_id"]: _fake_vectors(asset_position[case["required_asset_ids"][0]])
        for case in dataset["cases"]
        if case["expected_action"] == "answer"
    }
    rankings, lineage = _candidate_rankings(dataset, image_vectors, query_vectors)
    return {
        "run_id": RUN_ID,
        "execution_mode": "network-free-simulation",
        "provider_calls": 0,
        **_quality(dataset, rankings, lineage, instrument),
    }


def preflight() -> dict[str, Any]:
    validation = validate()
    instrument = _instrument()
    reasons: list[str] = []
    if not instrument["paid_execution_authorized"] or not instrument["provider_execution_authorized"]:
        reasons.append("checkpoint is not provider-authorized")
    if not _metadata_is_fresh(instrument):
        reasons.append("provider metadata is older than 24 hours")
    if not os.getenv("JINA_API_KEY", "").strip():
        reasons.append("JINA_API_KEY is missing")
    if not _git_clean():
        reasons.append("git worktree is not clean")
    if (DEFAULT_OUTPUT_ROOT / "provider-ledger.sqlite3").exists():
        reasons.append("exclusive provider ledger path already exists")
    return {
        **validation,
        "status": "ready" if not reasons else "blocked",
        "reasons": reasons,
        "network_calls_made": 0,
        "code_revision": _git_revision(),
    }


async def _call_and_record(
    *,
    provider: JinaVisualMultiVectorProvider,
    ledger: ProviderCallLedgerV1,
    request_key: str,
    payload: dict[str, Any],
    call: Callable[[], Awaitable[VisualEmbeddingResultV1]],
) -> MultiVector:
    request_sha256 = canonical_sha256(payload)
    replayed = ledger.replay(request_key=request_key, request_sha256=request_sha256)
    if replayed is not None:
        return tuple(tuple(float(value) for value in row) for row in replayed.content["vectors"])
    ledger.reserve(
        estimated_cost_usd=JINA_MAX_INPUT_TOKENS * JINA_INPUT_TOKEN_PRICE_USD
    )
    started = time.perf_counter()
    try:
        result = await call()
    except Exception as error:
        latency = (time.perf_counter() - started) * 1000
        ledger.record_failed(
            request_key=request_key,
            request_sha256=request_sha256,
            provider_role="visual-retrieval",
            failure_type=type(error).__name__,
            failure_detail=str(error),
            latency_ms=latency,
        )
        raise
    latency = (time.perf_counter() - started) * 1000
    ledger.record_completed(
        request_key=request_key,
        request_sha256=request_sha256,
        provider_role="visual-retrieval",
        response=ProviderJsonResponse(
            content={"vectors": [list(row) for row in result.vectors]},
            provider_model=result.model,
            input_tokens=result.usage.total_tokens,
            output_tokens=0,
            cost_usd=result.usage.total_tokens * JINA_INPUT_TOKEN_PRICE_USD,
            latency_ms=latency,
        ),
    )
    return result.vectors


async def execute(*, resume: bool, output_root: Path) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(RUN_ID, "external_model_evaluation")
    instrument = _instrument()
    if not instrument["paid_execution_authorized"] or not instrument["provider_execution_authorized"]:
        raise TrueVisualColpaliError("instrument is not provider-authorized")
    if not _metadata_is_fresh(instrument):
        raise TrueVisualColpaliError("provider metadata is older than 24 hours")
    if not _git_clean():
        raise TrueVisualColpaliError("provider execution requires a clean worktree")
    key = os.getenv("JINA_API_KEY", "").strip()
    if not key:
        raise TrueVisualColpaliError("JINA_API_KEY is missing")
    resolved = output_root.resolve()
    if not resolved.is_relative_to(GENERATED_ROOT):
        raise TrueVisualColpaliError("output must remain under reports/generated")
    dataset = _dataset()
    binding = {
        "run_id": RUN_ID,
        "instrument_sha256": canonical_sha256(instrument),
        "dataset_sha256": dataset["content_sha256"],
        "code_revision": _git_revision(),
        "provider": "jina-ai-first-party",
        "model": JINA_VISUAL_MODEL,
        "endpoint": JINA_EMBEDDING_ENDPOINT,
    }
    ledger = ProviderCallLedgerV1(
        resolved / "provider-ledger.sqlite3",
        run_binding=binding,
        maximum_calls=60,
        maximum_cost_usd=1.0,
        resume=resume,
    )
    provider = JinaVisualMultiVectorProvider(api_key=key)
    try:
        answerable_cases = [
            case for case in dataset["cases"] if case["expected_action"] == "answer"
        ]
        first_asset = dataset["assets"][0]
        first_case = answerable_cases[0]
        image_vectors: dict[str, MultiVector] = {}
        first_path = _render_path(first_asset)
        first_raw = first_path.read_bytes()
        first_image_payload = provider.image_payload(first_raw, mime_type="image/png")
        image_vectors[first_asset["asset_id"]] = await _call_and_record(
            provider=provider,
            ledger=ledger,
            request_key=f"image:{first_asset['asset_id']}",
            payload=first_image_payload,
            call=lambda: provider.embed_image(first_raw, mime_type="image/png"),
        )
        query_vectors: dict[str, MultiVector] = {}
        first_query_payload = provider.query_payload(first_case["question"])
        query_vectors[first_case["case_id"]] = await _call_and_record(
            provider=provider,
            ledger=ledger,
            request_key=f"query:{first_case['case_id']}",
            payload=first_query_payload,
            call=lambda: provider.embed_query(first_case["question"]),
        )
        for asset in dataset["assets"][1:]:
            path = _render_path(asset)
            raw = path.read_bytes()
            payload = provider.image_payload(raw, mime_type="image/png")
            image_vectors[asset["asset_id"]] = await _call_and_record(
                provider=provider,
                ledger=ledger,
                request_key=f"image:{asset['asset_id']}",
                payload=payload,
                call=lambda raw=raw: provider.embed_image(raw, mime_type="image/png"),
            )
        for case in answerable_cases[1:]:
            payload = provider.query_payload(case["question"])
            query_vectors[case["case_id"]] = await _call_and_record(
                provider=provider,
                ledger=ledger,
                request_key=f"query:{case['case_id']}",
                payload=payload,
                call=lambda question=case["question"]: provider.embed_query(question),
            )
        rankings, lineage = _candidate_rankings(dataset, image_vectors, query_vectors)
        quality = _quality(dataset, rankings, lineage, instrument)
        ledger.mark_complete()
        result = {
            "schema_version": "1.0.0",
            "run_id": RUN_ID,
            "execution_mode": "live-jina-multivector",
            "binding": binding,
            "quality": quality,
            "provider": ledger.snapshot(),
            "limitations": [
                "Fresh public educational visual sample; not representative professor material.",
                "Retrieval and original-region lineage are evaluated here; answer generation is a separate product checkpoint.",
                "Jina embeddings are ranking features and never authoritative source truth.",
            ],
        }
        atomic_write_json(resolved / "result.json", result)
        return result
    except Exception:
        try:
            ledger.mark_interrupted()
        except ProviderJsonError:
            pass
        raise
    finally:
        ledger.close()


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    if args.execute:
        require_bounded_pilot_operation_allowed(RUN_ID, "external_model_evaluation")
    try:
        if args.validate:
            result = validate()
        elif args.simulate:
            result = simulate()
        elif args.preflight:
            result = preflight()
        else:
            result = asyncio.run(execute(resume=args.resume, output_root=args.output_root))
    except (RepositoryFreezeError, TrueVisualColpaliError, ProviderJsonError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
