#!/usr/bin/env python3
"""Build the fresh, ambiguity-safe, source-disjoint grounding successor."""

# ruff: noqa: E402

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

from scripts import build_academic_factual_qa_atomic_m2_confirmation as atomic
from scripts import build_academic_factual_qa_semantic_target_successor as prior
from scripts import build_academic_factual_qa_source_semantic_atoms as previous
from scripts.build_academic_factual_qa_open_reference_validation import COURSE_IDS
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.evaluation.factual_qa_references import (
    SourceClusterV2,
    build_reference_cluster_rows,
    question_for_reference_target,
)
from src.digital_twin.evaluation.finite_retrieval_evaluation import (
    validate_exact_reference_matchability,
)
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.reference_uniqueness import (
    analyze_public_reference_uniqueness,
    derive_unique_public_cue,
    normalize_claim_class,
)
from src.digital_twin.grounding.semantic_evidence_atoms import (
    ATOM_VERSION,
    materialize_semantic_evidence_atoms,
)
from src.digital_twin.grounding.source_registration import registered_source_chunks
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


INSTRUMENT_ID = "academic-factual-qa-ambiguity-safe-successor-001"
PROGRAM_ID = "course-digital-twin-grounding-correction-003"
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
SOURCE_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-sources.json"
CASES_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-cases.json"
GOLD_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-gold.json"
TARGET_ALLOCATION: dict[str, dict[str, int]] = {
    "operating-systems": {"text": 25},
    "computer-networking": {
        "text": 18,
        "structured-code": 3,
        "structured-table": 4,
    },
    "data-structures": {
        "text": 16,
        "structured-equation": 9,
    },
    "python-programming": {"text": 15, "structured-code": 10},
}
MAX_CLUSTERS_PER_SOURCE_FAMILY = 1


class AmbiguitySafeSuccessorBuildError(RuntimeError):
    """Raised when the fresh successor violates a frozen invariant."""


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _load_hashed(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    observed = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != observed:
        raise AmbiguitySafeSuccessorBuildError(f"content hash drifted: {path.name}")
    return payload


def _prior_ranges() -> dict[tuple[str, str], list[tuple[int, int]]]:
    ranges = previous._prior_ranges()  # noqa: SLF001
    for row in _load_hashed(previous.SOURCE_PATH)["chunks"]:
        metadata = row["metadata"]
        ranges[(str(metadata["course_id"]), str(metadata["source_path"]))].append(
            (int(metadata["char_start"]), int(metadata["char_end"]))
        )
    return ranges


def _temporary_cluster(candidate: Any, identifier: str) -> SourceClusterV2:
    candidate = atomic._atomic_candidate(candidate)  # noqa: SLF001
    fourth = "multi-evidence" if candidate.modality == "text" else candidate.modality
    return prior._cluster(  # noqa: SLF001
        candidate,
        cluster_id=identifier,
        answerable_slices=[
            "direct-factual",
            "paraphrased",
            "definition-explanation",
            fourth,
        ],
        boundary_slice="no-evidence",
    )


def _cluster_cues(cluster: SourceClusterV2) -> list[tuple[str, ...]] | None:
    chunks = materialize_semantic_evidence_atoms(registered_source_chunks([cluster]))
    claims = [str(row.metadata["semantic_atom_claim"]) for row in chunks]
    output: list[tuple[str, ...]] = []
    for target in cluster.reference_targets:
        authoritative = _target_atom_claims(cluster, target, chunks)
        cues = tuple(
            derive_unique_public_cue(claim, claims) or ""
            for claim in authoritative
        )
        if not all(cues):
            return None
        output.append(cues)
    return output


def _target_atom_claims(
    cluster: SourceClusterV2,
    target: Any,
    chunks: list[DocumentChunk],
) -> list[str]:
    output = []
    for span in target.evidence_spans:
        expected = (
            cluster.char_start + span.relative_char_start,
            cluster.char_start + span.relative_char_end,
        )
        matches = [
            row
            for row in chunks
            if row.metadata.get("parent_cluster_id") == cluster.cluster_id
            and (
                int(row.metadata["char_start"]),
                int(row.metadata["char_end"]),
            )
            == expected
        ]
        if len(matches) != 1:
            raise AmbiguitySafeSuccessorBuildError(
                f"target-to-atom mapping is not unique: {cluster.cluster_id}"
            )
        output.append(str(matches[0].metadata["semantic_atom_claim"]))
    return output


def _select_candidates() -> tuple[list[Any], dict[str, Any]]:
    ranges = _prior_ranges()
    inventory = prior.build_candidate_inventory()
    inventory["operating-systems"] = prior._think_os_candidates()  # noqa: SLF001
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
                and not prior._overlaps(candidate, ranges)  # noqa: SLF001
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
                        if family_counts[prior._candidate_family_id(candidate)]  # noqa: SLF001
                        < MAX_CLUSTERS_PER_SOURCE_FAMILY
                        and (
                            candidate.course_id,
                            candidate.section.path,
                            candidate.section.heading,
                        )
                        not in selected_scopes
                        and not prior._overlaps(candidate, selected_ranges)  # noqa: SLF001
                    ),
                    key=lambda candidate: (
                        candidate.end - candidate.start,
                        candidate.identity,
                    ),
                )
                chosen = None
                for candidate in options:
                    probe = _temporary_cluster(
                        candidate,
                        f"ambiguity-probe-{course_id}-{modality}-{selection_index}",
                    )
                    if _cluster_cues(probe) is None:
                        rejected_non_unique[f"{course_id}:{modality}"] += 1
                        continue
                    chosen = candidate
                    break
                if chosen is None:
                    raise AmbiguitySafeSuccessorBuildError(
                        f"fresh ambiguity-safe allocation shortfall {course_id}:{modality}"
                    )
                selected.append(chosen)
                family_counts[prior._candidate_family_id(chosen)] += 1  # noqa: SLF001
                selected_scopes.add(
                    (chosen.course_id, chosen.section.path, chosen.section.heading)
                )
                selected_ranges[(chosen.course_id, chosen.section.path)].append(
                    prior._absolute_range(chosen)  # noqa: SLF001
                )

    selected.sort(key=lambda row: row.identity)
    expected = {
        (course_id, modality): count
        for course_id, allocation in TARGET_ALLOCATION.items()
        for modality, count in allocation.items()
    }
    observed = Counter((row.course_id, row.modality) for row in selected)
    if len(selected) != 100 or len({row.identity for row in selected}) != 100:
        raise AmbiguitySafeSuccessorBuildError("successor requires 100 clusters")
    if dict(observed) != expected:
        raise AmbiguitySafeSuccessorBuildError("course/modality allocation drifted")
    return selected, {
        "eligible_candidate_counts": eligible_counts,
        "rejected_non_unique_candidate_attempts": dict(rejected_non_unique),
        "selected_source_family_count": len(family_counts),
        "maximum_clusters_per_source_family": max(family_counts.values()),
    }


