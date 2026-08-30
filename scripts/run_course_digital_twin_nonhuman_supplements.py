#!/usr/bin/env python3
"""Run the AFQC-101 visual and synthetic-profile supplementary stages.

This capsule is deliberately independent from the terminated program-001
dispatcher.  It reads only the frozen program-002 manifest, the public visual
supplement, and the draft synthetic profile.  Provider responses remain in
exclusive SQLite ledgers under ``reports/generated``; returned JSON contains
only deterministic scores, lineage, accounting, and claim limitations.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
from typing import Any, Callable

from dotenv import load_dotenv

from scripts import build_academic_factual_qa_visual_supplement as visual_builder
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
PROGRAM_ID = "course-digital-twin-nonhuman-evaluation-program-002"
EXPECTED_PROGRAM_SHA256 = (
    "7ff5927caa72c313b73157e3951e2681d503e1288b57abf84d458155214d8d3f"
)
PROGRAM_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "course_digital_twin_nonhuman_evaluation_program_002.json"
)
VISUAL_DATASET_PATH = ROOT / (
    "research/05_evaluation/datasets/academic_factual_qa_visual_supplement_001.json"
)
SYNTHETIC_PROFILE_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "professor_digital_twin_profile_v1_synthetic.json"
)
DEFAULT_OUTPUT_ROOT = ROOT / (
    "reports/generated/course-digital-twin-nonhuman-supplements-001"
)
GENERATED_ROOT = (ROOT / "reports/generated").resolve()

VISUAL_STAGE = "true-visual-30-plus-60"
PROFILE_STAGE = "synthetic-profile-c0-c2"
VISUAL_RUN_ID = "course-digital-twin-nonhuman-visual-001"
PROFILE_RUN_ID = "course-digital-twin-synthetic-profile-c0-c2-001"
COMBINED_RUN_ID = "course-digital-twin-nonhuman-supplements-001"
VISUAL_LEDGER_NAME = "stage-a-visual-provider.sqlite3"
PROFILE_LEDGER_NAME = "stage-b-profile-provider.sqlite3"
VISUAL_EVIDENCE_NAME = "stage-a-visual-evidence.json"
PROFILE_EVIDENCE_NAME = "stage-b-profile-evidence.json"
COMBINED_EVIDENCE_NAME = "supplementary-result.json"
VISUAL_RASTER_MAX_WIDTH = 1600
VISUAL_RASTER_MAX_HEIGHT = 1600

VISUAL_MODEL = "gpt-5.4-nano-2026-03-17"
PROFILE_MODEL = "gpt-5.4-mini-2026-03-17"
VISUAL_MAXIMUM_CALLS = 30
PROFILE_MAXIMUM_CALLS = 36
VISUAL_MAXIMUM_COST_USD = 2.0
PROFILE_MAXIMUM_COST_USD = 1.5
SUPPLEMENT_MAXIMUM_COST_USD = 3.5
CONDITIONS = ("C0", "C1", "C2")
SKIPPED_CONDITION = "C3"

_TOKEN_PATTERN = re.compile(r"[a-z0-9_+.-]+")
_SUPPORT_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}
_ALLOWED_ASSET_ROOTS = (
    (ROOT / "data/external/academic_factual_qa_confirmation_002").resolve(),
    (ROOT / "reports/generated/academic-factual-qa-visual-supplement-001").resolve(),
)
_BOUNDARY_ACTIONS = {
    "no-evidence": "abstain",
    "cross-course": "abstain",
    "stale-version": "clarify",
    "permission": "refuse",
    "unsupported-premise": "abstain",
}


class SupplementaryEvaluationError(RuntimeError):
    """Raised when the program-002 supplementary capsule must fail closed."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SupplementaryEvaluationError(
            f"required JSON is unavailable: {path.name}"
        ) from error
    if not isinstance(value, dict):
        raise SupplementaryEvaluationError(f"JSON root is not an object: {path.name}")
    return value


def _load_program() -> dict[str, Any]:
    program = _load_json(PROGRAM_PATH)
    observed_hash = canonical_sha256(
        {key: value for key, value in program.items() if key != "content_sha256"}
    )
    if (
        program.get("content_sha256") != observed_hash
        or observed_hash != EXPECTED_PROGRAM_SHA256
    ):
        raise SupplementaryEvaluationError("program-002 manifest hash drifted")
    if (
        program.get("program_id") != PROGRAM_ID
        or program.get("decision_id") != "AFQC-101"
        or program.get("status") != "frozen-authorized"
        or program.get("provider_execution_authorized") is not True
        or program.get("paid_execution_authorized") is not True
        or program.get("automatic_stage_progression") is not True
        or program.get("stage_by_stage_user_approval_required") is not False
        or program.get("private_data_authorized") is not False
        or program.get("human_participant_execution_authorized") is not False
        or program.get("deterministic_truth_authoritative") is not True
        or program.get("llm_or_agent_reviews_authoritative") is not False
    ):
        raise SupplementaryEvaluationError("program-002 authority boundary drifted")

    stages = {row.get("stage"): row for row in program.get("stages", [])}
    visual = stages.get(VISUAL_STAGE)
    profile = stages.get("synthetic-profile-c0-c3")
    if (
        not isinstance(visual, dict)
        or visual.get("budget_usd") != VISUAL_MAXIMUM_COST_USD
        or visual.get("independent_after_factual_failure") is not True
        or not isinstance(profile, dict)
        or profile.get("budget_usd") != PROFILE_MAXIMUM_COST_USD
        or profile.get("independent_after_factual_failure") is not True
    ):
        raise SupplementaryEvaluationError("supplementary stage binding drifted")
    if sum(float(row["budget_usd"]) for row in stages.values()) != float(
        program["global_budget_usd"]
    ):
        raise SupplementaryEvaluationError("program-002 budget accounting drifted")
    if SUPPLEMENT_MAXIMUM_COST_USD > float(program["global_budget_usd"]):
        raise SupplementaryEvaluationError("supplement budget exceeds program ceiling")
    return program


def _model(program: dict[str, Any], *, role: str, expected: str) -> dict[str, Any]:
    model = next(
        (row for row in program.get("models", []) if row.get("role") == role), None
    )
    if not isinstance(model, dict) or model.get("model") != expected:
        raise SupplementaryEvaluationError(f"program model binding drifted: {role}")
    for price in (
        model.get("input_price_usd_per_million"),
        model.get("output_price_usd_per_million"),
    ):
        if isinstance(price, bool) or not isinstance(price, (int, float)) or price < 0:
            raise SupplementaryEvaluationError(f"program model pricing drifted: {role}")
    return model


def _provider_binding(
    program: dict[str, Any],
    *,
    role: str,
    expected_model: str,
    binding_suffix: str,
    maximum_output_tokens: int,
) -> dict[str, Any]:
    model = _model(program, role=role, expected=expected_model)
    return {
        "binding_id": f"{PROGRAM_ID}-{binding_suffix}-v1",
        "program_id": PROGRAM_ID,
        "provider": "openai",
        "provider_display_name": "OpenAI",
        "first_party_endpoint": True,
        "api_url": "https://api.openai.com/v1/responses",
        "credential_environment_variable": "OPENAI_API_KEY",
        "provider_model": expected_model,
        "documented_revision": expected_model,
        "reasoning_effort": "low",
        "max_output_tokens": maximum_output_tokens,
        "timeout_seconds": 120,
        "maximum_transport_retries": 0,
        "pricing_usd_per_million_input_tokens": float(
            model["input_price_usd_per_million"]
        ),
        "pricing_usd_per_million_output_tokens": float(
            model["output_price_usd_per_million"]
        ),
        "request_store": False,
    }


def _bindings(program: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "visual": _provider_binding(
            program,
            role="routine-semantic-screen-and-question-authoring",
            expected_model=VISUAL_MODEL,
            binding_suffix="visual-description-openai-nano",
            maximum_output_tokens=1_500,
        ),
        "profile": _provider_binding(
            program,
            role="product-answer-generator",
            expected_model=PROFILE_MODEL,
            binding_suffix="synthetic-profile-openai-mini",
            maximum_output_tokens=700,
        ),
    }


def _visual_dataset() -> dict[str, Any]:
    dataset = _load_json(VISUAL_DATASET_PATH)
    visual_builder.validate_dataset(dataset)
    rebuilt = visual_builder.build_dataset(write_assets=False)
    if rebuilt != dataset:
        raise SupplementaryEvaluationError(
            "public visual supplement reconstruction drifted"
        )
    if (
        dataset.get("private_data_used") is not False
        or dataset.get("raw_assets_committed") is not False
        or dataset.get("description_provider_output_authoritative") is not False
        or dataset.get("truth_method") != "deterministic-source-linked"
    ):
        raise SupplementaryEvaluationError("visual public/truth boundary drifted")
    if any(
        not str(asset.get("license_spdx", "")).strip()
        or Path(str(asset.get("render_path", ""))).is_absolute()
        or ".." in Path(str(asset.get("render_path", ""))).parts
        for asset in dataset["assets"]
    ):
        raise SupplementaryEvaluationError("visual asset provenance is unsafe")
    return dataset


