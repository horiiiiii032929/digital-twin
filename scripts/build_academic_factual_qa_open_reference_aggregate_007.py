#!/usr/bin/env python3
"""Build a question-stratified reference package from durable blind reviews."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_academic_factual_qa_open_reference_validation as runner  # noqa: E402
from scripts.build_academic_factual_qa_open_reference_validation import (  # noqa: E402
    build_reference_pool,
)
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_dataset import (  # noqa: E402
    normalize_question,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.factual_qa_reference_questions import (  # noqa: E402
    ReferenceQuestionAuthorResponseV1,
    ReferenceQuestionCandidateAuthorResponseV1,
    ReferenceQuestionCandidateReviewResponseV1,
    score_multi_candidate_reference_questions,
)
from src.digital_twin.evaluation.factual_qa_references import (  # noqa: E402
    SourceClusterV2,
)
from src.digital_twin.evaluation.provider_json import ProviderJsonResponse  # noqa: E402
from src.digital_twin.grounding.source_registration import (  # noqa: E402
    registered_source_chunks,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_ID = "academic-factual-qa-open-10000-reference-aggregate-007"
DATASET_ID = "academic-factual-qa-open-10000-v1-development-reference-aggregate-007"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_reference_aggregate_007.json"
)
CASES_PATH = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_reference_aggregate_007_cases.json"
)
GOLD_PATH = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_reference_aggregate_007_gold.json"
)
SOURCES_PATH = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_reference_aggregate_007_sources.json"
)
CONTROL_CASES_PATH = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_reference_aggregate_007_control_cases.json"
)
CONTROL_GOLD_PATH = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_reference_aggregate_007_control_gold.json"
)

COURSES = (
    "computer-networking",
    "data-structures",
    "operating-systems",
    "python-programming",
)
ANSWER_QUOTAS = {
    "computer-networking": {"q1": 25, "q2": 23, "q3": 25, "q4": 27},
    "data-structures": {"q1": 25, "q2": 27, "q3": 25, "q4": 23},
    "operating-systems": {"q1": 25, "q2": 25, "q3": 25, "q4": 25},
    "python-programming": {"q1": 25, "q2": 25, "q3": 25, "q4": 25},
}
BOUNDARY_SLICES = (
    "academic-integrity",
    "ambiguity",
    "cross-course",
    "no-evidence",
)
BOUNDARY_QUOTAS = {
    "computer-networking": {
        "academic-integrity": 6,
        "ambiguity": 6,
        "cross-course": 6,
        "no-evidence": 7,
    },
    "data-structures": {
        "academic-integrity": 6,
        "ambiguity": 7,
        "cross-course": 6,
        "no-evidence": 6,
    },
    "operating-systems": {
        "academic-integrity": 6,
        "ambiguity": 6,
        "cross-course": 7,
        "no-evidence": 6,
    },
    "python-programming": {
        "academic-integrity": 7,
        "ambiguity": 6,
        "cross-course": 6,
        "no-evidence": 6,
    },
}


class ReferenceAggregateError(RuntimeError):
    """Raised when the aggregate reference package is not reproducible."""


@dataclass(frozen=True)
class AcceptedQuestion:
    case_id: str
    question: str
    provenance: str
    rank: int


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReferenceAggregateError(f"JSON root is not an object: {path.name}")
    return value


def _load_hashed(path: Path, *, identity_key: str, identity: str) -> dict[str, Any]:
    value = _load(path)
    if value.get(identity_key) != identity:
        raise ReferenceAggregateError(f"identity drifted: {path.name}")
    observed = canonical_json_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != observed:
        raise ReferenceAggregateError(f"content hash drifted: {path.name}")
    return value


def _ledger_rows(path: Path) -> list[tuple[str, ProviderJsonResponse]]:
    if not path.is_file():
        raise ReferenceAggregateError(f"required local ledger missing: {path.name}")
    connection = sqlite3.connect(path)
    try:
        rows = connection.execute(
            "SELECT provider_role, response_json FROM calls "
            "WHERE status = 'completed' ORDER BY sequence"
        ).fetchall()
    finally:
        connection.close()
    return [
        (role, ProviderJsonResponse.model_validate_json(response_json))
        for role, response_json in rows
    ]


def _attempt_003_candidates(
    *, answerable_ids: set[str]
) -> list[AcceptedQuestion]:
    result = _load_hashed(
        runner.ATTEMPT_003.result_path,
        identity_key="instrument_id",
        identity=runner.ATTEMPT_003.instrument_id,
    )
    passed = {
        row["case_id"]
        for row in result["decisions"]
        if row["passed"] and row["case_id"] in answerable_ids
    }
    authored: dict[str, str] = {}
    for role, response in _ledger_rows(runner.ATTEMPT_003.ledger_path):
        if role != runner.AUTHOR_ROLE:
            continue
        for raw in response.content.get("items", []):
            row = ReferenceQuestionAuthorResponseV1.model_validate(raw)
            authored[row.case_id] = row.question
    return [
        AcceptedQuestion(
            case_id=case_id,
            question=authored[case_id],
            provenance="reference-validation-003-single-candidate",
            rank=400,
        )
        for case_id in sorted(passed)
    ]


def _multi_attempt_candidates(
    *,
    attempt: runner.ReferenceQuestionAttempt,
    canonical_cases: list[EvaluationCaseV1],
    canonical_gold: list[EvaluationGoldV1],
    cluster_modalities: dict[str, str],
    answerable_ids: set[str],
    rank_base: int,
) -> list[AcceptedQuestion]:
    authors: list[ReferenceQuestionCandidateAuthorResponseV1] = []
    reviewers: list[ReferenceQuestionCandidateReviewResponseV1] = []
    question_by_candidate: dict[str, str] = {}
    for role, response in _ledger_rows(attempt.ledger_path):
        if role == runner.AUTHOR_ROLE:
            for raw in response.content.get("items", []):
                try:
                    authored = ReferenceQuestionCandidateAuthorResponseV1.model_validate(
                        raw
                    )
                except ValueError:
                    continue
                if authored.case_id not in answerable_ids:
                    continue
                authors.append(authored)
                for ordinal, question in enumerate(authored.questions, start=1):
                    question_by_candidate[
                        f"{authored.case_id}-candidate-{ordinal}"
                    ] = question
        elif role == runner.REVIEWER_ROLE:
            for raw in response.content.get("items", []):
                try:
                    reviewers.append(
                        ReferenceQuestionCandidateReviewResponseV1.model_validate(raw)
                    )
                except ValueError:
                    continue
    scored = score_multi_candidate_reference_questions(
        canonical_cases=canonical_cases,
        gold=canonical_gold,
        cluster_modalities=cluster_modalities,
        authors=authors,
        reviewers=reviewers,
        target_allocation=runner.TARGET_ALLOCATION,
    )
    output: list[AcceptedQuestion] = []
    for decision in scored["decisions"]:
        if not decision["passed"]:
            continue
        candidate_id = decision["candidate_id"]
        question = question_by_candidate.get(candidate_id)
        if question is None:
            raise ReferenceAggregateError("passed candidate question is missing")
        ordinal = int(candidate_id.rsplit("-", 1)[-1])
        output.append(
            AcceptedQuestion(
                case_id=decision["case_id"],
                question=question,
                provenance=attempt.instrument_id,
                rank=rank_base + ordinal,
            )
        )
    return output


def _accepted_questions(
    *,
    canonical_cases: list[EvaluationCaseV1],
    canonical_gold: list[EvaluationGoldV1],
    pool: dict[str, Any],
) -> dict[str, list[AcceptedQuestion]]:
    answerable_ids = {
        row.case_id
        for row in canonical_gold
        if row.expected_action == EvaluationAction.ANSWER
    }
    cluster_modalities = {
        row["cluster_id"]: row["source_modality"] for row in pool["clusters"]
    }
    candidates: list[AcceptedQuestion] = []
    candidates.extend(
        _multi_attempt_candidates(
            attempt=runner.ATTEMPT_006,
            canonical_cases=canonical_cases,
            canonical_gold=canonical_gold,
            cluster_modalities=cluster_modalities,
            answerable_ids=answerable_ids,
            rank_base=0,
        )
    )
    candidates.extend(
        _multi_attempt_candidates(
            attempt=runner.ATTEMPT_005,
            canonical_cases=canonical_cases,
            canonical_gold=canonical_gold,
            cluster_modalities=cluster_modalities,
            answerable_ids=answerable_ids,
            rank_base=100,
        )
    )
    candidates.extend(
        _multi_attempt_candidates(
            attempt=runner.ATTEMPT_004,
            canonical_cases=canonical_cases,
            canonical_gold=canonical_gold,
            cluster_modalities=cluster_modalities,
            answerable_ids=answerable_ids,
            rank_base=200,
        )
    )
    candidates.extend(_attempt_003_candidates(answerable_ids=answerable_ids))
    grouped: dict[str, list[AcceptedQuestion]] = {}
    for candidate in sorted(
        candidates,
        key=lambda row: (row.case_id, row.rank, normalize_question(row.question)),
    ):
        existing = grouped.setdefault(candidate.case_id, [])
        if normalize_question(candidate.question) in {
            normalize_question(row.question) for row in existing
        }:
            continue
        existing.append(candidate)
    return grouped


def _case_position(case_id: str) -> str:
    position = case_id.rsplit("-", 1)[-1]
    if position not in {"q1", "q2", "q3", "q4", "q5"}:
        raise ReferenceAggregateError(f"unknown question position: {case_id}")
    return position


def build_payloads() -> dict[Path, dict[str, Any]]:
    instrument = _load_hashed(
        INSTRUMENT_PATH, identity_key="instrument_id", identity=INSTRUMENT_ID
    )
    pool = build_reference_pool()
    canonical_cases, canonical_gold = runner._canonical_rows(pool)  # noqa: SLF001
    case_by_id = {row.case_id: row for row in canonical_cases}
    gold_by_id = {row.case_id: row for row in canonical_gold}
    grouped = _accepted_questions(
        canonical_cases=canonical_cases,
        canonical_gold=canonical_gold,
        pool=pool,
    )

    selected_cases: list[EvaluationCaseV1] = []
    selected_gold: list[EvaluationGoldV1] = []
    provenance_rows: list[dict[str, str]] = []
    used_questions: set[str] = set()
    for course_id in COURSES:
        for position in ("q1", "q2", "q3", "q4"):
            required = ANSWER_QUOTAS[course_id][position]
            selected_for_cell = 0
            for case_id in sorted(grouped):
                case = case_by_id[case_id]
                if case.course_id != course_id or _case_position(case_id) != position:
                    continue
                chosen = next(
                    (
                        candidate
                        for candidate in grouped[case_id]
                        if normalize_question(candidate.question) not in used_questions
                    ),
                    None,
                )
                if chosen is None:
                    continue
                used_questions.add(normalize_question(chosen.question))
                selected_cases.append(
                    case.model_copy(
                        update={
                            "question": chosen.question,
                            "author_family": "blind-validated-aggregate-007",
                        }
                    )
                )
                selected_gold.append(gold_by_id[case_id])
                provenance_rows.append(
                    {
                        "case_id": case_id,
                        "question_provenance": chosen.provenance,
                    }
                )
                selected_for_cell += 1
                if selected_for_cell == required:
                    break
            if selected_for_cell != required:
                raise ReferenceAggregateError(
                    f"answer quota shortfall: {course_id}:{position} "
                    f"{selected_for_cell}/{required}"
                )

    boundary_cases = [
        row
        for row in canonical_cases
        if gold_by_id[row.case_id].expected_action != EvaluationAction.ANSWER
    ]
    for course_id in COURSES:
        for slice_id in BOUNDARY_SLICES:
            required = BOUNDARY_QUOTAS[course_id][slice_id]
            candidates = [
                row
                for row in boundary_cases
                if row.course_id == course_id and row.slice == slice_id
            ]
            if len(candidates) < required:
                raise ReferenceAggregateError(
                    f"boundary quota shortfall: {course_id}:{slice_id}"
                )
            for case in sorted(candidates, key=lambda row: row.case_id)[:required]:
                normalized = normalize_question(case.question)
                if normalized in used_questions:
                    raise ReferenceAggregateError("boundary question is duplicated")
                expected = gold_by_id[case.case_id]
                if expected.claims:
                    raise ReferenceAggregateError("boundary gold has evidence lineage")
                used_questions.add(normalized)
                selected_cases.append(case)
                selected_gold.append(expected)
                provenance_rows.append(
                    {
                        "case_id": case.case_id,
                        "question_provenance": "deterministic-boundary-template-v1",
                    }
                )

    selected_cases.sort(key=lambda row: row.case_id)
    selected_gold.sort(key=lambda row: row.case_id)
    provenance_rows.sort(key=lambda row: row["case_id"])
    if len(selected_cases) != 500 or len(selected_gold) != 500:
        raise ReferenceAggregateError("aggregate package is not 500 cases")
    if len({row.case_id for row in selected_cases}) != 500:
        raise ReferenceAggregateError("aggregate case IDs are duplicated")
    if len(used_questions) != 500:
        raise ReferenceAggregateError("aggregate questions are duplicated")

    action_counts = Counter(
        gold_by_id[row.case_id].expected_action.value for row in selected_cases
    )
    course_counts = Counter(row.course_id for row in selected_cases)
    position_counts = Counter(_case_position(row.case_id) for row in selected_cases)
    if action_counts["answer"] != 400 or sum(action_counts.values()) != 500:
        raise ReferenceAggregateError("aggregate action distribution drifted")
    if course_counts != Counter({course_id: 125 for course_id in COURSES}):
        raise ReferenceAggregateError("aggregate course distribution drifted")
    if any(position_counts[position] != 100 for position in ("q1", "q2", "q3", "q4", "q5")):
        raise ReferenceAggregateError("aggregate position distribution drifted")

    selected_cluster_ids = {row.cluster_id for row in selected_cases}
    selected_clusters = [
        SourceClusterV2.model_validate(row)
        for row in pool["clusters"]
        if row["cluster_id"] in selected_cluster_ids
    ]
    chunks = registered_source_chunks(selected_clusters)

    def package(dataset_id: str, rows_key: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": 1,
            "dataset_id": dataset_id,
            "construction_instrument_id": INSTRUMENT_ID,
            "case_count": len(rows),
            rows_key: rows,
            "private_data_used": False,
            "final_split_opened": False,
        }
        payload["content_sha256"] = canonical_json_sha256(payload)
        return payload

    cases_payload = package(
        DATASET_ID,
        "cases",
        [row.model_dump(mode="json") for row in selected_cases],
    )
    cases_payload["question_provenance"] = provenance_rows
    cases_payload["content_sha256"] = canonical_json_sha256(
        {key: row for key, row in cases_payload.items() if key != "content_sha256"}
    )
    gold_payload = package(
        DATASET_ID + "-gold",
        "gold",
        [row.model_dump(mode="json") for row in selected_gold],
    )
    source_payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": DATASET_ID + "-sources",
        "construction_instrument_id": INSTRUMENT_ID,
        "cluster_count": len(selected_clusters),
        "case_count": 500,
        "clusters": [row.model_dump(mode="json") for row in selected_clusters],
        "chunks": [row.model_dump(mode="json") for row in chunks],
        "private_data_used": False,
        "final_split_opened": False,
    }
    source_payload["content_sha256"] = canonical_json_sha256(source_payload)
    selected_case_by_id = {row.case_id: row for row in selected_cases}
    selected_gold_by_id = {row.case_id: row for row in selected_gold}
    control_ids: list[str] = []
    for course_id in COURSES:
        for position in ("q1", "q2", "q3", "q4"):
            eligible = sorted(
                row.case_id
                for row in selected_cases
                if row.course_id == course_id and _case_position(row.case_id) == position
            )
            control_ids.extend(eligible[:5])
        boundaries = sorted(
            row.case_id
            for row in selected_cases
            if row.course_id == course_id and _case_position(row.case_id) == "q5"
        )
        control_ids.extend(boundaries[:5])
    if len(control_ids) != 100 or len(set(control_ids)) != 100:
        raise ReferenceAggregateError("paired control subset drifted")
    control_cases_payload = package(
        DATASET_ID + "-control",
        "cases",
        [selected_case_by_id[case_id].model_dump(mode="json") for case_id in control_ids],
    )
    control_gold_payload = package(
        DATASET_ID + "-control-gold",
        "gold",
        [selected_gold_by_id[case_id].model_dump(mode="json") for case_id in control_ids],
    )
    if instrument["acceptance"]["case_count_required"] != 500:
        raise ReferenceAggregateError("instrument case target drifted")
    return {
        CASES_PATH: cases_payload,
        GOLD_PATH: gold_payload,
        SOURCES_PATH: source_payload,
        CONTROL_CASES_PATH: control_cases_payload,
        CONTROL_GOLD_PATH: control_gold_payload,
    }


def _write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise ReferenceAggregateError(f"output already exists: {path.name}")
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def build() -> dict[str, Any]:
    payloads = build_payloads()
    for path, payload in payloads.items():
        if path.exists():
            if _load(path) != payload:
                raise ReferenceAggregateError(f"existing output drifted: {path.name}")
            continue
        _write_exclusive(path, payload)
    return summary(payloads)


def _validate_package(
    path: Path,
    *,
    dataset_id: str,
    rows_key: str | None = None,
) -> dict[str, Any]:
    payload = _load_hashed(path, identity_key="dataset_id", identity=dataset_id)
    if payload.get("construction_instrument_id") != INSTRUMENT_ID:
        raise ReferenceAggregateError(f"construction identity drifted: {path.name}")
    if payload.get("private_data_used") is not False:
        raise ReferenceAggregateError(f"private-data boundary drifted: {path.name}")
    if payload.get("final_split_opened") is not False:
        raise ReferenceAggregateError(f"final-split boundary drifted: {path.name}")
    if rows_key is not None:
        rows = payload.get(rows_key)
        if not isinstance(rows, list) or payload.get("case_count") != len(rows):
            raise ReferenceAggregateError(f"row count drifted: {path.name}")
    return payload


def validate_packages() -> dict[Path, dict[str, Any]]:
    """Validate committed packages without requiring ignored provider ledgers."""

    instrument = _load_hashed(
        INSTRUMENT_PATH, identity_key="instrument_id", identity=INSTRUMENT_ID
    )
    cases_payload = _validate_package(
        CASES_PATH, dataset_id=DATASET_ID, rows_key="cases"
    )
    gold_payload = _validate_package(
        GOLD_PATH, dataset_id=DATASET_ID + "-gold", rows_key="gold"
    )
    sources_payload = _validate_package(
        SOURCES_PATH, dataset_id=DATASET_ID + "-sources"
    )
    control_cases_payload = _validate_package(
        CONTROL_CASES_PATH, dataset_id=DATASET_ID + "-control", rows_key="cases"
    )
    control_gold_payload = _validate_package(
        CONTROL_GOLD_PATH,
        dataset_id=DATASET_ID + "-control-gold",
        rows_key="gold",
    )

    cases = [EvaluationCaseV1.model_validate(row) for row in cases_payload["cases"]]
    gold = [EvaluationGoldV1.model_validate(row) for row in gold_payload["gold"]]
    control_cases = [
        EvaluationCaseV1.model_validate(row) for row in control_cases_payload["cases"]
    ]
    control_gold = [
        EvaluationGoldV1.model_validate(row) for row in control_gold_payload["gold"]
    ]
    clusters = [
        SourceClusterV2.model_validate(row) for row in sources_payload.get("clusters", [])
    ]
    if sources_payload.get("cluster_count") != len(clusters):
        raise ReferenceAggregateError("source cluster count drifted")
    if sources_payload.get("case_count") != 500:
        raise ReferenceAggregateError("source package case count drifted")

    case_by_id = {row.case_id: row for row in cases}
    gold_by_id = {row.case_id: row for row in gold}
    if len(cases) != 500 or len(case_by_id) != 500:
        raise ReferenceAggregateError("aggregate case identities drifted")
    if len(gold) != 500 or set(gold_by_id) != set(case_by_id):
        raise ReferenceAggregateError("aggregate gold identities drifted")
    if len({normalize_question(row.question) for row in cases}) != 500:
        raise ReferenceAggregateError("aggregate questions are duplicated")

    action_counts = Counter(row.expected_action.value for row in gold)
    course_counts = Counter(row.course_id for row in cases)
    position_counts = Counter(_case_position(row.case_id) for row in cases)
    if action_counts["answer"] != 400 or sum(action_counts.values()) != 500:
        raise ReferenceAggregateError("aggregate action distribution drifted")
    if course_counts != Counter({course_id: 125 for course_id in COURSES}):
        raise ReferenceAggregateError("aggregate course distribution drifted")
    if any(
        position_counts[position] != 100
        for position in ("q1", "q2", "q3", "q4", "q5")
    ):
        raise ReferenceAggregateError("aggregate position distribution drifted")
    for row in gold:
        if row.expected_action == EvaluationAction.ANSWER and not row.claims:
            raise ReferenceAggregateError(f"answer lineage missing: {row.case_id}")
        if row.expected_action != EvaluationAction.ANSWER and row.claims:
            raise ReferenceAggregateError(f"boundary lineage present: {row.case_id}")

    control_case_ids = [row.case_id for row in control_cases]
    control_gold_ids = [row.case_id for row in control_gold]
    if len(control_case_ids) != 100 or len(set(control_case_ids)) != 100:
        raise ReferenceAggregateError("control case identities drifted")
    if control_case_ids != control_gold_ids:
        raise ReferenceAggregateError("control gold ordering drifted")
    if not set(control_case_ids).issubset(case_by_id):
        raise ReferenceAggregateError("control cases are outside the candidate package")
    control_course_counts = Counter(row.course_id for row in control_cases)
    control_position_counts = Counter(_case_position(row.case_id) for row in control_cases)
    if control_course_counts != Counter({course_id: 25 for course_id in COURSES}):
        raise ReferenceAggregateError("control course distribution drifted")
    if any(
        control_position_counts[position] != 20
        for position in ("q1", "q2", "q3", "q4", "q5")
    ):
        raise ReferenceAggregateError("control position distribution drifted")

    provenance = cases_payload.get("question_provenance")
    if not isinstance(provenance, list) or {
        row.get("case_id") for row in provenance if isinstance(row, dict)
    } != set(case_by_id):
        raise ReferenceAggregateError("question provenance drifted")
    if instrument["acceptance"]["case_count_required"] != len(cases):
        raise ReferenceAggregateError("instrument case target drifted")
    return {
        CASES_PATH: cases_payload,
        GOLD_PATH: gold_payload,
        SOURCES_PATH: sources_payload,
        CONTROL_CASES_PATH: control_cases_payload,
        CONTROL_GOLD_PATH: control_gold_payload,
    }


def check() -> dict[str, Any]:
    return summary(validate_packages())


def summary(payloads: dict[Path, dict[str, Any]]) -> dict[str, Any]:
    cases = payloads[CASES_PATH]
    gold = payloads[GOLD_PATH]
    sources = payloads[SOURCES_PATH]
    control_cases = payloads[CONTROL_CASES_PATH]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-question-stratified-reference-package",
        "case_count": cases["case_count"],
        "answerable_count": sum(
            row["expected_action"] == "answer" for row in gold["gold"]
        ),
        "boundary_count": sum(
            row["expected_action"] != "answer" for row in gold["gold"]
        ),
        "source_cluster_count": sources["cluster_count"],
        "control_case_count": control_cases["case_count"],
        "cases_content_sha256": cases["content_sha256"],
        "gold_content_sha256": gold["content_sha256"],
        "sources_content_sha256": sources["content_sha256"],
        "provider_calls": 0,
        "product_calls": 0,
        "final_split_opened": False,
    }


def main() -> int:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "dataset_generation")
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true")
    group.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    result = build() if arguments.build else check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
