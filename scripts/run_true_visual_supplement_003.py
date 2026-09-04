#!/usr/bin/env python3
"""Run the method-level successor to the invalid visual supplement attempts."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Callable

from dotenv import load_dotenv

from scripts import build_academic_factual_qa_visual_supplement as visual_builder
from scripts import run_course_digital_twin_nonhuman_supplements as historical
from src.digital_twin.evaluation.finite_program_io import atomic_write_json
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
    ProviderJsonResponse,
    canonical_sha256,
)
from src.digital_twin.repository_freeze import (
    RepositoryFreezeError,
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = ROOT / "research/05_evaluation/instruments/true_visual_supplement_003.json"
DATASET_PATH = ROOT / "research/05_evaluation/datasets/academic_factual_qa_visual_supplement_001.json"
DEFAULT_OUTPUT_ROOT = ROOT / "reports/generated/true-visual-supplement-003"
GENERATED_ROOT = (ROOT / "reports/generated").resolve()
RUN_ID = "true-visual-supplement-003"
LEDGER_NAME = "provider-ledger.sqlite3"
RESULT_NAME = "result.json"
_SPACE = re.compile(r"\s+")


class TrueVisualSupplementError(RuntimeError):
    """Raised when supplement 003 cannot produce interpretable evidence."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TrueVisualSupplementError(f"JSON root is not an object: {path.name}")
    return value


def _instrument() -> dict[str, Any]:
    value = _load(INSTRUMENT_PATH)
    binding = value.get("provider_binding", {})
    if (
        value.get("instrument_id") != RUN_ID
        or value.get("dataset_id") != "academic-factual-qa-visual-supplement-001"
        or binding.get("provider") != "openai"
        or binding.get("api_url") != "https://api.openai.com/v1/responses"
        or binding.get("model") != historical.VISUAL_MODEL
        or binding.get("request_store") is not False
        or binding.get("maximum_calls") != 30
        or binding.get("maximum_transport_retries") != 0
        or float(binding.get("maximum_cost_usd", -1)) != 2.0
        or value.get("private_data_authorized") is not False
    ):
        raise TrueVisualSupplementError("visual successor instrument drifted")
    return value


def _dataset() -> dict[str, Any]:
    value = _load(DATASET_PATH)
    visual_builder.validate_dataset(value)
    if visual_builder.build_dataset(write_assets=False) != value:
        raise TrueVisualSupplementError("visual dataset reconstruction drifted")
    return value


def _provider_binding(instrument: dict[str, Any]) -> dict[str, Any]:
    source = instrument["provider_binding"]
    return {
        "binding_id": "true-visual-supplement-003-openai-nano-v1",
        "provider": "openai",
        "provider_display_name": "OpenAI",
        "first_party_endpoint": True,
        "api_url": source["api_url"],
        "credential_environment_variable": source["credential_environment_variable"],
        "provider_model": source["model"],
        "documented_revision": source["model"],
        "reasoning_effort": source["reasoning_effort"],
        "max_output_tokens": source["maximum_output_tokens"],
        "timeout_seconds": 120,
        "maximum_transport_retries": source["maximum_transport_retries"],
        "pricing_usd_per_million_input_tokens": source["input_price_usd_per_million"],
        "pricing_usd_per_million_output_tokens": source["output_price_usd_per_million"],
        "request_store": False,
    }


def _canonicalize_list(values: list[Any]) -> tuple[list[str], int]:
    result: list[str] = []
    seen: set[str] = set()
    removed = 0
    for raw in values:
        value = _SPACE.sub(" ", str(raw)).strip()
        if not value:
            removed += 1
            continue
        key = value.casefold()
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        result.append(value)
    return result, removed


