#!/usr/bin/env python3
"""Build the finite atomic-M2 actual-product 500+100 checkpoint."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import run_academic_factual_qa_atomic_m2_confirmation as retrieval
from src.digital_twin.evaluation.factual_qa_contract import SystemUnderTestManifestV1
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "course-digital-twin-nonhuman-evaluation-program-002"
INSTRUMENT_ID = "academic-factual-qa-atomic-m2-product-checkpoint-001"
DATASET_ID = "academic-factual-qa-atomic-m2-product-development-001"
CONTROL_DATASET_ID = f"{DATASET_ID}-control"
SOURCE = ROOT / "research/05_evaluation/datasets/academic-factual-qa-atomic-m2-confirmation-001-sources.json"
UPSTREAM_CASES = ROOT / "research/05_evaluation/datasets/academic-factual-qa-atomic-m2-confirmation-001-cases.json"
UPSTREAM_GOLD = ROOT / "research/05_evaluation/datasets/academic-factual-qa-atomic-m2-confirmation-001-gold.json"
UPSTREAM_RESULT = ROOT / "research/05_evaluation/records/academic-factual-qa-atomic-m2-confirmation-001.json"
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
INSTRUMENT_ROOT = ROOT / "research/05_evaluation/instruments"
CASES = DATASET_ROOT / f"{DATASET_ID}-cases.json"
GOLD = DATASET_ROOT / f"{DATASET_ID}-gold.json"
CONTROL_CASES = DATASET_ROOT / f"{CONTROL_DATASET_ID}-cases.json"
CONTROL_GOLD = DATASET_ROOT / f"{CONTROL_DATASET_ID}-gold.json"
INSTRUMENT = INSTRUMENT_ROOT / "academic_factual_qa_atomic_m2_product_checkpoint_001.json"
BINDING = INSTRUMENT_ROOT / "academic_factual_qa_atomic_m2_product_openai_binding_001.json"
CANDIDATE_MANIFEST = INSTRUMENT_ROOT / "academic_factual_qa_atomic_m2_product_candidate_manifest_001.json"
CONTROL_MANIFEST = INSTRUMENT_ROOT / "academic_factual_qa_atomic_m2_product_control_manifest_001.json"
RETRIEVAL_RUNTIME = INSTRUMENT_ROOT / "academic_factual_qa_atomic_m2_product_retrieval_runtime_001.json"
PROFILE = ROOT / "research/05_evaluation/profiles/student-tutor-r1-openai-candidate-v1.json"
GENERATED = ROOT / "reports/generated/academic-factual-qa-atomic-m2-confirmation-001"
QUERY_CACHE = GENERATED / "query-vectors.sqlite3"
INDEX_ROOT = GENERATED / "indexes"


class AtomicProductBuildError(RuntimeError):
    """Raised when the product checkpoint cannot be frozen exactly."""


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AtomicProductBuildError(f"JSON root is not an object: {path.name}")
    expected = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != expected:
        raise AtomicProductBuildError(f"content hash drifted: {path.name}")
    return payload


def _hashed(payload: dict[str, Any]) -> dict[str, Any]:
    value = dict(payload)
    value["content_sha256"] = canonical_json_sha256(value)
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package(
    *, dataset_id: str, rows_key: str, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    return _hashed(
        {
            "schema_version": 1,
            "dataset_id": dataset_id,
            "split": "development",
            "case_count": len(rows),
            rows_key: rows,
        }
    )


def _control_cluster_ids(
    cases: list[dict[str, Any]], source: dict[str, Any]
) -> set[str]:
    case_cluster_ids = {str(row["cluster_id"]) for row in cases}
    course_by_cluster: dict[str, str] = {}
    for row in source["chunks"]:
        metadata = row["metadata"]
        cluster_id = str(metadata["parent_cluster_id"])
        course_id = str(metadata["course_id"])
        previous = course_by_cluster.setdefault(cluster_id, course_id)
        if previous != course_id:
            raise AtomicProductBuildError("one source cluster spans multiple courses")
    if set(course_by_cluster) != case_cluster_ids:
        raise AtomicProductBuildError("source and public cluster identities drifted")
    by_course: dict[str, list[str]] = {}
    for cluster_id, course_id in course_by_cluster.items():
        by_course.setdefault(course_id, []).append(cluster_id)
    if len(by_course) != 4 or min(map(len, by_course.values())) < 5:
        raise AtomicProductBuildError("atomic portfolio cannot support four-course control")
    selected: set[str] = set()
    for course_id, identifiers in sorted(by_course.items()):
        identifiers.sort(
            key=lambda value: hashlib.sha256(
                f"atomic-m2-product-control:{course_id}:{value}".encode()
            ).hexdigest()
        )
        selected.update(identifiers[:5])
    if len(selected) != 20:
        raise AtomicProductBuildError("control cluster selection drifted")
    return selected


def _manifest(
    *, flow_id: str, evidence_gate: str, code_revision: str
) -> dict[str, Any]:
    manifest = SystemUnderTestManifestV1(
        flow_id=flow_id,
        adapter_version="v1",
        code_revision=code_revision,
        profile_sha256=_file_sha256(PROFILE),
        retriever=(
            "atomic-bm25-openai-small-rrf-v1@"
            "academic-factual-qa-atomic-m2-confirmation-001"
        ),
        generator="openai-gpt-5.4-mini-live-extractive-boundary",
        policy="grounded-assistant-approved-synthetic-policy-v1",
        evidence_gate=evidence_gate,
        model_bindings={
            "embedding": "text-embedding-3-small",
            "embedding-cache": "academic-factual-qa-atomic-m2-confirmation-001",
            "generator": "gpt-5.4-mini-2026-03-17",
            "response-contract": "extractive-boundary-output-v1",
            "claim-validator": "contiguous-quote-atomic-claim-verifier-v1@1.0.0",
        },
        known_benchmark=False,
    )
    return manifest.model_dump(mode="json")


def build(*, verified_at: str | None = None) -> dict[Path, dict[str, Any]]:
    source = _load(SOURCE)
    upstream_cases = _load(UPSTREAM_CASES)
    upstream_gold = _load(UPSTREAM_GOLD)
    upstream_result = json.loads(UPSTREAM_RESULT.read_text(encoding="utf-8"))
    cases_rows = list(upstream_cases["cases"])
    gold_rows = list(upstream_gold["gold"])
    if (
        len(cases_rows) != 500
        or len(gold_rows) != 500
        or {row["case_id"] for row in cases_rows}
        != {row["case_id"] for row in gold_rows}
        or source.get("registered_region_count") != 300
        or source.get("private_data_used") is not False
    ):
        raise AtomicProductBuildError("upstream atomic package drifted")
    selected_clusters = _control_cluster_ids(cases_rows, source)
    control_rows = [
        row for row in cases_rows if str(row["cluster_id"]) in selected_clusters
    ]
    control_ids = {row["case_id"] for row in control_rows}
    control_gold_rows = [row for row in gold_rows if row["case_id"] in control_ids]
    if len(control_rows) != 100 or len(control_gold_rows) != 100:
        raise AtomicProductBuildError("paired control count drifted")
    candidate = _package(dataset_id=DATASET_ID, rows_key="cases", rows=cases_rows)
    gold = _package(dataset_id=DATASET_ID, rows_key="gold", rows=gold_rows)
    control = _package(
        dataset_id=CONTROL_DATASET_ID, rows_key="cases", rows=control_rows
    )
    control_gold = _package(
        dataset_id=CONTROL_DATASET_ID,
        rows_key="gold",
        rows=control_gold_rows,
    )
    # This names the selected retrieval baseline. The exact executable product
    # revision is bound separately by the exclusive checkpoint ledger.
    code_revision = str(upstream_result["code_revision"])
    candidate_manifest = _manifest(
        flow_id="t0-atomic-m2-structured-candidate-001",
        evidence_gate="atomic-structured-coverage-evidence-gate-v1",
        code_revision=code_revision,
    )
    control_manifest = _manifest(
        flow_id="t0-atomic-m2-any-hit-control-001",
        evidence_gate="atomic-any-hit-evidence-gate-v1",
        code_revision=code_revision,
    )
    chunks = [DocumentChunk.model_validate(row) for row in source["chunks"]]
    chunks_by_course: dict[str, list[DocumentChunk]] = {}
    for chunk in chunks:
        chunks_by_course.setdefault(str(chunk.metadata["course_id"]), []).append(chunk)
    retrieval_instrument = _load(retrieval.INSTRUMENT_PATH)
    runtime_courses: dict[str, Any] = {}
    store = retrieval.StreamingRetrievalIndexMaterializerV2(INDEX_ROOT)
    for course_id, course_chunks in sorted(chunks_by_course.items()):
        index_binding = retrieval._binding(  # noqa: SLF001
            retrieval_instrument, course_id=course_id, chunks=course_chunks
        )
        pointer_path = store.bindings_root / f"{index_binding.binding_sha256}.json"
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        if pointer.get("binding_sha256") != index_binding.binding_sha256:
            raise AtomicProductBuildError("atomic retrieval pointer drifted")
        runtime_courses[course_id] = {
            "binding": index_binding.model_dump(mode="json"),
            "artifact_id": pointer["artifact_id"],
        }
    retrieval_runtime = _hashed(
        {
            "schema_version": 1,
            "runtime_id": "academic-factual-qa-atomic-m2-product-retrieval-runtime-001",
            "program_id": PROGRAM_ID,
            "instrument_id": INSTRUMENT_ID,
            "source_package": {
                "path": str(SOURCE.relative_to(ROOT)),
                "file_sha256": _file_sha256(SOURCE),
                "content_sha256": source["content_sha256"],
            },
            "query_cache": {
                "path": str(QUERY_CACHE.relative_to(ROOT)),
                "file_sha256": _file_sha256(QUERY_CACHE),
                "model": "text-embedding-3-small",
                "dimensions": 1536,
                "vector_count": 500,
            },
            "index_root": str(INDEX_ROOT.relative_to(ROOT)),
            "courses": runtime_courses,
            "hidden_gold_path_present": False,
        }
    )
    checked_at = verified_at or datetime.now(UTC).replace(microsecond=0).isoformat()
    binding = _hashed(
        {
            "schema_version": 1,
            "binding_id": "academic-factual-qa-atomic-m2-product-openai-binding-001",
            "program_id": PROGRAM_ID,
            "instrument_id": INSTRUMENT_ID,
            "verified_at": checked_at,
            "freshness_hours": 24,
            "official_sources": [
                "https://developers.openai.com/api/docs/models/gpt-5.4-mini",
                "https://developers.openai.com/api/reference/resources/responses/methods/create",
            ],
            "providers": {
                "high-volume-generator": {
                    "binding_id": "atomic-m2-product-openai-mini-v1",
                    "provider": "openai",
                    "provider_display_name": "OpenAI",
                    "first_party_endpoint": True,
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
                    "service_tier": "default"
                }
            },
            "authorization": {
                "authorized_by_program": True,
                "provider_execution_authorized": True,
                "paid_execution_authorized": True,
                "final_execution_authorized": False
            }
        }
    )
    instrument = _hashed(
        {
            "schema_version": 1,
            "instrument_id": INSTRUMENT_ID,
            "program_id": PROGRAM_ID,
            "status": "frozen-authorized-by-program",
            "owner_issue": 127,
            "decision_id": "AFQC-108",
            "source_package": {
                "path": str(SOURCE.relative_to(ROOT)),
                "content_sha256": source["content_sha256"],
                "file_sha256": _file_sha256(SOURCE),
                "registered_region_count": 300
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
                "control_case_count": 100
            },
            "method": {
                "retriever": "atomic-bm25-openai-small-rrf-v1",
                "candidate_evidence_gate": "atomic-structured-coverage-evidence-gate-v1",
                "control_evidence_gate": "atomic-any-hit-evidence-gate-v1",
                "generator": "gpt-5.4-mini-2026-03-17",
                "deterministic_scoring_authoritative": True
            },
            "provider_binding": {
                "path": str(BINDING.relative_to(ROOT)),
                "content_sha256": binding["content_sha256"]
            },
            "retrieval_runtime": {
                "path": str(RETRIEVAL_RUNTIME.relative_to(ROOT)),
                "content_sha256": retrieval_runtime["content_sha256"]
            },
            "execution": {
                "stage_order": ["candidate-500", "control-100", "hidden-gold-score", "paired-decision"],
                "maximum_product_calls": 600,
                "maximum_transport_retries": 0,
                "maximum_cost_usd": 7.0,
                "atomic_sqlite_checkpoints": True,
                "safe_resume": True,
                "hidden_gold_after_both_response_ledgers": True,
                "automatic_progression_on_pass": True,
                "final_execution_authorized": False
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
                "paired_boundary_safety_not_worse": True
            },
            "boundaries": {
                "private_data_used": False,
                "human_participants": 0,
                "visual_evaluation": "separate",
                "professor_fidelity": False,
                "final_10000_opened": False
            }
        }
    )
    return {
        CASES: candidate,
        GOLD: gold,
        CONTROL_CASES: control,
        CONTROL_GOLD: control_gold,
        CANDIDATE_MANIFEST: candidate_manifest,
        CONTROL_MANIFEST: control_manifest,
        RETRIEVAL_RUNTIME: retrieval_runtime,
        BINDING: binding,
        INSTRUMENT: instrument,
    }


def write(*, verified_at: str | None = None) -> dict[str, Any]:
    outputs = build(verified_at=verified_at)
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary(outputs)


def check() -> dict[str, Any]:
    outputs = build(
        verified_at=_load(BINDING)["verified_at"] if BINDING.is_file() else None
    )
    for path, payload in outputs.items():
        if not path.is_file() or json.loads(path.read_text(encoding="utf-8")) != payload:
            raise AtomicProductBuildError(f"generated checkpoint drifted: {path.name}")
    return summary(outputs)


def summary(outputs: dict[Path, dict[str, Any]]) -> dict[str, Any]:
    instrument = outputs[INSTRUMENT]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "candidate_case_count": instrument["dataset"]["candidate_case_count"],
        "control_case_count": instrument["dataset"]["control_case_count"],
        "registered_region_count": instrument["source_package"]["registered_region_count"],
        "maximum_product_calls": 600,
        "maximum_cost_usd": 7.0,
        "provider_calls": 0,
        "private_data_used": False,
        "final_10000_opened": False
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if arguments.write:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "dataset_generation")
    result = write() if arguments.write else check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