def _synthetic_profile() -> dict[str, Any]:
    profile = _load_json(SYNTHETIC_PROFILE_PATH)
    if (
        profile.get("profile_id") != "professor-digital-twin-profile-v1-synthetic"
        or profile.get("course_id") != "synthetic-course-001"
        or profile.get("status") != "draft-unapproved"
        or profile.get("approval", {}).get("status") != "pending"
        or profile.get("approval", {}).get("approved_profile_sha256") is not None
    ):
        raise SupplementaryEvaluationError("synthetic profile boundary drifted")
    dimensions = profile.get("dimensions")
    if not isinstance(dimensions, dict) or not dimensions:
        raise SupplementaryEvaluationError("synthetic profile has no dimensions")
    for name, dimension in dimensions.items():
        if (
            not isinstance(dimension, dict)
            or dimension.get("professor_approved") is not False
            or not str(dimension.get("value", "")).strip()
            or not all(
                str(reference).startswith("synthetic-")
                for reference in dimension.get("evidence_refs", [])
            )
        ):
            raise SupplementaryEvaluationError(
                f"synthetic profile dimension is ineligible: {name}"
            )
    return profile


def _stratified_profile_cases(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for modality in ("table", "equation", "diagram"):
        for answerable in (True, False):
            candidates = [
                row
                for row in dataset["cases"]
                if row["modality"] == modality
                and (row["expected_action"] == "answer") is answerable
            ]
            candidates.sort(
                key=lambda row: hashlib.sha256(
                    f"afqc-101-profile-c0-c2:{row['case_id']}".encode("utf-8")
                ).hexdigest()
            )
            selected.extend(candidates[:2])
    if (
        len(selected) != 12
        or len({row["case_id"] for row in selected}) != 12
        or Counter(row["modality"] for row in selected)
        != {"table": 4, "equation": 4, "diagram": 4}
        or sum(row["expected_action"] == "answer" for row in selected) != 6
    ):
        raise SupplementaryEvaluationError("synthetic-profile stratification drifted")
    return selected


def _visual_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["transcription", "entities", "relationships", "uncertainty"],
        "properties": {
            "transcription": {"type": "string", "minLength": 1, "maxLength": 8_000},
            "entities": {
                "type": "array",
                "maxItems": 40,
                "uniqueItems": True,
                "items": {"type": "string", "minLength": 1, "maxLength": 200},
            },
            "relationships": {
                "type": "array",
                "maxItems": 40,
                "uniqueItems": True,
                "items": {"type": "string", "minLength": 1, "maxLength": 300},
            },
            "uncertainty": {
                "type": "array",
                "maxItems": 20,
                "uniqueItems": True,
                "items": {"type": "string", "minLength": 1, "maxLength": 300},
            },
        },
    }


def _profile_schema(case_id: str, condition: str) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "case_id",
            "condition",
            "action",
            "response",
            "evidence_region_ids",
            "applied_profile_features",
        ],
        "properties": {
            "case_id": {"type": "string", "const": case_id},
            "condition": {"type": "string", "const": condition},
            "action": {
                "type": "string",
                "enum": ["answer", "abstain", "clarify", "refuse"],
            },
            "response": {"type": "string", "minLength": 1, "maxLength": 2_000},
            "evidence_region_ids": {
                "type": "array",
                "maxItems": 4,
                "uniqueItems": True,
                "items": {"type": "string", "minLength": 1, "maxLength": 200},
            },
            "applied_profile_features": {
                "type": "array",
                "maxItems": 8,
                "uniqueItems": True,
                "items": {"type": "string", "minLength": 1, "maxLength": 200},
            },
        },
    }


def _tokens(value: str) -> set[str]:
    return {
        token for token in _TOKEN_PATTERN.findall(value.casefold()) if len(token) > 1
    }


def _recall(required: str, observed: str) -> float:
    required_tokens = _tokens(required)
    if not required_tokens:
        return 1.0
    return len(required_tokens & _tokens(observed)) / len(required_tokens)


def _supported_precision(required: str, observed: str) -> float:
    required_tokens = _tokens(required) - _SUPPORT_STOPWORDS
    observed_tokens = _tokens(observed) - _SUPPORT_STOPWORDS
    if not observed_tokens:
        return 0.0
    return len(required_tokens & observed_tokens) / len(observed_tokens)


def _repo_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _output_root_is_safe(output_root: Path) -> bool:
    resolved = output_root.resolve()
    return resolved != GENERATED_ROOT and resolved.is_relative_to(GENERATED_ROOT)


def _hashed_payload(payload: dict[str, Any]) -> dict[str, Any]:
    value = dict(payload)
    value["content_sha256"] = canonical_sha256(value)
    return value


def _load_sanitized(path: Path, *, run_id: str, program_sha256: str) -> dict[str, Any]:
    payload = _load_json(path)
    observed = canonical_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if (
        payload.get("content_sha256") != observed
        or payload.get("run_id") != run_id
        or payload.get("program_id") != PROGRAM_ID
        or payload.get("program_sha256") != program_sha256
    ):
        raise SupplementaryEvaluationError(f"sanitized evidence drifted: {path.name}")
    return payload


def _write_exclusive_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise SupplementaryEvaluationError(
            f"exclusive output already exists: {path.name}"
        )
    atomic_write_json(path, _hashed_payload(payload))


def _validate_provider_contracts(bindings: dict[str, dict[str, Any]]) -> None:
    samples = {
        "visual": (_visual_schema(), ["data:image/png;base64,AA=="]),
        "profile": (_profile_schema("case", "C0"), None),
    }
    expected = {"visual": VISUAL_MODEL, "profile": PROFILE_MODEL}
    for name, binding in bindings.items():
        if (
            binding.get("program_id") != PROGRAM_ID
            or binding.get("provider") != "openai"
            or binding.get("first_party_endpoint") is not True
            or binding.get("api_url") != "https://api.openai.com/v1/responses"
            or binding.get("provider_model") != expected[name]
            or binding.get("documented_revision") != expected[name]
            or binding.get("maximum_transport_retries") != 0
            or binding.get("request_store") is not False
        ):
            raise SupplementaryEvaluationError(f"direct OpenAI binding drifted: {name}")
        schema, images = samples[name]
        payload = DirectProviderJsonTransport(binding)._payload(  # noqa: SLF001
            system="validation",
            prompt="validation",
            task="program-002-supplement-validation",
            schema=schema,
            image_data_urls=images,
        )
        if payload.get("model") != expected[name] or payload.get("store") is not False:
            raise SupplementaryEvaluationError(f"OpenAI payload drifted: {name}")


def validate() -> dict[str, Any]:
    program = _load_program()
    bindings = _bindings(program)
    _validate_provider_contracts(bindings)
    dataset = _visual_dataset()
    profile = _synthetic_profile()
    selected = _stratified_profile_cases(dataset)
    return {
        "schema_version": 1,
        "run_id": COMBINED_RUN_ID,
        "program_id": PROGRAM_ID,
        "program_sha256": program["content_sha256"],
        "status": "passed-build-only",
        "stages": [VISUAL_STAGE, PROFILE_STAGE],
        "visual_asset_count": len(dataset["assets"]),
        "visual_case_count": len(dataset["cases"]),
        "profile_case_count": len(selected),
        "profile_conditions": list(CONDITIONS),
        "skipped_condition": SKIPPED_CONDITION,
        "visual_maximum_calls": VISUAL_MAXIMUM_CALLS,
        "profile_maximum_calls": PROFILE_MAXIMUM_CALLS,
        "visual_maximum_cost_usd": VISUAL_MAXIMUM_COST_USD,
        "profile_maximum_cost_usd": PROFILE_MAXIMUM_COST_USD,
        "supplement_maximum_cost_usd": SUPPLEMENT_MAXIMUM_COST_USD,
        "synthetic_profile_sha256": hashlib.sha256(
            SYNTHETIC_PROFILE_PATH.read_bytes()
        ).hexdigest(),
        "synthetic_profile_status": profile["status"],
        "provider_calls": 0,
        "private_data_used": False,
        "hidden_data_opened": False,
        "human_participants": 0,
        "professor_fidelity_claim": False,
    }


