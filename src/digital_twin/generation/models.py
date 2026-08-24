from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.digital_twin.grounding.models import RetrievalHit
from src.digital_twin.llm import LlmMessage


class PolicyAction(StrEnum):
    ANSWER = "answer"
    REDIRECT_GRADED_WORK = "redirect-graded-work"
    NO_EVIDENCE = "no-evidence"
    POLICY_NOT_APPROVED = "policy-not-approved"
    INVALID_REQUEST = "invalid-request"


class PolicyDecision(BaseModel):
    action: PolicyAction
    reason: str = Field(min_length=1)
    matched_rules: list[str] = Field(default_factory=list)

    @property
    def permits_model_call(self) -> bool:
        return self.action == PolicyAction.ANSWER


class EvidenceBinding(BaseModel):
    citation_id: str = Field(pattern=r"^S[1-9][0-9]*$")
    hit: RetrievalHit


class PromptPackage(BaseModel):
    version: str = Field(min_length=1)
    messages: list[LlmMessage] = Field(min_length=2)
    evidence: list[EvidenceBinding] = Field(min_length=1)


class ModelTutorOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
    citation_ids: list[str]

    @field_validator("answer")
    @classmethod
    def answer_must_not_be_blank(cls, value: str) -> str:
        answer = value.strip()
        if not answer:
            raise ValueError("answer must not be blank")
        return answer


class ModelAtomicClaimOutput(BaseModel):
    """Prospective v2 output: factual text exists only as declared claims."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(pattern=r"^claim-[a-z0-9-]+$")
    text: str = Field(min_length=1)
    citation_ids: list[str] = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def claim_text_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("claim text must not be blank")
        return normalized

    @field_validator("citation_ids")
    @classmethod
    def citation_ids_must_be_unique(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("claim citation IDs must be unique")
        return values


class ModelTutorOutputV2(BaseModel):
    """Candidate claim-only response contract; not selected by the profile."""

    model_config = ConfigDict(extra="forbid")

    claims: list[ModelAtomicClaimOutput] = Field(min_length=1, max_length=8)

    @field_validator("claims")
    @classmethod
    def claim_ids_must_be_unique(
        cls,
        values: list[ModelAtomicClaimOutput],
    ) -> list[ModelAtomicClaimOutput]:
        claim_ids = [claim.claim_id for claim in values]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("claim IDs must be unique")
        return values
