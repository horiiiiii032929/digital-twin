#!/usr/bin/env python3
"""Build the fresh, source-contract-aligned 500-case grounding successor."""

# ruff: noqa: E402, SLF001

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_academic_factual_qa_ambiguity_safe_successor as base
from scripts import build_academic_factual_qa_atomic_m2_confirmation as atomic
from scripts import build_academic_factual_qa_semantic_target_successor as prior
from scripts import build_cross_engine_sealed_confirmation_010 as sealed
from scripts import build_governed_full_autonomy_v2_1_cross_engine_evaluation_010 as program_010
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.evaluation.finite_retrieval_evaluation import (
    validate_exact_reference_matchability,
)
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.semantic_evidence_atoms import (
    ATOM_VERSION,
    materialize_semantic_evidence_atoms,
)
from src.digital_twin.grounding.source_registration import registered_source_chunks
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


INSTRUMENT_ID = "governed-full-autonomy-v2-1-grounding-successor-011"
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
SOURCE_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-sources.json"
CASES_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-cases.json"
GOLD_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-gold.json"
TARGET_ALLOCATION: dict[str, dict[str, int]] = {
    "operating-systems": {"text": 25},
    "computer-networking": {
        "text": 20,
        "structured-code": 2,
        "structured-table": 3,
    },
    "data-structures": {"text": 25},
    "python-programming": {"text": 15, "structured-code": 10},
}
MAX_CLUSTERS_PER_SOURCE_FAMILY = 5
CANDIDATE_ARCHITECTURE_ID = "ambiguity-safe-source-semantic-evidence-atoms-v2"
CONTROL_ARCHITECTURE_ID = "source-semantic-evidence-atoms-v1"


class GroundingSuccessorBuildError(RuntimeError):
    """Raised when the prospective successor package violates its contract."""


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _prior_ranges() -> dict[tuple[str, str], list[tuple[int, int]]]:
    ranges = sealed._prior_ranges()
    _cases, _gold, chunks = program_010.sealed_inputs()
    for chunk in chunks:
        metadata = chunk.metadata
        ranges[(str(metadata["course_id"]), str(metadata["source_path"]))].append(
            (int(metadata["char_start"]), int(metadata["char_end"]))
        )
    return ranges