def _build_clusters(candidates: list[Any]) -> list[SourceClusterV2]:
    boundaries = ("no-evidence", "cross-course", "ambiguity", "academic-integrity")
    clusters = []
    for index, candidate in enumerate(candidates, start=1):
        cluster = _temporary_cluster(
            candidate,
            f"ambiguity-safe-dev-{index:04d}",
        )
        clusters.append(
            cluster.model_copy(
                update={
                    "boundary_slice": boundaries[(index - 1) % len(boundaries)],
                    "author_family": "deterministic-ambiguity-safe-question-planner-v1",
                    "verifier_family": "deterministic-reference-uniqueness-auditor-v1",
                }
            )
        )
    return clusters


def _build_rows(
    clusters: list[SourceClusterV2], chunks: list[DocumentChunk]
) -> tuple[list[EvaluationCaseV1], list[EvaluationGoldV1], dict[str, int]]:
    cases: list[EvaluationCaseV1] = []
    gold: list[EvaluationGoldV1] = []
    uniqueness_counts: Counter[str] = Counter()
    for cluster in clusters:
        cluster_cases, cluster_gold = build_reference_cluster_rows(
            cluster,
            course_ids=COURSE_IDS,
            source_derived_region_ids=True,
            public_source_scope=True,
        )
        scoped_claims = [
            str(row.metadata["semantic_atom_claim"])
            for row in chunks
            if row.metadata.get("source_path") == cluster.source_path
            and row.metadata.get("title") == cluster.section_heading
        ]
        for index, target in enumerate(cluster.reference_targets):
            authoritative = _target_atom_claims(cluster, target, chunks)
            cues = tuple(
                derive_unique_public_cue(claim, scoped_claims) or ""
                for claim in authoritative
            )
            if not all(cues):
                raise AmbiguitySafeSuccessorBuildError(
                    f"accepted cluster lost a unique public cue: {cluster.cluster_id}"
                )
            question = question_for_reference_target(
                cluster,
                target,
                public_source_scope=True,
                cues=cues,
            )
            observed = analyze_public_reference_uniqueness(question, chunks)
            if observed.status not in {"unique", "alternate-valid"}:
                raise AmbiguitySafeSuccessorBuildError(
                    f"non-unique sealed question {cluster_cases[index].case_id}: "
                    f"{observed.status}"
                )
            expected_classes = {
                normalize_claim_class(value) for value in authoritative
            }
            observed_classes = {
                value
                for result in observed.targets
                for value in result.canonical_claim_classes
            }
            if not expected_classes.issubset(observed_classes):
                raise AmbiguitySafeSuccessorBuildError(
                    f"question does not resolve to its canonical claim: "
                    f"{cluster_cases[index].case_id}"
                )
            cluster_cases[index] = cluster_cases[index].model_copy(
                update={
                    "question": question,
                    "author_family": "deterministic-ambiguity-safe-question-planner-v1",
                }
            )
            uniqueness_counts[observed.status] += 1
        cases.extend(cluster_cases)
        gold.extend(cluster_gold)
    return cases, gold, dict(uniqueness_counts)