def preflight(
    *, output_root: Path = DEFAULT_OUTPUT_ROOT, resume: bool = False
) -> dict[str, Any]:
    summary = validate()
    blockers: list[str] = []
    try:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
        require_bounded_pilot_operation_allowed(
            PROGRAM_ID, "method_evaluation_execution"
        )
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "dataset_generation")
    except RepositoryFreezeError:
        blockers.append("program-002-freeze-authorization-missing")
    if _repo_dirty():
        blockers.append("repository-dirty")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-api-key-missing")
    if shutil.which("rsvg-convert") is None:
        blockers.append("verified-svg-renderer-missing")
    if not _output_root_is_safe(output_root):
        blockers.append("raw-output-must-remain-under-reports-generated")
    combined = output_root / COMBINED_EVIDENCE_NAME
    known = {
        VISUAL_LEDGER_NAME,
        PROFILE_LEDGER_NAME,
        VISUAL_EVIDENCE_NAME,
        PROFILE_EVIDENCE_NAME,
        COMBINED_EVIDENCE_NAME,
    }
    if resume:
        if not output_root.is_dir():
            blockers.append("resume-output-root-missing")
        elif combined.exists():
            blockers.append("resume-output-is-terminal")
        elif not any((output_root / name).exists() for name in known):
            blockers.append("resume-state-missing")
    elif output_root.exists():
        blockers.append("exclusive-output-root-used")
    return {
        **summary,
        "status": "ready" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "output_root": str(output_root),
        "resume": resume,
        "public_only_preflight": True,
        "provider_metadata_network_calls": 0,
        "provider_inference_calls": 0,
        "credential_value_emitted": False,
    }


def _safe_asset_path(asset: dict[str, Any]) -> Path:
    relative = Path(str(asset["render_path"]))
    if relative.is_absolute() or ".." in relative.parts:
        raise SupplementaryEvaluationError("visual asset path escaped the repository")
    path = (ROOT / relative).resolve()
    if not any(path.is_relative_to(root) for root in _ALLOWED_ASSET_ROOTS):
        raise SupplementaryEvaluationError("visual asset escaped approved public roots")
    if not path.is_file():
        raise SupplementaryEvaluationError(
            f"visual asset is missing: {asset['asset_id']}"
        )
    if hashlib.sha256(path.read_bytes()).hexdigest() != asset["render_sha256"]:
        raise SupplementaryEvaluationError("visual asset hash drifted")
    return path


def _image_data_url(asset: dict[str, Any], output_root: Path) -> str:
    path = _safe_asset_path(asset)
    if path.suffix.casefold() == ".png":
        image = path.read_bytes()
        mime_type = "image/png"
    else:
        with tempfile.TemporaryDirectory(
            prefix="program-002-visual-raster-", dir=output_root
        ) as directory:
            rendered = Path(directory) / "asset.png"
            try:
                subprocess.run(
                    [
                        "rsvg-convert",
                        "--keep-aspect-ratio",
                        "--width",
                        str(VISUAL_RASTER_MAX_WIDTH),
                        "--height",
                        str(VISUAL_RASTER_MAX_HEIGHT),
                        "--output",
                        str(rendered),
                        str(path),
                    ],
                    check=True,
                    capture_output=True,
                )
            except (OSError, subprocess.CalledProcessError) as error:
                raise SupplementaryEvaluationError(
                    "verified SVG rasterization failed"
                ) from error
            image = rendered.read_bytes()
            mime_type = "image/png"
    return f"data:{mime_type};base64," + base64.b64encode(image).decode("ascii")


def _image_data_sha256(data_url: str) -> str:
    try:
        header, encoded = data_url.split(",", 1)
        if not header.startswith("data:image/") or ";base64" not in header:
            raise ValueError
        payload = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as error:
        raise SupplementaryEvaluationError("visual image payload is malformed") from error
    return hashlib.sha256(payload).hexdigest()


def _visual_prompt(asset: dict[str, Any]) -> tuple[str, str]:
    system = (
        "Describe only facts visibly present in this educational image. "
        "The description will be question-independent retrieval metadata, not "
        "authoritative truth. Transcribe labels, entities, and relationships; "
        "state uncertainty and never infer an unseen question or answer."
    )
    prompt = json.dumps(
        {
            "asset_id": asset["asset_id"],
            "modality": asset["modality"],
            "original_region_ids": [
                row["region_id"] for row in asset["region_lineage"]
            ],
            "instruction": "Return a question-independent visual description.",
        },
        sort_keys=True,
    )
    return system, prompt


def _description_record(
    asset: dict[str, Any],
    response: ProviderJsonResponse,
    *,
    transmitted_image_sha256: str,
    expected_transmitted_image_sha256: str,
) -> dict[str, Any]:
    if response.provider_model != VISUAL_MODEL or response.attempt_count != 1:
        raise SupplementaryEvaluationError("visual provider identity or retry drifted")
    content = response.content
    segments = [
        str(content["transcription"]),
        *[str(value) for value in content["entities"]],
        *[str(value) for value in content["relationships"]],
    ]
    text = "\n".join(segments)
    return {
        "asset_id": asset["asset_id"],
        "course_id": asset["course_id"],
        "modality": asset["modality"],
        "source_document_path": asset["source_document_path"],
        "source_image_sha256": asset["render_sha256"],
        "transmitted_image_sha256": transmitted_image_sha256,
        "expected_transmitted_image_sha256": expected_transmitted_image_sha256,
        "region_ids": [row["region_id"] for row in asset["region_lineage"]],
        "description_text": text,
        "description_segments": segments,
    }


def _retrieval_score(query: str, document: str) -> float:
    query_tokens = _tokens(query)
    document_tokens = _tokens(document)
    if not query_tokens:
        return 0.0
    overlap = len(query_tokens & document_tokens) / len(query_tokens)
    phrase_bonus = sum(0.05 for token in query_tokens if token in document.casefold())
    return overlap + phrase_bonus


def _visual_retrieval_metrics(
    dataset: dict[str, Any], descriptions: list[dict[str, Any]], *, generated: bool
) -> dict[str, Any]:
    assets = {row["asset_id"]: row for row in dataset["assets"]}
    by_course: dict[str, list[dict[str, Any]]] = {}
    for row in descriptions:
        by_course.setdefault(row["course_id"], []).append(row)
    answerable_evidence: list[dict[str, Any]] = []
    boundary_evidence: list[dict[str, Any]] = []
    for case in dataset["cases"]:
        if case["expected_action"] != "answer":
            reason = case["boundary_reason"]
            action = _BOUNDARY_ACTIONS.get(reason)
            if action is None:
                raise SupplementaryEvaluationError("unknown visual boundary policy")
            boundary_evidence.append(
                {
                    "case_id": case["case_id"],
                    "expected_action": case["expected_action"],
                    "observed_action": action,
                    "action_correct": action == case["expected_action"],
                    "answer_released": False,
                }
            )
            continue
        candidates = by_course.get(case["course_id"], [])
        ranked = sorted(
            candidates,
            key=lambda row: (
                -_retrieval_score(
                    case["question"],
                    " ".join(
                        [
                            row["description_text"] if generated else "",
                            row.get("retrieval_alias", "") if generated else "",
                            row["modality"],
                            row["source_document_path"],
                        ]
                    ),
                ),
                hashlib.sha256(
                    f"program-002-visual-rank:{case['case_id']}:{row['asset_id']}".encode(
                        "utf-8"
                    )
                ).hexdigest(),
            ),
        )
        top_three = ranked[:3]
        top_five = ranked[:5]
        required_asset = case["required_asset_ids"][0]
        required_regions = set(case["required_region_ids"])
        target = next(
            (row for row in top_five if row["asset_id"] == required_asset), None
        )
        asset_at_three = any(row["asset_id"] == required_asset for row in top_three)
        lineage_at_three = any(
            row["asset_id"] == required_asset
            and required_regions <= set(row["region_ids"])
            and row["source_image_sha256"] == assets[required_asset]["render_sha256"]
            for row in top_three
        )
        fact_recall = (
            _recall(case["canonical_answer"], target["description_text"])
            if generated and target is not None
            else 0.0
        )
        fact_precision = (
            _supported_precision(case["canonical_answer"], target["description_text"])
            if generated and target is not None
            else 0.0
        )
        unsupported_segments = (
            [
                segment
                for segment in target.get("description_segments", [])
                if _supported_precision(case["canonical_answer"], segment) < 0.50
            ]
            if generated and target is not None
            else []
        )
        answerable_evidence.append(
            {
                "case_id": case["case_id"],
                "required_asset_id": required_asset,
                "retrieved_asset_ids_at_3": [row["asset_id"] for row in top_three],
                "asset_retrieved_at_3": asset_at_three,
                "required_region_lineage_at_3": lineage_at_three,
                "visual_fact_recall": fact_recall,
                "visual_fact_precision": fact_precision,
                "unsupported_segment_count": len(unsupported_segments),
            }
        )
    complete = sum(
        row["asset_retrieved_at_3"] and row["required_region_lineage_at_3"]
        for row in answerable_evidence
    )
    fact_complete = sum(
        float(row["visual_fact_recall"]) >= 0.90 for row in answerable_evidence
    )
    fact_recall = sum(
        float(row["visual_fact_recall"]) for row in answerable_evidence
    ) / len(answerable_evidence)
    fact_precision = sum(
        float(row["visual_fact_precision"]) for row in answerable_evidence
    ) / len(answerable_evidence)
    unsupported_visual_facts = sum(
        int(row["unsupported_segment_count"]) for row in answerable_evidence
    )
    boundary_correct = sum(row["action_correct"] for row in boundary_evidence)
    boundary_releases = sum(row["answer_released"] for row in boundary_evidence)
    lineage_count = sum(
        set(row["region_ids"])
        == {value["region_id"] for value in assets[row["asset_id"]]["region_lineage"]}
        and row["source_image_sha256"] == assets[row["asset_id"]]["render_sha256"]
        and row["transmitted_image_sha256"]
        == row["expected_transmitted_image_sha256"]
        for row in descriptions
    )
    return {
        "complete_evidence_at_3": complete / len(answerable_evidence),
        "complete_evidence_at_3_count": complete,
        "answerable_visual_fact_recall": fact_recall,
        "answerable_visual_fact_precision": fact_precision,
        "answerable_fact_complete_count": fact_complete,
        "unsupported_visual_fact_count": unsupported_visual_facts,
        "boundary_policy_accuracy": boundary_correct / len(boundary_evidence),
        "boundary_release_count": boundary_releases,
        "original_region_lineage_rate": lineage_count / len(descriptions),
        "original_region_lineage_count": lineage_count,
        "answerable_case_evidence": answerable_evidence,
        "boundary_case_evidence": boundary_evidence,
    }


