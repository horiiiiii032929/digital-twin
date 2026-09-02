#!/usr/bin/env python3
"""Run the fixed-H 2x2 planner-by-generator engine comparison."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from typing import Any

from dotenv import load_dotenv

from scripts.run_successor_architecture_development_fold_001 import (
    ALL_ACTIONS,
    ArchitectureDevelopmentError,
    _ResponseLedger,
    _eligible_public_rows,
    _file_sha256,
    _initialize_graph_database,
    _job,
    _load_bound_package,
    _load_json,
    _planner_prompt,
    _proposal_from_row,
    _proposal_schema,
    _provider_failure_is_run_invalid,
)
from src.digital_twin.evaluation.hidden_state_metrics import paired_bootstrap_difference
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
    ProviderJsonError,
)
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from src.digital_twin.student.autonomy_eligibility import event_scoped_eligible_actions
from src.digital_twin.student.autonomy_eligibility import preferred_event_action
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
    GroundedTutorResponseV2,
)
from src.digital_twin.student.autonomy_runtime import (
    DeterministicAutonomousWordingGenerator,
    GovernedAutonomousTutoringGraph,
)
from src.digital_twin.student.planning_architectures import (
    GuardedPolicyValuePlanner,
    HierarchicalPlanningProposalV1,
    PlanningStateCardV1,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "successor-architecture-engine-comparison-006-001"
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "successor_architecture_engine_comparison_006_001.json"
)
OUTPUT_ROOT = ROOT / f"reports/generated/{INSTRUMENT_ID}"
PROVIDER_LEDGER = OUTPUT_ROOT / "provider.sqlite3"
RESPONSE_LEDGER = OUTPUT_ROOT / "responses.sqlite3"
GRAPH_LEDGER = OUTPUT_ROOT / "graph-checkpoints.sqlite3"
RESULT_PATH = ROOT / f"research/05_evaluation/records/{INSTRUMENT_ID}.json"
SUMMARY_PATH = ROOT / f"research/05_evaluation/{INSTRUMENT_ID}-results.md"
ALLOCATION_IDS = ("e1", "e2", "e3", "e4")
LEAD_STYLES = ("direct", "encouraging", "reflective")
PROMPT_MODES = ("explain", "retrieve", "contrast", "apply")
LEAD_TEXT = {
    "direct": "Use this approved course evidence for the next step.",
    "encouraging": "You can use this approved course evidence to make the next step concrete.",
    "reflective": "Pause and connect the next step to this approved course evidence.",
}
PROMPT_TEXT = {
    "explain": "Explain the next step in your own words.",
    "retrieve": "Recall the key point before continuing.",
    "contrast": "Contrast this point with the alternative you considered.",
    "apply": "Apply this point to the current activity.",
}


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _allocation_map(instrument: dict[str, Any]) -> dict[str, dict[str, str]]:
    rows = instrument["engine_allocations"]
    result = {str(row["allocation_id"]): dict(row) for row in rows}
    if tuple(result) != ALLOCATION_IDS:
        raise ArchitectureDevelopmentError("engine allocations drifted")
    return result


def _binding(instrument: dict[str, Any]) -> dict[str, Any]:
    return {
        "instrument_sha256": _file_sha256(INSTRUMENT_PATH),
        "public_sha256": instrument["dataset"]["public_file_sha256"],
        "gold_sha256": instrument["dataset"]["hidden_gold_file_sha256"],
        "code_revision": _git("rev-parse", "HEAD"),
        "architecture": instrument["design"]["architecture_fixed"],
        "engine_allocations": instrument["engine_allocations"],
        "provider_bindings": instrument["provider_bindings"],
    }


def validate() -> dict[str, Any]:
    instrument = _load_json(INSTRUMENT_PATH)
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise ArchitectureDevelopmentError("engine instrument identity drifted")
    public = _load_bound_package(instrument["dataset"], gold=False)
    case_ids = [str(row["case_id"]) for row in public["rows"]]
    if len(case_ids) != 300 or len(case_ids) != len(set(case_ids)):
        raise ArchitectureDevelopmentError("engine public identities drifted")
    if len({str(row["scenario_cluster_id"]) for row in public["rows"]}) != 300:
        raise ArchitectureDevelopmentError("engine scenario clusters drifted")
    allocations = _allocation_map(instrument)
    expected = {
        "e1": ("gpt-5.6-luna", "gpt-5.6-luna"),
        "e2": ("gpt-5.6-terra", "gpt-5.6-luna"),
        "e3": ("gpt-5.6-luna", "gpt-5.4-mini-2026-03-17"),
        "e4": ("gpt-5.6-terra", "gpt-5.4-mini-2026-03-17"),
    }
    for allocation_id, models in expected.items():
        observed = allocations[allocation_id]
        if (observed["planner_model"], observed["generator_model"]) != models:
            raise ArchitectureDevelopmentError(
                f"{allocation_id} model allocation drifted"
            )
    if instrument["execution"]["maximum_provider_calls"] != 1444:
        raise ArchitectureDevelopmentError("engine call ceiling drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed",
        "instrument_status": instrument["status"],
        "case_count": 300,
        "allocation_cell_count": 1200,
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


async def _simulate_network_free() -> dict[str, Any]:
    instrument = _load_json(INSTRUMENT_PATH)
    public = _load_bound_package(instrument["dataset"], gold=False)
    public_rows = list(public["rows"])
    eligible = _eligible_public_rows(public_rows)
    sampled = eligible[:8] + [row for row in public_rows if row["guard"] != "eligible"][:4]
    allocations = _allocation_map(instrument)
    proposals: dict[str, HierarchicalPlanningProposalV1 | None] = {}
    for row in sampled:
        if row["guard"] != "eligible":
            continue
        action = preferred_event_action(
            AutonomousEventKind(row["event_kind"]), ALL_ACTIONS
        )
        proposals[str(row["case_id"])] = HierarchicalPlanningProposalV1(
            selected_action=action,
            reason_code="network-free-simulation",
            expected_learner_action="Respond in the course workspace.",
            outcome_observation="Observe one learner response.",
            stop_condition="Stop after one bounded action.",
            replan_condition="Replan only after a new durable event.",
        )
    planner_values = {
        "gpt-5.6-luna": dict(proposals),
        "gpt-5.6-terra": dict(proposals),
    }
    generator_values: dict[str, dict[str, GroundedTutorResponseV2 | None]] = {}
    for allocation_id, allocation in allocations.items():
        actions = await _selected_actions(sampled[:8], allocation, proposals)
        generator_values[allocation_id] = {
            str(row["case_id"]): _safe_wording_response(
                row, actions[str(row["case_id"])]
            )
            for row in sampled[:8]
        }
    with tempfile.TemporaryDirectory(prefix="engine-comparison-006-") as directory:
        root = Path(directory)
        response_ledger = _ResponseLedger(
            root / "responses.sqlite3",
            binding={"simulation": INSTRUMENT_ID},
            resume=False,
        )
        try:
            await _run_graphs(
                public_rows=sampled,
                allocations=allocations,
                planner_values=planner_values,
                generator_values=generator_values,
                planner_failures={
                    "gpt-5.6-luna": set(),
                    "gpt-5.6-terra": set(),
                },
                generator_failures={allocation_id: set() for allocation_id in ALLOCATION_IDS},
                response_ledger=response_ledger,
                graph_ledger=root / "graph.sqlite3",
            )
            simulated_cells = len(response_ledger.rows())
        finally:
            response_ledger.close()
    return {
        **validate(),
        "status": "simulated-network-free",
        "eligible_case_count": len(eligible),
        "allocation_cell_count": len(public["rows"]) * len(ALLOCATION_IDS),
        "simulated_case_count": len(sampled),
        "simulated_cell_count": simulated_cells,
        "maximum_provider_calls": 4 + len(eligible) * 2 + len(eligible) * 4,
        "gold_loaded": False,
        "provider_calls": 0,
    }


def simulate() -> dict[str, Any]:
    return asyncio.run(_simulate_network_free())


def _wording_schema(case_id: str, action: AutonomousActionKind) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "case_id": {"type": "string", "enum": [case_id]},
            "action": {"type": "string", "enum": [action.value]},
            "lead_style": {"type": "string", "enum": list(LEAD_STYLES)},
            "prompt_mode": {"type": "string", "enum": list(PROMPT_MODES)},
        },
        "required": [
            "case_id",
            "action",
            "lead_style",
            "prompt_mode",
        ],
    }


def _wording_prompt(
    row: dict[str, Any], action: AutonomousActionKind
) -> str:
    return json.dumps(
        {
            "instruction": (
                "Choose one lead style and one learner-prompt mode for a concise in-app "
                "tutoring intervention. Do not write free text or repeat the evidence. "
                "Do not change the action, scope, evidence, or case_id."
            ),
            "case_id": row["case_id"],
            "event_kind": row["event_kind"],
            "action": action.value,
            "objective": row["objective"],
            "approved_evidence": row["evidence_quote"],
            "lead_styles": list(LEAD_STYLES),
            "prompt_modes": list(PROMPT_MODES),
        },
        sort_keys=True,
    )


def _wording_response(
    row: dict[str, Any],
    action: AutonomousActionKind,
    payload: dict[str, Any],
) -> GroundedTutorResponseV2:
    case_id = str(row["case_id"])
    evidence = str(row["evidence_quote"])
    if set(payload) != {"case_id", "action", "lead_style", "prompt_mode"}:
        raise ValueError("wording payload fields drifted")
    if payload.get("case_id") != case_id or payload.get("action") != action.value:
        raise ValueError("wording identity or action drifted")
    lead_style = str(payload.get("lead_style", ""))
    prompt_mode = str(payload.get("prompt_mode", ""))
    if lead_style not in LEAD_TEXT or prompt_mode not in PROMPT_TEXT:
        raise ValueError("wording strategy drifted")
    source_key = f"source-range-{case_id}"
    return GroundedTutorResponseV2(
        action=action,
        content=(
            f'{LEAD_TEXT[lead_style]} "{evidence}" {PROMPT_TEXT[prompt_mode]}'
        ),
        atomic_claims=[evidence],
        citation_ids=[f"citation:{source_key}"],
        source_range_keys=[source_key],
        policy_action="answer",
    )


def _safe_wording_response(
    row: dict[str, Any], action: AutonomousActionKind
) -> GroundedTutorResponseV2:
    """Return a source-extractive fallback without another provider call."""

    return _wording_response(
        row,
        action,
        {
            "case_id": row["case_id"],
            "action": action.value,
            "lead_style": "direct",
            "prompt_mode": "retrieve",
        },
    )


class _PlannerMap:
    def __init__(
        self,
        *,
        model_id: str,
        values: dict[str, HierarchicalPlanningProposalV1 | None],
    ) -> None:
        self.model_id = model_id
        self.values = values

    async def propose(self, **kwargs):
        case_id = _case_id(kwargs["job"].opportunity.opportunity_id)
        value = self.values.get(case_id)
        if value is None:
            raise ValueError("no persisted engine proposal")
        return value


class _GeneratorMap:
    def __init__(
        self,
        *,
        model_id: str,
        values: dict[str, GroundedTutorResponseV2 | None],
    ) -> None:
        self.model_id = model_id
        self.values = values
        self.fallback = DeterministicAutonomousWordingGenerator()

    async def generate(self, job, plan):
        case_id = _case_id(job.opportunity.opportunity_id)
        value = self.values.get(case_id)
        if value is not None:
            return value
        return await self.fallback.generate(job, plan)


def _case_id(opportunity_id: str) -> str:
    return opportunity_id.removeprefix("opportunity-").split("--allocation-", 1)[0]


def _engine_job(row: dict[str, Any], allocation: dict[str, str]):
    job = _job(row)
    allocation_id = allocation["allocation_id"]
    suffix = f"--allocation-{allocation_id}"
    goal = job.goal.model_copy(
        update={
            "planner_model": allocation["planner_model"],
            "generator_model": allocation["generator_model"],
        }
    ) if job.goal is not None else None
    opportunity = job.opportunity.model_copy(
        update={
            "opportunity_id": f"{job.opportunity.opportunity_id}{suffix}",
            "idempotency_key": f"{job.opportunity.idempotency_key}{suffix}",
            "planner_model": allocation["planner_model"],
            "generator_model": allocation["generator_model"],
        }
    )
    return job.model_copy(update={"goal": goal, "opportunity": opportunity})


async def _planner_canary(
    transport: DirectProviderJsonTransport,
    ledger: ProviderCallLedgerV1,
    row: dict[str, Any],
    model: str,
) -> None:
    case_id = str(row["case_id"])
    response = await transport.call_with_ledger(
        ledger=ledger,
        request_key=f"canary-planner-{model}",
        provider_role=f"canary-planner:{model}",
        system="Return one bounded synthetic pedagogical proposal.",
        prompt=_planner_prompt([row]),
        task="successor_engine_comparison_planner_canary",
        schema=_proposal_schema(case_id),
    )
    proposal = _proposal_from_row(response.content)
    eligible = event_scoped_eligible_actions(
        AutonomousEventKind(row["event_kind"]), ALL_ACTIONS
    )
    if proposal.selected_action not in eligible:
        raise ArchitectureDevelopmentError("engine planner canary left action envelope")


async def _generator_canary(
    transport: DirectProviderJsonTransport,
    ledger: ProviderCallLedgerV1,
    row: dict[str, Any],
    model: str,
) -> None:
    action = event_scoped_eligible_actions(
        AutonomousEventKind(row["event_kind"]), ALL_ACTIONS
    )[0]
    response = await transport.call_with_ledger(
        ledger=ledger,
        request_key=f"canary-generator-{model}",
        provider_role=f"canary-generator:{model}",
        system="Return one bounded source-grounded intervention wording object.",
        prompt=_wording_prompt(row, action),
        task="successor_engine_comparison_generator_canary",
        schema=_wording_schema(str(row["case_id"]), action),
    )
    _wording_response(row, action, response.content)


async def _call_planners(
    *,
    model: str,
    transport: DirectProviderJsonTransport,
    ledger: ProviderCallLedgerV1,
    rows: list[dict[str, Any]],
    concurrency: int,
) -> tuple[dict[str, HierarchicalPlanningProposalV1 | None], set[str]]:
    values: dict[str, HierarchicalPlanningProposalV1 | None] = {}
    failures: set[str] = set()

    async def call_one(row: dict[str, Any]):
        case_id = str(row["case_id"])
        try:
            response = await transport.call_with_ledger(
                ledger=ledger,
                request_key=f"planner-{model}-{case_id}",
                provider_role=f"planner:{model}",
                system=(
                    "Return one bounded pedagogical proposal. Do not include hidden "
                    "reasoning or personal data."
                ),
                prompt=_planner_prompt([row]),
                task="successor_engine_comparison_planner",
                schema=_proposal_schema(case_id),
                quarantine_failures=True,
            )
            proposal = _proposal_from_row(response.content)
            eligible = event_scoped_eligible_actions(
                AutonomousEventKind(row["event_kind"]), ALL_ACTIONS
            )
            if proposal.selected_action not in eligible or any(
                step.action not in eligible for step in proposal.episode_steps
            ):
                raise ValueError("planner left deterministic action envelope")
            return case_id, proposal, None
        except ProviderJsonError as error:
            if _provider_failure_is_run_invalid(error):
                raise
            return case_id, None, type(error).__name__
        except ValueError as error:
            return case_id, None, type(error).__name__

    for offset in range(0, len(rows), concurrency):
        completed = await asyncio.gather(
            *(call_one(row) for row in rows[offset : offset + concurrency])
        )
        for case_id, proposal, failure in completed:
            values[case_id] = proposal
            if failure is not None:
                failures.add(case_id)
    return values, failures


async def _selected_actions(
    rows: list[dict[str, Any]],
    allocation: dict[str, str],
    proposals: dict[str, HierarchicalPlanningProposalV1 | None],
) -> dict[str, AutonomousActionKind]:
    provider = _PlannerMap(model_id=allocation["planner_model"], values=proposals)
    selected: dict[str, AutonomousActionKind] = {}
    for row in rows:
        state = PlanningStateCardV1.model_validate(row["state_card"])
        planner = GuardedPolicyValuePlanner(
            proposal_provider=provider,
            state_card_resolver=lambda _job, state=state: state,
        )
        output = await planner.plan(_engine_job(row, allocation))
        selected[str(row["case_id"])] = output.action
    return selected


async def _call_generators(
    *,
    allocation: dict[str, str],
    transport: DirectProviderJsonTransport,
    ledger: ProviderCallLedgerV1,
    rows: list[dict[str, Any]],
    actions: dict[str, AutonomousActionKind],
    concurrency: int,
) -> tuple[dict[str, GroundedTutorResponseV2 | None], set[str]]:
    values: dict[str, GroundedTutorResponseV2 | None] = {}
    failures: set[str] = set()
    allocation_id = allocation["allocation_id"]
    model = allocation["generator_model"]

    async def call_one(row: dict[str, Any]):
        case_id = str(row["case_id"])
        action = actions[case_id]
        if action == AutonomousActionKind.NO_ACTION:
            return case_id, None, None
        try:
            response = await transport.call_with_ledger(
                ledger=ledger,
                request_key=f"generator-{allocation_id}-{case_id}",
                provider_role=f"generator:{allocation_id}:{model}",
                system=(
                    "Return one concise source-grounded tutoring intervention object. "
                    "Never add academic facts."
                ),
                prompt=_wording_prompt(row, action),
                task="successor_engine_comparison_generator",
                schema=_wording_schema(case_id, action),
                quarantine_failures=True,
            )
            return case_id, _wording_response(row, action, response.content), None
        except ProviderJsonError as error:
            if _provider_failure_is_run_invalid(error):
                raise
            return case_id, _safe_wording_response(row, action), type(error).__name__
        except ValueError as error:
            return case_id, _safe_wording_response(row, action), type(error).__name__

    for offset in range(0, len(rows), concurrency):
        completed = await asyncio.gather(
            *(call_one(row) for row in rows[offset : offset + concurrency])
        )
        for case_id, response, failure in completed:
            values[case_id] = response
            if failure is not None:
                failures.add(case_id)
    return values, failures


async def _run_graphs(
    *,
    public_rows: list[dict[str, Any]],
    allocations: dict[str, dict[str, str]],
    planner_values: dict[str, dict[str, HierarchicalPlanningProposalV1 | None]],
    generator_values: dict[str, dict[str, GroundedTutorResponseV2 | None]],
    planner_failures: dict[str, set[str]],
    generator_failures: dict[str, set[str]],
    response_ledger: _ResponseLedger,
    graph_ledger: Path = GRAPH_LEDGER,
) -> None:
    _initialize_graph_database(graph_ledger)
    for allocation_id in ALLOCATION_IDS:
        allocation = allocations[allocation_id]
        provider = _PlannerMap(
            model_id=allocation["planner_model"],
            values=planner_values[allocation["planner_model"]],
        )
        generator = _GeneratorMap(
            model_id=allocation["generator_model"],
            values=generator_values[allocation_id],
        )
        for row in public_rows:
            case_id = str(row["case_id"])
            if response_ledger.has(allocation_id, case_id):
                continue
            state = PlanningStateCardV1.model_validate(row["state_card"])
            graph = GovernedAutonomousTutoringGraph(
                planner=GuardedPolicyValuePlanner(
                    proposal_provider=provider,
                    state_card_resolver=lambda _job, state=state: state,
                ),
                generator=generator,
                checkpoint_database_path=str(graph_ledger),
            )
            result = await graph.run(_engine_job(row, allocation))
            response_ledger.record(
                allocation_id,
                case_id,
                {
                    "allocation_id": allocation_id,
                    "case_id": case_id,
                    "planner_model": allocation["planner_model"],
                    "generator_model": allocation["generator_model"],
                    "selected_action": result.action.kind.value,
                    "response": (
                        result.response.model_dump(mode="json")
                        if result.response is not None
                        else None
                    ),
                    "trace": result.trace.model_dump(mode="json"),
                    "planner_provider_success": (
                        case_id not in planner_failures[allocation["planner_model"]]
                    ),
                    "generator_provider_success": (
                        case_id not in generator_failures[allocation_id]
                    ),
                },
            )


def _provider_roles(ledger_path: Path) -> dict[str, dict[str, Any]]:
    connection = sqlite3.connect(f"file:{ledger_path}?mode=ro", uri=True)
    try:
        result: dict[str, dict[str, Any]] = {}
        roles = [
            str(row[0])
            for row in connection.execute(
                "SELECT DISTINCT provider_role FROM calls "
                "WHERE provider_role NOT LIKE 'canary-%' ORDER BY provider_role"
            )
        ]
        for role in roles:
            rows = list(
                connection.execute(
                    "SELECT status,input_tokens,output_tokens,cost_usd,latency_ms "
                    "FROM calls WHERE provider_role=? ORDER BY sequence",
                    (role,),
                )
            )
            latencies = sorted(float(row[4]) for row in rows)
            completed = sum(row[0] == "completed" for row in rows)
            result[role] = {
                "calls": len(rows),
                "completed_calls": completed,
                "completion_rate": completed / len(rows) if rows else 1.0,
                "input_tokens": sum(int(row[1]) for row in rows),
                "output_tokens": sum(int(row[2]) for row in rows),
                "cost_usd": sum(float(row[3]) for row in rows),
                "p95_latency_ms": (
                    latencies[max(0, int(0.95 * len(latencies)) - 1)]
                    if latencies
                    else 0.0
                ),
            }
        return result
    finally:
        connection.close()


def _paired(
    candidate: list[dict[str, Any]],
    control: list[dict[str, Any]],
    *,
    field: str,
    seed: str,
) -> dict[str, Any]:
    return paired_bootstrap_difference(
        candidate,
        control,
        value=lambda row: float(row[field]),
        key=lambda row: row["case_id"],
        resamples=5000,
        seed=seed,
    )


def _factor_effect(
    by_allocation: dict[str, list[dict[str, Any]]],
    *,
    candidate_allocations: tuple[str, ...],
    control_allocations: tuple[str, ...],
    field: str,
    seed: str,
    eligible_only: bool = False,
    interventions_only: bool = False,
) -> dict[str, Any]:
    """Estimate a 2x2 factor effect at the scenario-cluster grain."""

    indexed = {
        allocation_id: {str(row["case_id"]): row for row in rows}
        for allocation_id, rows in by_allocation.items()
    }
    case_ids = sorted(set.intersection(*(set(rows) for rows in indexed.values())))
    candidate: list[dict[str, Any]] = []
    control: list[dict[str, Any]] = []
    for case_id in case_ids:
        all_rows = [indexed[allocation_id][case_id] for allocation_id in ALLOCATION_IDS]
        if eligible_only and any(row["guard"] != "eligible" for row in all_rows):
            continue
        candidate_rows = [indexed[item][case_id] for item in candidate_allocations]
        control_rows = [indexed[item][case_id] for item in control_allocations]
        if interventions_only:
            candidate_rows = [row for row in candidate_rows if row["intervention"]]
            control_rows = [row for row in control_rows if row["intervention"]]
            if not candidate_rows and not control_rows:
                continue
            if len(candidate_rows) != len(control_rows):
                continue
        candidate.append(
            {
                "case_id": case_id,
                "factor_value": sum(float(row[field]) for row in candidate_rows)
                / len(candidate_rows),
            }
        )
        control.append(
            {
                "case_id": case_id,
                "factor_value": sum(float(row[field]) for row in control_rows)
                / len(control_rows),
            }
        )
    return _paired(
        candidate,
        control,
        field="factor_value",
        seed=seed,
    )


def _allowed_wording_contents(
    row: dict[str, Any], action: AutonomousActionKind
) -> set[str]:
    return {
        _wording_response(
            row,
            action,
            {
                "case_id": row["case_id"],
                "action": action.value,
                "lead_style": lead_style,
                "prompt_mode": prompt_mode,
            },
        ).content
        for lead_style in LEAD_STYLES
        for prompt_mode in PROMPT_MODES
    }


def _score(
    *,
    responses: list[dict[str, Any]],
    public_rows: list[dict[str, Any]],
    gold_rows: list[dict[str, Any]],
    role_metrics: dict[str, dict[str, Any]],
    provider_snapshot: dict[str, Any],
) -> dict[str, Any]:
    public_by_id = {str(row["case_id"]): row for row in public_rows}
    gold_by_id = {str(row["case_id"]): row for row in gold_rows}
    scored: list[dict[str, Any]] = []
    for response in responses:
        case_id = str(response["case_id"])
        public = public_by_id[case_id]
        gold = gold_by_id[case_id]
        action = AutonomousActionKind(str(response["selected_action"]))
        eligible = event_scoped_eligible_actions(
            AutonomousEventKind(public["event_kind"]), ALL_ACTIONS
        )
        boundary = public["guard"] != "eligible"
        intervention = action != AutonomousActionKind.NO_ACTION
        payload = response["response"]
        expected_key = f"source-range-{case_id}"
        allowed_contents = (
            _allowed_wording_contents(public, action) if intervention else set()
        )
        wording_valid = (
            not intervention
            and payload is None
            or intervention
            and isinstance(payload, dict)
            and payload.get("action") == action.value
            and payload.get("policy_action") == "answer"
            and payload.get("atomic_claims") == [public["evidence_quote"]]
            and payload.get("source_range_keys") == [expected_key]
            and payload.get("citation_ids") == [f"citation:{expected_key}"]
            and payload.get("content") in allowed_contents
        )
        utility = float(gold["action_utilities"][action.value])
        maximum = max(float(value) for value in gold["action_utilities"].values())
        scored.append(
            {
                **response,
                "event_action_valid": action in eligible,
                "boundary_action_valid": (not boundary) or not intervention,
                "preferred_action_agreement": action.value == gold["expected_action"],
                "policy_utility": utility,
                "policy_regret": maximum - utility,
                "near_optimal_within_0_05": maximum - utility <= 0.05 + 1e-12,
                "intervention": intervention,
                "guard": public["guard"],
                "wording_valid": wording_valid,
                "scope_valid": response["trace"]["course_id"]
                == "synthetic-autonomy-course",
            }
        )
    by_allocation = {
        allocation_id: sorted(
            [row for row in scored if row["allocation_id"] == allocation_id],
            key=lambda row: row["case_id"],
        )
        for allocation_id in ALLOCATION_IDS
    }
    aggregates: dict[str, Any] = {}
    allocation_gates: dict[str, dict[str, bool]] = {}
    for allocation_id, rows in by_allocation.items():
        interventions = [row for row in rows if row["intervention"]]
        wordings = [row["response"]["content"] for row in interventions]
        planner_model = str(rows[0]["planner_model"])
        generator_model = str(rows[0]["generator_model"])
        planner_role = role_metrics[f"planner:{planner_model}"]
        generator_role = role_metrics[
            f"generator:{allocation_id}:{generator_model}"
        ]
        regrets = sorted(float(row["policy_regret"]) for row in rows)
        aggregates[allocation_id] = {
            "case_count": len(rows),
            "planner_model": planner_model,
            "generator_model": generator_model,
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
            "mean_policy_regret": sum(row["policy_regret"] for row in rows)
            / len(rows),
            "p95_policy_regret": regrets[max(0, int(0.95 * len(regrets)) - 1)],
            "near_optimal_within_0_05": sum(
                row["near_optimal_within_0_05"] for row in rows
            )
            / len(rows),
            "valid_grounded_wording": sum(row["wording_valid"] for row in rows)
            / len(rows),
            "planner_provider_completion": planner_role["completion_rate"],
            "generator_provider_completion": generator_role["completion_rate"],
            "estimated_p95_provider_latency_ms": (
                planner_role["p95_latency_ms"] + generator_role["p95_latency_ms"]
            ),
            "estimated_provider_cost_usd": (
                planner_role["cost_usd"] / 2 + generator_role["cost_usd"] / 2
            ),
        }
        allocation_gates[allocation_id] = {
            "all_300_cells_durable": len(rows) == 300,
            "event_action_validity_is_1": all(row["event_action_valid"] for row in rows),
            "boundary_action_accuracy_is_1": all(
                row["boundary_action_valid"] for row in rows
            ),
            "grounded_wording_validity_is_1": all(row["wording_valid"] for row in rows),
            "scope_validity_is_1": all(row["scope_valid"] for row in rows),
            "zero_duplicate_intervention_wording": len(wordings) == len(set(wordings)),
            "planner_provider_completion_at_least_0_995": planner_role[
                "completion_rate"
            ]
            >= 0.995,
            "generator_provider_completion_at_least_0_995": generator_role[
                "completion_rate"
            ]
            >= 0.995,
            "provider_failure_safe_fallback": all(row["wording_valid"] for row in rows),
        }
    global_gates = {
        "all_1200_cells_durable": len(scored) == 1200,
        "zero_duplicate_cells": len(
            {(row["allocation_id"], row["case_id"]) for row in scored}
        )
        == 1200,
        "generator_factor_cannot_change_action": all(
            by_allocation["e1"][index]["selected_action"]
            == by_allocation["e3"][index]["selected_action"]
            and by_allocation["e2"][index]["selected_action"]
            == by_allocation["e4"][index]["selected_action"]
            for index in range(300)
        ),
    }
    planner_effect = _factor_effect(
        by_allocation,
        candidate_allocations=("e2", "e4"),
        control_allocations=("e1", "e3"),
        field="policy_utility",
        seed="engine-006-terra-vs-luna-planner-utility",
        eligible_only=True,
    )
    generator_effect = _factor_effect(
        by_allocation,
        candidate_allocations=("e3", "e4"),
        control_allocations=("e1", "e2"),
        field="generator_provider_success",
        seed="engine-006-mini-vs-luna-generator-completion",
        eligible_only=True,
        interventions_only=True,
    )
    preferred_planner = (
        "gpt-5.6-terra"
        if planner_effect["ci95"][0] > 0
        else "gpt-5.6-luna"
    )
    preferred_generator = (
        "gpt-5.4-mini-2026-03-17"
        if generator_effect["ci95"][0] > 0
        else "gpt-5.6-luna"
    )
    preferred = next(
        allocation_id
        for allocation_id, metrics in aggregates.items()
        if metrics["planner_model"] == preferred_planner
        and metrics["generator_model"] == preferred_generator
    )
    eligible_allocations = [
        allocation_id
        for allocation_id in ALLOCATION_IDS
        if all(allocation_gates[allocation_id].values())
    ]
    if not all(global_gates.values()):
        selected = None
    elif preferred in eligible_allocations:
        selected = preferred
    elif eligible_allocations:
        selected = sorted(
            eligible_allocations,
            key=lambda allocation_id: (
                -aggregates[allocation_id]["mean_policy_utility"],
                -aggregates[allocation_id]["valid_grounded_wording"],
                aggregates[allocation_id]["estimated_p95_provider_latency_ms"],
                aggregates[allocation_id]["estimated_provider_cost_usd"],
            ),
        )[0]
    else:
        selected = None
    passed = all(global_gates.values()) and selected is not None
    return {
        "status": "completed-keep" if passed else "completed-refine",
        "decision": {
            "outcome": "keep" if passed else "refine",
            "selected_allocation_id": selected,
            "selected_planner_model": (
                aggregates[selected]["planner_model"] if selected else None
            ),
            "selected_generator_model": (
                aggregates[selected]["generator_model"] if selected else None
            ),
            "rationale": (
                f"Select {selected.upper()} for whole-system confirmation under the preregistered factorial rule."
                if selected
                else "No allocation preserved every hard gate; stop before whole-system confirmation."
            ),
        },
        "case_count": 300,
        "allocation_cell_count": 1200,
        "aggregate": aggregates,
        "factorial_effects": {
            "terra_minus_luna_planner_policy_utility": planner_effect,
            "mini_minus_luna_provider_origin_valid_strategy": generator_effect,
        },
        "global_hard_gates": global_gates,
        "allocation_hard_gates": allocation_gates,
        "provider_roles": role_metrics,
        "provider": provider_snapshot,
    }


def _summary(result: dict[str, Any]) -> str:
    lines = [
        f"# {result['run_id']}",
        "",
        f"- **Status:** `{result['status']}`",
        f"- **Decision:** {result['decision']['rationale']}",
        f"- **Cases:** {result['case_count']} contexts / {result['allocation_cell_count']} cells.",
        f"- **Provider:** {result['provider']['provider_calls']} calls, USD {result['provider']['reported_cost_usd']:.6f}.",
        "",
        "## Results",
        "",
        "| Allocation | Planner | Generator | Preferred action* | Utility | Valid wording | Est. p95 latency |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for allocation_id, metrics in result["aggregate"].items():
        lines.append(
            f"| `{allocation_id}` | `{metrics['planner_model']}` | "
            f"`{metrics['generator_model']}` | "
            f"{metrics['preferred_action_agreement']:.1%} | "
            f"{metrics['mean_policy_utility']:.4f} | "
            f"{metrics['valid_grounded_wording']:.1%} | "
            f"{metrics['estimated_p95_provider_latency_ms']:.0f} ms |"
        )
    lines.extend(
        [
            "",
            "*Preferred-action agreement is diagnostic; deterministic authority and source-lineage checks are authoritative.*",
            "",
            "This factorial comparison selects an engine allocation for whole-system confirmation. It does not establish real student learning, professor fidelity, or release readiness.",
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
    allocations = _allocation_map(instrument)
    bindings = instrument["provider_bindings"]
    provider_ledger = ProviderCallLedgerV1(
        PROVIDER_LEDGER,
        run_binding=_binding(instrument),
        maximum_calls=instrument["execution"]["maximum_provider_calls"],
        maximum_cost_usd=instrument["execution"]["emergency_cost_stop_usd"],
        maximum_transport_retries_total=0,
        resume=resume,
    )
    response_ledger = _ResponseLedger(RESPONSE_LEDGER, binding=_binding(instrument), resume=resume)
    transports = {
        model: DirectProviderJsonTransport(binding)
        for model, binding in bindings.items()
    }
    planner_values: dict[str, dict[str, HierarchicalPlanningProposalV1 | None]] = {}
    planner_failures: dict[str, set[str]] = {}
    generator_values: dict[str, dict[str, GroundedTutorResponseV2 | None]] = {}
    generator_failures: dict[str, set[str]] = {}
    try:
        for model in ("gpt-5.6-luna", "gpt-5.6-terra"):
            await _planner_canary(transports[model], provider_ledger, eligible_rows[0], model)
        for model in ("gpt-5.6-luna", "gpt-5.4-mini-2026-03-17"):
            await _generator_canary(transports[model], provider_ledger, eligible_rows[0], model)
        for model in ("gpt-5.6-luna", "gpt-5.6-terra"):
            values, failures = await _call_planners(
                model=model,
                transport=transports[model],
                ledger=provider_ledger,
                rows=eligible_rows,
                concurrency=int(instrument["execution"]["concurrency"]),
            )
            planner_values[model] = values
            planner_failures[model] = failures
        for allocation_id in ALLOCATION_IDS:
            allocation = allocations[allocation_id]
            actions = await _selected_actions(
                eligible_rows,
                allocation,
                planner_values[allocation["planner_model"]],
            )
            values, failures = await _call_generators(
                allocation=allocation,
                transport=transports[allocation["generator_model"]],
                ledger=provider_ledger,
                rows=eligible_rows,
                actions=actions,
                concurrency=int(instrument["execution"]["concurrency"]),
            )
            generator_values[allocation_id] = values
            generator_failures[allocation_id] = failures
        await _run_graphs(
            public_rows=public_rows,
            allocations=allocations,
            planner_values=planner_values,
            generator_values=generator_values,
            planner_failures=planner_failures,
            generator_failures=generator_failures,
            response_ledger=response_ledger,
        )
        responses = response_ledger.rows()
        if len(responses) != 1200:
            raise ArchitectureDevelopmentError("engine responses incomplete before gold opening")
        gold = _load_bound_package(instrument["dataset"], gold=True)
        result = _score(
            responses=responses,
            public_rows=public_rows,
            gold_rows=list(gold["rows"]),
            role_metrics=_provider_roles(PROVIDER_LEDGER),
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
                "hidden_gold_sha256": instrument["dataset"][
                    "hidden_gold_file_sha256"
                ],
                "limitations": [
                    "Synthetic scenario utility does not establish real learning improvement.",
                    "Structured wording tests contract adherence and safe lineage, not professor fidelity.",
                    "Luna and Terra are mutable aliases; exact returned identity was required throughout execution.",
                    "The selected allocation still requires fresh whole-system factual and autonomy confirmation before release.",
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
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
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