def _package(*, key: str, rows: list[dict[str, Any]], source_hash: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "program_id": PROGRAM_ID,
        "instrument_id": INSTRUMENT_ID,
        "source_plan_sha256": source_hash,
        "case_count": 500,
        key: rows,
        "provider_calls": 0,
        "private_data_used": False,
        "known_benchmark": False,
        "final_split_opened": False,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    return payload


def build_packages() -> dict[str, Any]:
    candidates, selection = _select_candidates()
    clusters = _build_clusters(candidates)
    chunks = materialize_semantic_evidence_atoms(registered_source_chunks(clusters))
    cases, gold, uniqueness = _build_rows(clusters, chunks)
    cases.sort(key=lambda row: row.case_id)
    gold.sort(key=lambda row: row.case_id)
    if len(cases) != 500 or len(gold) != 500:
        raise AmbiguitySafeSuccessorBuildError("successor requires 500 cases")
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise AmbiguitySafeSuccessorBuildError("public and hidden-gold IDs differ")
    normalized = [normalize_question(row.question) for row in cases]
    if len(normalized) != len(set(normalized)):
        raise AmbiguitySafeSuccessorBuildError("normalized questions are duplicated")
    atomic._validate_non_overlapping_atoms(chunks)  # noqa: SLF001
    atomic._validate_atomic_cluster_cardinality(chunks)  # noqa: SLF001
    mapping = atomic._validate_unique_answer_atom_mapping(gold, chunks)  # noqa: SLF001
    relations = previous._validate_atom_relations(chunks)  # noqa: SLF001
    matchability = validate_exact_reference_matchability(gold=gold, chunks=chunks)
    source_payload: dict[str, Any] = {
        "schema_version": 1,
        "program_id": PROGRAM_ID,
        "instrument_id": INSTRUMENT_ID,
        "construction_method": "fresh-source-scoped-ambiguity-safe-semantic-atoms-v1",
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
        "source_range_disjoint_from_all_prior_development": True,
        "selection_diagnostics": selection,
        "relation_diagnostics": relations,
        "reference_uniqueness_diagnostics": uniqueness,
        "authoritative_evidence_unit": "source-side-self-contained-semantic-atom",
        "semantic_atom_version": ATOM_VERSION,
        "public_source_and_section_scope_required": True,
        "non_unique_candidate_clusters_rejected": True,
        "alternate_regions_require_one_canonical_claim_class": True,
        "normalized_questions_unique": True,
        "public_sources_only": True,
        "provider_calls": 0,
        "private_data_read": False,
        "private_data_used": False,
        "final_split_opened": False,
    }
    source_payload["content_sha256"] = canonical_json_sha256(source_payload)
    source_hash = str(source_payload["content_sha256"])
    packages = {
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
    }
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "cluster_count": 100,
        "case_count": 500,
        "registered_region_count": len(chunks),
        "matchability": matchability,
        "answer_atom_mapping": mapping,
        "reference_uniqueness": uniqueness,
        "source_range_disjoint_from_all_prior_development": True,
        "provider_calls": 0,
        "final_split_opened": False,
        "packages": packages,
    }


def build_byte_stable_packages() -> dict[str, Any]:
    first = build_packages()
    second = build_packages()
    for key in ("source", "cases", "gold"):
        if _json_bytes(first["packages"][key]) != _json_bytes(
            second["packages"][key]
        ):
            raise AmbiguitySafeSuccessorBuildError(f"{key} package is not byte stable")
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
        raise AmbiguitySafeSuccessorBuildError(
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