def _select_candidates() -> tuple[list[Any], dict[str, Any]]:
    ranges = _prior_ranges()
    inventory = prior.build_candidate_inventory()
    inventory["operating-systems"] = prior._think_os_candidates()
    selected: list[Any] = []
    selected_ranges: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    family_counts: Counter[str] = Counter()
    selected_scopes: set[tuple[str, str, str]] = set()
    rejected_non_unique: Counter[str] = Counter()
    eligible_counts: dict[str, int] = {}

    for course_id, allocation in TARGET_ALLOCATION.items():
        eligible_by_modality = {
            modality: [
                candidate
                for candidate in inventory[course_id]
                if candidate.modality == modality
                and not prior._overlaps(candidate, ranges)
            ]
            for modality in allocation
        }
        for modality, rows in eligible_by_modality.items():
            eligible_counts[f"{course_id}:{modality}"] = len(rows)
        for modality in sorted(
            allocation,
            key=lambda value: (
                len(eligible_by_modality[value]) / allocation[value],
                value,
            ),
        ):
            for selection_index in range(allocation[modality]):
                options = sorted(
                    (
                        candidate
                        for candidate in eligible_by_modality[modality]
                        if family_counts[prior._candidate_family_id(candidate)]
                        < MAX_CLUSTERS_PER_SOURCE_FAMILY
                        and (
                            candidate.course_id,
                            candidate.section.path,
                            candidate.section.heading,
                        )
                        not in selected_scopes
                        and not prior._overlaps(candidate, selected_ranges)
                    ),
                    key=lambda candidate: (
                        candidate.end - candidate.start,
                        candidate.identity,
                    ),
                )
                chosen = None
                for candidate in options:
                    probe = base._temporary_cluster(
                        candidate,
                        f"grounding-successor-probe-{course_id}-{modality}-{selection_index}",
                    )
                    if base._cluster_cues(probe) is None:
                        rejected_non_unique[f"{course_id}:{modality}"] += 1
                        continue
                    chosen = candidate
                    break
                if chosen is None:
                    raise GroundingSuccessorBuildError(
                        f"fresh allocation shortfall {course_id}:{modality}"
                    )
                selected.append(chosen)
                family_counts[prior._candidate_family_id(chosen)] += 1
                selected_scopes.add(
                    (chosen.course_id, chosen.section.path, chosen.section.heading)
                )
                selected_ranges[(chosen.course_id, chosen.section.path)].append(
                    prior._absolute_range(chosen)
                )

    selected.sort(key=lambda row: row.identity)
    expected = {
        (course_id, modality): count
        for course_id, allocation in TARGET_ALLOCATION.items()
        for modality, count in allocation.items()
    }
    observed = Counter((row.course_id, row.modality) for row in selected)
    if len(selected) != 100 or len({row.identity for row in selected}) != 100:
        raise GroundingSuccessorBuildError("successor requires 100 clusters")
    if dict(observed) != expected:
        raise GroundingSuccessorBuildError("course/modality allocation drifted")
    return selected, {
        "eligible_candidate_counts": eligible_counts,
        "rejected_non_unique_candidate_attempts": dict(rejected_non_unique),
        "selected_source_family_count": len(family_counts),
        "maximum_clusters_per_source_family": max(family_counts.values()),
    }


def _build_clusters(candidates: list[Any]) -> list[Any]:
    boundaries = ("no-evidence", "cross-course", "ambiguity", "academic-integrity")
    clusters = []
    for index, candidate in enumerate(candidates, start=1):
        cluster = base._temporary_cluster(
            candidate,
            f"grounding-successor-011-{index:04d}",
        )
        clusters.append(
            cluster.model_copy(
                update={
                    "boundary_slice": boundaries[(index - 1) % len(boundaries)],
                    "author_family": "deterministic-source-contract-question-planner-v1",
                    "verifier_family": "deterministic-reference-uniqueness-auditor-v1",
                }
            )
        )
    return clusters


def _canonicalize_gold(
    rows: list[EvaluationGoldV1], chunks: list[DocumentChunk]
) -> list[EvaluationGoldV1]:
    by_region = {chunk.region_id: chunk for chunk in chunks}
    if None in by_region or len(by_region) != len(chunks):
        raise GroundingSuccessorBuildError("source regions must be unique and non-null")
    output: list[EvaluationGoldV1] = []
    for row in rows:
        if row.expected_action.value != "answer":
            if row.claims or not row.boundary_reason:
                raise GroundingSuccessorBuildError(
                    f"boundary case carries source truth or lacks a reason: {row.case_id}"
                )
            output.append(row)
            continue
        claims = []
        for claim in row.claims:
            if len(claim.evidence_refs) != 1:
                raise GroundingSuccessorBuildError(
                    f"claim must bind exactly one source atom: {row.case_id}"
                )
            chunk = by_region.get(claim.evidence_refs[0].region_id)
            if chunk is None:
                raise GroundingSuccessorBuildError(
                    f"claim source region is missing: {row.case_id}"
                )
            if chunk.metadata.get("semantic_atom_version") != ATOM_VERSION:
                raise GroundingSuccessorBuildError(
                    f"claim source atom version drifted: {row.case_id}"
                )
            answer_span = str(chunk.metadata.get("semantic_atom_claim", "")).strip()
            if not answer_span:
                raise GroundingSuccessorBuildError(
                    f"claim source atom is blank: {row.case_id}"
                )
            claims.append(claim.model_copy(update={"answer_span": answer_span}))
        if not claims:
            raise GroundingSuccessorBuildError(
                f"answerable case has no source claim: {row.case_id}"
            )
        output.append(
            row.model_copy(
                update={
                    "claims": claims,
                    "canonical_answer": " ".join(
                        claim.answer_span for claim in claims
                    ),
                }
            )
        )
    return output


