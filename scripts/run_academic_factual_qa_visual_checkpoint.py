#!/usr/bin/env python3
"""Validate, simulate, or execute the two bounded visual checkpoints."""

from __future__ import annotations

import argparse
import asyncio
import base64
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Protocol, Sequence

from dotenv import load_dotenv
import httpx

from scripts.build_academic_factual_qa_confirmation_v2 import canonical_sha256
from scripts.build_academic_factual_qa_visual_supplement import (
    DATASET_PATH,
    validate_dataset,
)
from src.digital_twin.evaluation.visual_description import (
    VisualDescription,
    VisualDescriptionProvider,
    VisualRegionLineage,
)
from src.digital_twin.repository_freeze import (
    BOUNDED_PILOT_AUTHORIZATIONS,
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-professor-checkpoint-001"
INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/academic_factual_qa_professor_checkpoint_001.json"
)
BINDING_PATH = (
    ROOT / "research/05_evaluation/instruments/academic_factual_qa_visual_provider_binding_001.json"
)
SYNTHETIC_PATH = ROOT / "research/05_evaluation/multimodal_retrieval_v1_synthetic.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_ENDPOINTS_URL = "https://openrouter.ai/api/v1/models/google/gemini-3.7-flash/endpoints"
QUALIFICATION_STAGE = "gemini-visual-description-qualification-001"
PILOT_STAGE = "true-visual-30-cluster-pilot-001"
DEFAULT_QUALIFICATION_OUTPUT = ROOT / "reports/generated/gemini-visual-description-qualification-001.json"
DEFAULT_PILOT_OUTPUT = ROOT / "reports/generated/true-visual-30-cluster-pilot-001.json"

STOPWORDS = frozenset(
    "a an and are as at be by for from has have in is it of on or that the this to was which with".split()
)


class VisualCheckpointError(RuntimeError):
    """Raised when a visual checkpoint violates its frozen contract."""


@dataclass(frozen=True)
class VisualCallAccounting:
    provider_model: str
    provider_name: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float


class VisualTransport(VisualDescriptionProvider, Protocol):
    last_accounting: VisualCallAccounting | None


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return bool(result.stdout.strip())


def _repo_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _binding_age_hours(binding: dict[str, Any]) -> float:
    verified = datetime.fromisoformat(binding["verified_at"])
    if verified.tzinfo is None:
        raise VisualCheckpointError("visual binding timestamp lacks timezone")
    age = (datetime.now(timezone.utc) - verified.astimezone(timezone.utc)).total_seconds() / 3600
    if age < 0:
        raise VisualCheckpointError("visual binding is future dated")
    return age


