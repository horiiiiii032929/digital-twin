"""Contracts for the finite A/B/C autonomy architecture tournament."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.digital_twin.model_policy import (
    OPENAI_GPT_5_6_LUNA_MODEL,
    OPENAI_GPT_5_6_TERRA_MODEL,
    OPENAI_HIGH_VOLUME_MODEL,
)
from src.digital_twin.student.planning_architectures import AutonomyArchitectureId


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ArchitectureEngineAllocationV1(_Contract):
    allocation_id: Literal["e1", "e2", "e3", "e4"]
    provider: Literal["openai-direct"] = "openai-direct"
    planner_model: str
    generator_model: str
    verifier_model: str = OPENAI_GPT_5_6_LUNA_MODEL
    planner_reasoning_effort: Literal["low"] = "low"
    generator_reasoning_effort: Literal["none", "low"] = "none"
    store: Literal[False] = False
    fallback_allowed: Literal[False] = False
    exact_returned_identity_required: Literal[True] = True


class ArchitectureEvaluationStageV1(_Contract):
    stage_id: str = Field(min_length=1, max_length=128)
    case_count: int = Field(ge=1)
    maximum_executions: int = Field(ge=1)
    may_influence_development: bool
    requires_previous_pass: bool


class AutonomyArchitectureTournamentProgramV1(_Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    program_id: Literal["successor-architecture-paired-comparison-001"]
    owner_issue: Literal[184]
    status: Literal[
        "build-only",
        "frozen-pending-execution",
        "running",
        "completed-keep",
        "completed-refine",
        "invalid-execution",
    ]
    architectures: list[AutonomyArchitectureId] = Field(min_length=4, max_length=4)
    historical_controls: list[str] = Field(min_length=3)
    simulator_bounds: list[Literal["oracle", "never-intervene"]] = Field(
        min_length=2, max_length=2
    )
    engine_allocations: list[ArchitectureEngineAllocationV1] = Field(
        min_length=4, max_length=4
    )
    shared_authorities: list[str] = Field(min_length=1)
    stages: list[ArchitectureEvaluationStageV1] = Field(min_length=7)
    maximum_improvement_rounds: Literal[3]
    same_confirmation_quality_rerun_allowed: Literal[False]
    deterministic_truth_authoritative: Literal[True]
    llm_review_advisory_only: Literal[True]
    human_participants_required: Literal[False]
    paid_execution_authorized: bool
    automatic_progression_after_pass: bool
    total_emergency_budget_usd: float = Field(gt=0, le=100)
    hard_gates: list[str] = Field(min_length=1)
    decision_rule: str = Field(min_length=1)
    provider_freshness: dict[str, str | int | bool] = Field(min_length=1)
    prohibited_models: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def comparison_is_paired_finite_and_low_cost(
        self,
    ) -> "AutonomyArchitectureTournamentProgramV1":
        expected_architectures = set(AutonomyArchitectureId)
        if set(self.architectures) != expected_architectures:
            raise ValueError("tournament must include A, B, C, and C+V exactly once")
        if len(self.historical_controls) != len(set(self.historical_controls)):
            raise ValueError("historical controls must be unique")
        if len(self.stages) != len({stage.stage_id for stage in self.stages}):
            raise ValueError("tournament stage IDs must be unique")
        allocations = {item.allocation_id: item for item in self.engine_allocations}
        expected_allocations = {
            "e1": (OPENAI_GPT_5_6_LUNA_MODEL, OPENAI_GPT_5_6_LUNA_MODEL),
            "e2": (OPENAI_GPT_5_6_TERRA_MODEL, OPENAI_GPT_5_6_LUNA_MODEL),
            "e3": (OPENAI_GPT_5_6_LUNA_MODEL, OPENAI_HIGH_VOLUME_MODEL),
            "e4": (OPENAI_GPT_5_6_TERRA_MODEL, OPENAI_HIGH_VOLUME_MODEL),
        }
        if set(allocations) != set(expected_allocations):
            raise ValueError("tournament must bind E1 through E4 exactly once")
        for allocation_id, expected in expected_allocations.items():
            allocation = allocations[allocation_id]
            if (allocation.planner_model, allocation.generator_model) != expected:
                raise ValueError(f"{allocation_id.upper()} model allocation drifted")
        serialized = self.model_dump_json().casefold()
        if any(
            prohibited.casefold() in serialized
            for prohibited in ("gpt-5.6-sol", "openrouter", "deepseek", "gemma", "claude")
        ):
            # The explicit prohibited_models inventory is allowed to name the
            # excluded families, so validate the active bindings separately.
            active = " ".join(
                f"{item.provider} {item.planner_model} {item.generator_model} "
                f"{item.verifier_model}"
                for item in self.engine_allocations
            ).casefold()
            if any(
                prohibited in active
                for prohibited in ("gpt-5.6-sol", "openrouter", "deepseek", "gemma", "claude")
            ):
                raise ValueError("a prohibited model or provider entered an active binding")
        return self


__all__ = [
    "ArchitectureEngineAllocationV1",
    "ArchitectureEvaluationStageV1",
    "AutonomyArchitectureTournamentProgramV1",
]
