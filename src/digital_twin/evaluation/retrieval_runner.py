"""Execute development cases against an injected course-scoped ladder."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any

from src.digital_twin.evaluation.retrieval_qualification import (
    POSITIVE_SLICES,
    RetrievalMethod,
    assign_boundary_courses,
    score_ranking,
)
from src.digital_twin.grounding.protocols import Retriever


Synchronize = Callable[[], None]
CaseCallback = Callable[[int, list[dict[str, Any]]], None]


def evaluate_development_cases(
    cases: list[dict[str, Any]],
    *,
    runtimes: Mapping[str, Mapping[str, Retriever]],
    chunk_course: Mapping[str, str],
    result_limit: int,
    synchronize: Synchronize | None = None,
    on_case_complete: CaseCallback | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if len(cases) != 40:
        raise ValueError("qualification requires all 40 development cases")
    if any(case["split"] != "development" for case in cases):
        raise ValueError("qualification received a non-development case")
    if result_limit < 5:
        raise ValueError("result limit must be at least 5")
    expected_methods = {method.value for method in RetrievalMethod}
    if not runtimes:
        raise ValueError("qualification has no course runtimes")
    for course_id, methods in runtimes.items():
        if set(methods) != expected_methods:
            raise ValueError(f"{course_id} retrieval ladder is incomplete")

    for case in cases:
        for evidence in case["gold_evidence"]:
            if chunk_course.get(evidence["chunk_id"]) != case["target_course_id"]:
                raise ValueError(
                    f"{case['case_id']} gold evidence is outside target course"
                )

    boundary_assignments = assign_boundary_courses(
        cases,
        sorted(runtimes),
    )
    rows: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        is_positive = case["slice"] in POSITIVE_SLICES
        evaluation_course_id = (
            case["target_course_id"]
            if is_positive
            else boundary_assignments[case["case_id"]]
        )
        if evaluation_course_id not in runtimes:
            raise ValueError(f"{case['case_id']} has no authorized course runtime")
        for method in RetrievalMethod:
            if synchronize:
                synchronize()
            started = time.perf_counter()
            hits = runtimes[evaluation_course_id][method.value].retrieve(
                case["query"],
                limit=result_limit,
            )
            if synchronize:
                synchronize()
            latency_ms = (time.perf_counter() - started) * 1000
            ranked_ids = [hit.chunk.id for hit in hits]
            score = float(hits[0].raw_score or hits[0].relevance_score) if hits else 0.0
            row: dict[str, Any] = {
                "case_id": case["case_id"],
                "slice": case["slice"],
                "difficulty": case["difficulty"],
                "target_course_id": case["target_course_id"],
                "evaluation_course_id": evaluation_course_id,
                "method": method.value,
                "is_positive": is_positive,
                "decision_score": score,
                "latency_ms": latency_ms,
                "ranked_chunk_ids": ranked_ids,
                "course_isolation_violations": sum(
                    chunk_course.get(identifier) != evaluation_course_id
                    for identifier in ranked_ids
                ),
            }
            if is_positive:
                row["ranking"] = score_ranking(
                    [evidence["chunk_id"] for evidence in case["gold_evidence"]],
                    ranked_ids,
                )
            rows.append(row)
        if on_case_complete:
            on_case_complete(index, rows)
    return rows, boundary_assignments
