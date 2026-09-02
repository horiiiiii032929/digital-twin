#!/usr/bin/env python3
"""Run the first paired A/B/C/C+V development fold through the real graph."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sqlite3
import subprocess
from typing import Any

from dotenv import load_dotenv

from scripts.build_successor_architecture_development_fold_001 import canonical_hash
from src.digital_twin.evaluation.hidden_state_metrics import (
    brier_score,
    expected_calibration_error,
    paired_bootstrap_difference,
)
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
    ProviderJsonError,
)
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)
from src.digital_twin.student.autonomy_eligibility import event_scoped_eligible_actions
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
    AutonomousGoalV1,
    PedagogicalPolicyV2,
    ProactiveOpportunityV1,
)
from src.digital_twin.student.autonomy_runtime import (
    GRAPH_VERSION,
    AutonomousJobInput,
    GovernedAutonomousTutoringGraph,
)
from src.digital_twin.student.migrations import apply_migrations
from src.digital_twin.student.planning_architectures import (
    AutonomyArchitectureId,
    HierarchicalPlanningProposalV1,
    PlannerVerificationV1,
    PlanningStateCardV1,
    SwitchableAutonomyPlanner,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILE_SHA = "b" * 64
NOW = datetime(2026, 9, 2, 14, 30, tzinfo=UTC)
ALL_ACTIONS = [
    action for action in AutonomousActionKind if action != AutonomousActionKind.NO_ACTION
]


class ArchitectureDevelopmentError(RuntimeError):
    """A binding, transport, or execution invariant failed."""


def _initialize_graph_database(path: Path) -> None:
    """Create an isolated graph database through the product migration path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        apply_migrations(connection)
        required_tables = {
            "autonomous_model_calls_v2",
            "autonomous_opportunities",
            "schema_migrations",
        }
        observed_tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    missing = sorted(required_tables - observed_tables)
    if missing:
        raise ArchitectureDevelopmentError(
            "isolated graph database is missing product migrations: "
            + ", ".join(missing)
        )


@dataclass(frozen=True)
class DevelopmentRunContext:
    instrument_id: str
    instrument_path: Path
    output_root: Path
    provider_ledger: Path
    response_ledger: Path
    graph_ledger: Path
    result_path: Path
    summary_path: Path


def _run_context(attempt: str) -> DevelopmentRunContext:
    if attempt == "001":
        instrument_id = "successor-architecture-development-fold-001"
        instrument_name = "successor_architecture_development_fold_001.json"
    elif attempt == "002":
        instrument_id = "successor-architecture-development-fold-001-attempt-002"
        instrument_name = (
            "successor_architecture_development_fold_001_attempt_002.json"
        )
    elif attempt == "fold-002":
        instrument_id = "successor-architecture-development-fold-002-single-case-001"
        instrument_name = (
            "successor_architecture_development_fold_002_single_case_001.json"
        )
    elif attempt == "fold-002-corrective":
        instrument_id = (
            "successor-architecture-development-fold-002-single-case-attempt-002"
        )
        instrument_name = (
            "successor_architecture_development_fold_002_single_case_attempt_002.json"
        )
    elif attempt == "fold-003":
        instrument_id = "successor-architecture-development-fold-003-single-case-001"
        instrument_name = (
            "successor_architecture_development_fold_003_single_case_001.json"
        )
    else:
        raise ArchitectureDevelopmentError(f"unknown development attempt: {attempt}")
    output_root = ROOT / f"reports/generated/{instrument_id}"
    return DevelopmentRunContext(
        instrument_id=instrument_id,
        instrument_path=(
            ROOT / "research/05_evaluation/instruments" / instrument_name
        ),
        output_root=output_root,
        provider_ledger=output_root / "provider.sqlite3",
        response_ledger=output_root / "responses.sqlite3",
        graph_ledger=output_root / "graph-checkpoints.sqlite3",
        result_path=(
            ROOT / "research/05_evaluation/records" / f"{instrument_id}.json"
        ),
        summary_path=(
            ROOT / "research/05_evaluation" / f"{instrument_id}-results.md"
        ),
    )


DEFAULT_CONTEXT = _run_context("001")


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ArchitectureDevelopmentError(f"JSON root is not an object: {path}")
    return value


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _load_bound_package(binding: dict[str, Any], *, gold: bool) -> dict[str, Any]:
    prefix = "hidden_gold" if gold else "public"
    path = ROOT / str(binding[f"{prefix}_path"])
    if _file_sha256(path) != binding[f"{prefix}_file_sha256"]:
        raise ArchitectureDevelopmentError(f"{prefix} file hash drifted")
    value = _load_json(path)
    if value.get("content_sha256") != binding[f"{prefix}_content_sha256"]:
        raise ArchitectureDevelopmentError(f"{prefix} content binding drifted")
    unhashed = {key: item for key, item in value.items() if key != "content_sha256"}
    if canonical_hash(unhashed) != value["content_sha256"]:
        raise ArchitectureDevelopmentError(f"{prefix} package content drifted")
    return value


def _schema_string(nullable: bool = False) -> dict[str, Any]:
    return {"type": ["string", "null"] if nullable else "string"}


def _proposal_schema(case_id: str | None = None) -> dict[str, Any]:
    action = {"type": "string", "enum": [item.value for item in AutonomousActionKind]}
    step = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "action": action,
            "expected_observation": _schema_string(),
            "stop_or_replan_predicate": _schema_string(),
        },
        "required": ["action", "expected_observation", "stop_or_replan_predicate"],
    }
    row = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "case_id": _schema_string(),
            "selected_action": action,
            "reason_code": _schema_string(),
            "expected_learner_action": _schema_string(nullable=True),
            "outcome_observation": _schema_string(nullable=True),
            "stop_condition": _schema_string(),
            "replan_condition": _schema_string(nullable=True),
            "episode_steps": {"type": "array", "items": step, "maxItems": 3},
        },
        "required": [
            "case_id",
            "selected_action",
            "reason_code",
            "expected_learner_action",
            "outcome_observation",
            "stop_condition",
            "replan_condition",
            "episode_steps",
        ],
    }
    if case_id is not None:
        row["properties"]["case_id"] = {
            "type": "string",
            "enum": [case_id],
        }
        return row
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"rows": {"type": "array", "items": row}},
        "required": ["rows"],
    }


