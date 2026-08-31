"""Validate and simulate the governed V2.1 local product-freeze contract."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.digital_twin.action_router import DeterministicActionRouterV2
from src.digital_twin.student import (
    Conversation,
    Message,
    OutreachChannel,
    ProactiveOutreachService,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    TeachingProfileDepth,
    TeachingProfileService,
    seed_synthetic_student_workflow,
)
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
)
from src.digital_twin.student.autonomy_service import GovernedAutonomyService


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_product_freeze_001.json"
)
CASES_PATH = (
    ROOT
    / "research/05_evaluation/datasets/"
    "academic-factual-qa-action-router-product-development-001-cases.json"
)
GOLD_PATH = (
    ROOT
    / "research/05_evaluation/datasets/"
    "academic-factual-qa-action-router-product-development-001-gold.json"
)
NOW = datetime(2026, 8, 31, 4, 0, tzinfo=UTC)
OBJECTIVE = "Explain how cache coherence protects replicated processor data."
ACTION_MAP = {
    "redirect-graded-work": "refuse",
    "clarify": "clarify",
    "no-evidence": "abstain",
}
ALLOWED_ACTIONS = [
    AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
    AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE,
    AutonomousActionKind.RECOMMEND_APPROVED_SOURCE,
    AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE,
    AutonomousActionKind.SCHEDULE_FOLLOW_UP,
    AutonomousActionKind.SEND_IN_APP_CHECK_IN,
    AutonomousActionKind.SUMMARIZE_PROGRESS,
    AutonomousActionKind.CREATE_PROFESSOR_INSIGHT_DRAFT,
    AutonomousActionKind.NO_ACTION,
]


def validate() -> dict:
    instrument = json.loads(INSTRUMENT_PATH.read_text())
    if instrument["instrument_id"] != "governed-full-autonomy-v2-1-product-freeze-001":
        raise ValueError("wrong governed autonomy freeze instrument")
    if instrument["system"]["provider_calls"] != 0:
        raise ValueError("product-freeze simulation must remain network-free")
    if instrument["development_evidence"]["uses_program_011_sealed_final_set"]:
        raise ValueError("product-freeze simulation cannot open Program 011 final data")
    return instrument


def _action_router_result() -> dict:
    cases = json.loads(CASES_PATH.read_text())["cases"]
    gold = {
        item["case_id"]: item
        for item in json.loads(GOLD_PATH.read_text())["gold"]
    }
    router = DeterministicActionRouterV2()
    correct = 0
    by_action: dict[str, int] = {}
    for case in cases:
        route = router.route(case["question"])
        actual = ACTION_MAP.get(route.action if route is not None else "", "answer")
        expected = gold[case["case_id"]]["expected_action"]
        correct += int(actual == expected)
        by_action[expected] = by_action.get(expected, 0) + int(actual == expected)
    return {
        "case_count": len(cases),
        "correct": correct,
        "accuracy": correct / len(cases),
        "correct_by_expected_action": by_action,
    }


def _build_runtime(database_path: Path):
    repository = SQLiteStudentRepository(database_path)
    fixture = seed_synthetic_student_workflow(repository)
    profiles = TeachingProfileService(repository)
    draft = profiles.create_draft(
        fixture.professor_id,
        fixture.course_a_id,
        {
            "tone": "Patient, precise, and encouraging",
            "depth": TeachingProfileDepth.BALANCED,
            "explanation_structure": ["diagnose", "hint", "check"],
            "example_preferences": ["systems examples"],
            "misconception_handling": "Identify the misconception and ask for one corrected step.",
            "integrity_limits": "Require an attempt before assessed-work help.",
            "help_ladder": ["diagnostic question", "hint", "worked analogy"],
            "outreach_policy": "Private in-app follow-ups within approved limits.",
        },
    )
    preview = profiles.preview(fixture.professor_id, fixture.course_a_id, draft.profile_id)
    profile = profiles.approve(
        fixture.professor_id,
        fixture.course_a_id,
        draft.profile_id,
        preview_sha256=preview.preview_sha256,
    )
    source_release = repository.get_published_release(fixture.course_a_id)
    release = source_release.model_copy(
        update={
            "id": "release-governed-autonomy-freeze",
            "status": StudentReleaseStatus.DRAFT,
            "teaching_profile_id": profile.profile_id,
            "teaching_profile_sha256": profile.content_sha256,
            "created_at": NOW.isoformat(),
        },
        deep=True,
    )
    repository.save_release(release)
    repository.publish_release(release.id)
    outreach = ProactiveOutreachService(repository)
    outreach.update_preference(
        fixture.student_a_id,
        fixture.course_a_id,
        channel=OutreachChannel.IN_APP,
        enabled=True,
        timezone="UTC",
        quiet_hours_start="23:00",
        quiet_hours_end="02:00",
        max_messages_per_7_days=3,
    )
    service = GovernedAutonomyService(repository, outreach)
    service.set_policy(
        fixture.professor_id,
        fixture.course_a_id,
        approved_course_objectives=[OBJECTIVE],
        allowed_actions=ALLOWED_ACTIONS,
        autonomy_enabled=True,
    )
    return repository, fixture, release, service


async def simulate() -> dict:
    validate()
    routing = _action_router_result()
    with tempfile.TemporaryDirectory(prefix="governed-autonomy-freeze-") as directory:
        root = Path(directory)
        database_path = root / "candidate.sqlite3"
        repository, fixture, release, service = _build_runtime(database_path)
        goal = service.create_goal(
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            approved_course_objective=OBJECTIVE,
            learner_subgoal="Explain the purpose of cache invalidation.",
            success_condition="Answer one cited retrieval prompt without a hint.",
            expires_at=(NOW + timedelta(days=8)).isoformat(),
        )
        service.create_opportunity(
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            goal_id=goal.goal_id,
            event_kind=AutonomousEventKind.SPACED_REVIEW_DUE,
            concept_id="cache-coherence",
            source_chunk_id=release.chunks[0].id,
            earliest_action_at=NOW.isoformat(),
            latest_action_at=(NOW + timedelta(hours=12)).isoformat(),
            idempotency_key="freeze-day-0",
        )
        daily_results = []
        for day in range(3):
            daily_results.extend(
                await service.process_due(
                    worker_id=f"freeze-worker-day-{day}",
                    now=NOW + timedelta(days=day),
                )
            )
        repository.close()

        repository = SQLiteStudentRepository(database_path)
        service = GovernedAutonomyService(
            repository, ProactiveOutreachService(repository)
        )
        for day in range(3, 7):
            daily_results.extend(
                await service.process_due(
                    worker_id=f"freeze-worker-day-{day}",
                    now=NOW + timedelta(days=day),
                )
            )
        inbox = service.outreach.list_inbox(fixture.student_a_id)
        actions = repository.list_autonomous_actions(fixture.course_a_id)
        first_message = inbox[-1].message
        linked_action = next(
            action
            for action in actions
            if action.proactive_trigger_id == first_message.trigger_id
        )
        conversation = repository.save_conversation(
            Conversation(
                id="freeze-response-conversation",
                student_id=fixture.student_a_id,
                course_id=fixture.course_a_id,
                release_id=release.id,
                created_at=(NOW + timedelta(days=6, minutes=1)).isoformat(),
                updated_at=(NOW + timedelta(days=6, minutes=1)).isoformat(),
            )
        )
        student_message = Message(
            id="freeze-response-message",
            conversation_id=conversation.id,
            role="student",
            content="Invalidation prevents cached copies from silently diverging.",
            action="question",
            client_request_id="freeze-response-request",
            created_at=conversation.created_at,
        )
        tutor_message = Message(
            id="freeze-response-tutor-message",
            conversation_id=conversation.id,
            role="tutor",
            content="Response recorded; the next turn remains evidence-gated.",
            action="safe-failure",
            response_to_message_id=student_message.id,
            created_at=conversation.created_at,
        )
        repository.save_turn(
            conversation,
            student_message,
            tutor_message,
            [],
            [],
            responding_to_outreach_message_id=first_message.id,
        )
        linked_outcome = repository.get_autonomous_outcome(linked_action.action_id)
        service.outreach.update_preference(
            fixture.student_a_id,
            fixture.course_a_id,
            channel=OutreachChannel.IN_APP,
            enabled=False,
            timezone="UTC",
            quiet_hours_start="23:00",
            quiet_hours_end="02:00",
            max_messages_per_7_days=3,
        )
        cancelled_goal = repository.get_autonomous_goal(goal.goal_id)
        repository.close()

        backup_path = root / "backup.sqlite3"
        shutil.copy2(database_path, backup_path)
        restored = SQLiteStudentRepository(backup_path)
        restored_actions = restored.list_autonomous_actions(fixture.course_a_id)
        restored_goal = restored.get_autonomous_goal(goal.goal_id)
        restored.close()

        message_ids = [item.message.id for item in inbox]
        action_ids = [action.action_id for action in actions]
        gates = {
            "action_router_accuracy": routing["accuracy"] == 1.0,
            "seven_day_jobs_completed": len(daily_results) == 7,
            "frequency_limit_respected": len(inbox) == 3,
            "citation_lineage_valid": all(
                item.citations
                and all(citation.release_id == release.id for citation in item.citations)
                for item in inbox
            ),
            "duplicate_messages_zero": len(message_ids) == len(set(message_ids)),
            "duplicate_actions_zero": len(action_ids) == len(set(action_ids)),
            "restart_consistent": len(actions) == 7,
            "response_goal_linked": bool(
                linked_outcome is not None
                and linked_outcome.kind.value == "answered"
                and linked_outcome.goal_id == goal.goal_id
                and linked_outcome.learner_observation_id == student_message.id
            ),
            "consent_withdrawal_stops_goal": cancelled_goal.status.value == "cancelled",
            "backup_restore_consistent": bool(
                restored_goal == cancelled_goal
                and len(restored_actions) == len(actions)
            ),
            "per_job_call_limits_respected": all(
                result.planning_proposals in {0, 1}
                and result.generation_attempts in {0, 1}
                for result in daily_results
            ),
        }
        return {
            "instrument_id": "governed-full-autonomy-v2-1-product-freeze-001",
            "status": "passed" if all(gates.values()) else "failed",
            "routing": routing,
            "autonomy": {
                "simulated_days": 7,
                "job_count": len(daily_results),
                "delivered_message_count": len(inbox),
                "action_count": len(actions),
                "outcomes": [result.outcome for result in daily_results],
            },
            "gates": gates,
            "provider_calls": 0,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    arguments = parser.parse_args()
    if arguments.validate:
        print(json.dumps({"status": "valid", **validate()}, indent=2))
        return
    import asyncio

    result = asyncio.run(simulate())
    print(json.dumps(result, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
