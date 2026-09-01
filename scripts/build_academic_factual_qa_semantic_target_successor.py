#!/usr/bin/env python3
"""Build the fresh 500-case semantic-target grounding successor.

The package is development-only and provider-free.  It uses one newly pinned
operating-systems source plus unused ranges from the three existing open-course
repositories.  Public cases and hidden gold are emitted as separate packages.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_academic_factual_qa_atomic_m2_confirmation as atomic
from scripts.build_academic_factual_qa_confirmation_v2 import (
    COURSES,
    SNAPSHOT_ROOT,
    Section,
    file_sha256,
)
from scripts.build_academic_factual_qa_open_reference_validation import COURSE_IDS
from scripts.build_academic_factual_qa_open_source_plan_v2 import (
    Candidate,
    _text_candidates,
    build_candidate_inventory,
    build_source_plan,
)
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationGoldV1,
    EvaluationSplit,
)
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.evaluation.factual_qa_references import (
    ReferenceTargetV1,
    SourceClusterV2,
    build_reference_cluster_rows,
    target_from_regions,
)
from src.digital_twin.evaluation.finite_retrieval_evaluation import (
    validate_exact_reference_matchability,
)
from src.digital_twin.grounding.source_registration import registered_source_chunks
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


INSTRUMENT_ID = "academic-factual-qa-semantic-target-successor-001"
PROGRAM_ID = "course-digital-twin-grounding-correction-001"
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
SOURCE_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-sources.json"
CASES_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-cases.json"
GOLD_PATH = DATASET_ROOT / f"{INSTRUMENT_ID}-gold.json"
THINK_OS_ROOT = (
    ROOT / "data/external/semantic_target_successor_001/think-os"
)
THINK_OS_SOURCE_PATH = THINK_OS_ROOT / "book/book.tex"
THINK_OS_COMMIT = "5ab731d25042d4aab455566dc7698fdd31373c75"
THINK_OS_REPOSITORY = "https://github.com/AllenDowney/ThinkOS"
THINK_OS_LICENSE = "CC-BY-NC-SA-4.0"
PRIOR_SOURCE_PATHS = (
    DATASET_ROOT / "academic-factual-qa-source-aligned-confirmation-001-sources.json",
    DATASET_ROOT / "academic-factual-qa-atomic-m2-confirmation-001-sources.json",
    DATASET_ROOT / "academic-factual-qa-action-router-confirmation-001-sources.json",
)
TARGET_ALLOCATION: dict[str, dict[str, int]] = {
    "operating-systems": {"text": 25},
    "computer-networking": {
        "text": 18,
        "structured-code": 3,
        "structured-table": 4,
    },
    "data-structures": {
        "text": 16,
        "structured-equation": 5,
        "structured-table": 4,
    },
    "python-programming": {"text": 15, "structured-code": 10},
}
MAX_CLUSTERS_PER_SOURCE_FAMILY = 2
_HEADING = re.compile(r"\\(?:chapter|section|subsection)\{([^{}]+)\}")


class SemanticTargetBuildError(RuntimeError):
    """Raised when the fresh semantic-target package violates an invariant."""


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _load_hashed(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    observed = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != observed:
        raise SemanticTargetBuildError(f"content hash drifted: {path.name}")
    return payload


def _candidate_family_id(candidate: Candidate) -> str:
    value = f"{candidate.course_id}:{candidate.section.family_key}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _absolute_range(candidate: Candidate) -> tuple[int, int]:
    return (
        candidate.section.start + candidate.start,
        candidate.section.start + candidate.end,
    )


def _prior_ranges() -> dict[tuple[str, str], list[tuple[int, int]]]:
    ranges: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for row in build_source_plan()["clusters"]:
        ranges[(str(row["course_id"]), str(row["source_path"]))].append(
            (int(row["char_start"]), int(row["char_end"]))
        )
    for path in PRIOR_SOURCE_PATHS:
        for row in _load_hashed(path)["chunks"]:
            metadata = row["metadata"]
            ranges[(str(metadata["course_id"]), str(metadata["source_path"]))].append(
                (int(metadata["char_start"]), int(metadata["char_end"]))
            )
    return ranges


def _overlaps(
    candidate: Candidate,
    ranges: dict[tuple[str, str], list[tuple[int, int]]],
) -> bool:
    start, end = _absolute_range(candidate)
    return any(
        max(start, left) < min(end, right)
        for left, right in ranges[(candidate.course_id, candidate.section.path)]
    )


def _verify_think_os_source() -> None:
    if not THINK_OS_SOURCE_PATH.is_file():
        raise SemanticTargetBuildError(
            "missing pinned ThinkOS source; clone AllenDowney/ThinkOS at "
            f"{THINK_OS_COMMIT} under {THINK_OS_ROOT}"
        )
    git_head = subprocess.run(
        ["git", "-C", str(THINK_OS_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if git_head != THINK_OS_COMMIT:
        raise SemanticTargetBuildError("ThinkOS source revision drifted")
    header = THINK_OS_SOURCE_PATH.read_text(encoding="utf-8")[:500]
    if "Attribution-NonCommercial-ShareAlike 4.0 International" not in header:
        raise SemanticTargetBuildError("ThinkOS source license evidence drifted")


def _think_os_candidates() -> list[Candidate]:
    _verify_think_os_source()
    source = THINK_OS_SOURCE_PATH.read_text(encoding="utf-8")
    headings = list(_HEADING.finditer(source))
    occurrences: Counter[str] = Counter()
    candidates: list[Candidate] = []
    for index, match in enumerate(headings):
        heading = " ".join(match.group(1).split())
        if heading.casefold() in {"preface", "exercises", "glossary"}:
            continue
        occurrences[heading] += 1
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(source)
        section = Section(
            course_id="operating-systems",
            path="book/book.tex",
            heading=heading,
            occurrence=occurrences[heading],
            start=start,
            end=end,
            line_start=source.count("\n", 0, start) + 1,
            line_end=source.count("\n", 0, end) + 1,
            text=source[start:end],
            modalities=frozenset({"text"}),
        )
        candidates.extend(_text_candidates("operating-systems", section))
    return sorted(candidates, key=lambda row: row.identity)


def _select_candidates() -> tuple[list[Candidate], dict[str, Any]]:
    prior = _prior_ranges()
    inventory = build_candidate_inventory()
    inventory["operating-systems"] = _think_os_candidates()
    selected: list[Candidate] = []
    selected_ranges: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    family_counts: Counter[str] = Counter()
    eligible_counts: dict[str, int] = {}

    for course_id, allocation in TARGET_ALLOCATION.items():
        eligible_by_modality = {
            modality: [
                candidate
                for candidate in inventory[course_id]
                if candidate.modality == modality and not _overlaps(candidate, prior)
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
            for _ in range(allocation[modality]):
                options = [
                    candidate
                    for candidate in eligible_by_modality[modality]
                    if family_counts[_candidate_family_id(candidate)]
                    < MAX_CLUSTERS_PER_SOURCE_FAMILY
                    and not _overlaps(candidate, selected_ranges)
                ]
                options.sort(
                    key=lambda candidate: (
                        family_counts[_candidate_family_id(candidate)],
                        candidate.end - candidate.start,
                        candidate.identity,
                    )
                )
                if not options:
                    raise SemanticTargetBuildError(
                        f"fresh allocation shortfall {course_id}:{modality}"
                    )
                chosen = options[0]
                selected.append(chosen)
                family_counts[_candidate_family_id(chosen)] += 1
                selected_ranges[(chosen.course_id, chosen.section.path)].append(
                    _absolute_range(chosen)
                )

    selected.sort(key=lambda row: row.identity)
    expected = {
        (course_id, modality): count
        for course_id, allocation in TARGET_ALLOCATION.items()
        for modality, count in allocation.items()
    }
    observed = Counter((row.course_id, row.modality) for row in selected)
    if len(selected) != 100 or len({row.identity for row in selected}) != 100:
        raise SemanticTargetBuildError("successor must contain 100 unique clusters")
    if dict(observed) != expected:
        raise SemanticTargetBuildError("successor course/modality allocation drifted")
    if any(_overlaps(candidate, prior) for candidate in selected):
        raise SemanticTargetBuildError("successor overlaps prior source ranges")
    return selected, {
        "eligible_candidate_counts": eligible_counts,
        "selected_source_family_count": len(family_counts),
        "maximum_clusters_per_source_family": max(family_counts.values()),
    }


def _course_metadata(candidate: Candidate) -> tuple[dict[str, Any], Path]:
    if candidate.course_id == "operating-systems":
        return (
            {
                "repository_url": THINK_OS_REPOSITORY,
                "commit": THINK_OS_COMMIT,
                "license_spdx": THINK_OS_LICENSE,
            },
            THINK_OS_SOURCE_PATH,
        )
    course = next(row for row in COURSES if row["course_id"] == candidate.course_id)
    return course, SNAPSHOT_ROOT / course["snapshot"] / candidate.section.path


def _cluster(
    candidate: Candidate,
    *,
    cluster_id: str,
    answerable_slices: list[str],
    boundary_slice: str,
) -> SourceClusterV2:
    course, source_path = _course_metadata(candidate)
    absolute_start, absolute_end = _absolute_range(candidate)
    targets: list[ReferenceTargetV1] = [
        target_from_regions(
            slice_name=slice_name,
            cluster_start=candidate.start,
            regions=list(regions),
        )
        for slice_name, regions in zip(
            answerable_slices,
            candidate.target_regions,
            strict=True,
        )
    ]
    family_value = f"{candidate.course_id}:{candidate.section.family_key}"
    return SourceClusterV2(
        cluster_id=cluster_id,
        source_family_id=hashlib.sha256(family_value.encode()).hexdigest()[:24],
        course_id=candidate.course_id,
        source_artifact_id=f"{candidate.course_id}:{candidate.section.path}",
        source_version=1,
        source_sha256=file_sha256(source_path),
        source_path=candidate.section.path,
        section_heading=candidate.section.heading,
        char_start=absolute_start,
        char_end=absolute_end,
        text=candidate.section.text[candidate.start : candidate.end],
        source_modality=candidate.modality,
        split=EvaluationSplit.DEVELOPMENT,
        answerable_slices=answerable_slices,
        boundary_slice=boundary_slice,
        author_family="deterministic-semantic-target-planner-v1",
        verifier_family="deterministic-source-range-auditor-v3",
        license_spdx=str(course["license_spdx"]),
        repository_url=str(course["repository_url"]),
        repository_commit=str(course["commit"]),
        reference_targets=targets,
    )


def _build_clusters(candidates: list[Candidate]) -> list[SourceClusterV2]:
    clusters: list[SourceClusterV2] = []
    boundary = ("no-evidence", "cross-course", "ambiguity", "academic-integrity")
    for index, candidate in enumerate(candidates, start=1):
        candidate = atomic._atomic_candidate(candidate)  # noqa: SLF001
        fourth = "multi-evidence" if candidate.modality == "text" else candidate.modality
        clusters.append(
            _cluster(
                candidate,
                cluster_id=f"semantic-target-dev-{index:04d}",
                answerable_slices=[
                    "direct-factual",
                    "paraphrased",
                    "definition-explanation",
                    fourth,
                ],
                boundary_slice=boundary[(index - 1) % len(boundary)],
            )
        )
    return clusters


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
    cases = []
    gold: list[EvaluationGoldV1] = []
    for cluster in clusters:
        cluster_cases, cluster_gold = build_reference_cluster_rows(
            cluster,
            course_ids=COURSE_IDS,
            source_derived_region_ids=True,
        )
        cases.extend(cluster_cases)
        gold.extend(cluster_gold)
    atomic._make_questions_unique(cases, clusters)  # noqa: SLF001
    cases.sort(key=lambda row: row.case_id)
    gold.sort(key=lambda row: row.case_id)
    if len(cases) != 500 or len(gold) != 500:
        raise SemanticTargetBuildError("successor must contain exactly 500 cases")
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise SemanticTargetBuildError("public and hidden-gold identities differ")
    normalized = [normalize_question(row.question) for row in cases]
    if len(normalized) != len(set(normalized)):
        raise SemanticTargetBuildError("normalized questions are not unique")

    chunks = registered_source_chunks(clusters)
    atomic._validate_non_overlapping_atoms(chunks)  # noqa: SLF001
    atomic._validate_atomic_cluster_cardinality(chunks)  # noqa: SLF001
    mapping = atomic._validate_unique_answer_atom_mapping(gold, chunks)  # noqa: SLF001
    matchability = validate_exact_reference_matchability(gold=gold, chunks=chunks)
    source_payload: dict[str, Any] = {
        "schema_version": 1,
        "program_id": PROGRAM_ID,
        "instrument_id": INSTRUMENT_ID,
        "construction_method": "fresh-source-range-semantic-target-successor-v1",
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
        "new_operating_systems_source": {
            "repository_url": THINK_OS_REPOSITORY,
            "repository_commit": THINK_OS_COMMIT,
            "license_spdx": THINK_OS_LICENSE,
            "source_path": "book/book.tex",
        },
        "selection_diagnostics": selection,
        "authoritative_evidence_unit": "minimal-non-overlapping-source-range",
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
            raise SemanticTargetBuildError(f"{key} package is not byte stable")
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
        raise SemanticTargetBuildError(
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