def _metric(
    name: str,
    value: float,
    threshold: float,
    *,
    lower_is_better: bool = False,
) -> dict[str, Any]:
    passed = value <= threshold if lower_is_better else value >= threshold
    return {
        "name": name,
        "value": value,
        "unit": "count" if lower_is_better else "rate",
        "direction": "lower-is-better" if lower_is_better else "higher-is-better",
        "threshold": threshold,
        "passed": passed,
    }


def _visual_evidence_payload(
    *,
    program: dict[str, Any],
    dataset: dict[str, Any],
    descriptions: list[dict[str, Any]],
    provider: dict[str, Any],
    code_revision: str,
) -> dict[str, Any]:
    control = _visual_retrieval_metrics(dataset, descriptions, generated=False)
    candidate = _visual_retrieval_metrics(dataset, descriptions, generated=True)
    quality_passed = (
        candidate["complete_evidence_at_3"] >= 0.90
        and candidate["answerable_fact_complete_count"] >= 29
        and candidate["answerable_visual_fact_recall"] >= 29 / 30
        and candidate["answerable_visual_fact_precision"] >= 0.90
        and candidate["unsupported_visual_fact_count"] == 0
        and candidate["boundary_policy_accuracy"] == 1.0
        and candidate["boundary_release_count"] == 0
        and candidate["original_region_lineage_rate"] == 1.0
    )

    def candidate_record(
        *, role: str, implementation_id: str, metrics: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "role": role,
            "implementation": {
                "implementation_id": implementation_id,
                "version": "v1",
                "configuration": {
                    "course_scoped": True,
                    "top_k_evidence": 3,
                    "provider_model": VISUAL_MODEL if role == "candidate" else "none",
                    "program_sha256": program["content_sha256"],
                },
            },
            "metrics": [
                _metric(
                    "complete-visual-evidence-at-3",
                    float(metrics["complete_evidence_at_3"]),
                    0.90,
                ),
                _metric(
                    "answerable-visual-fact-recall",
                    float(metrics["answerable_visual_fact_recall"]),
                    29 / 30,
                ),
                _metric(
                    "answerable-visual-fact-precision",
                    float(metrics["answerable_visual_fact_precision"]),
                    0.90,
                ),
                _metric(
                    "boundary-policy-accuracy",
                    float(metrics["boundary_policy_accuracy"]),
                    1.0,
                ),
                _metric(
                    "original-region-lineage-rate",
                    float(metrics["original_region_lineage_rate"]),
                    1.0,
                ),
                _metric(
                    "boundary-release-count",
                    float(metrics["boundary_release_count"]),
                    0.0,
                    lower_is_better=True,
                ),
            ],
            "hard_gates": [
                {
                    "name": "zero-unsupported-visual-facts",
                    "passed": metrics["unsupported_visual_fact_count"] == 0,
                    "evidence": "Every accepted transcription, entity, and relationship segment must be deterministically supported by the canonical visual fact.",
                },
                {
                    "name": "public-only-inputs",
                    "passed": dataset["private_data_used"] is False,
                    "evidence": "The frozen visual supplement contains public/open or deterministic synthetic assets only.",
                },
                {
                    "name": "question-independent-description",
                    "passed": True,
                    "evidence": "Provider prompts contain asset metadata and image bytes but no evaluation question, expected action, or canonical answer.",
                },
                {
                    "name": "deterministic-boundary-policy",
                    "passed": metrics["boundary_release_count"] == 0,
                    "evidence": f"Observed {metrics['boundary_release_count']} answer releases across 30 boundary cases.",
                },
                {
                    "name": "provider-accounting",
                    "passed": (
                        provider["provider_calls"] == VISUAL_MAXIMUM_CALLS
                        and provider["provider_attempts"] == VISUAL_MAXIMUM_CALLS
                        and provider["reported_cost_usd"] <= VISUAL_MAXIMUM_COST_USD
                    ),
                    "evidence": "Thirty exact-model calls, zero retries, and the USD 2 stage stop are required.",
                },
            ],
            "failures_by_category": {
                "incomplete-evidence-at-3": 30
                - int(metrics["complete_evidence_at_3_count"]),
                "incomplete-visual-fact": 30
                - int(metrics["answerable_fact_complete_count"]),
                "boundary-action-error": 30
                - int(round(float(metrics["boundary_policy_accuracy"]) * 30)),
                "boundary-release": int(metrics["boundary_release_count"]),
                "lineage-error": 30 - int(metrics["original_region_lineage_count"]),
                "unsupported-visual-fact": int(
                    metrics["unsupported_visual_fact_count"]
                ),
            },
        }

    return {
        "schema_version": 1,
        "run_id": VISUAL_RUN_ID,
        "program_id": PROGRAM_ID,
        "program_sha256": program["content_sha256"],
        "stage": VISUAL_STAGE,
        "stage_status": "completed-go-deeper" if quality_passed else "completed-refine",
        "quality_gates_passed": quality_passed,
        "component": "figure-description",
        "dataset_id": dataset["dataset_id"],
        "corpus_id": "academic-factual-qa-public-visual-supplement-001",
        "code_revision": code_revision,
        "candidates": [
            candidate_record(
                role="control",
                implementation_id="course-scoped-visual-metadata-control",
                metrics=control,
            ),
            candidate_record(
                role="candidate",
                implementation_id="course-scoped-openai-visual-description-retrieval",
                metrics=candidate,
            ),
        ],
        "decision": {
            "outcome": "go-deeper" if quality_passed else "refine",
            "selected_implementation_id": (
                "course-scoped-openai-visual-description-retrieval"
                if quality_passed
                else None
            ),
            "rationale": (
                "The generated-description retrieval candidate passed every frozen visual and boundary gate."
                if quality_passed
                else "The visual stage completed validly but at least one frozen quality gate failed; Refine is terminal for this stage."
            ),
            "limitations": [
                "The 30-cluster public/synthetic supplement is development evidence, not a general visual-understanding estimate.",
                "Generated descriptions are non-authoritative retrieval metadata; citations retain original asset and region lineage.",
                "There is no independent human visual annotation in this stage.",
            ],
        },
        "case_evidence": {
            "answerable": candidate["answerable_case_evidence"],
            "boundary": candidate["boundary_case_evidence"],
        },
        "operational_summary": {
            "provider_model": VISUAL_MODEL,
            "provider_calls": int(provider["provider_calls"]),
            "provider_attempts": int(provider["provider_attempts"]),
            "maximum_calls": VISUAL_MAXIMUM_CALLS,
            "maximum_cost_usd": VISUAL_MAXIMUM_COST_USD,
            "reported_cost_usd": float(provider["reported_cost_usd"]),
            "raw_output_path": VISUAL_LEDGER_NAME,
            "request_store": False,
            "private_data_used": False,
            "hidden_data_opened": False,
            "human_participants": 0,
        },
    }


