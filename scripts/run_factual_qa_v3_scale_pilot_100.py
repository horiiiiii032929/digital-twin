#!/usr/bin/env python3
"""Validate, simulate, or execute the bounded factual-QA v3 100-case stage.

The committed instrument is deliberately execution-unauthorized. The
network-free simulator exercises the complete durable state machine with fake
provider responses; the paid path fails closed until a separate authorization
checkpoint changes both the instrument and repository freeze policy.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Protocol

from dotenv import load_dotenv

from scripts.build_factual_qa_v3_10000_blueprints import build_artifact
from services.llm import LiteLlmClient
from src.digital_twin.llm import LlmMessage
from src.digital_twin.model_policy import require_registered_current_model
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)
from scripts.run_factual_qa_quality_pilot import (
    AUTHOR_SCHEMA,
    REVIEW_SCHEMA,
    validate_review as validate_shared_review,
)
from scripts.run_factual_qa_v3_scale_rehearsal import (
    _strict_review_prompt,
    _strict_review_system_prompt,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
    "factual_qa_v3_scale_pilot_100_002.json"
)
DEFAULT_OUTPUT = (
    ROOT / "reports/generated/factual-qa-v3-scale-pilot-100-002.json"
)
LEGACY_INSTRUMENT_ID = "factual-qa-v3-scale-pilot-100-001"
INSTRUMENT_ID = "factual-qa-v3-scale-pilot-100-002"
SUPPORTED_INSTRUMENT_IDS = frozenset({LEGACY_INSTRUMENT_ID, INSTRUMENT_ID})
PIPELINE_ID = "factual-qa-v3-10000-pipeline-001"
PILOT_STAGE = "pilot-100"
ANSWER_ACTION = "answer"
BOUNDARY_ACTIONS = frozenset({"abstain", "clarify", "refuse"})
EXPECTED_MODELS = {
    "author": "deepseek-v4-flash",
    "dispute_reviewer": "deepseek-v4-pro",
}
ROLE_NAMES = ("author", "independent_reviewer", "dispute_reviewer")
EXPECTED_CALL_LIMITS = {
    "provider_canary_call_limit": 2,
    "author_call_limit": 100,
    "independent_review_call_limit": 100,
    "mutation_review_call_limit": 20,
    "dispute_review_call_limit": 24,
    "total_provider_call_limit": 246,
}
EXPECTED_MUTATIONS = {
    "missing-citation": 4,
    "truncated-citation": 4,
    "paraphrased-citation": 3,
    "extra-supported-claim": 3,
    "invalid-claim-binding": 3,
    "invalid-source-binding": 3,
}
REVIEW_BOOLEAN_FIELDS = (
    "question_matches_blueprint",
    "answer_or_action_correct",
    "fully_supported",
    "citation_lineage_correct",
    "no_external_knowledge",
    "course_boundary_respected",
)
HEALTH_SCHEMA = {
    "type": "object",
    "required": ["status"],
    "properties": {"status": {"type": "string", "enum": ["ok"]}},
}


class ScalePilotError(ValueError):
    """Raised when the pilot contract or durable execution state is invalid."""


class PlannedInterruption(RuntimeError):
    """Test-only interruption after a durable checkpoint."""


@dataclass(frozen=True)
class RawCall:
    content: str
    provider_model: str
    provider_revision: str | None
    input_tokens: int
    output_tokens: int
    approximate_cost_usd: float
    latency_ms: float


class RawTransport(Protocol):
    async def call(
        self,
        *,
        system: str,
        prompt: str,
        task: str,
        schema: dict[str, Any],
    ) -> RawCall: ...


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ScalePilotError(f"cannot load JSON: {path}") from error
    if not isinstance(value, dict):
        raise ScalePilotError(f"JSON root must be an object: {path}")
    return value


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _code_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _working_tree_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def validate_instrument(path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    instrument = _load_json(path)
    if instrument.get("schema_version") != 1:
        raise ScalePilotError("unsupported scale-pilot instrument schema")
    instrument_id = instrument.get("instrument_id")
    if instrument_id not in SUPPORTED_INSTRUMENT_IDS:
        raise ScalePilotError("unexpected scale-pilot instrument ID")
    if instrument.get("model_leaderboard") is not False:
        raise ScalePilotError("the scale pilot cannot become a model leaderboard")
    design = instrument.get("blueprint_design", {})
    if design.get("instrument_id") != PIPELINE_ID:
        raise ScalePilotError("blueprint pipeline identity drifted")
    if design.get("stage_id") != PILOT_STAGE or design.get("case_count") != 100:
        raise ScalePilotError("pilot stage design drifted")
    if instrument_id == INSTRUMENT_ID:
        contract = instrument.get("contract_design", {})
        if contract != {
            "version": "factual-qa-v3-contract-v2",
            "author_schema": "shared-full-json-schema",
            "reviewer_contract": "qualification-006-strict-contract",
            "mutation_basis": "deterministic-canonical-cases",
        }:
            raise ScalePilotError("successor contract design drifted")
        if instrument.get("method_version") != "factual-qa-v3-staged-pipeline-v2":
            raise ScalePilotError("successor method version drifted")
    execution = instrument.get("execution", {})
    authorized = execution.get("provider_execution_authorized")
    allowed_statuses = (
        {"frozen-pending-execution"}
        if authorized is True
        else {
            "draft-reviewed-provider-execution-unauthorized",
            "completed-refine-authorization-revoked",
        }
    )
    if authorized not in {True, False} or instrument.get("status") not in allowed_statuses:
        raise ScalePilotError("instrument status and provider authorization drifted")
    if execution.get("dataset_write_authorized") is not False:
        raise ScalePilotError("dataset writing must remain unauthorized")
    if execution.get("automatic_stage_promotion") is not False:
        raise ScalePilotError("automatic stage promotion must remain disabled")
    if execution.get("retry_attempts") != 0:
        raise ScalePilotError("provider retries must remain disabled")
    for field, expected in EXPECTED_CALL_LIMITS.items():
        if execution.get(field) != expected:
            raise ScalePilotError(f"execution call limit drifted: {field}")
    if execution.get("cost_stop_usd") != 3.0:
        raise ScalePilotError("pilot cost stop drifted")
    if instrument.get("quality_gates", {}).get("external_cost_usd_max") != 3.0:
        raise ScalePilotError("pilot operational cost ceiling drifted")
    if instrument.get("mutation_design", {}).get("type_counts") != EXPECTED_MUTATIONS:
        raise ScalePilotError("mutation distribution drifted")
    roles = instrument.get("model_roles", {})
    for role, expected_model in EXPECTED_MODELS.items():
        binding = roles.get(role, {})
        if binding.get("provider_model") != expected_model:
            raise ScalePilotError(f"model binding drifted: {role}")
        require_registered_current_model(str(binding.get("provider_model", "")))
        for field in (
            "max_input_tokens",
            "max_output_tokens",
            "pricing_usd_per_million_input_tokens",
            "pricing_usd_per_million_output_tokens",
        ):
            value = binding.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise ScalePilotError(f"invalid {role} pricing/limit field: {field}")
    reviewer = roles.get("independent_reviewer", {})
    reviewer_model = str(reviewer.get("provider_model", ""))
    require_registered_current_model(reviewer_model)
    for field in (
        "max_input_tokens",
        "max_output_tokens",
        "pricing_usd_per_million_input_tokens",
        "pricing_usd_per_million_output_tokens",
    ):
        value = reviewer.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ScalePilotError(
                f"invalid independent_reviewer pricing/limit field: {field}"
            )
    if reviewer_model == "mistralai/mistral-small-2603":
        if reviewer.get("qualification") != "factual-qa-v3-reviewer-qualification-006":
            raise ScalePilotError("Mistral reviewer qualification drifted")
        expected_routing = {
            "order": ["Mistral"],
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": "allow",
            "zdr": False,
        }
    elif reviewer_model == "qwen/qwen3.7-plus":
        if reviewer.get("qualification") != "factual-qa-v3-reviewer-qualification-007":
            raise ScalePilotError("Qwen reviewer qualification identity drifted")
        _validate_qwen_qualification_result(reviewer)
        expected_routing = {
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": "allow",
            "zdr": False,
        }
    else:
        raise ScalePilotError("independent reviewer model is not qualified")
    if reviewer.get("provider_routing") != expected_routing:
        raise ScalePilotError("independent reviewer routing drifted")
    if any(
        name not in instrument.get("excluded_models", [])
        for name in ("gemma", "claude", "local-qwen")
    ):
        raise ScalePilotError("prohibited model exclusions drifted")
    return instrument


def _validate_qwen_qualification_result(binding: dict[str, Any]) -> None:
    record = binding.get("qualification_result")
    if not isinstance(record, dict):
        raise ScalePilotError("Qwen requires a registered passing qualification result")
    relative_path = record.get("path")
    expected_sha256 = record.get("sha256")
    if not isinstance(relative_path, str) or not isinstance(expected_sha256, str):
        raise ScalePilotError("Qwen qualification result binding is incomplete")
    path = ROOT / relative_path
    if not path.is_file() or _sha256_file(path) != expected_sha256:
        raise ScalePilotError("Qwen qualification result hash drifted")
    result = _load_json(path)
    if result.get("run_type") != "factual-qa-v3-reviewer-qualification-007":
        raise ScalePilotError("Qwen qualification result identity drifted")
    if result.get("status") != "completed":
        raise ScalePilotError("Qwen qualification result is not complete")
    if result.get("decision") != (
        "keep-qwen37plus-as-independent-reviewer-candidate-for-100-case-stage"
    ):
        raise ScalePilotError("Qwen qualification did not select the candidate")
    gates = result.get("gate_results")
    if not isinstance(gates, dict) or not gates or not all(gates.values()):
        raise ScalePilotError("Qwen qualification gates did not all pass")
    if result.get("failed_gates") != []:
        raise ScalePilotError("Qwen qualification records failed gates")


def load_assets(
    instrument_path: Path = INSTRUMENT_PATH,
) -> dict[str, Any]:
    instrument = validate_instrument(instrument_path)
    artifact = build_artifact()
    summary = artifact["summary"]
    design = instrument["blueprint_design"]
    if summary["content_sha256"] != design["content_sha256"]:
        raise ScalePilotError("10,000-case blueprint content hash drifted")
    if summary["source_count"] != design["source_count"]:
        raise ScalePilotError("source count drifted")
    if summary["claim_count"] != design["claim_count"]:
        raise ScalePilotError("claim count drifted")
    blueprints = [
        item
        for item in artifact["blueprints"]
        if item["checkpoint_stage"] == PILOT_STAGE
    ]
    if len(blueprints) != 100:
        raise ScalePilotError("pilot stage must contain exactly 100 cases")
    sources = artifact["sources"]
    source_map = {source["source_unit_id"]: source for source in sources}
    validate_pilot_cases(blueprints, source_map=source_map)
    return {
        "instrument": instrument,
        "instrument_path": instrument_path,
        "blueprint_artifact_sha256": summary["content_sha256"],
        "sources": sources,
        "source_map": source_map,
        "blueprints": blueprints,
    }


def validate_pilot_cases(
    blueprints: list[dict[str, Any]],
    *,
    source_map: dict[str, dict[str, Any]],
) -> None:
    if len(blueprints) != 100:
        raise ScalePilotError("pilot requires exactly 100 blueprints")
    ids = [item["blueprint_id"] for item in blueprints]
    if len(ids) != len(set(ids)):
        raise ScalePilotError("pilot blueprint IDs are not unique")
    course_counts = Counter(item["course_id"] for item in blueprints)
    if len(course_counts) != 20 or set(course_counts.values()) != {5}:
        raise ScalePilotError("pilot is not exactly stratified across 20 courses")
    expected_slices = {
        "academic-integrity": 5,
        "ambiguous": 5,
        "code": 8,
        "cross-course-confusion": 5,
        "diagram": 5,
        "direct-text": 20,
        "equation": 4,
        "multi-source": 15,
        "no-evidence": 5,
        "paraphrase-text": 15,
        "table": 8,
        "visual-other": 5,
    }
    if Counter(item["slice"] for item in blueprints) != Counter(expected_slices):
        raise ScalePilotError("pilot slice stratification drifted")
    claim_index = {
        claim["claim_id"]: (source_id, claim)
        for source_id, source in source_map.items()
        for claim in source["claims"]
    }
    for blueprint in blueprints:
        evidence_ids = blueprint["evidence_unit_ids"]
        distractor_ids = blueprint["distractor_unit_ids"]
        if not set((*evidence_ids, *distractor_ids)).issubset(source_map):
            raise ScalePilotError("pilot references an unknown source")
        if not set(blueprint["target_claim_ids"]).issubset(claim_index):
            raise ScalePilotError("pilot references an unknown claim")
        expected_sources = {
            claim_index[claim_id][0] for claim_id in blueprint["target_claim_ids"]
        }
        if set(evidence_ids) != expected_sources:
            raise ScalePilotError("pilot claim/source lineage drifted")
        if blueprint["slice"] == "multi-source" and len(set(evidence_ids)) != 2:
            raise ScalePilotError("pilot multi-source case is not genuinely multi-source")


def _binding_snapshot(instrument: dict[str, Any]) -> dict[str, Any]:
    return {
        role: {
            field: binding[field]
            for field in (
                "provider",
                "litellm_model",
                "provider_model",
                "max_input_tokens",
                "max_output_tokens",
                "pricing_usd_per_million_input_tokens",
                "pricing_usd_per_million_output_tokens",
                "revision_required",
            )
        }
        for role, binding in instrument["model_roles"].items()
    }


def _maximum_reserved_cost(instrument: dict[str, Any]) -> float:
    counts = {
        "author": 1 + instrument["execution"]["author_call_limit"],
        "independent_reviewer": (
            1
            + instrument["execution"]["independent_review_call_limit"]
            + instrument["execution"]["mutation_review_call_limit"]
        ),
        "dispute_reviewer": instrument["execution"]["dispute_review_call_limit"],
    }
    total = 0.0
    for role, count in counts.items():
        binding = instrument["model_roles"][role]
        total += count * (
            float(binding["max_input_tokens"])
            * float(binding["pricing_usd_per_million_input_tokens"])
            + float(binding["max_output_tokens"])
            * float(binding["pricing_usd_per_million_output_tokens"])
        ) / 1_000_000
    return total


def build_preflight(
    assets: dict[str, Any],
    *,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    instrument = assets["instrument"]
    execution = instrument["execution"]
    credential_names = {
        binding["credential_environment_variable"]
        for binding in instrument["model_roles"].values()
    }
    credentials = {
        name: bool(os.getenv(name, "").strip()) for name in sorted(credential_names)
    }
    reservation = _maximum_reserved_cost(instrument)
    authorized = execution["provider_execution_authorized"] is True
    frozen = instrument["status"] == "frozen-pending-execution"
    ready = (
        authorized
        and frozen
        and all(credentials.values())
        and not _working_tree_dirty()
        and not output_path.exists()
        and reservation <= execution["cost_stop_usd"]
    )
    if not authorized:
        status = "blocked-not-authorized"
    elif not frozen:
        status = "blocked-not-frozen"
    else:
        status = "ready" if ready else "blocked-preflight"
    return {
        "run_type": "factual-qa-v3-scale-pilot-100-preflight",
        "instrument_id": instrument["instrument_id"],
        "status": status,
        "code_revision": _code_revision(),
        "provider_execution_authorized": authorized,
        "instrument_frozen": frozen,
        "case_count": len(assets["blueprints"]),
        "working_tree_dirty": _working_tree_dirty(),
        "credentials_present": credentials,
        "credential_values_emitted": False,
        "output_available": not output_path.exists(),
        "maximum_provider_calls": execution["total_provider_call_limit"],
        "maximum_reserved_cost_usd": reservation,
        "cost_stop_usd": execution["cost_stop_usd"],
        "external_call_enabled": False,
        "private_data_read": False,
        "checkpoint_1000_authorized": False,
        "scale_10000_authorized": False,
    }


def _source_context(
    blueprint: dict[str, Any],
    *,
    source_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "approved_sources": [
            source_map[source_id] for source_id in blueprint["evidence_unit_ids"]
        ],
        "distractors": [
            source_map[source_id]
            for source_id in blueprint.get("distractor_unit_ids", [])
        ],
    }


def _author_prompt(
    blueprint: dict[str, Any],
    *,
    source_map: dict[str, dict[str, Any]],
) -> str:
    return json.dumps(
        {
            "blueprint": blueprint,
            "source_context": _source_context(blueprint, source_map=source_map),
            "requirements": {
                "answer": "use exactly target_claim_ids and exact evidence quotes",
                "boundary": "use expected action with empty claims and citations",
                "external_knowledge": "prohibited",
                "output_contract": {
                    "exact_top_level_keys": [
                        "question",
                        "answer",
                        "action",
                        "selected_claim_ids",
                        "citations",
                    ],
                    "citation_object_exact_keys": ["source_unit_id", "quote"],
                    "citation_rule": (
                        "citations must be objects, never strings; source_unit_id "
                        "must name an approved source and quote must copy the complete "
                        "target evidence_quote verbatim"
                    ),
                    "claim_rule": (
                        "selected_claim_ids must equal target_claim_ids exactly, with "
                        "no aliases, omissions, duplicates, or extra claims"
                    ),
                },
            },
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _review_prompt(
    blueprint: dict[str, Any],
    authored: dict[str, Any] | None,
    *,
    source_map: dict[str, dict[str, Any]],
) -> str:
    return _strict_review_prompt(
        blueprint,
        authored=authored,
        source_context=_source_context(blueprint, source_map=source_map),
    )


def validate_authored(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScalePilotError("authored response root must be an object")
    required = {"question", "answer", "action", "selected_claim_ids", "citations"}
    if set(value) != required:
        raise ScalePilotError("authored response keys do not exactly match contract")
    if not isinstance(value["question"], str) or not value["question"].strip():
        raise ScalePilotError("authored question is empty")
    if not isinstance(value["answer"], str) or not value["answer"].strip():
        raise ScalePilotError("authored answer is empty")
    if value["action"] not in {ANSWER_ACTION, *BOUNDARY_ACTIONS}:
        raise ScalePilotError("authored action is invalid")
    if not isinstance(value["selected_claim_ids"], list) or any(
        not isinstance(claim_id, str) or not claim_id.strip()
        for claim_id in value["selected_claim_ids"]
    ):
        raise ScalePilotError("authored selected_claim_ids must be a list")
    if len(value["selected_claim_ids"]) != len(set(value["selected_claim_ids"])):
        raise ScalePilotError("authored selected_claim_ids contain duplicates")
    if not isinstance(value["citations"], list):
        raise ScalePilotError("authored citations must be a list")
    for citation in value["citations"]:
        if not isinstance(citation, dict) or set(citation) != {
            "source_unit_id",
            "quote",
        }:
            raise ScalePilotError("authored citation shape is invalid")
        if any(
            not isinstance(citation[field], str) or not citation[field].strip()
            for field in ("source_unit_id", "quote")
        ):
            raise ScalePilotError("authored citation values are invalid")
    return value


def validate_review(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScalePilotError("review response root must be an object")
    return validate_shared_review(value)


def deterministic_record(
    blueprint: dict[str, Any],
    authored: dict[str, Any] | None,
    *,
    source_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not isinstance(authored, dict):
        return {"passed": False, "checks": {"author_completed": False}}
    claims = authored.get("selected_claim_ids")
    citations = authored.get("citations")
    checks: dict[str, bool] = {
        "author_completed": True,
        "nonempty_question": isinstance(authored.get("question"), str)
        and bool(authored["question"].strip()),
        "nonempty_answer": isinstance(authored.get("answer"), str)
        and bool(authored["answer"].strip()),
        "action_matches": authored.get("action") == blueprint["expected_action"],
        "claim_list": isinstance(claims, list),
        "citation_list": isinstance(citations, list),
    }
    if not checks["claim_list"] or not checks["citation_list"]:
        return {"passed": False, "checks": checks}
    claim_index = {
        claim["claim_id"]: (source_id, claim)
        for source_id in blueprint["evidence_unit_ids"]
        for claim in source_map[source_id]["claims"]
    }
    citations_valid = True
    citation_source_ids: list[str] = []
    for citation in citations:
        if not isinstance(citation, dict):
            citations_valid = False
            continue
        source_id = citation.get("source_unit_id")
        quote = citation.get("quote")
        source = source_map.get(source_id)
        if not isinstance(source_id, str) or not isinstance(quote, str) or source is None:
            citations_valid = False
            continue
        citation_source_ids.append(source_id)
        if " ".join(quote.split()) not in " ".join(source["source_truth"].split()):
            citations_valid = False
    checks["citation_quotes_and_sources_valid"] = citations_valid
    if blueprint["expected_action"] == ANSWER_ACTION:
        targets = blueprint["target_claim_ids"]
        checks["target_claims_exact"] = (
            len(claims) == len(set(claims)) and set(claims) == set(targets)
        )
        checks["evidence_sources_exact"] = set(citation_source_ids) == set(
            blueprint["evidence_unit_ids"]
        )
        checks["target_claim_citations_complete"] = all(
            claim_id in claim_index
            and any(
                citation.get("source_unit_id") == claim_index[claim_id][0]
                and " ".join(claim_index[claim_id][1]["evidence_quote"].split())
                in " ".join(str(citation.get("quote", "")).split())
                for citation in citations
                if isinstance(citation, dict)
            )
            for claim_id in targets
        )
    else:
        checks["boundary_has_no_claims"] = claims == []
        checks["boundary_has_no_citations"] = citations == []
    if blueprint["slice"] == "cross-course-confusion":
        checks["cross_course_not_cited"] = not set(
            blueprint["distractor_unit_ids"]
        ).intersection(citation_source_ids)
    return {"passed": all(checks.values()), "checks": checks}


def _mutation_sequence() -> list[str]:
    return [
        mutation
        for mutation, count in EXPECTED_MUTATIONS.items()
        for _ in range(count)
    ]


def canonical_authored_case(
    blueprint: dict[str, Any],
    *,
    source_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a deterministic valid control without depending on model output."""
    if blueprint["expected_action"] != ANSWER_ACTION:
        return {
            "question": f"Boundary control for {blueprint['blueprint_id']}?",
            "answer": f"The required safe action is {blueprint['expected_action']}.",
            "action": blueprint["expected_action"],
            "selected_claim_ids": [],
            "citations": [],
        }
    claim_index = {
        claim["claim_id"]: (source_id, claim)
        for source_id in blueprint["evidence_unit_ids"]
        for claim in source_map[source_id]["claims"]
    }
    citations = [
        {
            "source_unit_id": claim_index[claim_id][0],
            "quote": claim_index[claim_id][1]["evidence_quote"],
        }
        for claim_id in blueprint["target_claim_ids"]
    ]
    return {
        "question": f"Canonical question for {blueprint['blueprint_id']}?",
        "answer": " ".join(
            claim_index[claim_id][1]["text"]
            for claim_id in blueprint["target_claim_ids"]
        ),
        "action": ANSWER_ACTION,
        "selected_claim_ids": list(blueprint["target_claim_ids"]),
        "citations": citations,
    }


