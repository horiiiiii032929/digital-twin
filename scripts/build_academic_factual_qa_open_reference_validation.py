#!/usr/bin/env python3
"""Build a fresh source-disjoint pool for reference-question validation."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_academic_factual_qa_open_source_plan_v2 import (  # noqa: E402
    Candidate,
    _cluster,
    build_candidate_inventory,
    build_source_plan,
)
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.factual_qa_references import (  # noqa: E402
    SourceClusterV2,
    build_reference_cluster_rows,
)


INSTRUMENT_ID = "academic-factual-qa-open-10000-reference-question-validation-001"
TARGET_ALLOCATION: dict[str, dict[str, int]] = {
    "operating-systems": {
        "text": 4,
        "structured-code": 20,
        "structured-table": 1,
    },
    "computer-networking": {
        "text": 18,
        "structured-code": 4,
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
CANDIDATE_ALLOCATION: dict[str, dict[str, int]] = {
    "operating-systems": {
        "text": 6,
        "structured-code": 31,
        "structured-table": 3,
    },
    "computer-networking": {
        "text": 28,
        "structured-code": 6,
        "structured-table": 6,
    },
    "data-structures": {
        "text": 30,
        "structured-equation": 10,
    },
    "python-programming": {
        "text": 11,
        "structured-code": 29,
    },
}
BOUNDARY_SLICES = (
    "no-evidence",
    "cross-course",
    "ambiguity",
    "academic-integrity",
)
COURSE_IDS = sorted(TARGET_ALLOCATION)
MAX_CLUSTERS_PER_SECTION = 5


class ReferenceValidationBuildError(RuntimeError):
    """Raised when the fresh validation pool violates its contract."""


def _overlaps_ranges(
    candidate: Candidate,
    ranges: dict[tuple[str, str], list[tuple[int, int]]],
) -> bool:
    key = (candidate.course_id, candidate.section.path)
    start = candidate.section.start + candidate.start
    end = candidate.section.start + candidate.end
    return any(max(start, left) < min(end, right) for left, right in ranges[key])


def _select_fresh_candidates() -> list[Candidate]:
    old_plan = build_source_plan()
    occupied: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for row in old_plan["clusters"]:
        occupied[(row["course_id"], row["source_path"])].append(
            (int(row["char_start"]), int(row["char_end"]))
        )
    inventory = build_candidate_inventory()
    selected: list[Candidate] = []
    selected_ranges: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    selected_ranges.update({key: list(value) for key, value in occupied.items()})
    section_counts: Counter[tuple[str, str]] = Counter()
    for course_id in sorted(CANDIDATE_ALLOCATION):
        modality_order = [
            modality
            for modality in (
                "text",
                "structured-table",
                "structured-equation",
                "structured-code",
            )
            if modality in CANDIDATE_ALLOCATION[course_id]
        ]
        for modality in modality_order:
            required = CANDIDATE_ALLOCATION[course_id][modality]
            options = [
                row
                for row in inventory[course_id]
                if row.modality == modality
                and not _overlaps_ranges(row, selected_ranges)
            ]
            options.sort(
                key=lambda row: (
                    section_counts[(row.course_id, row.section.family_key)],
                    row.end - row.start,
                    row.identity,
                )
            )
            accepted = 0
            for row in options:
                key = (row.course_id, row.section.family_key)
                if section_counts[key] >= MAX_CLUSTERS_PER_SECTION:
                    continue
                if _overlaps_ranges(row, selected_ranges):
                    continue
                selected.append(row)
                section_counts[key] += 1
                absolute = (
                    row.section.start + row.start,
                    row.section.start + row.end,
                )
                selected_ranges.setdefault((row.course_id, row.section.path), []).append(
                    absolute
                )
                accepted += 1
                if accepted == required:
                    break
            if accepted != required:
                raise ReferenceValidationBuildError(
                    f"fresh {course_id}:{modality} candidates {accepted}/{required}"
                )
    return selected


def _question_placeholder(case_id: str) -> str:
    return f"Pending independently validated question for case {case_id}?"


def build_reference_pool() -> dict[str, Any]:
    selected = _select_fresh_candidates()
    clusters: list[SourceClusterV2] = []
    for index, candidate in enumerate(selected, start=1):
        extra = "multi-evidence" if candidate.modality == "text" else candidate.modality
        slices = (
            ["direct-factual", "paraphrased", "definition-explanation", extra],
            BOUNDARY_SLICES[(index - 1) % len(BOUNDARY_SLICES)],
        )
        clusters.append(
            _cluster(
                candidate,
                cluster_id=f"academic-open-dev3-{index:04d}",
                slices=slices,
            )
        )
    if len(clusters) != 160:
        raise ReferenceValidationBuildError("fresh candidate pool is not 160 clusters")

    cases: list[EvaluationCaseV1] = []
    gold: list[EvaluationGoldV1] = []
    for cluster in clusters:
        cluster_cases, cluster_gold = build_reference_cluster_rows(
            cluster,
            course_ids=COURSE_IDS,
        )
        cases.extend(
            row.model_copy(update={"question": _question_placeholder(row.case_id)})
            for row in cluster_cases
        )
        gold.extend(cluster_gold)
    cases.sort(key=lambda row: row.case_id)
    gold.sort(key=lambda row: row.case_id)
    if len(cases) != 800 or len(gold) != 800:
        raise ReferenceValidationBuildError("fresh candidate pool is not 800 cases")
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise ReferenceValidationBuildError("fresh public and gold identities differ")

    candidate_distribution = Counter(
        (row.course_id, row.source_modality) for row in clusters
    )
    expected_distribution = {
        (course_id, modality): count
        for course_id, rows in CANDIDATE_ALLOCATION.items()
        for modality, count in rows.items()
    }
    if dict(candidate_distribution) != expected_distribution:
        raise ReferenceValidationBuildError("fresh candidate allocation drifted")

    old_clusters = [SourceClusterV2.model_validate(row) for row in build_source_plan()["clusters"]]
    for fresh in clusters:
        for old in old_clusters:
            if fresh.course_id != old.course_id or fresh.source_path != old.source_path:
                continue
            if max(fresh.char_start, old.char_start) < min(fresh.char_end, old.char_end):
                raise ReferenceValidationBuildError("fresh cluster overlaps checkpoint-007 source")

    payload: dict[str, Any] = {
        "schema_version": 1,
        "source_plan_id": "academic-factual-qa-open-10000-reference-validation-pool-001",
        "instrument_id": INSTRUMENT_ID,
        "split": "development-confirmation",
        "candidate_cluster_count": len(clusters),
        "candidate_case_count": len(cases),
        "target_cluster_count": 100,
        "target_case_count": 500,
        "candidate_allocation": CANDIDATE_ALLOCATION,
        "target_allocation": TARGET_ALLOCATION,
        "clusters": [row.model_dump(mode="json") for row in clusters],
        "base_cases": [row.model_dump(mode="json") for row in cases],
        "gold": [row.model_dump(mode="json") for row in gold],
        "source_disjoint_from_checkpoint_007": True,
        "provider_calls": 0,
        "private_data_read": False,
        "final_split_opened": False,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    return payload


def author_requests(pool: dict[str, Any]) -> list[dict[str, Any]]:
    clusters = {
        row["cluster_id"]: SourceClusterV2.model_validate(row)
        for row in pool["clusters"]
    }
    cases = {
        row["case_id"]: EvaluationCaseV1.model_validate(row)
        for row in pool["base_cases"]
    }
    gold = {
        row["case_id"]: EvaluationGoldV1.model_validate(row)
        for row in pool["gold"]
    }
    requests: list[dict[str, Any]] = []
    for case_id in sorted(cases):
        case = cases[case_id]
        expected = gold[case_id]
        cluster = clusters[case.cluster_id]
        requests.append(
            {
                "case_id": case_id,
                "cluster_id": case.cluster_id,
                "course_id": case.course_id,
                "source_course_id": cluster.course_id,
                "slice": case.slice,
                "section_heading": cluster.section_heading,
                "expected_action": expected.expected_action,
                "canonical_answer": (
                    expected.canonical_answer
                    if expected.expected_action == EvaluationAction.ANSWER
                    else None
                ),
                "required_answer_spans": [row.answer_span for row in expected.claims],
                "boundary_reason": expected.boundary_reason,
            }
        )
    return requests


def summary() -> dict[str, Any]:
    first = build_reference_pool()
    second = build_reference_pool()
    if first["content_sha256"] != second["content_sha256"]:
        raise ReferenceValidationBuildError("fresh source pool is not byte stable")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "source_plan_sha256": first["content_sha256"],
        "candidate_cluster_count": first["candidate_cluster_count"],
        "candidate_case_count": first["candidate_case_count"],
        "target_cluster_count": first["target_cluster_count"],
        "target_case_count": first["target_case_count"],
        "source_disjoint_from_checkpoint_007": True,
        "provider_calls": 0,
        "private_data_read": False,
        "final_split_opened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    parser.parse_args()
    print(json.dumps(summary(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