def validate_checkpoint() -> dict[str, Any]:
    instrument = _load(INSTRUMENT_PATH)
    binding = _load(BINDING_PATH)
    dataset = _load(DATASET_PATH)
    synthetic = _load(SYNTHETIC_PATH)
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise VisualCheckpointError("checkpoint identity drifted")
    if instrument.get("status") != "frozen-build-only-five-authorizations-required":
        raise VisualCheckpointError("checkpoint status drifted")
    if [row["checkpoint_id"] for row in instrument["execution_checkpoints"]] != [
        "corrective-reviewer-calibration-002",
        "blinded-200-case-panel-001",
        QUALIFICATION_STAGE,
        PILOT_STAGE,
        "live-t0-product-confirmation-001",
    ]:
        raise VisualCheckpointError("checkpoint sequence drifted")
    if any(row["authorized"] for row in instrument["execution_checkpoints"]):
        raise VisualCheckpointError("a paid checkpoint is unexpectedly authorized")
    validate_dataset(dataset)
    if dataset["content_sha256"] != instrument["visual_supplement"]["content_sha256"]:
        raise VisualCheckpointError("visual supplement binding drifted")
    expected_binding_hash = canonical_sha256(
        {key: value for key, value in binding.items() if key != "content_sha256"}
    )
    if binding.get("content_sha256") != expected_binding_hash:
        raise VisualCheckpointError("visual provider binding hash drifted")
    if binding["content_sha256"] != instrument["visual_provider_binding"]["content_sha256"]:
        raise VisualCheckpointError("instrument visual binding drifted")
    if (
        binding["provider_model"] != "google/gemini-3.7-flash"
        or binding["documented_revision"] != "google/gemini-3.7-flash-20260813"
        or binding["endpoint_provider"] != "Google"
        or binding["endpoint_tag"] != "google-vertex/global"
        or binding["routing"]["allow_fallbacks"] is not False
        or binding["question_independent_description_required"] is not True
        or binding["description_is_authoritative_truth"] is not False
    ):
        raise VisualCheckpointError("Gemini visual contract drifted")
    if any(binding["authorization"].values()):
        raise VisualCheckpointError("visual execution authority must remain false")
    if instrument["visual_pilot_gates"].get("boundary_release_minimum_matching_terms") != 2:
        raise VisualCheckpointError("visual boundary release gate drifted")
    if len(synthetic.get("source_assets", [])) != 9 or len(synthetic.get("cases", [])) != 21:
        raise VisualCheckpointError("Gemini qualification fixture must contain 9 assets and 21 cases")
    for asset in synthetic["source_assets"]:
        path = ROOT / asset["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
            raise VisualCheckpointError(f"synthetic image hash drifted: {asset['asset_id']}")
    return {"instrument": instrument, "binding": binding, "dataset": dataset, "synthetic": synthetic}


def _live_metadata_failures(binding: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    with httpx.Client(timeout=20) as client:
        models = client.get(OPENROUTER_MODELS_URL).json()["data"]
        endpoints = client.get(OPENROUTER_ENDPOINTS_URL).json()["data"]["endpoints"]
    model = next((row for row in models if row.get("id") == binding["provider_model"]), None)
    if model is None:
        return ["gemini-model-missing"]
    if (
        model.get("context_length") != binding["context_window_tokens"]
        or model.get("architecture", {}).get("input_modalities") != binding["input_modalities"]
        or "structured_outputs" not in model.get("supported_parameters", [])
    ):
        failures.append("gemini-model-metadata-drift")
    endpoint = next(
        (
            row
            for row in endpoints
            if row.get("provider_name") == binding["endpoint_provider"]
            and row.get("tag") == binding["endpoint_tag"]
        ),
        None,
    )
    if endpoint is None or endpoint.get("name", "").split(" | ")[-1] != binding["documented_revision"]:
        failures.append("gemini-endpoint-identity-drift")
    if endpoint is not None and endpoint.get("status") != 0:
        failures.append("gemini-endpoint-unhealthy")
    return failures


def preflight(
    stage: str,
    *,
    live: bool,
    output: Path,
    resume: bool = False,
) -> dict[str, Any]:
    assets = validate_checkpoint()
    binding = assets["binding"]
    authorization_key = (
        "gemini_qualification_authorized" if stage == QUALIFICATION_STAGE else "visual_pilot_authorized"
    )
    blockers: list[str] = []
    if not binding["authorization"][authorization_key] or not binding["authorization"]["paid_execution_authorized"]:
        blockers.append("stage-not-authorized")
    if INSTRUMENT_ID not in BOUNDED_PILOT_AUTHORIZATIONS:
        blockers.append("bounded-freeze-authorization-missing")
    age = _binding_age_hours(binding)
    if age > binding["maximum_age_hours_for_execution"]:
        blockers.append("provider-binding-stale")
    live_failures = _live_metadata_failures(binding) if live else ["live-metadata-not-checked"]
    if live_failures:
        blockers.append("live-provider-metadata-not-current")
    if not os.getenv(binding["credential_environment_variable"], "").strip():
        blockers.append("provider-credential-missing")
    if _repo_dirty():
        blockers.append("working-tree-dirty")
    if output.exists() and not resume:
        blockers.append("output-path-already-exists")
    if resume:
        if not output.is_file():
            blockers.append("resume-ledger-missing")
        else:
            ledger = _load(output)
            if ledger.get("status") not in {"running", "interrupted"}:
                blockers.append("resume-ledger-terminal")
            if ledger.get("stage") != stage:
                blockers.append("resume-stage-drift")
    return {
        "instrument_id": INSTRUMENT_ID,
        "stage": stage,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "binding_age_hours": age,
        "live_metadata_checked": live,
        "live_metadata_failures": live_failures,
        "provider_calls": 0,
        "credential_values_emitted": False,
        "resume": resume,
    }


def _rasterize(path: Path, mime_type: str) -> tuple[bytes, str]:
    raw = path.read_bytes()
    if mime_type != "image/svg+xml":
        return raw, mime_type
    process = subprocess.run(
        ["rsvg-convert", "-f", "png", str(path)], check=True, capture_output=True
    )
    return process.stdout, "image/png"


def _response_schema() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "visual_description",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["transcription", "entities", "relationships", "uncertainty", "region_ids"],
                "properties": {
                    "transcription": {"type": "string"},
                    "entities": {"type": "array", "items": {"type": "string"}},
                    "relationships": {"type": "array", "items": {"type": "string"}},
                    "uncertainty": {"type": "array", "items": {"type": "string"}},
                    "region_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    }


class OpenRouterGeminiVisualProvider:
    implementation_id = "openrouter-google-gemini-3.7-flash-visual-description-v1"

    def __init__(self, binding: dict[str, Any]) -> None:
        self.binding = binding
        self.last_accounting: VisualCallAccounting | None = None

    async def describe(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        regions: Sequence[VisualRegionLineage],
    ) -> VisualDescription:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        region_ids = [row.region_id for row in regions]
        prompt = (
            "Describe this educational visual without answering any user question. "
            "Transcribe visible text, list visible entities, state only relationships directly visible, "
            "and list uncertainty. Do not infer facts outside the image. Use only these original region IDs: "
            + json.dumps(region_ids)
        )
        payload = {
            "model": self.binding["provider_model"],
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
            ]}],
            "temperature": 0,
            "max_tokens": 2048,
            "response_format": _response_schema(),
            "provider": self.binding["routing"],
        }
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json"},
                json=payload,
            )
        latency_ms = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        raw = response.json()
        model = str(raw.get("model", ""))
        if model not in {self.binding["provider_model"], self.binding["documented_revision"]}:
            raise VisualCheckpointError("Gemini runtime identity drifted")
        provider_name = str(raw.get("provider", ""))
        if provider_name != self.binding["endpoint_provider"]:
            raise VisualCheckpointError("Gemini runtime provider identity drifted")
        usage = raw.get("usage") or {}
        self.last_accounting = VisualCallAccounting(
            provider_model=model,
            provider_name=provider_name,
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            cost_usd=float(usage.get("cost", 0) or 0),
            latency_ms=latency_ms,
        )
        content = raw["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if set(parsed["region_ids"]) - set(region_ids):
            raise VisualCheckpointError("description invented a region identity")
        selected_regions = tuple(row for row in regions if row.region_id in parsed["region_ids"])
        if not selected_regions:
            selected_regions = tuple(regions)
        return VisualDescription(
            transcription=parsed["transcription"],
            entities=tuple(dict.fromkeys(parsed["entities"])),
            relationships=tuple(dict.fromkeys(parsed["relationships"])),
            uncertainty=tuple(parsed["uncertainty"]),
            provider_model=model,
            provider_revision=self.binding["documented_revision"],
            provider_name=provider_name,
            source_image_sha256=regions[0].image_sha256,
            region_lineage=selected_regions,
        )


class SimulatedVisualProvider:
    implementation_id = "simulated-visual-description-provider"

    def __init__(self, facts_by_asset: dict[str, list[str]]) -> None:
        self.facts_by_asset = facts_by_asset
        self.last_accounting: VisualCallAccounting | None = None

    async def describe(self, *, image_bytes: bytes, mime_type: str, regions: Sequence[VisualRegionLineage]) -> VisualDescription:
        del image_bytes, mime_type
        asset_id = regions[0].asset_id
        facts = list(dict.fromkeys(self.facts_by_asset.get(asset_id, [])))
        self.last_accounting = VisualCallAccounting(
            provider_model="google/gemini-3.7-flash",
            provider_name="Google",
            input_tokens=100,
            output_tokens=40,
            cost_usd=0.001,
            latency_ms=1.0,
        )
        return VisualDescription(
            transcription=" ".join(facts),
            entities=(),
            relationships=tuple(facts),
            uncertainty=(),
            provider_model="google/gemini-3.7-flash",
            provider_revision="google/gemini-3.7-flash-20260813",
            provider_name="Google",
            source_image_sha256=regions[0].image_sha256,
            region_lineage=tuple(regions),
        )


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 1 and token not in STOPWORDS
    }