def _profile_prompt(
    case: dict[str, Any], condition: str, profile: dict[str, Any]
) -> tuple[str, str]:
    if condition not in CONDITIONS:
        raise SupplementaryEvaluationError("profile condition escaped C0-C2")
    answerable = case["expected_action"] == "answer"
    evidence: dict[str, Any] | None = None
    if condition in {"C1", "C2"}:
        evidence = {
            "canonical_source_fact": case["canonical_answer"] if answerable else None,
            "original_region_ids": case["required_region_ids"],
            "evidence_available": answerable,
        }
    synthetic_profile = (
        {name: dimension["value"] for name, dimension in profile["dimensions"].items()}
        if condition == "C2"
        else None
    )
    system = (
        "Act as a bounded generic course tutor. Deterministic repository truth is "
        "authoritative. Answer only from supplied oracle evidence, otherwise choose "
        "abstain, clarify, or refuse. Never invent citations."
        if condition != "C2"
        else "Act as a bounded course tutor using the supplied synthetic profile. "
        "Deterministic repository truth is authoritative. Answer only from supplied "
        "oracle evidence, otherwise choose abstain, clarify, or refuse. Report which "
        "synthetic profile features were applied and never imply professor approval."
    )
    prompt = json.dumps(
        {
            "case_id": case["case_id"],
            "condition": condition,
            "question": case["question"],
            "oracle_evidence": evidence,
            "synthetic_profile": synthetic_profile,
        },
        sort_keys=True,
    )
    if (
        condition == "C0"
        and case["canonical_answer"]
        and case["canonical_answer"] in prompt
    ):
        raise SupplementaryEvaluationError("C0 prompt leaked oracle truth")
    return system, prompt


def _expected_profile_action(case: dict[str, Any], condition: str) -> str:
    if condition == "C0" and case["expected_action"] == "answer":
        return "abstain"
    return str(case["expected_action"])


def _profile_metrics(
    cases: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    condition: str,
    *,
    allowed_profile_features: set[str],
) -> dict[str, Any]:
    selected = [row for row in outputs if row["condition"] == condition]
    if len(selected) != len(cases):
        raise SupplementaryEvaluationError("profile output accounting drifted")
    by_id = {row["case_id"]: row for row in selected}
    evidence: list[dict[str, Any]] = []
    for case in cases:
        row = by_id[case["case_id"]]
        expected_action = _expected_profile_action(case, condition)
        required_regions = set(case["required_region_ids"])
        observed_regions = set(row["evidence_region_ids"])
        answerable_with_evidence = (
            condition in {"C1", "C2"} and case["expected_action"] == "answer"
        )
        lineage_correct = (
            observed_regions == required_regions
            if answerable_with_evidence and row["action"] == "answer"
            else not observed_regions
        )
        fact_recall = (
            _recall(case["canonical_answer"], row["response"])
            if answerable_with_evidence and row["action"] == "answer"
            else 0.0
            if case["expected_action"] == "answer"
            else 1.0
        )
        applied_features = set(row["applied_profile_features"])
        profile_contract = (
            bool(applied_features)
            and applied_features <= allowed_profile_features
            if condition == "C2"
            else not applied_features
        )
        unsupported_release = row["action"] == "answer" and (
            condition == "C0" or case["expected_action"] != "answer"
        )
        evidence.append(
            {
                "case_id": case["case_id"],
                "condition": condition,
                "expected_action": expected_action,
                "observed_action": row["action"],
                "action_correct": row["action"] == expected_action,
                "visual_fact_recall": fact_recall,
                "lineage_correct": lineage_correct,
                "profile_contract_correct": profile_contract,
                "unsupported_release": unsupported_release,
            }
        )
    boundary = [
        row
        for row in evidence
        if next(case for case in cases if case["case_id"] == row["case_id"])[
            "expected_action"
        ]
        != "answer"
    ]
    answerable = [
        row
        for row in evidence
        if next(case for case in cases if case["case_id"] == row["case_id"])[
            "expected_action"
        ]
        == "answer"
    ]
    return {
        "action_accuracy": sum(row["action_correct"] for row in evidence)
        / len(evidence),
        "boundary_policy_accuracy": sum(row["action_correct"] for row in boundary)
        / len(boundary),
        "answerable_visual_fact_recall": sum(
            float(row["visual_fact_recall"]) for row in answerable
        )
        / len(answerable),
        "lineage_accuracy": sum(row["lineage_correct"] for row in evidence)
        / len(evidence),
        "condition_contract_accuracy": sum(
            row["profile_contract_correct"] for row in evidence
        )
        / len(evidence),
        "unsupported_release_count": sum(
            row["unsupported_release"] for row in evidence
        ),
        "case_evidence": evidence,
    }


def _profile_evidence_payload(
    *,
    program: dict[str, Any],
    dataset: dict[str, Any],
    profile: dict[str, Any],
    cases: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    provider: dict[str, Any],
    code_revision: str,
) -> dict[str, Any]:
    metrics = {
        condition: _profile_metrics(
            cases,
            outputs,
            condition,
            allowed_profile_features=set(profile["dimensions"]),
        )
        for condition in CONDITIONS
    }
    candidate = metrics["C2"]
    c1_by_id = {
        row["case_id"]: row for row in outputs if row["condition"] == "C1"
    }
    c2_by_id = {
        row["case_id"]: row for row in outputs if row["condition"] == "C2"
    }
    paired_profile_effect_count = sum(
        c1_by_id[case["case_id"]]["response"].strip()
        != c2_by_id[case["case_id"]]["response"].strip()
        for case in cases
    )
    paired_profile_effect_rate = paired_profile_effect_count / len(cases)
    quality_passed = (
        candidate["action_accuracy"] >= 0.95
        and candidate["boundary_policy_accuracy"] == 1.0
        and candidate["answerable_visual_fact_recall"] >= 0.90
        and candidate["lineage_accuracy"] == 1.0
        and candidate["condition_contract_accuracy"] == 1.0
        and candidate["unsupported_release_count"] == 0
        and paired_profile_effect_rate >= 0.75
    )

    def condition_record(condition: str) -> dict[str, Any]:
        values = metrics[condition]
        return {
            "role": "control" if condition == "C0" else "candidate",
            "condition": condition,
            "implementation": {
                "implementation_id": {
                    "C0": "synthetic-profile-c0-no-evidence-generic",
                    "C1": "synthetic-profile-c1-oracle-evidence-generic",
                    "C2": "synthetic-profile-c2-oracle-evidence-profile",
                }[condition],
                "version": "v1",
                "configuration": {
                    "provider_model": PROFILE_MODEL,
                    "oracle_evidence": condition in {"C1", "C2"},
                    "synthetic_profile": condition == "C2",
                    "program_sha256": program["content_sha256"],
                },
            },
            "metrics": [
                _metric("action-accuracy", values["action_accuracy"], 0.95),
                _metric(
                    "boundary-policy-accuracy",
                    values["boundary_policy_accuracy"],
                    1.0,
                ),
                _metric(
                    "answerable-visual-fact-recall",
                    values["answerable_visual_fact_recall"],
                    0.90,
                ),
                _metric("evidence-lineage-accuracy", values["lineage_accuracy"], 1.0),
                _metric(
                    "condition-contract-accuracy",
                    values["condition_contract_accuracy"],
                    1.0,
                ),
                _metric(
                    "unsupported-release-count",
                    float(values["unsupported_release_count"]),
                    0.0,
                    lower_is_better=True,
                ),
                _metric(
                    "paired-profile-effect-rate",
                    paired_profile_effect_rate,
                    0.75,
                ),
            ],
            "hard_gates": [
                {
                    "name": "deterministic-truth-authoritative",
                    "passed": True,
                    "evidence": "Actions, canonical facts, evidence identities, and policy scoring come from the frozen public dataset.",
                },
                {
                    "name": "condition-input-contract",
                    "passed": values["condition_contract_accuracy"] == 1.0,
                    "evidence": "C0 has no evidence/profile, C1 has oracle evidence only, and C2 adds only the unapproved synthetic profile.",
                },
                {
                    "name": "provider-accounting",
                    "passed": (
                        provider["provider_calls"] == PROFILE_MAXIMUM_CALLS
                        and provider["provider_attempts"] == PROFILE_MAXIMUM_CALLS
                        and provider["reported_cost_usd"] <= PROFILE_MAXIMUM_COST_USD
                    ),
                    "evidence": "Thirty-six exact-model calls, zero retries, and the USD 1.5 stage stop are required.",
                },
                {
                    "name": "paired-profile-effect",
                    "passed": paired_profile_effect_rate >= 0.75,
                    "evidence": "C2 must differ from paired C1 on at least nine of twelve responses while retaining identical truth and evidence gates.",
                },
            ],
            "failures_by_category": {
                "action-error": 12 - int(round(float(values["action_accuracy"]) * 12)),
                "boundary-action-error": 6
                - int(round(float(values["boundary_policy_accuracy"]) * 6)),
                "lineage-error": 12
                - int(round(float(values["lineage_accuracy"]) * 12)),
                "condition-contract-error": 12
                - int(round(float(values["condition_contract_accuracy"]) * 12)),
                "unsupported-release": int(values["unsupported_release_count"]),
                "missing-paired-profile-effect": (
                    12 - paired_profile_effect_count if condition == "C2" else 0
                ),
            },
        }

    return {
        "schema_version": 1,
        "run_id": PROFILE_RUN_ID,
        "program_id": PROGRAM_ID,
        "program_sha256": program["content_sha256"],
        "stage": PROFILE_STAGE,
        "program_manifest_stage": "synthetic-profile-c0-c3",
        "stage_status": "completed-go-deeper" if quality_passed else "completed-refine",
        "quality_gates_passed": quality_passed,
        "paired_profile_effect_count": paired_profile_effect_count,
        "paired_profile_effect_rate": paired_profile_effect_rate,
        "component": "tutor-policy",
        "dataset_id": "academic-factual-qa-visual-supplement-001-profile-stratified-12",
        "corpus_id": "public-and-synthetic-visual-facts-only",
        "code_revision": code_revision,
        "conditions_executed": list(CONDITIONS),
        "conditions_skipped": [
            {
                "condition": SKIPPED_CONDITION,
                "reason": "C3 requires a selected factual retrieval/product path; AFQC-103 ended that branch with a valid Refine result.",
            }
        ],
        "candidates": [condition_record(condition) for condition in CONDITIONS],
        "decision": {
            "outcome": "go-deeper" if quality_passed else "refine",
            "selected_implementation_id": (
                "synthetic-profile-c2-oracle-evidence-profile"
                if quality_passed
                else None
            ),
            "rationale": (
                "C2 passed the frozen synthetic diagnostic gates and demonstrated a paired response effect over C1; this supports further calibration but selects no professor profile."
                if quality_passed
                else "C2 completed validly but failed at least one frozen synthetic diagnostic gate."
            ),
            "limitations": [
                "C3 was not run because the factual retrieval/product branch failed prospectively.",
                "The profile is synthetic, draft, and unapproved; no professor-fidelity claim is possible.",
                "Oracle evidence isolates evidence and profile effects but is not product retrieval.",
                "The direct OpenAI outputs are non-authoritative; deterministic truth and policy graders control the result.",
            ],
        },
        "case_evidence": [
            row
            for condition in CONDITIONS
            for row in metrics[condition]["case_evidence"]
        ],
        "profile_boundary": {
            "profile_id": profile["profile_id"],
            "profile_sha256": hashlib.sha256(
                SYNTHETIC_PROFILE_PATH.read_bytes()
            ).hexdigest(),
            "profile_status": profile["status"],
            "professor_approved": False,
            "professor_fidelity_claim": False,
        },
        "operational_summary": {
            "provider_model": PROFILE_MODEL,
            "provider_calls": int(provider["provider_calls"]),
            "provider_attempts": int(provider["provider_attempts"]),
            "maximum_calls": PROFILE_MAXIMUM_CALLS,
            "maximum_cost_usd": PROFILE_MAXIMUM_COST_USD,
            "reported_cost_usd": float(provider["reported_cost_usd"]),
            "raw_output_path": PROFILE_LEDGER_NAME,
            "request_store": False,
            "private_data_used": False,
            "hidden_data_opened": False,
            "human_participants": 0,
        },
    }


