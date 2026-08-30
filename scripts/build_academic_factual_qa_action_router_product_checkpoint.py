#!/usr/bin/env python3
"""Build the finite, provider-unauthorized 500+100 action-router checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import build_academic_factual_qa_action_router_confirmation as dataset
from src.digital_twin.evaluation.factual_qa_contract import SystemUnderTestManifestV1
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-action-router-product-checkpoint-001"
DATASET_ID = "academic-factual-qa-action-router-product-development-001"
CONTROL_DATASET_ID = f"{DATASET_ID}-control"
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
INSTRUMENT_ROOT = ROOT / "research/05_evaluation/instruments"
CASES = DATASET_ROOT / f"{DATASET_ID}-cases.json"
GOLD = DATASET_ROOT / f"{DATASET_ID}-gold.json"
CONTROL_CASES = DATASET_ROOT / f"{CONTROL_DATASET_ID}-cases.json"
CONTROL_GOLD = DATASET_ROOT / f"{CONTROL_DATASET_ID}-gold.json"
INSTRUMENT = INSTRUMENT_ROOT / "academic_factual_qa_action_router_product_checkpoint_001.json"
BINDING = INSTRUMENT_ROOT / "academic_factual_qa_action_router_product_openai_binding_001.json"
CANDIDATE_MANIFEST = INSTRUMENT_ROOT / "academic_factual_qa_action_router_product_candidate_manifest_001.json"
CONTROL_MANIFEST = INSTRUMENT_ROOT / "academic_factual_qa_action_router_product_control_manifest_001.json"
PROFILE = ROOT / "research/05_evaluation/profiles/student-tutor-r1-openai-candidate-v1.json"
RETRIEVAL_RUNTIME = ROOT / "reports/generated/academic-factual-qa-action-router-product-checkpoint-001/retrieval-runtime.json"
METADATA_VERIFIED_AT = "2026-08-30T14:09:26+00:00"
PROVIDER_EXECUTION_AUTHORIZED = True
PAID_EXECUTION_AUTHORIZED = True


class ActionRouterCheckpointBuildError(RuntimeError):
    """Raised when the checkpoint cannot be frozen exactly."""


def _load_hashed(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    observed = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != observed:
        raise ActionRouterCheckpointBuildError(f"content hash drifted: {path.name}")
    return payload


def _hashed(payload: dict[str, Any]) -> dict[str, Any]:
    value = dict(payload)
    value["content_sha256"] = canonical_json_sha256(value)
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package(
    *, dataset_id: str, key: str, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    return _hashed(
        {
            "schema_version": 1,
            "dataset_id": dataset_id,
            "split": "development-confirmation",
            "case_count": len(rows),
            key: rows,
        }
    )


def _control_clusters(
    cases: list[dict[str, Any]], source: dict[str, Any]
) -> set[str]:
    course_by_cluster = {
        str(row["cluster_id"]): str(row["course_id"])
        for row in source["clusters"]
    }
    if len(course_by_cluster) != 100:
        raise ActionRouterCheckpointBuildError("source cluster count drifted")
    by_course: dict[str, list[str]] = {}
    for cluster_id, course_id in course_by_cluster.items():
        by_course.setdefault(course_id, []).append(cluster_id)
    allocation = {
        "operating-systems": 2,
        "computer-networking": 6,
        "data-structures": 6,
        "python-programming": 6,
    }
    selected: set[str] = set()
    for course_id, count in allocation.items():
        identifiers = by_course[course_id]
        identifiers.sort(
            key=lambda value: hashlib.sha256(
                f"action-router-control:{course_id}:{value}".encode()
            ).hexdigest()
        )
        selected.update(identifiers[:count])
    if len(selected) != 20:
        raise ActionRouterCheckpointBuildError("control cluster selection drifted")
    if len([row for row in cases if str(row["cluster_id"]) in selected]) != 100:
        raise ActionRouterCheckpointBuildError("control case count drifted")
    return selected


def _manifest(
    *,
    flow_id: str,
    evidence_gate: str,
    generator: str,
    action_router: str,
) -> dict[str, Any]:
    return SystemUnderTestManifestV1(
        flow_id=flow_id,
        adapter_version="v2-action-router",
        # The immutable manifest records the clean base revision. The exclusive
        # execution ledger binds the exact successor commit at run time.
        code_revision="2c18d9e",
        profile_sha256=_file_sha256(PROFILE),
        retriever=(
            "atomic-bm25-openai-small-rrf-v1@"
            "academic-factual-qa-action-router-confirmation-001"
        ),
        generator=generator,
        policy="grounded-assistant-approved-synthetic-policy-v1",
        evidence_gate=evidence_gate,
        model_bindings={
            "embedding": "text-embedding-3-small",
            "generator": "gpt-5.4-mini-2026-03-17",
            "response-contract": "extractive-boundary-output-v1",
            "action-router": action_router,
            "claim-validator": "contiguous-quote-atomic-claim-verifier-v1@1.0.0",
        },
        known_benchmark=False,
    ).model_dump(mode="json")


def build(*, metadata_verified_at: str | None = None) -> dict[Path, dict[str, Any]]:
    source = _load_hashed(dataset.SOURCE_PATH)
    public = _load_hashed(dataset.CASES_PATH)
    hidden = _load_hashed(dataset.GOLD_PATH)
    cases_rows = list(public["cases"])
    gold_rows = list(hidden["gold"])
    if (
        len(cases_rows) != 500
        or len(gold_rows) != 500
        or {row["case_id"] for row in cases_rows}
        != {row["case_id"] for row in gold_rows}
        or source.get("registered_region_count") != 300
        or source.get("source_range_disjoint_from_all_prior_development") is not True
        or source.get("private_data_used") is not False
    ):
        raise ActionRouterCheckpointBuildError("fresh source package drifted")
    selected = _control_clusters(cases_rows, source)
    control_rows = [
        row for row in cases_rows if str(row["cluster_id"]) in selected
    ]
    control_ids = {row["case_id"] for row in control_rows}
    control_gold_rows = [row for row in gold_rows if row["case_id"] in control_ids]
    candidate = _package(dataset_id=DATASET_ID, key="cases", rows=cases_rows)
    gold = _package(dataset_id=DATASET_ID, key="gold", rows=gold_rows)
    control = _package(
        dataset_id=CONTROL_DATASET_ID, key="cases", rows=control_rows
    )
    control_gold = _package(
        dataset_id=CONTROL_DATASET_ID, key="gold", rows=control_gold_rows
    )
    candidate_manifest = _manifest(
        flow_id="t0-action-router-targeted-atomic-candidate-001",
        evidence_gate="question-targeted-atomic-evidence-gate-v1",
        generator="openai-gpt-5.4-mini-question-targeted-atomic-v1",
        action_router="deterministic-tutor-action-router-v1",
    )
    control_manifest = _manifest(
        flow_id="t0-atomic-m2-structured-control-002",
        evidence_gate="atomic-structured-coverage-control-v1",
        generator="openai-gpt-5.4-mini-live-extractive-boundary",
        action_router="none-historical-control",
    )
    checked_at = (
        metadata_verified_at
        if metadata_verified_at is not None
        else METADATA_VERIFIED_AT
    )
    binding = _hashed(
        {
            "schema_version": 1,
            "binding_id": "academic-factual-qa-action-router-product-openai-binding-001",
            "instrument_id": INSTRUMENT_ID,
            "metadata_status": (
                "fresh" if checked_at is not None else "refresh-required"
            ),
            "verified_at": checked_at,
            "freshness_hours": 24,
            "official_sources": [
                "https://developers.openai.com/api/docs/models/gpt-5.4-mini",
                "https://developers.openai.com/api/docs/models/text-embedding-3-small",
                "https://developers.openai.com/api/reference/resources/responses/methods/create",
                "https://developers.openai.com/api/docs/guides/your-data",
            ],
            "data_controls": {
                "api_training_default": "not-used-unless-explicitly-opted-in",
                "abuse_monitoring_retention_days_max": 30,
                "responses_store": False,
                "responses_application_state_with_store_false": "none",
                "embeddings_application_state": "none",
            },
            "providers": {
                "embedding": {
                    "provider": "openai",
                    "provider_model": "text-embedding-3-small",
                    "dimensions": 1536,
                    "batch_size": 128,
                    "request_token_limit": 250000,
                    "input_price_usd_per_million": 0.02,
                    "maximum_transport_retries": 0,
                },
                "high-volume-generator": {
                    "provider": "openai",
                    "api_url": "https://api.openai.com/v1/responses",
                    "credential_environment_variable": "OPENAI_API_KEY",
                    "provider_model": "gpt-5.4-mini-2026-03-17",
                    "documented_revision": "gpt-5.4-mini-2026-03-17",
                    "reasoning_effort": "low",
                    "max_output_tokens": 600,
                    "timeout_seconds": 60,
                    "maximum_transport_retries": 0,
                    "pricing_usd_per_million_input_tokens": 0.75,
                    "pricing_usd_per_million_output_tokens": 4.5,
                    "request_store": False,
                },
            },
            "authorization": {
                "provider_execution_authorized": PROVIDER_EXECUTION_AUTHORIZED,
                "paid_execution_authorized": PAID_EXECUTION_AUTHORIZED,
                "final_execution_authorized": False,
            },
        }
    )
    instrument = _hashed(
        {
            "schema_version": 1,
            "instrument_id": INSTRUMENT_ID,
            "status": (
                "frozen-pending-execution"
                if PROVIDER_EXECUTION_AUTHORIZED and PAID_EXECUTION_AUTHORIZED
                else "reviewed-provider-unauthorized"
            ),
            "owner_issue": 127,
            "decision_id": "AFQC-110",
            "decision_question": (
                "Does deterministic action routing plus question-targeted atomic "
                "evidence/answer construction correct the valid atomic-M2 T0 failure?"
            ),
            "source_package": {
                "path": str(dataset.SOURCE_PATH.relative_to(ROOT)),
                "content_sha256": source["content_sha256"],
                "file_sha256": _file_sha256(dataset.SOURCE_PATH),
                "source_range_disjoint_from_all_prior_development": True,
                "source_family_disjoint_from_prior_development": False,
            },
            "dataset": {
                "candidate_cases_path": str(CASES.relative_to(ROOT)),
                "candidate_cases_sha256": candidate["content_sha256"],
                "candidate_gold_path": str(GOLD.relative_to(ROOT)),
                "candidate_gold_sha256": gold["content_sha256"],
                "control_cases_path": str(CONTROL_CASES.relative_to(ROOT)),
                "control_cases_sha256": control["content_sha256"],
                "control_gold_path": str(CONTROL_GOLD.relative_to(ROOT)),
                "control_gold_sha256": control_gold["content_sha256"],
                "candidate_case_count": 500,
                "control_case_count": 100,
            },
            "candidate_method": {
                "retriever": "atomic-bm25-openai-small-rrf-v1",
                "action_router": "deterministic-tutor-action-router-v1",
                "evidence_gate": "question-targeted-atomic-evidence-gate-v1",
                "generator": "openai-gpt-5.4-mini-question-targeted-atomic-v1",
                "deterministic_scoring_authoritative": True,
            },
            "control_method": {
                "retriever": "atomic-bm25-openai-small-rrf-v1",
                "action_router": "none-historical-control",
                "evidence_gate": "atomic-structured-coverage-control-v1",
                "generator": "openai-gpt-5.4-mini-live-extractive-boundary",
            },
            "provider_binding": {
                "path": str(BINDING.relative_to(ROOT)),
                "content_sha256": binding["content_sha256"],
            },
            "execution": {
                "stage_order": [
                    "embedding-materialization",
                    "candidate-500",
                    "control-100",
                    "hidden-gold-score",
                    "paired-decision",
                ],
                "maximum_embedding_calls": 20,
                "maximum_product_calls": 600,
                "maximum_total_calls": 620,
                "maximum_transport_retries": 0,
                "maximum_cost_usd": 8.0,
                "atomic_sqlite_checkpoints": True,
                "safe_resume": True,
                "hidden_gold_after_both_response_ledgers": True,
                "automatic_final_10000_progression": False,
            },
            "hard_gates": {
                "fully_grounded_factual_success_min": 0.95,
                "fully_grounded_source_family_lower_95_min": 0.93,
                "action_accuracy_overall_min": 0.95,
                "action_accuracy_answerable_min": 0.95,
                "boundary_action_accuracy_min": 0.98,
                "severe_unsupported_release_count_max": 0,
                "atomic_claim_precision_min": 0.98,
                "atomic_claim_recall_min": 0.95,
                "citation_precision_min": 0.98,
                "citation_recall_min": 0.95,
                "source_version_validity_min": 1.0,
                "canonical_all_evidence_at_3_min": 0.90,
                "evidence_recall_at_5_min": 0.95,
                "provider_completion_min": 0.995,
                "malformed_output_max": 0.005,
                "exact_duplicate_count_max": 0,
                "paired_supported_retention_delta_lower_95_min": -0.03,
                "paired_boundary_safety_not_worse": True,
            },
            "boundaries": {
                "private_data_used": False,
                "human_participants": 0,
                "visual_evaluation": "separate",
                "professor_fidelity": False,
                "final_10000_opened": False,
                "one_method_level_successor_only": True,
            },
        }
    )
    return {
        CASES: candidate,
        GOLD: gold,
        CONTROL_CASES: control,
        CONTROL_GOLD: control_gold,
        BINDING: binding,
        CANDIDATE_MANIFEST: candidate_manifest,
        CONTROL_MANIFEST: control_manifest,
        INSTRUMENT: instrument,
    }


def check() -> dict[str, Any]:
    expected = build(metadata_verified_at=METADATA_VERIFIED_AT)
    for path, payload in expected.items():
        if not path.is_file() or json.loads(path.read_text(encoding="utf-8")) != payload:
            raise ActionRouterCheckpointBuildError(f"checkpoint artifact drifted: {path.name}")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": (
            "frozen-pending-execution"
            if PROVIDER_EXECUTION_AUTHORIZED and PAID_EXECUTION_AUTHORIZED
            else "passed-build-only"
        ),
        "candidate_case_count": 500,
        "control_case_count": 100,
        "provider_execution_authorized": PROVIDER_EXECUTION_AUTHORIZED,
        "provider_calls": 0,
        "final_10000_opened": False,
    }


def _write(outputs: dict[Path, dict[str, Any]]) -> None:
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--metadata-verified-at")
    arguments = parser.parse_args()
    if arguments.write:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
        _write(build(metadata_verified_at=arguments.metadata_verified_at))
        result = {
            "instrument_id": INSTRUMENT_ID,
            "status": (
                "frozen-pending-execution"
                if PROVIDER_EXECUTION_AUTHORIZED and PAID_EXECUTION_AUTHORIZED
                else "completed-build-only"
            ),
            "provider_execution_authorized": PROVIDER_EXECUTION_AUTHORIZED,
            "provider_calls": 0,
        }
    else:
        result = check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
