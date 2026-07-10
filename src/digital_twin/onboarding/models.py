from pydantic import BaseModel, Field

from src.digital_twin.tutor_policy import (
    ApprovalItem,
    ChatMessage,
    EvidenceSnapshot,
    PreviewCase,
    PreviewDecisionRecord,
    RevisionProposal,
    SourceInventoryItem,
    TutorPolicy,
    WorkflowTraceItem,
)


class OnboardingSession(BaseModel):
    session_id: str
    current_step: str
    answers: dict[str, str] = Field(default_factory=dict)
    messages: list[ChatMessage] = Field(default_factory=list)
    source_inventory: list[SourceInventoryItem] = Field(default_factory=list)
    policy: TutorPolicy | None = None
    policy_version: int = 1
    preview_cases: list[PreviewCase] = Field(default_factory=list)
    preview_decisions: dict[str, PreviewDecisionRecord] = Field(default_factory=dict)
    evidence_snapshots: list[EvidenceSnapshot] = Field(default_factory=list)
    revision_proposal: RevisionProposal | None = None
    approval_checklist: list[ApprovalItem] = Field(default_factory=list)
    release_blockers: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "source_inventory": [],
            "policy_fields": [],
            "approval_checklist": [],
            "preview_decisions": [],
            "preview_acceptance": [],
        }
    )
    trace: list[WorkflowTraceItem] = Field(default_factory=list)