def _ledger_metadata(path: Path) -> dict[str, str]:
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            return dict(connection.execute("SELECT key, value FROM metadata"))
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise SupplementaryEvaluationError("provider ledger is corrupt") from error


def _completed_ledger(
    path: Path,
    *,
    run_binding: dict[str, Any],
    maximum_calls: int,
    maximum_cost_usd: float,
) -> tuple[dict[str, ProviderJsonResponse], dict[str, Any]]:
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            if (
                metadata.get("status") != "completed"
                or metadata.get("run_binding_sha256") != canonical_sha256(run_binding)
                or metadata.get("maximum_calls") != str(maximum_calls)
                or metadata.get("maximum_cost_usd") != str(maximum_cost_usd)
                or metadata.get("maximum_transport_retries_total") != "0"
            ):
                raise SupplementaryEvaluationError("completed ledger binding drifted")
            rows = list(
                connection.execute(
                    "SELECT request_key, response_json, status, attempt_count, "
                    "input_tokens, output_tokens, cost_usd, latency_ms "
                    "FROM calls ORDER BY sequence"
                )
            )
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise SupplementaryEvaluationError("provider ledger is corrupt") from error
    if (
        len(rows) != maximum_calls
        or any(row[2] != "completed" or row[1] is None for row in rows)
        or any(int(row[3]) != 1 for row in rows)
    ):
        raise SupplementaryEvaluationError("completed ledger accounting drifted")
    responses = {
        str(row[0]): ProviderJsonResponse.model_validate_json(row[1]) for row in rows
    }
    cost = sum(float(row[6]) for row in rows)
    if cost > maximum_cost_usd:
        raise SupplementaryEvaluationError("completed ledger exceeded stage budget")
    snapshot = {
        **metadata,
        "provider_calls": len(rows),
        "provider_attempts": sum(int(row[3]) for row in rows),
        "recovered_transport_failures": sum(int(row[3]) - 1 for row in rows),
        "failed_calls": 0,
        "input_tokens": sum(int(row[4]) for row in rows),
        "output_tokens": sum(int(row[5]) for row in rows),
        "maximum_latency_ms": max(float(row[7]) for row in rows),
        "reported_cost_usd": cost,
    }
    return responses, snapshot


def _run_binding(
    *,
    program: dict[str, Any],
    stage: str,
    binding: dict[str, Any],
    dataset: dict[str, Any],
    code_revision: str,
    profile_sha256: str | None = None,
) -> dict[str, Any]:
    value = {
        "program_id": PROGRAM_ID,
        "program_sha256": program["content_sha256"],
        "stage": stage,
        "provider_binding": binding,
        "visual_dataset_sha256": dataset["content_sha256"],
        "code_revision": code_revision,
        "private_data_used": False,
        "hidden_data_opened": False,
    }
    if profile_sha256 is not None:
        value["synthetic_profile_sha256"] = profile_sha256
        value["conditions"] = list(CONDITIONS)
    return value


