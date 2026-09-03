#!/usr/bin/env python3
"""Run the fresh 1,000-case A-versus-H architecture confirmation."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
import subprocess
from typing import Any

from dotenv import load_dotenv

from scripts.run_successor_architecture_development_fold_001 import (
    ALL_ACTIONS,
    ArchitectureDevelopmentError,
    _ProposalMap,
    _ResponseLedger,
    _call_planner_single_cases,
    _eligible_public_rows,
    _file_sha256,
    _initialize_graph_database,
    _job,
    _load_bound_package,
    _load_json,
    _planner_prompt,
    _proposal_from_row,
    _proposal_schema,
)
from src.digital_twin.evaluation.hidden_state_metrics import paired_bootstrap_difference
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
)
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from src.digital_twin.student.autonomy_eligibility import event_scoped_eligible_actions
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
)
from src.digital_twin.student.autonomy_runtime import GovernedAutonomousTutoringGraph
from src.digital_twin.student.planning_architectures import (
    AutonomyArchitectureId,
    GuardedPolicyValuePlanner,
    HierarchicalPlanningProposalV1,
    PlanningStateCardV1,
    SwitchableAutonomyPlanner,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "successor-architecture-confirmation-005-001"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "successor_architecture_confirmation_005_001.json"
)
OUTPUT_ROOT = ROOT / f"reports/generated/{INSTRUMENT_ID}"
PROVIDER_LEDGER = OUTPUT_ROOT / "provider.sqlite3"
RESPONSE_LEDGER = OUTPUT_ROOT / "responses.sqlite3"
GRAPH_LEDGER = OUTPUT_ROOT / "graph-checkpoints.sqlite3"
RESULT_PATH = ROOT / f"research/05_evaluation/records/{INSTRUMENT_ID}.json"
SUMMARY_PATH = ROOT / f"research/05_evaluation/{INSTRUMENT_ID}-results.md"

CONTROL_A = AutonomyArchitectureId.DETERMINISTIC_WORKFLOW_A.value
CANDIDATE_H = GuardedPolicyValuePlanner.implementation_id
CONDITIONS = (CONTROL_A, CANDIDATE_H)


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _binding(instrument: dict[str, Any]) -> dict[str, Any]:
    return {
        "instrument_sha256": _file_sha256(INSTRUMENT_PATH),
        "public_sha256": instrument["dataset"]["public_file_sha256"],
        "gold_sha256": instrument["dataset"]["hidden_gold_file_sha256"],
        "code_revision": _git("rev-parse", "HEAD"),
        "engine": instrument["fixed_engine"],
        "conditions": list(CONDITIONS),
    }


def validate() -> dict[str, Any]:
    instrument = _load_json(INSTRUMENT_PATH)
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise ArchitectureDevelopmentError("confirmation instrument identity drifted")
    public = _load_bound_package(instrument["dataset"], gold=False)
    case_ids = [str(row["case_id"]) for row in public["rows"]]
    if len(case_ids) != 1000 or len(case_ids) != len(set(case_ids)):
        raise ArchitectureDevelopmentError("confirmation public identity drifted")
    if len({str(row["scenario_cluster_id"]) for row in public["rows"]}) != 1000:
        raise ArchitectureDevelopmentError("confirmation scenario clusters drifted")
    if tuple(instrument["conditions"]) != CONDITIONS:
        raise ArchitectureDevelopmentError("confirmation conditions drifted")
    if instrument["execution"]["maximum_provider_calls"] != 801:
        raise ArchitectureDevelopmentError("confirmation call ceiling drifted")
    if instrument["fixed_engine"]["provider_model"] != "gpt-5.6-luna":
        raise ArchitectureDevelopmentError("confirmation engine drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed",
        "instrument_status": instrument["status"],
        "case_count": 1000,
        "condition_cell_count": 2000,
        "provider_execution_authorized": instrument["execution"][
            "provider_execution_authorized"
        ],
        "paid_execution_authorized": instrument["execution"][
            "paid_execution_authorized"
        ],
        "provider_calls": 0,
    }


def preflight(*, resume: bool) -> dict[str, Any]:
    result = validate()
    instrument = _load_json(INSTRUMENT_PATH)
    blockers: list[str] = []
    execution = instrument["execution"]
    if not execution["provider_execution_authorized"]:
        blockers.append("provider-execution-not-authorized")
    if not execution["paid_execution_authorized"]:
        blockers.append("paid-execution-not-authorized")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("OPENAI_API_KEY-missing")
    if _git("status", "--porcelain"):
        blockers.append("working-tree-dirty")
    verified = datetime.fromisoformat(instrument["provider_freshness"]["verified_at"])
    age = (datetime.now(UTC) - verified.astimezone(UTC)).total_seconds() / 3600
    if age > instrument["provider_freshness"]["maximum_age_hours"]:
        blockers.append("provider-metadata-stale")
    for path in (PROVIDER_LEDGER, RESPONSE_LEDGER, GRAPH_LEDGER):
        if resume and not path.exists():
            blockers.append(f"resume-artifact-missing:{path.name}")
        if not resume and path.exists():
            blockers.append(f"exclusive-output-exists:{path.name}")
    if not resume:
        for path in (RESULT_PATH, SUMMARY_PATH):
            if path.exists():
                blockers.append(f"exclusive-output-exists:{path.name}")
    return {
        **result,
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "resume": resume,
    }


def simulate() -> dict[str, Any]:
    instrument = _load_json(INSTRUMENT_PATH)
    public = _load_bound_package(instrument["dataset"], gold=False)
    eligible = _eligible_public_rows(list(public["rows"]))
    return {
        **validate(),
        "status": "simulated-network-free",
        "eligible_case_count": len(eligible),
        "condition_cell_count": len(public["rows"]) * len(CONDITIONS),
        "maximum_provider_calls": 1 + len(eligible),
        "gold_loaded": False,
        "provider_calls": 0,
    }


async def _planner_canary(
    transport: DirectProviderJsonTransport,
    ledger: ProviderCallLedgerV1,
    row: dict[str, Any],
) -> None:
    case_id = str(row["case_id"])
    response = await transport.call_with_ledger(
        ledger=ledger,
        request_key="canary-planner",
        provider_role="confirmation-policy-value-planner-canary",
        system="Return one bounded synthetic pedagogical proposal.",
        prompt=_planner_prompt([row]),
        task="successor_architecture_confirmation_planner_canary",
        schema=_proposal_schema(case_id),
    )
    proposal = _proposal_from_row(response.content)
    eligible = event_scoped_eligible_actions(
        AutonomousEventKind(row["event_kind"]), ALL_ACTIONS
    )
    if proposal.selected_action not in eligible or any(
        step.action not in eligible for step in proposal.episode_steps
    ):
        raise ArchitectureDevelopmentError("confirmation canary left action envelope")


def _condition_job(row: dict[str, Any], condition_id: str):
    job = _job(row)
    suffix = f"--architecture-{condition_id}"
    return job.model_copy(
        update={
            "opportunity": job.opportunity.model_copy(
                update={
                    "opportunity_id": f"{job.opportunity.opportunity_id}{suffix}",
                    "idempotency_key": f"{job.opportunity.idempotency_key}{suffix}",
                }
            )
        }
    )


def _planner_for_condition(
    condition_id: str,
    *,
    provider: _ProposalMap,
    state: PlanningStateCardV1,
):
    if condition_id == CONTROL_A:
        return SwitchableAutonomyPlanner(
            architecture_id=AutonomyArchitectureId.DETERMINISTIC_WORKFLOW_A
        )
    if condition_id == CANDIDATE_H:
        return GuardedPolicyValuePlanner(
            proposal_provider=provider,
            state_card_resolver=lambda _job: state,
        )
    raise ArchitectureDevelopmentError(
        f"unknown confirmation condition: {condition_id}"
    )


async def _run_graphs(
    *,
    public_rows: list[dict[str, Any]],
    proposals: dict[str, HierarchicalPlanningProposalV1 | None],
    response_ledger: _ResponseLedger,
) -> None:
    _initialize_graph_database(GRAPH_LEDGER)
    provider = _ProposalMap(proposals)
    for condition_id in CONDITIONS:
        for row in public_rows:
            case_id = str(row["case_id"])
            if response_ledger.has(condition_id, case_id):
                continue
            state = PlanningStateCardV1.model_validate(row["state_card"])
            graph = GovernedAutonomousTutoringGraph(
                planner=_planner_for_condition(
                    condition_id, provider=provider, state=state
                ),
                checkpoint_database_path=str(GRAPH_LEDGER),
            )
            result = await graph.run(_condition_job(row, condition_id))
            response_ledger.record(
                condition_id,
                case_id,
                {
                    "architecture_id": condition_id,
                    "case_id": case_id,
                    "selected_action": result.action.kind.value,
                    "response": (
                        result.response.model_dump(mode="json")
                        if result.response is not None
                        else None
                    ),
                    "trace": result.trace.model_dump(mode="json"),
                },
            )


def _paired(
    candidate: list[dict[str, Any]],
    control: list[dict[str, Any]],
    *,
    value,
    seed: str,
) -> dict[str, Any]:
    return paired_bootstrap_difference(
        candidate,
        control,
        value=value,
        key=lambda row: row["case_id"],
        resamples=5000,
        seed=seed,
    )


def _score(
    *,
    responses: list[dict[str, Any]],
    public_rows: list[dict[str, Any]],
    gold_rows: list[dict[str, Any]],
    planner_failures: list[str],
    provider_snapshot: dict[str, Any],
) -> dict[str, Any]:
    public_by_id = {str(row["case_id"]): row for row in public_rows}
    gold_by_id = {str(row["case_id"]): row for row in gold_rows}
    scored: list[dict[str, Any]] = []
    for response in responses:
        case_id = str(response["case_id"])
        public = public_by_id[case_id]
        gold = gold_by_id[case_id]
        selected = str(response["selected_action"])
        action = AutonomousActionKind(selected)
        eligible = event_scoped_eligible_actions(
            AutonomousEventKind(public["event_kind"]), ALL_ACTIONS
        )
        boundary = public["guard"] != "eligible"
        intervention = action != AutonomousActionKind.NO_ACTION
        payload = response["response"]
        utility = float(gold["action_utilities"][selected])
        maximum_utility = max(
            float(value) for value in gold["action_utilities"].values()
        )
        scored.append(
            {
                **response,
                "event_action_valid": action in eligible,
                "boundary_action_valid": (not boundary) or not intervention,
                "preferred_action_agreement": selected == gold["expected_action"],
                "policy_utility": utility,
                "policy_regret": maximum_utility - utility,
                "near_optimal_within_0_05": maximum_utility - utility <= 0.05 + 1e-12,
                "intervention": intervention,
                "unnecessary_intervention": boundary and intervention,
                "citation_valid": not intervention
                or (
                    isinstance(payload, dict)
                    and payload.get("source_range_keys") == [f"source-range-{case_id}"]
                ),
                "scope_valid": response["trace"]["course_id"]
                == "synthetic-autonomy-course",
            }
        )
    by_condition = {
        condition: sorted(
            [row for row in scored if row["architecture_id"] == condition],
            key=lambda row: row["case_id"],
        )
        for condition in CONDITIONS
    }
    aggregate: dict[str, Any] = {}
    for condition, rows in by_condition.items():
        interventions = [row for row in rows if row["intervention"]]
        regrets = sorted(float(row["policy_regret"]) for row in rows)
        aggregate[condition] = {
            "case_count": len(rows),
            "event_action_validity": sum(row["event_action_valid"] for row in rows)
            / len(rows),
            "boundary_action_accuracy": sum(
                row["boundary_action_valid"] for row in rows
            )
            / len(rows),
            "preferred_action_agreement": sum(
                row["preferred_action_agreement"] for row in rows
            )
            / len(rows),
            "mean_policy_utility": sum(row["policy_utility"] for row in rows)
            / len(rows),
            "mean_policy_regret": sum(row["policy_regret"] for row in rows) / len(rows),
            "p95_policy_regret": regrets[max(0, int(0.95 * len(rows)) - 1)],
            "near_optimal_within_0_05": sum(
                row["near_optimal_within_0_05"] for row in rows
            )
            / len(rows),
            "proactive_precision": (
                sum(row["preferred_action_agreement"] for row in interventions)
                / len(interventions)
                if interventions
                else 1.0
            ),
            "unnecessary_intervention_rate": sum(
                row["unnecessary_intervention"] for row in rows
            )
            / len(rows),
            "citation_validity": sum(row["citation_valid"] for row in rows) / len(rows),
            "scope_validity": sum(row["scope_valid"] for row in rows) / len(rows),
        }
    a_rows = by_condition[CONTROL_A]
    h_rows = by_condition[CANDIDATE_H]
    preference = _paired(
        h_rows,
        a_rows,
        value=lambda row: float(row["preferred_action_agreement"]),
        seed="confirmation-005-h-vs-a-preference",
    )
    utility = _paired(
        h_rows,
        a_rows,
        value=lambda row: float(row["policy_utility"]),
        seed="confirmation-005-h-vs-a-utility",
    )
    failures = set(planner_failures)
    by_cell = {(row["architecture_id"], row["case_id"]): row for row in scored}
    fallback_checks = [
        by_cell[(CANDIDATE_H, case_id)]["selected_action"]
        == by_cell[(CONTROL_A, case_id)]["selected_action"]
        for case_id in failures
    ]
    fallback_rate = (
        sum(fallback_checks) / len(fallback_checks) if fallback_checks else 1.0
    )
    completion = (800 - len(failures)) / 800
    gates = {
        "all_2000_cells_durable": len(scored) == 2000,
        "zero_duplicate_cells": len(
            {(row["architecture_id"], row["case_id"]) for row in scored}
        )
        == 2000,
        "event_scoped_action_validity_is_1": all(
            row["event_action_valid"] for row in scored
        ),
        "boundary_action_accuracy_is_1": all(
            row["boundary_action_valid"] for row in scored
        ),
        "citation_validity_is_1": all(row["citation_valid"] for row in scored),
        "scope_validity_is_1": all(row["scope_valid"] for row in scored),
        "provider_completion_at_least_0_995": completion >= 0.995,
        "fallback_is_safe_and_deterministic": fallback_rate == 1.0,
    }
    h_confirmed = (
        all(gates.values())
        and preference["ci95"][0] >= -0.05
        and utility["ci95"][0] > 0
        and aggregate[CANDIDATE_H]["mean_policy_regret"]
        <= aggregate[CONTROL_A]["mean_policy_regret"]
        and aggregate[CANDIDATE_H]["near_optimal_within_0_05"] + 0.01
        >= aggregate[CONTROL_A]["near_optimal_within_0_05"]
    )
    selected = (
        CANDIDATE_H if h_confirmed else CONTROL_A if all(gates.values()) else None
    )
    return {
        "status": "completed-keep" if all(gates.values()) else "completed-refine",
        "decision": {
            "outcome": "keep" if all(gates.values()) else "refine",
            "selected_architecture_id": selected,
            "candidate_confirmed": h_confirmed,
            "rationale": (
                "Select guarded policy-value H for cross-engine evaluation because its positive paired utility improvement replicated while every hard gate held."
                if h_confirmed
                else "Retain deterministic A for cross-engine evaluation because H did not replicate every prospective incremental-benefit gate."
                if all(gates.values())
                else "Select no architecture because one or more confirmation hard gates failed."
            ),
        },
        "case_count": 1000,
        "condition_cell_count": 2000,
        "aggregate": aggregate,
        "paired_comparisons": {
            "guarded-policy-value-h-vs-deterministic-a": {
                "preferred_action_difference": preference,
                "utility_difference": utility,
            }
        },
        "provider_quality": {
            "planner_case_count": 800,
            "planner_failure_case_ids": sorted(failures),
            "provider_completion_rate": completion,
            "fallback_safe_and_deterministic_rate": fallback_rate,
        },
        "hard_gates": gates,
        "provider": provider_snapshot,
    }


def _summary(result: dict[str, Any]) -> str:
    lines = [
        f"# {result['run_id']}",
        "",
        f"- **Status:** `{result['status']}`",
        f"- **Decision:** {result['decision']['rationale']}",
        f"- **Cases:** {result['case_count']} contexts / {result['condition_cell_count']} cells.",
        f"- **Provider:** {result['provider']['provider_calls']} calls, USD {result['provider']['reported_cost_usd']:.6f}.",
        "",
        "## Results",
        "",
        "| Condition | Valid action | Preferred action* | Mean utility | Mean regret |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for condition, metrics in result["aggregate"].items():
        lines.append(
            f"| `{condition}` | {metrics['event_action_validity']:.1%} | "
            f"{metrics['preferred_action_agreement']:.1%} | "
            f"{metrics['mean_policy_utility']:.4f} | "
            f"{metrics['mean_policy_regret']:.4f} |"
        )
    lines.extend(
        [
            "",
            "*Preferred-action agreement is diagnostic; deterministic event/action-envelope validity is authoritative.*",
            "",
            "This synthetic confirmation selects an architecture for cross-engine evaluation. It does not establish real student learning or professor fidelity.",
            "",
        ]
    )
    return "\n".join(lines)


async def execute(*, resume: bool) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID, "method_evaluation_execution"
    )
    ready = preflight(resume=resume)
    if ready["status"] != "ready":
        raise ArchitectureDevelopmentError(f"preflight blocked: {ready['blockers']}")
    instrument = _load_json(INSTRUMENT_PATH)
    public = _load_bound_package(instrument["dataset"], gold=False)
    public_rows = list(public["rows"])
    eligible_rows = _eligible_public_rows(public_rows)
    binding = _binding(instrument)
    provider_ledger = ProviderCallLedgerV1(
        PROVIDER_LEDGER,
        run_binding=binding,
        maximum_calls=instrument["execution"]["maximum_provider_calls"],
        maximum_cost_usd=instrument["execution"]["emergency_cost_stop_usd"],
        maximum_transport_retries_total=0,
        resume=resume,
    )
    response_ledger = _ResponseLedger(RESPONSE_LEDGER, binding=binding, resume=resume)
    transport = DirectProviderJsonTransport(instrument["fixed_engine"])
    planner_failures: list[str] = []
    try:
        await _planner_canary(transport, provider_ledger, eligible_rows[0])
        proposals, planner_failures = await _call_planner_single_cases(
            transport=transport,
            ledger=provider_ledger,
            public_rows=eligible_rows,
            concurrency=int(instrument["execution"]["concurrency"]),
        )
        await _run_graphs(
            public_rows=public_rows,
            proposals=proposals,
            response_ledger=response_ledger,
        )
        responses = response_ledger.rows()
        if len(responses) != 2000:
            raise ArchitectureDevelopmentError(
                "responses incomplete before gold opening"
            )
        gold = _load_bound_package(instrument["dataset"], gold=True)
        result = _score(
            responses=responses,
            public_rows=public_rows,
            gold_rows=list(gold["rows"]),
            planner_failures=planner_failures,
            provider_snapshot=provider_ledger.snapshot(),
        )
        result.update(
            {
                "record_schema": "research-evaluation-run-v1",
                "schema_version": 1,
                "run_id": INSTRUMENT_ID,
                "code_revision": _git("rev-parse", "HEAD"),
                "dirty_state": bool(_git("status", "--porcelain")),
                "instrument_sha256": _file_sha256(INSTRUMENT_PATH),
                "public_sha256": instrument["dataset"]["public_file_sha256"],
                "hidden_gold_sha256": instrument["dataset"]["hidden_gold_file_sha256"],
                "limitations": [
                    "Synthetic policy-oracle cases do not establish real learning improvement.",
                    "Preferred-action agreement is diagnostic; the deterministic event/action envelope is authoritative.",
                    "Architecture is confirmed under one fixed planner engine; engine allocation is evaluated separately.",
                    "Luna has no dated snapshot; exact returned identity is required throughout execution.",
                ],
            }
        )
        response_ledger.complete()
        provider_ledger.mark_complete()
        result["provider"] = provider_ledger.snapshot()
        _atomic_write(RESULT_PATH, json.dumps(result, indent=2, sort_keys=True) + "\n")
        _atomic_write(SUMMARY_PATH, _summary(result))
        return result
    except Exception:
        provider_ledger.mark_invalid_execution()
        raise
    finally:
        provider_ledger.close()
        response_ledger.close()


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.execute:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "external_model_evaluation"
        )
        result = asyncio.run(execute(resume=args.resume))
    elif args.preflight:
        result = preflight(resume=args.resume)
    elif args.simulate:
        result = simulate()
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
