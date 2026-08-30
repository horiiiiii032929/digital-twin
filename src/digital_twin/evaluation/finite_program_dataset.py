"""Deterministic construction helpers for the finite 10,000-case program."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Protocol

from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
    EvaluationSplit,
)
from src.digital_twin.evaluation.factual_qa_dataset import (
    AuthoredClusterVariantsV1,
    ClusterDraftV1,
    SourceClusterV1,
    assemble_deterministic_verified_cluster,
    build_deterministic_cluster_truth_v2,
    normalize_question,
)
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256


COURSE_IDS = (
    "operating-systems",
    "computer-networking",
    "data-structures",
    "python-programming",
)


class BaseModelLike(Protocol):
    """Small structural contract used by package serialization."""

    def model_dump(self, *, mode: str) -> dict[str, Any]: ...


class FiniteProgramDatasetError(ValueError):
    """Raised when deterministic final construction violates its frozen design."""


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FiniteProgramDatasetError("dataset input is unavailable or malformed") from error
    if not isinstance(value, dict):
        raise FiniteProgramDatasetError("dataset JSON root must be an object")
    return value


def _unique_canonical_question(
    case: EvaluationCaseV1,
    *,
    cluster: SourceClusterV1,
    seen: set[str],
) -> EvaluationCaseV1:
    normalized = normalize_question(case.question)
    if normalized not in seen:
        seen.add(normalized)
        return case
    source_name = Path(cluster.source_path).stem.replace("_", " ").replace("-", " ")
    suffix = hashlib.sha256(case.case_id.encode("utf-8")).hexdigest()[:8]
    question = (
        f"{case.question.rstrip('?.!')} in the source section "
        f'"{source_name}: {cluster.section_heading}" (source example {suffix})?'
    )
    normalized = normalize_question(question)
    if normalized in seen:
        raise FiniteProgramDatasetError("canonical fallback cannot be made unique")
    seen.add(normalized)
    return case.model_copy(update={"question": question})


def build_canonical_final_rows(
    source_plan_path: Path,
) -> tuple[list[EvaluationCaseV1], list[EvaluationGoldV1], dict[str, Any]]:
    """Build source-linked canonical truth without a provider or model judgment."""

    plan = _load_object(source_plan_path)
    raw_clusters = [
        row for row in plan.get("clusters", []) if row.get("split") == "final"
    ]
    clusters = [SourceClusterV1.model_validate(row) for row in raw_clusters]
    if len(clusters) != 2_000:
        raise FiniteProgramDatasetError("final source plan must contain 2,000 clusters")
    if len({row.cluster_id for row in clusters}) != len(clusters):
        raise FiniteProgramDatasetError("final source clusters must be unique")

    cases: list[EvaluationCaseV1] = []
    gold: list[EvaluationGoldV1] = []
    seen_questions: set[str] = set()
    for original in sorted(clusters, key=lambda row: row.cluster_id):
        cluster = original.model_copy(
            update={
                "author_family": "deterministic-canonical-final-v1",
                "verifier_family": "deterministic-source-validator-v1",
            }
        )
        truth = build_deterministic_cluster_truth_v2(cluster, course_ids=COURSE_IDS)
        authored = AuthoredClusterVariantsV1(
            cluster_id=cluster.cluster_id,
            questions=[
                {"case_id": row.case_id, "question": row.canonical_question}
                for row in truth.questions
            ],
        )
        verifier = ClusterDraftV1(
            cluster_id=cluster.cluster_id,
            questions=[
                {
                    "case_id": row.case_id,
                    "question": authored.questions[index].question,
                    "action": row.action,
                    "answer": row.canonical_answer,
                    "evidence_spans": [
                        span.model_dump(mode="json") for span in row.evidence_spans
                    ],
                    "boundary_reason": row.boundary_reason,
                }
                for index, row in enumerate(truth.questions)
            ],
        )
        cluster_cases, cluster_gold = assemble_deterministic_verified_cluster(
            cluster, truth, authored, verifier
        )
        cases.extend(
            _unique_canonical_question(row, cluster=cluster, seen=seen_questions)
            for row in cluster_cases
        )
        gold.extend(cluster_gold)

    ordered_cases = sorted(cases, key=lambda row: row.case_id)
    ordered_gold = sorted(gold, key=lambda row: row.case_id)
    validate_final_rows(ordered_cases, ordered_gold)
    diagnostics = {
        "source_plan_sha256": str(plan.get("content_sha256", "")),
        "cluster_count": len(clusters),
        "case_count": len(ordered_cases),
        "answerable_count": sum(
            row.expected_action == EvaluationAction.ANSWER for row in ordered_gold
        ),
        "boundary_count": sum(
            row.expected_action != EvaluationAction.ANSWER for row in ordered_gold
        ),
        "course_distribution": dict(
            sorted(Counter(row.course_id for row in ordered_cases).items())
        ),
        "slice_distribution": dict(
            sorted(Counter(row.slice for row in ordered_cases).items())
        ),
        "provider_calls": 0,
        "private_data_used": False,
    }
    diagnostics["canonical_rows_sha256"] = canonical_json_sha256(
        {
            "cases": [row.model_dump(mode="json") for row in ordered_cases],
            "gold": [row.model_dump(mode="json") for row in ordered_gold],
        }
    )
    return ordered_cases, ordered_gold, diagnostics


def validate_final_rows(
    cases: list[EvaluationCaseV1], gold: list[EvaluationGoldV1]
) -> None:
    if len(cases) != 10_000 or len(gold) != 10_000:
        raise FiniteProgramDatasetError("final benchmark must contain 10,000 rows")
    case_ids = [row.case_id for row in cases]
    gold_ids = [row.case_id for row in gold]
    if len(case_ids) != len(set(case_ids)) or set(case_ids) != set(gold_ids):
        raise FiniteProgramDatasetError("public and gold identities must match uniquely")
    if any(row.split != EvaluationSplit.FINAL for row in cases):
        raise FiniteProgramDatasetError("final public package contains another split")
    answerable = [row for row in gold if row.expected_action == EvaluationAction.ANSWER]
    boundary = [row for row in gold if row.expected_action != EvaluationAction.ANSWER]
    if len(answerable) != 8_000 or len(boundary) != 2_000:
        raise FiniteProgramDatasetError("final action distribution drifted")
    normalized = [normalize_question(row.question) for row in cases]
    if len(normalized) != len(set(normalized)):
        raise FiniteProgramDatasetError("final questions contain exact normalized duplicates")
    gold_by_id = {row.case_id: row for row in gold}
    for case in cases:
        reference = gold_by_id[case.case_id]
        if reference.expected_action == EvaluationAction.ANSWER:
            normalized_answer = normalize_question(reference.canonical_answer)
            if normalized_answer and normalized_answer in normalize_question(case.question):
                raise FiniteProgramDatasetError(
                    f"public question leaks its canonical answer: {case.case_id}"
                )
            if not reference.claims:
                raise FiniteProgramDatasetError("answerable final case lacks claims")
        elif reference.claims:
            raise FiniteProgramDatasetError("boundary final case acquired evidence")


def apply_reviewed_wording(
    canonical_cases: list[EvaluationCaseV1],
    gold: list[EvaluationGoldV1],
    *,
    authored_questions: dict[str, str],
    verifier_rows: dict[str, dict[str, Any]],
) -> tuple[list[EvaluationCaseV1], list[dict[str, str]]]:
    """Accept wording only when the independent answer/action matches truth."""

    gold_by_id = {row.case_id: row for row in gold}
    accepted_questions: set[str] = set()
    output: list[EvaluationCaseV1] = []
    provenance: list[dict[str, str]] = []
    for canonical in sorted(canonical_cases, key=lambda row: row.case_id):
        reference = gold_by_id[canonical.case_id]
        candidate = authored_questions.get(canonical.case_id, "").strip()
        vote = verifier_rows.get(canonical.case_id)
        accepted = False
        reason = "missing-model-output"
        if candidate and isinstance(vote, dict):
            action = str(vote.get("action", ""))
            answer = str(vote.get("answer", "")).strip()
            evidence_quotes = vote.get("evidence_quotes", [])
            expected_quotes = [
                claim.answer_span for claim in reference.claims
            ]
            accepted = (
                action == reference.expected_action.value
                and bool(vote.get("faithful", False))
                and (
                    (reference.expected_action == EvaluationAction.ANSWER
                    and answer == reference.canonical_answer
                    and evidence_quotes == expected_quotes)
                    or (
                        reference.expected_action != EvaluationAction.ANSWER
                        and not evidence_quotes
                    )
                )
                and normalize_question(reference.canonical_answer)
                not in normalize_question(candidate)
            )
            reason = "accepted-model-wording" if accepted else "verifier-disagreement"
        normalized = normalize_question(candidate) if accepted else ""
        if accepted and normalized in accepted_questions:
            accepted = False
            reason = "normalized-duplicate"
        if accepted:
            selected = canonical.model_copy(
                update={
                    "question": candidate,
                    "author_family": "gpt-5.4-nano-wording-v1",
                }
            )
            accepted_questions.add(normalized)
        else:
            selected = canonical.model_copy(
                update={"author_family": "deterministic-canonical-fallback-v1"}
            )
            fallback = normalize_question(selected.question)
            if fallback in accepted_questions:
                raise FiniteProgramDatasetError(
                    "canonical fallback collides with accepted model wording"
                )
            accepted_questions.add(fallback)
        output.append(selected)
        provenance.append(
            {
                "case_id": canonical.case_id,
                "wording_provenance": selected.author_family,
                "decision": reason,
            }
        )
    validate_final_rows(output, gold)
    return output, provenance


def paired_control_subset(
    cases: list[EvaluationCaseV1], gold: list[EvaluationGoldV1]
) -> tuple[list[EvaluationCaseV1], list[EvaluationGoldV1]]:
    clusters = sorted(
        {row.cluster_id for row in cases},
        key=lambda value: hashlib.sha256(
            f"20260830:{value}".encode("utf-8")
        ).hexdigest(),
    )[:200]
    cluster_ids = set(clusters)
    selected_cases = [row for row in cases if row.cluster_id in cluster_ids]
    selected_ids = {row.case_id for row in selected_cases}
    selected_gold = [row for row in gold if row.case_id in selected_ids]
    if len(selected_cases) != 1_000 or len(selected_gold) != 1_000:
        raise FiniteProgramDatasetError("paired control must contain 200 complete clusters")
    return selected_cases, selected_gold


def package_rows(
    *,
    dataset_id: str,
    split: str,
    rows_key: str,
    rows: Iterable[BaseModelLike],
    source_plan_sha256: str,
) -> dict[str, Any]:
    values = [row.model_dump(mode="json") for row in rows]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "program_id": "course-digital-twin-evaluation-program-001",
        "split": split,
        "case_count": len(values),
        "source_plan_sha256": source_plan_sha256,
        rows_key: values,
        "private_data_used": False,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    return payload
