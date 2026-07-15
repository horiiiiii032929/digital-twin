import re
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator


_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_REVISION_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")


class ComponentKind(StrEnum):
    SOURCE_ADAPTER = "source-adapter"
    PARSER = "parser"
    CHUNKER = "chunker"
    RETRIEVER = "retriever"
    RERANKER = "reranker"
    FIGURE_DESCRIPTION = "figure-description"
    GENERATOR = "generator"
    PROMPT = "prompt"
    TUTOR_POLICY = "tutor-policy"
    POLICY_ENFORCEMENT = "policy-enforcement"
    CITATION_VALIDATION = "citation-validation"
    CONVERSATION_ORCHESTRATION = "conversation-orchestration"
    PROACTIVE_TRIGGER = "proactive-trigger"
    LEARNING_GAP_ANALYTICS = "learning-gap-analytics"


class ComponentStatus(StrEnum):
    SELECTED = "selected"
    PENDING = "pending"
    DISABLED = "disabled"


class ProfileStage(StrEnum):
    EXPERIMENTAL = "experimental"
    RELEASE_CANDIDATE = "release-candidate"
    RELEASED = "released"


class DecisionOutcome(StrEnum):
    KEEP = "keep"
    REFINE = "refine"
    GO_DEEPER = "go-deeper"
    DROP = "drop"


class MetricDirection(StrEnum):
    HIGHER_IS_BETTER = "higher-is-better"
    LOWER_IS_BETTER = "lower-is-better"


class ImplementationRef(BaseModel):
    implementation_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    configuration: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def identifier_must_be_portable(self) -> "ImplementationRef":
        if not _IDENTIFIER_PATTERN.fullmatch(self.implementation_id):
            raise ValueError("implementation_id must use lowercase kebab-case")
        return self


class MetricResult(BaseModel):
    name: str = Field(min_length=1)
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1)
    direction: MetricDirection
    threshold: float = Field(allow_inf_nan=False)
    passed: bool

    @model_validator(mode="after")
    def pass_state_must_match_threshold(self) -> "MetricResult":
        expected = (
            self.value >= self.threshold
            if self.direction == MetricDirection.HIGHER_IS_BETTER
            else self.value <= self.threshold
        )
        if self.passed != expected:
            raise ValueError("metric pass state does not match its threshold")
        return self


class GateResult(BaseModel):
    name: str = Field(min_length=1)
    passed: bool
    evidence: str = Field(min_length=1)


class CandidateEvaluation(BaseModel):
    implementation: ImplementationRef
    role: Literal["control", "candidate"]
    metrics: list[MetricResult] = Field(min_length=1)
    hard_gates: list[GateResult] = Field(min_length=1)
    failures_by_category: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def result_names_and_failure_counts_must_be_valid(self) -> "CandidateEvaluation":
        metric_names = [metric.name for metric in self.metrics]
        gate_names = [gate.name for gate in self.hard_gates]
        if len(metric_names) != len(set(metric_names)):
            raise ValueError("candidate metric names must be unique")
        if len(gate_names) != len(set(gate_names)):
            raise ValueError("candidate hard-gate names must be unique")
        if any(count < 0 for count in self.failures_by_category.values()):
            raise ValueError("failure counts must be non-negative")
        return self


class EvaluationDecision(BaseModel):
    outcome: DecisionOutcome
    selected_implementation_id: str | None = None
    rationale: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def selected_implementation_matches_outcome(self) -> "EvaluationDecision":
        if self.outcome == DecisionOutcome.DROP and self.selected_implementation_id:
            raise ValueError("drop decisions cannot select an implementation")
        if self.outcome in {DecisionOutcome.KEEP, DecisionOutcome.GO_DEEPER} and not (
            self.selected_implementation_id
        ):
            raise ValueError("keep and go-deeper decisions require a selection")
        return self