def _verifier_schema(case_id: str | None = None) -> dict[str, Any]:
    row = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "case_id": _schema_string(),
            "accept": {"type": "boolean"},
            "reason_code": _schema_string(),
        },
        "required": ["case_id", "accept", "reason_code"],
    }
    if case_id is not None:
        row["properties"]["case_id"] = {
            "type": "string",
            "enum": [case_id],
        }
        return row
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"rows": {"type": "array", "items": row}},
        "required": ["rows"],
    }


def _chunks(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[index : index + size] for index in range(0, len(rows), size)]


def _validate_id_set(rows: list[dict[str, Any]], expected: list[str]) -> None:
    observed = [str(row.get("case_id", "")) for row in rows]
    if len(observed) != len(set(observed)):
        raise ArchitectureDevelopmentError("provider returned duplicate case IDs")
    if set(observed) != set(expected):
        raise ArchitectureDevelopmentError("provider returned missing or unknown case IDs")


def _eligible_public_rows(public_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in public_rows if row["guard"] == "eligible"]


def _planner_prompt(rows: list[dict[str, Any]]) -> str:
    payload = []
    for row in rows:
        event = AutonomousEventKind(row["event_kind"])
        eligible = event_scoped_eligible_actions(event, ALL_ACTIONS)
        payload.append(
            {
                "case_id": row["case_id"],
                "event_kind": event.value,
                "state_card": row["state_card"],
                "objective": row["objective"],
                "eligible_actions": [item.value for item in eligible],
                "evidence_ready": row["evidence_ready"],
                "maximum_episode_steps": 3,
            }
        )
    return json.dumps(
        {
            "instruction": (
                "For each case choose one pedagogically appropriate action from that "
                "case's eligible_actions. Use only observable state. Do not change scope, "
                "policy, evidence, consent, learner state, or delivery. Return concise "
                "structured reasons, not hidden reasoning. Preserve every case_id exactly."
            ),
            "cases": payload,
        },
        sort_keys=True,
    )


def _verifier_prompt(rows: list[dict[str, Any]]) -> str:
    return json.dumps(
        {
            "instruction": (
                "For each case reject only when the selected move is pedagogically "
                "inappropriate for the observable state. Never amend an action and "
                "preserve every case_id exactly."
            ),
            "cases": rows,
        },
        sort_keys=True,
    )


def _proposal_from_row(row: dict[str, Any]) -> HierarchicalPlanningProposalV1:
    payload = {key: value for key, value in row.items() if key != "case_id"}
    return HierarchicalPlanningProposalV1.model_validate(payload)


def _job(row: dict[str, Any]) -> AutonomousJobInput:
    case_id = str(row["case_id"])
    state = PlanningStateCardV1.model_validate(row["state_card"])
    evidence_ready = bool(row["evidence_ready"])
    goal = AutonomousGoalV1(
        goal_id=f"goal-{case_id}",
        student_id=f"learner-{case_id}",
        course_id="synthetic-autonomy-course",
        release_id="release-a",
        policy_version=1,
        profile_id="profile-a",
        profile_sha256=PROFILE_SHA,
        graph_version=GRAPH_VERSION,
        planner_model="gpt-5.6-luna",
        generator_model="deterministic/autonomy-wording-v1",
        approved_course_objective=row["objective"],
        learner_subgoal="Choose one evidence-grounded next learning move.",
        success_condition="Produce one assessed learner response.",
        attempt_limit=3,
        attempt_count=max(0, 3 - state.goal_attempts_remaining),
        expires_at=(NOW + timedelta(days=7)).isoformat(),
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
    )
    opportunity = ProactiveOpportunityV1(
        opportunity_id=f"opportunity-{case_id}",
        idempotency_key=f"idempotency-{case_id}",
        event_kind=AutonomousEventKind(row["event_kind"]),
        student_id=goal.student_id,
        course_id=goal.course_id,
        release_id=goal.release_id,
        policy_version=1,
        profile_id="profile-a",
        profile_sha256=PROFILE_SHA,
        graph_version=GRAPH_VERSION,
        planner_model="gpt-5.6-luna",
        generator_model="deterministic/autonomy-wording-v1",
        goal_id=goal.goal_id,
        supporting_observation_ids=[
            f"observation-{case_id}-{index}"
            for index in range(state.assessed_evidence_count)
        ],
        concept_id=state.concept_id,
        source_chunk_id=f"chunk-{case_id}" if evidence_ready else None,
        source_chunk_ids=[f"chunk-{case_id}"] if evidence_ready else [],
        earliest_action_at=(NOW - timedelta(minutes=1)).isoformat(),
        latest_action_at=(NOW + timedelta(hours=1)).isoformat(),
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
    )
    policy = PedagogicalPolicyV2(
        course_id=goal.course_id,
        version=1,
        approved_by="synthetic-professor",
        approved_profile_id="profile-a",
        approved_profile_sha256=PROFILE_SHA,
        approved_course_objectives=[row["objective"]],
        autonomy_enabled=True,
        allowed_actions=ALL_ACTIONS,
        updated_at=NOW.isoformat(),
    )
    return AutonomousJobInput(
        opportunity=opportunity,
        goal=goal,
        policy=policy,
        professor_id="synthetic-professor",
        current_release_id=("release-a" if row["current_release_matches"] else "release-b"),
        current_profile_id="profile-a",
        current_profile_sha256=PROFILE_SHA,
        membership_active=bool(row["membership_active"]),
        consent_active=bool(row["consent_active"]),
        within_quiet_hours=bool(row["within_quiet_hours"]),
        recent_message_count=int(row["recent_message_count"]),
        same_concept_cooldown_active=bool(row["same_concept_cooldown_active"]),
        evidence_keys=[f"source-range-{case_id}"] if evidence_ready else [],
        evidence_chunk_ids=[f"chunk-{case_id}"] if evidence_ready else [],
        evidence_decision_reason="fresh-synthetic-authoritative-evidence",
        evidence_complete=evidence_ready,
        evidence_unique=evidence_ready,
        evidence_current=evidence_ready,
        evidence_authorized=evidence_ready,
        now=NOW.isoformat(),
    )