def _package(
    *, key: str, rows: list[dict[str, Any]], source_hash: str
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "program_id": INSTRUMENT_ID,
        "instrument_id": INSTRUMENT_ID,
        "source_plan_sha256": source_hash,
        "case_count": 500,
        key: rows,
        "provider_calls": 0,
        "private_data_used": False,
        "known_benchmark": False,
        "fresh_source_ranges": True,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    return payload


def build_packages() -> dict[str, Any]:
    candidates, selection = _select_candidates()
    clusters = _build_clusters(candidates)
    chunks = materialize_semantic_evidence_atoms(registered_source_chunks(clusters))
    cases, original_gold, uniqueness = base._build_rows(clusters, chunks)
    gold = _canonicalize_gold(original_gold, chunks)
    cases.sort(key=lambda row: row.case_id)
    gold.sort(key=lambda row: row.case_id)
    if len(cases) != 500 or len(gold) != 500:
        raise GroundingSuccessorBuildError("successor requires 500 cases")
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise GroundingSuccessorBuildError("public and hidden-gold IDs differ")
    normalized = [normalize_question(row.question) for row in cases]
    if len(normalized) != len(set(normalized)):
        raise GroundingSuccessorBuildError("normalized questions are duplicated")
    atomic._validate_non_overlapping_atoms(chunks)
    atomic._validate_atomic_cluster_cardinality(chunks)
    mapping = atomic._validate_unique_answer_atom_mapping(gold, chunks)
    relations = base.previous._validate_atom_relations(chunks)
    matchability = validate_exact_reference_matchability(gold=gold, chunks=chunks)
    source_payload: dict[str, Any] = {
        "schema_version": 1,
        "program_id": INSTRUMENT_ID,
        "instrument_id": INSTRUMENT_ID,
        "construction_method": "fresh-source-contract-aligned-semantic-atoms-v1",
        "split": "development-confirmation",
        "cluster_count": 100,
        "case_count": 500,
        "registered_region_count": len(chunks),
        "clusters": [
            {
                "cluster_id": row.cluster_id,
                "course_id": row.course_id,
                "source_family_id": row.source_family_id,
                "source_artifact_id": row.source_artifact_id,
                "source_version": row.source_version,
                "source_sha256": row.source_sha256,
                "source_modality": row.source_modality,
                "source_path": row.source_path,
                "license_spdx": row.license_spdx,
                "repository_url": row.repository_url,
                "repository_commit": row.repository_commit,
            }
            for row in clusters
        ],
        "chunks": [row.model_dump(mode="json") for row in chunks],
        "target_allocation": TARGET_ALLOCATION,
        "source_range_disjoint_from_prior_development_and_sealed_010": True,
        "selection_diagnostics": selection,
        "relation_diagnostics": relations,
        "reference_uniqueness_diagnostics": uniqueness,
        "authoritative_evidence_unit": "source-side-self-contained-semantic-atom",
        "canonical_answer_contract": "semantic_atom_claim",
        "semantic_atom_version": ATOM_VERSION,
        "public_source_and_section_scope_required": True,
        "normalized_questions_unique": True,
        "public_sources_only": True,
        "provider_calls": 0,
        "private_data_read": False,
        "private_data_used": False,
    }
    source_payload["content_sha256"] = canonical_json_sha256(source_payload)
    source_hash = str(source_payload["content_sha256"])
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "cluster_count": 100,
        "case_count": 500,
        "registered_region_count": len(chunks),
        "matchability": matchability,
        "answer_atom_mapping": mapping,
        "reference_uniqueness": uniqueness,
        "source_range_disjoint_from_prior_development_and_sealed_010": True,
        "provider_calls": 0,
        "packages": {
            "source": source_payload,
            "cases": _package(
                key="cases",
                rows=[row.model_dump(mode="json") for row in cases],
                source_hash=source_hash,
            ),
            "gold": _package(
                key="gold",
                rows=[row.model_dump(mode="json") for row in gold],
                source_hash=source_hash,
            ),
        },
    }


