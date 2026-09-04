#!/usr/bin/env python3
"""Run the confirmation-024 winner against the sealed 10,000+1,000 benchmark.

Modes, in the order they are meant to be used:

    --validate    check the instrument, the sealed package, and the binding
    --simulate    exercise the whole path on a tiny synthetic package
    --preflight   prove a deterministic arm reaches no provider at all
    --canary N    run N real cases, measure wall time, project the full arm
    --execute     run the arm and leave a durable, resumable ledger

Hidden gold is never touched here. Scoring is a separate step that runs only
once every arm ledger reports a complete response count.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import statistics
import sys
import time
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import academic_factual_qa_open_10000_sealed_package as sealed  # noqa: E402
from scripts import academic_factual_qa_open_10000_winner_adapter as winner  # noqa: E402
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationCaseV1,
    SystemUnderTestManifestV1,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    ResponseLedgerV1,
    canonical_json_sha256,
    execute_cases,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_ID = "academic-factual-qa-open-10000-winner-regression-001"
INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_v1_winner_regression_001.json"
)
OUTPUT_ROOT = ROOT / "reports/generated" / INSTRUMENT_ID
CODE_REVISION = "2bac95d"
# T1-v2 keeps a learner belief state per conversation. Program 011 shared one
# conversation per course because T0 is stateless; doing that here would make
# each case depend on every earlier case in the same course, so every arm runs
# one conversation per case and the ledger binding records that choice.
CONVERSATION_SCOPE = "case"

ARMS: dict[str, dict[str, Any]] = {
    "candidate-deterministic": {
        "case_source": "public_cases",
        "expected_case_count": 10_000,
        "evidence_gate": winner.CANDIDATE_EVIDENCE_GATE,
        "provider_backed": False,
    },
    "control": {
        "case_source": "control_cases",
        "expected_case_count": 1_000,
        "evidence_gate": winner.CONTROL_EVIDENCE_GATE,
        "provider_backed": False,
    },
    "candidate-provider": {
        "case_source": "control_cases",
        "expected_case_count": 1_000,
        "evidence_gate": winner.CANDIDATE_EVIDENCE_GATE,
        "provider_backed": True,
    },
}


class WinnerRunError(RuntimeError):
    """Raised when the run would leave invalid or unreadable evidence."""


def _instrument() -> dict[str, Any]:
    return json.loads(INSTRUMENT_PATH.read_text(encoding="utf-8"))


def _arm_root(arm_id: str) -> Path:
    return OUTPUT_ROOT / arm_id


def _manifest(arm_id: str) -> SystemUnderTestManifestV1:
    arm = ARMS[arm_id]
    bindings = {"factual_generator": "deterministic/evidence-set-v2"}
    if arm["provider_backed"]:
        bindings["reactive_planner"] = "openai/gpt-5.6-luna"
    else:
        bindings["reactive_planner"] = "deterministic/reactive-semantic-planner"
    return SystemUnderTestManifestV1(
        flow_id=winner.WINNER_FLOW_ID,
        adapter_version="v1",
        code_revision=CODE_REVISION,
        profile_sha256=winner.winner_profile_sha256(),
        retriever=winner.WINNER_RETRIEVER_ID,
        generator=winner.WINNER_GENERATOR_ID,
        policy=winner.WINNER_POLICY_ID,
        evidence_gate=arm["evidence_gate"],
        model_bindings=bindings,
        known_benchmark=True,
    )


def _run_configuration(
    arm_id: str,
    package: sealed.SealedPackageV1,
    *,
    case_count: int,
) -> dict[str, Any]:
    return {
        "instrument_id": INSTRUMENT_ID,
        "arm_id": arm_id,
        "code_revision": CODE_REVISION,
        "case_count": case_count,
        "case_source": ARMS[arm_id]["case_source"],
        "conversation_scope": CONVERSATION_SCOPE,
        "construction_result_sha256": package.construction_sha256,
        "package_sha256": dict(sorted(package.package_sha256.items())),
    }


def _cases_for(arm_id: str, package: sealed.SealedPackageV1) -> list[EvaluationCaseV1]:
    source = ARMS[arm_id]["case_source"]
    if source == "public_cases":
        return package.public_cases(strict_count=True)
    return package.control_cases(strict_count=True)


def _build_adapter(
    arm_id: str,
    *,
    package: sealed.SealedPackageV1,
    cases: list[EvaluationCaseV1],
    state_path: Path,
) -> winner.WinnerEvaluationAdapterV1:
    runtime: dict[str, Any] = {
        "state_path": state_path,
        "source_package_path": package.root / "final-source-corpus.json",
        "conversation_scope": CONVERSATION_SCOPE,
    }
    budgeted = None
    if ARMS[arm_id]["provider_backed"]:
        planner, budgeted = _live_reactive_planner()
        runtime["reactive_semantic_planner"] = planner
    adapter = winner.build_winner_adapter(
        manifest=_manifest(arm_id),
        cases=cases,
        runtime=runtime,
    )
    adapter.budgeted_client = budgeted
    return adapter


PROVIDER_ARM_MAXIMUM_COST_USD = 5.0
PROVIDER_ARM_MAXIMUM_CALLS = 4_000


def _live_reactive_planner() -> tuple[Any, Any]:
    """Build the confirmation-024 reactive planner under one arm-wide budget.

    The budget is arm-wide, not per case: the ceiling the researcher authorized
    is a total, so a single BudgetedLlmClient must see every call. The
    authoritative factual generator stays deterministic, exactly as it was in
    confirmation 024; only intent planning reaches a provider.
    """

    from scripts.governed_full_autonomy_v2_1_actual_product_runtime import (
        _engine_client,
        selected_h_e1_engine_binding,
    )
    from services.llm import BudgetedLlmClient
    from src.digital_twin.student.tutoring_graph import LiveReactiveSemanticPlanner

    engine = selected_h_e1_engine_binding()
    if engine.provider == "deterministic":
        raise WinnerRunError("the provider arm requires a provider-backed engine")
    budgeted = BudgetedLlmClient(
        _engine_client(engine, role="planner"),
        max_calls=PROVIDER_ARM_MAXIMUM_CALLS,
        max_cost_usd=PROVIDER_ARM_MAXIMUM_COST_USD,
    )
    planner = LiveReactiveSemanticPlanner(budgeted, model_id=engine.planner_model)
    return planner, budgeted


def validate() -> dict[str, Any]:
    """Check every binding that must hold before any case is executed."""

    instrument = _instrument()
    package = sealed.resolve_sealed_package()
    candidate = package.public_cases(strict_count=True)
    control = package.control_cases(strict_count=True)
    candidate_ids = {row.case_id for row in candidate}
    control_ids = {row.case_id for row in control}
    if not control_ids <= candidate_ids:
        raise WinnerRunError("control cases are not a subset of the candidate package")

    declared = instrument["dataset"]["package_sha256"]
    if declared != dict(sorted(package.package_sha256.items())):
        raise WinnerRunError("instrument package hashes disagree with the sealed disk")
    binding = instrument["selected_binding"]
    if binding["evidence_gate_implementation_id"] != "source-semantic-evidence-atom-gate-v3":
        raise WinnerRunError("instrument evidence gate drifted from confirmation 024")
    if binding["authoritative_factual_generator"] != winner.WINNER_GENERATOR_ID:
        raise WinnerRunError("instrument factual generator drifted from confirmation 024")
    if instrument["gates"]["thresholds_changed"] is not False:
        raise WinnerRunError("registered gate thresholds must not change")
    if not instrument["known_benchmark"]:
        raise WinnerRunError("this package is a known benchmark and must say so")

    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "validated",
        "candidate_case_count": len(candidate),
        "control_case_count": len(control),
        "control_is_paired_subset": True,
        "arms": sorted(ARMS),
        "known_benchmark": True,
        "hidden_gold_opened": False,
        **package.provenance(),
    }


def simulate(arm_id: str) -> dict[str, Any]:
    """Exercise build, execute, resume, and completion on a synthetic package."""

    import tempfile

    package = sealed.resolve_sealed_package()
    cases = _cases_for(arm_id, package)[:8]
    manifest = _manifest(arm_id)
    workspace = Path(tempfile.mkdtemp(prefix="winner-simulate-"))
    adapter = _build_adapter(
        arm_id,
        package=package,
        cases=cases,
        state_path=workspace / "state.sqlite3",
    )
    ledger = ResponseLedgerV1(
        workspace / "responses.sqlite3",
        cases_sha256=package.declared_content_sha256(ARMS[arm_id]["case_source"]),
        system_manifest_sha256=canonical_json_sha256(manifest.model_dump(mode="json")),
        run_configuration_sha256=canonical_json_sha256(
            _run_configuration(arm_id, package, case_count=len(cases))
        ),
        resume=False,
    )
    snapshot = asyncio.run(
        execute_cases(cases=cases, adapter=adapter, manifest=manifest, ledger=ledger)
    )
    ledger.close()
    return {
        "arm_id": arm_id,
        "status": "simulated",
        "case_count": len(cases),
        "ledger_status": snapshot["status"],
        "response_count": snapshot["response_count"],
        "provider_calls": adapter.provider_call_count,
        "workspace": str(workspace),
    }


def preflight(arm_id: str, *, sample: int = 50) -> dict[str, Any]:
    """Prove a deterministic arm reaches no provider before any bulk spend."""

    import tempfile

    if ARMS[arm_id]["provider_backed"]:
        raise WinnerRunError(
            "preflight asserts zero provider calls and cannot run a "
            "provider-backed arm"
        )
    package = sealed.resolve_sealed_package()
    cases = _cases_for(arm_id, package)[:sample]
    workspace = Path(tempfile.mkdtemp(prefix="winner-preflight-"))
    adapter = _build_adapter(
        arm_id,
        package=package,
        cases=cases,
        state_path=workspace / "state.sqlite3",
    )

    async def run() -> list[float]:
        durations: list[float] = []
        for case in cases:
            start = time.monotonic()
            await adapter.evaluate(case)
            durations.append(time.monotonic() - start)
        return durations

    durations = asyncio.run(run())
    adapter.finalize()
    if adapter.provider_call_count != 0:
        raise WinnerRunError(
            "the deterministic fast path made "
            f"{adapter.provider_call_count} provider calls; stop before bulk "
            "and publish a revised call and cost projection"
        )
    return {
        "arm_id": arm_id,
        "status": "preflight-passed",
        "sample_case_count": len(cases),
        "provider_calls": 0,
        "projected_cost_usd": 0.0,
        "mean_seconds_per_case": statistics.fmean(durations),
        "p99_seconds_per_case": _percentile(durations, 0.99),
    }


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
    return ordered[index]


def canary(arm_id: str, *, case_count: int) -> dict[str, Any]:
    """Measure real cases and project the full arm before committing to it."""

    import tempfile

    package = sealed.resolve_sealed_package()
    cases = _cases_for(arm_id, package)[:case_count]
    workspace = Path(tempfile.mkdtemp(prefix="winner-canary-"))
    adapter = _build_adapter(
        arm_id,
        package=package,
        cases=cases,
        state_path=workspace / "state.sqlite3",
    )

    async def run() -> tuple[list[float], list[Any]]:
        durations: list[float] = []
        responses: list[Any] = []
        for case in cases:
            start = time.monotonic()
            responses.append(await adapter.evaluate(case))
            durations.append(time.monotonic() - start)
        return durations, responses

    started = time.monotonic()
    durations, responses = asyncio.run(run())
    elapsed = time.monotonic() - started
    adapter.finalize()

    total = ARMS[arm_id]["expected_case_count"]
    cost = sum(row.usage.cost_usd for row in responses)
    actions: dict[str, int] = {}
    for row in responses:
        actions[row.action] = actions.get(row.action, 0) + 1
    return {
        "arm_id": arm_id,
        "status": "canary-complete",
        "case_count": len(cases),
        "elapsed_seconds": elapsed,
        "mean_seconds_per_case": statistics.fmean(durations),
        "p99_seconds_per_case": _percentile(durations, 0.99),
        "projected_arm_minutes": elapsed / max(len(cases), 1) * total / 60,
        "provider_calls": adapter.provider_call_count,
        "observed_cost_usd": cost,
        "projected_arm_cost_usd": cost / max(len(cases), 1) * total,
        "action_counts": dict(sorted(actions.items())),
        "operational_failures": sum(
            1 for row in responses if row.operational_status != "completed"
        ),
    }


def execute(arm_id: str, *, resume: bool) -> dict[str, Any]:
    """Run the arm and leave a durable ledger. Gold stays sealed."""

    # Executing against the sealed held-out package is a bounded-pilot
    # operation under the active repository freeze, whether or not it spends.
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "heldout_execution")
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID, "method_evaluation_execution"
    )
    if ARMS[arm_id]["provider_backed"]:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "external_model_evaluation"
        )
    package = sealed.resolve_sealed_package()
    cases = _cases_for(arm_id, package)
    manifest = _manifest(arm_id)
    root = _arm_root(arm_id)
    root.mkdir(parents=True, exist_ok=True)
    adapter = _build_adapter(
        arm_id,
        package=package,
        cases=cases,
        state_path=root / "state.sqlite3",
    )
    ledger = ResponseLedgerV1(
        root / "responses.sqlite3",
        cases_sha256=package.declared_content_sha256(ARMS[arm_id]["case_source"]),
        system_manifest_sha256=canonical_json_sha256(manifest.model_dump(mode="json")),
        run_configuration_sha256=canonical_json_sha256(
            _run_configuration(arm_id, package, case_count=len(cases))
        ),
        resume=resume,
    )
    started = time.monotonic()
    try:
        snapshot = asyncio.run(
            execute_cases(
                cases=cases,
                adapter=adapter,
                manifest=manifest,
                ledger=ledger,
            )
        )
    finally:
        elapsed = time.monotonic() - started
    result = {
        "arm_id": arm_id,
        "status": "executed",
        "case_count": len(cases),
        "elapsed_seconds": elapsed,
        "ledger_status": snapshot["status"],
        "response_count": snapshot["response_count"],
        "provider_calls": adapter.provider_call_count,
        "ledger_path": str(root / "responses.sqlite3"),
        "hidden_gold_opened": False,
        **_run_configuration(arm_id, package, case_count=len(cases)),
    }
    if not ARMS[arm_id]["provider_backed"] and adapter.provider_call_count != 0:
        raise WinnerRunError(
            f"deterministic arm {arm_id} made "
            f"{adapter.provider_call_count} provider calls"
        )
    budgeted = getattr(adapter, "budgeted_client", None)
    if budgeted is not None:
        snapshot = budgeted.snapshot()
        result["provider_budget"] = {
            "maximum_cost_usd": PROVIDER_ARM_MAXIMUM_COST_USD,
            "observed_cost_usd": sum(
                row.get("reported_cost_usd") or 0.0
                for row in snapshot.get("call_records", [])
            ),
            "call_count": len(snapshot.get("call_records", [])),
        }
    (root / "execution-result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    ledger.close()
    return result


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=sorted(ARMS), default="candidate-deterministic")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--canary", type=int, metavar="N")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()

    if arguments.execute:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "heldout_execution")
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
    if arguments.validate:
        result = validate()
    elif arguments.simulate:
        result = simulate(arguments.arm)
    elif arguments.preflight:
        result = preflight(arguments.arm)
    elif arguments.canary is not None:
        result = canary(arguments.arm, case_count=arguments.canary)
    else:
        result = execute(arguments.arm, resume=arguments.resume)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
