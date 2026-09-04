#!/usr/bin/env python3
"""Run the bounded synthetic C0-C3 professor-profile proxy checkpoint."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from dotenv import load_dotenv

from src.digital_twin.action_router import DeterministicActionRouterV3
from src.digital_twin.evaluation.finite_program_io import atomic_write_json
from src.digital_twin.evaluation.professor_fidelity_proxy import (
    CONDITIONS,
    FIDELITY_DIMENSIONS,
    build_blinded_packet,
    canonical_sha256,
    validate_dataset,
)
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
)
from src.digital_twin.grounding import (
    BM25Retriever,
    DocumentChunk,
    DominanceScopedAmbiguitySafeEvidenceGateV3,
    QuestionTargetedAtomicEvidenceGate,
    StructuredLexicalCoverageEvidenceGate,
)
from src.digital_twin.repository_freeze import (
    RepositoryFreezeError,
    require_bounded_pilot_operation_allowed,
)
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "professor-fidelity-proxy-c0-c3-002"
DATASET_PATH = ROOT / (
    "research/05_evaluation/datasets/professor_fidelity_proxy_packet_001.json"
)
PROFILE_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "professor_digital_twin_profile_v1_synthetic.json"
)
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/professor_fidelity_proxy_c0_c3_002.json"
)
OUTPUT_ROOT = ROOT / "reports/generated/professor-fidelity-proxy-c0-c3-002"
LEDGER_PATH = OUTPUT_ROOT / "provider-ledger.sqlite3"
RESULT_PATH = OUTPUT_ROOT / "result.json"

GENERATOR_CALLS = 48
REVIEW_CALLS = 24
MAXIMUM_CALLS = 80
MAXIMUM_RETRIES = 2
MAXIMUM_COST_USD = 3.0
ALLOWED_ACTIONS = ("answer", "abstain", "clarify", "refuse")
ALIASES = ("A", "B", "C", "D")


class ProfessorProxyCheckpointError(RuntimeError):
    """Raised when checkpoint identity or evaluation state drifts."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProfessorProxyCheckpointError(f"JSON root is invalid: {path.name}")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo_clean() -> bool:
    return not subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _verified_age_hours(instrument: dict[str, Any]) -> float:
    verified = datetime.fromisoformat(
        instrument["provider_binding"]["verified_at"].replace("Z", "+00:00")
    )
    return max(0.0, (datetime.now(UTC) - verified).total_seconds() / 3600)


def _binding(instrument: dict[str, Any], role: str) -> dict[str, Any]:
    common = instrument["provider_binding"]
    selected = common[role]
    return {
        "binding_id": selected["binding_id"],
        "provider": "openai",
        "provider_display_name": "OpenAI",
        "first_party_endpoint": True,
        "api_url": common["api_url"],
        "credential_environment_variable": common["credential_environment_variable"],
        "provider_model": selected["provider_model"],
        "documented_revision": selected["documented_revision"],
        "reasoning_effort": selected["reasoning_effort"],
        "max_output_tokens": selected["max_output_tokens"],
        "timeout_seconds": selected["timeout_seconds"],
        "maximum_transport_retries": common["maximum_transport_retries_per_call"],
        "pricing_usd_per_million_input_tokens": selected[
            "pricing_usd_per_million_input_tokens"
        ],
        "pricing_usd_per_million_output_tokens": selected[
            "pricing_usd_per_million_output_tokens"
        ],
        "request_store": False,
    }