async def _execute_visual_stage(
    *,
    program: dict[str, Any],
    dataset: dict[str, Any],
    binding: dict[str, Any],
    output_root: Path,
    resume: bool,
    code_revision: str,
    transport_factory: Callable[[dict[str, Any]], Any],
    image_data_url_factory: Callable[[dict[str, Any], Path], str],
) -> dict[str, Any]:
    evidence_path = output_root / VISUAL_EVIDENCE_NAME
    ledger_path = output_root / VISUAL_LEDGER_NAME
    run_binding = _run_binding(
        program=program,
        stage=VISUAL_STAGE,
        binding=binding,
        dataset=dataset,
        code_revision=code_revision,
    )
    if evidence_path.exists():
        if not resume or not ledger_path.is_file():
            raise SupplementaryEvaluationError(
                "visual evidence is exclusive or incomplete"
            )
        _completed_ledger(
            ledger_path,
            run_binding=run_binding,
            maximum_calls=VISUAL_MAXIMUM_CALLS,
            maximum_cost_usd=VISUAL_MAXIMUM_COST_USD,
        )
        return _load_sanitized(
            evidence_path,
            run_id=VISUAL_RUN_ID,
            program_sha256=program["content_sha256"],
        )
    image_payloads: dict[str, str] = {}
    transmitted_image_hashes: dict[str, str] = {}
    expected_image_hashes: dict[str, str] = {}
    for asset in sorted(dataset["assets"], key=lambda row: row["asset_id"]):
        actual = image_data_url_factory(asset, output_root)
        expected = _image_data_url(asset, output_root)
        actual_sha256 = _image_data_sha256(actual)
        expected_sha256 = _image_data_sha256(expected)
        if actual_sha256 != expected_sha256:
            raise SupplementaryEvaluationError(
                "transmitted visual raster does not match the pinned source render"
            )
        image_payloads[asset["asset_id"]] = actual
        transmitted_image_hashes[asset["asset_id"]] = actual_sha256
        expected_image_hashes[asset["asset_id"]] = expected_sha256
    existing_status = (
        _ledger_metadata(ledger_path).get("status") if ledger_path.exists() else None
    )
    if existing_status == "completed":
        if not resume:
            raise SupplementaryEvaluationError("visual ledger is terminal")
        responses, provider = _completed_ledger(
            ledger_path,
            run_binding=run_binding,
            maximum_calls=VISUAL_MAXIMUM_CALLS,
            maximum_cost_usd=VISUAL_MAXIMUM_COST_USD,
        )
    else:
        ledger = ProviderCallLedgerV1(
            ledger_path,
            run_binding=run_binding,
            maximum_calls=VISUAL_MAXIMUM_CALLS,
            maximum_cost_usd=VISUAL_MAXIMUM_COST_USD,
            resume=resume and ledger_path.exists(),
            maximum_transport_retries_total=0,
        )
        transport = transport_factory(binding)
        responses = {}
        try:
            for asset in sorted(dataset["assets"], key=lambda row: row["asset_id"]):
                system, prompt = _visual_prompt(asset)
                response = await transport.call_with_ledger(
                    ledger=ledger,
                    request_key=f"visual-{asset['asset_id']}",
                    provider_role="question-independent-visual-description",
                    system=system,
                    prompt=prompt,
                    task="program-002-question-independent-visual-description",
                    schema=_visual_schema(),
                    image_data_urls=[image_payloads[asset["asset_id"]]],
                )
                responses[f"visual-{asset['asset_id']}"] = response
            snapshot = ledger.snapshot()
            if (
                snapshot["provider_calls"] != VISUAL_MAXIMUM_CALLS
                or snapshot["provider_attempts"] != VISUAL_MAXIMUM_CALLS
                or snapshot["recovered_transport_failures"] != 0
            ):
                ledger.mark_invalid_execution()
                raise SupplementaryEvaluationError("visual call accounting drifted")
            ledger.mark_complete()
            provider = ledger.snapshot()
        except KeyboardInterrupt:
            if ledger.snapshot().get("status") == "running":
                ledger.mark_interrupted()
            raise
        except BaseException:
            if ledger.snapshot().get("status") == "running":
                ledger.mark_invalid_execution()
            raise
        finally:
            ledger.close()
    descriptions = []
    for asset in sorted(dataset["assets"], key=lambda row: row["asset_id"]):
        key = f"visual-{asset['asset_id']}"
        if key not in responses:
            raise SupplementaryEvaluationError(
                "visual response portfolio is incomplete"
            )
        descriptions.append(
            _description_record(
                asset,
                responses[key],
                transmitted_image_sha256=transmitted_image_hashes[asset["asset_id"]],
                expected_transmitted_image_sha256=expected_image_hashes[
                    asset["asset_id"]
                ],
            )
        )
    payload = _visual_evidence_payload(
        program=program,
        dataset=dataset,
        descriptions=descriptions,
        provider=provider,
        code_revision=code_revision,
    )
    _write_exclusive_json(evidence_path, payload)
    return _load_sanitized(
        evidence_path,
        run_id=VISUAL_RUN_ID,
        program_sha256=program["content_sha256"],
    )


async def _execute_profile_stage(
    *,
    program: dict[str, Any],
    dataset: dict[str, Any],
    profile: dict[str, Any],
    cases: list[dict[str, Any]],
    binding: dict[str, Any],
    output_root: Path,
    resume: bool,
    code_revision: str,
    transport_factory: Callable[[dict[str, Any]], Any],
) -> dict[str, Any]:
    evidence_path = output_root / PROFILE_EVIDENCE_NAME
    ledger_path = output_root / PROFILE_LEDGER_NAME
    profile_sha256 = hashlib.sha256(SYNTHETIC_PROFILE_PATH.read_bytes()).hexdigest()
    run_binding = _run_binding(
        program=program,
        stage=PROFILE_STAGE,
        binding=binding,
        dataset=dataset,
        code_revision=code_revision,
        profile_sha256=profile_sha256,
    )
    if evidence_path.exists():
        if not resume or not ledger_path.is_file():
            raise SupplementaryEvaluationError(
                "profile evidence is exclusive or incomplete"
            )
        _completed_ledger(
            ledger_path,
            run_binding=run_binding,
            maximum_calls=PROFILE_MAXIMUM_CALLS,
            maximum_cost_usd=PROFILE_MAXIMUM_COST_USD,
        )
        return _load_sanitized(
            evidence_path,
            run_id=PROFILE_RUN_ID,
            program_sha256=program["content_sha256"],
        )
    existing_status = (
        _ledger_metadata(ledger_path).get("status") if ledger_path.exists() else None
    )
    if existing_status == "completed":
        if not resume:
            raise SupplementaryEvaluationError("profile ledger is terminal")
        responses, provider = _completed_ledger(
            ledger_path,
            run_binding=run_binding,
            maximum_calls=PROFILE_MAXIMUM_CALLS,
            maximum_cost_usd=PROFILE_MAXIMUM_COST_USD,
        )
    else:
        ledger = ProviderCallLedgerV1(
            ledger_path,
            run_binding=run_binding,
            maximum_calls=PROFILE_MAXIMUM_CALLS,
            maximum_cost_usd=PROFILE_MAXIMUM_COST_USD,
            resume=resume and ledger_path.exists(),
            maximum_transport_retries_total=0,
        )
        transport = transport_factory(binding)
        responses = {}
        try:
            for condition in CONDITIONS:
                for case in cases:
                    system, prompt = _profile_prompt(case, condition, profile)
                    key = f"profile-{condition}-{case['case_id']}"
                    response = await transport.call_with_ledger(
                        ledger=ledger,
                        request_key=key,
                        provider_role="synthetic-profile-diagnostic",
                        system=system,
                        prompt=prompt,
                        task="program-002-synthetic-profile-c0-c2",
                        schema=_profile_schema(case["case_id"], condition),
                    )
                    responses[key] = response
            snapshot = ledger.snapshot()
            if (
                snapshot["provider_calls"] != PROFILE_MAXIMUM_CALLS
                or snapshot["provider_attempts"] != PROFILE_MAXIMUM_CALLS
                or snapshot["recovered_transport_failures"] != 0
            ):
                ledger.mark_invalid_execution()
                raise SupplementaryEvaluationError("profile call accounting drifted")
            ledger.mark_complete()
            provider = ledger.snapshot()
        except KeyboardInterrupt:
            if ledger.snapshot().get("status") == "running":
                ledger.mark_interrupted()
            raise
        except BaseException:
            if ledger.snapshot().get("status") == "running":
                ledger.mark_invalid_execution()
            raise
        finally:
            ledger.close()
    outputs: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        for case in cases:
            key = f"profile-{condition}-{case['case_id']}"
            response = responses.get(key)
            if response is None:
                raise SupplementaryEvaluationError(
                    "profile response portfolio is incomplete"
                )
            if response.provider_model != PROFILE_MODEL or response.attempt_count != 1:
                raise SupplementaryEvaluationError(
                    "profile provider identity or retry drifted"
                )
            outputs.append(dict(response.content))
    payload = _profile_evidence_payload(
        program=program,
        dataset=dataset,
        profile=profile,
        cases=cases,
        outputs=outputs,
        provider=provider,
        code_revision=code_revision,
    )
    _write_exclusive_json(evidence_path, payload)
    return _load_sanitized(
        evidence_path,
        run_id=PROFILE_RUN_ID,
        program_sha256=program["content_sha256"],
    )


def _combined_payload(
    *, program: dict[str, Any], visual: dict[str, Any], profile: dict[str, Any]
) -> dict[str, Any]:
    total_calls = int(visual["operational_summary"]["provider_calls"]) + int(
        profile["operational_summary"]["provider_calls"]
    )
    total_cost = float(visual["operational_summary"]["reported_cost_usd"]) + float(
        profile["operational_summary"]["reported_cost_usd"]
    )
    if total_calls != VISUAL_MAXIMUM_CALLS + PROFILE_MAXIMUM_CALLS:
        raise SupplementaryEvaluationError("supplement call accounting drifted")
    if total_cost > SUPPLEMENT_MAXIMUM_COST_USD:
        raise SupplementaryEvaluationError("supplement global budget exceeded")
    return {
        "schema_version": 1,
        "run_id": COMBINED_RUN_ID,
        "program_id": PROGRAM_ID,
        "program_sha256": program["content_sha256"],
        "status": "completed",
        "stage_results": [
            {
                "stage": visual["stage"],
                "run_id": visual["run_id"],
                "status": visual["stage_status"],
                "quality_gates_passed": visual["quality_gates_passed"],
                "sanitized_evidence_path": VISUAL_EVIDENCE_NAME,
                "sanitized_evidence_sha256": visual["content_sha256"],
            },
            {
                "stage": profile["stage"],
                "run_id": profile["run_id"],
                "status": profile["stage_status"],
                "quality_gates_passed": profile["quality_gates_passed"],
                "sanitized_evidence_path": PROFILE_EVIDENCE_NAME,
                "sanitized_evidence_sha256": profile["content_sha256"],
            },
        ],
        "independent_quality_failures_do_not_skip_peer_stage": True,
        "conditions_executed": list(CONDITIONS),
        "conditions_skipped": [SKIPPED_CONDITION],
        "c3_skip_reason": "The factual branch ended at AFQC-103 Refine; no selected retrieval/product path exists for C3.",
        "provider_calls": total_calls,
        "maximum_calls": VISUAL_MAXIMUM_CALLS + PROFILE_MAXIMUM_CALLS,
        "reported_cost_usd": total_cost,
        "maximum_cost_usd": SUPPLEMENT_MAXIMUM_COST_USD,
        "private_data_used": False,
        "hidden_data_opened": False,
        "human_participants": 0,
        "professor_fidelity_claim": False,
        "completed_at": datetime.now(UTC).isoformat(),
    }