class ComponentEvaluationRecord(BaseModel):
    schema_version: Literal[1]
    run_id: str = Field(min_length=1)
    component: ComponentKind
    dataset_id: str = Field(min_length=1)
    corpus_id: str | None = None
    code_revision: str
    candidates: list[CandidateEvaluation] = Field(min_length=2)
    decision: EvaluationDecision

    @model_validator(mode="after")
    def selected_candidate_must_exist_and_pass(self) -> "ComponentEvaluationRecord":
        if not _IDENTIFIER_PATTERN.fullmatch(self.run_id):
            raise ValueError("run_id must use lowercase kebab-case")
        if not _REVISION_PATTERN.fullmatch(self.code_revision):
            raise ValueError("code_revision must be a Git hexadecimal revision")

        identifiers = [
            candidate.implementation.implementation_id for candidate in self.candidates
        ]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("candidate implementation identifiers must be unique")
        if sum(candidate.role == "control" for candidate in self.candidates) != 1:
            raise ValueError("an evaluation record requires exactly one control")
        metric_names = {metric.name for metric in self.candidates[0].metrics}
        gate_names = {gate.name for gate in self.candidates[0].hard_gates}
        if any(
            {metric.name for metric in candidate.metrics} != metric_names
            for candidate in self.candidates[1:]
        ):
            raise ValueError("candidates must use the same metric set")
        if any(
            {gate.name for gate in candidate.hard_gates} != gate_names
            for candidate in self.candidates[1:]
        ):
            raise ValueError("candidates must use the same hard-gate set")

        selected_id = self.decision.selected_implementation_id
        if selected_id is None:
            return self
        selected = next(
            (
                candidate
                for candidate in self.candidates
                if candidate.implementation.implementation_id == selected_id
            ),
            None,
        )
        if selected is None:
            raise ValueError("selected implementation is absent from candidates")
        if not all(metric.passed for metric in selected.metrics):
            raise ValueError("selected implementation failed a required metric")
        if not all(gate.passed for gate in selected.hard_gates):
            raise ValueError("selected implementation failed a hard gate")
        return self


class ComponentProfileEntry(BaseModel):
    component: ComponentKind
    status: ComponentStatus
    implementation: ImplementationRef | None = None
    control: ImplementationRef | None = None
    decision: DecisionOutcome | None = None
    evaluation_dataset: str | None = None
    evaluation_record_path: str | None = None
    evidence_paths: list[str] = Field(default_factory=list)
    hard_gates: list[str] = Field(default_factory=list)
    candidate_ids: list[str] = Field(default_factory=list)
    notes: str = Field(min_length=1)

    @model_validator(mode="after")
    def status_must_match_selection_evidence(self) -> "ComponentProfileEntry":
        if len(self.evidence_paths) != len(set(self.evidence_paths)):
            raise ValueError("component evidence paths must be unique")
        if len(self.hard_gates) != len(set(self.hard_gates)):
            raise ValueError("component hard gates must be unique")
        if len(self.candidate_ids) != len(set(self.candidate_ids)):
            raise ValueError("component candidate identifiers must be unique")
        if any(
            not _IDENTIFIER_PATTERN.fullmatch(candidate_id)
            for candidate_id in self.candidate_ids
        ):
            raise ValueError("candidate identifiers must use lowercase kebab-case")

        if self.status == ComponentStatus.SELECTED:
            if self.implementation is None or self.decision is None:
                raise ValueError(
                    "selected components require implementation and decision"
                )
            if not self.evidence_paths or not self.hard_gates:
                raise ValueError("selected components require evidence and hard gates")
            if self.decision == DecisionOutcome.DROP:
                raise ValueError("selected components cannot have a drop decision")
        elif self.status == ComponentStatus.PENDING:
            if (
                self.implementation is not None
                or self.control is not None
                or self.decision is not None
                or self.evaluation_record_path is not None
            ):
                raise ValueError("pending components cannot select an implementation")
        elif self.status == ComponentStatus.DISABLED:
            if self.implementation is not None or self.control is not None:
                raise ValueError("disabled components cannot select an implementation")
            if (
                self.decision != DecisionOutcome.DROP
                or not self.evidence_paths
                or self.evaluation_record_path is None
            ):
                raise ValueError("disabled components require a recorded drop decision")
        return self


class SystemReleaseProfile(BaseModel):
    schema_version: Literal[1]
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    stage: ProfileStage
    components: list[ComponentProfileEntry]

    @model_validator(mode="after")
    def component_inventory_must_be_complete(self) -> "SystemReleaseProfile":
        if not _IDENTIFIER_PATTERN.fullmatch(self.profile_id):
            raise ValueError("profile_id must use lowercase kebab-case")
        components = [entry.component for entry in self.components]
        if len(components) != len(set(components)):
            raise ValueError("profile components must be unique")
        missing = set(ComponentKind) - set(components)
        if missing:
            names = ", ".join(sorted(component.value for component in missing))
            raise ValueError(f"profile is missing components: {names}")
        if self.stage != ProfileStage.EXPERIMENTAL and any(
            entry.status == ComponentStatus.PENDING for entry in self.components
        ):
            raise ValueError(
                "release candidates and releases cannot contain pending components"
            )
        return self


def load_release_profile(path: Path) -> SystemReleaseProfile:
    return SystemReleaseProfile.model_validate_json(path.read_text(encoding="utf-8"))


def load_evaluation_record(path: Path) -> ComponentEvaluationRecord:
    return ComponentEvaluationRecord.model_validate_json(
        path.read_text(encoding="utf-8")
    )