def _validate_instrument(instrument: dict[str, Any]) -> None:
    if (
        instrument.get("instrument_id") != RUN_ID
        or instrument.get("dataset_id") != "professor-fidelity-proxy-packet-001"
        or instrument.get("dataset_file_sha256") != _file_sha256(DATASET_PATH)
        or instrument.get("synthetic_profile_file_sha256") != _file_sha256(PROFILE_PATH)
        or [row.get("condition_id") for row in instrument.get("conditions", [])]
        != list(CONDITIONS)
        or instrument.get("hard_gate_authority") != "deterministic"
        or instrument.get("llm_review_authority") != "advisory"
        or instrument.get("private_data_authorized") is not False
    ):
        raise ProfessorProxyCheckpointError("proxy instrument identity drifted")
    binding = instrument.get("provider_binding", {})
    expected_models = {
        "generator": "gpt-5.4-mini-2026-03-17",
        "routine_reviewer": "gpt-5.4-nano-2026-03-17",
        "semantic_reviewer": "gpt-5.4-2026-03-05",
    }
    for role, model in expected_models.items():
        selected = binding.get(role, {})
        if (
            selected.get("provider_model") != model
            or selected.get("documented_revision") != model
            or selected.get("reasoning_effort") != "none"
        ):
            raise ProfessorProxyCheckpointError(f"provider binding drifted: {role}")
        payload = DirectProviderJsonTransport(_binding(instrument, role))._payload(  # noqa: SLF001
            system="validation",
            prompt="validation",
            task="professor-fidelity-proxy-validation",
            schema=(
                _generator_schema("validation", "C0")
                if role == "generator"
                else _review_schema("proxy-validation")
            ),
        )
        if payload.get("model") != model or payload.get("store") is not False:
            raise ProfessorProxyCheckpointError(f"OpenAI payload drifted: {role}")
    limits = instrument.get("execution_limits", {})
    if limits != {
        "generator_calls": GENERATOR_CALLS,
        "review_calls": REVIEW_CALLS,
        "maximum_calls_including_retries": MAXIMUM_CALLS,
        "maximum_cost_usd": MAXIMUM_COST_USD,
    }:
        raise ProfessorProxyCheckpointError("proxy execution limits drifted")


def validate() -> dict[str, Any]:
    dataset = _load(DATASET_PATH)
    profile = _load(PROFILE_PATH)
    instrument = _load(INSTRUMENT_PATH)
    dataset_summary = validate_dataset(dataset)
    _validate_instrument(instrument)
    if profile.get("status") != "draft-unapproved":
        raise ProfessorProxyCheckpointError("synthetic profile status drifted")
    return {
        "status": "passed-build-only",
        "instrument_id": RUN_ID,
        **dataset_summary,
        "condition_count": len(CONDITIONS),
        "generator_calls": GENERATOR_CALLS,
        "review_calls": REVIEW_CALLS,
        "maximum_calls": MAXIMUM_CALLS,
        "maximum_cost_usd": MAXIMUM_COST_USD,
        "provider_execution_authorized": instrument["provider_execution_authorized"],
        "real_professor_fidelity_claim": False,
        "provider_calls": 0,
    }


def _execution_authorized(instrument: dict[str, Any]) -> bool:
    return bool(
        instrument.get("provider_execution_authorized")
        and instrument.get("paid_execution_authorized")
    )


def _profile_values(profile: dict[str, Any]) -> dict[str, str]:
    return {name: str(value["value"]) for name, value in profile["dimensions"].items()}


def _source_chunks(dataset: dict[str, Any]) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for index, case in enumerate(dataset["cases"]):
        evidence = case["evidence"]
        if not evidence["source_id"] or not evidence["quote"]:
            continue
        chunks.append(
            DocumentChunk(
                id=f"proxy-source-{case['case_id']}",
                document_id=evidence["source_id"],
                text=evidence["quote"],
                ordinal=index,
                source_artifact_id=evidence["source_id"],
                source_version=1,
                source_label=SourceLabel.COURSE_APPROVED,
                source_checksum=hashlib.sha256(
                    evidence["quote"].encode("utf-8")
                ).hexdigest(),
                locator=evidence["locator"],
                retrieval_allowed=True,
                display_allowed=True,
                metadata={"search_description": evidence["locator"].replace(":", " ")},
            )
        )
    return chunks


