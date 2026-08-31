"""Run network-free V2.1 implementation acceptance checks.

This is software verification, not an academic evaluation result. Historical
instruments and their immutable outputs remain unchanged.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from datetime import timedelta
from pathlib import Path

from scripts.run_governed_full_autonomy_product_freeze import (
    NOW,
    OBJECTIVE,
    _build_runtime,
)
from src.digital_twin.student import ProactiveOutreachService, SQLiteStudentRepository
from src.digital_twin.student.autonomy_models import (
    AutonomousEventKind,
)
from src.digital_twin.student.autonomy_service import GovernedAutonomyService


async def simulate_thirty_days() -> dict:
    """Exercise expiry, a process restart, frequency limits, and deduplication."""

    with tempfile.TemporaryDirectory(prefix="governed-autonomy-v2-1-") as directory:
        database_path = Path(directory) / "long-horizon.sqlite3"
        repository, fixture, release, service = _build_runtime(database_path)
        goal = service.create_goal(
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            approved_course_objective=OBJECTIVE,
            learner_subgoal="Revisit cache coherence until the governed goal expires.",
            success_condition="Provide two assessed source-grounded explanations.",
            expires_at=(NOW + timedelta(days=15)).isoformat(),
            attempt_limit=10,
        )
        service.create_opportunity(
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            goal_id=goal.goal_id,
            event_kind=AutonomousEventKind.SPACED_REVIEW_DUE,
            concept_id="cache-coherence-long-horizon",
            source_chunk_id=release.chunks[0].id,
            earliest_action_at=NOW.isoformat(),
            latest_action_at=(NOW + timedelta(hours=12)).isoformat(),
            idempotency_key="long-horizon-day-0",
        )
        results_by_day: list[list[object]] = []
        for day in range(30):
            if day == 8:
                repository.close()
                repository = SQLiteStudentRepository(database_path)
                service = GovernedAutonomyService(
                    repository,
                    ProactiveOutreachService(repository),
                )
            results_by_day.append(
                await service.process_due(
                    worker_id=f"long-horizon-worker-day-{day}",
                    now=NOW + timedelta(days=day),
                )
            )
        actions = repository.list_autonomous_actions(
            fixture.course_a_id,
            student_id=fixture.student_a_id,
        )
        inbox = service.outreach.list_inbox(fixture.student_a_id)
        final_goal = repository.get_autonomous_goal(goal.goal_id)
        repository.close()

    action_ids = [action.action_id for action in actions]
    message_ids = [item.message.id for item in inbox]
    active_day_count = sum(bool(items) for items in results_by_day)
    post_expiry_jobs = sum(len(items) for items in results_by_day[16:])
    gates = {
        "goal_expires": final_goal.status.value == "expired",
        "post_expiry_jobs_zero": post_expiry_jobs == 0,
        "loop_is_finite": active_day_count < 30,
        "restart_preserves_progress": bool(actions and active_day_count >= 8),
        "duplicate_actions_zero": len(action_ids) == len(set(action_ids)),
        "duplicate_messages_zero": len(message_ids) == len(set(message_ids)),
    }
    return {
        "verification_id": "governed-autonomy-v2-1-implementation-acceptance",
        "status": "passed" if all(gates.values()) else "failed",
        "simulated_days": 30,
        "active_day_count": active_day_count,
        "job_count": sum(len(items) for items in results_by_day),
        "delivered_message_count": len(inbox),
        "post_expiry_job_count": post_expiry_jobs,
        "goal_status": final_goal.status.value,
        "gates": gates,
        "provider_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", action="store_true", required=True)
    parser.parse_args()
    result = asyncio.run(simulate_thirty_days())
    print(json.dumps(result, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
