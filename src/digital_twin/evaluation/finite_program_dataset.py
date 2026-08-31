"""Deterministic construction helpers for the finite 10,000-case program."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Protocol

from src.digital_twin.evaluation.factual_qa_contract import (
    CanonicalEvidenceRefV1,
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
    EvaluationSplit,
)
from src.digital_twin.grounding import DocumentChunk
from src.digital_twin.grounding.source_registration import (
    canonical_region_id,
    registered_search_description,
)
from src.digital_twin.tutor_policy import SourceLabel
from src.digital_twin.evaluation.factual_qa_dataset import (
    AuthoredClusterVariantsV1,
    ClusterDraftV1,
    SourceClusterV1,
    assemble_deterministic_verified_cluster,
    build_deterministic_cluster_truth_v2,
    normalize_question,
    normalized_token_sequence_contains,
)
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256


COURSE_IDS = (
    "operating-systems",
    "computer-networking",
    "data-structures",
    "python-programming",
)
_QUESTION_CUE_STOPWORDS = {
    "about",
    "after",
    "course",
    "detail",
    "does",
    "example",
    "following",
    "provide",
    "section",
    "source",
    "state",
    "this",
    "what",
    "which",
}


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
    suffix = hashlib.sha256(case.case_id.encode("utf-8")).hexdigest()[:8]
    question = f"{case.question.rstrip('?.!')} (source example {suffix})?"
    normalized = normalize_question(question)
    if normalized in seen:
        raise FiniteProgramDatasetError("canonical fallback cannot be made unique")
    seen.add(normalized)
    return case.model_copy(update={"question": question})


def _safe_canonical_question(
    *, question: str, answer: str, cluster: SourceClusterV1, slice_name: str
) -> str:
    """Replace a rare answer-bearing template with a deterministic safe cue."""

    if not normalized_token_sequence_contains(question, answer):
        return question
    answer_tokens = set(normalize_question(answer).split())
    cue_tokens: list[str] = []
    for token in normalize_question(cluster.text).split():
        if (
            token in answer_tokens
            or token in _QUESTION_CUE_STOPWORDS
            or len(token) < 3
            or token in cue_tokens
        ):
            continue
        cue_tokens.append(token)
        if len(cue_tokens) == 4:
            break
    cue = " ".join(cue_tokens) or f"source example {cluster.cluster_id[-8:]}"
    detail = (
        "code or command detail"
        if slice_name == "structured-code"
        else "equation detail"
        if slice_name == "structured-equation"
        else "table detail"
        if slice_name == "structured-table"
        else "fact"
    )
    question_role = slice_name.replace("-", " ")
    replacement = (
        f"What {detail} is stated for the {question_role} case in the context "
        f"of {cue}?"
    )
    if normalized_token_sequence_contains(replacement, answer):
        replacement = (
            f"What {detail} is requested for the {question_role} case by source "
            f"example {cluster.cluster_id[-8:]}?"
        )
    if normalized_token_sequence_contains(replacement, answer):
        raise FiniteProgramDatasetError("safe canonical wording still leaks answer")
    return replacement


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
                {
                    "case_id": row.case_id,
                    "question": _safe_canonical_question(
                        question=row.canonical_question,
                        answer=row.canonical_answer,
                        cluster=cluster,
                        slice_name=(
                            cluster.answerable_slices[index]
                            if index < 4
                            else cluster.boundary_slice
                        ),
                    ),
                }
                for index, row in enumerate(truth.questions)
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


def build_atomic_final_rows(
    source_plan_path: Path,
    *,
    program_id: str,
) -> tuple[
    list[EvaluationCaseV1],
    list[EvaluationGoldV1],
    dict[str, Any],
    dict[str, Any],
]:
    """Create one non-overlapping authoritative retrieval corpus for final gold."""

    cases, gold, diagnostics = build_canonical_final_rows(source_plan_path)
    plan = _load_object(source_plan_path)
    clusters = [
        SourceClusterV1.model_validate(row)
        for row in plan.get("clusters", [])
        if row.get("split") == "final"
    ]
    clusters_by_source: dict[tuple[str, int, str], list[SourceClusterV1]] = {}
    for cluster in clusters:
        key = (
            cluster.source_artifact_id,
            cluster.source_version,
            cluster.source_sha256,
        )
        clusters_by_source.setdefault(key, []).append(cluster)

    reference_ranges: dict[
        tuple[str, int, str], set[tuple[int, int]]
    ] = {}
    for row in gold:
        if row.expected_action != EvaluationAction.ANSWER:
            continue
        for claim in row.claims:
            for reference in claim.evidence_refs:
                key = (
                    reference.source_artifact_id,
                    reference.source_version,
                    reference.source_sha256,
                )
                reference_ranges.setdefault(key, set()).add(
                    (reference.char_start, reference.char_end)
                )

    merged_ranges: dict[
        tuple[str, int, str], list[tuple[int, int]]
    ] = {}
    for key, values in reference_ranges.items():
        merged: list[list[int]] = []
        for start, end in sorted(values):
            if merged and start < merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        merged_ranges[key] = [(start, end) for start, end in merged]

    replacement: dict[
        tuple[str, int, str, int, int], CanonicalEvidenceRefV1
    ] = {}
    chunks: list[DocumentChunk] = []
    ordinals: dict[str, int] = {}
    for key, ranges in sorted(merged_ranges.items()):
        source_id, source_version, source_sha256 = key
        for start, end in ranges:
            containing = [
                cluster
                for cluster in clusters_by_source.get(key, [])
                if cluster.char_start <= start and cluster.char_end >= end
            ]
            if len(containing) != 1:
                raise FiniteProgramDatasetError(
                    "final authoritative range does not map to one source cluster"
                )
            cluster = containing[0]
            relative_start = start - cluster.char_start
            relative_end = end - cluster.char_start
            quote = cluster.text[relative_start:relative_end]
            if not quote.strip():
                raise FiniteProgramDatasetError("final authoritative range is empty")
            modality = cluster.source_modality
            region_id = canonical_region_id(
                source_artifact_id=source_id,
                source_version=source_version,
                source_sha256=source_sha256,
                char_start=start,
                char_end=end,
                modality=modality,
            )
            course_id = cluster.course_id
            ordinal = ordinals.get(course_id, 0)
            ordinals[course_id] = ordinal + 1
            chunks.append(
                DocumentChunk(
                    id=region_id,
                    document_id=source_id,
                    text=quote,
                    ordinal=ordinal,
                    source_artifact_id=source_id,
                    source_version=source_version,
                    source_label=SourceLabel.COURSE_APPROVED,
                    locator=f"{cluster.source_path} characters {start}–{end}",
                    region_id=region_id,
                    source_checksum=source_sha256,
                    retrieval_allowed=True,
                    display_allowed=True,
                    metadata={
                        "title": cluster.section_heading,
                        "course_id": course_id,
                        "char_start": str(start),
                        "char_end": str(end),
                        "source_path": cluster.source_path,
                        "source_family_id": cluster.source_family_id,
                        "parent_cluster_id": cluster.cluster_id,
                        "modality": modality,
                        "search_description": registered_search_description(
                            course_id=course_id,
                            section_heading=cluster.section_heading,
                            source_path=cluster.source_path,
                            modality=modality,
                            text=cluster.text,
                        ),
                    },
                )
            )
            for original_start, original_end in reference_ranges[key]:
                if start <= original_start and end >= original_end:
                    replacement[
                        (source_id, source_version, source_sha256, original_start, original_end)
                    ] = CanonicalEvidenceRefV1(
                        source_artifact_id=source_id,
                        source_version=source_version,
                        source_sha256=source_sha256,
                        char_start=start,
                        char_end=end,
                        region_id=region_id,
                    )

    rewritten_gold: list[EvaluationGoldV1] = []
    for row in gold:
        claims = []
        for claim in row.claims:
            refs = []
            for reference in claim.evidence_refs:
                key = (
                    reference.source_artifact_id,
                    reference.source_version,
                    reference.source_sha256,
                    reference.char_start,
                    reference.char_end,
                )
                if key not in replacement:
                    raise FiniteProgramDatasetError(
                        "final evidence reference was not atomized"
                    )
                refs.append(replacement[key])
            claims.append(claim.model_copy(update={"evidence_refs": refs}))
        rewritten_gold.append(row.model_copy(update={"claims": claims}))

    validate_final_rows(cases, rewritten_gold)
    source_payload: dict[str, Any] = {
        "schema_version": 1,
        "program_id": program_id,
        "construction_method": "merged-non-overlapping-authoritative-atoms-v1",
        "split": "final-retrieval-corpus",
        "cluster_count": len(clusters),
        "case_count": len(cases),
        "registered_region_count": len(chunks),
        "source_plan_sha256": diagnostics["source_plan_sha256"],
        "chunks": [row.model_dump(mode="json") for row in chunks],
        "authoritative_regions_non_overlapping": True,
        "provider_calls": 0,
        "private_data_used": False,
    }
    source_payload["content_sha256"] = canonical_json_sha256(source_payload)
    diagnostics = {
        **diagnostics,
        "original_unique_reference_count": sum(
            len(values) for values in reference_ranges.values()
        ),
        "registered_region_count": len(chunks),
        "merged_overlap_count": sum(
            len(reference_ranges[key]) - len(merged_ranges[key])
            for key in reference_ranges
        ),
    }
    return cases, rewritten_gold, diagnostics, source_payload


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
            if normalized_token_sequence_contains(
                case.question, reference.canonical_answer
            ):
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
                and not normalized_token_sequence_contains(
                    candidate, reference.canonical_answer
                )
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
    program_id: str = "course-digital-twin-evaluation-program-001",
) -> dict[str, Any]:
    values = [row.model_dump(mode="json") for row in rows]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "program_id": program_id,
        "split": split,
        "case_count": len(values),
        "source_plan_sha256": source_plan_sha256,
        rows_key: values,
        "private_data_used": False,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    return payload