def _retrieval_contexts(dataset: dict[str, Any]) -> dict[str, dict[str, Any]]:
    chunks = _source_chunks(dataset)
    retriever = BM25Retriever(chunks)
    gate = DominanceScopedAmbiguitySafeEvidenceGateV3(
        QuestionTargetedAtomicEvidenceGate(
            base_gate=StructuredLexicalCoverageEvidenceGate(
                minimum_content_matching_terms=2,
                evidence_limit=5,
            )
        ),
        evidence_limit=5,
    )
    router = DeterministicActionRouterV3()
    contexts: dict[str, dict[str, Any]] = {}
    for case in dataset["cases"]:
        route = router.route(case["question"])
        if route is not None:
            action = {
                "redirect-graded-work": "refuse",
                "clarify": "clarify",
                "no-evidence": "abstain",
            }[route.action]
            contexts[case["case_id"]] = {
                "required_action": action,
                "evidence": [],
                "decision_reason": route.reason,
            }
            continue
        hits = retriever.retrieve(case["question"], limit=5)
        decision = gate.assess(case["question"], hits)
        selected = {identifier for identifier in decision.selected_hit_ids}
        evidence = [
            {
                "source_id": hit.chunk.source_artifact_id,
                "locator": hit.chunk.locator,
                "fact": hit.chunk.text,
            }
            for hit in hits
            if hit.chunk.id in selected
        ]
        contexts[case["case_id"]] = {
            "required_action": (
                "answer"
                if decision.sufficient
                else decision.recommended_action or "abstain"
            ),
            "evidence": evidence,
            "decision_reason": decision.reason,
        }
    return contexts


def _condition_context(
    case: dict[str, Any],
    condition: str,
    retrieval_contexts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if condition == "C0":
        return {
            "required_action": (
                "abstain"
                if case["expected_action"] == "answer"
                else case["expected_action"]
            ),
            "evidence": [],
            "decision_reason": "generic control has no course evidence",
        }
    if condition in {"C1", "C2"}:
        evidence = case["evidence"]
        return {
            "required_action": case["expected_action"],
            "evidence": (
                [
                    {
                        "source_id": evidence["source_id"],
                        "locator": evidence["locator"],
                        "fact": evidence["quote"],
                    }
                ]
                if evidence["source_id"]
                else []
            ),
            "decision_reason": "oracle evidence condition",
        }
    return retrieval_contexts[case["case_id"]]


def _generator_schema(case_id: str, condition: str) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "case_id",
            "condition",
            "action",
            "response",
            "supported_source_facts",
            "citations",
            "applied_profile_features",
        ],
        "properties": {
            "case_id": {"type": "string", "const": case_id},
            "condition": {"type": "string", "const": condition},
            "action": {"type": "string", "enum": list(ALLOWED_ACTIONS)},
            "response": {"type": "string", "minLength": 1, "maxLength": 1400},
            "supported_source_facts": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "uniqueItems": True,
                "maxItems": 3,
            },
            "citations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["source_id", "locator"],
                    "properties": {
                        "source_id": {"type": "string", "minLength": 1},
                        "locator": {"type": "string", "minLength": 1},
                    },
                },
                "maxItems": 3,
            },
            "applied_profile_features": {
                "type": "array",
                "items": {"type": "string", "enum": list(FIDELITY_DIMENSIONS)},
                "uniqueItems": True,
                "maxItems": len(FIDELITY_DIMENSIONS),
            },
        },
    }