def _description_record(
    asset: dict[str, Any],
    response: ProviderJsonResponse,
    *,
    transmitted_image_sha256: str,
) -> dict[str, Any]:
    if response.provider_model != historical.VISUAL_MODEL or response.attempt_count != 1:
        raise TrueVisualSupplementError("visual provider identity or retry drifted")
    content = response.content
    normalized: dict[str, list[str]] = {}
    removed: dict[str, int] = {}
    for field in ("entities", "relationships", "uncertainty"):
        values = content.get(field)
        if not isinstance(values, list):
            raise TrueVisualSupplementError("visual semantic list is malformed")
        normalized[field], removed[field] = _canonicalize_list(values)
    transcription = _SPACE.sub(" ", str(content.get("transcription", ""))).strip()
    if not transcription:
        raise TrueVisualSupplementError("visual transcription is empty")
    segments = [transcription, *normalized["entities"], *normalized["relationships"]]
    return {
        "asset_id": asset["asset_id"],
        "course_id": asset["course_id"],
        "modality": asset["modality"],
        "source_document_path": asset["source_document_path"],
        "source_image_sha256": asset["render_sha256"],
        "transmitted_image_sha256": transmitted_image_sha256,
        "expected_transmitted_image_sha256": transmitted_image_sha256,
        "region_ids": [row["region_id"] for row in asset["region_lineage"]],
        "description_text": "\n".join(segments),
        "description_segments": segments,
        "semantic_list_duplicate_removals": removed,
        "semantic_list_duplicate_removal_count": sum(removed.values()),
    }


def _run_binding(instrument: dict[str, Any], dataset: dict[str, Any], revision: str) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "instrument_sha256": canonical_sha256(instrument),
        "dataset_sha256": dataset["content_sha256"],
        "provider_binding": _provider_binding(instrument),
        "code_revision": revision,
        "private_data_used": False,
    }


def validate() -> dict[str, Any]:
    instrument = _instrument()
    dataset = _dataset()
    binding = _provider_binding(instrument)
    payload = DirectProviderJsonTransport(binding)._payload(  # noqa: SLF001
        system="validation",
        prompt="validation",
        task="true-visual-supplement-003-validation",
        schema=historical._visual_schema(),
        image_data_urls=["data:image/png;base64,AA=="],
    )
    if payload.get("model") != historical.VISUAL_MODEL or payload.get("store") is not False:
        raise TrueVisualSupplementError("OpenAI request contract drifted")
    return {
        "status": "passed-build-only",
        "run_id": RUN_ID,
        "asset_count": len(dataset["assets"]),
        "case_count": len(dataset["cases"]),
        "instrument_sha256": canonical_sha256(instrument),
        "dataset_sha256": dataset["content_sha256"],
        "provider_calls": 0,
        "paid_execution_authorized": instrument["paid_execution_authorized"],
        "private_data_used": False,
    }


def _quality(dataset: dict[str, Any], descriptions: list[dict[str, Any]], instrument: dict[str, Any]) -> dict[str, Any]:
    metrics = historical._visual_retrieval_metrics(dataset, descriptions, generated=True)
    gates = instrument["quality_gates"]
    passed = (
        metrics["complete_evidence_at_3"] >= gates["complete_visual_evidence_at_3_min"]
        and metrics["answerable_fact_complete_count"] >= gates["complete_visual_fact_cases_min"]
        and metrics["answerable_visual_fact_recall"] >= gates["mean_visual_fact_recall_min"]
        and metrics["answerable_visual_fact_precision"] >= gates["mean_visual_fact_precision_min"]
        and metrics["unsupported_visual_fact_count"] <= gates["unsupported_visual_facts_max"]
        and metrics["boundary_policy_accuracy"] >= gates["boundary_policy_accuracy_min"]
        and metrics["boundary_release_count"] <= gates["boundary_releases_max"]
        and metrics["original_region_lineage_rate"] >= gates["original_region_lineage_min"]
    )
    return {
        "status": "completed-go-deeper" if passed else "completed-refine",
        "decision": "Go Deeper" if passed else "Refine",
        "quality_gates_passed": passed,
        "metrics": metrics,
        "semantic_list_duplicate_removal_count": sum(
            row["semantic_list_duplicate_removal_count"] for row in descriptions
        ),
        "assets_with_duplicate_removals": sum(
            row["semantic_list_duplicate_removal_count"] > 0 for row in descriptions
        ),
    }


def simulate() -> dict[str, Any]:
    instrument = _instrument()
    dataset = _dataset()
    case_by_asset = {
        case["required_asset_ids"][0]: case
        for case in dataset["cases"]
        if case["expected_action"] == "answer"
    }
    descriptions = []
    for asset in dataset["assets"]:
        row = historical._simulated_description(asset, case_by_asset, passing=True)
        row["semantic_list_duplicate_removals"] = {"entities": 0, "relationships": 0, "uncertainty": 0}
        row["semantic_list_duplicate_removal_count"] = 0
        descriptions.append(row)
    return {
        "run_id": RUN_ID,
        "simulation": True,
        "provider_calls": 0,
        **_quality(dataset, descriptions, instrument),
    }