def _claim_recalled(claim: str, description: str) -> bool:
    expected = _tokens(claim)
    return bool(expected) and len(expected & _tokens(description)) / len(expected) >= 0.6


def _fact_audit_candidates(
    descriptions: dict[str, dict[str, Any]],
    reference_by_asset: dict[str, str],
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for asset_id, description in descriptions.items():
        reference_tokens = _tokens(reference_by_asset.get(asset_id, ""))
        for field in ("entities", "relationships"):
            for fact in description.get(field, []):
                fact_tokens = _tokens(fact)
                if not fact_tokens:
                    continue
                overlap = len(fact_tokens & reference_tokens) / len(fact_tokens)
                if overlap < 0.6:
                    candidates.append(
                        {
                            "asset_id": asset_id,
                            "field": field,
                            "fact": fact,
                            "fact_sha256": hashlib.sha256(fact.encode("utf-8")).hexdigest(),
                            "reason": "not-deterministically-covered-by-frozen-reference",
                        }
                    )
    return candidates


def _audit_outcome(
    candidates: list[dict[str, str]],
    audit: dict[str, Any] | None,
    *,
    stage: str,
) -> dict[str, Any]:
    if not candidates:
        return {"complete": True, "unsupported_count": 0, "audited_count": 0}
    if audit is None:
        return {
            "complete": False,
            "unsupported_count": None,
            "audited_count": 0,
        }
    if audit.get("stage") != stage:
        raise VisualCheckpointError("visual fact audit stage drifted")
    decisions = {
        (row["asset_id"], row["fact_sha256"]): row["verdict"]
        for row in audit.get("decisions", [])
    }
    expected = {(row["asset_id"], row["fact_sha256"]) for row in candidates}
    if set(decisions) != expected or any(
        verdict not in {"supported", "unsupported"} for verdict in decisions.values()
    ):
        raise VisualCheckpointError("visual fact audit does not cover the exact candidate set")
    return {
        "complete": True,
        "unsupported_count": sum(value == "unsupported" for value in decisions.values()),
        "audited_count": len(decisions),
    }


def _lexical_score(query: str, text: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    return len(query_tokens & _tokens(text)) / len(query_tokens)


def _lineage(asset: dict[str, Any], image_sha256: str) -> tuple[VisualRegionLineage, ...]:
    source_id = asset.get("source_id", asset["asset_id"])
    return tuple(
        VisualRegionLineage(
            source_id=source_id,
            asset_id=asset["asset_id"],
            region_id=row["region_id"],
            image_sha256=image_sha256,
            bbox=tuple(row["bbox"]),
        )
        for row in asset.get("region_lineage", asset.get("regions", []))
    )


def _asset_path(asset: dict[str, Any]) -> Path:
    return ROOT / (asset.get("render_path") or asset["path"])


def _atomic_write(path: Path, payload: dict[str, Any], *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive and path.exists():
        raise VisualCheckpointError(f"output already exists: {path}")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


async def _describe_all(
    *,
    stage: str,
    assets: list[dict[str, Any]],
    provider: VisualTransport,
    output: Path,
    maximum_calls: int,
    hard_stop: float,
    binding_sha256: str,
    source_sha256: str,
    resume: bool = False,
) -> dict[str, Any]:
    expected = {
        "instrument_id": INSTRUMENT_ID,
        "stage": stage,
        "code_revision": _repo_revision(),
        "binding_sha256": binding_sha256,
        "source_sha256": source_sha256,
        "maximum_calls": maximum_calls,
        "hard_stop_usd": hard_stop,
    }
    if resume:
        ledger = _load(output)
        if any(ledger.get(key) != value for key, value in expected.items()):
            raise VisualCheckpointError("visual resume binding drifted")
        if ledger.get("status") not in {"running", "interrupted"}:
            raise VisualCheckpointError("visual resume ledger is terminal")
        ledger["resume_count"] = int(ledger.get("resume_count", 0)) + 1
        ledger["status"] = "running"
        _atomic_write(output, ledger)
    else:
        ledger = {
            "schema_version": 1,
            **expected,
            "status": "running",
            "resume_count": 0,
            "provider_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "reported_cost_usd": 0.0,
            "descriptions": [],
            "failures": [],
        }
        _atomic_write(output, ledger, exclusive=True)
    completed_assets = {row["asset_id"] for row in ledger["descriptions"]}
    expected_prefix = [row["asset_id"] for row in assets[: len(completed_assets)]]
    actual_prefix = [row["asset_id"] for row in ledger["descriptions"]]
    if actual_prefix != expected_prefix:
        raise VisualCheckpointError("visual resume asset order drifted")
    for asset in assets:
        if asset["asset_id"] in completed_assets:
            continue
        if ledger["provider_calls"] >= maximum_calls:
            ledger["status"] = "invalid-execution"
            ledger["failures"].append("provider-call-limit")
            break
        if ledger["reported_cost_usd"] >= hard_stop:
            ledger["status"] = "invalid-execution"
            ledger["failures"].append("pre-call-budget-stop")
            break
        path = _asset_path(asset)
        raw, mime_type = _rasterize(path, asset["mime_type"])
        image_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            description = await provider.describe(
                image_bytes=raw,
                mime_type=mime_type,
                regions=_lineage(asset, image_sha256),
            )
        except Exception as error:
            ledger["provider_calls"] += 1
            ledger["status"] = "invalid-execution"
            ledger["failures"].append({"asset_id": asset["asset_id"], "error": type(error).__name__, "detail": str(error)[:300]})
            _atomic_write(output, ledger)
            return ledger
        accounting = provider.last_accounting
        if accounting is None:
            raise VisualCheckpointError("provider accounting is missing")
        ledger["provider_calls"] += 1
        ledger["input_tokens"] += accounting.input_tokens
        ledger["output_tokens"] += accounting.output_tokens
        ledger["reported_cost_usd"] = round(ledger["reported_cost_usd"] + accounting.cost_usd, 9)
        ledger["descriptions"].append({"asset_id": asset["asset_id"], "description": description.to_record(), "accounting": accounting.__dict__})
        if ledger["reported_cost_usd"] > hard_stop:
            ledger["status"] = "invalid-execution"
            ledger["failures"].append("post-call-budget-stop")
            _atomic_write(output, ledger)
            return ledger
        _atomic_write(output, ledger)
    return ledger


def _qualification_summary(
    ledger: dict[str, Any],
    synthetic: dict[str, Any],
    audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    descriptions = {
        row["asset_id"]: VisualDescription(**{
            **row["description"],
            "entities": tuple(row["description"]["entities"]),
            "relationships": tuple(row["description"]["relationships"]),
            "uncertainty": tuple(row["description"]["uncertainty"]),
            "region_lineage": tuple(VisualRegionLineage(**{**region, "bbox": tuple(region["bbox"])}) for region in row["description"]["region_lineage"]),
        })
        for row in ledger["descriptions"]
    }
    answerable = [row for row in synthetic["cases"] if row["expected_action"] == "retrieve" and row["slice"] != "text_control"]
    recalled = 0
    total = 0
    lineage_valid = 0
    for case in answerable:
        description = descriptions[case["asset_id"]]
        text = description.retrieval_text()
        for claim in case["required_claims"]:
            total += 1
            recalled += int(_claim_recalled(claim, text))
        lineage_valid += int(set(case["gold_region_ids"]) <= {row.region_id for row in description.region_lineage})
    recall = recalled / total if total else 0.0
    records = {row["asset_id"]: row["description"] for row in ledger["descriptions"]}
    references = {
        asset["asset_id"]: " ".join(
            [
                asset.get("surrounding_text", ""),
                *(
                    claim
                    for case in synthetic["cases"]
                    if case["asset_id"] == asset["asset_id"] and case["expected_action"] == "retrieve"
                    for claim in case["required_claims"]
                ),
            ]
        )
        for asset in synthetic["source_assets"]
    }
    audit_candidates = _fact_audit_candidates(records, references)
    audit_outcome = _audit_outcome(audit_candidates, audit, stage=QUALIFICATION_STAGE)
    text_controls = [row for row in synthetic["cases"] if row["slice"] == "text_control"]
    text_control_passes = sum(
        all(
            _claim_recalled(claim, descriptions[row["asset_id"]].retrieval_text())
            for claim in row["required_claims"]
        )
        for row in text_controls
    )
    exact_identity = all(
        row["description"]["provider_model"]
        in {"google/gemini-3.7-flash", "google/gemini-3.7-flash-20260813"}
        and row["description"]["provider_name"] == "Google"
        for row in ledger["descriptions"]
    )
    gates = {
        "complete_structured_responses": len(descriptions) == 9,
        "exact_model_provider_identity": exact_identity,
        "visual_fact_recall": recall >= 0.9,
        "unsupported_visual_facts": audit_outcome["complete"] and audit_outcome["unsupported_count"] == 0,
        "modality_coverage": {row["modality"] for row in synthetic["cases"] if row["expected_action"] == "retrieve"} >= {"table", "diagram", "equation"},
        "original_region_lineage": lineage_valid == len(answerable),
        "text_controls_retained": text_control_passes == len(text_controls),
        "complete_accounting": ledger["provider_calls"] == 9,
    }
    decision = None if not audit_outcome["complete"] else ("Keep" if all(gates.values()) else "Refine")
    return {
        "visual_fact_recall": recall,
        "unsupported_visual_fact_count": audit_outcome["unsupported_count"],
        "unsupported_fact_audit_candidates": audit_candidates,
        "fact_audit_complete": audit_outcome["complete"],
        "lineage_valid_case_count": lineage_valid,
        "text_control_pass_count": text_control_passes,
        "gate_results": gates,
        "decision": decision,
    }


def _visual_pilot_summary(
    ledger: dict[str, Any],
    dataset: dict[str, Any],
    audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    descriptions = {row["asset_id"]: row["description"] for row in ledger["descriptions"]}
    assets = {row["asset_id"]: row for row in dataset["assets"]}
    answerable = [row for row in dataset["cases"] if row["expected_action"] == "answer"]
    complete_at_3 = 0
    recall_at_5 = 0
    fallback_complete_at_3 = 0
    fallback_recall_at_5 = 0
    region_citations = 0
    for case in answerable:
        ranked = sorted(
            descriptions,
            key=lambda asset_id: _lexical_score(
                case["question"],
                "\n".join([
                    descriptions[asset_id]["transcription"],
                    *descriptions[asset_id]["entities"],
                    *descriptions[asset_id]["relationships"],
                ]),
            ),
            reverse=True,
        )
        fallback_ranked = sorted(
            descriptions,
            key=lambda asset_id: _lexical_score(
                case["question"], descriptions[asset_id]["transcription"]
            ),
            reverse=True,
        )
        required = case["required_asset_ids"][0]
        complete_at_3 += int(required in ranked[:3])
        recall_at_5 += int(required in ranked[:5])
        fallback_complete_at_3 += int(required in fallback_ranked[:3])
        fallback_recall_at_5 += int(required in fallback_ranked[:5])
        cited_regions = {row["region_id"] for row in descriptions[required]["region_lineage"]}
        region_citations += int(set(case["required_region_ids"]) <= cited_regions)
    boundary_rows = [row for row in dataset["cases"] if row["expected_action"] != "answer"]
    boundary_releases = sum(
        any(
            len(_tokens(case["question"]) & _tokens("\n".join([
                description["transcription"],
                *description["entities"],
                *description["relationships"],
            ]))) >= 2
            for description in descriptions.values()
        )
        for case in boundary_rows
    )
    references = {
        row["required_asset_ids"][0]: " ".join(claim["text"] for claim in row["atomic_claims"])
        for row in answerable
    }
    audit_candidates = _fact_audit_candidates(descriptions, references)
    audit_outcome = _audit_outcome(audit_candidates, audit, stage=PILOT_STAGE)
    exact_identity = all(
        row["provider_model"] in {"google/gemini-3.7-flash", "google/gemini-3.7-flash-20260813"}
        and row["provider_name"] == "Google"
        for row in descriptions.values()
    )
    gates = {
        "complete_visual_evidence_at_3": complete_at_3 >= 27,
        "atomic_evidence_recall_at_5": recall_at_5 >= 29,
        "zero_boundary_releases": boundary_releases == 0,
        "original_region_citations": region_citations == 30,
        "unsupported_accepted_descriptions": audit_outcome["complete"] and audit_outcome["unsupported_count"] == 0,
        "text_control_no_regression": complete_at_3 >= fallback_complete_at_3 and recall_at_5 >= fallback_recall_at_5,
        "complete_accounting": ledger["provider_calls"] == 30,
        "exact_model_provider_identity": exact_identity,
    }
    decision = None if not audit_outcome["complete"] else ("Go Deeper" if all(gates.values()) else "Refine")
    return {
        "complete_visual_evidence_at_3_count": complete_at_3,
        "atomic_evidence_recall_at_5_count": recall_at_5,
        "fallback_complete_visual_evidence_at_3_count": fallback_complete_at_3,
        "fallback_atomic_evidence_recall_at_5_count": fallback_recall_at_5,
        "boundary_release_count": boundary_releases,
        "original_region_citation_count": region_citations,
        "unsupported_accepted_description_count": audit_outcome["unsupported_count"],
        "unsupported_fact_audit_candidates": audit_candidates,
        "fact_audit_complete": audit_outcome["complete"],
        "gate_results": gates,
        "decision": decision,
        "profile_selected": False,
    }


def _simulated_facts_for_synthetic(synthetic: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {row["asset_id"]: [] for row in synthetic["source_assets"]}
    for case in synthetic["cases"]:
        if case["expected_action"] == "retrieve":
            result[case["asset_id"]].extend(case["required_claims"])
    return result


def _simulated_facts_for_visual(dataset: dict[str, Any]) -> dict[str, list[str]]:
    result = {row["asset_id"]: [] for row in dataset["assets"]}
    for case in dataset["cases"]:
        if case["expected_action"] == "answer":
            result[case["required_asset_ids"][0]].extend(
                [case["canonical_answer"], *(row["text"] for row in case["atomic_claims"])]
            )
    return result


async def run_stage(
    stage: str,
    *,
    provider: VisualTransport,
    output: Path,
    audit: dict[str, Any] | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    checkpoint = validate_checkpoint()
    if stage == QUALIFICATION_STAGE:
        source = checkpoint["synthetic"]
        assets = source["source_assets"]
        contract = checkpoint["binding"]["qualification_contract"]
    else:
        source = checkpoint["dataset"]
        assets = source["assets"]
        contract = checkpoint["binding"]["visual_pilot_contract"]
    ledger = await _describe_all(
        stage=stage,
        assets=assets,
        provider=provider,
        output=output,
        maximum_calls=contract["maximum_provider_calls"],
        hard_stop=contract["emergency_hard_stop_usd"],
        binding_sha256=checkpoint["binding"]["content_sha256"],
        source_sha256=(
            checkpoint["dataset"]["content_sha256"]
            if stage == PILOT_STAGE
            else canonical_sha256(checkpoint["synthetic"])
        ),
        resume=resume,
    )
    if ledger["status"] == "invalid-execution":
        return ledger
    summary = (
        _qualification_summary(ledger, source, audit)
        if stage == QUALIFICATION_STAGE
        else _visual_pilot_summary(ledger, source, audit)
    )
    ledger["summary"] = summary
    ledger["status"] = (
        "ready-codex-audit"
        if summary["decision"] is None
        else "completed-keep"
        if summary["decision"] == "Keep"
        else "completed-go-deeper"
        if summary["decision"] == "Go Deeper"
        else "completed-refine"
    )
    _atomic_write(output, ledger)
    return ledger


def finalize_stage(
    stage: str,
    *,
    output: Path,
    audit_path: Path,
) -> dict[str, Any]:
    checkpoint = validate_checkpoint()
    if not output.is_file() or not audit_path.is_file():
        raise VisualCheckpointError("visual result and audit decisions must both exist")
    ledger = _load(output)
    if ledger.get("stage") != stage or ledger.get("status") != "ready-codex-audit":
        raise VisualCheckpointError("visual result is not awaiting the requested audit")
    audit = _load(audit_path)
    summary = (
        _qualification_summary(ledger, checkpoint["synthetic"], audit)
        if stage == QUALIFICATION_STAGE
        else _visual_pilot_summary(ledger, checkpoint["dataset"], audit)
    )
    ledger["summary"] = summary
    ledger["fact_audit"] = {
        "path": str(audit_path),
        "content_sha256": hashlib.sha256(audit_path.read_bytes()).hexdigest(),
        "reviewer_role": audit.get("reviewer_role"),
    }
    ledger["status"] = (
        "completed-keep"
        if summary["decision"] == "Keep"
        else "completed-go-deeper"
        if summary["decision"] == "Go Deeper"
        else "completed-refine"
    )
    _atomic_write(output, ledger)
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--preflight-qualification", action="store_true")
    mode.add_argument("--preflight-visual-pilot", action="store_true")
    mode.add_argument("--preflight-live-qualification", action="store_true")
    mode.add_argument("--preflight-live-visual-pilot", action="store_true")
    mode.add_argument("--simulate-qualification", action="store_true")
    mode.add_argument("--simulate-visual-pilot", action="store_true")
    mode.add_argument("--execute-qualification", action="store_true")
    mode.add_argument("--execute-visual-pilot", action="store_true")
    mode.add_argument("--finalize-qualification", action="store_true")
    mode.add_argument("--finalize-visual-pilot", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--audit-decisions", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.resume and not (args.execute_qualification or args.execute_visual_pilot):
        raise VisualCheckpointError("--resume is valid only with a live execute mode")
    load_dotenv(ROOT / ".env")
    if args.execute_qualification or args.execute_visual_pilot:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
    checkpoint = validate_checkpoint()
    if args.validate:
        result = {"instrument_id": INSTRUMENT_ID, "status": "validated-build-only", "visual_assets": 30, "visual_cases": 60, "qualification_assets": 9, "qualification_cases": 21, "provider_calls": 0}
    elif args.preflight_qualification or args.preflight_live_qualification:
        result = preflight(QUALIFICATION_STAGE, live=args.preflight_live_qualification, output=args.output or DEFAULT_QUALIFICATION_OUTPUT)
    elif args.preflight_visual_pilot or args.preflight_live_visual_pilot:
        result = preflight(PILOT_STAGE, live=args.preflight_live_visual_pilot, output=args.output or DEFAULT_PILOT_OUTPUT)
    elif args.simulate_qualification:
        provider = SimulatedVisualProvider(_simulated_facts_for_synthetic(checkpoint["synthetic"]))
        result = asyncio.run(run_stage(QUALIFICATION_STAGE, provider=provider, output=args.output or DEFAULT_QUALIFICATION_OUTPUT.with_name("gemini-visual-description-qualification-001-simulation.json")))
    elif args.simulate_visual_pilot:
        provider = SimulatedVisualProvider(_simulated_facts_for_visual(checkpoint["dataset"]))
        result = asyncio.run(run_stage(PILOT_STAGE, provider=provider, output=args.output or DEFAULT_PILOT_OUTPUT.with_name("true-visual-30-cluster-pilot-001-simulation.json")))
    elif args.finalize_qualification or args.finalize_visual_pilot:
        if args.audit_decisions is None:
            raise VisualCheckpointError("--audit-decisions is required when finalizing")
        stage = QUALIFICATION_STAGE if args.finalize_qualification else PILOT_STAGE
        result = finalize_stage(
            stage,
            output=args.output or (
                DEFAULT_QUALIFICATION_OUTPUT
                if stage == QUALIFICATION_STAGE
                else DEFAULT_PILOT_OUTPUT
            ),
            audit_path=args.audit_decisions,
        )
    else:
        stage = QUALIFICATION_STAGE if args.execute_qualification else PILOT_STAGE
        live = preflight(
            stage,
            live=True,
            output=args.output or (
                DEFAULT_QUALIFICATION_OUTPUT
                if stage == QUALIFICATION_STAGE
                else DEFAULT_PILOT_OUTPUT
            ),
            resume=args.resume,
        )
        if live["status"] != "ready":
            raise VisualCheckpointError(f"execution preflight blocked: {live['blockers']}")
        result = asyncio.run(
            run_stage(
                stage,
                provider=OpenRouterGeminiVisualProvider(checkpoint["binding"]),
                output=args.output or (
                    DEFAULT_QUALIFICATION_OUTPUT
                    if stage == QUALIFICATION_STAGE
                    else DEFAULT_PILOT_OUTPUT
                ),
                resume=args.resume,
            )
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
