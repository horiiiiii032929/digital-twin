"""Finite-program progression and stage-result validation.

Stage implementations write sanitized result envelopes.  This control plane is
the only component allowed to advance the program ledger, so a provider runner
cannot silently promote itself or reinterpret an unfavorable result.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.digital_twin.evaluation.finite_program import (
    ProgramError,
    ProgramLedgerV1,
    ProgramManifestV1,
    ProgramStageName,
    ProgramStageStatus,
    canonical_sha256,
)


class StageResultEnvelopeV1(BaseModel):
    """Sanitized decision returned by one immutable stage implementation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    program_id: Literal["course-digital-twin-evaluation-program-001"]
    program_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    stage: ProgramStageName
    status: ProgramStageStatus
    provider_calls: int = Field(ge=0)
    cost_usd: float = Field(ge=0, allow_inf_nan=False)
    severe_release_count: int = Field(default=0, ge=0)
    private_data_used: Literal[False] = False
    gold_leakage_detected: Literal[False] = False
    identity_drift_detected: Literal[False] = False
    method_changed_during_run: Literal[False] = False
    hard_stop_reason: str | None = None
    metrics: dict[str, int | float | str | bool] = Field(default_factory=dict)
    artifacts: dict[str, str] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_result(self) -> "StageResultEnvelopeV1":
        allowed = {
            ProgramStageStatus.COMPLETED_KEEP,
            ProgramStageStatus.COMPLETED_REFINE,
            ProgramStageStatus.COMPLETED_GO_DEEPER,
            ProgramStageStatus.INVALID_EXECUTION,
        }
        if self.status not in allowed:
            raise ValueError("stage result has a non-decision status")
        expected = canonical_sha256(
            self.model_dump(mode="json", exclude={"result_sha256"})
        )
        if self.result_sha256 != expected:
            raise ValueError("stage result hash drifted")
        return self


StageExecutor = Callable[["StageExecutionContext"], StageResultEnvelopeV1]


@dataclass(frozen=True)
class StageExecutionContext:
    root: Path
    output_root: Path
    manifest: ProgramManifestV1
    stage: ProgramStageName
    resume: bool
    remaining_stage_budget_usd: float
    remaining_program_budget_usd: float
    recorded_stage_provider_calls: int
    recorded_stage_cost_usd: float


def build_stage_result(
    *,
    manifest: ProgramManifestV1,
    stage: ProgramStageName,
    status: ProgramStageStatus,
    provider_calls: int,
    cost_usd: float,
    severe_release_count: int = 0,
    metrics: dict[str, int | float | str | bool] | None = None,
    artifacts: dict[str, str] | None = None,
    limitations: list[str] | None = None,
    hard_stop_reason: str | None = None,
) -> StageResultEnvelopeV1:
    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "program_id": manifest.program_id,
        "program_manifest_sha256": manifest.content_sha256,
        "stage": stage.value,
        "status": status.value,
        "provider_calls": provider_calls,
        "cost_usd": float(cost_usd),
        "severe_release_count": severe_release_count,
        "private_data_used": False,
        "gold_leakage_detected": False,
        "identity_drift_detected": False,
        "method_changed_during_run": False,
        "hard_stop_reason": hard_stop_reason,
        "metrics": metrics or {},
        "artifacts": artifacts or {},
        "limitations": limitations or [],
    }
    payload["result_sha256"] = canonical_sha256(payload)
    return StageResultEnvelopeV1.model_validate(payload)


