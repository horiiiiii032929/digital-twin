"""Construction contracts for the open 10,000-case factual-QA benchmark."""

from __future__ import annotations

import hashlib
import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.digital_twin.evaluation.factual_qa_contract import (
    CanonicalEvidenceRefV1,
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationClaimV1,
    EvaluationGoldV1,
    EvaluationSplit,
)


class SourceClusterV1(BaseModel):
    """One non-overlapping source window offered to the authoring models."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, frozen=True)
    cluster_id: str = Field(min_length=1)
    source_family_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    source_version: int = Field(ge=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_path: str = Field(min_length=1)
    section_heading: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)
    text: str = Field(min_length=1)
    source_modality: str = Field(min_length=1)
    split: EvaluationSplit
    answerable_slices: list[str] = Field(min_length=4, max_length=4)
    boundary_slice: str = Field(min_length=1)
    author_family: str = Field(min_length=1)
    verifier_family: str = Field(min_length=1)
    license_spdx: str = Field(min_length=1)
    repository_url: str = Field(min_length=1)
    repository_commit: str = Field(pattern=r"^[0-9a-f]{40}$")

    @model_validator(mode="after")
    def validate_lineage_and_roles(self) -> "SourceClusterV1":
        if self.char_end <= self.char_start:
            raise ValueError("source cluster range must be non-empty")
        if len(set(self.answerable_slices)) != 4:
            raise ValueError("a cluster requires four distinct answerable slices")
        extended_slice = self.answerable_slices[-1]
        if extended_slice.startswith("structured-") and extended_slice != self.source_modality:
            raise ValueError("structured slice does not match the source-window modality")
        if self.author_family == self.verifier_family:
            raise ValueError("author and verifier model families must differ")
        return self


class DraftEvidenceSpanV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote: str = Field(min_length=1)
    relative_char_start: int = Field(ge=0)
    relative_char_end: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_range(self) -> "DraftEvidenceSpanV1":
        if self.relative_char_end <= self.relative_char_start:
            raise ValueError("draft evidence range must be non-empty")
        return self


class DraftQuestionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    action: EvaluationAction
    answer: str = Field(min_length=1)
    evidence_spans: list[DraftEvidenceSpanV1] = Field(default_factory=list)
    boundary_reason: str | None = None

    @model_validator(mode="after")
    def validate_action(self) -> "DraftQuestionV1":
        if self.action == EvaluationAction.ANSWER:
            if not self.evidence_spans or self.boundary_reason is not None:
                raise ValueError("answer draft requires evidence and no boundary reason")
        elif self.action != EvaluationAction.OPERATIONAL_FAILURE:
            if self.evidence_spans or not self.boundary_reason:
                raise ValueError("boundary draft requires no evidence and a reason")
        return self


class ClusterDraftV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cluster_id: str = Field(min_length=1)
    questions: list[DraftQuestionV1] = Field(min_length=5, max_length=5)

    @field_validator("questions")
    @classmethod
    def questions_must_be_unique(cls, rows: list[DraftQuestionV1]) -> list[DraftQuestionV1]:
        identifiers = [row.case_id for row in rows]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("draft case IDs must be unique")
        return rows


def normalize_question(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def _validated_ref(
    cluster: SourceClusterV1,
    span: DraftEvidenceSpanV1,
) -> CanonicalEvidenceRefV1:
    if span.relative_char_end > len(cluster.text):
        raise ValueError("evidence range exceeds its source cluster")
    if cluster.text[span.relative_char_start : span.relative_char_end] != span.quote:
        raise ValueError("evidence quote is not exact at the claimed source range")
    return CanonicalEvidenceRefV1(
        source_artifact_id=cluster.source_artifact_id,
        source_version=cluster.source_version,
        source_sha256=cluster.source_sha256,
        char_start=cluster.char_start + span.relative_char_start,
        char_end=cluster.char_start + span.relative_char_end,
    )


def assemble_verified_cluster(
    cluster: SourceClusterV1,
    author: ClusterDraftV1,
    verifier: ClusterDraftV1,
) -> tuple[list[EvaluationCaseV1], list[EvaluationGoldV1]]:
    """Accept only exact author/verifier agreement over source-derived truth."""

    if author.cluster_id != cluster.cluster_id or verifier.cluster_id != cluster.cluster_id:
        raise ValueError("cluster draft identity mismatch")
    author_by_id = {row.case_id: row for row in author.questions}
    verifier_by_id = {row.case_id: row for row in verifier.questions}
    if author_by_id.keys() != verifier_by_id.keys():
        raise ValueError("author and verifier case sets differ")
    expected_ids = [f"{cluster.cluster_id}-q{index}" for index in range(1, 6)]
    if sorted(author_by_id) != expected_ids:
        raise ValueError("cluster drafts do not contain the five frozen case IDs")

    cases: list[EvaluationCaseV1] = []
    gold: list[EvaluationGoldV1] = []
    for index, case_id in enumerate(expected_ids):
        authored = author_by_id[case_id]
        verified = verifier_by_id[case_id]
        if authored.action != verified.action:
            raise ValueError(f"action disagreement for {case_id}")
        author_spans = [row.model_dump(mode="json") for row in authored.evidence_spans]
        verifier_spans = [row.model_dump(mode="json") for row in verified.evidence_spans]
        if authored.action == EvaluationAction.ANSWER:
            if authored.answer.strip() != verified.answer.strip() or author_spans != verifier_spans:
                raise ValueError(f"answer or evidence disagreement for {case_id}")
            refs = [_validated_ref(cluster, row) for row in authored.evidence_spans]
            if authored.answer not in cluster.text:
                raise ValueError(f"canonical answer is not an exact source span: {case_id}")
            claims = [
                EvaluationClaimV1(
                    claim_id=f"{case_id}-claim-{claim_index}",
                    answer_span=span.quote,
                    evidence_refs=[ref],
                )
                for claim_index, (span, ref) in enumerate(
                    zip(authored.evidence_spans, refs, strict=True), start=1
                )
            ]
            slice_name = cluster.answerable_slices[index]
        else:
            if authored.boundary_reason != verified.boundary_reason:
                raise ValueError(f"boundary-reason disagreement for {case_id}")
            if authored.answer.strip() != verified.answer.strip():
                raise ValueError(f"boundary-answer disagreement for {case_id}")
            claims = []
            slice_name = cluster.boundary_slice

        cases.append(
            EvaluationCaseV1(
                case_id=case_id,
                cluster_id=cluster.cluster_id,
                source_family_id=cluster.source_family_id,
                course_id=cluster.course_id,
                question=authored.question,
                split=cluster.split,
                slice=slice_name,
                author_family=cluster.author_family,
            )
        )
        gold.append(
            EvaluationGoldV1(
                case_id=case_id,
                expected_action=authored.action,
                canonical_answer=authored.answer,
                claims=claims,
                boundary_reason=authored.boundary_reason,
            )
        )

    normalized = [normalize_question(row.question) for row in cases]
    if len(normalized) != len(set(normalized)):
        raise ValueError("cluster contains normalized duplicate questions")
    return cases, gold


def source_cluster_hash(cluster: SourceClusterV1) -> str:
    return hashlib.sha256(
        cluster.model_dump_json(exclude={"answerable_slices", "boundary_slice"}).encode(
            "utf-8"
        )
    ).hexdigest()