def build_mutations(
    blueprints: list[dict[str, Any]],
    *,
    blueprints_by_id: dict[str, dict[str, Any]],
    source_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    eligible = [
        blueprint
        for blueprint in blueprints
        if blueprint["expected_action"] == ANSWER_ACTION
    ]
    selected: list[dict[str, Any]] = []
    remaining = list(eligible)
    while remaining and len(selected) < 20:
        seen = {item["slice"] for item in selected}
        choice = next(
            (item for item in remaining if item["slice"] not in seen), remaining[0]
        )
        selected.append(choice)
        remaining.remove(choice)
    mutations: list[dict[str, Any]] = []
    if len(selected) != 20:
        raise ScalePilotError("insufficient answerable blueprints for mutations")
    for blueprint, mutation_type in zip(selected, _mutation_sequence(), strict=True):
        if blueprints_by_id[blueprint["blueprint_id"]] != blueprint:
            raise ScalePilotError("mutation blueprint lookup drifted")
        control = canonical_authored_case(blueprint, source_map=source_map)
        if not deterministic_record(blueprint, control, source_map=source_map)["passed"]:
            raise ScalePilotError("canonical mutation control is invalid")
        mutated = deepcopy(control)
        if mutation_type == "missing-citation":
            mutated["citations"] = []
        elif mutation_type == "truncated-citation":
            quote = str(mutated["citations"][0]["quote"])
            mutated["citations"][0]["quote"] = quote.rsplit(" ", 1)[0]
        elif mutation_type == "paraphrased-citation":
            mutated["citations"][0]["quote"] = "Semantically equivalent paraphrase."
        elif mutation_type == "extra-supported-claim":
            target_ids = set(blueprint["target_claim_ids"])
            source_id, claim = next(
                (source_id, claim)
                for source_id in blueprint["evidence_unit_ids"]
                for claim in source_map[source_id]["claims"]
                if claim["claim_id"] not in target_ids
            )
            mutated["selected_claim_ids"].append(claim["claim_id"])
            mutated["citations"].append(
                {"source_unit_id": source_id, "quote": claim["evidence_quote"]}
            )
        elif mutation_type == "invalid-claim-binding":
            mutated["selected_claim_ids"][0] = "invalid-claim-id"
        elif mutation_type == "invalid-source-binding":
            mutated["citations"][0]["source_unit_id"] = "invalid-source-id"
        else:
            raise AssertionError("unknown mutation type")
        deterministic = deterministic_record(
            blueprint, mutated, source_map=source_map
        )
        if deterministic["passed"]:
            raise ScalePilotError("mutation failed to create a deterministic defect")
        mutations.append(
            {
                "blueprint_id": blueprint["blueprint_id"],
                "slice": blueprint["slice"],
                "mutation_type": mutation_type,
                "control_case": control,
                "mutated_case": mutated,
                "deterministic": deterministic,
                "review_outcome": None,
            }
        )
    return mutations


class ProviderTransport:
    """Raw, identity-pinned transport used only after external authorization."""

    def __init__(self, binding: dict[str, Any]) -> None:
        self.binding = binding
        provider_options: dict[str, Any] = {}
        if binding["provider"] == "openrouter":
            provider_options = {
                "extra_body": {"provider": deepcopy(binding["provider_routing"])}
            }
        elif binding["provider"] == "deepseek-official-api":
            provider_options = {
                "extra_body": {"thinking": {"type": binding["thinking"]}}
            }
        self.client = LiteLlmClient(
            binding["litellm_model"],
            timeout_seconds=binding["timeout_seconds"],
            max_output_tokens=binding["max_output_tokens"],
            temperature=binding["temperature"],
            response_format={"type": "json_object"},
            provider_options=provider_options,
            expected_provider_model=binding["provider_model"],
        )

    async def call(
        self,
        *,
        system: str,
        prompt: str,
        task: str,
        schema: dict[str, Any],
    ) -> RawCall:
        request = "\n".join(
            (prompt, "OUTPUT JSON SCHEMA:", json.dumps(schema, sort_keys=True))
        )
        started = time.perf_counter()
        response = await self.client.chat(
            [
                LlmMessage(role="system", content=system),
                LlmMessage(role="user", content=request),
            ],
            task=task,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        usage = response.usage
        cost = (
            usage.input_tokens
            * float(self.binding["pricing_usd_per_million_input_tokens"])
            + usage.output_tokens
            * float(self.binding["pricing_usd_per_million_output_tokens"])
        ) / 1_000_000
        return RawCall(
            content=response.content,
            provider_model=response.provider_model,
            provider_revision=response.provider_revision,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            approximate_cost_usd=cost,
            latency_ms=latency_ms,
        )


class SimulatedTransport:
    """Network-free deterministic provider double for full pipeline rehearsal."""

    def __init__(
        self,
        *,
        role: str,
        model: str,
        fail_tasks: set[str] | None = None,
        malformed_tasks: set[str] | None = None,
        invert_review_tasks: set[str] | None = None,
        cost_per_call: float = 0.0001,
        input_tokens: int = 100,
        output_tokens: int = 50,
    ) -> None:
        self.role = role
        self.model = model
        self.fail_tasks = fail_tasks or set()
        self.malformed_tasks = malformed_tasks or set()
        self.invert_review_tasks = invert_review_tasks or set()
        self.cost_per_call = cost_per_call
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls = 0

    async def call(
        self,
        *,
        system: str,
        prompt: str,
        task: str,
        schema: dict[str, Any],
    ) -> RawCall:
        del system, schema
        self.calls += 1
        if task in self.fail_tasks:
            raise RuntimeError("simulated provider failure")
        if task in self.malformed_tasks:
            content = "not-json"
        elif task.endswith("health"):
            content = json.dumps({"status": "ok"})
        elif task.endswith("author"):
            payload = json.loads(prompt)
            blueprint = payload["blueprint"]
            context = payload["source_context"]
            source_map = {
                source["source_unit_id"]: source
                for source in (
                    *context["approved_sources"],
                    *context["distractors"],
                )
            }
            if blueprint["expected_action"] == ANSWER_ACTION:
                claim_index = {
                    claim["claim_id"]: (source_id, claim)
                    for source_id in blueprint["evidence_unit_ids"]
                    for claim in source_map[source_id]["claims"]
                }
                citations = [
                    {
                        "source_unit_id": claim_index[claim_id][0],
                        "quote": claim_index[claim_id][1]["evidence_quote"],
                    }
                    for claim_id in blueprint["target_claim_ids"]
                ]
                value = {
                    "question": f"Synthetic question {blueprint['blueprint_id']}?",
                    "answer": " ".join(
                        claim_index[claim_id][1]["text"]
                        for claim_id in blueprint["target_claim_ids"]
                    ),
                    "action": ANSWER_ACTION,
                    "selected_claim_ids": blueprint["target_claim_ids"],
                    "citations": citations,
                }
            else:
                value = {
                    "question": f"Synthetic boundary {blueprint['blueprint_id']}?",
                    "answer": f"The safe action is {blueprint['expected_action']}.",
                    "action": blueprint["expected_action"],
                    "selected_claim_ids": [],
                    "citations": [],
                }
            content = json.dumps(value)
        else:
            payload = json.loads(prompt)
            context = payload.get("source_context")
            if context is None:
                context = {
                    "approved_sources": payload[
                        "approved_target_course_sources"
                    ],
                    "distractors": payload[
                        "unapproved_other_course_distractors"
                    ],
                }
            source_map = {
                source["source_unit_id"]: source
                for source in (
                    *context["approved_sources"],
                    *context["distractors"],
                )
            }
            deterministic = deterministic_record(
                payload["blueprint"],
                payload["authored_case"],
                source_map=source_map,
            )
            passed = deterministic["passed"]
            value = {
                "verdict": "accept" if passed else "reject",
                "question_matches_blueprint": passed,
                "answer_or_action_correct": passed,
                "fully_supported": passed,
                "citation_lineage_correct": passed,
                "no_external_knowledge": True,
                "course_boundary_respected": passed,
                "failure_categories": [] if passed else ["deterministic-defect"],
                "rationale": "Deterministic simulation review.",
            }
            if task in self.invert_review_tasks:
                inverted = not passed
                value.update(
                    {
                        "verdict": "accept" if inverted else "reject",
                        "question_matches_blueprint": inverted,
                        "answer_or_action_correct": inverted,
                        "fully_supported": inverted,
                        "citation_lineage_correct": inverted,
                        "course_boundary_respected": inverted,
                        "failure_categories": (
                            [] if inverted else ["simulated-reviewer-disagreement"]
                        ),
                    }
                )
            content = json.dumps(value)
        return RawCall(
            content=content,
            provider_model=self.model,
            provider_revision=f"simulated-{self.model}-revision",
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            approximate_cost_usd=self.cost_per_call,
            latency_ms=1.0,
        )


def _write_initial(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as error:
        raise ScalePilotError(f"refusing to overwrite existing output: {path}") from error


def _checkpoint(path: Path, state: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise ScalePilotError("stale checkpoint temporary exists")
    temporary.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _state_bindings(assets: dict[str, Any]) -> dict[str, Any]:
    instrument = assets["instrument"]
    return {
        "instrument_sha256": _sha256_file(assets["instrument_path"]),
        "blueprint_artifact_sha256": assets["blueprint_artifact_sha256"],
        "code_revision": _code_revision(),
        "runner_sha256": _sha256_file(Path(__file__)),
        "model_and_pricing_sha256": _canonical_sha256(
            _binding_snapshot(instrument)
        ),
    }


def _initial_state(assets: dict[str, Any], *, simulation: bool) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_type": assets["instrument"]["instrument_id"],
        "status": "running",
        "simulation": simulation,
        "bindings": _state_bindings(assets),
        "data_boundary": assets["instrument"]["data_boundary"],
        "private_data_read": False,
        "private_data_emitted": False,
        "checkpoint_1000_authorized": False,
        "scale_10000_authorized": False,
        "maximum_reserved_cost_usd": _maximum_reserved_cost(
            assets["instrument"]
        ),
        "accounting": {
            "calls_attempted": 0,
            "calls_with_provider_response": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "external_cost_usd": 0.0,
            "input_token_limit_exceeded_count": 0,
            "output_token_limit_exceeded_count": 0,
            "token_limit_exceeded_call_count": 0,
            "latency_ms": [],
        },
        "canaries": {},
        "results": [],
        "mutations": [],
    }


def _load_resume(path: Path, assets: dict[str, Any], *, simulation: bool) -> dict[str, Any]:
    state = _load_json(path)
    if state.get("status") != "running":
        raise ScalePilotError("only a running checkpoint may be resumed")
    if state.get("simulation") is not simulation:
        raise ScalePilotError("simulation/external resume mode drifted")
    if state.get("bindings") != _state_bindings(assets):
        raise ScalePilotError("resume bindings drifted")
    if state.get("run_type") != assets["instrument"]["instrument_id"]:
        raise ScalePilotError("resume run identity drifted")
    return state


def _call_record(raw: RawCall, binding: dict[str, Any]) -> dict[str, Any]:
    input_limit = int(binding["max_input_tokens"])
    output_limit = int(binding["max_output_tokens"])
    return {
        "provider_model": raw.provider_model,
        "provider_revision": raw.provider_revision,
        "input_tokens": raw.input_tokens,
        "output_tokens": raw.output_tokens,
        "requested_max_input_tokens": input_limit,
        "requested_max_output_tokens": output_limit,
        "input_token_limit_exceeded": raw.input_tokens > input_limit,
        "output_token_limit_exceeded": raw.output_tokens > output_limit,
        "approximate_cost_usd": raw.approximate_cost_usd,
        "latency_ms": raw.latency_ms,
    }


def _record_raw_call(
    state: dict[str, Any], raw: RawCall, binding: dict[str, Any]
) -> None:
    accounting = state["accounting"]
    accounting["calls_with_provider_response"] += 1
    accounting["input_tokens"] += raw.input_tokens
    accounting["output_tokens"] += raw.output_tokens
    accounting["external_cost_usd"] += raw.approximate_cost_usd
    input_exceeded = raw.input_tokens > int(binding["max_input_tokens"])
    output_exceeded = raw.output_tokens > int(binding["max_output_tokens"])
    accounting["input_token_limit_exceeded_count"] += int(input_exceeded)
    accounting["output_token_limit_exceeded_count"] += int(output_exceeded)
    accounting["token_limit_exceeded_call_count"] += int(
        input_exceeded or output_exceeded
    )
    accounting["latency_ms"].append(raw.latency_ms)


async def _safe_call(
    *,
    role: str,
    transport: RawTransport,
    system: str,
    prompt: str,
    task: str,
    schema: dict[str, Any],
    validator: Any,
    state: dict[str, Any],
    instrument: dict[str, Any],
    output_path: Path,
    stop_after_calls: int | None,
) -> dict[str, Any]:
    accounting = state["accounting"]
    cost_stop = float(instrument["execution"]["cost_stop_usd"])
    if accounting["external_cost_usd"] >= cost_stop:
        state["status"] = "invalid-execution"
        state["invalid_reason"] = "cost-stop-reached-before-call"
        _checkpoint(output_path, state)
        return {
            "status": "budget-stop",
            "error_type": None,
            "provider_response_received": False,
            "latency_ms": 0.0,
            "value": None,
            "call": None,
        }
    if accounting["calls_attempted"] >= instrument["execution"]["total_provider_call_limit"]:
        raise ScalePilotError("provider call limit reached")
    if stop_after_calls is not None and accounting["calls_attempted"] >= stop_after_calls:
        _checkpoint(output_path, state)
        raise PlannedInterruption("planned interruption after durable checkpoint")
    accounting["calls_attempted"] += 1
    started = time.perf_counter()
    try:
        raw = await transport.call(
            system=system,
            prompt=prompt,
            task=task,
            schema=schema,
        )
    except Exception as error:
        outcome = {
            "status": "provider-error",
            "error_type": type(error).__name__,
            "provider_response_received": False,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "value": None,
            "call": None,
        }
        return outcome
    binding = instrument["model_roles"][role]
    _record_raw_call(state, raw, binding)
    expected_model = binding["provider_model"]
    if raw.provider_model != expected_model:
        state["status"] = "invalid-execution"
        state["invalid_reason"] = "provider-model-identity-drift"
    if state["accounting"]["external_cost_usd"] >= cost_stop:
        state["status"] = "invalid-execution"
        state["invalid_reason"] = "cost-stop-exceeded"
    try:
        parsed = json.loads(raw.content)
        value = validator(parsed)
        outcome = {
            "status": "complete",
            "error_type": None,
            "provider_response_received": True,
            "value": value,
            "call": _call_record(raw, binding),
        }
    except (json.JSONDecodeError, ScalePilotError, TypeError, ValueError) as error:
        outcome = {
            "status": "malformed-response",
            "error_type": type(error).__name__,
            "provider_response_received": True,
            "content_sha256": hashlib.sha256(raw.content.encode()).hexdigest(),
            "value": None,
            "call": _call_record(raw, binding),
        }
    return outcome


def _health_validator(value: Any) -> dict[str, Any]:
    if value != {"status": "ok"}:
        raise ScalePilotError("provider health response is not exactly ok")
    return value


def _expected_verdict(record: dict[str, Any]) -> str:
    return "accept" if record["deterministic"]["passed"] else "reject"


def _model_identity_stable(state: dict[str, Any], instrument: dict[str, Any]) -> bool:
    by_role: dict[str, list[dict[str, Any]]] = {role: [] for role in ROLE_NAMES}
    for outcome in state["canaries"].values():
        if outcome.get("call"):
            by_role[outcome["role"]].append(outcome["call"])
    for result in state["results"]:
        for field, role in (
            ("author_outcome", "author"),
            ("review_outcome", "independent_reviewer"),
            ("dispute_outcome", "dispute_reviewer"),
        ):
            outcome = result.get(field)
            if outcome and outcome.get("call"):
                by_role[role].append(outcome["call"])
    for mutation in state["mutations"]:
        outcome = mutation.get("review_outcome")
        if outcome and outcome.get("call"):
            by_role["independent_reviewer"].append(outcome["call"])
    for role, calls in by_role.items():
        binding = instrument["model_roles"][role]
        if role == "dispute_reviewer" and not calls:
            continue
        if not calls or any(call["provider_model"] != binding["provider_model"] for call in calls):
            return False
        revisions = {
            call["provider_revision"]
            for call in calls
            if call["provider_revision"] not in {None, ""}
        }
        if binding["revision_required"] and (
            len(revisions) != 1
            or any(call["provider_revision"] in {None, ""} for call in calls)
        ):
            return False
        if len(revisions) > 1:
            return False
    return True


def _normalize_question(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value).casefold()))


def _percentile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(probability * len(ordered)) - 1)]


