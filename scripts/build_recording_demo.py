"""Build a network-free, synthetic service-event trace for the recording page.

This is a presentation fixture, not a model or learning-effect evaluation.
Run: uv run python -m scripts.build_recording_demo
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.grounding import StructuredLexicalCoverageEvidenceGate
from src.digital_twin.student import (
    SQLiteStudentRepository, StudentTutoringService, TeachingProfileService,
    TeachingProfileDepth, ProactiveOutreachService, OutreachChannel,
    StudentReleaseStatus, seed_synthetic_student_workflow,
    CanonicalSourceRangeV1, CourseConceptV1, CourseDomainModelV1, CourseObjectiveV1,
)
from src.digital_twin.student.models import Account, AccountRole, CourseMembership, MembershipRole
from src.digital_twin.student.autonomy_models import AutonomousActionKind, AutonomousEventKind
from src.digital_twin.student.autonomy_service import GovernedAutonomyService
from src.digital_twin.student.tutoring_graph import TutoringMode

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
OUTPUT = ROOT / "apps/web/public/recording-demo.json"


async def build_trace(database: Path) -> dict:
    repository = SQLiteStudentRepository(database)
    clock = VirtualUtcClock(datetime(2026, 9, 7, 4, tzinfo=UTC))
    events = []
    def record(at, kind, title, *, course=None, student=None, data=None):
        events.append(dict(at=at, kind=kind, title=title, course=course, student=student,
                           virtual_time=clock.now().isoformat(), data=data or {}))
    try:
        fixture = seed_synthetic_student_workflow(repository)
        professor_b = "professor-b-recording"
        repository.save_account(Account(id=professor_b, role=AccountRole.PROFESSOR))
        original_b = repository.get_course(fixture.course_b_id)
        course_b = original_b.model_copy(update={"id": "course-b-recording", "owner_professor_id": professor_b})
        repository.save_course(course_b)
        original_release_b = repository.get_published_release(fixture.course_b_id)
        repository.save_release(original_release_b.model_copy(update={
            "id": "release-b-recording-seed", "course_id": course_b.id,
            "chunks": [chunk.model_copy(update={"metadata": {**chunk.metadata, "course_id": course_b.id}})
                       for chunk in original_release_b.chunks],
        }, deep=True))
        repository.save_membership(CourseMembership(account_id=professor_b, course_id=course_b.id,
                                                     role=MembershipRole.PROFESSOR))
        courses = [
            dict(id=fixture.course_a_id, professor=fixture.professor_id, label="Systems", instructor="Professor A",
                 topic="Cache coherence", objective="Explain how cache coherence protects replicated processor data."),
            dict(id=course_b.id, professor=professor_b, label="Release governance", instructor="Professor B",
                 topic="Release policy", objective="Explain approval and withdrawal controls in a release policy."),
        ]
        students = [
            dict(id=fixture.student_a_id, label="Student A1", course=courses[0]["id"]),
            dict(id="student-a2-recording", label="Student A2", course=courses[0]["id"]),
            dict(id=fixture.student_b_id, label="Student B1", course=courses[1]["id"]),
            dict(id="student-b2-recording", label="Student B2", course=courses[1]["id"]),
        ]
        profiles = TeachingProfileService(repository)
        outreach = ProactiveOutreachService(repository)
        autonomy = GovernedAutonomyService(repository, outreach, clock=clock)
        actions = [AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE]
        releases = {}
        for i, course in enumerate(courses):
            draft = profiles.create_draft(course["professor"], course["id"], {
                "tone": "Patient and precise", "depth": TeachingProfileDepth.BALANCED,
                "explanation_structure": ["explain", "check"],
                "example_preferences": [course["topic"]],
                "misconception_handling": "Check the student's explanation against approved sources.",
                "integrity_limits": "Require an attempt on assessed work.",
                "help_ladder": ["question", "hint", "approved source"],
                "outreach_policy": "Private in-app practice with student consent.",
            })
            preview = profiles.preview(course["professor"], course["id"], draft.profile_id)
            approved = profiles.approve(course["professor"], course["id"], draft.profile_id,
                                        preview_sha256=preview.preview_sha256)
            original = repository.get_published_release(course["id"])
            release = original.model_copy(update={
                "id": f"recording-release-{i}", "status": StudentReleaseStatus.DRAFT,
                "teaching_profile_id": approved.profile_id, "teaching_profile_sha256": approved.content_sha256,
                "created_at": clock.now().isoformat(),
            }, deep=True)
            repository.save_release(release)
            repository.publish_release(release.id)
            chunk = release.chunks[0]
            repository.save_course_domain_model(CourseDomainModelV1(
                domain_model_id=f"recording-domain-{i}", course_id=course["id"], release_id=release.id,
                release_sha256=hashlib.sha256(release.model_dump_json().encode()).hexdigest(), version=1,
                objectives=[CourseObjectiveV1(objective_id=f"objective-{i}", statement=course["objective"],
                                              concept_ids=[f"concept-{i}"])],
                concepts=[CourseConceptV1(concept_id=f"concept-{i}", label=course["topic"], description=chunk.text,
                    canonical_ranges=[CanonicalSourceRangeV1(source_artifact_id=chunk.source_artifact_id,
                        source_version=chunk.source_version, source_sha256=chunk.source_checksum or chunk.content_hash,
                        locator=chunk.locator, char_start=0, char_end=len(chunk.text))])],
                approved_by=course["professor"],
            ))
            policy = autonomy.set_policy(course["professor"], course["id"],
                approved_course_objectives=[course["objective"]], allowed_actions=actions, autonomy_enabled=True)
            releases[course["id"]] = release
            record(i * 3, "configuration", "Approved course release", course=course["id"],
                   data={"release_id": release.id, "profile_id": approved.profile_id,
                         "profile_sha256": approved.content_sha256, "policy": policy.model_dump(mode="json")})
        service = StudentTutoringService(repository, profile_path=PROFILE, tutoring_mode=TutoringMode.T1,
                                        evidence_gate=StructuredLexicalCoverageEvidenceGate(), clock=clock)
        conversations = {}
        for student in students:
            repository.save_account(Account(id=student["id"], role=AccountRole.STUDENT))
            repository.save_membership(CourseMembership(account_id=student["id"], course_id=student["course"],
                                                         role=MembershipRole.STUDENT))
            outreach.update_preference(student["id"], student["course"], channel=OutreachChannel.IN_APP,
                enabled=True, timezone="UTC", quiet_hours_start="23:00", quiet_hours_end="02:00",
                max_messages_per_7_days=3)
            conversation = service.create_conversation(student["id"], student["course"])
            conversations[student["id"]] = conversation
            record(7, "joined", "Separate conversation created", course=student["course"], student=student["id"],
                   data={"conversation_id": conversation.id})
        questions = [
            "What is cache coherence?",
            "What is virtual memory?",
            "What does a release policy define?",
            "What are approval and withdrawal controls in a release policy?",
        ]
        for index, (student, question) in enumerate(zip(students, questions, strict=True)):
            clock.advance_by(30)
            conversation = conversations[student["id"]]
            turn = await service.submit_message(student["id"], conversation.id, content=question,
                                                 client_request_id=f"recording-turn-{index}")
            state = repository.get_learner_state(conversation.id)
            record(11 + index * 6, "turn", "Course-grounded dialogue saved", course=student["course"],
                   student=student["id"], data={
                       "turn": turn.model_dump(mode="json"),
                       "state": state.model_dump(mode="json") if state else None,
                       "saved_message_count": len(repository.list_messages(conversation.id)),
                   })
        # Script the opportunities explicitly: do not imply that a mastery estimate scheduled them.
        opportunities = []
        for student, course_index in [(students[0], 0), (students[3], 1)]:
            course = courses[course_index]
            release = releases[course["id"]]
            goal = autonomy.create_goal(student_id=student["id"], course_id=course["id"],
                approved_course_objective=course["objective"], learner_subgoal=f"Recall {course['topic'].lower()}.",
                success_condition="Explain the approved source rule without a hint.",
                expires_at=(clock.now() + timedelta(days=7)).isoformat())
            opportunity = autonomy.create_opportunity(student_id=student["id"], course_id=course["id"],
                goal_id=goal.goal_id, event_kind=AutonomousEventKind.SPACED_REVIEW_DUE,
                concept_id=f"concept-{course_index}", source_chunk_id=release.chunks[0].id,
                earliest_action_at=(clock.now() + timedelta(days=1)).isoformat(),
                latest_action_at=(clock.now() + timedelta(days=1, hours=1)).isoformat(),
                idempotency_key=f"recording-practice-{course_index}")
            opportunities.append((student, opportunity))
            record(36, "scheduled", "Practice opportunity scheduled by the demo", course=course["id"],
                   student=student["id"], data={"opportunity": opportunity.model_dump(mode="json")})
        clock.advance_by(86400)
        record(40, "clock", "Virtual clock advances by one day")
        course = courses[1]
        paused = autonomy.set_policy(course["professor"], course["id"],
            approved_course_objectives=[course["objective"]], allowed_actions=actions,
            autonomy_enabled=True, paused=True)
        record(44, "paused", "Professor B pauses continuing support", course=course["id"],
               data={"policy": paused.model_dump(mode="json")})
        results = await autonomy.process_due(worker_id="recording-worker", now=clock.now())
        for student, opportunity in opportunities:
            inbox = outreach.list_inbox(student["id"], course_id=student["course"])
            stored = repository.get_autonomous_opportunity(opportunity.opportunity_id)
            record(48 if student["id"] == students[0]["id"] else 53, "support",
                   "Practice delivered" if inbox else "No practice delivered",
                   course=student["course"], student=student["id"],
                   data={"inbox": [item.model_dump(mode="json") for item in inbox],
                         "opportunity": stored.model_dump(mode="json"),
                         "results": [r.model_dump(mode="json") for r in results
                                     if r.opportunity_id == opportunity.opportunity_id]})
        repeated = await autonomy.process_due(worker_id="recording-worker-retry", now=clock.now())
        record(57, "retry", "Worker retry: no additional delivery",
               data={"results": [r.model_dump(mode="json") for r in repeated],
                     "inbox_counts": {s["id"]: len(outreach.list_inbox(s["id"])) for s in students}})
        return {
            "schema_version": 1, "duration": 60, "courses": courses, "students": students,
            "events": sorted(events, key=lambda event: event["at"]),
            "provenance": {
                "source": "Actual domain services in one isolated SQLite store; sequential synthetic actions.",
                "mode": "Deterministic baseline replay", "tutoring_mode": TutoringMode.T1,
                "limitations": "Not a live concurrent-load test, teaching-style comparison, or learning-effect evaluation. Opportunities are scripted; presentation time is compressed.",
                "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
                "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "profile_sha256": hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
                "profile_path": str(PROFILE.relative_to(ROOT)),
                "generated_at": datetime.now(UTC).isoformat(),
            },
        }
    finally:
        repository.close()


def main():
    with tempfile.TemporaryDirectory(prefix="digital-twin-recording-") as directory:
        trace = asyncio.run(build_trace(Path(directory) / "demo.sqlite3"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(trace['events'])} service events to {OUTPUT}")


if __name__ == "__main__":
    main()
