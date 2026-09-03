"""Flow-independent contracts for factual-QA product evaluation."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class EvaluationAction(StrEnum):
    ANSWER = "answer"
    ABSTAIN = "abstain"
    CLARIFY = "clarify"
    REFUSE = "refuse"
    OPERATIONAL_FAILURE = "operational-failure"


class EvaluationSplit(StrEnum):
    DEVELOPMENT = "development"
    FINAL = "final"


class EvaluationCaseV1(BaseModel):
    """The complete payload allowed to cross into a system under test."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, frozen=True)
    case_id: str = Field(min_length=1)
    cluster_id: str = Field(min_length=1)
    source_family_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    split: EvaluationSplit
    slice: str = Field(min_length=1)
    author_family: str = Field(min_length=1)


class CanonicalEvidenceRefV1(BaseModel):
    """Stable evidence identity independent of runtime chunks."""

    model_config = ConfigDict(extra="forbid")

    source_artifact_id: str = Field(min_length=1)
    source_version: int = Field(ge=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)
    region_id: str | None = None

    @model_validator(mode="after")
    def range_must_be_ordered(self) -> "CanonicalEvidenceRefV1":
        if self.char_end <= self.char_start:
            raise ValueError("canonical evidence range must be non-empty")
        return self


class EvaluationClaimV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1)
    answer_span: str = Field(min_length=1)
    evidence_refs: list[CanonicalEvidenceRefV1] = Field(min_length=1)

    @field_validator("answer_span")
    @classmethod
    def answer_span_must_be_short(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("answer span cannot be blank")
        if len(normalized.split()) > 30:
            raise ValueError("answer span exceeds the extractive contract")
        return normalized


class EvaluationGoldV1(BaseModel):
    """Hidden reference data opened only by the scoring process."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, frozen=True)
    case_id: str = Field(min_length=1)
    expected_action: EvaluationAction
    canonical_answer: str = Field(min_length=1)
    claims: list[EvaluationClaimV1] = Field(default_factory=list)
    boundary_reason: str | None = None

    @model_validator(mode="after")
    def action_must_match_lineage(self) -> "EvaluationGoldV1":
        if self.expected_action == EvaluationAction.ANSWER:
            if not self.claims or self.boundary_reason is not None:
                raise ValueError("answer gold requires claims and no boundary reason")
        elif self.expected_action != EvaluationAction.OPERATIONAL_FAILURE:
            if self.claims or not self.boundary_reason:
                raise ValueError("boundary gold requires empty claims and a reason")
        return self


class EvaluationCitationV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_artifact_id: str = Field(min_length=1)
    source_version: int = Field(ge=1)
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, gt=0)
    region_id: str | None = None

    @model_validator(mode="after")
    def optional_range_must_be_complete(self) -> "EvaluationCitationV1":
        if (self.char_start is None) != (self.char_end is None):
            raise ValueError("citation range must provide both endpoints")
        if (
            self.char_start is not None
            and self.char_end is not None
            and self.char_end <= self.char_start
        ):
            raise ValueError("citation range must be non-empty")
        return self


class EvaluationAtomicClaimV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    citations: list[EvaluationCitationV1] = Field(default_factory=list)


class EvaluationUsageV1(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0, ge=0, allow_inf_nan=False)
    latency_ms: float = Field(default=0, ge=0, allow_inf_nan=False)


class EvaluationResponseV1(BaseModel):
    """Normalized observable response from any application flow."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, frozen=True)
    case_id: str = Field(min_length=1)
    flow_id: str = Field(min_length=1)
    action: EvaluationAction
    answer: str = Field(min_length=1)
    atomic_claims: list[EvaluationAtomicClaimV1] = Field(default_factory=list)
    citations: list[EvaluationCitationV1] = Field(default_factory=list)
    retrieved_evidence: list[EvaluationCitationV1] = Field(default_factory=list)
    operational_status: str = Field(min_length=1)
    provider_model: str | None = None
    provider_revision: str | None = None
    usage: EvaluationUsageV1 = Field(default_factory=EvaluationUsageV1)
    trace: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class SystemUnderTestManifestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, frozen=True)
    flow_id: str = Field(min_length=1)
    adapter_version: str = Field(min_length=1)
    code_revision: str = Field(pattern=r"^[0-9a-f]{7,40}$")
    profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retriever: str = Field(min_length=1)
    generator: str = Field(min_length=1)
    policy: str = Field(min_length=1)
    evidence_gate: str = Field(min_length=1)
    model_bindings: dict[str, str] = Field(default_factory=dict)
    known_benchmark: bool = False


@runtime_checkable
class TutorEvaluationAdapterV1(Protocol):
    flow_id: str
    adapter_version: str

    async def evaluate(self, case: EvaluationCaseV1) -> EvaluationResponseV1: ...


def evidence_ranges_overlap(
    expected: CanonicalEvidenceRefV1,
    observed: EvaluationCitationV1,
) -> bool:
    if (
        expected.source_artifact_id != observed.source_artifact_id
        or expected.source_version != observed.source_version
    ):
        return False
    if expected.source_sha256 != observed.source_sha256:
        return False
    # A region identity is additional provenance: it refines a match the
    # canonical range already establishes, so it decides only when both sides
    # declare one. Comparing it when only one side does made a citation that
    # agrees on artifact, version, sha256 and character range score a miss for
    # carrying more provenance than the gold.
    if observed.region_id is not None and expected.region_id is not None:
        return observed.region_id == expected.region_id
    if observed.char_start is None or observed.char_end is None:
        return False
    return max(expected.char_start, observed.char_start) < min(
        expected.char_end, observed.char_end
    )