def analyze_state(state: dict[str, Any], instrument: dict[str, Any]) -> dict[str, Any]:
    results = state["results"]
    mutations = state["mutations"]
    completed_authors = [
        item for item in results if item["author_outcome"]["status"] == "complete"
    ]
    deterministic_passes = [item for item in results if item["deterministic"]["passed"]]
    answerable = [item for item in results if item["expected_action"] == ANSWER_ACTION]
    boundary = [item for item in results if item["expected_action"] in BOUNDARY_ACTIONS]
    completed_reviews = [
        item for item in results if item.get("review_outcome", {}).get("status") == "complete"
    ]
    agreements = [
        item
        for item in completed_reviews
        if item["review_outcome"]["value"]["verdict"] == _expected_verdict(item)
    ]
    disagreements = [item for item in results if item not in agreements]
    unresolved = [
        item
        for item in disagreements
        if (item.get("dispute_outcome") or {}).get("status") != "complete"
        or item["dispute_outcome"]["value"]["verdict"] != _expected_verdict(item)
    ]
    mutation_completed = [
        item for item in mutations if item.get("review_outcome", {}).get("status") == "complete"
    ]
    mutation_rejects = [
        item for item in mutation_completed if item["review_outcome"]["value"]["verdict"] == "reject"
    ]
    all_outcomes = [
        *state["canaries"].values(),
        *(item["author_outcome"] for item in results),
        *(item.get("review_outcome") for item in results if item.get("review_outcome")),
        *(item.get("dispute_outcome") for item in results if item.get("dispute_outcome")),
        *(item.get("review_outcome") for item in mutations if item.get("review_outcome")),
    ]
    bulk_outcomes = [
        *(item["author_outcome"] for item in results),
        *(item.get("review_outcome") for item in results if item.get("review_outcome")),
        *(item.get("dispute_outcome") for item in results if item.get("dispute_outcome")),
        *(item.get("review_outcome") for item in mutations if item.get("review_outcome")),
    ]
    malformed = [
        outcome for outcome in bulk_outcomes if outcome["status"] == "malformed-response"
    ]
    provider_completed = [
        outcome for outcome in bulk_outcomes if outcome["provider_response_received"]
    ]
    citation_valid = [
        item
        for item in answerable
        if item["deterministic"]["checks"].get("citation_quotes_and_sources_valid")
    ]
    claim_complete = [
        item
        for item in answerable
        if item["deterministic"]["checks"].get("target_claim_citations_complete")
        and item["deterministic"]["checks"].get("target_claims_exact")
    ]
    boundary_correct = [
        item
        for item in boundary
        if item["authored_case"] is not None
        and item["authored_case"].get("action") == item["expected_action"]
    ]
    questions = [
        _normalize_question(item["authored_case"].get("question"))
        for item in completed_authors
    ]
    duplicate_count = len(questions) - len(set(questions))
    accounting = state["accounting"]
    metrics = {
        "provider_response_completion_rate": (
            len(provider_completed) / len(bulk_outcomes) if bulk_outcomes else 0.0
        ),
        "deterministic_acceptance_rate": len(deterministic_passes) / 100,
        "reviewer_agreement_rate": len(agreements) / 100,
        "citation_validity_rate": len(citation_valid) / len(answerable),
        "target_claim_completeness_rate": len(claim_complete) / len(answerable),
        "boundary_action_accuracy": len(boundary_correct) / len(boundary),
        "exact_duplicate_question_rate": duplicate_count / 100,
        "unresolved_dispute_rate": len(unresolved) / 100,
        "malformed_response_rate": (
            len(malformed) / len(bulk_outcomes) if bulk_outcomes else 0.0
        ),
        "mutation_sensitivity": len(mutation_rejects) / 20,
        "model_identity_stable": _model_identity_stable(state, instrument),
        "cost_and_latency_accounting_complete": all(
            outcome.get("call") is not None
            or outcome["status"] == "provider-error"
            for outcome in all_outcomes
        ),
        "external_cost_usd": accounting["external_cost_usd"],
        "input_token_limit_exceeded_count": accounting[
            "input_token_limit_exceeded_count"
        ],
        "output_token_limit_exceeded_count": accounting[
            "output_token_limit_exceeded_count"
        ],
        "token_limit_exceeded_call_count": accounting[
            "token_limit_exceeded_call_count"
        ],
        "private_data_calls": 0,
        "provider_calls": accounting["calls_attempted"],
        "p95_latency_ms": _percentile(accounting["latency_ms"], 0.95),
    }
    gates = instrument["quality_gates"]
    gate_results = {
        "provider_response_completion_rate": metrics["provider_response_completion_rate"]
        >= gates["provider_response_completion_rate_min"],
        "deterministic_acceptance_rate": metrics["deterministic_acceptance_rate"]
        >= gates["deterministic_acceptance_rate_min"],
        "reviewer_agreement_rate": metrics["reviewer_agreement_rate"]
        >= gates["reviewer_agreement_rate_min"],
        "citation_validity_rate": metrics["citation_validity_rate"]
        >= gates["citation_validity_rate_min"],
        "target_claim_completeness_rate": metrics["target_claim_completeness_rate"]
        >= gates["target_claim_completeness_rate_min"],
        "boundary_action_accuracy": metrics["boundary_action_accuracy"]
        >= gates["boundary_action_accuracy_min"],
        "exact_duplicate_question_rate": metrics["exact_duplicate_question_rate"]
        <= gates["exact_duplicate_question_rate_max"],
        "unresolved_dispute_rate": metrics["unresolved_dispute_rate"]
        <= gates["unresolved_dispute_rate_max"],
        "malformed_response_rate": metrics["malformed_response_rate"]
        <= gates["malformed_response_rate_max"],
        "mutation_sensitivity": metrics["mutation_sensitivity"]
        >= gates["mutation_sensitivity_min"],
        "model_identity_stable": metrics["model_identity_stable"]
        is gates["model_identity_stable_required"],
        "cost_and_latency_accounting_complete": metrics[
            "cost_and_latency_accounting_complete"
        ]
        is gates["cost_and_latency_accounting_complete_required"],
        "external_cost_usd": metrics["external_cost_usd"]
        <= gates["external_cost_usd_max"],
        "private_data_calls": metrics["private_data_calls"]
        <= gates["private_data_calls_max"],
        "provider_calls": metrics["provider_calls"]
        <= instrument["execution"]["total_provider_call_limit"],
    }
    slice_metrics = {
        slice_name: {
            "count": len(items),
            "deterministic_acceptance_rate": sum(
                item["deterministic"]["passed"] for item in items
            )
            / len(items),
            "reviewer_agreement_rate": sum(
                item.get("review_outcome", {}).get("status") == "complete"
                and item["review_outcome"]["value"]["verdict"]
                == _expected_verdict(item)
                for item in items
            )
            / len(items),
        }
        for slice_name in sorted({item["slice"] for item in results})
        if (items := [item for item in results if item["slice"] == slice_name])
    }
    keep = all(gate_results.values())
    return {
        "status": "completed-keep" if keep else "completed-refine",
        "decision": "keep-method" if keep else "refine-method",
        "machine_gates_passed": keep,
        "metrics": metrics,
        "gate_results": gate_results,
        "failed_gates": sorted(name for name, passed in gate_results.items() if not passed),
        "slice_metrics": slice_metrics,
        "checkpoint_1000_authorized": False,
        "scale_10000_authorized": False,
    }