class _ProposalMap:
    model_id = "gpt-5.6-luna"

    def __init__(
        self, values: dict[str, HierarchicalPlanningProposalV1 | None]
    ) -> None:
        self.values = values

    async def propose(self, **kwargs):
        case_id = _case_id_from_opportunity(
            kwargs["job"].opportunity.opportunity_id
        )
        if case_id not in self.values or self.values[case_id] is None:
            raise ValueError("no valid persisted proposal for eligible case")
        return self.values[case_id]


class _VerifierMap:
    model_id = "gpt-5.6-luna"

    def __init__(self, values: dict[str, PlannerVerificationV1 | None]) -> None:
        self.values = values

    async def verify(self, **kwargs):
        case_id = _case_id_from_opportunity(
            kwargs["job"].opportunity.opportunity_id
        )
        if case_id not in self.values or self.values[case_id] is None:
            raise ValueError("no valid persisted verifier decision for selected case")
        return self.values[case_id]


def _case_id_from_opportunity(opportunity_id: str) -> str:
    return opportunity_id.removeprefix("opportunity-").split(
        "--architecture-", 1
    )[0]


def _architecture_scoped_job(
    row: dict[str, Any], architecture: AutonomyArchitectureId
) -> AutonomousJobInput:
    job = _job(row)
    suffix = f"--architecture-{architecture.value}"
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


