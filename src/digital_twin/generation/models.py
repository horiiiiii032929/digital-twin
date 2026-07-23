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
