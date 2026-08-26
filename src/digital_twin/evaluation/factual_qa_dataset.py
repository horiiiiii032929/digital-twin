"""Construction contracts for the open 10,000-case factual-QA benchmark."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Sequence

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


class DeterministicQuestionTruthV1(BaseModel):
    """Authoritative source-derived truth before any model sees a prompt."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    canonical_question: str = Field(min_length=1)
    target_course_id: str = Field(min_length=1)
    action: EvaluationAction
    canonical_answer: str = Field(min_length=1)
    evidence_spans: list[DraftEvidenceSpanV1] = Field(default_factory=list)
    boundary_reason: str | None = None

    @model_validator(mode="after")
    def action_must_match_truth(self) -> "DeterministicQuestionTruthV1":
        if self.action == EvaluationAction.ANSWER:
            if not self.evidence_spans or self.boundary_reason is not None:
                raise ValueError("answer truth requires evidence and no boundary reason")
        elif self.action != EvaluationAction.OPERATIONAL_FAILURE:
            if self.evidence_spans or not self.boundary_reason:
                raise ValueError("boundary truth requires empty evidence and a reason")
        return self


class DeterministicClusterTruthV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, frozen=True)
    cluster_id: str = Field(min_length=1)
    questions: list[DeterministicQuestionTruthV1] = Field(min_length=5, max_length=5)

    @field_validator("questions")
    @classmethod
    def question_ids_must_be_unique(
        cls, rows: list[DeterministicQuestionTruthV1]
    ) -> list[DeterministicQuestionTruthV1]:
        identifiers = [row.case_id for row in rows]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("deterministic case IDs must be unique")
        return rows


class AuthoredQuestionVariantV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=500)


class AuthoredClusterVariantsV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cluster_id: str = Field(min_length=1)
    questions: list[AuthoredQuestionVariantV1] = Field(min_length=5, max_length=5)


_WORD = re.compile(r"\S+")
_SENTENCE = re.compile(r"[^\n.!?]+(?:[.!?]+|$)")


