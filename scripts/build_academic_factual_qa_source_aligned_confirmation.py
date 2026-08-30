#!/usr/bin/env python3
"""Build a fresh source-family-disjoint, exactly matchable confirmation set."""

from __future__ import annotations

import argparse
from collections import Counter
from collections import defaultdict
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
    build_reference_pool,
)
from scripts.build_academic_factual_qa_open_source_plan_v2 import (  # noqa: E402
    build_source_plan,
)
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question  # noqa: E402
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.factual_qa_references import (  # noqa: E402
    SourceClusterV2,
    build_reference_cluster_rows,
)
from src.digital_twin.evaluation.finite_retrieval_evaluation import (  # noqa: E402
    validate_exact_reference_matchability,
)
from src.digital_twin.grounding.source_registration import (  # noqa: E402
    registered_source_chunks,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


PROGRAM_ID = "course-digital-twin-nonhuman-evaluation-program-002"
INSTRUMENT_ID = "academic-factual-qa-source-aligned-confirmation-001"
TARGET_ALLOCATION = {
    "operating-systems": {
        "text": 4,
        "structured-code": 20,
        "structured-table": 1,
    },
    "computer-networking": {
        "text": 20,
        "structured-code": 2,
        "structured-table": 3,
    },
    "data-structures": {
        "text": 19,
        "structured-equation": 6,
    },
    "python-programming": {
        "text": 7,
        "structured-code": 18,
    },
}
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
SOURCE_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-sources.json"
CASES_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-cases.json"
GOLD_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-gold.json"


class SourceAlignedBuildError(RuntimeError):
    """Raised when exact source/question/gold alignment cannot be proved."""


def _select_clusters() -> list[SourceClusterV2]:
    pool = build_reference_pool()
    historical_families = {
        str(row["source_family_id"]) for row in build_source_plan()["clusters"]
    }
    candidates = [
        SourceClusterV2.model_validate(row)
        for row in pool["clusters"]
        if str(row["source_family_id"]) not in historical_families
    ]
    selected: list[SourceClusterV2] = []
    for course_id, modalities in TARGET_ALLOCATION.items():
        for modality, required in modalities.items():
            available = sorted(
                (
                    row
                    for row in candidates
                    if row.course_id == course_id and row.source_modality == modality
                ),
                key=lambda row: row.cluster_id,
            )
            if len(available) < required:
                raise SourceAlignedBuildError(
                    f"source-family-disjoint allocation shortfall {course_id}:{modality}"
                )
            selected.extend(available[:required])
    selected.sort(key=lambda row: row.cluster_id)
    if len(selected) != 100 or len({row.cluster_id for row in selected}) != 100:
        raise SourceAlignedBuildError("source-aligned confirmation is not 100 clusters")
    return selected


def _package(*, key: str, rows: list[dict[str, Any]], source_hash: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
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
    clusters = _select_clusters()
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
            source_name = Path(cluster.source_path).stem.replace("_", " ").replace("-", " ")
            cases[index] = row.model_copy(
                update={
                    "question": (
                        f"{row.question.rstrip('?.!')} in the source section "
                        f'\"{source_name}: {cluster.section_heading}\"?'
                    )
                }
            )
    cases.sort(key=lambda row: row.case_id)
    gold.sort(key=lambda row: row.case_id)
    if len(cases) != 500 or len(gold) != 500:
        raise SourceAlignedBuildError("source-aligned confirmation is not 500 cases")
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise SourceAlignedBuildError("source-aligned public/gold identities differ")
    normalized = [normalize_question(row.question) for row in cases]
    canonical_seed_duplicate_count = len(normalized) - len(set(normalized))

    chunks = registered_source_chunks(clusters)
    matchability = validate_exact_reference_matchability(gold=gold, chunks=chunks)
    source_payload: dict[str, Any] = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "construction_method": "complete-region-contextual-registration-v1",
        "cluster_count": len(clusters),
        "registered_region_count": len(chunks),
        "canonical_seed_duplicate_count": canonical_seed_duplicate_count,
        "clusters": [row.model_dump(mode="json") for row in clusters],
        "chunks": [row.model_dump(mode="json") for row in chunks],
        "target_allocation": TARGET_ALLOCATION,
        "source_family_disjoint_from_afqc_100": True,
        "provider_calls": 0,
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
        "cluster_count": len(clusters),
        "case_count": len(cases),
        "registered_region_count": len(chunks),
        "matchability": matchability,
        "course_modality_distribution": {
            f"{course}:{modality}": count
            for (course, modality), count in sorted(
                Counter((row.course_id, row.source_modality) for row in clusters).items()
            )
        },
        "provider_calls": 0,
        "private_data_used": False,
        "packages": packages,
    }


def _exclusive_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise SourceAlignedBuildError(f"exclusive output already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--write", action="store_true")
    arguments = parser.parse_args()
    result = build_packages()
    if arguments.write:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "dataset_generation")
        _exclusive_json(SOURCE_PATH, result["packages"]["source"])
        _exclusive_json(CASES_PATH, result["packages"]["cases"])
        _exclusive_json(GOLD_PATH, result["packages"]["gold"])
        result["status"] = "completed-build-only"
    result.pop("packages")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