class _ResponseLedger:
    def __init__(self, path: Path, *, binding: dict[str, Any], resume: bool) -> None:
        if resume and not path.is_file():
            raise ArchitectureDevelopmentError("response resume ledger is missing")
        if not resume and path.exists():
            raise ArchitectureDevelopmentError("exclusive response ledger exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)"
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS responses(
                   architecture_id TEXT NOT NULL,
                   case_id TEXT NOT NULL,
                   payload_json TEXT NOT NULL,
                   PRIMARY KEY(architecture_id,case_id)
               )"""
        )
        expected = canonical_hash(binding)
        current = self.connection.execute(
            "SELECT value FROM metadata WHERE key='binding_sha256'"
        ).fetchone()
        if resume:
            if current is None or current[0] != expected:
                raise ArchitectureDevelopmentError("response resume binding drifted")
        else:
            self.connection.execute(
                "INSERT INTO metadata(key,value) VALUES('binding_sha256',?)", (expected,)
            )
            self.connection.execute(
                "INSERT INTO metadata(key,value) VALUES('status','running')"
            )
            self.connection.commit()

    def has(self, architecture_id: str, case_id: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM responses WHERE architecture_id=? AND case_id=?",
            (architecture_id, case_id),
        ).fetchone() is not None

    def record(self, architecture_id: str, case_id: str, payload: dict[str, Any]) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO responses(architecture_id,case_id,payload_json) VALUES(?,?,?)",
                (architecture_id, case_id, json.dumps(payload, sort_keys=True)),
            )

    def rows(self) -> list[dict[str, Any]]:
        return [
            json.loads(row[0])
            for row in self.connection.execute(
                "SELECT payload_json FROM responses ORDER BY architecture_id,case_id"
            )
        ]

    def complete(self) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE metadata SET value='completed' WHERE key='status'"
            )

    def close(self) -> None:
        self.connection.close()


def _binding(
    instrument: dict[str, Any], context: DevelopmentRunContext
) -> dict[str, Any]:
    return {
        "instrument_sha256": _file_sha256(context.instrument_path),
        "public_sha256": instrument["dataset"]["public_file_sha256"],
        "gold_sha256": instrument["dataset"]["hidden_gold_file_sha256"],
        "code_revision": _git("rev-parse", "HEAD"),
        "engine": instrument["fixed_engine"],
    }


def validate(context: DevelopmentRunContext = DEFAULT_CONTEXT) -> dict[str, Any]:
    instrument = _load_json(context.instrument_path)
    if instrument["instrument_id"] != context.instrument_id:
        raise ArchitectureDevelopmentError("instrument identity drifted")
    public = _load_bound_package(instrument["dataset"], gold=False)
    public_ids = [row["case_id"] for row in public["rows"]]
    if len(public_ids) != 150 or len(public_ids) != len(set(public_ids)):
        raise ArchitectureDevelopmentError("public fold identity drifted")
    if instrument["dataset"]["architecture_cell_count"] != 600:
        raise ArchitectureDevelopmentError("architecture cell count drifted")
    if instrument["fixed_engine"]["provider_model"] != "gpt-5.6-luna":
        raise ArchitectureDevelopmentError("fixed engine drifted")
    contract_mode = instrument["execution"].get("contract_mode", "four-case-batch")
    expected_call_ceiling = 242 if contract_mode == "single-case-object" else 62
    if instrument["execution"]["maximum_provider_calls"] != expected_call_ceiling:
        raise ArchitectureDevelopmentError("call ceiling drifted")
    if instrument["analysis"]["learner_state_is_shared_not_a_selection_dimension"] is not True:
        raise ArchitectureDevelopmentError("shared learner-state diagnostic drifted")
    return {
        "instrument_id": instrument["instrument_id"],
        "status": "passed",
        "instrument_status": instrument["status"],
        "case_count": len(public_ids),
        "architecture_cell_count": 600,
        "provider_execution_authorized": instrument["execution"][
            "provider_execution_authorized"
        ],
        "paid_execution_authorized": instrument["execution"][
            "paid_execution_authorized"
        ],
        "provider_calls": 0,
    }


def preflight(
    *, resume: bool, context: DevelopmentRunContext = DEFAULT_CONTEXT
) -> dict[str, Any]:
    result = validate(context)
    instrument = _load_json(context.instrument_path)
    blockers: list[str] = []
    authority = instrument["execution"]
    if not authority["provider_execution_authorized"]:
        blockers.append("provider-execution-not-authorized")
    if not authority["paid_execution_authorized"]:
        blockers.append("paid-execution-not-authorized")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("OPENAI_API_KEY-missing")
    if _git("status", "--porcelain"):
        blockers.append("working-tree-dirty")
    verified = datetime.fromisoformat(instrument["provider_freshness"]["verified_at"])
    age_hours = (datetime.now(UTC) - verified.astimezone(UTC)).total_seconds() / 3600
    if age_hours > instrument["provider_freshness"]["maximum_age_hours"]:
        blockers.append("provider-metadata-stale")
    for path in (
        context.provider_ledger,
        context.response_ledger,
        context.graph_ledger,
    ):
        if resume and not path.exists():
            blockers.append(f"resume-artifact-missing:{path.name}")
        if not resume and path.exists():
            blockers.append(f"exclusive-output-exists:{path.name}")
    if not resume:
        for path in (context.result_path, context.summary_path):
            if path.exists():
                blockers.append(f"exclusive-output-exists:{path.name}")
    return {
        **result,
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "resume": resume,
        "provider_calls": 0,
    }


async def _call_planner_batches(
    *,
    transport: DirectProviderJsonTransport,
    ledger: ProviderCallLedgerV1,
    public_rows: list[dict[str, Any]],
) -> dict[str, HierarchicalPlanningProposalV1]:
    result: dict[str, HierarchicalPlanningProposalV1] = {}
    for batch_index, batch in enumerate(_chunks(public_rows, 4), start=1):
        response = await transport.call_with_ledger(
            ledger=ledger,
            request_key=f"planner-{batch_index:03d}",
            provider_role="shared-fixed-engine-planner",
            system=(
                "Return only bounded pedagogical proposals for the supplied synthetic "
                "cases. Do not include chain-of-thought or personal data."
            ),
            prompt=_planner_prompt(batch),
            task="successor_architecture_planner_batch",
            schema=_proposal_schema(),
        )
        rows = response.content.get("rows")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ArchitectureDevelopmentError("planner batch rows are malformed")
        expected = [row["case_id"] for row in batch]
        _validate_id_set(rows, expected)
        by_id = {str(row["case_id"]): row for row in rows}
        for source in batch:
            case_id = source["case_id"]
            proposal = _proposal_from_row(by_id[case_id])
            eligible = event_scoped_eligible_actions(
                AutonomousEventKind(source["event_kind"]), ALL_ACTIONS
            )
            if proposal.selected_action not in eligible or any(
                step.action not in eligible for step in proposal.episode_steps
            ):
                raise ArchitectureDevelopmentError(
                    f"planner left deterministic envelope: {case_id}"
                )
            result[case_id] = proposal
    return result


def _provider_failure_is_run_invalid(error: Exception) -> bool:
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "identity drifted",
            "cost limit",
            "call limit",
            "binding drifted",
            "ledger is not running",
        )
    )


async def _call_planner_single_cases(
    *,
    transport: DirectProviderJsonTransport,
    ledger: ProviderCallLedgerV1,
    public_rows: list[dict[str, Any]],
    concurrency: int,
) -> tuple[dict[str, HierarchicalPlanningProposalV1 | None], list[str]]:
    result: dict[str, HierarchicalPlanningProposalV1 | None] = {}
    failures: list[str] = []

    async def call_one(source: dict[str, Any]) -> tuple[str, HierarchicalPlanningProposalV1 | None, str | None]:
        case_id = str(source["case_id"])
        try:
            response = await transport.call_with_ledger(
                ledger=ledger,
                request_key=f"planner-{case_id}",
                provider_role="shared-fixed-engine-planner",
                system=(
                    "Return one bounded pedagogical proposal for the supplied "
                    "synthetic case. Do not include chain-of-thought or personal data."
                ),
                prompt=_planner_prompt([source]),
                task="successor_architecture_planner_single_case",
                schema=_proposal_schema(case_id),
                quarantine_failures=True,
            )
            proposal = _proposal_from_row(response.content)
            eligible = event_scoped_eligible_actions(
                AutonomousEventKind(source["event_kind"]), ALL_ACTIONS
            )
            if proposal.selected_action not in eligible or any(
                step.action not in eligible for step in proposal.episode_steps
            ):
                return case_id, None, "action-envelope-violation"
            return case_id, proposal, None
        except ProviderJsonError as error:
            if _provider_failure_is_run_invalid(error):
                raise
            return case_id, None, type(error).__name__
        except ValueError as error:
            return case_id, None, type(error).__name__

    for batch in _chunks(public_rows, concurrency):
        completed = await asyncio.gather(*(call_one(source) for source in batch))
        for case_id, proposal, failure in completed:
            result[case_id] = proposal
            if failure is not None:
                failures.append(case_id)
    return result, failures


async def _selected_c_rows(
    public_rows: list[dict[str, Any]],
    proposals: dict[str, HierarchicalPlanningProposalV1 | None],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    provider = _ProposalMap(proposals)
    for row in public_rows:
        case_id = row["case_id"]
        state = PlanningStateCardV1.model_validate(row["state_card"])
        planner = SwitchableAutonomyPlanner(
            architecture_id=AutonomyArchitectureId.HIERARCHICAL_MODEL_BASED_C,
            proposal_provider=provider,
            state_card_resolver=lambda _job, state=state: state,
        )
        proposal, _trace = await planner.plan_with_trace(_job(row))
        if proposal.action != AutonomousActionKind.NO_ACTION:
            rows.append(
                {
                    "case_id": case_id,
                    "event_kind": row["event_kind"],
                    "state_card": row["state_card"],
                    "eligible_actions": [
                        item.value
                        for item in event_scoped_eligible_actions(
                            AutonomousEventKind(row["event_kind"]), ALL_ACTIONS
                        )
                    ],
                    "proposal": proposal.model_dump(mode="json"),
                }
            )
    return rows


async def _call_verifier_batches(
    *,
    transport: DirectProviderJsonTransport,
    ledger: ProviderCallLedgerV1,
    selected_rows: list[dict[str, Any]],
) -> dict[str, PlannerVerificationV1]:
    result: dict[str, PlannerVerificationV1] = {}
    for batch_index, batch in enumerate(_chunks(selected_rows, 4), start=1):
        response = await transport.call_with_ledger(
            ledger=ledger,
            request_key=f"verifier-{batch_index:03d}",
            provider_role="reject-only-verifier",
            system=(
                "Return only reject-only decisions for the supplied synthetic tutoring "
                "moves. Do not propose replacements or include hidden reasoning."
            ),
            prompt=_verifier_prompt(batch),
            task="successor_architecture_verifier_batch",
            schema=_verifier_schema(),
        )
        rows = response.content.get("rows")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ArchitectureDevelopmentError("verifier batch rows are malformed")
        expected = [row["case_id"] for row in batch]
        _validate_id_set(rows, expected)
        by_id = {str(row["case_id"]): row for row in rows}
        for case_id in expected:
            result[case_id] = PlannerVerificationV1.model_validate(
                {key: value for key, value in by_id[case_id].items() if key != "case_id"}
            )
    return result


async def _call_verifier_single_cases(
    *,
    transport: DirectProviderJsonTransport,
    ledger: ProviderCallLedgerV1,
    selected_rows: list[dict[str, Any]],
    concurrency: int,
) -> tuple[dict[str, PlannerVerificationV1 | None], list[str]]:
    result: dict[str, PlannerVerificationV1 | None] = {}
    failures: list[str] = []

    async def call_one(source: dict[str, Any]) -> tuple[str, PlannerVerificationV1 | None, str | None]:
        case_id = str(source["case_id"])
        try:
            response = await transport.call_with_ledger(
                ledger=ledger,
                request_key=f"verifier-{case_id}",
                provider_role="reject-only-verifier",
                system=(
                    "Return one reject-only decision for the supplied synthetic "
                    "tutoring move. Do not propose a replacement or hidden reasoning."
                ),
                prompt=_verifier_prompt([source]),
                task="successor_architecture_verifier_single_case",
                schema=_verifier_schema(case_id),
                quarantine_failures=True,
            )
            decision = PlannerVerificationV1.model_validate(
                {
                    key: value
                    for key, value in response.content.items()
                    if key != "case_id"
                }
            )
            return case_id, decision, None
        except ProviderJsonError as error:
            if _provider_failure_is_run_invalid(error):
                raise
            return case_id, None, type(error).__name__
        except ValueError as error:
            return case_id, None, type(error).__name__

    for batch in _chunks(selected_rows, concurrency):
        completed = await asyncio.gather(*(call_one(source) for source in batch))
        for case_id, decision, failure in completed:
            result[case_id] = decision
            if failure is not None:
                failures.append(case_id)
    return result, failures


async def _canaries(
    transport: DirectProviderJsonTransport,
    ledger: ProviderCallLedgerV1,
    row: dict[str, Any],
    *,
    contract_mode: str = "four-case-batch",
) -> None:
    single_case = contract_mode == "single-case-object"
    case_id = str(row["case_id"])
    planner = await transport.call_with_ledger(
        ledger=ledger,
        request_key="canary-planner",
        provider_role="planner-canary",
        system="Return one bounded synthetic pedagogical proposal.",
        prompt=_planner_prompt([row]),
        task="successor_architecture_planner_canary",
        schema=_proposal_schema(case_id if single_case else None),
    )
    if single_case:
        proposal = _proposal_from_row(planner.content)
    else:
        planner_rows = planner.content.get("rows")
        if not isinstance(planner_rows, list):
            raise ArchitectureDevelopmentError("planner canary rows are malformed")
        _validate_id_set(planner_rows, [case_id])
        proposal = _proposal_from_row(planner_rows[0])
    eligible = event_scoped_eligible_actions(
        AutonomousEventKind(row["event_kind"]), ALL_ACTIONS
    )
    if proposal.selected_action not in eligible or any(
        step.action not in eligible for step in proposal.episode_steps
    ):
        raise ArchitectureDevelopmentError("planner canary left deterministic envelope")
    verifier_input = {
        "case_id": case_id,
        "event_kind": row["event_kind"],
        "state_card": row["state_card"],
        "eligible_actions": [
            item.value
            for item in event_scoped_eligible_actions(
                AutonomousEventKind(row["event_kind"]), ALL_ACTIONS
            )
        ],
        "proposal": {
            "action": proposal.selected_action.value,
            "reason_code": proposal.reason_code,
            "expected_learner_action": proposal.expected_learner_action,
            "required_evidence_keys": [],
            "outcome_observation": proposal.outcome_observation,
            "stop_condition": proposal.stop_condition,
            "replan_condition": proposal.replan_condition,
        },
    }
    verifier = await transport.call_with_ledger(
        ledger=ledger,
        request_key="canary-verifier",
        provider_role="verifier-canary",
        system="Return one reject-only synthetic tutoring decision.",
        prompt=_verifier_prompt([verifier_input]),
        task="successor_architecture_verifier_canary",
        schema=_verifier_schema(case_id if single_case else None),
    )
    if single_case:
        verifier_row = verifier.content
    else:
        verifier_rows = verifier.content.get("rows")
        if not isinstance(verifier_rows, list):
            raise ArchitectureDevelopmentError("verifier canary rows are malformed")
        _validate_id_set(verifier_rows, [case_id])
        verifier_row = verifier_rows[0]
    PlannerVerificationV1.model_validate(
        {key: value for key, value in verifier_row.items() if key != "case_id"}
    )


async def _run_graphs(
    *,
    public_rows: list[dict[str, Any]],
    proposals: dict[str, HierarchicalPlanningProposalV1 | None],
    verifications: dict[str, PlannerVerificationV1 | None],
    response_ledger: _ResponseLedger,
    graph_ledger: Path,
) -> None:
    _initialize_graph_database(graph_ledger)
    proposal_provider = _ProposalMap(proposals)
    verifier_provider = _VerifierMap(verifications)
    for architecture in AutonomyArchitectureId:
        for row in public_rows:
            case_id = row["case_id"]
            if response_ledger.has(architecture.value, case_id):
                continue
            state = PlanningStateCardV1.model_validate(row["state_card"])
            if architecture == AutonomyArchitectureId.DETERMINISTIC_WORKFLOW_A:
                planner = SwitchableAutonomyPlanner(architecture_id=architecture)
            else:
                planner = SwitchableAutonomyPlanner(
                    architecture_id=architecture,
                    proposal_provider=proposal_provider,
                    verifier=(
                        verifier_provider
                        if architecture
                        == AutonomyArchitectureId.HIERARCHICAL_WITH_VERIFIER_CV
                        else None
                    ),
                    state_card_resolver=lambda _job, state=state: state,
                )
            graph = GovernedAutonomousTutoringGraph(
                planner=planner,
                checkpoint_database_path=str(graph_ledger),
            )
            result = await graph.run(_architecture_scoped_job(row, architecture))
            response_ledger.record(
                architecture.value,
                case_id,
                {
                    "architecture_id": architecture.value,
                    "case_id": case_id,
                    "selected_action": result.action.kind.value,
                    "response": result.response.model_dump(mode="json")
                    if result.response is not None
                    else None,
                    "trace": result.trace.model_dump(mode="json"),
                },
            )


def _exact_mcnemar(a: list[bool], b: list[bool]) -> dict[str, Any]:
    a_only = sum(left and not right for left, right in zip(a, b, strict=True))
    b_only = sum(right and not left for left, right in zip(a, b, strict=True))
    discordant = a_only + b_only
    if discordant == 0:
        return {"a_only": 0, "b_only": 0, "p_value": 1.0}
    tail = sum(math.comb(discordant, index) for index in range(min(a_only, b_only) + 1))
    p_value = min(1.0, 2 * tail / (2**discordant))
    return {"a_only": a_only, "b_only": b_only, "p_value": p_value}


def _score(
    responses: list[dict[str, Any]],
    public_rows: list[dict[str, Any]],
    gold_rows: list[dict[str, Any]],
    provider_snapshot: dict[str, Any],
    provider_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provider_quality = provider_quality or {
        "planner_case_count": 0,
        "verifier_case_count": 0,
        "planner_failure_case_ids": [],
        "verifier_failure_case_ids": [],
    }
    public_by_id = {row["case_id"]: row for row in public_rows}
    gold_by_id = {row["case_id"]: row for row in gold_rows}
    scored: list[dict[str, Any]] = []
    for response in responses:
        case_id = response["case_id"]
        gold = gold_by_id[case_id]
        selected = response["selected_action"]
        accepted = selected in gold["acceptable_actions"]
        expected_no_action = gold["expected_action"] == AutonomousActionKind.NO_ACTION.value
        intervention = selected != AutonomousActionKind.NO_ACTION.value
        response_payload = response["response"]
        citation_valid = (
            not intervention
            or (
                isinstance(response_payload, dict)
                and response_payload.get("source_range_keys")
                == [f"source-range-{case_id}"]
            )
        )
        scored.append(
            {
                **response,
                "accepted": accepted,
                "policy_utility": float(gold["action_utilities"][selected]),
                "intervention": intervention,
                "unnecessary_intervention": expected_no_action and intervention,
                "citation_valid": citation_valid,
                "scope_valid": response["trace"]["course_id"] == "synthetic-autonomy-course",
            }
        )
    by_architecture: dict[str, list[dict[str, Any]]] = {}
    for row in scored:
        by_architecture.setdefault(row["architecture_id"], []).append(row)
    aggregate: dict[str, Any] = {}
    for architecture_id, rows in sorted(by_architecture.items()):
        interventions = [row for row in rows if row["intervention"]]
        aggregate[architecture_id] = {
            "case_count": len(rows),
            "acceptable_move_accuracy": sum(row["accepted"] for row in rows) / len(rows),
            "mean_policy_utility": sum(row["policy_utility"] for row in rows) / len(rows),
            "proactive_precision": (
                sum(row["accepted"] for row in interventions) / len(interventions)
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
    ordered_ids = [row["case_id"] for row in public_rows]
    comparisons: dict[str, Any] = {}
    for candidate, control in (
        (AutonomyArchitectureId.GOVERNED_SINGLE_PLANNER_B.value, AutonomyArchitectureId.DETERMINISTIC_WORKFLOW_A.value),
        (AutonomyArchitectureId.HIERARCHICAL_MODEL_BASED_C.value, AutonomyArchitectureId.GOVERNED_SINGLE_PLANNER_B.value),
        (AutonomyArchitectureId.HIERARCHICAL_WITH_VERIFIER_CV.value, AutonomyArchitectureId.HIERARCHICAL_MODEL_BASED_C.value),
    ):
        candidate_rows = sorted(by_architecture[candidate], key=lambda row: ordered_ids.index(row["case_id"]))
        control_rows = sorted(by_architecture[control], key=lambda row: ordered_ids.index(row["case_id"]))
        key = f"{candidate}-vs-{control}"
        comparisons[key] = {
            "acceptable_move_mcnemar": _exact_mcnemar(
                [row["accepted"] for row in candidate_rows],
                [row["accepted"] for row in control_rows],
            ),
            "utility_difference": paired_bootstrap_difference(
                candidate_rows,
                control_rows,
                value=lambda row: float(row["policy_utility"]),
                key=lambda row: row["case_id"],
                resamples=2000,
                seed=f"{key}-utility",
            ),
            "precision_difference": paired_bootstrap_difference(
                candidate_rows,
                control_rows,
                value=lambda row: float(row["accepted"]) if row["intervention"] else None,
                key=lambda row: row["case_id"],
                resamples=2000,
                seed=f"{key}-precision",
            ),
            "unnecessary_intervention_reduction": paired_bootstrap_difference(
                control_rows,
                candidate_rows,
                value=lambda row: float(row["unnecessary_intervention"]),
                key=lambda row: row["case_id"],
                resamples=2000,
                seed=f"{key}-unnecessary",
            ),
        }
    predictions = [
        (
            PlanningStateCardV1.model_validate(public_by_id[row["case_id"]]["state_card"]).mastery_probability,
            bool(row["hidden_learner_knows"]),
        )
        for row in gold_rows
    ]
    planner_failures = set(provider_quality["planner_failure_case_ids"])
    verifier_failures = set(provider_quality["verifier_failure_case_ids"])
    model_case_count = int(provider_quality["planner_case_count"]) + int(
        provider_quality["verifier_case_count"]
    )
    model_failure_count = len(planner_failures) + len(verifier_failures)
    provider_completion_rate = (
        (model_case_count - model_failure_count) / model_case_count
        if model_case_count
        else 1.0
    )
    scored_by_cell = {
        (row["architecture_id"], row["case_id"]): row for row in scored
    }
    safe_fallback_cells = [
        scored_by_cell[(architecture.value, case_id)]["selected_action"]
        == AutonomousActionKind.NO_ACTION.value
        for case_id in planner_failures
        for architecture in (
            AutonomyArchitectureId.GOVERNED_SINGLE_PLANNER_B,
            AutonomyArchitectureId.HIERARCHICAL_MODEL_BASED_C,
            AutonomyArchitectureId.HIERARCHICAL_WITH_VERIFIER_CV,
        )
    ] + [
        scored_by_cell[
            (AutonomyArchitectureId.HIERARCHICAL_WITH_VERIFIER_CV.value, case_id)
        ]["selected_action"]
        == AutonomousActionKind.NO_ACTION.value
        for case_id in verifier_failures
    ]
    provider_failure_safe_fallback_rate = (
        sum(safe_fallback_cells) / len(safe_fallback_cells)
        if safe_fallback_cells
        else 1.0
    )
    safety = {
        "zero_unauthorized_or_unsupported_actions": all(
            not row["unnecessary_intervention"] for row in scored
        ),
        "zero_invalid_citations": all(row["citation_valid"] for row in scored),
        "zero_incorrect_scope": all(row["scope_valid"] for row in scored),
        "all_600_cells_durable": len(scored) == 600,
        "zero_duplicate_cells": len(
            {(row["architecture_id"], row["case_id"]) for row in scored}
        )
        == 600,
        "provider_completion_at_least_0_995": provider_completion_rate >= 0.995,
        "provider_failure_safe_fallback_rate_is_1": (
            provider_failure_safe_fallback_rate == 1.0
        ),
        "all_architectures_valid_transition_at_least_0_95": all(
            metrics["acceptable_move_accuracy"] >= 0.95
            for metrics in aggregate.values()
        ),
    }
    ranking = sorted(
        aggregate,
        key=lambda architecture_id: (
            aggregate[architecture_id]["acceptable_move_accuracy"],
            aggregate[architecture_id]["proactive_precision"],
            -aggregate[architecture_id]["unnecessary_intervention_rate"],
        ),
        reverse=True,
    )
    return {
        "status": "completed-go-deeper" if all(safety.values()) else "completed-refine",
        "decision": {
            "outcome": "go-deeper" if all(safety.values()) else "refine",
            "provisional_ranking": ranking,
            "selected_architecture_id": None,
            "rationale": (
                "This fresh fold is development evidence. It may rank candidates but cannot "
                "select the final architecture before the remaining fresh folds and "
                "cross-engine comparison."
            ),
        },
        "case_count": 150,
        "architecture_cell_count": 600,
        "aggregate": aggregate,
        "paired_comparisons": comparisons,
        "shared_learner_state_diagnostic": {
            "brier_score": brier_score(predictions),
            "expected_calibration_error": expected_calibration_error(predictions),
            "selection_dimension": False,
        },
        "provider_quality": {
            **provider_quality,
            "model_case_count": model_case_count,
            "model_failure_count": model_failure_count,
            "provider_completion_rate": provider_completion_rate,
            "provider_failure_safe_fallback_rate": (
                provider_failure_safe_fallback_rate
            ),
        },
        "hard_gates": safety,
        "provider": provider_snapshot,
    }


def _finalize_ledgers(
    result: dict[str, Any],
    *,
    response_ledger: _ResponseLedger,
    provider_ledger: ProviderCallLedgerV1,
) -> None:
    """Close both ledgers before their terminal state is published in a result."""

    response_ledger.complete()
    provider_ledger.mark_complete()
    result["provider"] = provider_ledger.snapshot()


async def execute(
    *, resume: bool, context: DevelopmentRunContext = DEFAULT_CONTEXT
) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(
        context.instrument_id,
        "external_model_evaluation",
    )
    require_bounded_pilot_operation_allowed(
        context.instrument_id,
        "method_evaluation_execution",
    )
    ready = preflight(resume=resume, context=context)
    if ready["status"] != "ready":
        raise ArchitectureDevelopmentError(f"preflight blocked: {ready['blockers']}")
    instrument = _load_json(context.instrument_path)
    public = _load_bound_package(instrument["dataset"], gold=False)
    public_rows = list(public["rows"])
    eligible_rows = _eligible_public_rows(public_rows)
    binding = _binding(instrument, context)
    provider_ledger = ProviderCallLedgerV1(
        context.provider_ledger,
        run_binding=binding,
        maximum_calls=instrument["execution"]["maximum_provider_calls"],
        maximum_cost_usd=instrument["execution"]["emergency_cost_stop_usd"],
        maximum_transport_retries_total=0,
        resume=resume,
    )
    response_ledger = _ResponseLedger(
        context.response_ledger, binding=binding, resume=resume
    )
    transport = DirectProviderJsonTransport(instrument["fixed_engine"])
    contract_mode = instrument["execution"].get(
        "contract_mode", "four-case-batch"
    )
    planner_failures: list[str] = []
    verifier_failures: list[str] = []
    try:
        await _canaries(
            transport,
            provider_ledger,
            eligible_rows[0],
            contract_mode=contract_mode,
        )
        if contract_mode == "single-case-object":
            proposals, planner_failures = await _call_planner_single_cases(
                transport=transport,
                ledger=provider_ledger,
                public_rows=eligible_rows,
                concurrency=int(instrument["execution"]["concurrency"]),
            )
        else:
            proposals = await _call_planner_batches(
                transport=transport,
                ledger=provider_ledger,
                public_rows=eligible_rows,
            )
        selected = await _selected_c_rows(eligible_rows, proposals)
        if contract_mode == "single-case-object":
            verifications, verifier_failures = await _call_verifier_single_cases(
                transport=transport,
                ledger=provider_ledger,
                selected_rows=selected,
                concurrency=int(instrument["execution"]["concurrency"]),
            )
        else:
            verifications = await _call_verifier_batches(
                transport=transport,
                ledger=provider_ledger,
                selected_rows=selected,
            )
        await _run_graphs(
            public_rows=public_rows,
            proposals=proposals,
            verifications=verifications,
            response_ledger=response_ledger,
            graph_ledger=context.graph_ledger,
        )
        responses = response_ledger.rows()
        if len(responses) != 600:
            raise ArchitectureDevelopmentError("responses incomplete before gold opening")
        gold = _load_bound_package(instrument["dataset"], gold=True)
        result = _score(
            responses,
            public_rows,
            list(gold["rows"]),
            provider_ledger.snapshot(),
            {
                "planner_case_count": len(eligible_rows),
                "verifier_case_count": len(selected),
                "planner_failure_case_ids": sorted(planner_failures),
                "verifier_failure_case_ids": sorted(verifier_failures),
            },
        )
        result.update(
            {
                "record_schema": "research-evaluation-run-v1",
                "schema_version": 1,
                "run_id": instrument["instrument_id"],
                "code_revision": _git("rev-parse", "HEAD"),
                "dirty_state": bool(_git("status", "--porcelain")),
                "instrument_sha256": _file_sha256(context.instrument_path),
                "public_sha256": instrument["dataset"]["public_file_sha256"],
                "hidden_gold_sha256": instrument["dataset"]["hidden_gold_file_sha256"],
                "limitations": [
                    "Synthetic policy-oracle development cases do not establish real learning improvement.",
                    "Luna has no dated snapshot; one shared persisted proposal is reused across B, C, and C+V to prevent cross-condition proposal drift.",
                    "A single fresh development fold cannot select a final architecture or product model.",
                ],
            }
        )
        _finalize_ledgers(
            result,
            response_ledger=response_ledger,
            provider_ledger=provider_ledger,
        )
        _atomic_write(
            context.result_path,
            json.dumps(result, indent=2, sort_keys=True) + "\n",
        )
        _atomic_write(context.summary_path, _summary(result))
        return result
    except Exception:
        provider_ledger.mark_invalid_execution()
        raise
    finally:
        provider_ledger.close()
        response_ledger.close()


def _summary(result: dict[str, Any]) -> str:
    lines = [
        f"# {result['run_id']}",
        "",
        f"- **Status:** `{result['status']}`",
        "- **Decision:** no final architecture selected; continue only according to the frozen finite program.",
        f"- **Cases:** {result['case_count']} paired contexts / {result['architecture_cell_count']} graph cells.",
        f"- **Provider:** {result['provider']['provider_calls']} calls, USD {result['provider']['reported_cost_usd']:.6f}.",
        f"- **Provider completion:** {result['provider_quality']['provider_completion_rate']:.1%}; safe fallback {result['provider_quality']['provider_failure_safe_fallback_rate']:.1%}.",
        "",
        "## Architecture metrics",
        "",
        "| Architecture | Acceptable move | Proactive precision | Unnecessary intervention |",
        "| --- | ---: | ---: | ---: |",
    ]
    for architecture, metrics in result["aggregate"].items():
        lines.append(
            f"| `{architecture}` | {metrics['acceptable_move_accuracy']:.1%} | "
            f"{metrics['proactive_precision']:.1%} | "
            f"{metrics['unnecessary_intervention_rate']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            result["decision"]["rationale"],
            "",
            "Learner-state calibration is reported once as a shared diagnostic because this ablation holds the learner-state plane fixed. It is not counted as an architecture win.",
            "",
        ]
    )
    return "\n".join(lines)


def simulate(context: DevelopmentRunContext = DEFAULT_CONTEXT) -> dict[str, Any]:
    instrument = _load_json(context.instrument_path)
    public = _load_bound_package(instrument["dataset"], gold=False)
    eligible = _eligible_public_rows(list(public["rows"]))
    contract_mode = instrument["execution"].get(
        "contract_mode", "four-case-batch"
    )
    batches = _chunks(eligible, instrument["execution"]["batch_size"])
    maximum_provider_calls = (
        2 + 2 * len(eligible)
        if contract_mode == "single-case-object"
        else 2 + 2 * len(batches)
    )
    return {
        **validate(context),
        "status": "simulated-network-free",
        "eligible_case_count": len(eligible),
        "planner_batch_count": len(batches),
        "maximum_verifier_batch_count": len(batches),
        "maximum_provider_calls": maximum_provider_calls,
        "gold_loaded": False,
        "provider_calls": 0,
    }


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--attempt",
        choices=("001", "002", "fold-002", "fold-002-corrective", "fold-003"),
        default="001",
    )
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    context = _run_context(args.attempt)
    if args.execute:
        require_bounded_pilot_operation_allowed(
            context.instrument_id, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            context.instrument_id, "method_evaluation_execution"
        )
        result = asyncio.run(execute(resume=args.resume, context=context))
    elif args.preflight:
        result = preflight(resume=args.resume, context=context)
    elif args.simulate:
        result = simulate(context)
    else:
        result = validate(context)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