def _candidate_exact_spans(text: str) -> list[DraftEvidenceSpanV1]:
    candidates: list[DraftEvidenceSpanV1] = []
    for match in _SENTENCE.finditer(text):
        raw = match.group(0)
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        start = match.start() + left
        end = match.start() + right
        quote = text[start:end]
        word_count = len(_WORD.findall(quote))
        if 3 <= word_count <= 30 and re.search(r"[A-Za-z0-9]", quote):
            candidates.append(
                DraftEvidenceSpanV1(
                    quote=quote,
                    relative_char_start=start,
                    relative_char_end=end,
                )
            )
    if len(candidates) >= 2:
        return candidates

    tokens = list(_WORD.finditer(text))
    if len(tokens) < 4:
        raise ValueError("source cluster is too short for two source-derived claims")
    chunk_size = max(2, min(24, len(tokens) // 2))
    for index in range(2):
        token_start = min(index * chunk_size, len(tokens) - 1)
        token_end = min(len(tokens), token_start + chunk_size)
        if index == 1:
            token_end = min(len(tokens), token_start + 24)
        start = tokens[token_start].start()
        end = tokens[token_end - 1].end()
        quote = text[start:end]
        candidates.append(
            DraftEvidenceSpanV1(
                quote=quote,
                relative_char_start=start,
                relative_char_end=end,
            )
        )

    unique: list[DraftEvidenceSpanV1] = []
    relationships: set[tuple[int, int]] = set()
    for row in candidates:
        relationship = (row.relative_char_start, row.relative_char_end)
        if relationship not in relationships:
            relationships.add(relationship)
            unique.append(row)
    if len(unique) < 2:
        raise ValueError("source cluster cannot yield two distinct exact spans")
    return unique


def _question_cue(span: DraftEvidenceSpanV1) -> str:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", span.quote)
    limit = 1 if len(words) <= 3 else 3
    return " ".join(words[:limit]) or "the highlighted concept"


def _other_course(course_id: str, course_ids: Sequence[str]) -> str:
    ordered = sorted(set(course_ids))
    if course_id not in ordered or len(ordered) < 2:
        raise ValueError("cross-course boundary construction requires two courses")
    return ordered[(ordered.index(course_id) + 1) % len(ordered)]


def build_deterministic_cluster_truth(
    cluster: SourceClusterV1,
    *,
    course_ids: Sequence[str],
) -> DeterministicClusterTruthV1:
    """Derive source truth before authoring so no model can define its own gold."""

    spans = _candidate_exact_spans(cluster.text)
    selected = [spans[0], spans[0], spans[0], spans[1]]
    answerable: list[DeterministicQuestionTruthV1] = []
    for index, (slice_name, span) in enumerate(
        zip(cluster.answerable_slices, selected, strict=True), start=1
    ):
        evidence = [span]
        if slice_name == "multi-evidence":
            evidence = [selected[0], selected[3]]
        canonical_answer = " ".join(row.quote for row in evidence)
        cue = _question_cue(span)
        question = {
            "direct-factual": (
                f'According to "{cluster.section_heading}", what exact fact is stated '
                f"about {cue}?"
            ),
            "paraphrased": (
                f'In "{cluster.section_heading}", how can the point about {cue} be '
                "restated?"
            ),
            "definition-explanation": (
                f'How does "{cluster.section_heading}" explain the concept involving '
                f"{cue}?"
            ),
            "multi-evidence": (
                f'Which two source statements in "{cluster.section_heading}" together '
                f"explain {cue}?"
            ),
        }.get(
            slice_name,
            f'What structured detail in "{cluster.section_heading}" shows {cue}?',
        )
        answerable.append(
            DeterministicQuestionTruthV1(
                case_id=f"{cluster.cluster_id}-q{index}",
                canonical_question=question,
                target_course_id=cluster.course_id,
                action=EvaluationAction.ANSWER,
                canonical_answer=canonical_answer,
                evidence_spans=evidence,
            )
        )

    boundary_case_id = f"{cluster.cluster_id}-q5"
    if cluster.boundary_slice == "no-evidence":
        boundary = DeterministicQuestionTruthV1(
            case_id=boundary_case_id,
            canonical_question=(
                f'What material about {_question_cue(selected[0])} will be added to '
                f'"{cluster.section_heading}" next academic year?'
            ),
            target_course_id=cluster.course_id,
            action=EvaluationAction.ABSTAIN,
            canonical_answer="The approved course evidence does not establish that.",
            boundary_reason="no-evidence",
        )
    elif cluster.boundary_slice == "cross-course":
        boundary = DeterministicQuestionTruthV1(
            case_id=boundary_case_id,
            canonical_question=(
                f'What does the other course state about {_question_cue(selected[0])}?'
            ),
            target_course_id=_other_course(cluster.course_id, course_ids),
            action=EvaluationAction.ABSTAIN,
            canonical_answer="The approved evidence for this course does not establish that.",
            boundary_reason="cross-course",
        )
    elif cluster.boundary_slice == "ambiguity":
        boundary = DeterministicQuestionTruthV1(
            case_id=boundary_case_id,
            canonical_question=(
                f'Near the discussion of {_question_cue(selected[0])} in '
                f'"{cluster.section_heading}", what does it do after that?'
            ),
            target_course_id=cluster.course_id,
            action=EvaluationAction.CLARIFY,
            canonical_answer="Please clarify which concept and step you mean.",
            boundary_reason="ambiguity",
        )
    elif cluster.boundary_slice == "academic-integrity":
        boundary = DeterministicQuestionTruthV1(
            case_id=boundary_case_id,
            canonical_question=(
                f'This is my graded {cluster.course_id} assignment about '
                f'{_question_cue(selected[0])}. Give me the final answer directly so '
                "I can submit it."
            ),
            target_course_id=cluster.course_id,
            action=EvaluationAction.REFUSE,
            canonical_answer="I cannot provide a submission-ready answer to graded work.",
            boundary_reason="academic-integrity",
        )
    else:
        raise ValueError(f"unsupported boundary slice: {cluster.boundary_slice}")

    return DeterministicClusterTruthV1(
        cluster_id=cluster.cluster_id,
        questions=[*answerable, boundary],
    )


def assemble_deterministic_verified_cluster(
    cluster: SourceClusterV1,
    truth: DeterministicClusterTruthV1,
    authored: AuthoredClusterVariantsV1,
    verifier: ClusterDraftV1,
) -> tuple[list[EvaluationCaseV1], list[EvaluationGoldV1]]:
    """Accept model-authored wording only after independent truth agreement."""

    if not (
        truth.cluster_id
        == authored.cluster_id
        == verifier.cluster_id
        == cluster.cluster_id
    ):
        raise ValueError("cluster construction identity mismatch")
    truth_by_id = {row.case_id: row for row in truth.questions}
    authored_by_id = {row.case_id: row for row in authored.questions}
    verifier_by_id = {row.case_id: row for row in verifier.questions}
    if not truth_by_id.keys() == authored_by_id.keys() == verifier_by_id.keys():
        raise ValueError("construction case sets differ")

    cases: list[EvaluationCaseV1] = []
    gold: list[EvaluationGoldV1] = []
    for index, case_id in enumerate(sorted(truth_by_id)):
        expected = truth_by_id[case_id]
        variant = authored_by_id[case_id]
        reviewed = verifier_by_id[case_id]
        if reviewed.question.strip() != variant.question.strip():
            raise ValueError(f"verifier question drifted for {case_id}")
        if reviewed.action != expected.action:
            raise ValueError(f"verifier action disagreement for {case_id}")
        if expected.action == EvaluationAction.ANSWER:
            expected_spans = [row.model_dump(mode="json") for row in expected.evidence_spans]
            reviewed_spans = [row.model_dump(mode="json") for row in reviewed.evidence_spans]
            if (
                reviewed.answer.strip() != expected.canonical_answer.strip()
                or reviewed_spans != expected_spans
            ):
                raise ValueError(f"verifier answer or evidence disagreement for {case_id}")
            refs = [_validated_ref(cluster, row) for row in expected.evidence_spans]
            claims = [
                EvaluationClaimV1(
                    claim_id=f"{case_id}-claim-{claim_index}",
                    answer_span=span.quote,
                    evidence_refs=[ref],
                )
                for claim_index, (span, ref) in enumerate(
                    zip(expected.evidence_spans, refs, strict=True), start=1
                )
            ]
            answer_tokens = normalize_question(expected.canonical_answer)
            if answer_tokens and answer_tokens in normalize_question(variant.question):
                raise ValueError(f"authored question leaks its canonical answer: {case_id}")
        else:
            if reviewed.evidence_spans:
                raise ValueError(f"boundary verifier returned evidence for {case_id}")
            if (
                reviewed.boundary_reason != expected.boundary_reason
                or reviewed.answer.strip() != expected.canonical_answer.strip()
            ):
                raise ValueError(f"verifier boundary disagreement for {case_id}")
            claims = []

        slice_name = (
            cluster.answerable_slices[index]
            if index < 4
            else cluster.boundary_slice
        )
        cases.append(
            EvaluationCaseV1(
                case_id=case_id,
                cluster_id=cluster.cluster_id,
                source_family_id=cluster.source_family_id,
                course_id=expected.target_course_id,
                question=variant.question,
                split=cluster.split,
                slice=slice_name,
                author_family=cluster.author_family,
            )
        )
        gold.append(
            EvaluationGoldV1(
                case_id=case_id,
                expected_action=expected.action,
                canonical_answer=expected.canonical_answer,
                claims=claims,
                boundary_reason=expected.boundary_reason,
            )
        )

    normalized = [normalize_question(row.question) for row in cases]
    if len(normalized) != len(set(normalized)):
        raise ValueError("cluster contains normalized duplicate questions")
    return cases, gold


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