async def execute(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    resume: bool = False,
    transport_factory: Callable[[dict[str, Any]], Any] = DirectProviderJsonTransport,
    image_data_url_factory: Callable[[dict[str, Any], Path], str] = _image_data_url,
    enforce_preflight: bool = True,
) -> dict[str, Any]:
    if not _output_root_is_safe(output_root):
        raise SupplementaryEvaluationError(
            "raw output must remain under reports/generated"
        )
    require_bounded_pilot_operation_allowed(PROGRAM_ID, "dataset_generation")
    require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
    require_bounded_pilot_operation_allowed(PROGRAM_ID, "method_evaluation_execution")
    if enforce_preflight:
        readiness = preflight(output_root=output_root, resume=resume)
        if readiness["status"] != "ready":
            raise SupplementaryEvaluationError(
                "supplement preflight blocked: " + ", ".join(readiness["blockers"])
            )
    program = _load_program()
    dataset = _visual_dataset()
    profile = _synthetic_profile()
    cases = _stratified_profile_cases(dataset)
    bindings = _bindings(program)
    _validate_provider_contracts(bindings)
    code_revision = _repo_revision()
    if not resume:
        output_root.mkdir(parents=True, exist_ok=False)
    elif not output_root.is_dir():
        raise SupplementaryEvaluationError("resume output root is missing")

    # Rendered table/equation images remain ignored raw execution assets.
    materialized = visual_builder.build_dataset(write_assets=True)
    if materialized != dataset:
        raise SupplementaryEvaluationError("materialized visual supplement drifted")

    visual = await _execute_visual_stage(
        program=program,
        dataset=dataset,
        binding=bindings["visual"],
        output_root=output_root,
        resume=resume,
        code_revision=code_revision,
        transport_factory=transport_factory,
        image_data_url_factory=image_data_url_factory,
    )
    # A valid visual Refine is a terminal visual result, not a program-level
    # safety failure. Stage B is independently authorized and still executes.
    profile_result = await _execute_profile_stage(
        program=program,
        dataset=dataset,
        profile=profile,
        cases=cases,
        binding=bindings["profile"],
        output_root=output_root,
        resume=resume,
        code_revision=code_revision,
        transport_factory=transport_factory,
    )
    combined_path = output_root / COMBINED_EVIDENCE_NAME
    if combined_path.exists():
        raise SupplementaryEvaluationError("combined evidence output already exists")
    _write_exclusive_json(
        combined_path,
        _combined_payload(program=program, visual=visual, profile=profile_result),
    )
    return _load_sanitized(
        combined_path,
        run_id=COMBINED_RUN_ID,
        program_sha256=program["content_sha256"],
    )


def _simulated_description(
    asset: dict[str, Any], case_by_asset: dict[str, dict[str, Any]], *, passing: bool
) -> dict[str, Any]:
    case = case_by_asset[asset["asset_id"]]
    text = (
        case["canonical_answer"]
        if passing
        else "Unrelated visual content with no source-linked fact."
    )
    return {
        "asset_id": asset["asset_id"],
        "course_id": asset["course_id"],
        "modality": asset["modality"],
        "source_document_path": asset["source_document_path"],
        "source_image_sha256": asset["render_sha256"],
        "transmitted_image_sha256": asset["render_sha256"],
        "expected_transmitted_image_sha256": asset["render_sha256"],
        "region_ids": [row["region_id"] for row in asset["region_lineage"]],
        "description_text": text,
        "description_segments": [text],
        "retrieval_alias": case["question"] if passing else "",
    }


def _simulated_profile_outputs(
    cases: list[dict[str, Any]], profile: dict[str, Any], *, passing: bool
) -> list[dict[str, Any]]:
    feature = next(iter(profile["dimensions"]))
    outputs: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        for case in cases:
            expected = _expected_profile_action(case, condition)
            action = expected if passing else "answer"
            answerable_with_evidence = (
                condition in {"C1", "C2"} and case["expected_action"] == "answer"
            )
            outputs.append(
                {
                    "case_id": case["case_id"],
                    "condition": condition,
                    "action": action,
                    "response": (
                        (
                            "Profile-guided explanation: "
                            + case["canonical_answer"]
                            if condition == "C2"
                            else case["canonical_answer"]
                        )
                        if answerable_with_evidence
                        else (
                            "Profile-guided boundary: I cannot answer from authorized evidence."
                            if condition == "C2"
                            else "I cannot answer from authorized evidence."
                        )
                    ),
                    "evidence_region_ids": (
                        case["required_region_ids"]
                        if answerable_with_evidence and action == "answer"
                        else []
                    ),
                    "applied_profile_features": [feature] if condition == "C2" else [],
                }
            )
    return outputs


def simulate(
    *, visual_quality_pass: bool = True, profile_quality_pass: bool = True
) -> dict[str, Any]:
    program = _load_program()
    dataset = _visual_dataset()
    profile = _synthetic_profile()
    cases = _stratified_profile_cases(dataset)
    case_by_asset = {
        row["required_asset_ids"][0]: row
        for row in dataset["cases"]
        if row["expected_action"] == "answer"
    }
    descriptions = [
        _simulated_description(asset, case_by_asset, passing=visual_quality_pass)
        for asset in dataset["assets"]
    ]
    visual_provider = {
        "provider_calls": VISUAL_MAXIMUM_CALLS,
        "provider_attempts": VISUAL_MAXIMUM_CALLS,
        "reported_cost_usd": 0.0,
    }
    profile_provider = {
        "provider_calls": PROFILE_MAXIMUM_CALLS,
        "provider_attempts": PROFILE_MAXIMUM_CALLS,
        "reported_cost_usd": 0.0,
    }
    visual = _visual_evidence_payload(
        program=program,
        dataset=dataset,
        descriptions=descriptions,
        provider=visual_provider,
        code_revision="a" * 40,
    )
    profile_result = _profile_evidence_payload(
        program=program,
        dataset=dataset,
        profile=profile,
        cases=cases,
        outputs=_simulated_profile_outputs(
            cases, profile, passing=profile_quality_pass
        ),
        provider=profile_provider,
        code_revision="a" * 40,
    )
    return {
        "schema_version": 1,
        "run_id": COMBINED_RUN_ID,
        "program_id": PROGRAM_ID,
        "program_sha256": program["content_sha256"],
        "status": "simulated",
        "provider_calls": 0,
        "provider_inference_calls": 0,
        "simulated_accounted_calls": VISUAL_MAXIMUM_CALLS + PROFILE_MAXIMUM_CALLS,
        "visual_stage_status": visual["stage_status"],
        "profile_stage_status": profile_result["stage_status"],
        "both_stages_executed": True,
        "conditions_executed": list(CONDITIONS),
        "conditions_skipped": [SKIPPED_CONDITION],
        "private_data_used": False,
        "hidden_data_opened": False,
        "human_participants": 0,
        "professor_fidelity_claim": False,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true")
    action.add_argument("--simulate", action="store_true")
    action.add_argument("--preflight", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    arguments = parser.parse_args()
    if arguments.resume and not arguments.execute:
        parser.error("--resume is valid only with --execute")
    return arguments


def main() -> int:
    load_dotenv(ROOT / ".env")
    arguments = _arguments()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            PROGRAM_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            PROGRAM_ID, "method_evaluation_execution"
        )
    if arguments.validate:
        result = validate()
    elif arguments.simulate:
        result = simulate()
    elif arguments.preflight:
        result = preflight(output_root=arguments.output_root, resume=False)
    else:
        result = asyncio.run(
            execute(output_root=arguments.output_root, resume=arguments.resume)
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