def _priority_packet(state: dict[str, Any], *, maximum: int) -> list[dict[str, Any]]:
    def priority(item: dict[str, Any]) -> tuple[bool, bool, str, str]:
        review = item.get("review_outcome")
        agreement = (
            review is not None
            and review["status"] == "complete"
            and review["value"]["verdict"] == _expected_verdict(item)
        )
        return (
            item["deterministic"]["passed"],
            agreement,
            item["slice"],
            item["blueprint_id"],
        )

    selected = sorted(state["results"], key=priority)[:maximum]
    return [
        {
            "blueprint_id": item["blueprint_id"],
            "slice": item["slice"],
            "authored_case": item["authored_case"],
            "deterministic": item["deterministic"],
            "independent_review": item.get("review_outcome"),
            "dispute_review": item.get("dispute_outcome"),
            "requested_checks": [
                "question_clarity",
                "answer_or_action_correctness",
                "complete_claim_support",
                "citation_lineage",
            ],
        }
        for item in selected
    ]


async def execute(
    assets: dict[str, Any],
    *,
    transports: dict[str, RawTransport],
    output_path: Path,
    simulation: bool,
    resume: bool = False,
    stop_after_calls: int | None = None,
) -> dict[str, Any]:
    instrument = assets["instrument"]
    reservation = _maximum_reserved_cost(instrument)
    if reservation > instrument["execution"]["cost_stop_usd"]:
        raise ScalePilotError("maximum cost reservation exceeds the hard stop")
    if resume:
        state = _load_resume(output_path, assets, simulation=simulation)
    else:
        state = _initial_state(assets, simulation=simulation)
        _write_initial(output_path, state)
    source_map = assets["source_map"]
    blueprints = assets["blueprints"]
    blueprints_by_id = {item["blueprint_id"]: item for item in blueprints}
    health_system = "Return the exact requested synthetic-public health JSON."
    for role in ("author", "independent_reviewer"):
        if role in state["canaries"]:
            continue
        outcome = await _safe_call(
            role=role,
            transport=transports[role],
            system=health_system,
            prompt='Return {"status":"ok"}.',
            task=f"factual_qa_v3_pilot_100_{role}_health",
            schema=HEALTH_SCHEMA,
            validator=_health_validator,
            state=state,
            instrument=instrument,
            output_path=output_path,
            stop_after_calls=stop_after_calls,
        )
        state["canaries"][role] = {"role": role, **outcome}
        _checkpoint(output_path, state)
        if outcome["status"] != "complete" or state["status"] == "invalid-execution":
            if state["status"] != "invalid-execution":
                state["status"] = "invalid-execution"
                state["invalid_reason"] = "provider-canary-failed"
            _checkpoint(output_path, state)
            return state

    author_system = (
        "Author one exact source-grounded synthetic factual-QA case. Return one "
        "JSON object only, with exactly these top-level keys: question, answer, "
        "action, selected_claim_ids, citations. Every citation must be an object "
        "with exactly source_unit_id and quote. Never return citation strings, "
        "claim_id citation keys, evidence_quote citation keys, Markdown, or prose "
        "outside the JSON object."
    )
    for blueprint in blueprints[len(state["results"]):]:
        outcome = await _safe_call(
            role="author",
            transport=transports["author"],
            system=author_system,
            prompt=_author_prompt(blueprint, source_map=source_map),
            task="factual_qa_v3_pilot_100_author",
            schema=AUTHOR_SCHEMA,
            validator=validate_authored,
            state=state,
            instrument=instrument,
            output_path=output_path,
            stop_after_calls=stop_after_calls,
        )
        authored = outcome["value"] if outcome["status"] == "complete" else None
        state["results"].append(
            {
                "blueprint_id": blueprint["blueprint_id"],
                "slice": blueprint["slice"],
                "course_id": blueprint["course_id"],
                "expected_action": blueprint["expected_action"],
                "authored_case": authored,
                "deterministic": deterministic_record(
                    blueprint, authored, source_map=source_map
                ),
                "author_outcome": outcome,
                "review_outcome": None,
                "dispute_outcome": None,
            }
        )
        _checkpoint(output_path, state)
        if state["status"] == "invalid-execution":
            return state

    review_system = _strict_review_system_prompt()
    for result in state["results"]:
        if result["review_outcome"] is not None:
            continue
        blueprint = blueprints_by_id[result["blueprint_id"]]
        result["review_outcome"] = await _safe_call(
            role="independent_reviewer",
            transport=transports["independent_reviewer"],
            system=review_system,
            prompt=_review_prompt(
                blueprint, result["authored_case"], source_map=source_map
            ),
            task="factual_qa_v3_pilot_100_independent_review",
            schema=REVIEW_SCHEMA,
            validator=validate_review,
            state=state,
            instrument=instrument,
            output_path=output_path,
            stop_after_calls=stop_after_calls,
        )
        _checkpoint(output_path, state)
        if state["status"] == "invalid-execution":
            return state

    if not state["mutations"]:
        state["mutations"] = build_mutations(
            blueprints,
            blueprints_by_id=blueprints_by_id,
            source_map=source_map,
        )
        _checkpoint(output_path, state)
    for mutation in state["mutations"]:
        if mutation["review_outcome"] is not None:
            continue
        blueprint = blueprints_by_id[mutation["blueprint_id"]]
        mutation["review_outcome"] = await _safe_call(
            role="independent_reviewer",
            transport=transports["independent_reviewer"],
            system=review_system,
            prompt=_review_prompt(
                blueprint, mutation["mutated_case"], source_map=source_map
            ),
            task="factual_qa_v3_pilot_100_mutation_review",
            schema=REVIEW_SCHEMA,
            validator=validate_review,
            state=state,
            instrument=instrument,
            output_path=output_path,
            stop_after_calls=stop_after_calls,
        )
        _checkpoint(output_path, state)
        if state["status"] == "invalid-execution":
            return state

    disagreements = [
        item
        for item in state["results"]
        if item["review_outcome"]["status"] != "complete"
        or item["review_outcome"]["value"]["verdict"] != _expected_verdict(item)
    ][: instrument["execution"]["dispute_review_call_limit"]]
    for result in disagreements:
        if result["dispute_outcome"] is not None:
            continue
        blueprint = blueprints_by_id[result["blueprint_id"]]
        result["dispute_outcome"] = await _safe_call(
            role="dispute_reviewer",
            transport=transports["dispute_reviewer"],
            system=review_system,
            prompt=_review_prompt(
                blueprint, result["authored_case"], source_map=source_map
            ),
            task="factual_qa_v3_pilot_100_dispute_review",
            schema=REVIEW_SCHEMA,
            validator=validate_review,
            state=state,
            instrument=instrument,
            output_path=output_path,
            stop_after_calls=stop_after_calls,
        )
        _checkpoint(output_path, state)
        if state["status"] == "invalid-execution":
            return state

    summary = analyze_state(state, instrument)
    state["summary"] = summary
    state["human_priority_packet"] = _priority_packet(
        state, maximum=instrument["quality_gates"]["human_priority_packet_max"]
    )
    state["status"] = summary["status"]
    _checkpoint(output_path, state)
    return state