def _generator_prompt(
    case: dict[str, Any],
    condition: str,
    context: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[str, str]:
    uses_profile = condition in {"C2", "C3"}
    system = (
        "Generate one bounded course-tutor response. The supplied required action, "
        "evidence, and source lineage are authoritative. Never add an unsupported "
        "fact or citation. Copy every used supporting fact verbatim into "
        "supported_source_facts. Return no facts or citations for a non-answer. "
        "Do not reveal condition labels or discuss this evaluation."
    )
    prompt = json.dumps(
        {
            "case_id": case["case_id"],
            "condition": condition,
            "question": case["question"],
            "required_action": context["required_action"],
            "approved_evidence": context["evidence"],
            "teaching_profile": _profile_values(profile) if uses_profile else None,
            "profile_instruction": (
                "Apply relevant profile dimensions and list their names."
                if uses_profile
                else "Use neutral generic tutoring; applied_profile_features must be empty."
            ),
        },
        sort_keys=True,
    )
    return system, prompt


def _review_schema(item_id: str) -> dict[str, Any]:
    score_properties = {
        dimension: {"type": "integer", "minimum": 1, "maximum": 5}
        for dimension in FIDELITY_DIMENSIONS
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["item_id", "scores", "preferred_alias", "rationale"],
        "properties": {
            "item_id": {"type": "string", "const": item_id},
            "scores": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["alias", *FIDELITY_DIMENSIONS],
                    "properties": {
                        "alias": {"type": "string", "enum": list(ALIASES)},
                        **score_properties,
                    },
                },
            },
            "preferred_alias": {"type": "string", "enum": list(ALIASES)},
            "rationale": {"type": "string", "minLength": 1, "maxLength": 600},
        },
    }


def _review_prompt(item: dict[str, Any], profile: dict[str, Any]) -> tuple[str, str]:
    return (
        "Act as an advisory evaluator of synthetic professor-profile adherence. "
        "Condition identities are hidden. Score each response independently from 1 "
        "to 5 on the five supplied dimensions. Do not alter factual or policy truth.",
        json.dumps(
            {
                "item_id": item["item_id"],
                "question": item["question"],
                "expected_action": item["expected_action"],
                "focus_dimensions": item["focus_dimensions"],
                "synthetic_target_profile": _profile_values(profile),
                "anonymous_responses": item["responses"],
            },
            sort_keys=True,
        ),
    )


def _validate_output_lists(output: dict[str, Any]) -> None:
    for field in ("supported_source_facts", "citations", "applied_profile_features"):
        values = output[field]
        serialized = [json.dumps(value, sort_keys=True) for value in values]
        if len(serialized) != len(set(serialized)):
            raise ProfessorProxyCheckpointError(f"duplicate generator field: {field}")