def _repo_revision() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def _repo_dirty() -> bool:
    return bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip())


def preflight(*, output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    result = validate()
    instrument = _instrument()
    blockers: list[str] = []
    if instrument.get("provider_execution_authorized") is not True or instrument.get("paid_execution_authorized") is not True:
        blockers.append("paid-execution-not-authorized")
    try:
        require_bounded_pilot_operation_allowed(RUN_ID, "external_model_evaluation")
        require_bounded_pilot_operation_allowed(RUN_ID, "method_evaluation_execution")
    except RepositoryFreezeError:
        blockers.append("execution-freeze-authorization-missing")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-api-key-missing")
    if _repo_dirty():
        blockers.append("repository-dirty")
    if shutil.which("rsvg-convert") is None:
        blockers.append("verified-svg-renderer-missing")
    if output_root.exists():
        blockers.append("exclusive-output-root-used")
    if not output_root.resolve().is_relative_to(GENERATED_ROOT) or output_root.resolve() == GENERATED_ROOT:
        blockers.append("unsafe-output-root")
    if instrument["provider_binding"]["metadata_refresh_required_before_paid_execution"] is True:
        blockers.append("provider-metadata-refresh-required")
    return {**result, "status": "ready" if not blockers else "blocked", "blockers": sorted(set(blockers))}


async def execute(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    transport_factory: Callable[[dict[str, Any]], Any] = DirectProviderJsonTransport,
) -> dict[str, Any]:
    readiness = preflight(output_root=output_root)
    if readiness["status"] != "ready":
        raise TrueVisualSupplementError("preflight blocked: " + ", ".join(readiness["blockers"]))
    instrument = _instrument()
    dataset = _dataset()
    binding = _provider_binding(instrument)
    visual_builder.build_dataset(write_assets=True)
    output_root.mkdir(parents=True, exist_ok=False)
    revision = _repo_revision()
    ledger = ProviderCallLedgerV1(
        output_root / LEDGER_NAME,
        run_binding=_run_binding(instrument, dataset, revision),
        maximum_calls=30,
        maximum_cost_usd=2.0,
        resume=False,
        maximum_transport_retries_total=0,
    )
    transport = transport_factory(binding)
    descriptions: list[dict[str, Any]] = []
    try:
        for asset in sorted(dataset["assets"], key=lambda row: row["asset_id"]):
            image_data_url = historical._image_data_url(asset, output_root)
            image_hash = historical._image_data_sha256(image_data_url)
            system, prompt = historical._visual_prompt(asset)
            response = await transport.call_with_ledger(
                ledger=ledger,
                request_key=f"visual-{asset['asset_id']}",
                provider_role="question-independent-visual-description",
                system=system,
                prompt=prompt,
                task=RUN_ID,
                schema=historical._visual_schema(),
                image_data_urls=[image_data_url],
            )
            descriptions.append(_description_record(asset, response, transmitted_image_sha256=image_hash))
        ledger.mark_complete()
        provider = ledger.snapshot()
    except BaseException:
        if ledger.snapshot().get("status") == "running":
            ledger.mark_invalid_execution()
        raise
    finally:
        ledger.close()
    result = {
        "schema_version": "1.0.0",
        "run_id": RUN_ID,
        "code_revision": revision,
        "instrument_sha256": canonical_sha256(instrument),
        "dataset_sha256": dataset["content_sha256"],
        "completed_at": datetime.now(UTC).isoformat(),
        "provider": provider,
        "private_data_used": False,
        "real_visual_capability_claim": False,
        **_quality(dataset, descriptions, instrument),
    }
    result["content_sha256"] = canonical_sha256(result)
    atomic_write_json(output_root / RESULT_NAME, result)
    return result


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true")
    action.add_argument("--simulate", action="store_true")
    action.add_argument("--preflight", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(RUN_ID, "external_model_evaluation")
        require_bounded_pilot_operation_allowed(RUN_ID, "method_evaluation_execution")
    if arguments.simulate:
        result = simulate()
    elif arguments.preflight:
        result = preflight(output_root=arguments.output_root)
    elif arguments.execute:
        result = asyncio.run(execute(output_root=arguments.output_root))
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
