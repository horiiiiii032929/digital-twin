#!/usr/bin/env python3
"""Build the fresh atomic-evidence package for the finite M2 successor."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_academic_factual_qa_open_reference_validation import (  # noqa: E402
    COURSE_IDS,
)
from scripts.build_academic_factual_qa_open_source_plan_v2 import (  # noqa: E402
    Candidate,
    _cluster,
    build_candidate_inventory,
    build_source_plan,
)
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationAction,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_dataset import (  # noqa: E402
    normalize_question,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.factual_qa_references import (  # noqa: E402
    SourceClusterV2,
    build_reference_cluster_rows,
    extract_structured_atoms,
)
from src.digital_twin.evaluation.finite_retrieval_evaluation import (  # noqa: E402
    validate_exact_reference_matchability,
)
from src.digital_twin.grounding.models import DocumentChunk  # noqa: E402
from src.digital_twin.grounding.source_registration import (  # noqa: E402
    registered_source_chunks,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


PROGRAM_ID = "course-digital-twin-nonhuman-evaluation-program-002"
INSTRUMENT_ID = "academic-factual-qa-atomic-m2-confirmation-001"
AFQC_103_SOURCE_PATH = (
    ROOT
    / "research/05_evaluation/datasets/"
    "academic-factual-qa-source-aligned-confirmation-001-sources.json"
)
TARGET_ALLOCATION: dict[str, dict[str, int]] = {
    "operating-systems": {
        "text": 1,
        "structured-code": 4,
        "structured-table": 3,
    },
    "computer-networking": {
        "text": 20,
        "structured-code": 4,
        "structured-table": 4,
    },
    "data-structures": {
        "text": 20,
        "structured-equation": 10,
        "structured-table": 4,
    },
    "python-programming": {
        "text": 10,
        "structured-code": 18,
        "structured-equation": 2,
    },
}
MAX_CLUSTERS_PER_SOURCE_FAMILY = 5
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
SOURCE_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-sources.json"
CASES_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-cases.json"
GOLD_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-gold.json"


class AtomicM2BuildError(RuntimeError):
    """Raised when the fresh atomic package violates a frozen invariant."""


def _candidate_family_id(candidate: Candidate) -> str:
    value = f"{candidate.course_id}:{candidate.section.family_key}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _absolute_range(candidate: Candidate) -> tuple[int, int]:
    return (
        candidate.section.start + candidate.start,
        candidate.section.start + candidate.end,
    )


def _load_afqc_103_source_package() -> dict[str, Any]:
    payload = json.loads(AFQC_103_SOURCE_PATH.read_text(encoding="utf-8"))
    if payload.get("instrument_id") != "academic-factual-qa-source-aligned-confirmation-001":
        raise AtomicM2BuildError("AFQC-103 source package identity drifted")
    observed = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != observed:
        raise AtomicM2BuildError("AFQC-103 source package hash drifted")
    return payload


def excluded_source_families() -> dict[str, set[str]]:
    historical = {
        str(row["source_family_id"]) for row in build_source_plan()["clusters"]
    }
    afqc_103 = {
        str(row["source_family_id"])
        for row in _load_afqc_103_source_package()["clusters"]
    }
    return {
        "historical_build_source_plan": historical,
        "afqc_103_source_package": afqc_103,
    }


def _overlaps_selected(
    candidate: Candidate,
    ranges: dict[tuple[str, str], list[tuple[int, int]]],
) -> bool:
    start, end = _absolute_range(candidate)
    return any(
        max(start, left) < min(end, right)
        for left, right in ranges[(candidate.course_id, candidate.section.path)]
    )


def _select_candidates() -> tuple[list[Candidate], dict[str, set[str]]]:
    excluded = excluded_source_families()
    excluded_union = set().union(*excluded.values())
    inventory = build_candidate_inventory()
    selected: list[Candidate] = []
    selected_ranges: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    family_counts: Counter[str] = Counter()

    for course_id, allocation in TARGET_ALLOCATION.items():
        eligible_by_modality = {
            modality: [
                candidate
                for candidate in inventory[course_id]
                if candidate.modality == modality
                and _candidate_family_id(candidate) not in excluded_union
            ]
            for modality in allocation
        }
        modality_order = sorted(
            allocation,
            key=lambda modality: (
                len(eligible_by_modality[modality]) / allocation[modality],
                modality,
            ),
        )
        for modality in modality_order:
            for _ in range(allocation[modality]):
                options = [
                    candidate
                    for candidate in eligible_by_modality[modality]
                    if family_counts[_candidate_family_id(candidate)]
                    < MAX_CLUSTERS_PER_SOURCE_FAMILY
                    and not _overlaps_selected(candidate, selected_ranges)
                ]
                options.sort(
                    key=lambda candidate: (
                        family_counts[_candidate_family_id(candidate)],
                        candidate.end - candidate.start,
                        candidate.identity,
                    )
                )
                if not options:
                    raise AtomicM2BuildError(
                        f"fresh allocation shortfall {course_id}:{modality}"
                    )
                chosen = options[0]
                selected.append(chosen)
                family_counts[_candidate_family_id(chosen)] += 1
                selected_ranges[(chosen.course_id, chosen.section.path)].append(
                    _absolute_range(chosen)
                )

    selected.sort(key=lambda candidate: candidate.identity)
    observed = Counter((row.course_id, row.modality) for row in selected)
    expected = {
        (course_id, modality): count
        for course_id, rows in TARGET_ALLOCATION.items()
        for modality, count in rows.items()
    }
    if len(selected) != 100 or len({row.identity for row in selected}) != 100:
        raise AtomicM2BuildError("atomic M2 confirmation is not 100 unique clusters")
    if dict(observed) != expected:
        raise AtomicM2BuildError("atomic M2 course/modality allocation drifted")
    if any(_candidate_family_id(row) in excluded_union for row in selected):
        raise AtomicM2BuildError("atomic M2 source-family exclusion drifted")
    return selected, excluded


def _atomic_candidate(candidate: Candidate) -> Candidate:
    if candidate.modality == "text":
        return candidate

    structured_parent = candidate.target_regions[-1][0]
    atoms = extract_structured_atoms(structured_parent)
    if not atoms:
        raise AtomicM2BuildError(
            f"structured candidate has no authoritative atom: {candidate.identity}"
        )
    first_three = list(candidate.target_regions[:3])
    if not any(
        region.modality == candidate.modality
        for group in first_three
        for region in group
    ):
        first_three[-1] = (atoms[0],)
    return Candidate(
        course_id=candidate.course_id,
        section=candidate.section,
        modality=candidate.modality,
        start=candidate.start,
        end=candidate.end,
        target_regions=(*first_three, (atoms[0],)),
    )


def _build_clusters(candidates: list[Candidate]) -> list[SourceClusterV2]:
    clusters: list[SourceClusterV2] = []
    for index, candidate in enumerate(candidates, start=1):
        atomic = _atomic_candidate(candidate)
        fourth_slice = "multi-evidence" if atomic.modality == "text" else atomic.modality
        clusters.append(
            _cluster(
                atomic,
                cluster_id=f"academic-atomic-m2-dev-{index:04d}",
                slices=(
                    [
                        "direct-factual",
                        "paraphrased",
                        "definition-explanation",
                        fourth_slice,
                    ],
                    ("no-evidence", "cross-course", "ambiguity", "academic-integrity")[
                        (index - 1) % 4
                    ],
                ),
            )
        )
    return clusters


def _make_questions_unique(cases: list[Any], clusters: list[SourceClusterV2]) -> None:
    cluster_by_id = {row.cluster_id: row for row in clusters}
    duplicate_groups: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(cases):
        duplicate_groups[normalize_question(row.question)].append(index)
    for indices in duplicate_groups.values():
        if len(indices) < 2:
            continue
        for index in indices:
            row = cases[index]
            cluster = cluster_by_id[row.cluster_id]
            cases[index] = row.model_copy(
                update={
                    "question": (
                        f"{row.question.rstrip('?.!')} for source cluster "
                        f'"{cluster.cluster_id}"?'
                    )
                }
            )
    normalized = [normalize_question(row.question) for row in cases]
    if len(normalized) != len(set(normalized)):
        raise AtomicM2BuildError("atomic M2 normalized questions are not unique")


def _validate_non_overlapping_atoms(chunks: list[DocumentChunk]) -> None:
    by_source: dict[tuple[str, int, str], list[DocumentChunk]] = defaultdict(list)
    for chunk in chunks:
        source_id = chunk.source_artifact_id or chunk.document_id
        by_source[(source_id, chunk.source_version, chunk.source_checksum)].append(chunk)
    for rows in by_source.values():
        ordered = sorted(rows, key=lambda row: int(row.metadata["char_start"]))
        for left, right in zip(ordered, ordered[1:]):
            if int(right.metadata["char_start"]) < int(left.metadata["char_end"]):
                raise AtomicM2BuildError(
                    f"authoritative evidence atoms overlap: {left.id} and {right.id}"
                )


def _validate_atomic_cluster_cardinality(chunks: list[DocumentChunk]) -> None:
    counts = Counter(str(row.metadata["parent_cluster_id"]) for row in chunks)
    if len(counts) != 100 or set(counts.values()) != {3}:
        raise AtomicM2BuildError(
            "each atomic M2 cluster must expose exactly three authoritative atoms"
        )


def _validate_unique_answer_atom_mapping(
    gold: list[EvaluationGoldV1], chunks: list[DocumentChunk]
) -> dict[str, int]:
    mapping_count = 0
    for row in gold:
        if row.expected_action != EvaluationAction.ANSWER:
            continue
        for claim in row.claims:
            for reference in claim.evidence_refs:
                matches = [
                    chunk
                    for chunk in chunks
                    if (chunk.source_artifact_id or chunk.document_id)
                    == reference.source_artifact_id
                    and chunk.source_version == reference.source_version
                    and chunk.source_checksum == reference.source_sha256
                    and max(
                        int(chunk.metadata["char_start"]), reference.char_start
                    )
                    < min(int(chunk.metadata["char_end"]), reference.char_end)
                ]
                if len(matches) != 1:
                    raise AtomicM2BuildError(
                        f"answer span maps to {len(matches)} authoritative atoms: "
                        f"{claim.claim_id}"
                    )
                mapping_count += 1
    return {"uniquely_mapped_answer_span_count": mapping_count}


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
    candidates, excluded = _select_candidates()
    clusters = _build_clusters(candidates)
    cases = []
    gold = []
    for cluster in clusters:
        cluster_cases, cluster_gold = build_reference_cluster_rows(
            cluster,
            course_ids=COURSE_IDS,
            source_derived_region_ids=True,
        )
        cases.extend(cluster_cases)
        gold.extend(cluster_gold)
    _make_questions_unique(cases, clusters)
    cases.sort(key=lambda row: row.case_id)
    gold.sort(key=lambda row: row.case_id)
    if len(cases) != 500 or len(gold) != 500:
        raise AtomicM2BuildError("atomic M2 confirmation is not 500 cases")
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise AtomicM2BuildError("atomic M2 public/gold identities differ")

    chunks = registered_source_chunks(clusters)
    _validate_non_overlapping_atoms(chunks)
    _validate_atomic_cluster_cardinality(chunks)
    mapping = _validate_unique_answer_atom_mapping(gold, chunks)
    matchability = validate_exact_reference_matchability(gold=gold, chunks=chunks)
    afqc_103 = _load_afqc_103_source_package()
    source_payload: dict[str, Any] = {
        "schema_version": 1,
        "program_id": PROGRAM_ID,
        "instrument_id": INSTRUMENT_ID,
        "construction_method": "minimal-non-overlapping-authoritative-atoms-v1",
        "split": "development-confirmation",
        "cluster_count": len(clusters),
        "case_count": len(cases),
        "registered_region_count": len(chunks),
        "clusters": [row.model_dump(mode="json") for row in clusters],
        "chunks": [row.model_dump(mode="json") for row in chunks],
        "target_allocation": TARGET_ALLOCATION,
        "historical_build_source_plan_family_count": len(
            excluded["historical_build_source_plan"]
        ),
        "afqc_103_source_family_count": len(excluded["afqc_103_source_package"]),
        "afqc_103_source_package_sha256": afqc_103["content_sha256"],
        "source_family_disjoint_from_historical_build_source_plan": True,
        "source_family_disjoint_from_afqc_103": True,
        "parent_cluster_context_usage": "search-metadata-only",
        "authoritative_evidence_unit": "minimal-non-overlapping-atom",
        "authoritative_regions_non_overlapping": True,
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
        "program_id": PROGRAM_ID,
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "cluster_count": len(clusters),
        "case_count": len(cases),
        "registered_region_count": len(chunks),
        "matchability": matchability,
        "answer_atom_mapping": mapping,
        "course_modality_distribution": {
            f"{course}:{modality}": count
            for (course, modality), count in sorted(
                Counter((row.course_id, row.source_modality) for row in clusters).items()
            )
        },
        "normalized_questions_unique": True,
        "source_family_disjoint_from_historical_build_source_plan": True,
        "source_family_disjoint_from_afqc_103": True,
        "public_sources_only": True,
        "provider_calls": 0,
        "private_data_read": False,
        "final_split_opened": False,
        "packages": packages,
    }


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_byte_stable_packages() -> dict[str, Any]:
    first = build_packages()
    second = build_packages()
    for key in ("source", "cases", "gold"):
        if _json_bytes(first["packages"][key]) != _json_bytes(second["packages"][key]):
            raise AtomicM2BuildError(f"{key} package is not byte stable")
    first["byte_stable"] = True
    return first


def _write_packages_exclusive(packages: dict[str, dict[str, Any]]) -> None:
    outputs = {
        SOURCE_PATH: packages["source"],
        CASES_PATH: packages["cases"],
        GOLD_PATH: packages["gold"],
    }
    existing = [path.name for path in outputs if path.exists()]
    if existing:
        raise AtomicM2BuildError(
            f"exclusive output already exists: {', '.join(sorted(existing))}"
        )
    DATASET_ROOT.mkdir(parents=True, exist_ok=True)
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
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "dataset_generation")
        _write_packages_exclusive(result["packages"])
        result["status"] = "completed-build-only"
    result.pop("packages")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
