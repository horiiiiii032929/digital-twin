#!/usr/bin/env python3
"""Validate, simulate, or execute the additional-900 / cumulative-1,000 checkpoint."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
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
    ANSWER_ACTION,
    BOUNDARY_ACTIONS,
    HEALTH_SCHEMA,
    REVIEW_SCHEMA,
    ProviderTransport,
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
    canonical_authored_case,
    deterministic_record,
    validate_review,
)
from scripts.run_factual_qa_v3_scale_pilot_100_003 import (
    QUESTION_VARIANT_SCHEMA,
    QuestionVariantSimulatedTransport,
    _author_prompt,
    assemble_case,
    validate_question_variant,
)
from scripts.validate_factual_qa_provider_freshness import (
    compare_live_metadata,
    fetch_live_provider_metadata,
    snapshot_age_hours,
)
from src.digital_twin.model_policy import require_registered_current_model
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


INSTRUMENT_PATH = ROOT / "research/05_evaluation/instruments/factual_qa_v3_scale_checkpoint_1000_002.json"
PREVIOUS_SUMMARY_PATH = ROOT / "research/05_evaluation/judgments/factual-qa-v3-scale-pilot-100-003-summary.json"
DEFAULT_OUTPUT = ROOT / "reports/generated/factual-qa-v3-scale-checkpoint-1000-002.json"
INSTRUMENT_ID = "factual-qa-v3-scale-checkpoint-1000-002"
TRUTH_INSTRUMENT_ID = "factual-qa-v3-10000-pipeline-002"
STAGE = "checkpoint-1000"
NEW_CASE_COUNT = 900
MUTATION_TYPES = (
    "missing-citation",
    "truncated-citation",
    "paraphrased-citation",
    "extra-supported-claim",
    "invalid-claim-binding",
    "invalid-source-binding",
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ScalePilotError(f"cannot load JSON: {path}") from error
    if not isinstance(value, dict):
        raise ScalePilotError(f"JSON root must be an object: {path}")
    return value


def validate_instrument(path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    instrument = _load_json(path)
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise ScalePilotError("unexpected checkpoint instrument ID")
    if instrument.get("status") not in {
        "draft-reviewed-provider-execution-unauthorized",
        "frozen-pending-execution",
        "completed-refine-authorization-revoked",
        "completed-keep-authorization-revoked",
        "invalid-execution-authorization-revoked",
    }:
        raise ScalePilotError("unexpected checkpoint status")
    execution = instrument.get("execution", {})
    authorized = execution.get("provider_execution_authorized")
    frozen = instrument["status"] == "frozen-pending-execution"
    if authorized not in {True, False} or authorized is not frozen:
        raise ScalePilotError("checkpoint authorization and frozen state differ")
    if execution.get("automatic_stage_promotion") is not False:
        raise ScalePilotError("automatic stage promotion must remain disabled")
    expected_limits = {
        "provider_canary_call_limit": 2,
        "author_call_limit": 900,
        "independent_review_call_limit": 900,
        "mutation_review_call_limit": 180,
        "dispute_review_call_limit": 9,
        "total_provider_call_limit": 1991,
        "retry_attempts": 0,
    }
    for name, expected in expected_limits.items():
        if execution.get(name) != expected:
            raise ScalePilotError(f"checkpoint limit drifted: {name}")
    truth = instrument.get("truth_design", {})
    if (
        truth.get("instrument_id") != TRUTH_INSTRUMENT_ID
        or truth.get("stage_id") != STAGE
        or truth.get("new_case_count") != NEW_CASE_COUNT
        or truth.get("cumulative_case_count") != 1000
    ):
        raise ScalePilotError("checkpoint truth design drifted")
    if _sha256_file(PREVIOUS_SUMMARY_PATH) != truth.get("carried_forward_summary_sha256"):
        raise ScalePilotError("carried-forward 100-case summary drifted")
    if instrument["mutation_design"].get("type_counts") != {
        mutation_type: 30 for mutation_type in MUTATION_TYPES
    }:
        raise ScalePilotError("checkpoint mutation design drifted")
    for role, model in {
        "author": "deepseek-v4-flash",
        "independent_reviewer": "mistralai/mistral-small-2603",
        "dispute_reviewer": "deepseek-v4-pro",
    }.items():
        binding = instrument["model_roles"].get(role, {})
        if binding.get("provider_model") != model:
            raise ScalePilotError(f"checkpoint model binding drifted: {role}")
        require_registered_current_model(model)
    reviewer = instrument["model_roles"]["independent_reviewer"]
    if reviewer.get("qualification") != "factual-qa-v3-reviewer-qualification-006":
        raise ScalePilotError("reviewer qualification drifted")
    if reviewer.get("provider_routing") != {
        "order": ["Mistral"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "allow",
        "zdr": False,
    }:
        raise ScalePilotError("reviewer routing drifted")
    if _maximum_reserved_cost(instrument) > execution["cost_stop_usd"]:
        raise ScalePilotError("maximum reservation exceeds emergency cost stop")
    return instrument


def _authoritative_blueprint(upstream: dict[str, Any], truth: dict[str, Any]) -> dict[str, Any]:
    return {
        **upstream,
        "expected_action": truth["expected_action"],
        "target_claim_ids": list(truth["selected_claim_ids"]),
        "evidence_unit_ids": list(truth["context_source_ids"]),
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
        package for package in artifact["truth_packages"]
        if package["checkpoint_stage"] == STAGE
    ]
    upstream = [
        blueprint for blueprint in artifact["blueprints"]
        if blueprint["checkpoint_stage"] == STAGE
    ]
    if len(truth_packages) != NEW_CASE_COUNT or len(upstream) != NEW_CASE_COUNT:
        raise ScalePilotError("checkpoint must contain exactly 900 new cases")
    truth_by_id = {package["blueprint_id"]: package for package in truth_packages}
    if set(truth_by_id) != {item["blueprint_id"] for item in upstream}:
        raise ScalePilotError("checkpoint blueprint identities drifted")
    normalized = [package["normalized_canonical_question"] for package in truth_packages]
    if len(normalized) != len(set(normalized)):
        raise ScalePilotError("checkpoint canonical questions are not unique")
    return {
        "instrument": instrument,
        "instrument_path": instrument_path,
        "truth_artifact_sha256": summary["content_sha256"],
        "truth_configuration_sha256": summary["configuration_sha256"],
        "sources": artifact["sources"],
        "source_map": {source["source_unit_id"]: source for source in artifact["sources"]},
        "blueprints": [_authoritative_blueprint(item, truth_by_id[item["blueprint_id"]]) for item in upstream],
        "truth_packages": truth_packages,
        "truth_by_id": truth_by_id,
        "previous_summary": _load_json(PREVIOUS_SUMMARY_PATH),
    }


def _state_bindings(assets: dict[str, Any]) -> dict[str, Any]:
    return {
        "instrument_sha256": _sha256_file(assets["instrument_path"]),
        "truth_artifact_sha256": assets["truth_artifact_sha256"],
        "truth_configuration_sha256": assets["truth_configuration_sha256"],
        "carried_forward_summary_sha256": _sha256_file(PREVIOUS_SUMMARY_PATH),
        "code_revision": _code_revision(),
        "runner_sha256": _sha256_file(Path(__file__)),
        "model_pricing_and_freshness_sha256": _canonical_sha256({
            "model_roles": _binding_snapshot(assets["instrument"]),
            "freshness": assets["instrument"]["freshness"],
        }),
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
        "cumulative_case_count_if_completed": 1000,
        "scale_10000_authorized": False,
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
    if state.get("simulation") is not simulation or state.get("bindings") != _state_bindings(assets):
        raise ScalePilotError("checkpoint resume bindings drifted")
    if state.get("run_type") != INSTRUMENT_ID:
        raise ScalePilotError("checkpoint resume identity drifted")
    return state


def build_preflight(
    assets: dict[str, Any], *, output_path: Path = DEFAULT_OUTPUT,
    live_metadata: dict[str, Any] | None = None, now: datetime | None = None,
) -> dict[str, Any]:
    instrument = assets["instrument"]
    execution = instrument["execution"]
    credential_names = {
        binding["credential_environment_variable"]
        for binding in instrument["model_roles"].values()
    }
    credentials = {name: bool(os.getenv(name, "").strip()) for name in sorted(credential_names)}
    age = snapshot_age_hours(instrument, now=now)
    fresh = age <= float(instrument["freshness"]["maximum_age_hours_for_paid_execution"])
    live_failures = compare_live_metadata(instrument, live_metadata) if live_metadata else ["live-provider-match-not-checked"]
    live_match = not live_failures
    authorized = execution["provider_execution_authorized"] is True
    frozen = instrument["status"] == "frozen-pending-execution"
    ready = all((authorized, frozen, fresh, live_match, all(credentials.values()), not _working_tree_dirty(), not output_path.exists()))
    status = "ready" if ready else (
        "blocked-not-authorized" if not authorized else
        "blocked-not-frozen" if not frozen else
        "blocked-provider-freshness" if not fresh or not live_match else
        "blocked-preflight"
    )
    return {
        "run_type": f"{INSTRUMENT_ID}-preflight",
        "instrument_id": INSTRUMENT_ID,
        "status": status,
        "code_revision": _code_revision(),
        "provider_execution_authorized": authorized,
        "instrument_frozen": frozen,
        "new_case_count": NEW_CASE_COUNT,
        "cumulative_case_count": 1000,
        "working_tree_dirty": _working_tree_dirty(),
        "credentials_present": credentials,
        "credential_values_emitted": False,
        "output_available": not output_path.exists(),
        "freshness_snapshot_age_hours": age,
        "freshness_snapshot_current": fresh,
        "live_provider_match_checked": live_metadata is not None,
        "live_provider_match": live_match,
        "live_provider_failures": live_failures,
        "maximum_provider_calls": execution["total_provider_call_limit"],
        "maximum_reserved_cost_usd": _maximum_reserved_cost(instrument),
        "cost_stop_usd": execution["cost_stop_usd"],
        "external_call_enabled": False,
        "scale_10000_authorized": False,
    }


def _build_mutations(assets: dict[str, Any]) -> list[dict[str, Any]]:
    blueprints = assets["blueprints"]
    source_map = assets["source_map"]
    answerable = [item for item in blueprints if item["expected_action"] == ANSWER_ACTION]
    selected: list[dict[str, Any]] = []
    remaining = list(answerable)
    while remaining and len(selected) < 180:
        seen = Counter(item["slice"] for item in selected)
        choice = min(remaining, key=lambda item: (seen[item["slice"]], item["blueprint_id"]))
        selected.append(choice)
        remaining.remove(choice)
    if len(selected) != 180:
        raise ScalePilotError("insufficient checkpoint cases for mutations")
    mutations: list[dict[str, Any]] = []
    sequence = [kind for kind in MUTATION_TYPES for _ in range(30)]
    for blueprint, mutation_type in zip(selected, sequence, strict=True):
        control = canonical_authored_case(blueprint, source_map=source_map)
        mutated = deepcopy(control)
        if mutation_type == "missing-citation":
            mutated["citations"] = []
        elif mutation_type == "truncated-citation":
            mutated["citations"][0]["quote"] = str(mutated["citations"][0]["quote"]).rsplit(" ", 1)[0]
        elif mutation_type == "paraphrased-citation":
            mutated["citations"][0]["quote"] = "Semantically equivalent paraphrase."
        elif mutation_type == "extra-supported-claim":
            targets = set(blueprint["target_claim_ids"])
            source_id, claim = next(
                (source_id, claim)
                for source_id in blueprint["evidence_unit_ids"]
                for claim in source_map[source_id]["claims"]
                if claim["claim_id"] not in targets
            )
            mutated["selected_claim_ids"].append(claim["claim_id"])
            mutated["citations"].append({"source_unit_id": source_id, "quote": claim["evidence_quote"]})
        elif mutation_type == "invalid-claim-binding":
            mutated["selected_claim_ids"][0] = "invalid-claim-id"
        else:
            mutated["citations"][0]["source_unit_id"] = "invalid-source-id"
        deterministic = deterministic_record(blueprint, mutated, source_map=source_map)
        if deterministic["passed"]:
            raise ScalePilotError("mutation failed to create a deterministic defect")
        mutations.append({
            "blueprint_id": blueprint["blueprint_id"],
            "slice": blueprint["slice"],
            "mutation_type": mutation_type,
            "control_case": control,
            "mutated_case": mutated,
            "deterministic": deterministic,
            "review_outcome": None,
        })
    return mutations


def _expected_verdict(item: dict[str, Any]) -> str:
    return "accept" if item["deterministic"]["passed"] else "reject"


def _identity_stable(state: dict[str, Any], instrument: dict[str, Any]) -> bool:
    by_role: dict[str, list[dict[str, Any]]] = {role: [] for role in instrument["model_roles"]}
    for role, outcome in state["canaries"].items():
        if outcome.get("call"):
            by_role[role].append(outcome["call"])
    for result in state["results"]:
        for field, role in (("author_outcome", "author"), ("review_outcome", "independent_reviewer"), ("dispute_outcome", "dispute_reviewer")):
            outcome = result.get(field)
            if outcome and outcome.get("call"):
                by_role[role].append(outcome["call"])
    for mutation in state["mutations"]:
        outcome = mutation.get("review_outcome")
        if outcome and outcome.get("call"):
            by_role["independent_reviewer"].append(outcome["call"])
    for role, calls in by_role.items():
        if role == "dispute_reviewer" and not calls:
            continue
        binding = instrument["model_roles"][role]
        if not calls or any(call["provider_model"] != binding["provider_model"] for call in calls):
            return False
        revisions = {call["provider_revision"] for call in calls if call["provider_revision"]}
        if binding["revision_required"] and (len(revisions) != 1 or any(not call["provider_revision"] for call in calls)):
            return False
        if len(revisions) > 1:
            return False
    return True


def analyze(state: dict[str, Any], instrument: dict[str, Any]) -> dict[str, Any]:
    results = state["results"]
    mutations = state["mutations"]
    answerable = [item for item in results if item["expected_action"] == ANSWER_ACTION]
    boundary = [item for item in results if item["expected_action"] in BOUNDARY_ACTIONS]
    agreements = [
        item for item in results
        if (item.get("review_outcome") or {}).get("status") == "complete"
        and item["review_outcome"]["value"]["verdict"] == _expected_verdict(item)
    ]
    disagreements = [item for item in results if item not in agreements]
    unresolved = [
        item for item in disagreements
        if (item.get("dispute_outcome") or {}).get("status") != "complete"
        or item["dispute_outcome"]["value"]["verdict"] != _expected_verdict(item)
    ]
    bulk = [
        *(item["author_outcome"] for item in results),
        *(item["review_outcome"] for item in results if item.get("review_outcome")),
        *(item["dispute_outcome"] for item in results if item.get("dispute_outcome")),
        *(item["review_outcome"] for item in mutations if item.get("review_outcome")),
    ]
    completed = [item for item in bulk if item["provider_response_received"]]
    malformed = [item for item in bulk if item["status"] == "malformed-response"]
    questions = [normalize_question(item["authored_case"]["question"]) for item in results]
    accepted = sum(item["wording_provenance"]["variant_accepted"] for item in results)
    mutation_rejects = sum(
        (item.get("review_outcome") or {}).get("status") == "complete"
        and item["review_outcome"]["value"]["verdict"] == "reject"
        for item in mutations
    )
    accounting = state["accounting"]
    latencies = sorted(accounting["latency_ms"])
    metrics = {
        "provider_response_completion_rate": len(completed) / len(bulk),
        "model_question_variant_acceptance_rate": accepted / NEW_CASE_COUNT,
        "deterministic_acceptance_rate": sum(item["deterministic"]["passed"] for item in results) / NEW_CASE_COUNT,
        "reviewer_agreement_rate": len(agreements) / NEW_CASE_COUNT,
        "citation_validity_rate": sum(item["deterministic"]["checks"].get("citation_quotes_and_sources_valid", False) for item in answerable) / len(answerable),
        "target_claim_completeness_rate": sum(item["deterministic"]["checks"].get("target_claim_citations_complete", False) and item["deterministic"]["checks"].get("target_claims_exact", False) for item in answerable) / len(answerable),
        "boundary_action_accuracy": sum(item["authored_case"]["action"] == item["expected_action"] for item in boundary) / len(boundary),
        "exact_duplicate_question_rate": (len(questions) - len(set(questions))) / NEW_CASE_COUNT,
        "unresolved_dispute_rate": len(unresolved) / NEW_CASE_COUNT,
        "malformed_response_rate": len(malformed) / len(bulk),
        "mutation_sensitivity": mutation_rejects / len(mutations),
        "model_identity_stable": _identity_stable(state, instrument),
        "cost_and_latency_accounting_complete": len(accounting["latency_ms"]) == accounting["calls_with_provider_response"],
        "external_cost_usd": accounting["external_cost_usd"],
        "provider_calls": accounting["calls_attempted"],
        "input_tokens": accounting["input_tokens"],
        "output_tokens": accounting["output_tokens"],
        "token_limit_exceeded_call_count": accounting["token_limit_exceeded_call_count"],
        "p95_latency_ms": latencies[max(0, math.ceil(0.95 * len(latencies)) - 1)] if latencies else 0.0,
        "private_data_calls": 0,
        "new_case_count": NEW_CASE_COUNT,
        "cumulative_case_count": 1000,
        "deterministic_fallback_count": NEW_CASE_COUNT - accepted,
        "near_duplicate_template_group_count": sum(count > 1 for count in Counter(near_duplicate_signature(item["authored_case"]["question"]) for item in results).values()),
    }
    gates = instrument["quality_gates"]
    checks = {
        "provider_response_completion_rate": metrics["provider_response_completion_rate"] >= gates["provider_response_completion_rate_min"],
        "model_question_variant_acceptance_rate": metrics["model_question_variant_acceptance_rate"] >= gates["model_question_variant_acceptance_rate_min"],
        "deterministic_acceptance_rate": metrics["deterministic_acceptance_rate"] >= gates["deterministic_acceptance_rate_min"],
        "reviewer_agreement_rate": metrics["reviewer_agreement_rate"] >= gates["reviewer_agreement_rate_min"],
        "citation_validity_rate": metrics["citation_validity_rate"] >= gates["citation_validity_rate_min"],
        "target_claim_completeness_rate": metrics["target_claim_completeness_rate"] >= gates["target_claim_completeness_rate_min"],
        "boundary_action_accuracy": metrics["boundary_action_accuracy"] >= gates["boundary_action_accuracy_min"],
        "exact_duplicate_question_rate": metrics["exact_duplicate_question_rate"] <= gates["exact_duplicate_question_rate_max"],
        "unresolved_dispute_rate": metrics["unresolved_dispute_rate"] <= gates["unresolved_dispute_rate_max"],
        "malformed_response_rate": metrics["malformed_response_rate"] <= gates["malformed_response_rate_max"],
        "mutation_sensitivity": metrics["mutation_sensitivity"] >= gates["mutation_sensitivity_min"],
        "model_identity_stable": metrics["model_identity_stable"] is True,
        "cost_and_latency_accounting_complete": metrics["cost_and_latency_accounting_complete"] is True,
        "external_cost_usd": metrics["external_cost_usd"] <= gates["external_cost_usd_max"],
        "private_data_calls": metrics["private_data_calls"] == 0,
        "provider_calls": metrics["provider_calls"] <= instrument["execution"]["total_provider_call_limit"],
    }
    passed = all(checks.values())
    return {
        "status": "completed-keep" if passed else "completed-refine",
        "decision": "keep-and-prepare-separate-9000-stage" if passed else "stop-scaling-and-decide-method",
        "machine_gates_passed": passed,
        "metrics": metrics,
        "gate_results": checks,
        "failed_gates": sorted(name for name, value in checks.items() if not value),
        "scale_10000_authorized": False,
    }


def _simulation_transports(instrument: dict[str, Any]) -> dict[str, RawTransport]:
    return {
        "author": QuestionVariantSimulatedTransport(model=instrument["model_roles"]["author"]["provider_model"]),
        "independent_reviewer": SimulatedTransport(role="independent_reviewer", model=instrument["model_roles"]["independent_reviewer"]["provider_model"]),
        "dispute_reviewer": SimulatedTransport(role="dispute_reviewer", model=instrument["model_roles"]["dispute_reviewer"]["provider_model"]),
    }


async def execute(
    assets: dict[str, Any], *, transports: dict[str, RawTransport], output_path: Path,
    simulation: bool, resume: bool = False,
) -> dict[str, Any]:
    instrument = assets["instrument"]
    state = _load_resume(output_path, assets, simulation=simulation) if resume else _initial_state(assets, simulation=simulation)
    if not resume:
        _write_initial(output_path, state)
    source_map = assets["source_map"]
    blueprints = assets["blueprints"]
    blueprints_by_id = {item["blueprint_id"]: item for item in blueprints}
    for role in ("author", "independent_reviewer"):
        if role in state["canaries"]:
            continue
        outcome = await _safe_call(
            role=role, transport=transports[role],
            system="Return the exact requested synthetic-public health JSON.",
            prompt='Return {"status":"ok"}.', task=f"fqa1000_{role}_health",
            schema=HEALTH_SCHEMA, validator=_health_validator, state=state,
            instrument=instrument, output_path=output_path, stop_after_calls=None,
        )
        state["canaries"][role] = {"role": role, **outcome}
        _checkpoint(output_path, state)
        if outcome["status"] != "complete" or state["status"] == "invalid-execution":
            state["status"] = "invalid-execution"
            state["invalid_reason"] = state.get("invalid_reason", "provider-canary-failed")
            _checkpoint(output_path, state)
            return state
    used = {item["wording_provenance"]["normalized_question"] for item in state["results"]}
    author_system = "Paraphrase the supplied canonical synthetic question faithfully. Return one JSON object with exactly the key question_variant. Do not create an answer, action, claim ID, citation, source ID, or external fact."
    for index, truth in enumerate(assets["truth_packages"][len(state["results"]):], start=len(state["results"]) + 1):
        outcome = await _safe_call(
            role="author", transport=transports["author"], system=author_system,
            prompt=_author_prompt(truth), task="fqa1000_author",
            schema=QUESTION_VARIANT_SCHEMA, validator=validate_question_variant,
            state=state, instrument=instrument, output_path=output_path, stop_after_calls=None,
        )
        variant = outcome["value"]["question_variant"] if outcome["status"] == "complete" else None
        authored, provenance = assemble_case(truth, question_variant=variant, used_normalized_questions=used)
        blueprint = blueprints_by_id[truth["blueprint_id"]]
        state["results"].append({
            "blueprint_id": blueprint["blueprint_id"], "slice": blueprint["slice"],
            "course_id": blueprint["course_id"], "expected_action": blueprint["expected_action"],
            "truth_package_sha256": truth["truth_package_sha256"], "authored_case": authored,
            "wording_provenance": provenance,
            "deterministic": deterministic_record(blueprint, authored, source_map=source_map),
            "author_outcome": outcome, "review_outcome": None, "dispute_outcome": None,
        })
        _checkpoint(output_path, state)
        if not simulation and index % 50 == 0:
            print(f"author progress {index}/{NEW_CASE_COUNT}", file=sys.stderr, flush=True)
        if state["status"] == "invalid-execution":
            return state
    review_system = _strict_review_system_prompt()
    reviewed = sum(item["review_outcome"] is not None for item in state["results"])
    for result in state["results"]:
        if result["review_outcome"] is not None:
            continue
        blueprint = blueprints_by_id[result["blueprint_id"]]
        result["review_outcome"] = await _safe_call(
            role="independent_reviewer", transport=transports["independent_reviewer"],
            system=review_system, prompt=_review_prompt(blueprint, result["authored_case"], source_map=source_map),
            task="fqa1000_independent_review", schema=REVIEW_SCHEMA,
            validator=validate_review, state=state, instrument=instrument,
            output_path=output_path, stop_after_calls=None,
        )
        reviewed += 1
        _checkpoint(output_path, state)
        if not simulation and reviewed % 50 == 0:
            print(f"review progress {reviewed}/{NEW_CASE_COUNT}", file=sys.stderr, flush=True)
        if state["status"] == "invalid-execution":
            return state
    if not state["mutations"]:
        state["mutations"] = _build_mutations(assets)
        _checkpoint(output_path, state)
    mutation_done = sum(item["review_outcome"] is not None for item in state["mutations"])
    for mutation in state["mutations"]:
        if mutation["review_outcome"] is not None:
            continue
        blueprint = blueprints_by_id[mutation["blueprint_id"]]
        mutation["review_outcome"] = await _safe_call(
            role="independent_reviewer", transport=transports["independent_reviewer"],
            system=review_system, prompt=_review_prompt(blueprint, mutation["mutated_case"], source_map=source_map),
            task="fqa1000_mutation_review", schema=REVIEW_SCHEMA,
            validator=validate_review, state=state, instrument=instrument,
            output_path=output_path, stop_after_calls=None,
        )
        mutation_done += 1
        _checkpoint(output_path, state)
        if not simulation and mutation_done % 30 == 0:
            print(f"mutation progress {mutation_done}/180", file=sys.stderr, flush=True)
        if state["status"] == "invalid-execution":
            return state
    disagreements = [
        item for item in state["results"]
        if (item.get("review_outcome") or {}).get("status") != "complete"
        or item["review_outcome"]["value"]["verdict"] != _expected_verdict(item)
    ][: instrument["execution"]["dispute_review_call_limit"]]
    for result in disagreements:
        if result["dispute_outcome"] is not None:
            continue
        blueprint = blueprints_by_id[result["blueprint_id"]]
        result["dispute_outcome"] = await _safe_call(
            role="dispute_reviewer", transport=transports["dispute_reviewer"],
            system=review_system, prompt=_review_prompt(blueprint, result["authored_case"], source_map=source_map),
            task="fqa1000_dispute_review", schema=REVIEW_SCHEMA,
            validator=validate_review, state=state, instrument=instrument,
            output_path=output_path, stop_after_calls=None,
        )
        _checkpoint(output_path, state)
        if state["status"] == "invalid-execution":
            return state
    summary = analyze(state, instrument)
    state["summary"] = summary
    state["human_priority_packet"] = _priority_packet(state, maximum=instrument["quality_gates"]["human_priority_packet_max"])
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
    args = parser.parse_args()
    if sum((args.validate, args.preflight, args.preflight_live, args.simulate, args.execute)) > 1:
        parser.error("choose one mode")
    if args.resume and not (args.simulate or args.execute):
        parser.error("--resume requires --simulate or --execute")
    return args


def main() -> int:
    args = parse_args()
    load_dotenv(ROOT / ".env")
    assets = load_assets(args.instrument)
    if args.validate:
        print(json.dumps({
            "status": "passed", "instrument_id": INSTRUMENT_ID,
            "new_case_count": NEW_CASE_COUNT, "cumulative_case_count": 1000,
            "maximum_reserved_cost_usd": _maximum_reserved_cost(assets["instrument"]),
            "provider_called": False, "private_data_read": False,
        }, indent=2, sort_keys=True))
        return 0
    if args.preflight or args.preflight_live:
        live = fetch_live_provider_metadata() if args.preflight_live else None
        print(json.dumps(build_preflight(assets, output_path=args.output, live_metadata=live, now=datetime.now(timezone.utc)), indent=2, sort_keys=True))
        return 0
    if args.simulate:
        result = asyncio.run(execute(assets, transports=_simulation_transports(assets["instrument"]), output_path=args.output, simulation=True, resume=args.resume))
        print(json.dumps(result.get("summary", result), indent=2, sort_keys=True))
        return 0
    if args.execute:
        live = fetch_live_provider_metadata()
        preflight = build_preflight(assets, output_path=args.output, live_metadata=live, now=datetime.now(timezone.utc))
        if preflight["status"] != "ready":
            print(json.dumps(preflight, indent=2, sort_keys=True))
            return 2
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
        transports = {role: ProviderTransport(binding) for role, binding in assets["instrument"]["model_roles"].items()}
        result = asyncio.run(execute(assets, transports=transports, output_path=args.output, simulation=False, resume=args.resume))
        print(json.dumps(result.get("summary", result), indent=2, sort_keys=True))
        return 0
    print(json.dumps(build_preflight(assets, output_path=args.output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