def load_inputs() -> tuple[
    list[EvaluationCaseV1], list[EvaluationGoldV1], list[DocumentChunk]
]:
    cases_payload = base._load_hashed(CASES_PATH)
    gold_payload = base._load_hashed(GOLD_PATH)
    source_payload = base._load_hashed(SOURCE_PATH)
    cases = [EvaluationCaseV1.model_validate(row) for row in cases_payload["cases"]]
    gold = [EvaluationGoldV1.model_validate(row) for row in gold_payload["gold"]]
    chunks = [DocumentChunk.model_validate(row) for row in source_payload["chunks"]]
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise GroundingSuccessorBuildError("persisted public and gold IDs differ")
    return cases, gold, chunks


def control_case_ids(cases: list[EvaluationCaseV1]) -> list[str]:
    by_cluster: dict[str, list[EvaluationCaseV1]] = defaultdict(list)
    for case in cases:
        by_cluster[case.cluster_id].append(case)
    by_primary_course: dict[str, list[str]] = defaultdict(list)
    for cluster_id, rows in sorted(by_cluster.items()):
        counts = Counter(row.course_id for row in rows)
        primary_course = min(counts, key=lambda value: (-counts[value], value))
        by_primary_course[primary_course].append(cluster_id)
    selected_clusters = {
        cluster_id
        for course_id in sorted(by_primary_course)
        for cluster_id in sorted(by_primary_course[course_id])[:5]
    }
    selected = [
        row.case_id
        for row in sorted(cases, key=lambda value: value.case_id)
        if row.cluster_id in selected_clusters
    ]
    if len(selected) != 100:
        raise GroundingSuccessorBuildError("control requires 20 complete clusters")
    return selected


def rankings(*, control: bool) -> dict[str, Any]:
    cases, _gold, chunks = load_inputs()
    if control:
        selected = set(control_case_ids(cases))
        cases = [row for row in cases if row.case_id in selected]
    payload = program_010._rankings_for(
        cases,
        chunks,
        architecture_id=(
            CONTROL_ARCHITECTURE_ID if control else CANDIDATE_ARCHITECTURE_ID
        ),
    )
    payload["program_id"] = INSTRUMENT_ID
    payload["content_sha256"] = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    return payload


def build_byte_stable_packages() -> dict[str, Any]:
    first = build_packages()
    second = build_packages()
    for key in ("source", "cases", "gold"):
        if _json_bytes(first["packages"][key]) != _json_bytes(
            second["packages"][key]
        ):
            raise GroundingSuccessorBuildError(f"{key} package is not byte stable")
    first["byte_stable"] = True
    return first


def _write_exclusive(packages: dict[str, dict[str, Any]]) -> None:
    outputs = {
        SOURCE_PATH: packages["source"],
        CASES_PATH: packages["cases"],
        GOLD_PATH: packages["gold"],
    }
    existing = [path.name for path in outputs if path.exists()]
    if existing:
        raise GroundingSuccessorBuildError(
            "exclusive output already exists: " + ", ".join(sorted(existing))
        )
    created: list[Path] = []
    try:
        for path, payload in outputs.items():
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            created.append(path)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(_json_bytes(payload))
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--write", action="store_true")
    arguments = parser.parse_args()
    result = build_byte_stable_packages()
    if arguments.write:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "dataset_generation")
        _write_exclusive(result["packages"])
        result["status"] = "completed-build-only"
    result.pop("packages")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
