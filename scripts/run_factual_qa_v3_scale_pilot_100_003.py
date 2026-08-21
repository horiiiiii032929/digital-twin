#!/usr/bin/env python3
"""Validate, simulate, or execute deterministic factual-QA pilot 003."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_factual_qa_v3_10000_truth_packages import (
    build_artifact as build_truth_artifact,
    near_duplicate_signature,
    normalize_question,
)
from scripts.run_factual_qa_v3_scale_pilot_100 import (
    HEALTH_SCHEMA,
    REVIEW_SCHEMA,
    PlannedInterruption,
    ProviderTransport,
    RawCall,
    RawTransport,
    ScalePilotError,
    SimulatedTransport,
    _binding_snapshot,
    _canonical_sha256,
    _checkpoint,
    _code_revision,
    _health_validator,
    _maximum_reserved_cost,
    _priority_packet,
    _review_prompt,
    _safe_call,
    _sha256_file,
    _strict_review_system_prompt,
    _working_tree_dirty,
    _write_initial,
    analyze_state,
    build_mutations,
    deterministic_record,
    validate_review,
)
from scripts.validate_factual_qa_provider_freshness import (
    compare_live_metadata,
    fetch_live_provider_metadata,
    load_instrument as load_freshness_instrument,
    snapshot_age_hours,
)
from src.digital_twin.model_policy import require_registered_current_model
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/factual_qa_v3_scale_pilot_100_003.json"
)
DEFAULT_OUTPUT = ROOT / "reports/generated/factual-qa-v3-scale-pilot-100-003.json"
INSTRUMENT_ID = "factual-qa-v3-scale-pilot-100-003"
TRUTH_INSTRUMENT_ID = "factual-qa-v3-10000-pipeline-002"
PILOT_STAGE = "pilot-100"
EXPECTED_CALL_LIMITS = {
    "provider_canary_call_limit": 2,
    "author_call_limit": 100,
    "independent_review_call_limit": 100,
    "mutation_review_call_limit": 20,
    "dispute_review_call_limit": 24,
    "total_provider_call_limit": 246,
}
EXPECTED_MODELS = {
    "author": "deepseek-v4-flash",
    "independent_reviewer": "mistralai/mistral-small-2603",
    "dispute_reviewer": "deepseek-v4-pro",
}
QUESTION_VARIANT_SCHEMA = {
    "type": "object",
    "required": ["question_variant"],
    "additionalProperties": False,
    "properties": {
        "question_variant": {"type": "string", "minLength": 1},
    },
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ScalePilotError(f"cannot load JSON: {path}") from error
    if not isinstance(value, dict):
        raise ScalePilotError(f"JSON root must be an object: {path}")
    return value


def validate_instrument(path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    instrument = load_freshness_instrument(path)
    if instrument.get("status") not in {
        "draft-reviewed-provider-execution-unauthorized",
        "frozen-pending-execution",
        "completed-refine-authorization-revoked",
        "completed-keep-authorization-revoked",
    }:
        raise ScalePilotError("unexpected successor instrument status")
    authorized = instrument.get("execution", {}).get("provider_execution_authorized")
    if authorized not in {True, False}:
        raise ScalePilotError("provider authorization must be explicit")
    if authorized is True and instrument["status"] != "frozen-pending-execution":
        raise ScalePilotError("authorized successor must be frozen pending execution")
    if authorized is False and instrument["status"] == "frozen-pending-execution":
        raise ScalePilotError("frozen pending execution requires authorization")
    if instrument.get("method_version") != "factual-qa-v3-deterministic-truth-pipeline-v1":
        raise ScalePilotError("successor method version drifted")
    if instrument.get("contract_design") != {
        "version": "factual-qa-v3-contract-v3",
        "truth_package": "factual-qa-v3-truth-package-v1",
        "author_schema": "question-variant-only",
        "assembler": "deterministic-authoritative-metadata-v1",
        "malformed_fallback": "canonical-question-not-model-authored",
        "reviewer_contract": "qualification-006-strict-contract",
        "mutation_basis": "deterministic-canonical-cases",
        "normalized_question_uniqueness": "unicode-nfkc-casefold-alphanumeric-tokens",
    }:
        raise ScalePilotError("successor contract design drifted")
    truth = instrument.get("truth_design", {})
    if (
        truth.get("instrument_id") != TRUTH_INSTRUMENT_ID
        or truth.get("stage_id") != PILOT_STAGE
        or truth.get("case_count") != 100
    ):
        raise ScalePilotError("successor truth design drifted")
    execution = instrument["execution"]
    if execution.get("dataset_write_authorized") is not False:
        raise ScalePilotError("dataset writing must remain unauthorized")
    if execution.get("automatic_stage_promotion") is not False:
        raise ScalePilotError("automatic stage promotion must remain disabled")
    if execution.get("retry_attempts") != 0:
        raise ScalePilotError("provider retries must remain disabled")
    for field, expected in EXPECTED_CALL_LIMITS.items():
        if execution.get(field) != expected:
            raise ScalePilotError(f"successor call limit drifted: {field}")
    if execution.get("cost_stop_usd") != 3.0:
        raise ScalePilotError("successor cost stop drifted")
    for role, model in EXPECTED_MODELS.items():
        binding = instrument["model_roles"].get(role, {})
        if binding.get("provider_model") != model:
            raise ScalePilotError(f"successor model binding drifted: {role}")
        require_registered_current_model(model)
        for field in (
            "max_input_tokens",
            "max_output_tokens",
            "pricing_usd_per_million_input_tokens",
            "pricing_usd_per_million_output_tokens",
        ):
            value = binding.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise ScalePilotError(f"invalid successor binding field: {role}.{field}")
    reviewer = instrument["model_roles"]["independent_reviewer"]
    if reviewer.get("qualification") != "factual-qa-v3-reviewer-qualification-006":
        raise ScalePilotError("successor reviewer qualification drifted")
    if reviewer.get("provider_routing") != {
        "order": ["Mistral"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "allow",
        "zdr": False,
    }:
        raise ScalePilotError("successor reviewer routing drifted")
    if any(
        excluded not in instrument.get("excluded_models", [])
        for excluded in ("gemma", "claude", "local-qwen")
    ):
        raise ScalePilotError("successor prohibited-model exclusions drifted")
    return instrument


def _authoritative_blueprint(
    upstream: dict[str, Any],
    truth_package: dict[str, Any],
) -> dict[str, Any]:
    """Project immutable upstream structure through the successor truth contract."""
    return {
        **upstream,
        "expected_action": truth_package["expected_action"],
        "target_claim_ids": list(truth_package["selected_claim_ids"]),
        "evidence_unit_ids": list(truth_package["context_source_ids"]),
    }


def load_assets(instrument_path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    instrument = validate_instrument(instrument_path)
    artifact = build_truth_artifact()
    summary = artifact["summary"]
    truth_design = instrument["truth_design"]
    for field in ("content_sha256", "configuration_sha256"):
        if summary[field] != truth_design[field]:
            raise ScalePilotError(f"truth-package {field} drifted")
    if summary["upstream_content_sha256"] != truth_design["upstream_blueprint_sha256"]:
        raise ScalePilotError("upstream blueprint hash drifted")
    truth_packages = [
        package
        for package in artifact["truth_packages"]
        if package["checkpoint_stage"] == PILOT_STAGE
    ]
    if len(truth_packages) != 100:
        raise ScalePilotError("successor pilot must contain exactly 100 truth packages")
    questions = [package["normalized_canonical_question"] for package in truth_packages]
    if len(questions) != len(set(questions)):
        raise ScalePilotError("successor pilot canonical questions are not unique")
    upstream_blueprints = [
        blueprint
        for blueprint in artifact["blueprints"]
        if blueprint["checkpoint_stage"] == PILOT_STAGE
    ]
    blueprint_ids = {
        blueprint["blueprint_id"] for blueprint in upstream_blueprints
    }
    if blueprint_ids != {package["blueprint_id"] for package in truth_packages}:
        raise ScalePilotError("successor blueprint/truth package identities drifted")
    truth_by_id = {
        package["blueprint_id"]: package for package in truth_packages
    }
    blueprints = [
        _authoritative_blueprint(
            blueprint,
            truth_by_id[blueprint["blueprint_id"]],
        )
        for blueprint in upstream_blueprints
    ]
    source_map = {
        source["source_unit_id"]: source for source in artifact["sources"]
    }
    return {
        "instrument": instrument,
        "instrument_path": instrument_path,
        "truth_artifact_sha256": summary["content_sha256"],
        "truth_configuration_sha256": summary["configuration_sha256"],
        "sources": artifact["sources"],
        "source_map": source_map,
        "blueprints": blueprints,
        "truth_packages": truth_packages,
        "truth_by_id": truth_by_id,
    }


def validate_question_variant(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"question_variant"}:
        raise ScalePilotError("question-variant response must contain exactly one key")
    question = value["question_variant"]
    if not isinstance(question, str) or not question.strip():
        raise ScalePilotError("question variant is empty")
    if len(question) > 1000:
        raise ScalePilotError("question variant exceeds the bounded length")
    return {"question_variant": question.strip()}


def _author_prompt(truth_package: dict[str, Any]) -> str:
    return json.dumps(
        {
            "blueprint_id": truth_package["blueprint_id"],
            "slice": truth_package["slice"],
            "course_id": truth_package["course_id"],
            "expected_action": truth_package["expected_action"],
            "canonical_question": truth_package["canonical_question"],
            "canonical_answer": truth_package["canonical_answer"],
            "structured_target_claims": truth_package["structured_target_claims"],
            "candidate_claims": truth_package["candidate_claims"],
            "boundary_reason": truth_package["boundary_reason"],
            "requirements": {
                "task": "produce one faithful natural-language question variant",
                "do_not_add_facts": True,
                "do_not_change_expected_action": True,
                "output_exact_keys": ["question_variant"],
            },
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def assemble_case(
    truth_package: dict[str, Any],
    *,
    question_variant: str | None,
    used_normalized_questions: set[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    used = used_normalized_questions if used_normalized_questions is not None else set()
    canonical = truth_package["canonical_question"]
    candidate = question_variant.strip() if isinstance(question_variant, str) else None
    candidate_normalized = normalize_question(candidate or "")
    accepted = bool(candidate_normalized) and candidate_normalized not in used
    if accepted:
        question = candidate or canonical
        wording_source = "model-question-variant"
        rejection_reason = None
    else:
        question = canonical
        wording_source = "deterministic-canonical-fallback"
        rejection_reason = "duplicate-normalized-question" if candidate_normalized else "missing-or-malformed-question"
    normalized = normalize_question(question)
    if normalized in used:
        raise ScalePilotError("canonical fallback question is not unique")
    used.add(normalized)
    case = {
        "question": question,
        "answer": truth_package["canonical_answer"],
        "action": truth_package["expected_action"],
        "selected_claim_ids": list(truth_package["selected_claim_ids"]),
        "citations": list(truth_package["citations"]),
    }
    provenance = {
        "wording_source": wording_source,
        "variant_accepted": accepted,
        "variant_rejection_reason": rejection_reason,
        "truth_package_sha256": truth_package["truth_package_sha256"],
        "normalized_question": normalized,
    }
    return case, provenance


def _state_bindings(assets: dict[str, Any]) -> dict[str, Any]:
    instrument = assets["instrument"]
    return {
        "instrument_sha256": _sha256_file(assets["instrument_path"]),
        "truth_artifact_sha256": assets["truth_artifact_sha256"],
        "truth_configuration_sha256": assets["truth_configuration_sha256"],
        "code_revision": _code_revision(),
        "runner_sha256": _sha256_file(Path(__file__)),
        "model_pricing_and_freshness_sha256": _canonical_sha256(
            {
                "model_roles": _binding_snapshot(instrument),
                "freshness": instrument["freshness"],
            }
        ),
    }


def _initial_state(assets: dict[str, Any], *, simulation: bool) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_type": INSTRUMENT_ID,
        "status": "running",
        "simulation": simulation,
        "bindings": _state_bindings(assets),
        "data_boundary": assets["instrument"]["data_boundary"],
        "private_data_read": False,
        "private_data_emitted": False,
        "checkpoint_1000_authorized": False,
        "scale_10000_authorized": False,
        "maximum_reserved_cost_usd": _maximum_reserved_cost(assets["instrument"]),
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


def _load_resume(
    path: Path, assets: dict[str, Any], *, simulation: bool
) -> dict[str, Any]:
    state = _load_json(path)
    if state.get("status") != "running":
        raise ScalePilotError("only a running successor checkpoint may be resumed")
    if state.get("simulation") is not simulation:
        raise ScalePilotError("successor simulation/external resume mode drifted")
    if state.get("bindings") != _state_bindings(assets):
        raise ScalePilotError("successor resume bindings drifted")
    if state.get("run_type") != INSTRUMENT_ID:
        raise ScalePilotError("successor resume identity drifted")
    return state


def build_preflight(
    assets: dict[str, Any],
    *,
    output_path: Path = DEFAULT_OUTPUT,
    live_metadata: dict[str, Any] | None = None,
    now: datetime | None = None,
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
    age = snapshot_age_hours(instrument, now=now)
    maximum_age = float(instrument["freshness"]["maximum_age_hours_for_paid_execution"])
    snapshot_fresh = age <= maximum_age
    live_failures = (
        compare_live_metadata(instrument, live_metadata)
        if live_metadata is not None
        else ["live-provider-match-not-checked"]
    )
    live_match = not live_failures
    reservation = _maximum_reserved_cost(instrument)
    authorized = execution["provider_execution_authorized"] is True
    frozen = instrument["status"] == "frozen-pending-execution"
    ready = (
        authorized
        and frozen
        and snapshot_fresh
        and live_match
        and all(credentials.values())
        and not _working_tree_dirty()
        and not output_path.exists()
        and reservation <= execution["cost_stop_usd"]
    )
    if not authorized:
        status = "blocked-not-authorized"
    elif not frozen:
        status = "blocked-not-frozen"
    elif not snapshot_fresh or not live_match:
        status = "blocked-provider-freshness"
    else:
        status = "ready" if ready else "blocked-preflight"
    return {
        "run_type": f"{INSTRUMENT_ID}-preflight",
        "instrument_id": INSTRUMENT_ID,
        "status": status,
        "code_revision": _code_revision(),
        "provider_execution_authorized": authorized,
        "instrument_frozen": frozen,
        "case_count": len(assets["truth_packages"]),
        "working_tree_dirty": _working_tree_dirty(),
        "credentials_present": credentials,
        "credential_values_emitted": False,
        "output_available": not output_path.exists(),
        "freshness_snapshot_age_hours": age,
        "freshness_snapshot_maximum_age_hours": maximum_age,
        "freshness_snapshot_current": snapshot_fresh,
        "live_provider_match_checked": live_metadata is not None,
        "live_provider_match": live_match,
        "live_provider_failures": live_failures,
        "maximum_provider_calls": execution["total_provider_call_limit"],
        "maximum_reserved_cost_usd": reservation,
        "cost_stop_usd": execution["cost_stop_usd"],
        "external_call_enabled": False,
        "private_data_read": False,
        "checkpoint_1000_authorized": False,
        "scale_10000_authorized": False,
    }


class QuestionVariantSimulatedTransport:
    """Network-free author double for the question-only contract."""

    def __init__(
        self,
        *,
        model: str,
        fail_tasks: set[str] | None = None,
        malformed_tasks: set[str] | None = None,
        forced_question: str | None = None,
        cost_per_call: float = 0.0001,
    ) -> None:
        self.model = model
        self.fail_tasks = fail_tasks or set()
        self.malformed_tasks = malformed_tasks or set()
        self.forced_question = forced_question
        self.cost_per_call = cost_per_call
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
        else:
            payload = json.loads(prompt)
            question = self.forced_question or (
                f"Please answer this source-grounded question: "
                f"{payload['canonical_question']}"
            )
            content = json.dumps({"question_variant": question})
        return RawCall(
            content=content,
            provider_model=self.model,
            provider_revision=f"simulated-{self.model}-revision",
            input_tokens=100,
            output_tokens=30,
            approximate_cost_usd=self.cost_per_call,
            latency_ms=1.0,
        )


def _simulation_transports(instrument: dict[str, Any]) -> dict[str, RawTransport]:
    return {
        "author": QuestionVariantSimulatedTransport(
            model=instrument["model_roles"]["author"]["provider_model"]
        ),
        "independent_reviewer": SimulatedTransport(
            role="independent_reviewer",
            model=instrument["model_roles"]["independent_reviewer"]["provider_model"],
        ),
        "dispute_reviewer": SimulatedTransport(
            role="dispute_reviewer",
            model=instrument["model_roles"]["dispute_reviewer"]["provider_model"],
        ),
    }


def analyze_successor_state(
    state: dict[str, Any], instrument: dict[str, Any]
) -> dict[str, Any]:
    summary = analyze_state(state, instrument)
    accepted = sum(
        result["wording_provenance"]["variant_accepted"]
        for result in state["results"]
    )
    rate = accepted / 100
    groups = Counter(
        near_duplicate_signature(result["authored_case"]["question"])
        for result in state["results"]
    )
    summary["metrics"]["model_question_variant_acceptance_rate"] = rate
    summary["metrics"]["deterministic_fallback_count"] = 100 - accepted
    summary["metrics"]["near_duplicate_template_group_count"] = sum(
        count > 1 for count in groups.values()
    )
    summary["gate_results"]["model_question_variant_acceptance_rate"] = (
        rate >= instrument["quality_gates"]["model_question_variant_acceptance_rate_min"]
    )
    keep = all(summary["gate_results"].values())
    summary.update(
        {
            "status": "completed-keep" if keep else "completed-refine",
            "decision": "keep-method" if keep else "refine-method",
            "machine_gates_passed": keep,
            "failed_gates": sorted(
                name for name, passed in summary["gate_results"].items() if not passed
            ),
        }
    )
    return summary


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
    if _maximum_reserved_cost(instrument) > instrument["execution"]["cost_stop_usd"]:
        raise ScalePilotError("successor maximum cost reservation exceeds the hard stop")
    state = (
        _load_resume(output_path, assets, simulation=simulation)
        if resume
        else _initial_state(assets, simulation=simulation)
    )
    if not resume:
        _write_initial(output_path, state)
    source_map = assets["source_map"]
    blueprints = assets["blueprints"]
    blueprints_by_id = {item["blueprint_id"]: item for item in blueprints}
    truth_by_id = assets["truth_by_id"]
    health_system = "Return the exact requested synthetic-public health JSON."
    for role in ("author", "independent_reviewer"):
        if role in state["canaries"]:
            continue
        outcome = await _safe_call(
            role=role,
            transport=transports[role],
            system=health_system,
            prompt='Return {"status":"ok"}.',
            task=f"factual_qa_v3_pilot_100_003_{role}_health",
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

    used_questions = {
        result["wording_provenance"]["normalized_question"]
        for result in state["results"]
    }
    author_system = (
        "Paraphrase the supplied canonical synthetic question faithfully. Return "
        "one JSON object with exactly the key question_variant. Do not create an "
        "answer, action, claim ID, citation, source ID, or external fact."
    )
    for truth_package in assets["truth_packages"][len(state["results"]):]:
        outcome = await _safe_call(
            role="author",
            transport=transports["author"],
            system=author_system,
            prompt=_author_prompt(truth_package),
            task="factual_qa_v3_pilot_100_003_author",
            schema=QUESTION_VARIANT_SCHEMA,
            validator=validate_question_variant,
            state=state,
            instrument=instrument,
            output_path=output_path,
            stop_after_calls=stop_after_calls,
        )
        question_variant = (
            outcome["value"]["question_variant"]
            if outcome["status"] == "complete"
            else None
        )
        authored, provenance = assemble_case(
            truth_package,
            question_variant=question_variant,
            used_normalized_questions=used_questions,
        )
        blueprint = blueprints_by_id[truth_package["blueprint_id"]]
        state["results"].append(
            {
                "blueprint_id": blueprint["blueprint_id"],
                "slice": blueprint["slice"],
                "course_id": blueprint["course_id"],
                "expected_action": blueprint["expected_action"],
                "truth_package_sha256": truth_package["truth_package_sha256"],
                "authored_case": authored,
                "wording_provenance": provenance,
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
            task="factual_qa_v3_pilot_100_003_independent_review",
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
            task="factual_qa_v3_pilot_100_003_mutation_review",
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
        result
        for result in state["results"]
        if result["review_outcome"]["status"] != "complete"
        or result["review_outcome"]["value"]["verdict"]
        != ("accept" if result["deterministic"]["passed"] else "reject")
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
            task="factual_qa_v3_pilot_100_003_dispute_review",
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

    summary = analyze_successor_state(state, instrument)
    state["summary"] = summary
    base_packet = _priority_packet(
        state, maximum=instrument["quality_gates"]["human_priority_packet_max"]
    )
    provenance_by_id = {
        result["blueprint_id"]: result["wording_provenance"]
        for result in state["results"]
    }
    state["human_priority_packet"] = [
        {
            **item,
            "wording_provenance": provenance_by_id[item["blueprint_id"]],
        }
        for item in base_packet
    ]
    state["status"] = summary["status"]
    _checkpoint(output_path, state)
    return state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=INSTRUMENT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--preflight-live", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if sum(
        (
            arguments.validate,
            arguments.preflight,
            arguments.preflight_live,
            arguments.simulate,
            arguments.execute,
        )
    ) > 1:
        parser.error("choose one validation, preflight, simulation, or execution mode")
    if arguments.resume and not (arguments.simulate or arguments.execute):
        parser.error("--resume requires --simulate or --execute")
    return arguments


def main() -> int:
    arguments = parse_args()
    load_dotenv(ROOT / ".env")
    assets = load_assets(arguments.instrument)
    if arguments.validate:
        print(
            json.dumps(
                {
                    "status": "passed",
                    "instrument_id": INSTRUMENT_ID,
                    "truth_package_count": 10_000,
                    "pilot_case_count": 100,
                    "truth_artifact_sha256": assets["truth_artifact_sha256"],
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
    if arguments.preflight or arguments.preflight_live:
        live = fetch_live_provider_metadata() if arguments.preflight_live else None
        print(
            json.dumps(
                build_preflight(
                    assets,
                    output_path=arguments.output,
                    live_metadata=live,
                    now=datetime.now(timezone.utc),
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if arguments.simulate:
        result = asyncio.run(
            execute(
                assets,
                transports=_simulation_transports(assets["instrument"]),
                output_path=arguments.output,
                simulation=True,
                resume=arguments.resume,
            )
        )
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
        return 0
    if arguments.execute:
        live = fetch_live_provider_metadata()
        preflight = build_preflight(
            assets,
            output_path=arguments.output,
            live_metadata=live,
            now=datetime.now(timezone.utc),
        )
        if preflight["status"] != "ready":
            print(json.dumps(preflight, indent=2, sort_keys=True))
            return 2
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
        transports: dict[str, RawTransport] = {
            role: ProviderTransport(binding)
            for role, binding in assets["instrument"]["model_roles"].items()
        }
        result = asyncio.run(
            execute(
                assets,
                transports=transports,
                output_path=arguments.output,
                simulation=False,
                resume=arguments.resume,
            )
        )
        print(json.dumps(result.get("summary", result), indent=2, sort_keys=True))
        return 0
    print(
        json.dumps(
            build_preflight(assets, output_path=arguments.output),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
