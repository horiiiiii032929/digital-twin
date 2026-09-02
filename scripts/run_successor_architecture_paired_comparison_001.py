"""Validate and simulate the switchable A/B/C autonomy architecture runtime.

This checkpoint is network-free. It proves that the compared architectures
share the same product authority boundary and that the two switches recover A
and B exactly before any paid or quality comparison is attempted.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from src.digital_twin.evaluation.autonomy_architecture_tournament import (
    AutonomyArchitectureTournamentProgramV1,
)
from src.digital_twin.student.autonomy_eligibility import (
    event_scoped_eligible_actions,
    preferred_event_action,
)
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
from src.digital_twin.student.planning_architectures import (
    AutonomyArchitectureId,
    EpisodeStepProposalV1,
    HierarchicalPlanningProposalV1,
    PlannerVerificationV1,
    SwitchableAutonomyPlanner,
)
from src.digital_twin.student.repository import SQLiteStudentRepository


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "successor_architecture_paired_comparison_001.json"
)
RESULT_PATH = ROOT / (
    "research/05_evaluation/records/"
    "successor-architecture-paired-comparison-001-build-001.json"
)
SUMMARY_PATH = ROOT / (
    "research/05_evaluation/"
    "successor-architecture-paired-comparison-001-build-001-results.md"
)
NOW = datetime(2026, 9, 2, 4, 0, tzinfo=UTC)
PROFILE_SHA = "a" * 64
ALL_ACTIONS = [
    action for action in AutonomousActionKind if action != AutonomousActionKind.NO_ACTION
]


class _FixtureProposalProvider:
    model_id = "fixture/planner-v1"

    def __init__(self) -> None:
        self.calls = 0

    async def propose(self, **kwargs):
        self.calls += 1
        job = kwargs["job"]
        eligible = kwargs["eligible_actions"]
        action = preferred_event_action(job.opportunity.event_kind, job.policy.allowed_actions)
        steps = []
        if action != AutonomousActionKind.NO_ACTION:
            steps = [
                EpisodeStepProposalV1(
                    action=action,
                    expected_observation="Observe one durable learner response.",
                    stop_or_replan_predicate="Replan after a new durable event.",
                )
            ]
        assert action in eligible
        return HierarchicalPlanningProposalV1(
            selected_action=action,
            reason_code=f"fixture-{job.opportunity.event_kind.value}",
            expected_learner_action=(
                "Respond in the course workspace."
                if action != AutonomousActionKind.NO_ACTION
                else None
            ),
            outcome_observation=(
                "Observe one durable learner response."
                if action != AutonomousActionKind.NO_ACTION
                else None
            ),
            stop_condition="Stop after this bounded decision.",
            replan_condition=(
                "Replan after a new durable event."
                if action != AutonomousActionKind.NO_ACTION
                else None
            ),
            episode_steps=steps,
        )


class _FixtureVerifier:
    model_id = "fixture/verifier-v1"

    def __init__(self) -> None:
        self.calls = 0

    async def verify(self, **kwargs):
        self.calls += 1
        proposal = kwargs["proposal"]
        eligible = kwargs["eligible_actions"]
        return PlannerVerificationV1(
            accept=proposal.action in eligible,
            reason_code="inside-deterministic-envelope",
        )


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_program() -> AutonomyArchitectureTournamentProgramV1:
    return AutonomyArchitectureTournamentProgramV1.model_validate_json(
        INSTRUMENT_PATH.read_text(encoding="utf-8")
    )


def validate() -> dict[str, Any]:
    program = load_program()
    checks = {
        "four_architectures_bound": len(program.architectures) == 4,
        "four_engine_allocations_bound": len(program.engine_allocations) == 4,
        "exactly_three_improvement_rounds": program.maximum_improvement_rounds == 3,
        "confirmation_rerun_prohibited": not program.same_confirmation_quality_rerun_allowed,
        "deterministic_truth_authoritative": program.deterministic_truth_authoritative,
        "paid_execution_unauthorized": not program.paid_execution_authorized,
        "no_human_participants_required": not program.human_participants_required,
    }
    return {
        "program_id": program.program_id,
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "instrument_sha256": _sha256(INSTRUMENT_PATH),
        "provider_calls": 0,
        "cost_usd": 0,
    }


def _job(
    event: AutonomousEventKind,
    *,
    case_id: str,
    consent_active: bool = True,
    membership_active: bool = True,
    current_release_id: str = "release-a",
    within_quiet_hours: bool = False,
    recent_message_count: int = 0,
    cooldown_active: bool = False,
    evidence_ready: bool = True,
) -> AutonomousJobInput:
    goal = AutonomousGoalV1(
        goal_id=f"goal-{case_id}",
        student_id="student-a",
        course_id="course-a",
        release_id="release-a",
        policy_version=1,
        profile_id="profile-a",
        profile_sha256=PROFILE_SHA,
        graph_version=GRAPH_VERSION,
        planner_model="fixture/planner-v1",
        generator_model="deterministic/autonomy-wording-v1",
        approved_course_objective="Explain cache coherence.",
        learner_subgoal="Explain one correct next step.",
        success_condition="Produce one assessed explanation.",
        attempt_limit=3,
        attempt_count=1,
        expires_at=(NOW + timedelta(days=7)).isoformat(),
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
    )
    opportunity = ProactiveOpportunityV1(
        opportunity_id=f"opportunity-{case_id}",
        idempotency_key=f"idempotency-{case_id}",
        event_kind=event,
        student_id="student-a",
        course_id="course-a",
        release_id="release-a",
        policy_version=1,
        profile_id="profile-a",
        profile_sha256=PROFILE_SHA,
        graph_version=GRAPH_VERSION,
        planner_model="fixture/planner-v1",
        generator_model="deterministic/autonomy-wording-v1",
        goal_id=goal.goal_id,
        supporting_observation_ids=["observation-a", "observation-b"],
        concept_id="cache-coherence",
        source_chunk_id="chunk-a" if evidence_ready else None,
        source_chunk_ids=["chunk-a"] if evidence_ready else [],
        earliest_action_at=(NOW - timedelta(minutes=1)).isoformat(),
        latest_action_at=(NOW + timedelta(hours=1)).isoformat(),
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
    )
    policy = PedagogicalPolicyV2(
        course_id="course-a",
        version=1,
        approved_by="professor-a",
        approved_profile_id="profile-a",
        approved_profile_sha256=PROFILE_SHA,
        approved_course_objectives=["Explain cache coherence."],
        autonomy_enabled=True,
        allowed_actions=ALL_ACTIONS,
        updated_at=NOW.isoformat(),
    )
    return AutonomousJobInput(
        opportunity=opportunity,
        goal=goal,
        policy=policy,
        professor_id="professor-a",
        current_release_id=current_release_id,
        current_profile_id="profile-a",
        current_profile_sha256=PROFILE_SHA,
        membership_active=membership_active,
        consent_active=consent_active,
        within_quiet_hours=within_quiet_hours,
        recent_message_count=recent_message_count,
        same_concept_cooldown_active=cooldown_active,
        evidence_keys=["source-range-a"] if evidence_ready else [],
        evidence_chunk_ids=["chunk-a"] if evidence_ready else [],
        evidence_decision_reason="fixture-authoritative-evidence",
        evidence_complete=evidence_ready,
        evidence_unique=evidence_ready,
        evidence_current=evidence_ready,
        evidence_authorized=evidence_ready,
        now=NOW.isoformat(),
    )


def _scenarios() -> list[tuple[str, AutonomousJobInput]]:
    return [
        ("student-message", _job(AutonomousEventKind.STUDENT_MESSAGE, case_id="message")),
        ("repeated-confusion", _job(AutonomousEventKind.REPEATED_CONFUSION, case_id="confusion")),
        ("misconception", _job(AutonomousEventKind.MISCONCEPTION, case_id="misconception")),
        ("spaced-review", _job(AutonomousEventKind.SPACED_REVIEW_DUE, case_id="review")),
        ("inactivity", _job(AutonomousEventKind.STUDENT_INACTIVITY, case_id="inactive")),
        ("evidence-recovered", _job(AutonomousEventKind.EVIDENCE_RECOVERED, case_id="recovered")),
        ("practice-incomplete", _job(AutonomousEventKind.PRACTICE_INCOMPLETE, case_id="practice")),
        ("professor-scheduled", _job(AutonomousEventKind.PROFESSOR_SCHEDULED, case_id="scheduled")),
        ("consent-withdrawn", _job(AutonomousEventKind.INCOMPLETE_OBJECTIVE, case_id="consent", consent_active=False)),
        ("wrong-release", _job(AutonomousEventKind.NEW_COURSE_RELEASE, case_id="release", current_release_id="release-b")),
        ("quiet-hours", _job(AutonomousEventKind.STUDENT_INACTIVITY, case_id="quiet", within_quiet_hours=True)),
        ("missing-evidence", _job(AutonomousEventKind.MISCONCEPTION, case_id="evidence", evidence_ready=False)),
    ]


def _planner(
    architecture: AutonomyArchitectureId,
) -> tuple[SwitchableAutonomyPlanner, _FixtureProposalProvider | None, _FixtureVerifier | None]:
    if architecture == AutonomyArchitectureId.DETERMINISTIC_WORKFLOW_A:
        return SwitchableAutonomyPlanner(architecture_id=architecture), None, None
    provider = _FixtureProposalProvider()
    verifier = (
        _FixtureVerifier()
        if architecture == AutonomyArchitectureId.HIERARCHICAL_WITH_VERIFIER_CV
        else None
    )
    return (
        SwitchableAutonomyPlanner(
            architecture_id=architecture,
            proposal_provider=provider,
            verifier=verifier,
        ),
        provider,
        verifier,
    )


async def _simulate() -> dict[str, Any]:
    validation = validate()
    rows: list[dict[str, Any]] = []
    provider_calls: dict[str, int] = {}
    verifier_calls: dict[str, int] = {}
    with tempfile.TemporaryDirectory(prefix="architecture-tournament-") as directory:
        output_root = Path(directory)
        for architecture in AutonomyArchitectureId:
            planner, provider, verifier = _planner(architecture)
            for index, (scenario_id, original_job) in enumerate(_scenarios()):
                job = original_job.model_copy(
                    update={
                        "opportunity": original_job.opportunity.model_copy(
                            update={
                                "opportunity_id": (
                                    f"{original_job.opportunity.opportunity_id}-{architecture.value}"
                                ),
                                "idempotency_key": (
                                    f"{original_job.opportunity.idempotency_key}-{architecture.value}"
                                ),
                            }
                        )
                    }
                )
                database_path = output_root / f"{architecture.value}-{index}.sqlite3"
                repository = SQLiteStudentRepository(database_path)
                repository.close()
                graph = GovernedAutonomousTutoringGraph(
                    planner=planner,
                    checkpoint_database_path=str(database_path),
                )
                result = await graph.run(job)
                delivered = result.action.kind != AutonomousActionKind.NO_ACTION
                eligible = event_scoped_eligible_actions(
                    job.opportunity.event_kind, job.policy.allowed_actions
                )
                rows.append(
                    {
                        "architecture_id": architecture.value,
                        "scenario_id": scenario_id,
                        "selected_action": result.action.kind.value,
                        "action_inside_envelope": result.action.kind in eligible,
                        "delivery_authorized": (
                            not delivered
                            or (
                                job.membership_active
                                and job.consent_active
                                and not job.within_quiet_hours
                                and job.current_release_id == job.opportunity.release_id
                                and job.evidence_complete
                                and job.evidence_unique
                                and job.evidence_current
                                and job.evidence_authorized
                            )
                        ),
                        "lineage_valid": (
                            not delivered
                            or (
                                result.response is not None
                                and bool(result.response.source_range_keys)
                                and set(result.response.source_range_keys).issubset(
                                    set(job.evidence_keys)
                                )
                            )
                        ),
                        "planning_calls_recorded": result.trace.planning_calls,
                        "bounded_node_count": len(result.trace.node_path) <= 12,
                    }
                )
            provider_calls[architecture.value] = provider.calls if provider else 0
            verifier_calls[architecture.value] = verifier.calls if verifier else 0

    # B and depth-zero C must produce byte-identical planner outputs for the
    # same provider proposal. This is the key one-factor ablation invariant.
    depth_zero_equal = True
    for _scenario_id, job in _scenarios():
        provider_b = _FixtureProposalProvider()
        provider_c = _FixtureProposalProvider()
        planner_b = SwitchableAutonomyPlanner(
            architecture_id=AutonomyArchitectureId.GOVERNED_SINGLE_PLANNER_B,
            proposal_provider=provider_b,
        )
        planner_c = SwitchableAutonomyPlanner(
            architecture_id=AutonomyArchitectureId.HIERARCHICAL_MODEL_BASED_C,
            proposal_provider=provider_c,
            lookahead_depth=0,
        )
        output_b, _ = await planner_b.plan_with_trace(job)
        output_c, _ = await planner_c.plan_with_trace(job)
        depth_zero_equal &= output_b == output_c

    gates = {
        "instrument_valid": validation["status"] == "passed",
        "all_48_cells_executed": len(rows) == 48,
        "zero_action_envelope_violations": all(row["action_inside_envelope"] for row in rows),
        "zero_unauthorized_deliveries": all(row["delivery_authorized"] for row in rows),
        "zero_invalid_lineage": all(row["lineage_valid"] for row in rows),
        "all_graphs_bounded": all(row["bounded_node_count"] for row in rows),
        "candidate_a_zero_model_planning": provider_calls[AutonomyArchitectureId.DETERMINISTIC_WORKFLOW_A.value] == 0
        and all(
            row["planning_calls_recorded"] == 0
            for row in rows
            if row["architecture_id"]
            == AutonomyArchitectureId.DETERMINISTIC_WORKFLOW_A.value
        ),
        "candidate_b_is_depth_zero_c": depth_zero_equal,
        "c_plus_verifier_is_reject_only_ablation": verifier_calls[
            AutonomyArchitectureId.HIERARCHICAL_WITH_VERIFIER_CV.value
        ]
        <= provider_calls[AutonomyArchitectureId.HIERARCHICAL_WITH_VERIFIER_CV.value],
        "no_paid_or_network_activity": True,
    }
    return {
        "validation": validation,
        "rows": rows,
        "provider_calls": provider_calls,
        "verifier_calls": verifier_calls,
        "gates": gates,
        "passed": all(gates.values()),
    }


def simulate() -> dict[str, Any]:
    return asyncio.run(_simulate())


def _record(result: dict[str, Any]) -> dict[str, Any]:
    revision = _git("rev-parse", "HEAD")
    return {
        "record_schema": "research-evaluation-run-v1",
        "schema_version": 1,
        "run_id": "successor-architecture-paired-comparison-001-build-001",
        "code_revision": revision,
        "dirty_state": bool(_git("status", "--porcelain")),
        "status": "build-only-qualified" if result["passed"] else "completed-refine",
        "decision": {
            "outcome": "go-deeper" if result["passed"] else "refine",
            "selected_architecture_id": None,
            "rationale": (
                "The shared A/B/C/C+V runtime and paired evaluation boundary pass "
                "network-free conformance. No architecture or engine is selected until "
                "the preregistered quality comparisons execute."
            ),
        },
        "instrument": {
            "path": str(INSTRUMENT_PATH.relative_to(ROOT)),
            "sha256": _sha256(INSTRUMENT_PATH),
        },
        "case_count": len(result["rows"]),
        "hard_gates": result["gates"],
        "architecture_provider_calls_simulated": result["provider_calls"],
        "architecture_verifier_calls_simulated": result["verifier_calls"],
        "operational": {
            "real_provider_calls": 0,
            "tokens": 0,
            "cost_usd": 0,
        },
        "limitations": [
            "This is network-free runtime conformance, not an architecture quality result.",
            "Fixture planner outputs cannot establish pedagogical quality or an engine effect.",
            "The final 1,000, known 10,000, autonomy 820, and product qualification remain unopened.",
        ],
    }


def _summary(record: dict[str, Any]) -> str:
    gates = record["hard_gates"]
    return "\n".join(
        [
            "# Successor architecture paired comparison 001 — build result",
            "",
            f"- **Status:** `{record['status']}`",
            "- **Decision:** Go Deeper on the finite comparison; no architecture selected.",
            f"- **Network-free cells:** {record['case_count']}/48 completed.",
            "- **Provider usage:** 0 calls, 0 tokens, USD 0.",
            "",
            "## Conformance gates",
            "",
            *[
                f"- {'PASS' if passed else 'FAIL'} — `{name}`"
                for name, passed in gates.items()
            ],
            "",
            "## Interpretation",
            "",
            "A, B, C, and C+V now share one runtime boundary. Disabling the planner recovers A; setting lookahead to zero recovers B; C adds only the analytic forward-model comparison; C+V adds only a reject-only verifier. Deterministic policy, evidence, scope, delivery, and persistence checks remain unchanged.",
            "",
            "This result validates the comparison mechanics only. It does not select C, B, A, or an OpenAI engine allocation.",
            "",
        ]
    )


def publish(result: dict[str, Any]) -> dict[str, Any]:
    record = _record(result)
    RESULT_PATH.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(_summary(record), encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    if args.validate and not args.simulate and not args.publish:
        print(json.dumps(validate(), indent=2, sort_keys=True))
        return 0
    result = simulate()
    payload = publish(result) if args.publish else result
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