class FiniteProgramRunner:
    """Run frozen stages once, with one harness-only correction at most."""

    def __init__(
        self,
        *,
        root: Path,
        output_root: Path,
        manifest: ProgramManifestV1,
        ledger: ProgramLedgerV1,
        executors: dict[ProgramStageName, StageExecutor],
    ) -> None:
        expected = {row.name for row in manifest.stages}
        if set(executors) != expected:
            missing = sorted(row.value for row in expected - set(executors))
            extra = sorted(row.value for row in set(executors) - expected)
            raise ProgramError(
                f"stage executor registry drifted; missing={missing}, extra={extra}"
            )
        self.root = root
        self.output_root = output_root
        self.manifest = manifest
        self.ledger = ledger
        self.executors = executors

    def _dependency_failed(self, stage: ProgramStageName) -> bool:
        snapshot = self.ledger.snapshot()
        status_by_name = {
            row["name"]: ProgramStageStatus(row["status"])
            for row in snapshot["stages"]
        }
        specification = self.manifest.stage(stage)
        return any(
            status_by_name[dependency.value]
            not in self.manifest.stage(dependency).valid_keep_statuses
            for dependency in specification.dependencies
        )

    def run(self, *, resume: bool) -> dict[str, Any]:
        factual_failed = False
        for specification in self.manifest.stages:
            stage = specification.name
            current = next(
                row
                for row in self.ledger.snapshot()["stages"]
                if row["name"] == stage.value
            )
            current_status = ProgramStageStatus(current["status"])
            if current_status in {
                ProgramStageStatus.COMPLETED_KEEP,
                ProgramStageStatus.COMPLETED_REFINE,
                ProgramStageStatus.COMPLETED_GO_DEEPER,
                ProgramStageStatus.SKIPPED_DEPENDENCY,
            }:
                factual_failed = factual_failed or (
                    current_status == ProgramStageStatus.COMPLETED_REFINE
                    and not specification.independent_after_factual_failure
                )
                continue
            if (
                self._dependency_failed(stage)
                or factual_failed
                and not specification.independent_after_factual_failure
            ):
                if current_status == ProgramStageStatus.PENDING:
                    self.ledger.skip_stage(stage, reason="factual-dependency-did-not-pass")
                continue

            while True:
                self.ledger.start_stage(stage)
                context = StageExecutionContext(
                    root=self.root,
                    output_root=self.output_root / stage.value,
                    manifest=self.manifest,
                    stage=stage,
                    resume=resume or int(current["execution_attempts"]) > 0,
                    remaining_stage_budget_usd=self.ledger.remaining_budget_usd(stage),
                    remaining_program_budget_usd=float(
                        self.ledger.snapshot()["remaining_budget_usd"]
                    ),
                    recorded_stage_provider_calls=int(current["provider_calls"]),
                    recorded_stage_cost_usd=float(current["cost_usd"]),
                )
                result = self.executors[stage](context)
                if result.program_manifest_sha256 != self.manifest.content_sha256:
                    self.ledger.mark_invalid(stage, reason="result-manifest-drift")
                    raise ProgramError("stage result escaped the program manifest")
                if result.stage != stage:
                    self.ledger.mark_invalid(stage, reason="result-stage-drift")
                    raise ProgramError("stage result identity drifted")
                call_delta = result.provider_calls - int(current["provider_calls"])
                cost_delta = result.cost_usd - float(current["cost_usd"])
                if call_delta < 0 or cost_delta < -1e-9:
                    self.ledger.mark_invalid(stage, reason="stage-accounting-regressed")
                    raise ProgramError("stage cumulative accounting regressed")
                try:
                    self.ledger.record_usage(
                        stage,
                        provider_calls=call_delta,
                        cost_usd=max(0.0, cost_delta),
                    )
                except ProgramError:
                    self.ledger.terminate(reason="program-cost-ceiling")
                    return self.ledger.snapshot()
                if result.status == ProgramStageStatus.INVALID_EXECUTION:
                    self.ledger.mark_invalid(stage, reason="stage-invalid-execution")
                    if result.hard_stop_reason is not None:
                        self.ledger.terminate(reason=result.hard_stop_reason)
                        return self.ledger.snapshot()
                    row = next(
                        row
                        for row in self.ledger.snapshot()["stages"]
                        if row["name"] == stage.value
                    )
                    if int(row["invalid_corrections"]) >= 1:
                        self.ledger.terminate(reason="second-invalid-stage-execution")
                        return self.ledger.snapshot()
                    resume = True
                    current = row
                    continue
                self.ledger.complete_stage(
                    stage,
                    status=result.status,
                    result=result.model_dump(mode="json"),
                )
                if (
                    result.status == ProgramStageStatus.COMPLETED_REFINE
                    and not specification.independent_after_factual_failure
                ):
                    factual_failed = True
                break

        self.ledger.mark_complete()
        return self.ledger.snapshot()
