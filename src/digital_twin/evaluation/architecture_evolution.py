"""Contracts for finite, fully recorded whole-system architecture evolution.

The contracts in this module do not execute an evaluation.  They make the
selection process auditable: development folds are distinct from final
confirmation, every round must publish a terminal record before progression,
and non-human proxy evidence cannot be relabelled as human fidelity or learning
evidence.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from src.digital_twin.evaluation.models import GateResult, MetricResult


_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_REVISION_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ArchitecturePlane(StrEnum):
    DOMAIN = "domain"
    RETRIEVAL = "retrieval"
    ACTION_ROUTING = "action-routing"
    CLAIM_CITATION = "claim-citation"
    LEARNER_STATE = "learner-state"
    PEDAGOGICAL_POLICY = "pedagogical-policy"
    REACTIVE_LOOP = "reactive-loop"
    PROACTIVE_LOOP = "proactive-loop"
    GOVERNANCE = "governance"
    PERSISTENCE = "persistence"
    PRODUCT_EXPERIENCE = "product-experience"
    OPERATIONS = "operations"
    EVALUATION = "evaluation"


class TrancheRole(StrEnum):
    DEVELOPMENT = "development"
    FRESH_CONFIRMATION = "fresh-confirmation"
    KNOWN_REGRESSION = "known-regression"
    AUTONOMY = "autonomy"
    VISUAL_SUPPLEMENT = "visual-supplement"
    PROFILE_PROXY = "profile-proxy"
    LEARNING_UTILITY_PROXY = "learning-utility-proxy"
    PRODUCT_QUALIFICATION = "product-qualification"
    SECURITY_RED_TEAM = "security-red-team"


class TrancheStatus(StrEnum):
    PLANNED = "planned"
    FROZEN = "frozen"
    HISTORICAL = "historical"


class ArchitectureRunStatus(StrEnum):
    BUILD_ONLY_QUALIFIED = "build-only-qualified"
    COMPLETED_KEEP = "completed-keep"
    COMPLETED_REFINE = "completed-refine"
    COMPLETED_GO_DEEPER = "completed-go-deeper"
    INVALID_EXECUTION = "invalid-execution"
    CANCELLED_BEFORE_EXECUTION = "cancelled-before-execution"


class ArchitectureDecisionOutcome(StrEnum):
    KEEP = "keep"
    REFINE = "refine"
    REPLACE = "replace"
    REDESIGN = "redesign"
    GO_DEEPER = "go-deeper"
    NO_RELEASE = "no-release"


class BoundArtifactV1(BaseModel):
    path: str = Field(min_length=1)
    sha256: str
    role: str = Field(min_length=1)

    @model_validator(mode="after")
    def path_and_hash_are_portable(self) -> "BoundArtifactV1":
        path = Path(self.path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("bound artifact paths must be repository relative")
        if not _SHA256_PATTERN.fullmatch(self.sha256):
            raise ValueError("bound artifact sha256 must be lowercase hexadecimal")
        return self


class DatasetTrancheV1(BaseModel):
    tranche_id: str
    role: TrancheRole
    status: TrancheStatus
    source_disjoint_group: str = Field(min_length=1)
    case_count: int = Field(ge=1)
    public_path: str | None = None
    public_sha256: str | None = None
    gold_path: str | None = None
    gold_sha256: str | None = None
    may_influence_development: bool
    maximum_executions: int = Field(ge=1)

    @model_validator(mode="after")
    def frozen_tranches_require_bindings(self) -> "DatasetTrancheV1":
        if not _IDENTIFIER_PATTERN.fullmatch(self.tranche_id):
            raise ValueError("tranche_id must use lowercase kebab-case")
        path_pairs = (
            (self.public_path, self.public_sha256),
            (self.gold_path, self.gold_sha256),
        )
        for path_value, digest in path_pairs:
            if (path_value is None) != (digest is None):
                raise ValueError("dataset paths and hashes must be supplied together")
            if path_value is not None:
                path = Path(path_value)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("dataset paths must be repository relative")
                if digest is None or not _SHA256_PATTERN.fullmatch(digest):
                    raise ValueError("dataset sha256 must be lowercase hexadecimal")
        if self.status in {TrancheStatus.FROZEN, TrancheStatus.HISTORICAL} and (
            self.public_path is None or self.public_sha256 is None
        ):
            raise ValueError("frozen and historical tranches require public bindings")
        if self.role == TrancheRole.FRESH_CONFIRMATION:
            if self.may_influence_development:
                raise ValueError("fresh confirmation cannot influence development")
            if self.maximum_executions != 1:
                raise ValueError("fresh confirmation can be executed only once")
        if self.role == TrancheRole.KNOWN_REGRESSION and not (
            self.may_influence_development
        ):
            raise ValueError("known regression must be labelled development-visible")
        return self


class FrozenDevelopmentTrancheV1(BaseModel):
    """One immutable, gold-isolated architecture-development fold."""

    tranche_id: str
    round_number: int = Field(ge=1, le=3)
    source: BoundArtifactV1
    public_cases: BoundArtifactV1
    hidden_gold: BoundArtifactV1
    case_count: int = Field(ge=400)
    cluster_count: int = Field(ge=1)
    removed_duplicate_case_ids: list[str] = Field(default_factory=list)
    source_range_overlap_with_earlier_folds: Literal[0]
    normalized_question_overlap_with_earlier_folds: Literal[0]

    @model_validator(mode="after")
    def identifiers_and_roles_are_consistent(self) -> "FrozenDevelopmentTrancheV1":
        if not _IDENTIFIER_PATTERN.fullmatch(self.tranche_id):
            raise ValueError("frozen tranche ID must use lowercase kebab-case")
        if len(self.removed_duplicate_case_ids) != len(
            set(self.removed_duplicate_case_ids)
        ):
            raise ValueError("removed duplicate case IDs must be unique")
        roles = {
            self.source.role,
            self.public_cases.role,
            self.hidden_gold.role,
        }
        if roles != {"source-corpus", "public-cases", "hidden-gold"}:
            raise ValueError("frozen tranche artifacts require distinct canonical roles")
        return self


class ArchitectureDevelopmentFreezeV1(BaseModel):
    """Realization of the three planned development folds.

    The main program remains immutable build evidence.  This successor binds
    the concrete source/case/gold packages without rewriting that checkpoint.
    """

    schema_version: Literal[1]
    freeze_id: str
    program_id: str
    program_sha256: str
    status: Literal["frozen-build-only"]
    deterministic_truth_authoritative: Literal[True]
    product_inputs_exclude_gold: Literal[True]
    provider_calls: Literal[0]
    paid_cost_usd: Literal[0]
    tranches: list[FrozenDevelopmentTrancheV1]

    @model_validator(mode="after")
    def exactly_three_rounds_are_frozen(self) -> "ArchitectureDevelopmentFreezeV1":
        if not _IDENTIFIER_PATTERN.fullmatch(self.freeze_id):
            raise ValueError("freeze ID must use lowercase kebab-case")
        if not _IDENTIFIER_PATTERN.fullmatch(self.program_id):
            raise ValueError("program ID must use lowercase kebab-case")
        if not _SHA256_PATTERN.fullmatch(self.program_sha256):
            raise ValueError("program sha256 must be lowercase hexadecimal")
        if [row.round_number for row in self.tranches] != [1, 2, 3]:
            raise ValueError("development freeze requires exactly rounds 1, 2, and 3")
        tranche_ids = [row.tranche_id for row in self.tranches]
        if len(tranche_ids) != len(set(tranche_ids)):
            raise ValueError("development freeze tranche IDs must be unique")
        return self


class ArchitectureSystemManifestV1(BaseModel):
    """Flow-independent architecture identity used by every comparison."""

    schema_version: Literal[1]
    architecture_id: str
    version: str = Field(min_length=1)
    role: Literal["baseline", "candidate", "winner"]
    plane_bindings: dict[ArchitecturePlane, str]
    factual_adapter: str = Field(min_length=1)
    autonomy_adapter: str = Field(min_length=1)
    rollback_architecture_id: str | None = None
    public_question_only_planning: bool
    hidden_gold_available_to_runtime: Literal[False]
    deterministic_policy_authoritative: Literal[True]
    deterministic_source_truth_authoritative: Literal[True]
    provider_execution_authorized: bool

    @model_validator(mode="after")
    def every_plane_is_bound(self) -> "ArchitectureSystemManifestV1":
        if not _IDENTIFIER_PATTERN.fullmatch(self.architecture_id):
            raise ValueError("architecture ID must use lowercase kebab-case")
        if set(self.plane_bindings) != set(ArchitecturePlane):
            raise ValueError("architecture manifest must bind every system plane")
        if any(not value.strip() for value in self.plane_bindings.values()):
            raise ValueError("architecture plane bindings cannot be blank")
        if self.rollback_architecture_id is not None and not _IDENTIFIER_PATTERN.fullmatch(
            self.rollback_architecture_id
        ):
            raise ValueError("rollback architecture ID must use lowercase kebab-case")
        return self


class ArchitectureRoundInstrumentV1(BaseModel):
    schema_version: Literal[1]
    instrument_id: str
    program_id: str
    round_number: int = Field(ge=1, le=3)
    status: Literal["frozen-network-free", "completed"]
    development_freeze: BoundArtifactV1
    development_tranche_id: str
    candidates: list[ArchitectureSystemManifestV1] = Field(min_length=2, max_length=4)
    network_free_execution_authorized: bool
    provider_execution_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    hidden_gold_after_response_persistence: Literal[True]
    maximum_executions: Literal[1]
    hard_gates: dict[str, float] = Field(min_length=1)
    output_directory: str = Field(min_length=1)

    @model_validator(mode="after")
    def round_is_finite_and_portable(self) -> "ArchitectureRoundInstrumentV1":
        for identifier in (
            self.instrument_id,
            self.program_id,
            self.development_tranche_id,
        ):
            if not _IDENTIFIER_PATTERN.fullmatch(identifier):
                raise ValueError("round identifiers must use lowercase kebab-case")
        architecture_ids = [row.architecture_id for row in self.candidates]
        if len(architecture_ids) != len(set(architecture_ids)):
            raise ValueError("round architecture IDs must be unique")
        if sum(row.role == "baseline" for row in self.candidates) != 1:
            raise ValueError("round requires exactly one baseline architecture")
        output = Path(self.output_directory)
        if output.is_absolute() or ".." in output.parts:
            raise ValueError("round output directory must be repository relative")
        if any(not math.isfinite(value) for value in self.hard_gates.values()):
            raise ValueError("round hard gates must be finite")
        return self


class ArchitectureRoundV1(BaseModel):
    round_number: int = Field(ge=1, le=3)
    development_tranche_id: str
    minimum_candidate_count: int = Field(ge=1)
    maximum_candidate_count: int = Field(ge=2)
    allowed_planes: list[ArchitecturePlane] = Field(min_length=1)
    result_required_before_progression: Literal[True]
    invalid_harness_corrections_maximum: Literal[1]
    same_tranche_quality_rerun_allowed: Literal[False]
    selection_rule: str = Field(min_length=1)

    @model_validator(mode="after")
    def candidate_bounds_are_ordered(self) -> "ArchitectureRoundV1":
        if self.minimum_candidate_count > self.maximum_candidate_count:
            raise ValueError("minimum candidate count exceeds maximum")
        if len(self.allowed_planes) != len(set(self.allowed_planes)):
            raise ValueError("round architecture planes must be unique")
        return self


class FinalEvaluationStageV1(BaseModel):
    stage_id: str
    tranche_ids: list[str] = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    result_required: Literal[True]
    provider_backed: bool

    @model_validator(mode="after")
    def identifiers_are_portable(self) -> "FinalEvaluationStageV1":
        identifiers = [self.stage_id, *self.tranche_ids, *self.depends_on]
        if any(not _IDENTIFIER_PATTERN.fullmatch(value) for value in identifiers):
            raise ValueError("stage and dependency identifiers must use kebab-case")
        if len(self.tranche_ids) != len(set(self.tranche_ids)):
            raise ValueError("final stage tranche identifiers must be unique")
        return self


class RecordingPolicyV1(BaseModel):
    stable_run_id_required: Literal[True]
    manifest_required: Literal[True]
    machine_record_required: Literal[True]
    readable_summary_required: Literal[True]
    registry_entry_required: Literal[True]
    artifact_hashes_required: Literal[True]
    operational_accounting_required: Literal[True]
    limitations_required: Literal[True]
    github_checkpoint_required: Literal[True]
    unfavorable_results_immutable: Literal[True]
    zero_call_runs_recorded: Literal[True]
    corrections_use_new_run_id: Literal[True]
    registry_path: str
    records_directory: str


class ArchitectureEvolutionProgramV1(BaseModel):
    schema_version: Literal[1]
    program_id: str
    status: Literal["reviewed-build-only", "frozen", "running", "completed"]
    owner_issue: int = Field(ge=1)
    parent_issue: int = Field(ge=1)
    provider_execution_authorized: bool
    paid_execution_authorized: bool
    automatic_stage_progression: bool
    maximum_architecture_rounds: Literal[3]
    final_confirmation_maximum_executions: Literal[1]
    human_participants_required: Literal[False]
    deterministic_truth_authoritative: Literal[True]
    llm_reviews_authoritative: Literal[False]
    historical_baseline_run_ids: list[str] = Field(min_length=1)
    baseline_artifacts: list[BoundArtifactV1] = Field(min_length=1)
    architecture_planes: list[ArchitecturePlane]
    recording_policy: RecordingPolicyV1
    tranches: list[DatasetTrancheV1]
    rounds: list[ArchitectureRoundV1]
    final_stages: list[FinalEvaluationStageV1]
    hard_stops: list[str] = Field(min_length=1)
    allowed_claims: list[str] = Field(min_length=1)
    prohibited_claims: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def program_is_finite_and_leakage_safe(self) -> "ArchitectureEvolutionProgramV1":
        if not _IDENTIFIER_PATTERN.fullmatch(self.program_id):
            raise ValueError("program_id must use lowercase kebab-case")
        if len(self.historical_baseline_run_ids) != len(
            set(self.historical_baseline_run_ids)
        ):
            raise ValueError("historical baseline run identifiers must be unique")
        if any(
            not _IDENTIFIER_PATTERN.fullmatch(value)
            for value in self.historical_baseline_run_ids
        ):
            raise ValueError("historical baseline run IDs must use kebab-case")
        if len(self.architecture_planes) != len(set(self.architecture_planes)):
            raise ValueError("architecture planes must be unique")
        if set(self.architecture_planes) != set(ArchitecturePlane):
            raise ValueError("program must cover every architecture plane")

        tranche_ids = [tranche.tranche_id for tranche in self.tranches]
        if len(tranche_ids) != len(set(tranche_ids)):
            raise ValueError("program tranche identifiers must be unique")
        tranches = {tranche.tranche_id: tranche for tranche in self.tranches}

        if [item.round_number for item in self.rounds] != [1, 2, 3]:
            raise ValueError("program requires exactly three ordered rounds")
        development_ids = [item.development_tranche_id for item in self.rounds]
        if len(development_ids) != len(set(development_ids)):
            raise ValueError("architecture rounds require distinct development tranches")
        for tranche_id in development_ids:
            tranche = tranches.get(tranche_id)
            if tranche is None or tranche.role != TrancheRole.DEVELOPMENT:
                raise ValueError("architecture rounds must bind development tranches")
            if not tranche.may_influence_development:
                raise ValueError("round development tranches must permit development use")

        stage_ids = [stage.stage_id for stage in self.final_stages]
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("final stage identifiers must be unique")
        known_ids = set(tranche_ids)
        for stage in self.final_stages:
            if not set(stage.tranche_ids) <= known_ids:
                raise ValueError("final stage references an unknown tranche")
            if not set(stage.depends_on) <= set(stage_ids):
                raise ValueError("final stage references an unknown dependency")

        final_confirmation = [
            tranche for tranche in self.tranches
            if tranche.role == TrancheRole.FRESH_CONFIRMATION
        ]
        if len(final_confirmation) != 1:
            raise ValueError("program requires exactly one fresh confirmation tranche")
        if final_confirmation[0].tranche_id in development_ids:
            raise ValueError("fresh confirmation cannot be used by architecture rounds")

        recording_paths = (
            self.recording_policy.registry_path,
            self.recording_policy.records_directory,
        )
        for value in recording_paths:
            path = Path(value)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("recording paths must be repository relative")
        return self


class ArchitectureCandidateResultV1(BaseModel):
    architecture_id: str
    version: str = Field(min_length=1)
    role: Literal["baseline", "candidate", "winner"]
    changed_planes: list[ArchitecturePlane]
    metrics: list[MetricResult] = Field(min_length=1)
    hard_gates: list[GateResult] = Field(min_length=1)

    @model_validator(mode="after")
    def candidate_fields_are_unique(self) -> "ArchitectureCandidateResultV1":
        if not _IDENTIFIER_PATTERN.fullmatch(self.architecture_id):
            raise ValueError("architecture_id must use lowercase kebab-case")
        if len(self.changed_planes) != len(set(self.changed_planes)):
            raise ValueError("changed architecture planes must be unique")
        metric_names = [metric.name for metric in self.metrics]
        gate_names = [gate.name for gate in self.hard_gates]
        if len(metric_names) != len(set(metric_names)):
            raise ValueError("candidate metric names must be unique")
        if len(gate_names) != len(set(gate_names)):
            raise ValueError("candidate gate names must be unique")
        return self


class OperationalAccountingV1(BaseModel):
    provider_calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    reported_cost_usd: float = Field(ge=0, allow_inf_nan=False)
    malformed_responses: int = Field(ge=0)
    provider_failures: int = Field(ge=0)
    p95_latency_ms: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def zero_calls_have_zero_usage(self) -> "OperationalAccountingV1":
        if self.provider_calls == 0 and any(
            value != 0
            for value in (
                self.input_tokens,
                self.output_tokens,
                self.reported_cost_usd,
                self.malformed_responses,
                self.provider_failures,
                self.p95_latency_ms,
            )
        ):
            raise ValueError("zero-call runs must report zero provider accounting")
        return self


class FailureClassificationV1(BaseModel):
    category: Literal[
        "implementation",
        "method",
        "data",
        "architecture",
        "provider",
        "policy",
        "ux",
        "operations",
        "evaluation",
    ]
    count: int = Field(ge=1)
    evidence: str = Field(min_length=1)


class ArchitectureRunDecisionV1(BaseModel):
    outcome: ArchitectureDecisionOutcome
    selected_architecture_id: str | None = None
    rationale: str = Field(min_length=1)


class ArchitectureEvolutionRunRecordV1(BaseModel):
    record_schema: Literal["architecture-evolution-run-v1"]
    schema_version: Literal[1]
    run_id: str
    program_id: str
    stage_id: str
    round_number: int | None = Field(default=None, ge=1, le=3)
    status: ArchitectureRunStatus
    supersedes: list[str] = Field(default_factory=list)
    decision_question: str = Field(min_length=1)
    code_revision: str
    dirty_state: bool
    started_at: datetime
    completed_at: datetime
    bindings: list[BoundArtifactV1] = Field(min_length=1)
    candidates: list[ArchitectureCandidateResultV1] = Field(min_length=1)
    operational: OperationalAccountingV1
    failures: list[FailureClassificationV1] = Field(default_factory=list)
    decision: ArchitectureRunDecisionV1
    limitations: list[str] = Field(min_length=1)
    summary_path: str
    record_path: str

    @model_validator(mode="after")
    def terminal_record_is_consistent(self) -> "ArchitectureEvolutionRunRecordV1":
        identifiers = [self.run_id, self.program_id, self.stage_id, *self.supersedes]
        if any(not _IDENTIFIER_PATTERN.fullmatch(value) for value in identifiers):
            raise ValueError("run identifiers must use lowercase kebab-case")
        if not _REVISION_PATTERN.fullmatch(self.code_revision):
            raise ValueError("code_revision must be a Git hexadecimal revision")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        if len(self.supersedes) != len(set(self.supersedes)):
            raise ValueError("supersedes identifiers must be unique")
        architecture_ids = [candidate.architecture_id for candidate in self.candidates]
        if len(architecture_ids) != len(set(architecture_ids)):
            raise ValueError("candidate architecture identifiers must be unique")
        selected_id = self.decision.selected_architecture_id
        if selected_id is not None and selected_id not in architecture_ids:
            raise ValueError("selected architecture is absent from candidates")

        for value in (self.summary_path, self.record_path):
            path = Path(value)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("result paths must be repository relative")
        if not self.summary_path.endswith("-results.md"):
            raise ValueError("summary_path must identify a durable result summary")
        if not self.record_path.startswith("research/05_evaluation/records/"):
            raise ValueError("record_path must use the evaluation records directory")

        passing_status = self.status in {
            ArchitectureRunStatus.BUILD_ONLY_QUALIFIED,
            ArchitectureRunStatus.COMPLETED_KEEP,
            ArchitectureRunStatus.COMPLETED_GO_DEEPER,
        }
        if passing_status:
            if selected_id is None:
                raise ValueError("passing run states require a selected architecture")
            selected = next(
                candidate for candidate in self.candidates
                if candidate.architecture_id == selected_id
            )
            if not all(metric.passed for metric in selected.metrics):
                raise ValueError("selected architecture failed a required metric")
            if not all(gate.passed for gate in selected.hard_gates):
                raise ValueError("selected architecture failed a hard gate")

        if self.status == ArchitectureRunStatus.INVALID_EXECUTION and (
            self.decision.outcome
            not in {
                ArchitectureDecisionOutcome.REFINE,
                ArchitectureDecisionOutcome.REDESIGN,
                ArchitectureDecisionOutcome.NO_RELEASE,
            }
        ):
            raise ValueError("invalid execution cannot produce a quality selection")
        if not math.isfinite(self.operational.reported_cost_usd):
            raise ValueError("reported cost must be finite")
        return self


def load_architecture_evolution_program(path: Path) -> ArchitectureEvolutionProgramV1:
    return ArchitectureEvolutionProgramV1.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def load_architecture_run_record(path: Path) -> ArchitectureEvolutionRunRecordV1:
    return ArchitectureEvolutionRunRecordV1.model_validate_json(
        path.read_text(encoding="utf-8")
    )