def _simulation_transports(instrument: dict[str, Any]) -> dict[str, RawTransport]:
    return {
        role: SimulatedTransport(
            role=role,
            model=binding["provider_model"],
        )
        for role, binding in instrument["model_roles"].items()
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=INSTRUMENT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if sum((arguments.validate, arguments.simulate, arguments.execute)) > 1:
        parser.error("choose at most one of --validate, --simulate, or --execute")
    if arguments.resume and not (arguments.simulate or arguments.execute):
        parser.error("--resume requires --simulate or --execute")
    return arguments


def main() -> int:
    arguments = _arguments()
    load_dotenv(ROOT / ".env", override=False)
    instrument_path = (
        arguments.instrument
        if arguments.instrument.is_absolute()
        else ROOT / arguments.instrument
    )
    output_path = (
        arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
    )
    assets = load_assets(instrument_path)
    if arguments.validate:
        print(
            json.dumps(
                {
                    "status": "passed",
                    "instrument_id": INSTRUMENT_ID,
                    "case_count": 100,
                    "maximum_reserved_cost_usd": _maximum_reserved_cost(
                        assets["instrument"]
                    ),
                    "provider_called": False,
                    "private_data_read": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if arguments.simulate:
        state = asyncio.run(
            execute(
                assets,
                transports=_simulation_transports(assets["instrument"]),
                output_path=output_path,
                simulation=True,
                resume=arguments.resume,
            )
        )
        print(
            json.dumps(
                {
                    "status": state["status"],
                    "simulation": True,
                    "summary": state.get("summary"),
                    "provider_called": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    preflight = build_preflight(assets, output_path=output_path)
    if not arguments.execute:
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return 0
    require_bounded_pilot_operation_allowed(assets["instrument"]["instrument_id"])
    if preflight["status"] != "ready":
        raise ScalePilotError("paid pilot preflight is not ready")
    transports: dict[str, RawTransport] = {
        role: ProviderTransport(binding)
        for role, binding in assets["instrument"]["model_roles"].items()
    }
    state = asyncio.run(
        execute(
            assets,
            transports=transports,
            output_path=output_path,
            simulation=False,
            resume=arguments.resume,
        )
    )
    print(json.dumps({"status": state["status"], "summary": state.get("summary")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