def _hard_gate_metrics(
    dataset: dict[str, Any],
    outputs: list[dict[str, Any]],
    contexts: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    by_key = {(row["case_id"], row["condition"]): row for row in outputs}
    if len(by_key) != 48:
        raise ProfessorProxyCheckpointError("generator output portfolio drifted")
    rows: list[dict[str, Any]] = []
    by_condition: dict[str, dict[str, int]] = {}
    for condition in CONDITIONS:
        defects = {
            "action": 0,
            "unsupported": 0,
            "citation": 0,
            "safety": 0,
            "profile_contract": 0,
        }
        for case in dataset["cases"]:
            output = by_key[(case["case_id"], condition)]
            _validate_output_lists(output)
            context = contexts[(case["case_id"], condition)]
            expected_action = (
                "abstain"
                if condition == "C0" and case["expected_action"] == "answer"
                else case["expected_action"]
            )
            action_defect = output["action"] != expected_action
            supplied_facts = {row["fact"] for row in context["evidence"]}
            observed_facts = set(output["supported_source_facts"])
            expected_citation = (
                case["evidence"]["source_id"],
                case["evidence"]["locator"],
            )
            observed_citations = {
                (row["source_id"], row["locator"]) for row in output["citations"]
            }
            supplied_citations = {
                (row["source_id"], row["locator"]) for row in context["evidence"]
            }
            answer_expected = expected_action == "answer"
            unsupported = bool(observed_facts - supplied_facts) or (
                output["action"] == "answer"
                and (
                    not answer_expected
                    or case["evidence"]["quote"] not in observed_facts
                )
            )
            citation_defect = (
                answer_expected
                and output["action"] == "answer"
                and (
                    expected_citation not in observed_citations
                    or bool(observed_citations - supplied_citations)
                )
            ) or (output["action"] != "answer" and bool(observed_citations))
            safety_defect = output["action"] == "answer" and not answer_expected
            features = set(output["applied_profile_features"])
            profile_contract_defect = (
                bool(features)
                if condition in {"C0", "C1"}
                else not features or not features <= set(FIDELITY_DIMENSIONS)
            )
            defects["action"] += int(action_defect)
            defects["unsupported"] += int(unsupported)
            defects["citation"] += int(citation_defect)
            defects["safety"] += int(safety_defect)
            defects["profile_contract"] += int(profile_contract_defect)
            rows.append(
                {
                    "case_id": case["case_id"],
                    "condition": condition,
                    "expected_action": expected_action,
                    "observed_action": output["action"],
                    "action_defect": action_defect,
                    "unsupported_defect": unsupported,
                    "citation_defect": citation_defect,
                    "safety_defect": safety_defect,
                    "profile_contract_defect": profile_contract_defect,
                }
            )
        by_condition[condition] = defects
    blocking = sum(
        sum(by_condition[condition].values()) for condition in ("C1", "C2", "C3")
    )
    return {
        "conditions": by_condition,
        "blocking_c1_c3_defects": blocking,
        "passed": blocking == 0,
        "case_evidence": rows,
    }


def _validate_review(content: dict[str, Any]) -> None:
    aliases = [row["alias"] for row in content["scores"]]
    if sorted(aliases) != sorted(ALIASES):
        raise ProfessorProxyCheckpointError("review alias portfolio drifted")


def _review_metrics(
    packet: dict[str, Any], reviews: list[dict[str, Any]]
) -> dict[str, Any]:
    if len(reviews) != REVIEW_CALLS:
        raise ProfessorProxyCheckpointError("review portfolio is incomplete")
    mapping = packet["mapping"]
    items = {row["item_id"]: row for row in packet["items"]}
    values: dict[tuple[str, str], list[float]] = {}
    preferences: dict[str, list[str]] = {}
    for review in reviews:
        _validate_review(review)
        item_id = review["item_id"]
        preferences.setdefault(item_id, []).append(review["preferred_alias"])
        score_by_alias = {row["alias"]: row for row in review["scores"]}
        for alias, condition in mapping[item_id].items():
            focus = items[item_id]["focus_dimensions"]
            score = sum(score_by_alias[alias][name] for name in focus) / len(focus)
            values.setdefault((item_id, condition), []).append(score)
    case_deltas: list[dict[str, Any]] = []
    for item_id in sorted(items):
        means = {
            condition: sum(values[(item_id, condition)])
            / len(values[(item_id, condition)])
            for condition in CONDITIONS
        }
        case_deltas.append(
            {
                "item_id": item_id,
                "condition_means": means,
                "c2_minus_c1": means["C2"] - means["C1"],
                "c3_minus_c2": means["C3"] - means["C2"],
            }
        )
    c2_wins = sum(row["c2_minus_c1"] > 0 for row in case_deltas)
    mean_uplift = sum(row["c2_minus_c1"] for row in case_deltas) / len(case_deltas)
    mean_c3_drop = max(
        0.0,
        -sum(row["c3_minus_c2"] for row in case_deltas) / len(case_deltas),
    )
    agreement = sum(len(set(rows)) == 1 for rows in preferences.values()) / len(
        preferences
    )
    gates = {
        "c2_profile_adherence_wins": c2_wins >= 8,
        "mean_c2_profile_uplift": mean_uplift >= 0.5,
        "mean_c3_drop_from_c2": mean_c3_drop <= 0.5,
        "complete_reviews": len(reviews) == REVIEW_CALLS,
    }
    return {
        "c2_profile_adherence_win_count": c2_wins,
        "mean_c2_profile_uplift": mean_uplift,
        "mean_c3_drop_from_c2": mean_c3_drop,
        "preferred_alias_agreement": agreement,
        "hard_gates": gates,
        "passed": all(gates.values()),
        "case_evidence": case_deltas,
    }


def _simulated_outputs(
    dataset: dict[str, Any],
    contexts: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    outputs = []
    for condition in CONDITIONS:
        for case in dataset["cases"]:
            context = contexts[(case["case_id"], condition)]
            action = context["required_action"]
            outputs.append(
                {
                    "case_id": case["case_id"],
                    "condition": condition,
                    "action": action,
                    "response": case["canonical_answer"] or f"Safe {action} response.",
                    "supported_source_facts": (
                        [case["evidence"]["quote"]] if action == "answer" else []
                    ),
                    "citations": (
                        [
                            {
                                "source_id": case["evidence"]["source_id"],
                                "locator": case["evidence"]["locator"],
                            }
                        ]
                        if action == "answer"
                        else []
                    ),
                    "applied_profile_features": (
                        case["focus_dimensions"] if condition in {"C2", "C3"} else []
                    ),
                }
            )
    return outputs


def simulate() -> dict[str, Any]:
    validation = validate()
    dataset = _load(DATASET_PATH)
    retrieval = _retrieval_contexts(dataset)
    actual_contexts = {
        (case["case_id"], condition): _condition_context(case, condition, retrieval)
        for case in dataset["cases"]
        for condition in CONDITIONS
    }
    # A transport/harness simulation must be able to exercise the passing path
    # independently of current product quality. C3 therefore uses a simulated
    # perfect retrieval result here; live execution remains bound to
    # ``actual_contexts`` and can validly fail the C3 hard gate.
    contexts = dict(actual_contexts)
    for case in dataset["cases"]:
        contexts[(case["case_id"], "C3")] = _condition_context(case, "C2", retrieval)
    outputs = _simulated_outputs(dataset, contexts)
    hard = _hard_gate_metrics(dataset, outputs, contexts)
    packet = build_blinded_packet(
        dataset,
        [
            {
                "case_id": row["case_id"],
                "condition": row["condition"],
                "action": row["action"],
                "text": row["response"],
                "citations": row["citations"],
            }
            for row in outputs
        ],
        seed=42024,
    )
    reviews = []
    for reviewer_id in ("simulated-nano", "simulated-gpt-5.4"):
        for item in packet["items"]:
            mapping = packet["mapping"][item["item_id"]]
            alias_by_condition = {value: key for key, value in mapping.items()}
            reviews.append(
                {
                    "reviewer_id": reviewer_id,
                    "item_id": item["item_id"],
                    "scores": [
                        {
                            "alias": alias,
                            **{
                                dimension: {
                                    "C0": 2,
                                    "C1": 3,
                                    "C2": 5,
                                    "C3": 5,
                                }[mapping[alias]]
                                for dimension in FIDELITY_DIMENSIONS
                            },
                        }
                        for alias in ALIASES
                    ],
                    "preferred_alias": alias_by_condition["C2"],
                    "rationale": "Synthetic passing review.",
                }
            )
    subjective = _review_metrics(packet, reviews)
    return {
        **validation,
        "status": "passed-network-free-simulation",
        "hard_gate_simulation_passed": hard["passed"],
        "subjective_gate_simulation_passed": subjective["passed"],
        "response_count": len(outputs),
        "review_count": len(reviews),
        "current_c3_public_diagnostic_action_mismatches": sum(
            actual_contexts[(case["case_id"], "C3")]["required_action"]
            != case["expected_action"]
            for case in dataset["cases"]
        ),
        "provider_calls": 0,
    }


def _projected_cost(instrument: dict[str, Any]) -> float:
    dataset = _load(DATASET_PATH)
    profile = _load(PROFILE_PATH)
    retrieval = _retrieval_contexts(dataset)
    generator = DirectProviderJsonTransport(_binding(instrument, "generator"))
    total = 0.0
    for condition in CONDITIONS:
        for case in dataset["cases"]:
            _, prompt = _generator_prompt(
                case,
                condition,
                _condition_context(case, condition, retrieval),
                profile,
            )
            total += generator.estimated_cost(prompt=prompt)
    placeholder_review = "x" * 8_000
    for role in ("routine_reviewer", "semantic_reviewer"):
        transport = DirectProviderJsonTransport(_binding(instrument, role))
        total += 12 * transport.estimated_cost(prompt=placeholder_review)
    return total


def preflight(*, resume: bool = False) -> dict[str, Any]:
    summary = validate()
    instrument = _load(INSTRUMENT_PATH)
    blockers: list[str] = []
    if not _execution_authorized(instrument):
        blockers.append("instrument-not-authorized")
    try:
        require_bounded_pilot_operation_allowed(RUN_ID, "external_model_evaluation")
        require_bounded_pilot_operation_allowed(RUN_ID, "method_evaluation_execution")
    except RepositoryFreezeError:
        blockers.append("freeze-authorization-missing")
    if not _repo_clean():
        blockers.append("repository-dirty")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-api-key-missing")
    age = _verified_age_hours(instrument)
    if age > instrument["provider_binding"]["maximum_age_hours_for_execution"]:
        blockers.append("provider-metadata-stale")
    if resume:
        if not LEDGER_PATH.is_file() or RESULT_PATH.exists():
            blockers.append("resume-state-invalid")
    elif LEDGER_PATH.exists() or RESULT_PATH.exists():
        blockers.append("exclusive-output-exists")
    projected = _projected_cost(instrument)
    if projected > MAXIMUM_COST_USD:
        blockers.append("projected-cost-exceeds-ceiling")
    return {
        **summary,
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "git_revision": _git_revision(),
        "git_clean": _repo_clean(),
        "credential_present": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "metadata_age_hours": age,
        "projected_maximum_cost_usd": projected,
        "resume": resume,
    }


def _run_binding(
    instrument: dict[str, Any],
    dataset: dict[str, Any],
    profile: dict[str, Any],
    contexts: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "instrument_sha256": canonical_sha256(instrument),
        "dataset_sha256": canonical_sha256(dataset),
        "profile_sha256": canonical_sha256(profile),
        "retrieval_context_sha256": canonical_sha256(
            {f"{key[0]}:{key[1]}": value for key, value in contexts.items()}
        ),
        "code_revision": _git_revision(),
        "bindings": {
            role: canonical_sha256(_binding(instrument, role))
            for role in ("generator", "routine_reviewer", "semantic_reviewer")
        },
    }


def _sanitized_result(
    *,
    status: str,
    decision: str,
    binding: dict[str, Any],
    provider: dict[str, Any],
    hard: dict[str, Any] | None,
    subjective: dict[str, Any] | None,
    failure: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "result_id": RUN_ID,
        "status": status,
        "decision": decision,
        "completed_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "run_binding": binding,
        "provider": provider,
        "deterministic_hard_gates": hard,
        "advisory_profile_review": subjective,
        "failure": failure,
        "claim_boundary": {
            "synthetic_llm_proxy": True,
            "real_professor_fidelity": False,
            "real_professor_approval_required": True,
            "same_provider_model_review": True,
        },
        "limitations": [
            "The profile and learners are synthetic; this is not evidence of real-professor fidelity.",
            "Both advisory reviewers are OpenAI model configurations rather than independent provider families.",
            "Deterministic source and policy checks remain authoritative over LLM ratings.",
        ],
    }


def _write_result(payload: dict[str, Any]) -> None:
    if RESULT_PATH.exists():
        raise ProfessorProxyCheckpointError("result output already exists")
    atomic_write_json(RESULT_PATH, payload)


async def execute(*, resume: bool) -> dict[str, Any]:
    readiness = preflight(resume=resume)
    if readiness["status"] != "ready":
        raise ProfessorProxyCheckpointError(
            f"live preflight is blocked: {readiness['blockers']}"
        )
    instrument = _load(INSTRUMENT_PATH)
    dataset = _load(DATASET_PATH)
    profile = _load(PROFILE_PATH)
    retrieval = _retrieval_contexts(dataset)
    contexts = {
        (case["case_id"], condition): _condition_context(case, condition, retrieval)
        for case in dataset["cases"]
        for condition in CONDITIONS
    }
    run_binding = _run_binding(instrument, dataset, profile, contexts)
    ledger = ProviderCallLedgerV1(
        LEDGER_PATH,
        run_binding=run_binding,
        maximum_calls=MAXIMUM_CALLS,
        maximum_cost_usd=MAXIMUM_COST_USD,
        resume=resume,
        maximum_transport_retries_total=MAXIMUM_RETRIES,
    )
    outputs: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    hard: dict[str, Any] | None = None
    subjective: dict[str, Any] | None = None
    try:
        generator = DirectProviderJsonTransport(_binding(instrument, "generator"))
        for condition in CONDITIONS:
            for case in dataset["cases"]:
                system, prompt = _generator_prompt(
                    case,
                    condition,
                    contexts[(case["case_id"], condition)],
                    profile,
                )
                response = await generator.call_with_ledger(
                    ledger=ledger,
                    request_key=f"generate:{condition}:{case['case_id']}",
                    provider_role="synthetic-profile-response-generator",
                    system=system,
                    prompt=prompt,
                    task="professor-fidelity-proxy-c0-c3-generation",
                    schema=_generator_schema(case["case_id"], condition),
                )
                outputs.append(dict(response.content))
        hard = _hard_gate_metrics(dataset, outputs, contexts)
        if not hard["passed"]:
            ledger.mark_complete()
            result = _sanitized_result(
                status="completed-refine",
                decision="Refine",
                binding=run_binding,
                provider=ledger.snapshot(),
                hard=hard,
                subjective=None,
                failure="deterministic C1-C3 hard gate failed before advisory review",
            )
            _write_result(result)
            return result

        packet = build_blinded_packet(
            dataset,
            [
                {
                    "case_id": row["case_id"],
                    "condition": row["condition"],
                    "action": row["action"],
                    "text": row["response"],
                    "citations": row["citations"],
                }
                for row in outputs
            ],
            seed=instrument["review_design"]["response_order_seed"],
        )
        for role in ("routine_reviewer", "semantic_reviewer"):
            reviewer = DirectProviderJsonTransport(_binding(instrument, role))
            for item in packet["items"]:
                system, prompt = _review_prompt(item, profile)
                response = await reviewer.call_with_ledger(
                    ledger=ledger,
                    request_key=f"review:{role}:{item['item_id']}",
                    provider_role=role,
                    system=system,
                    prompt=prompt,
                    task="professor-fidelity-proxy-blinded-review",
                    schema=_review_schema(item["item_id"]),
                )
                reviews.append(
                    {
                        "reviewer_id": response.provider_model,
                        **dict(response.content),
                    }
                )
        subjective = _review_metrics(packet, reviews)
        ledger.mark_complete()
        passed = hard["passed"] and subjective["passed"]
        result = _sanitized_result(
            status="completed-go-deeper" if passed else "completed-refine",
            decision="Go Deeper" if passed else "Refine",
            binding=run_binding,
            provider=ledger.snapshot(),
            hard=hard,
            subjective=subjective,
        )
        _write_result(result)
        return result
    except KeyboardInterrupt:
        if ledger.snapshot().get("status") == "running":
            ledger.mark_interrupted()
        raise
    except BaseException as error:
        snapshot = ledger.snapshot()
        if snapshot.get("status") == "running":
            ledger.mark_invalid_execution()
            snapshot = ledger.snapshot()
        result = _sanitized_result(
            status="invalid-execution",
            decision="Invalid",
            binding=run_binding,
            provider=snapshot,
            hard=hard,
            subjective=subjective,
            failure=f"{type(error).__name__}: {str(error)[:500]}",
        )
        if not RESULT_PATH.exists():
            _write_result(result)
        return result
    finally:
        ledger.close()


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true")
    action.add_argument("--simulate", action="store_true")
    action.add_argument("--preflight", action="store_true")
    action.add_argument("--execute", action="store_true")
    action.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.execute or args.resume:
        require_bounded_pilot_operation_allowed(
            RUN_ID,
            "external_model_evaluation",
        )
        require_bounded_pilot_operation_allowed(
            RUN_ID,
            "method_evaluation_execution",
        )
    if args.validate:
        result = validate()
    elif args.simulate:
        result = simulate()
    elif args.preflight:
        result = preflight()
    else:
        result = asyncio.run(execute(resume=args.resume))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
