"""Complete live-executor registry for the finite evaluation program."""

from __future__ import annotations

import sqlite3

from scripts.course_digital_twin_program_factual import (
    run_final_construction,
    run_final_product,
    run_product_development,
    run_retrieval_decision,
)
from scripts.course_digital_twin_program_release import (
    run_release_regression,
    run_reporting,
)
from scripts.course_digital_twin_program_supplementary import (
    run_provider_t0_t1,
    run_synthetic_profile,
    run_true_visual,
)
from src.digital_twin.evaluation.finite_program import (
    ProgramManifestV1,
    ProgramStageName,
    ProgramStageStatus,
)
from src.digital_twin.evaluation.finite_program_runner import (
    StageExecutionContext,
    StageExecutor,
    build_stage_result,
)


LIVE_EXECUTORS_COMPLETE = True
_HARD_STOP_FRAGMENTS = (
    "private data",
    "gold leakage",
    "identity drift",
    "hash drift",
    "checksum drift",
    "security",
    "cost ceiling",
)


def _observed_usage(context: StageExecutionContext) -> tuple[int, float]:
    calls = 0
    cost = 0.0
    if not context.output_root.exists():
        return calls, cost
    for path in context.output_root.rglob("*.sqlite3"):
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            row = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(cost_usd), 0) FROM calls"
            ).fetchone()
        except sqlite3.Error:
            continue
        finally:
            if connection is not None:
                connection.close()
        if row is None:
            continue
        calls += int(row[0])
        cost += float(row[1])
    return calls, cost


def _protected(executor: StageExecutor) -> StageExecutor:
    def run(context: StageExecutionContext):
        try:
            return executor(context)
        except Exception as error:
            calls, cost = _observed_usage(context)
            sanitized = f"{type(error).__name__}: {str(error)[:300]}"
            lowered = sanitized.casefold()
            hard_stop = next(
                (fragment for fragment in _HARD_STOP_FRAGMENTS if fragment in lowered),
                None,
            )
            return build_stage_result(
                manifest=context.manifest,
                stage=context.stage,
                status=ProgramStageStatus.INVALID_EXECUTION,
                provider_calls=calls,
                cost_usd=cost,
                metrics={"failure_type": type(error).__name__},
                limitations=[sanitized],
                hard_stop_reason=hard_stop,
            )

    return run


def live_executors(manifest: ProgramManifestV1) -> dict[ProgramStageName, StageExecutor]:
    del manifest
    values: dict[ProgramStageName, StageExecutor] = {
        ProgramStageName.RETRIEVAL_DECISION: run_retrieval_decision,
        ProgramStageName.PRODUCT_DEVELOPMENT: run_product_development,
        ProgramStageName.FINAL_CONSTRUCTION: run_final_construction,
        ProgramStageName.FINAL_PRODUCT: run_final_product,
        ProgramStageName.TRUE_VISUAL: run_true_visual,
        ProgramStageName.SYNTHETIC_PROFILE: run_synthetic_profile,
        ProgramStageName.PROVIDER_T0_T1: run_provider_t0_t1,
        ProgramStageName.RELEASE_REGRESSION: run_release_regression,
        ProgramStageName.REPORTING: run_reporting,
    }
    return {name: _protected(executor) for name, executor in values.items()}
