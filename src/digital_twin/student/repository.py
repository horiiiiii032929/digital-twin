from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Protocol

from src.digital_twin.grounding.models import DocumentChunk, GenerationTrace
from src.digital_twin.student.learning_gap import (
    LearningGapSignalV1,
    normalize_learning_gap_timestamp,
)
from src.digital_twin.student.autonomy_models import (
    AgentTraceV2,
    AutonomousActionStatus,
    AutonomousActionV1,
    AutonomousGoalStatus,
    AutonomousGoalV1,
    AutonomousOutcomeKind,
    AutonomousOutcomeV1,
    AutonomousOpportunityStatus,
    AutonomousWakeUpV1,
    CourseDomainModelV1,
    CourseTutoringRuntimeProfileV1,
    GroundedTutorResponseV2,
    LearnerBeliefStateV2,
    LearnerObservationV2,
    LearnerStateDeltaV2,
    PedagogicalPlanV2,
    PedagogicalPolicyV2,
    ProactiveOpportunityV1,
    ReactiveTurnArtifactsV2,
)
from src.digital_twin.student.autonomy_runtime import AutonomousJobResult
from src.digital_twin.student.models import (
    Account,
    AccountRole,
    AccountStatus,
    AuditEvent,
    Citation,
    Conversation,
    Course,
    CourseMembership,
    DeliveryOutboxItem,
    DigitalTwinRelease,
    NoEvidenceTurn,
    Message,
    MembershipRole,
    OutreachChannel,
    OutreachPreference,
    ProactiveMessage,
    ProactiveMessageStatus,
    ProactiveTrigger,
    ProactiveTriggerStatus,
    ReleaseEvaluationStatus,
    StudentReleaseStatus,
)
from src.digital_twin.student.migrations import apply_migrations
from src.digital_twin.student.tutoring_graph import LearnerState
from src.digital_twin.student.teaching_profile import (
    TeachingProfileStatus,
    TeachingProfileV1,
)
from src.digital_twin.tutor_policy import TutorPolicy, timestamp_now


class DuplicateTurnError(RuntimeError):
    """A concurrent request already claimed the conversation request ID."""


class LearnerStateConflictError(RuntimeError):
    """The durable learner state advanced before this turn could commit."""


class StudentRepository(Protocol):
    def save_account(self, account: Account) -> Account: ...

    def save_course(self, course: Course) -> Course: ...

    def save_course_with_owner(
        self, course: Course, membership: CourseMembership
    ) -> Course: ...

    def save_membership(self, membership: CourseMembership) -> CourseMembership: ...

    def save_release(self, release: DigitalTwinRelease) -> DigitalTwinRelease: ...

    def get_account(self, account_id: str) -> Account | None: ...

    def get_course(self, course_id: str) -> Course | None: ...

    def get_membership(
        self, account_id: str, course_id: str
    ) -> CourseMembership | None: ...

    def get_release(self, release_id: str) -> DigitalTwinRelease | None: ...

    def get_published_release(self, course_id: str) -> DigitalTwinRelease | None: ...

    def list_student_courses(
        self, account_id: str
    ) -> list[tuple[Course, DigitalTwinRelease]]: ...

    def list_professor_courses(self, account_id: str) -> list[Course]: ...

    def list_course_memberships(self, course_id: str) -> list[CourseMembership]: ...

    def list_course_releases(self, course_id: str) -> list[DigitalTwinRelease]: ...

    def save_conversation(self, conversation: Conversation) -> Conversation: ...

    def get_conversation(self, conversation_id: str) -> Conversation | None: ...

    def list_course_conversations(self, course_id: str) -> list[Conversation]: ...

    def get_learner_state(self, conversation_id: str) -> LearnerState | None: ...

    def save_course_domain_model(
        self, model: CourseDomainModelV1
    ) -> CourseDomainModelV1: ...

    def get_course_domain_model(
        self, release_id: str
    ) -> CourseDomainModelV1 | None: ...

    def save_course_tutoring_runtime_profile(
        self, profile: CourseTutoringRuntimeProfileV1
    ) -> CourseTutoringRuntimeProfileV1: ...

    def get_course_tutoring_runtime_profile(
        self, course_id: str
    ) -> CourseTutoringRuntimeProfileV1 | None: ...

    def get_learner_belief_state_v2(
        self, conversation_id: str
    ) -> LearnerBeliefStateV2 | None: ...

    def list_learner_observations_v2(
        self, conversation_id: str
    ) -> list[LearnerObservationV2]: ...

    def list_learner_state_deltas_v2(
        self, conversation_id: str
    ) -> list[LearnerStateDeltaV2]: ...

    def list_pedagogical_plans_v2(
        self, conversation_id: str
    ) -> list[PedagogicalPlanV2]: ...

    def list_grounded_responses_v2(
        self, conversation_id: str
    ) -> list[GroundedTutorResponseV2]: ...

    def list_agent_traces_v2(
        self, course_id: str, *, conversation_id: str | None = None
    ) -> list[AgentTraceV2]: ...

    def save_learning_gap_signal(self, signal: LearningGapSignalV1) -> bool: ...

    def list_learning_gap_signals(
        self, course_id: str, release_id: str, *, active_at: str
    ) -> list[LearningGapSignalV1]: ...

    def delete_expired_learning_gap_signals(self, *, expired_at: str) -> int: ...

    def save_teaching_profile(self, profile: TeachingProfileV1) -> TeachingProfileV1: ...

    def get_teaching_profile(self, profile_id: str) -> TeachingProfileV1 | None: ...

    def list_teaching_profiles(self, course_id: str) -> list[TeachingProfileV1]: ...

    def set_teaching_profile_status(
        self,
        profile_id: str,
        status: TeachingProfileStatus,
        *,
        preview_sha256: str | None,
        changed_at: str,
    ) -> TeachingProfileV1: ...

    def list_messages(self, conversation_id: str) -> list[Message]: ...

    def list_no_evidence_turns(
        self,
        course_id: str,
        *,
        excluding_release_id: str,
        limit: int = 100,
    ) -> list[NoEvidenceTurn]: ...

    def get_message(self, message_id: str) -> Message | None: ...

    def find_turn(
        self, conversation_id: str, client_request_id: str
    ) -> tuple[Message, Message, list[Citation]] | None: ...

    def save_turn(
        self,
        conversation: Conversation,
        student_message: Message,
        tutor_message: Message,
        citations: list[Citation],
        audit_events: list[AuditEvent],
        learner_state: LearnerState | None = None,
        expected_learner_state_revision: int | None = None,
        learning_gap_signal: LearningGapSignalV1 | None = None,
        autonomous_opportunity: ProactiveOpportunityV1 | None = None,
        responding_to_outreach_message_id: str | None = None,
        completed_autonomous_goal_ids: list[str] | None = None,
        reactive_v2_artifacts: ReactiveTurnArtifactsV2 | None = None,
    ) -> None: ...

    def list_citations(self, message_id: str) -> list[Citation]: ...

    def save_audit_event(self, event: AuditEvent) -> AuditEvent: ...

    def list_audit_events(self) -> list[AuditEvent]: ...

    def set_release_status(
        self, release_id: str, status: StudentReleaseStatus
    ) -> None: ...

    def set_release_evaluation_status(
        self, release_id: str, status: ReleaseEvaluationStatus
    ) -> None: ...

    def publish_release(self, release_id: str) -> None: ...

    def save_outreach_preference(
        self, preference: OutreachPreference
    ) -> OutreachPreference: ...

    def get_outreach_preference(
        self, student_id: str, course_id: str, channel: OutreachChannel
    ) -> OutreachPreference | None: ...

    def list_outreach_preferences(
        self, student_id: str, course_id: str
    ) -> list[OutreachPreference]: ...

    def save_proactive_trigger(self, trigger: ProactiveTrigger) -> ProactiveTrigger: ...

    def get_proactive_trigger(self, trigger_id: str) -> ProactiveTrigger | None: ...

    def find_proactive_trigger_by_key(
        self, idempotency_key: str
    ) -> ProactiveTrigger | None: ...

    def list_proactive_triggers(self, course_id: str) -> list[ProactiveTrigger]: ...

    def list_due_proactive_triggers(
        self, due_at: str, *, limit: int = 100
    ) -> list[ProactiveTrigger]: ...

    def set_proactive_trigger_status(
        self,
        trigger_id: str,
        status: ProactiveTriggerStatus,
        *,
        suppression_reason: str | None,
        updated_at: str,
    ) -> ProactiveTrigger: ...

    def materialize_proactive_message(
        self,
        trigger: ProactiveTrigger,
        message: ProactiveMessage,
        citations: list[Citation],
        outbox_item: DeliveryOutboxItem | None,
        audit_event: AuditEvent,
    ) -> bool: ...

    def get_proactive_message(
        self, message_id: str
    ) -> ProactiveMessage | None: ...

    def get_proactive_message_for_trigger(
        self, trigger_id: str
    ) -> ProactiveMessage | None: ...

    def list_proactive_messages(
        self, student_id: str, *, course_id: str | None = None
    ) -> list[ProactiveMessage]: ...

    def list_proactive_citations(self, message_id: str) -> list[Citation]: ...

    def set_proactive_message_status(
        self,
        message_id: str,
        status: ProactiveMessageStatus,
        *,
        changed_at: str,
    ) -> ProactiveMessage: ...

    def count_recent_proactive_messages(
        self,
        student_id: str,
        course_id: str,
        *,
        since: str,
    ) -> int: ...

    def list_delivery_outbox(self) -> list[DeliveryOutboxItem]: ...

    def save_autonomy_policy(self, policy: PedagogicalPolicyV2) -> PedagogicalPolicyV2: ...

    def get_autonomy_policy(self, course_id: str) -> PedagogicalPolicyV2 | None: ...

    def list_autonomy_policies(self) -> list[PedagogicalPolicyV2]: ...

    def save_autonomous_goal(self, goal: AutonomousGoalV1) -> AutonomousGoalV1: ...

    def get_autonomous_goal(self, goal_id: str) -> AutonomousGoalV1 | None: ...

    def list_autonomous_goals(
        self, student_id: str, course_id: str, *, active_only: bool = False
    ) -> list[AutonomousGoalV1]: ...

    def set_autonomous_goal_status(
        self,
        goal_id: str,
        status: AutonomousGoalStatus,
        *,
        changed_at: str,
    ) -> AutonomousGoalV1: ...

    def save_autonomous_opportunity(
        self, opportunity: ProactiveOpportunityV1
    ) -> ProactiveOpportunityV1: ...

    def get_autonomous_opportunity(
        self, opportunity_id: str
    ) -> ProactiveOpportunityV1 | None: ...

    def get_autonomous_opportunity_by_key(
        self, idempotency_key: str
    ) -> ProactiveOpportunityV1 | None: ...

    def list_due_autonomous_opportunities(
        self, due_at: str, *, limit: int = 100
    ) -> list[ProactiveOpportunityV1]: ...

    def list_due_autonomous_wakeups(
        self, due_at: str, *, limit: int = 100
    ) -> list[AutonomousWakeUpV1]: ...

    def materialize_autonomous_wakeup(
        self,
        wake_up_id: str,
        opportunity: ProactiveOpportunityV1,
        *,
        fired_at: str,
    ) -> bool: ...

    def claim_autonomous_opportunity(
        self,
        opportunity_id: str,
        *,
        lease_owner: str,
        acquired_at: str,
        lease_expires_at: str,
    ) -> ProactiveOpportunityV1 | None: ...

    def commit_autonomous_job(self, result: AutonomousJobResult) -> None: ...

    def bind_autonomous_action_trigger(
        self,
        action_id: str,
        *,
        trigger_id: str,
        status: AutonomousActionStatus,
        updated_at: str,
    ) -> AutonomousActionV1: ...

    def list_autonomous_actions(
        self, course_id: str, *, student_id: str | None = None
    ) -> list[AutonomousActionV1]: ...

    def get_autonomous_outcome(
        self, action_id: str
    ) -> AutonomousOutcomeV1 | None: ...

    def list_autonomous_outcomes(
        self, course_id: str, *, student_id: str | None = None
    ) -> list[AutonomousOutcomeV1]: ...

    def expire_autonomous_goals(self, *, expired_at: str) -> int: ...

    def expire_autonomous_opportunities(self, *, expired_at: str) -> int: ...

    def cancel_autonomy_scope(
        self,
        *,
        student_id: str | None = None,
        course_id: str,
        release_id: str | None = None,
        changed_at: str,
    ) -> int: ...


class SQLiteStudentRepository:
    """Small local repository with restart-surviving, transaction-safe turns."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        if self.path != ":memory:":
            self._connection.execute("PRAGMA journal_mode = WAL")
        self._initialize()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def healthcheck(self) -> bool:
        with self._lock:
            return self._connection.execute("SELECT 1").fetchone()[0] == 1

    def _initialize(self) -> None:
        with self._lock:
            apply_migrations(self._connection)

    def save_account(self, account: Account) -> Account:
        account = Account.model_validate(account.model_dump(mode="python"))
        with self._lock, self._connection:
            existing = self._connection.execute(
                "SELECT role FROM accounts WHERE id = ?", (account.id,)
            ).fetchone()
            if existing is not None and existing["role"] != account.role.value:
                raise ValueError("account role is immutable")
            self._connection.execute(
                """INSERT INTO accounts(id, role, status) VALUES (?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     role = excluded.role,
                     status = excluded.status""",
                (account.id, account.role.value, account.status.value),
            )
            if (
                account.role == AccountRole.STUDENT
                and account.status != AccountStatus.ACTIVE
            ):
                course_rows = self._connection.execute(
                    "SELECT course_id FROM memberships WHERE account_id = ?",
                    (account.id,),
                ).fetchall()
                for row in course_rows:
                    self._cancel_autonomy_scope_sql(
                        student_id=account.id,
                        course_id=str(row["course_id"]),
                        release_id=None,
                        changed_at=timestamp_now(),
                    )
        return account.model_copy(deep=True)

    def save_course(self, course: Course) -> Course:
        course = Course.model_validate(course.model_dump(mode="python"))
        with self._lock, self._connection:
            existing = self._connection.execute(
                "SELECT owner_professor_id FROM courses WHERE id = ?", (course.id,)
            ).fetchone()
            if (
                existing is not None
                and existing["owner_professor_id"] != course.owner_professor_id
            ):
                raise ValueError("course ownership is immutable")
            self._validate_course_owner(course)
            self._connection.execute(
                """INSERT INTO courses(id, title, owner_professor_id)
                   VALUES (?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     title = excluded.title,
                     owner_professor_id = excluded.owner_professor_id""",
                (course.id, course.title, course.owner_professor_id),
            )
        return course.model_copy(deep=True)

    def save_course_with_owner(
        self, course: Course, membership: CourseMembership
    ) -> Course:
        course = Course.model_validate(course.model_dump(mode="python"))
        membership = CourseMembership.model_validate(
            membership.model_dump(mode="python")
        )
        if (
            membership.account_id != course.owner_professor_id
            or membership.course_id != course.id
            or membership.role != MembershipRole.PROFESSOR
            or not membership.active
        ):
            raise ValueError("course owner membership is inconsistent")
        with self._lock, self._connection:
            self._validate_course_owner(course)
            if self._connection.execute(
                "SELECT 1 FROM courses WHERE id = ?", (course.id,)
            ).fetchone() is not None:
                raise ValueError("course identifier already exists")
            self._connection.execute(
                """INSERT INTO courses(id, title, owner_professor_id)
                   VALUES (?, ?, ?)""",
                (course.id, course.title, course.owner_professor_id),
            )
            self._connection.execute(
                """INSERT INTO memberships(account_id, course_id, role, active)
                   VALUES (?, ?, ?, ?)""",
                (
                    membership.account_id,
                    membership.course_id,
                    membership.role.value,
                    int(membership.active),
                ),
            )
        return course.model_copy(deep=True)

    def save_membership(self, membership: CourseMembership) -> CourseMembership:
        membership = CourseMembership.model_validate(
            membership.model_dump(mode="python")
        )
        with self._lock, self._connection:
            account = self._connection.execute(
                "SELECT role FROM accounts WHERE id = ?", (membership.account_id,)
            ).fetchone()
            course = self._connection.execute(
                "SELECT owner_professor_id FROM courses WHERE id = ?",
                (membership.course_id,),
            ).fetchone()
            expected_role = {
                MembershipRole.PROFESSOR: AccountRole.PROFESSOR.value,
                MembershipRole.STUDENT: AccountRole.STUDENT.value,
            }[membership.role]
            if account is None or course is None or account["role"] != expected_role:
                raise ValueError("membership account, course, and role are inconsistent")
            if (
                membership.role == MembershipRole.PROFESSOR
                and course["owner_professor_id"] != membership.account_id
            ):
                raise ValueError("only the course owner may hold professor membership")
            existing = self._connection.execute(
                """SELECT role FROM memberships
                   WHERE account_id = ? AND course_id = ?""",
                (membership.account_id, membership.course_id),
            ).fetchone()
            if existing is not None and existing["role"] != membership.role.value:
                raise ValueError("membership role is immutable")
            self._connection.execute(
                """INSERT INTO memberships
                   (account_id, course_id, role, active) VALUES (?, ?, ?, ?)
                   ON CONFLICT(account_id, course_id) DO UPDATE SET
                     role = excluded.role,
                     active = excluded.active""",
                (
                    membership.account_id,
                    membership.course_id,
                    membership.role.value,
                    int(membership.active),
                ),
            )
            if membership.role == MembershipRole.STUDENT and not membership.active:
                self._cancel_autonomy_scope_sql(
                    student_id=membership.account_id,
                    course_id=membership.course_id,
                    release_id=None,
                    changed_at=timestamp_now(),
                )
        return membership.model_copy(deep=True)

    def _validate_course_owner(self, course: Course) -> None:
        owner = self._connection.execute(
            "SELECT role, status FROM accounts WHERE id = ?",
            (course.owner_professor_id,),
        ).fetchone()
        if (
            owner is None
            or owner["role"] != AccountRole.PROFESSOR.value
            or owner["status"] != "active"
        ):
            raise ValueError("course owner must be an active professor")

    def save_release(self, release: DigitalTwinRelease) -> DigitalTwinRelease:
        release = DigitalTwinRelease.model_validate(release.model_dump(mode="python"))
        with self._lock, self._connection:
            try:
                self._connection.execute(
                    """INSERT INTO releases
                       (id, course_id, profile_id, profile_version, policy_version,
                        policy_json, teaching_profile_id, teaching_profile_sha256,
                        status, evaluation_status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        release.id,
                        release.course_id,
                        release.profile_id,
                        release.profile_version,
                        release.policy_version,
                        release.policy.model_dump_json(),
                        release.teaching_profile_id,
                        release.teaching_profile_sha256,
                        release.status.value,
                        release.evaluation_status.value,
                        release.created_at,
                    ),
                )
            except sqlite3.IntegrityError as error:
                if self._connection.execute(
                    "SELECT 1 FROM releases WHERE id = ?", (release.id,)
                ).fetchone():
                    raise ValueError(
                        "release content is immutable after creation"
                    ) from error
                raise
            self._connection.executemany(
                "INSERT INTO release_chunks(release_id, chunk_id, chunk_json) VALUES (?, ?, ?)",
                [
                    (release.id, chunk.id, chunk.model_dump_json())
                    for chunk in release.chunks
                ],
            )
        return release.model_copy(deep=True)

    def get_account(self, account_id: str) -> Account | None:
        row = self._one("SELECT * FROM accounts WHERE id = ?", (account_id,))
        return Account.model_validate(dict(row)) if row else None

    def get_course(self, course_id: str) -> Course | None:
        row = self._one("SELECT * FROM courses WHERE id = ?", (course_id,))
        return Course.model_validate(dict(row)) if row else None

    def get_membership(
        self, account_id: str, course_id: str
    ) -> CourseMembership | None:
        row = self._one(
            "SELECT * FROM memberships WHERE account_id = ? AND course_id = ?",
            (account_id, course_id),
        )
        if row is None:
            return None
        value = dict(row)
        value["active"] = bool(value["active"])
        return CourseMembership.model_validate(value)

    def get_release(self, release_id: str) -> DigitalTwinRelease | None:
        row = self._one("SELECT * FROM releases WHERE id = ?", (release_id,))
        return self._release(row) if row else None

    def get_published_release(self, course_id: str) -> DigitalTwinRelease | None:
        row = self._one(
            """SELECT * FROM releases
               WHERE course_id = ? AND status = ?
               ORDER BY created_at DESC, id DESC LIMIT 1""",
            (course_id, StudentReleaseStatus.PUBLISHED.value),
        )
        return self._release(row) if row else None

    def list_student_courses(
        self, account_id: str
    ) -> list[tuple[Course, DigitalTwinRelease]]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT c.* FROM courses c
                   JOIN memberships m ON m.course_id = c.id
                   WHERE m.account_id = ? AND m.role = 'student' AND m.active = 1
                   ORDER BY c.id""",
                (account_id,),
            ).fetchall()
        result: list[tuple[Course, DigitalTwinRelease]] = []
        for row in rows:
            course = Course.model_validate(dict(row))
            release = self.get_published_release(course.id)
            if release is not None:
                result.append((course, release))
        return result

    def list_professor_courses(self, account_id: str) -> list[Course]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT c.* FROM courses c
                   JOIN memberships m ON m.course_id = c.id
                   WHERE m.account_id = ? AND m.role = 'professor'
                     AND m.active = 1 AND c.owner_professor_id = ?
                   ORDER BY c.title, c.id""",
                (account_id, account_id),
            ).fetchall()
        return [Course.model_validate(dict(row)) for row in rows]

    def list_course_memberships(self, course_id: str) -> list[CourseMembership]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT * FROM memberships WHERE course_id = ?
                   ORDER BY role, account_id""",
                (course_id,),
            ).fetchall()
        memberships: list[CourseMembership] = []
        for row in rows:
            value = dict(row)
            value["active"] = bool(value["active"])
            memberships.append(CourseMembership.model_validate(value))
        return memberships

    def list_course_releases(self, course_id: str) -> list[DigitalTwinRelease]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT * FROM releases WHERE course_id = ?
                   ORDER BY created_at DESC, id DESC""",
                (course_id,),
            ).fetchall()
        return [self._release(row) for row in rows]

    def save_conversation(self, conversation: Conversation) -> Conversation:
        conversation = Conversation.model_validate(
            conversation.model_dump(mode="python")
        )
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO conversations
                   (id, student_id, course_id, release_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    conversation.id,
                    conversation.student_id,
                    conversation.course_id,
                    conversation.release_id,
                    conversation.created_at,
                    conversation.updated_at,
                ),
            )
        return conversation.model_copy(deep=True)

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        row = self._one("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        return Conversation.model_validate(dict(row)) if row else None

    def list_course_conversations(self, course_id: str) -> list[Conversation]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT * FROM conversations WHERE course_id = ?
                   ORDER BY updated_at DESC, id""",
                (course_id,),
            ).fetchall()
        return [Conversation.model_validate(dict(row)) for row in rows]

    def get_learner_state(self, conversation_id: str) -> LearnerState | None:
        row = self._one(
            "SELECT state_json FROM conversation_learner_states WHERE conversation_id = ?",
            (conversation_id,),
        )
        return LearnerState.model_validate_json(row["state_json"]) if row else None

    def save_course_domain_model(
        self, model: CourseDomainModelV1
    ) -> CourseDomainModelV1:
        model = CourseDomainModelV1.model_validate(model.model_dump(mode="python"))
        with self._lock, self._connection:
            release = self._connection.execute(
                "SELECT course_id FROM releases WHERE id = ?", (model.release_id,)
            ).fetchone()
            course = self._connection.execute(
                "SELECT owner_professor_id FROM courses WHERE id = ?", (model.course_id,)
            ).fetchone()
            if release is None or course is None:
                raise KeyError("domain_model_scope_not_found")
            if release["course_id"] != model.course_id:
                raise ValueError("domain model release has cross-course scope")
            if course["owner_professor_id"] != model.approved_by:
                raise ValueError("domain model must be approved by the course owner")
            existing = self._connection.execute(
                "SELECT model_json FROM course_domain_models WHERE release_id = ?",
                (model.release_id,),
            ).fetchone()
            if existing is not None:
                stored = CourseDomainModelV1.model_validate_json(existing["model_json"])
                if stored != model:
                    raise ValueError("release domain model is immutable")
                return stored
            self._connection.execute(
                """INSERT INTO course_domain_models
                   (domain_model_id, course_id, release_id, release_sha256,
                    version, model_json, approved_by, approved_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    model.domain_model_id,
                    model.course_id,
                    model.release_id,
                    model.release_sha256,
                    model.version,
                    model.model_dump_json(),
                    model.approved_by,
                    model.approved_at,
                ),
            )
        return model.model_copy(deep=True)

    def get_course_domain_model(
        self, release_id: str
    ) -> CourseDomainModelV1 | None:
        row = self._one(
            "SELECT model_json FROM course_domain_models WHERE release_id = ?",
            (release_id,),
        )
        return CourseDomainModelV1.model_validate_json(row["model_json"]) if row else None

    def save_course_tutoring_runtime_profile(
        self, profile: CourseTutoringRuntimeProfileV1
    ) -> CourseTutoringRuntimeProfileV1:
        profile = CourseTutoringRuntimeProfileV1.model_validate(
            profile.model_dump(mode="python")
        )
        with self._lock, self._connection:
            course = self._connection.execute(
                "SELECT owner_professor_id FROM courses WHERE id = ?",
                (profile.course_id,),
            ).fetchone()
            if course is None:
                raise KeyError("course_not_found")
            if course["owner_professor_id"] != profile.changed_by:
                raise ValueError("runtime profile must be changed by the course owner")
            existing = self._connection.execute(
                "SELECT version FROM course_tutoring_runtime_profiles WHERE course_id = ?",
                (profile.course_id,),
            ).fetchone()
            expected_version = 1 if existing is None else int(existing["version"]) + 1
            if profile.version != expected_version:
                raise ValueError("runtime profile version must advance exactly once")
            self._connection.execute(
                """INSERT INTO course_tutoring_runtime_profiles
                   (course_id, mode, version, profile_json, changed_by, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(course_id) DO UPDATE SET
                     mode = excluded.mode,
                     version = excluded.version,
                     profile_json = excluded.profile_json,
                     changed_by = excluded.changed_by,
                     updated_at = excluded.updated_at""",
                (
                    profile.course_id,
                    profile.mode,
                    profile.version,
                    profile.model_dump_json(),
                    profile.changed_by,
                    profile.updated_at,
                ),
            )
        return profile.model_copy(deep=True)

    def get_course_tutoring_runtime_profile(
        self, course_id: str
    ) -> CourseTutoringRuntimeProfileV1 | None:
        row = self._one(
            "SELECT profile_json FROM course_tutoring_runtime_profiles WHERE course_id = ?",
            (course_id,),
        )
        return (
            CourseTutoringRuntimeProfileV1.model_validate_json(row["profile_json"])
            if row
            else None
        )

    def get_learner_belief_state_v2(
        self, conversation_id: str
    ) -> LearnerBeliefStateV2 | None:
        row = self._one(
            "SELECT state_json FROM learner_belief_states_v2 WHERE conversation_id = ?",
            (conversation_id,),
        )
        return LearnerBeliefStateV2.model_validate_json(row["state_json"]) if row else None

    def list_learner_observations_v2(
        self, conversation_id: str
    ) -> list[LearnerObservationV2]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT observation_json FROM learner_observations_v2
                   WHERE conversation_id = ? ORDER BY observed_at, observation_id""",
                (conversation_id,),
            ).fetchall()
        return [
            LearnerObservationV2.model_validate_json(row["observation_json"])
            for row in rows
        ]

    def list_learner_state_deltas_v2(
        self, conversation_id: str
    ) -> list[LearnerStateDeltaV2]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT delta_json FROM learner_state_deltas_v2
                   WHERE conversation_id = ? ORDER BY next_revision""",
                (conversation_id,),
            ).fetchall()
        return [LearnerStateDeltaV2.model_validate_json(row["delta_json"]) for row in rows]

    def list_pedagogical_plans_v2(
        self, conversation_id: str
    ) -> list[PedagogicalPlanV2]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT plan_json FROM reactive_pedagogical_plans_v2
                   WHERE conversation_id = ? ORDER BY created_at, observation_id""",
                (conversation_id,),
            ).fetchall()
        return [PedagogicalPlanV2.model_validate_json(row["plan_json"]) for row in rows]

    def list_grounded_responses_v2(
        self, conversation_id: str
    ) -> list[GroundedTutorResponseV2]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT response_json FROM grounded_tutor_responses_v2
                   WHERE conversation_id = ? ORDER BY created_at, observation_id""",
                (conversation_id,),
            ).fetchall()
        return [
            GroundedTutorResponseV2.model_validate_json(row["response_json"])
            for row in rows
        ]

    def list_agent_traces_v2(
        self, course_id: str, *, conversation_id: str | None = None
    ) -> list[AgentTraceV2]:
        query = (
            """SELECT trace_json FROM tutoring_agent_traces_v2
               WHERE course_id = ? AND conversation_id = ? ORDER BY created_at DESC"""
            if conversation_id is not None
            else """SELECT trace_json FROM tutoring_agent_traces_v2
                     WHERE course_id = ? ORDER BY created_at DESC"""
        )
        parameters = (
            (course_id, conversation_id)
            if conversation_id is not None
            else (course_id,)
        )
        with self._lock:
            rows = self._connection.execute(query, parameters).fetchall()
        return [AgentTraceV2.model_validate_json(row["trace_json"]) for row in rows]

    def save_learning_gap_signal(self, signal: LearningGapSignalV1) -> bool:
        """Persist an idempotent privacy-minimized signal within its release scope."""

        signal = LearningGapSignalV1.model_validate(signal.model_dump(mode="python"))
        with self._lock, self._connection:
            return self._insert_learning_gap_signal(signal)

    def _insert_learning_gap_signal(self, signal: LearningGapSignalV1) -> bool:
        """Insert inside the caller's transaction; the caller owns locking."""

        release = self._connection.execute(
            "SELECT course_id FROM releases WHERE id = ?", (signal.release_id,)
        ).fetchone()
        if release is None:
            raise KeyError("release_not_found")
        if release["course_id"] != signal.course_id:
            raise ValueError("learning-gap signal has cross-course release scope")
        existing = self._connection.execute(
            """SELECT signal_json FROM learning_gap_signals
               WHERE source_turn_key = ? AND topic_key = ? AND signal_kind = ?""",
            (signal.source_turn_key, signal.topic_key, signal.signal_kind.value),
        ).fetchone()
        if existing is not None:
            stored = LearningGapSignalV1.model_validate_json(existing["signal_json"])
            if stored != signal:
                raise ValueError("learning-gap signal idempotency conflict")
            return False
        try:
            self._connection.execute(
                """INSERT INTO learning_gap_signals
                   (signal_id, source_turn_key, learner_key, course_id,
                    release_id, topic_key, signal_kind, observed_at,
                    expires_at, signal_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    signal.signal_id,
                    signal.source_turn_key,
                    signal.learner_key,
                    signal.course_id,
                    signal.release_id,
                    signal.topic_key,
                    signal.signal_kind.value,
                    signal.observed_at,
                    signal.expires_at,
                    signal.model_dump_json(),
                ),
            )
        except sqlite3.IntegrityError as error:
            raise ValueError("learning-gap signal identifier conflict") from error
        return True

    def list_learning_gap_signals(
        self, course_id: str, release_id: str, *, active_at: str
    ) -> list[LearningGapSignalV1]:
        active_at = normalize_learning_gap_timestamp(active_at)
        with self._lock:
            release = self._connection.execute(
                "SELECT course_id FROM releases WHERE id = ?", (release_id,)
            ).fetchone()
            if release is None:
                raise KeyError("release_not_found")
            if release["course_id"] != course_id:
                raise ValueError("learning-gap query has cross-course release scope")
            rows = self._connection.execute(
                """SELECT signal_json FROM learning_gap_signals
                   WHERE course_id = ? AND release_id = ? AND expires_at > ?
                   ORDER BY observed_at, signal_id""",
                (course_id, release_id, active_at),
            ).fetchall()
        return [
            LearningGapSignalV1.model_validate_json(row["signal_json"])
            for row in rows
        ]

    def delete_expired_learning_gap_signals(self, *, expired_at: str) -> int:
        expired_at = normalize_learning_gap_timestamp(expired_at)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "DELETE FROM learning_gap_signals WHERE expires_at <= ?",
                (expired_at,),
            )
        return int(cursor.rowcount)

    def save_teaching_profile(self, profile: TeachingProfileV1) -> TeachingProfileV1:
        profile = TeachingProfileV1.model_validate(profile.model_dump(mode="python"))
        with self._lock, self._connection:
            course = self._connection.execute(
                "SELECT 1 FROM courses WHERE id = ?", (profile.course_id,)
            ).fetchone()
            if course is None:
                raise KeyError("course_not_found")
            existing = self._connection.execute(
                "SELECT profile_json FROM teaching_profiles WHERE profile_id = ?",
                (profile.profile_id,),
            ).fetchone()
            if existing is not None:
                stored = TeachingProfileV1.model_validate_json(existing["profile_json"])
                if stored != profile:
                    raise ValueError("teaching profile content is immutable")
                return stored
            self._connection.execute(
                """INSERT INTO teaching_profiles
                   (profile_id, course_id, version, status, content_sha256,
                    preview_sha256, profile_json, created_at, approved_at,
                    withdrawn_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    profile.profile_id,
                    profile.course_id,
                    profile.version,
                    profile.status.value,
                    profile.content_sha256,
                    profile.preview_sha256,
                    profile.model_dump_json(),
                    profile.created_at,
                    profile.approved_at,
                    profile.withdrawn_at,
                ),
            )
        return profile.model_copy(deep=True)

    def get_teaching_profile(self, profile_id: str) -> TeachingProfileV1 | None:
        row = self._one(
            "SELECT profile_json FROM teaching_profiles WHERE profile_id = ?",
            (profile_id,),
        )
        return TeachingProfileV1.model_validate_json(row["profile_json"]) if row else None

    def list_teaching_profiles(self, course_id: str) -> list[TeachingProfileV1]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT profile_json FROM teaching_profiles
                   WHERE course_id = ? ORDER BY version DESC""",
                (course_id,),
            ).fetchall()
        return [TeachingProfileV1.model_validate_json(row["profile_json"]) for row in rows]

    def set_teaching_profile_status(
        self,
        profile_id: str,
        status: TeachingProfileStatus,
        *,
        preview_sha256: str | None,
        changed_at: str,
    ) -> TeachingProfileV1:
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT profile_json FROM teaching_profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
            if row is None:
                raise KeyError("teaching_profile_not_found")
            profile = TeachingProfileV1.model_validate_json(row["profile_json"])
            allowed = {
                TeachingProfileStatus.DRAFT: {
                    TeachingProfileStatus.APPROVED,
                    TeachingProfileStatus.WITHDRAWN,
                },
                TeachingProfileStatus.APPROVED: {
                    TeachingProfileStatus.SUPERSEDED,
                    TeachingProfileStatus.WITHDRAWN,
                },
                TeachingProfileStatus.SUPERSEDED: set(),
                TeachingProfileStatus.WITHDRAWN: set(),
            }
            if status not in allowed[profile.status]:
                raise ValueError("teaching profile status transition is not allowed")
            updated = profile.model_copy(
                update={
                    "status": status,
                    "preview_sha256": (
                        preview_sha256
                        if status == TeachingProfileStatus.APPROVED
                        else profile.preview_sha256
                    ),
                    "approved_at": (
                        changed_at
                        if status == TeachingProfileStatus.APPROVED
                        else profile.approved_at
                    ),
                    "withdrawn_at": (
                        changed_at
                        if status == TeachingProfileStatus.WITHDRAWN
                        else profile.withdrawn_at
                    ),
                }
            )
            updated = TeachingProfileV1.model_validate(updated.model_dump(mode="python"))
            self._connection.execute(
                """UPDATE teaching_profiles SET status = ?, preview_sha256 = ?,
                   profile_json = ?, approved_at = ?, withdrawn_at = ?
                   WHERE profile_id = ?""",
                (
                    updated.status.value,
                    updated.preview_sha256,
                    updated.model_dump_json(),
                    updated.approved_at,
                    updated.withdrawn_at,
                    profile_id,
                ),
            )
        return updated

    def list_messages(self, conversation_id: str) -> list[Message]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT * FROM messages WHERE conversation_id = ?
                   ORDER BY created_at, rowid""",
                (conversation_id,),
            ).fetchall()
        return [self._message(row) for row in rows]

    def get_message(self, message_id: str) -> Message | None:
        row = self._one("SELECT * FROM messages WHERE id = ?", (message_id,))
        return self._message(row) if row else None

    def list_no_evidence_turns(
        self,
        course_id: str,
        *,
        excluding_release_id: str,
        limit: int = 100,
    ) -> list[NoEvidenceTurn]:
        if isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValueError("no-evidence turn limit must be between 1 and 500")
        with self._lock:
            rows = self._connection.execute(
                """SELECT student.id AS student_message_id,
                          tutor.id AS tutor_message_id,
                          conversation.id AS conversation_id,
                          conversation.student_id AS student_id,
                          conversation.course_id AS course_id,
                          conversation.release_id AS release_id,
                          student.content AS question,
                          tutor.created_at AS created_at
                   FROM messages AS tutor
                   JOIN messages AS student
                     ON student.id = tutor.response_to_message_id
                    AND student.role = 'student'
                   JOIN conversations AS conversation
                     ON conversation.id = tutor.conversation_id
                   WHERE tutor.role = 'tutor'
                     AND tutor.action = 'no-evidence'
                     AND conversation.course_id = ?
                     AND conversation.release_id != ?
                   ORDER BY tutor.created_at, tutor.rowid
                   LIMIT ?""",
                (course_id, excluding_release_id, limit),
            ).fetchall()
        return [NoEvidenceTurn.model_validate(dict(row)) for row in rows]

    def find_turn(
        self, conversation_id: str, client_request_id: str
    ) -> tuple[Message, Message, list[Citation]] | None:
        student_row = self._one(
            """SELECT * FROM messages
               WHERE conversation_id = ? AND client_request_id = ? AND role = 'student'""",
            (conversation_id, client_request_id),
        )
        if student_row is None:
            return None
        student_message = self._message(student_row)
        tutor_row = self._one(
            "SELECT * FROM messages WHERE response_to_message_id = ? AND role = 'tutor'",
            (student_message.id,),
        )
        if tutor_row is None:
            return None
        tutor_message = self._message(tutor_row)
        return student_message, tutor_message, self.list_citations(tutor_message.id)

    def save_turn(
        self,
        conversation: Conversation,
        student_message: Message,
        tutor_message: Message,
        citations: list[Citation],
        audit_events: list[AuditEvent],
        learner_state: LearnerState | None = None,
        expected_learner_state_revision: int | None = None,
        learning_gap_signal: LearningGapSignalV1 | None = None,
        autonomous_opportunity: ProactiveOpportunityV1 | None = None,
        responding_to_outreach_message_id: str | None = None,
        completed_autonomous_goal_ids: list[str] | None = None,
        reactive_v2_artifacts: ReactiveTurnArtifactsV2 | None = None,
    ) -> None:
        conversation = Conversation.model_validate(
            conversation.model_dump(mode="python")
        )
        student_message = Message.model_validate(
            student_message.model_dump(mode="python")
        )
        tutor_message = Message.model_validate(tutor_message.model_dump(mode="python"))
        citations = [
            Citation.model_validate(citation.model_dump(mode="python"))
            for citation in citations
        ]
        audit_events = [
            AuditEvent.model_validate(event.model_dump(mode="python"))
            for event in audit_events
        ]
        if learning_gap_signal is not None:
            learning_gap_signal = LearningGapSignalV1.model_validate(
                learning_gap_signal.model_dump(mode="python")
            )
            if (
                learning_gap_signal.course_id != conversation.course_id
                or learning_gap_signal.release_id != conversation.release_id
            ):
                raise ValueError("learning-gap signal has inconsistent turn scope")
        if autonomous_opportunity is not None:
            autonomous_opportunity = ProactiveOpportunityV1.model_validate(
                autonomous_opportunity.model_dump(mode="python")
            )
            if (
                autonomous_opportunity.student_id != conversation.student_id
                or autonomous_opportunity.course_id != conversation.course_id
                or autonomous_opportunity.release_id != conversation.release_id
            ):
                raise ValueError("autonomous opportunity has inconsistent turn scope")
        completed_autonomous_goal_ids = completed_autonomous_goal_ids or []
        if len(completed_autonomous_goal_ids) != len(set(completed_autonomous_goal_ids)):
            raise ValueError("completed autonomous goal IDs must be unique")
        completed_goals: list[AutonomousGoalV1] = []
        for goal_id in completed_autonomous_goal_ids:
            goal = self.get_autonomous_goal(goal_id)
            if (
                goal is None
                or goal.student_id != conversation.student_id
                or goal.course_id != conversation.course_id
                or goal.release_id != conversation.release_id
                or goal.status != AutonomousGoalStatus.ACTIVE
            ):
                raise ValueError("completed autonomous goal has inconsistent turn scope")
            completed_goals.append(goal)
        if learner_state is not None:
            learner_state = LearnerState.model_validate(
                learner_state.model_dump(mode="python")
            )
            if (
                learner_state.conversation_id != conversation.id
                or learner_state.course_id != conversation.course_id
                or learner_state.release_id != conversation.release_id
                or expected_learner_state_revision is None
                or learner_state.revision != expected_learner_state_revision + 1
            ):
                raise ValueError("learner state has inconsistent turn lineage")
        elif expected_learner_state_revision is not None:
            raise ValueError("learner state revision requires learner state")
        if reactive_v2_artifacts is not None:
            reactive_v2_artifacts = ReactiveTurnArtifactsV2.model_validate(
                reactive_v2_artifacts.model_dump(mode="python")
            )
            if (
                reactive_v2_artifacts.conversation_id != conversation.id
                or reactive_v2_artifacts.observation.course_id != conversation.course_id
                or reactive_v2_artifacts.observation.release_id != conversation.release_id
                or reactive_v2_artifacts.trace.event_id
                != reactive_v2_artifacts.observation.observation_id
            ):
                raise ValueError("reactive V2 artifacts have inconsistent turn scope")
        response_message: ProactiveMessage | None = None
        response_action: AutonomousActionV1 | None = None
        if responding_to_outreach_message_id is not None:
            response_message = self.get_proactive_message(
                responding_to_outreach_message_id
            )
            if (
                response_message is None
                or response_message.student_id != conversation.student_id
                or response_message.course_id != conversation.course_id
                or response_message.release_id != conversation.release_id
            ):
                raise ValueError("outreach response does not match the turn scope")
            response_action = self._autonomous_action_for_trigger(
                response_message.trigger_id
            )
        if (
            student_message.conversation_id != conversation.id
            or tutor_message.conversation_id != conversation.id
            or student_message.role != "student"
            or tutor_message.role != "tutor"
            or not student_message.client_request_id
            or tutor_message.response_to_message_id != student_message.id
            or any(
                citation.message_id != tutor_message.id
                or citation.course_id != conversation.course_id
                or citation.release_id != conversation.release_id
                for citation in citations
            )
        ):
            raise ValueError("tutor turn records have inconsistent lineage")
        try:
            with self._lock, self._connection:
                if learner_state is not None:
                    current = self._connection.execute(
                        """SELECT revision FROM conversation_learner_states
                           WHERE conversation_id = ?""",
                        (conversation.id,),
                    ).fetchone()
                    current_revision = int(current["revision"]) if current else 0
                    if current_revision != expected_learner_state_revision:
                        duplicate = self._connection.execute(
                            """SELECT 1 FROM messages
                               WHERE conversation_id = ? AND client_request_id = ?""",
                            (conversation.id, student_message.client_request_id),
                        ).fetchone()
                        if duplicate is not None:
                            raise DuplicateTurnError
                        raise LearnerStateConflictError
                if reactive_v2_artifacts is not None:
                    current_v2 = self._connection.execute(
                        """SELECT revision FROM learner_belief_states_v2
                           WHERE conversation_id = ?""",
                        (conversation.id,),
                    ).fetchone()
                    current_v2_revision = int(current_v2["revision"]) if current_v2 else 0
                    expected_v2_revision = reactive_v2_artifacts.trace.input_state_revision
                    if current_v2_revision != expected_v2_revision:
                        duplicate = self._connection.execute(
                            """SELECT 1 FROM messages
                               WHERE conversation_id = ? AND client_request_id = ?""",
                            (conversation.id, student_message.client_request_id),
                        ).fetchone()
                        if duplicate is not None:
                            raise DuplicateTurnError
                        raise LearnerStateConflictError
                self._insert_message(student_message)
                self._insert_message(tutor_message)
                self._connection.executemany(
                    """INSERT INTO citations
                       (id, message_id, course_id, release_id, source_artifact_id,
                        source_document_id, source_version, title, locator,
                        source_checksum, page, region_id, region_kind,
                        bounding_box_json, crop_ref)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        (
                            citation.id,
                            citation.message_id,
                            citation.course_id,
                            citation.release_id,
                            citation.source_artifact_id,
                            citation.source_document_id,
                            citation.source_version,
                            citation.title,
                            citation.locator,
                            citation.source_checksum,
                            citation.page,
                            citation.region_id,
                            citation.region_kind,
                            (
                                json.dumps(citation.bounding_box)
                                if citation.bounding_box is not None
                                else None
                            ),
                            citation.crop_ref,
                        )
                        for citation in citations
                    ],
                )
                for event in audit_events:
                    self._insert_audit_event(event)
                if learner_state is not None:
                    self._connection.execute(
                        """INSERT INTO conversation_learner_states
                           (conversation_id, course_id, release_id, revision,
                            state_json, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?)
                           ON CONFLICT(conversation_id) DO UPDATE SET
                             course_id = excluded.course_id,
                             release_id = excluded.release_id,
                             revision = excluded.revision,
                             state_json = excluded.state_json,
                             updated_at = excluded.updated_at""",
                        (
                            learner_state.conversation_id,
                            learner_state.course_id,
                            learner_state.release_id,
                            learner_state.revision,
                            learner_state.model_dump_json(),
                            learner_state.updated_at,
                        ),
                    )
                if reactive_v2_artifacts is not None:
                    self._insert_reactive_v2_artifacts(
                        conversation.id,
                        reactive_v2_artifacts,
                    )
                if learning_gap_signal is not None:
                    self._insert_learning_gap_signal(learning_gap_signal)
                if autonomous_opportunity is not None:
                    self._insert_autonomous_opportunity(autonomous_opportunity)
                for goal in completed_goals:
                    completed = goal.model_copy(
                        update={
                            "status": AutonomousGoalStatus.COMPLETED,
                            "updated_at": conversation.updated_at,
                        }
                    )
                    self._connection.execute(
                        """UPDATE autonomous_goals
                           SET status = ?, goal_json = ?, updated_at = ?
                           WHERE goal_id = ? AND status = ?""",
                        (
                            AutonomousGoalStatus.COMPLETED.value,
                            completed.model_dump_json(),
                            conversation.updated_at,
                            goal.goal_id,
                            AutonomousGoalStatus.ACTIVE.value,
                        ),
                    )
                    self._set_goal_opportunities_status(
                        goal.goal_id,
                        AutonomousOpportunityStatus.CANCELLED,
                        changed_at=conversation.updated_at,
                    )
                    self._connection.execute(
                        """UPDATE autonomous_wakeups SET status = 'cancelled'
                           WHERE goal_id = ? AND status = 'pending'""",
                        (goal.goal_id,),
                    )
                if response_message is not None:
                    self._link_autonomous_response(
                        response_message=response_message,
                        student_message=student_message,
                        action=response_action,
                        learner_state=learner_state,
                        linked_at=conversation.updated_at,
                    )
                self._connection.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?",
                    (conversation.updated_at, conversation.id),
                )
        except sqlite3.IntegrityError as error:
            if "messages.conversation_id, messages.client_request_id" in str(error):
                raise DuplicateTurnError from error
            raise

    def _insert_reactive_v2_artifacts(
        self,
        conversation_id: str,
        artifacts: ReactiveTurnArtifactsV2,
    ) -> None:
        """Insert sanitized V2 records inside the caller-owned turn transaction."""

        observation = artifacts.observation
        belief = artifacts.belief_state
        delta = artifacts.state_delta
        trace = artifacts.trace
        self._connection.execute(
            """INSERT INTO learner_observations_v2
               (observation_id, conversation_id, learner_key, course_id,
                release_id, source_turn_key, observation_json, observed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                observation.observation_id,
                conversation_id,
                observation.learner_key,
                observation.course_id,
                observation.release_id,
                observation.source_turn_key,
                observation.model_dump_json(),
                observation.observed_at,
            ),
        )
        if artifacts.state_committed:
            assert belief is not None and delta is not None
            self._connection.execute(
                """INSERT INTO learner_belief_states_v2
               (conversation_id, learner_key, course_id, release_id, revision,
                state_json, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(conversation_id) DO UPDATE SET
                 learner_key = excluded.learner_key,
                 course_id = excluded.course_id,
                 release_id = excluded.release_id,
                 revision = excluded.revision,
                 state_json = excluded.state_json,
                 updated_at = excluded.updated_at""",
                (
                    conversation_id,
                    belief.learner_key,
                    belief.course_id,
                    belief.release_id,
                    belief.revision,
                    belief.model_dump_json(),
                    belief.updated_at,
                ),
            )
            self._connection.executemany(
                """INSERT INTO learner_concept_attributions_v2
               (conversation_id, revision, concept_id, attribution_json, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
                [
                    (
                        conversation_id,
                        belief.revision,
                        item.concept_id,
                        item.model_dump_json(),
                        belief.updated_at,
                    )
                    for item in belief.concepts
                ],
            )
            self._connection.execute(
                """INSERT INTO learner_state_deltas_v2
               (conversation_id, next_revision, observation_id, delta_json, created_at)
               VALUES (?, ?, ?, ?, ?)""",
                (
                    conversation_id,
                    delta.next_revision,
                    observation.observation_id,
                    delta.model_dump_json(),
                    belief.updated_at,
                ),
            )
        recorded_at = belief.updated_at if belief is not None else observation.observed_at
        self._connection.execute(
            """INSERT INTO reactive_pedagogical_plans_v2
               (observation_id, conversation_id, plan_json, created_at)
               VALUES (?, ?, ?, ?)""",
            (
                observation.observation_id,
                conversation_id,
                artifacts.plan.model_dump_json(),
                recorded_at,
            ),
        )
        self._connection.execute(
            """INSERT INTO grounded_tutor_responses_v2
               (observation_id, conversation_id, response_json, created_at)
               VALUES (?, ?, ?, ?)""",
            (
                observation.observation_id,
                conversation_id,
                artifacts.response.model_dump_json(),
                recorded_at,
            ),
        )
        self._connection.execute(
            """INSERT INTO tutoring_agent_traces_v2
               (trace_id, event_id, conversation_id, learner_key, course_id,
                release_id, graph_version, input_state_revision,
                output_state_revision, trace_json, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trace.trace_id,
                trace.event_id,
                conversation_id,
                trace.learner_key,
                trace.course_id,
                trace.release_id,
                trace.graph_version,
                trace.input_state_revision,
                trace.output_state_revision,
                trace.model_dump_json(),
                trace.started_at,
                trace.completed_at,
            ),
        )

    def list_citations(self, message_id: str) -> list[Citation]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM citations WHERE message_id = ? ORDER BY rowid",
                (message_id,),
            ).fetchall()
        return [self._citation(row) for row in rows]

    def save_audit_event(self, event: AuditEvent) -> AuditEvent:
        event = AuditEvent.model_validate(event.model_dump(mode="python"))
        with self._lock, self._connection:
            self._insert_audit_event(event)
        return event.model_copy(deep=True)

    def list_audit_events(self) -> list[AuditEvent]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM audit_events ORDER BY created_at, rowid"
            ).fetchall()
        return [self._audit_event(row) for row in rows]

    def save_outreach_preference(
        self, preference: OutreachPreference
    ) -> OutreachPreference:
        preference = OutreachPreference.model_validate(
            preference.model_dump(mode="python")
        )
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO outreach_preferences
                   (student_id, course_id, channel, enabled, timezone,
                    quiet_hours_start, quiet_hours_end, max_messages_per_7_days,
                    snoozed_until, destination_ref, private_destination, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(student_id, course_id, channel) DO UPDATE SET
                     enabled = excluded.enabled,
                     timezone = excluded.timezone,
                     quiet_hours_start = excluded.quiet_hours_start,
                     quiet_hours_end = excluded.quiet_hours_end,
                     max_messages_per_7_days = excluded.max_messages_per_7_days,
                     snoozed_until = excluded.snoozed_until,
                     destination_ref = excluded.destination_ref,
                     private_destination = excluded.private_destination,
                     updated_at = excluded.updated_at""",
                (
                    preference.student_id,
                    preference.course_id,
                    preference.channel.value,
                    int(preference.enabled),
                    preference.timezone,
                    preference.quiet_hours_start,
                    preference.quiet_hours_end,
                    preference.max_messages_per_7_days,
                    preference.snoozed_until,
                    preference.destination_ref,
                    int(preference.private_destination),
                    preference.updated_at,
                ),
            )
            if preference.channel == OutreachChannel.IN_APP and not preference.enabled:
                self._cancel_autonomy_scope_sql(
                    student_id=preference.student_id,
                    course_id=preference.course_id,
                    release_id=None,
                    changed_at=preference.updated_at,
                )
        return preference.model_copy(deep=True)

    def get_outreach_preference(
        self, student_id: str, course_id: str, channel: OutreachChannel
    ) -> OutreachPreference | None:
        row = self._one(
            """SELECT * FROM outreach_preferences
               WHERE student_id = ? AND course_id = ? AND channel = ?""",
            (student_id, course_id, channel.value),
        )
        return self._outreach_preference(row) if row else None

    def list_outreach_preferences(
        self, student_id: str, course_id: str
    ) -> list[OutreachPreference]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT * FROM outreach_preferences
                   WHERE student_id = ? AND course_id = ? ORDER BY channel""",
                (student_id, course_id),
            ).fetchall()
        return [self._outreach_preference(row) for row in rows]

    def save_proactive_trigger(self, trigger: ProactiveTrigger) -> ProactiveTrigger:
        trigger = ProactiveTrigger.model_validate(trigger.model_dump(mode="python"))
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO proactive_triggers
                   (id, idempotency_key, professor_id, student_id, course_id,
                    release_id, channel, kind, scheduled_for, expires_at, topic,
                    prompt, source_chunk_id, status, suppression_reason,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trigger.id,
                    trigger.idempotency_key,
                    trigger.professor_id,
                    trigger.student_id,
                    trigger.course_id,
                    trigger.release_id,
                    trigger.channel.value,
                    trigger.kind.value,
                    trigger.scheduled_for,
                    trigger.expires_at,
                    trigger.topic,
                    trigger.prompt,
                    trigger.source_chunk_id,
                    trigger.status.value,
                    trigger.suppression_reason,
                    trigger.created_at,
                    trigger.updated_at,
                ),
            )
        return trigger.model_copy(deep=True)

    def get_proactive_trigger(self, trigger_id: str) -> ProactiveTrigger | None:
        row = self._one("SELECT * FROM proactive_triggers WHERE id = ?", (trigger_id,))
        return ProactiveTrigger.model_validate(dict(row)) if row else None

    def find_proactive_trigger_by_key(
        self, idempotency_key: str
    ) -> ProactiveTrigger | None:
        row = self._one(
            "SELECT * FROM proactive_triggers WHERE idempotency_key = ?",
            (idempotency_key,),
        )
        return ProactiveTrigger.model_validate(dict(row)) if row else None

    def list_proactive_triggers(self, course_id: str) -> list[ProactiveTrigger]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT * FROM proactive_triggers
                   WHERE course_id = ? ORDER BY scheduled_for DESC, id""",
                (course_id,),
            ).fetchall()
        return [ProactiveTrigger.model_validate(dict(row)) for row in rows]

    def list_due_proactive_triggers(
        self, due_at: str, *, limit: int = 100
    ) -> list[ProactiveTrigger]:
        if limit < 1 or limit > 500:
            raise ValueError("proactive trigger limit must be between 1 and 500")
        with self._lock:
            rows = self._connection.execute(
                """SELECT * FROM proactive_triggers
                   WHERE status = ? AND scheduled_for <= ?
                   ORDER BY scheduled_for, id LIMIT ?""",
                (ProactiveTriggerStatus.PENDING.value, due_at, limit),
            ).fetchall()
        return [ProactiveTrigger.model_validate(dict(row)) for row in rows]

    def set_proactive_trigger_status(
        self,
        trigger_id: str,
        status: ProactiveTriggerStatus,
        *,
        suppression_reason: str | None,
        updated_at: str,
    ) -> ProactiveTrigger:
        if status == ProactiveTriggerStatus.PENDING:
            raise ValueError("terminal proactive trigger update cannot restore pending")
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """UPDATE proactive_triggers
                   SET status = ?, suppression_reason = ?, updated_at = ?
                   WHERE id = ? AND status = ?""",
                (
                    status.value,
                    suppression_reason,
                    updated_at,
                    trigger_id,
                    ProactiveTriggerStatus.PENDING.value,
                ),
            )
            if cursor.rowcount != 1:
                row = self._connection.execute(
                    "SELECT * FROM proactive_triggers WHERE id = ?", (trigger_id,)
                ).fetchone()
                if row is None:
                    raise KeyError("proactive_trigger_not_found")
        trigger = self.get_proactive_trigger(trigger_id)
        if trigger is None:
            raise KeyError("proactive_trigger_not_found")
        return trigger

    def materialize_proactive_message(
        self,
        trigger: ProactiveTrigger,
        message: ProactiveMessage,
        citations: list[Citation],
        outbox_item: DeliveryOutboxItem | None,
        audit_event: AuditEvent,
    ) -> bool:
        trigger = ProactiveTrigger.model_validate(trigger.model_dump(mode="python"))
        message = ProactiveMessage.model_validate(message.model_dump(mode="python"))
        citations = [
            Citation.model_validate(citation.model_dump(mode="python"))
            for citation in citations
        ]
        if outbox_item is not None:
            outbox_item = DeliveryOutboxItem.model_validate(
                outbox_item.model_dump(mode="python")
            )
        audit_event = AuditEvent.model_validate(audit_event.model_dump(mode="python"))
        if (
            message.trigger_id != trigger.id
            or message.student_id != trigger.student_id
            or message.course_id != trigger.course_id
            or message.release_id != trigger.release_id
            or message.channel != trigger.channel
            or not citations
            or any(
                citation.message_id != message.id
                or citation.course_id != message.course_id
                or citation.release_id != message.release_id
                for citation in citations
            )
            or (
                message.channel == OutreachChannel.IN_APP
                and (
                    outbox_item is not None
                    or message.status != ProactiveMessageStatus.DELIVERED
                )
            )
            or (
                message.channel == OutreachChannel.DISCORD
                and (
                    outbox_item is None
                    or outbox_item.message_id != message.id
                    or outbox_item.channel != message.channel
                    or message.status != ProactiveMessageStatus.QUEUED
                )
            )
        ):
            raise ValueError("proactive message records have inconsistent lineage")
        try:
            with self._lock, self._connection:
                current = self._connection.execute(
                    "SELECT status FROM proactive_triggers WHERE id = ?", (trigger.id,)
                ).fetchone()
                if current is None:
                    raise KeyError("proactive_trigger_not_found")
                if current["status"] != ProactiveTriggerStatus.PENDING.value:
                    return False
                self._connection.execute(
                    """INSERT INTO proactive_messages
                       (id, trigger_id, student_id, course_id, release_id, channel,
                        content, status, created_at, read_at, dismissed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        message.id,
                        message.trigger_id,
                        message.student_id,
                        message.course_id,
                        message.release_id,
                        message.channel.value,
                        message.content,
                        message.status.value,
                        message.created_at,
                        message.read_at,
                        message.dismissed_at,
                    ),
                )
                self._insert_proactive_citations(citations)
                if outbox_item is not None:
                    self._connection.execute(
                        """INSERT INTO proactive_delivery_outbox
                           (id, message_id, channel, destination_ref, status,
                            attempts, last_error, available_at, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            outbox_item.id,
                            outbox_item.message_id,
                            outbox_item.channel.value,
                            outbox_item.destination_ref,
                            outbox_item.status.value,
                            outbox_item.attempts,
                            outbox_item.last_error,
                            outbox_item.available_at,
                            outbox_item.created_at,
                            outbox_item.updated_at,
                        ),
                    )
                self._insert_audit_event(audit_event)
                self._connection.execute(
                    """UPDATE proactive_triggers
                       SET status = ?, updated_at = ? WHERE id = ?""",
                    (
                        ProactiveTriggerStatus.MATERIALIZED.value,
                        message.created_at,
                        trigger.id,
                    ),
                )
        except sqlite3.IntegrityError as error:
            if "proactive_messages.trigger_id" in str(error):
                return False
            raise
        return True

    def get_proactive_message(self, message_id: str) -> ProactiveMessage | None:
        row = self._one("SELECT * FROM proactive_messages WHERE id = ?", (message_id,))
        return ProactiveMessage.model_validate(dict(row)) if row else None

    def get_proactive_message_for_trigger(
        self, trigger_id: str
    ) -> ProactiveMessage | None:
        row = self._one(
            "SELECT * FROM proactive_messages WHERE trigger_id = ?", (trigger_id,)
        )
        return ProactiveMessage.model_validate(dict(row)) if row else None

    def list_proactive_messages(
        self, student_id: str, *, course_id: str | None = None
    ) -> list[ProactiveMessage]:
        sql = "SELECT * FROM proactive_messages WHERE student_id = ?"
        parameters: tuple[object, ...] = (student_id,)
        if course_id is not None:
            sql += " AND course_id = ?"
            parameters += (course_id,)
        sql += " ORDER BY created_at DESC, rowid DESC"
        with self._lock:
            rows = self._connection.execute(sql, parameters).fetchall()
        return [ProactiveMessage.model_validate(dict(row)) for row in rows]

    def list_proactive_citations(self, message_id: str) -> list[Citation]:
        with self._lock:
            rows = self._connection.execute(
                """SELECT * FROM proactive_citations
                   WHERE message_id = ? ORDER BY rowid""",
                (message_id,),
            ).fetchall()
        return [self._citation(row) for row in rows]

    def set_proactive_message_status(
        self,
        message_id: str,
        status: ProactiveMessageStatus,
        *,
        changed_at: str,
    ) -> ProactiveMessage:
        if status not in {
            ProactiveMessageStatus.READ,
            ProactiveMessageStatus.DISMISSED,
        }:
            raise ValueError("student message state may only become read or dismissed")
        column = "read_at" if status == ProactiveMessageStatus.READ else "dismissed_at"
        with self._lock, self._connection:
            message_row = self._connection.execute(
                "SELECT trigger_id FROM proactive_messages WHERE id = ?",
                (message_id,),
            ).fetchone()
            cursor = self._connection.execute(
                f"""UPDATE proactive_messages SET status = ?, {column} = ?
                    WHERE id = ? AND status IN (?, ?)""",
                (
                    status.value,
                    changed_at,
                    message_id,
                    ProactiveMessageStatus.DELIVERED.value,
                    ProactiveMessageStatus.READ.value,
                ),
            )
            if cursor.rowcount != 1:
                row = self._connection.execute(
                    "SELECT 1 FROM proactive_messages WHERE id = ?", (message_id,)
                ).fetchone()
                if row is None:
                    raise KeyError("proactive_message_not_found")
                raise ValueError("proactive message cannot change from its current state")
            if (
                status == ProactiveMessageStatus.DISMISSED
                and message_row is not None
            ):
                action = self._autonomous_action_for_trigger(
                    str(message_row["trigger_id"])
                )
                if action is not None:
                    outcome_row = self._connection.execute(
                        "SELECT outcome_json FROM autonomous_outcomes WHERE action_id = ?",
                        (action.action_id,),
                    ).fetchone()
                    if outcome_row is None:
                        raise ValueError("autonomous dismissal has no outcome")
                    outcome = AutonomousOutcomeV1.model_validate_json(
                        outcome_row["outcome_json"]
                    ).model_copy(
                        update={
                            "kind": AutonomousOutcomeKind.DISMISSED,
                            "next_wake_at": None,
                            "recorded_at": changed_at,
                        }
                    )
                    self._connection.execute(
                        """UPDATE autonomous_outcomes SET outcome_json = ?, recorded_at = ?
                           WHERE action_id = ?""",
                        (outcome.model_dump_json(), changed_at, action.action_id),
                    )
                    if action.goal_id is not None:
                        self._set_goal_opportunities_status(
                            action.goal_id,
                            AutonomousOpportunityStatus.CANCELLED,
                            changed_at=changed_at,
                        )
                        self._connection.execute(
                            """UPDATE autonomous_wakeups SET status = 'cancelled'
                               WHERE goal_id = ? AND status = 'pending'""",
                            (action.goal_id,),
                        )
        message = self.get_proactive_message(message_id)
        if message is None:
            raise KeyError("proactive_message_not_found")
        return message

    def count_recent_proactive_messages(
        self,
        student_id: str,
        course_id: str,
        *,
        since: str,
    ) -> int:
        row = self._one(
            """SELECT COUNT(*) AS count FROM proactive_messages
               WHERE student_id = ? AND course_id = ? AND created_at >= ?
                 AND status != ?""",
            (
                student_id,
                course_id,
                since,
                ProactiveMessageStatus.CANCELLED.value,
            ),
        )
        return int(row["count"]) if row else 0

    def list_delivery_outbox(self) -> list[DeliveryOutboxItem]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM proactive_delivery_outbox ORDER BY created_at, rowid"
            ).fetchall()
        return [DeliveryOutboxItem.model_validate(dict(row)) for row in rows]

    def save_autonomy_policy(
        self, policy: PedagogicalPolicyV2
    ) -> PedagogicalPolicyV2:
        policy = PedagogicalPolicyV2.model_validate(policy.model_dump(mode="python"))
        with self._lock, self._connection:
            course = self._connection.execute(
                "SELECT owner_professor_id FROM courses WHERE id = ?",
                (policy.course_id,),
            ).fetchone()
            profile = self._connection.execute(
                """SELECT status, content_sha256 FROM teaching_profiles
                   WHERE profile_id = ? AND course_id = ?""",
                (policy.approved_profile_id, policy.course_id),
            ).fetchone()
            if course is None or course["owner_professor_id"] != policy.approved_by:
                raise ValueError("autonomy policy requires the course owner")
            if (
                profile is None
                or profile["status"] != "approved"
                or profile["content_sha256"] != policy.approved_profile_sha256
            ):
                raise ValueError("autonomy policy requires the approved profile hash")
            current = self._connection.execute(
                "SELECT version, policy_json FROM autonomy_policies WHERE course_id = ?",
                (policy.course_id,),
            ).fetchone()
            if current is not None:
                stored_policy = PedagogicalPolicyV2.model_validate_json(
                    current["policy_json"]
                )
                if policy.version < int(current["version"]):
                    raise ValueError("autonomy policy version cannot decrease")
                if (
                    policy.version == int(current["version"])
                    and _autonomy_boundary_payload(policy)
                    != _autonomy_boundary_payload(stored_policy)
                ):
                    raise ValueError(
                        "autonomy boundary changes require a new policy version"
                    )
            self._connection.execute(
                """INSERT INTO autonomy_policies
                   (course_id, version, policy_json, updated_at) VALUES (?, ?, ?, ?)
                   ON CONFLICT(course_id) DO UPDATE SET
                     version = excluded.version,
                     policy_json = excluded.policy_json,
                     updated_at = excluded.updated_at""",
                (
                    policy.course_id,
                    policy.version,
                    policy.model_dump_json(),
                    policy.updated_at,
                ),
            )
            boundary_changed = bool(
                current is not None and policy.version != int(current["version"])
            )
            if (
                boundary_changed
                or policy.kill_switch
                or not policy.autonomy_enabled
            ):
                self._cancel_autonomy_scope_sql(
                    student_id=None,
                    course_id=policy.course_id,
                    release_id=None,
                    changed_at=policy.updated_at,
                )
        return policy.model_copy(deep=True)

    def get_autonomy_policy(self, course_id: str) -> PedagogicalPolicyV2 | None:
        row = self._one(
            "SELECT policy_json FROM autonomy_policies WHERE course_id = ?",
            (course_id,),
        )
        return PedagogicalPolicyV2.model_validate_json(row["policy_json"]) if row else None

    def list_autonomy_policies(self) -> list[PedagogicalPolicyV2]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT policy_json FROM autonomy_policies ORDER BY course_id"
            ).fetchall()
        return [
            PedagogicalPolicyV2.model_validate_json(row["policy_json"])
            for row in rows
        ]

    def save_autonomous_goal(self, goal: AutonomousGoalV1) -> AutonomousGoalV1:
        goal = AutonomousGoalV1.model_validate(goal.model_dump(mode="python"))
        with self._lock, self._connection:
            existing = self._connection.execute(
                "SELECT goal_json FROM autonomous_goals WHERE goal_id = ?",
                (goal.goal_id,),
            ).fetchone()
            if existing is not None:
                stored = AutonomousGoalV1.model_validate_json(existing["goal_json"])
                if stored != goal:
                    raise ValueError("autonomous goal content is immutable")
                return stored
            policy = self.get_autonomy_policy(goal.course_id)
            membership = self.get_membership(goal.student_id, goal.course_id)
            release = self.get_published_release(goal.course_id)
            if (
                policy is None
                or not policy.autonomy_enabled
                or policy.paused
                or policy.kill_switch
                or policy.version != goal.policy_version
                or policy.approved_profile_id != goal.profile_id
                or policy.approved_profile_sha256 != goal.profile_sha256
            ):
                raise ValueError("goal does not match an active autonomy policy")
            if (
                membership is None
                or membership.role != MembershipRole.STUDENT
                or not membership.active
                or release is None
                or release.id != goal.release_id
                or release.teaching_profile_id != goal.profile_id
                or release.teaching_profile_sha256 != goal.profile_sha256
            ):
                raise ValueError("goal does not match current student release scope")
            active_count = int(
                self._connection.execute(
                    """SELECT COUNT(*) FROM autonomous_goals
                       WHERE student_id = ? AND course_id = ? AND status = ?""",
                    (goal.student_id, goal.course_id, AutonomousGoalStatus.ACTIVE.value),
                ).fetchone()[0]
            )
            if goal.status == AutonomousGoalStatus.ACTIVE and active_count >= policy.max_active_goals:
                raise ValueError("active autonomous goal limit reached")
            self._insert_autonomous_goal(goal)
        return goal.model_copy(deep=True)

    def get_autonomous_goal(self, goal_id: str) -> AutonomousGoalV1 | None:
        row = self._one(
            "SELECT goal_json FROM autonomous_goals WHERE goal_id = ?", (goal_id,)
        )
        return AutonomousGoalV1.model_validate_json(row["goal_json"]) if row else None

    def list_autonomous_goals(
        self, student_id: str, course_id: str, *, active_only: bool = False
    ) -> list[AutonomousGoalV1]:
        sql = """SELECT goal_json FROM autonomous_goals
                 WHERE student_id = ? AND course_id = ?"""
        parameters: list[object] = [student_id, course_id]
        if active_only:
            sql += " AND status = ?"
            parameters.append(AutonomousGoalStatus.ACTIVE.value)
        sql += " ORDER BY priority DESC, created_at, goal_id"
        with self._lock:
            rows = self._connection.execute(sql, tuple(parameters)).fetchall()
        return [AutonomousGoalV1.model_validate_json(row["goal_json"]) for row in rows]

    def set_autonomous_goal_status(
        self,
        goal_id: str,
        status: AutonomousGoalStatus,
        *,
        changed_at: str,
    ) -> AutonomousGoalV1:
        if status == AutonomousGoalStatus.ACTIVE:
            raise ValueError("terminal autonomous goal cannot be reactivated")
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT goal_json FROM autonomous_goals WHERE goal_id = ?", (goal_id,)
            ).fetchone()
            if row is None:
                raise KeyError("autonomous_goal_not_found")
            goal = AutonomousGoalV1.model_validate_json(row["goal_json"])
            if goal.status != AutonomousGoalStatus.ACTIVE:
                return goal
            updated = goal.model_copy(update={"status": status, "updated_at": changed_at})
            self._connection.execute(
                """UPDATE autonomous_goals SET status = ?, goal_json = ?, updated_at = ?
                   WHERE goal_id = ?""",
                (status.value, updated.model_dump_json(), changed_at, goal_id),
            )
            self._connection.execute(
                "DELETE FROM autonomy_execution_leases WHERE opportunity_id IN "
                "(SELECT opportunity_id FROM autonomous_opportunities WHERE goal_id = ?)",
                (goal_id,),
            )
            self._set_goal_opportunities_status(
                goal_id,
                AutonomousOpportunityStatus.CANCELLED,
                changed_at=changed_at,
            )
            self._connection.execute(
                "UPDATE autonomous_wakeups SET status = 'cancelled' WHERE goal_id = ? AND status = 'pending'",
                (goal_id,),
            )
        return updated

    def save_autonomous_opportunity(
        self, opportunity: ProactiveOpportunityV1
    ) -> ProactiveOpportunityV1:
        opportunity = ProactiveOpportunityV1.model_validate(
            opportunity.model_dump(mode="python")
        )
        with self._lock, self._connection:
            existing = self._connection.execute(
                """SELECT opportunity_json FROM autonomous_opportunities
                   WHERE idempotency_key = ?""",
                (opportunity.idempotency_key,),
            ).fetchone()
            if existing is not None:
                stored = ProactiveOpportunityV1.model_validate_json(
                    existing["opportunity_json"]
                )
                if stored != opportunity:
                    raise ValueError("autonomous opportunity key has conflicting content")
                return stored
            self._validate_autonomous_opportunity_scope(opportunity)
            self._insert_autonomous_opportunity(opportunity)
        return opportunity.model_copy(deep=True)

    def get_autonomous_opportunity(
        self, opportunity_id: str
    ) -> ProactiveOpportunityV1 | None:
        row = self._one(
            """SELECT opportunity_json FROM autonomous_opportunities
               WHERE opportunity_id = ?""",
            (opportunity_id,),
        )
        return (
            ProactiveOpportunityV1.model_validate_json(row["opportunity_json"])
            if row
            else None
        )

    def get_autonomous_opportunity_by_key(
        self, idempotency_key: str
    ) -> ProactiveOpportunityV1 | None:
        row = self._one(
            """SELECT opportunity_json FROM autonomous_opportunities
               WHERE idempotency_key = ?""",
            (idempotency_key,),
        )
        return (
            ProactiveOpportunityV1.model_validate_json(row["opportunity_json"])
            if row
            else None
        )

    def list_due_autonomous_opportunities(
        self, due_at: str, *, limit: int = 100
    ) -> list[ProactiveOpportunityV1]:
        if isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValueError("autonomous opportunity limit must be between 1 and 500")
        with self._lock:
            rows = self._connection.execute(
                """SELECT o.opportunity_json
                   FROM autonomous_opportunities AS o
                   LEFT JOIN autonomy_execution_leases AS lease
                     ON lease.opportunity_id = o.opportunity_id
                   WHERE o.earliest_action_at <= ? AND o.latest_action_at >= ?
                     AND (o.status = ? OR (o.status = ? AND lease.lease_expires_at <= ?))
                   ORDER BY o.earliest_action_at, o.opportunity_id LIMIT ?""",
                (
                    due_at,
                    due_at,
                    AutonomousOpportunityStatus.PENDING.value,
                    AutonomousOpportunityStatus.LEASED.value,
                    due_at,
                    limit,
                ),
            ).fetchall()
        return [
            ProactiveOpportunityV1.model_validate_json(row["opportunity_json"])
            for row in rows
        ]

    def list_due_autonomous_wakeups(
        self, due_at: str, *, limit: int = 100
    ) -> list[AutonomousWakeUpV1]:
        if isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValueError("autonomous wake-up limit must be between 1 and 500")
        with self._lock:
            rows = self._connection.execute(
                """SELECT wake_up_json FROM autonomous_wakeups
                   WHERE status = 'pending' AND due_at <= ?
                   ORDER BY due_at, wake_up_id LIMIT ?""",
                (due_at, limit),
            ).fetchall()
        return [
            AutonomousWakeUpV1.model_validate_json(row["wake_up_json"])
            for row in rows
        ]

    def materialize_autonomous_wakeup(
        self,
        wake_up_id: str,
        opportunity: ProactiveOpportunityV1,
        *,
        fired_at: str,
    ) -> bool:
        opportunity = ProactiveOpportunityV1.model_validate(
            opportunity.model_dump(mode="python")
        )
        with self._lock, self._connection:
            wake = self._connection.execute(
                """SELECT wake_up_json, status FROM autonomous_wakeups
                   WHERE wake_up_id = ?""",
                (wake_up_id,),
            ).fetchone()
            if wake is None:
                raise KeyError("autonomous_wakeup_not_found")
            if wake["status"] == "fired":
                existing = self._connection.execute(
                    """SELECT opportunity_json FROM autonomous_opportunities
                       WHERE idempotency_key = ?""",
                    (opportunity.idempotency_key,),
                ).fetchone()
                return existing is not None
            if wake["status"] != "pending":
                return False
            source = AutonomousWakeUpV1.model_validate_json(wake["wake_up_json"])
            if (
                source.goal_id != opportunity.goal_id
                or source.student_id != opportunity.student_id
                or source.course_id != opportunity.course_id
                or source.release_id != opportunity.release_id
            ):
                raise ValueError("wake-up opportunity has inconsistent scope")
            self._validate_autonomous_opportunity_scope(opportunity)
            self._insert_autonomous_opportunity(opportunity)
            fired = source.model_copy(update={"status": "fired"})
            self._connection.execute(
                """UPDATE autonomous_wakeups SET status = 'fired', wake_up_json = ?
                   WHERE wake_up_id = ?""",
                (fired.model_dump_json(), wake_up_id),
            )
        return True

    def claim_autonomous_opportunity(
        self,
        opportunity_id: str,
        *,
        lease_owner: str,
        acquired_at: str,
        lease_expires_at: str,
    ) -> ProactiveOpportunityV1 | None:
        with self._lock, self._connection:
            row = self._connection.execute(
                """SELECT opportunity_json, status, earliest_action_at, latest_action_at
                   FROM autonomous_opportunities WHERE opportunity_id = ?""",
                (opportunity_id,),
            ).fetchone()
            if row is None or not (
                row["earliest_action_at"] <= acquired_at <= row["latest_action_at"]
            ):
                return None
            lease = self._connection.execute(
                """SELECT lease_expires_at FROM autonomy_execution_leases
                   WHERE opportunity_id = ?""",
                (opportunity_id,),
            ).fetchone()
            if row["status"] == AutonomousOpportunityStatus.LEASED.value and (
                lease is None or lease["lease_expires_at"] > acquired_at
            ):
                return None
            if row["status"] not in {
                AutonomousOpportunityStatus.PENDING.value,
                AutonomousOpportunityStatus.LEASED.value,
            }:
                return None
            self._connection.execute(
                """INSERT INTO autonomy_execution_leases
                   (opportunity_id, lease_owner, lease_expires_at, acquired_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(opportunity_id) DO UPDATE SET
                     lease_owner = excluded.lease_owner,
                     lease_expires_at = excluded.lease_expires_at,
                     acquired_at = excluded.acquired_at""",
                (opportunity_id, lease_owner, lease_expires_at, acquired_at),
            )
            opportunity = ProactiveOpportunityV1.model_validate_json(
                row["opportunity_json"]
            ).model_copy(
                update={
                    "status": AutonomousOpportunityStatus.LEASED,
                    "updated_at": acquired_at,
                }
            )
            self._connection.execute(
                """UPDATE autonomous_opportunities
                   SET status = ?, opportunity_json = ?, updated_at = ?
                   WHERE opportunity_id = ?""",
                (
                    opportunity.status.value,
                    opportunity.model_dump_json(),
                    acquired_at,
                    opportunity_id,
                ),
            )
        return opportunity

    def commit_autonomous_job(self, result: AutonomousJobResult) -> None:
        result = AutonomousJobResult.model_validate(result.model_dump(mode="python"))
        opportunity = result.opportunity
        plan = result.plan
        action = result.action
        outcome = result.outcome
        if not (
            plan.opportunity_id == opportunity.opportunity_id
            == action.opportunity_id
            and plan.plan_id == action.plan_id
            and action.action_id == outcome.action_id
            and plan.student_id == action.student_id == outcome.student_id
            == opportunity.student_id
            and plan.course_id == action.course_id == outcome.course_id
            == opportunity.course_id
            and plan.release_id == action.release_id == outcome.release_id
            == opportunity.release_id
        ):
            raise ValueError("autonomous job records have inconsistent lineage")
        terminal_status = (
            AutonomousOpportunityStatus.NO_ACTION
            if action.kind.value == "no-action"
            else AutonomousOpportunityStatus.COMPLETED
        )
        terminal_opportunity = opportunity.model_copy(
            update={"status": terminal_status, "updated_at": timestamp_now()}
        )
        binding_payload = {
            "opportunity": opportunity.model_dump(mode="json"),
            "plan": plan.model_dump(mode="json"),
            "action": action.model_dump(mode="json"),
            "outcome": outcome.model_dump(mode="json"),
            "trace": result.trace.model_dump(mode="json"),
        }
        binding_json = json.dumps(binding_payload, sort_keys=True, separators=(",", ":"))
        binding_sha256 = hashlib.sha256(binding_json.encode("utf-8")).hexdigest()
        with self._lock, self._connection:
            current = self._connection.execute(
                "SELECT status FROM autonomous_opportunities WHERE opportunity_id = ?",
                (opportunity.opportunity_id,),
            ).fetchone()
            if current is None:
                raise KeyError("autonomous_opportunity_not_found")
            if current["status"] not in {
                AutonomousOpportunityStatus.PENDING.value,
                AutonomousOpportunityStatus.LEASED.value,
            }:
                existing = self._connection.execute(
                    "SELECT binding_sha256 FROM autonomous_graph_checkpoints WHERE opportunity_id = ?",
                    (opportunity.opportunity_id,),
                ).fetchone()
                if existing is not None and existing["binding_sha256"] == binding_sha256:
                    return
                raise ValueError("autonomous opportunity is already terminal")
            self._connection.execute(
                """INSERT INTO autonomous_plans
                   (plan_id, opportunity_id, goal_id, student_id, course_id,
                    release_id, policy_version, profile_sha256, graph_version,
                    plan_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    plan.plan_id,
                    plan.opportunity_id,
                    plan.goal_id,
                    plan.student_id,
                    plan.course_id,
                    plan.release_id,
                    plan.policy_version,
                    plan.profile_sha256,
                    plan.graph_version,
                    plan.model_dump_json(),
                    plan.created_at,
                ),
            )
            self._connection.execute(
                """INSERT INTO autonomous_actions
                   (action_id, plan_id, opportunity_id, goal_id, student_id,
                    course_id, release_id, policy_version, profile_sha256,
                    graph_version, proactive_trigger_id, status, action_json,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    action.action_id,
                    action.plan_id,
                    action.opportunity_id,
                    action.goal_id,
                    action.student_id,
                    action.course_id,
                    action.release_id,
                    action.policy_version,
                    action.profile_sha256,
                    action.graph_version,
                    action.proactive_trigger_id,
                    action.status.value,
                    action.model_dump_json(),
                    action.created_at,
                    action.updated_at,
                ),
            )
            self._connection.execute(
                """INSERT INTO autonomous_outcomes
                   (outcome_id, action_id, goal_id, student_id, course_id,
                    release_id, policy_version, profile_sha256, graph_version,
                    outcome_json, recorded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    outcome.outcome_id,
                    outcome.action_id,
                    outcome.goal_id,
                    outcome.student_id,
                    outcome.course_id,
                    outcome.release_id,
                    outcome.policy_version,
                    outcome.profile_sha256,
                    outcome.graph_version,
                    outcome.model_dump_json(),
                    outcome.recorded_at,
                ),
            )
            if (
                action.goal_id is not None
                and action.status == AutonomousActionStatus.DELIVERED
            ):
                goal_row = self._connection.execute(
                    "SELECT goal_json FROM autonomous_goals WHERE goal_id = ?",
                    (action.goal_id,),
                ).fetchone()
                if goal_row is None:
                    raise ValueError("delivered autonomous action has no goal")
                goal = AutonomousGoalV1.model_validate_json(goal_row["goal_json"])
                if goal.status != AutonomousGoalStatus.ACTIVE:
                    raise ValueError("delivered autonomous action goal is not active")
                if goal.attempt_count >= goal.attempt_limit:
                    raise ValueError("autonomous goal attempt limit is exhausted")
                attempted = goal.model_copy(
                    update={
                        "attempt_count": goal.attempt_count + 1,
                        "updated_at": action.updated_at,
                    }
                )
                self._connection.execute(
                    """UPDATE autonomous_goals SET goal_json = ?, updated_at = ?
                       WHERE goal_id = ?""",
                    (
                        attempted.model_dump_json(),
                        attempted.updated_at,
                        attempted.goal_id,
                    ),
                )
            if result.wake_up is not None:
                self._insert_autonomous_wakeup(result.wake_up)
            self._connection.execute(
                """INSERT INTO autonomous_graph_checkpoints
                   (job_id, opportunity_id, binding_sha256, status, state_json, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    f"autonomous-job:{opportunity.opportunity_id}",
                    opportunity.opportunity_id,
                    binding_sha256,
                    terminal_status.value,
                    binding_json,
                    terminal_opportunity.updated_at,
                ),
            )
            self._connection.execute(
                """UPDATE autonomous_opportunities SET status = ?,
                   opportunity_json = ?, updated_at = ? WHERE opportunity_id = ?""",
                (
                    terminal_status.value,
                    terminal_opportunity.model_dump_json(),
                    terminal_opportunity.updated_at,
                    opportunity.opportunity_id,
                ),
            )
            self._connection.execute(
                "DELETE FROM autonomy_execution_leases WHERE opportunity_id = ?",
                (opportunity.opportunity_id,),
            )

    def bind_autonomous_action_trigger(
        self,
        action_id: str,
        *,
        trigger_id: str,
        status: AutonomousActionStatus,
        updated_at: str,
    ) -> AutonomousActionV1:
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT action_json FROM autonomous_actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
            if row is None:
                raise KeyError("autonomous_action_not_found")
            action = AutonomousActionV1.model_validate_json(row["action_json"])
            if action.proactive_trigger_id not in {None, trigger_id}:
                raise ValueError("autonomous action is bound to another trigger")
            updated = action.model_copy(
                update={
                    "proactive_trigger_id": trigger_id,
                    "status": status,
                    "updated_at": updated_at,
                }
            )
            self._connection.execute(
                """UPDATE autonomous_actions SET proactive_trigger_id = ?, status = ?,
                   action_json = ?, updated_at = ? WHERE action_id = ?""",
                (
                    trigger_id,
                    status.value,
                    updated.model_dump_json(),
                    updated_at,
                    action_id,
                ),
            )
        return updated

    def list_autonomous_actions(
        self, course_id: str, *, student_id: str | None = None
    ) -> list[AutonomousActionV1]:
        sql = "SELECT action_json FROM autonomous_actions WHERE course_id = ?"
        parameters: list[object] = [course_id]
        if student_id is not None:
            sql += " AND student_id = ?"
            parameters.append(student_id)
        sql += " ORDER BY created_at DESC, action_id"
        with self._lock:
            rows = self._connection.execute(sql, tuple(parameters)).fetchall()
        return [AutonomousActionV1.model_validate_json(row["action_json"]) for row in rows]

    def get_autonomous_outcome(
        self, action_id: str
    ) -> AutonomousOutcomeV1 | None:
        row = self._one(
            "SELECT outcome_json FROM autonomous_outcomes WHERE action_id = ?",
            (action_id,),
        )
        return (
            AutonomousOutcomeV1.model_validate_json(row["outcome_json"])
            if row is not None
            else None
        )

    def list_autonomous_outcomes(
        self, course_id: str, *, student_id: str | None = None
    ) -> list[AutonomousOutcomeV1]:
        sql = "SELECT outcome_json FROM autonomous_outcomes WHERE course_id = ?"
        parameters: list[object] = [course_id]
        if student_id is not None:
            sql += " AND student_id = ?"
            parameters.append(student_id)
        sql += " ORDER BY recorded_at DESC, outcome_id"
        with self._lock:
            rows = self._connection.execute(sql, tuple(parameters)).fetchall()
        return [
            AutonomousOutcomeV1.model_validate_json(row["outcome_json"])
            for row in rows
        ]

    def expire_autonomous_goals(self, *, expired_at: str) -> int:
        with self._lock, self._connection:
            rows = self._connection.execute(
                """SELECT goal_json FROM autonomous_goals
                   WHERE status = ? AND expires_at <= ?""",
                (AutonomousGoalStatus.ACTIVE.value, expired_at),
            ).fetchall()
            for row in rows:
                goal = AutonomousGoalV1.model_validate_json(row["goal_json"])
                updated = goal.model_copy(
                    update={
                        "status": AutonomousGoalStatus.EXPIRED,
                        "updated_at": expired_at,
                    }
                )
                self._connection.execute(
                    """UPDATE autonomous_goals SET status = ?, goal_json = ?,
                       updated_at = ? WHERE goal_id = ?""",
                    (
                        updated.status.value,
                        updated.model_dump_json(),
                        expired_at,
                        updated.goal_id,
                    ),
                )
                self._set_goal_opportunities_status(
                    updated.goal_id,
                    AutonomousOpportunityStatus.EXPIRED,
                    changed_at=expired_at,
                )
                self._connection.execute(
                    """UPDATE autonomous_wakeups SET status = 'cancelled'
                       WHERE goal_id = ? AND status = 'pending'""",
                    (updated.goal_id,),
                )
            return len(rows)

    def expire_autonomous_opportunities(self, *, expired_at: str) -> int:
        with self._lock, self._connection:
            rows = self._connection.execute(
                """SELECT opportunity_id, opportunity_json
                   FROM autonomous_opportunities
                   WHERE status IN (?, ?) AND latest_action_at < ?""",
                (
                    AutonomousOpportunityStatus.PENDING.value,
                    AutonomousOpportunityStatus.LEASED.value,
                    expired_at,
                ),
            ).fetchall()
            for row in rows:
                opportunity = ProactiveOpportunityV1.model_validate_json(
                    row["opportunity_json"]
                ).model_copy(
                    update={
                        "status": AutonomousOpportunityStatus.EXPIRED,
                        "updated_at": expired_at,
                    }
                )
                self._connection.execute(
                    """UPDATE autonomous_opportunities SET status = ?,
                       opportunity_json = ?, updated_at = ?
                       WHERE opportunity_id = ?""",
                    (
                        opportunity.status.value,
                        opportunity.model_dump_json(),
                        expired_at,
                        opportunity.opportunity_id,
                    ),
                )
                self._connection.execute(
                    """DELETE FROM autonomy_execution_leases
                       WHERE opportunity_id = ?""",
                    (opportunity.opportunity_id,),
                )
            return len(rows)

    def cancel_autonomy_scope(
        self,
        *,
        student_id: str | None = None,
        course_id: str,
        release_id: str | None = None,
        changed_at: str,
    ) -> int:
        with self._lock, self._connection:
            return self._cancel_autonomy_scope_sql(
                student_id=student_id,
                course_id=course_id,
                release_id=release_id,
                changed_at=changed_at,
            )

    def set_release_status(self, release_id: str, status: StudentReleaseStatus) -> None:
        if status == StudentReleaseStatus.PUBLISHED:
            raise ValueError("publish_release must be used to publish a release")
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "UPDATE releases SET status = ? WHERE id = ?",
                (status.value, release_id),
            )
            if cursor.rowcount != 1:
                raise KeyError("release_not_found")
            if status == StudentReleaseStatus.WITHDRAWN:
                self._cancel_release_outreach(release_id)
                release = self.get_release(release_id)
                if release is not None:
                    self._cancel_autonomy_scope_sql(
                        student_id=None,
                        course_id=release.course_id,
                        release_id=release_id,
                        changed_at=timestamp_now(),
                    )

    def set_release_evaluation_status(
        self, release_id: str, status: ReleaseEvaluationStatus
    ) -> None:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """UPDATE releases SET evaluation_status = ?
                   WHERE id = ? AND (status != ? OR ? = ?)""",
                (
                    status.value,
                    release_id,
                    StudentReleaseStatus.PUBLISHED.value,
                    status.value,
                    ReleaseEvaluationStatus.PASSED.value,
                ),
            )
            if cursor.rowcount != 1:
                if self._connection.execute(
                    "SELECT 1 FROM releases WHERE id = ?", (release_id,)
                ).fetchone() is None:
                    raise KeyError("release_not_found")
                raise ValueError("published releases must retain passed evaluation")

    def publish_release(self, release_id: str) -> None:
        """Atomically make one course release current and withdraw its predecessor."""
        with self._lock, self._connection:
            release = self.get_release(release_id)
            if release is None:
                raise KeyError("release_not_found")
            DigitalTwinRelease.model_validate(
                {
                    **release.model_dump(mode="python"),
                    "status": StudentReleaseStatus.PUBLISHED,
                }
            )
            changed_at = timestamp_now()
            prior_release_ids = [
                str(row["id"])
                for row in self._connection.execute(
                    """SELECT id FROM releases WHERE course_id = ?
                       AND status = ? AND id != ?""",
                    (
                        release.course_id,
                        StudentReleaseStatus.PUBLISHED.value,
                        release_id,
                    ),
                ).fetchall()
            ]
            for prior_release_id in prior_release_ids:
                self._cancel_autonomy_scope_sql(
                    student_id=None,
                    course_id=release.course_id,
                    release_id=prior_release_id,
                    changed_at=changed_at,
                )
            self._connection.execute(
                """UPDATE releases SET status = ?
                   WHERE course_id = ? AND status = ? AND id != ?""",
                (
                    StudentReleaseStatus.WITHDRAWN.value,
                    release.course_id,
                    StudentReleaseStatus.PUBLISHED.value,
                    release_id,
                ),
            )
            self._connection.execute(
                """UPDATE proactive_triggers SET status = ?, updated_at = ?
                   WHERE course_id = ? AND release_id != ? AND status = ?""",
                (
                    ProactiveTriggerStatus.CANCELLED.value,
                    changed_at,
                    release.course_id,
                    release_id,
                    ProactiveTriggerStatus.PENDING.value,
                ),
            )
            self._connection.execute(
                """UPDATE proactive_delivery_outbox SET status = ?, updated_at = ?
                   WHERE message_id IN (
                       SELECT id FROM proactive_messages
                       WHERE course_id = ? AND release_id != ?
                   ) AND status = ?""",
                (
                    "cancelled",
                    changed_at,
                    release.course_id,
                    release_id,
                    "pending",
                ),
            )
            self._connection.execute(
                """UPDATE proactive_messages SET status = ?
                   WHERE course_id = ? AND release_id != ? AND status IN (?, ?)""",
                (
                    ProactiveMessageStatus.CANCELLED.value,
                    release.course_id,
                    release_id,
                    ProactiveMessageStatus.QUEUED.value,
                    ProactiveMessageStatus.DELIVERED.value,
                ),
            )
            cursor = self._connection.execute(
                "UPDATE releases SET status = ? WHERE id = ?",
                (StudentReleaseStatus.PUBLISHED.value, release_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("release publication update failed")

    def _validate_autonomous_opportunity_scope(
        self, opportunity: ProactiveOpportunityV1
    ) -> None:
        policy = self.get_autonomy_policy(opportunity.course_id)
        membership = self.get_membership(
            opportunity.student_id, opportunity.course_id
        )
        release = self.get_published_release(opportunity.course_id)
        if (
            policy is None
            or not policy.autonomy_enabled
            or policy.paused
            or policy.kill_switch
            or policy.version != opportunity.policy_version
            or policy.approved_profile_id != opportunity.profile_id
            or policy.approved_profile_sha256 != opportunity.profile_sha256
        ):
            raise ValueError("opportunity does not match active autonomy policy")
        if (
            membership is None
            or membership.role != MembershipRole.STUDENT
            or not membership.active
            or release is None
            or release.id != opportunity.release_id
            or release.teaching_profile_id != opportunity.profile_id
            or release.teaching_profile_sha256 != opportunity.profile_sha256
        ):
            raise ValueError("opportunity does not match current student release scope")
        if opportunity.goal_id is not None:
            goal = self.get_autonomous_goal(opportunity.goal_id)
            if (
                goal is None
                or goal.status != AutonomousGoalStatus.ACTIVE
                or goal.student_id != opportunity.student_id
                or goal.course_id != opportunity.course_id
                or goal.release_id != opportunity.release_id
            ):
                raise ValueError("opportunity goal is unavailable or out of scope")

    def _insert_autonomous_goal(self, goal: AutonomousGoalV1) -> None:
        self._connection.execute(
            """INSERT INTO autonomous_goals
               (goal_id, student_id, course_id, release_id, policy_version,
                profile_id, profile_sha256, graph_version, planner_model,
                generator_model, status, priority, expires_at, goal_json,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                goal.goal_id,
                goal.student_id,
                goal.course_id,
                goal.release_id,
                goal.policy_version,
                goal.profile_id,
                goal.profile_sha256,
                goal.graph_version,
                goal.planner_model,
                goal.generator_model,
                goal.status.value,
                goal.priority,
                goal.expires_at,
                goal.model_dump_json(),
                goal.created_at,
                goal.updated_at,
            ),
        )

    def _insert_autonomous_opportunity(
        self, opportunity: ProactiveOpportunityV1
    ) -> None:
        self._connection.execute(
            """INSERT INTO autonomous_opportunities
               (opportunity_id, idempotency_key, goal_id, student_id, course_id,
                release_id, policy_version, profile_id, profile_sha256,
                graph_version, planner_model, generator_model, event_kind, status,
                earliest_action_at, latest_action_at, opportunity_json,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                opportunity.opportunity_id,
                opportunity.idempotency_key,
                opportunity.goal_id,
                opportunity.student_id,
                opportunity.course_id,
                opportunity.release_id,
                opportunity.policy_version,
                opportunity.profile_id,
                opportunity.profile_sha256,
                opportunity.graph_version,
                opportunity.planner_model,
                opportunity.generator_model,
                opportunity.event_kind.value,
                opportunity.status.value,
                opportunity.earliest_action_at,
                opportunity.latest_action_at,
                opportunity.model_dump_json(),
                opportunity.created_at,
                opportunity.updated_at,
            ),
        )

    def _insert_autonomous_wakeup(self, wake_up: AutonomousWakeUpV1) -> None:
        wake_up = AutonomousWakeUpV1.model_validate(wake_up.model_dump(mode="python"))
        self._connection.execute(
            """INSERT INTO autonomous_wakeups
               (wake_up_id, goal_id, student_id, course_id, release_id, due_at,
                event_kind, status, wake_up_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                wake_up.wake_up_id,
                wake_up.goal_id,
                wake_up.student_id,
                wake_up.course_id,
                wake_up.release_id,
                wake_up.due_at,
                wake_up.event_kind.value,
                wake_up.status,
                wake_up.model_dump_json(),
                wake_up.created_at,
            ),
        )

    def _cancel_autonomy_scope_sql(
        self,
        *,
        student_id: str | None,
        course_id: str,
        release_id: str | None,
        changed_at: str,
    ) -> int:
        filters = ["course_id = ?"]
        parameters: list[object] = [course_id]
        if student_id is not None:
            filters.append("student_id = ?")
            parameters.append(student_id)
        if release_id is not None:
            filters.append("release_id = ?")
            parameters.append(release_id)
        scope = " AND ".join(filters)
        goal_rows = self._connection.execute(
            f"SELECT goal_id, goal_json FROM autonomous_goals WHERE {scope} AND status = ?",
            (*parameters, AutonomousGoalStatus.ACTIVE.value),
        ).fetchall()
        for row in goal_rows:
            goal = AutonomousGoalV1.model_validate_json(row["goal_json"]).model_copy(
                update={
                    "status": AutonomousGoalStatus.CANCELLED,
                    "updated_at": changed_at,
                }
            )
            self._connection.execute(
                """UPDATE autonomous_goals SET status = ?, goal_json = ?, updated_at = ?
                   WHERE goal_id = ?""",
                (
                    goal.status.value,
                    goal.model_dump_json(),
                    changed_at,
                    goal.goal_id,
                ),
            )
        opportunity_rows = self._connection.execute(
            f"""SELECT opportunity_id, opportunity_json FROM autonomous_opportunities
                WHERE {scope} AND status IN (?, ?)""",
            (
                *parameters,
                AutonomousOpportunityStatus.PENDING.value,
                AutonomousOpportunityStatus.LEASED.value,
            ),
        ).fetchall()
        for row in opportunity_rows:
            opportunity = ProactiveOpportunityV1.model_validate_json(
                row["opportunity_json"]
            ).model_copy(
                update={
                    "status": AutonomousOpportunityStatus.CANCELLED,
                    "updated_at": changed_at,
                }
            )
            self._connection.execute(
                """UPDATE autonomous_opportunities SET status = ?,
                   opportunity_json = ?, updated_at = ? WHERE opportunity_id = ?""",
                (
                    opportunity.status.value,
                    opportunity.model_dump_json(),
                    changed_at,
                    opportunity.opportunity_id,
                ),
            )
            self._connection.execute(
                "DELETE FROM autonomy_execution_leases WHERE opportunity_id = ?",
                (opportunity.opportunity_id,),
            )
        wake_filters = ["course_id = ?"]
        wake_parameters: list[object] = [course_id]
        if student_id is not None:
            wake_filters.append("student_id = ?")
            wake_parameters.append(student_id)
        if release_id is not None:
            wake_filters.append("release_id = ?")
            wake_parameters.append(release_id)
        self._connection.execute(
            f"""UPDATE autonomous_wakeups SET status = 'cancelled'
                WHERE {' AND '.join(wake_filters)} AND status = 'pending'""",
            tuple(wake_parameters),
        )
        return len(goal_rows) + len(opportunity_rows)

    def _one(self, sql: str, parameters: tuple[object, ...]) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(sql, parameters).fetchone()

    def _release(self, row: sqlite3.Row) -> DigitalTwinRelease:
        with self._lock:
            chunk_rows = self._connection.execute(
                """SELECT chunk_json FROM release_chunks
                   WHERE release_id = ? ORDER BY rowid""",
                (row["id"],),
            ).fetchall()
        return DigitalTwinRelease(
            id=row["id"],
            course_id=row["course_id"],
            profile_id=row["profile_id"],
            profile_version=row["profile_version"],
            policy_version=row["policy_version"],
            policy=TutorPolicy.model_validate_json(row["policy_json"]),
            teaching_profile_id=row["teaching_profile_id"],
            teaching_profile_sha256=row["teaching_profile_sha256"],
            chunks=[
                DocumentChunk.model_validate_json(item["chunk_json"])
                for item in chunk_rows
            ],
            status=row["status"],
            evaluation_status=row["evaluation_status"],
            created_at=row["created_at"],
        )

    def _insert_message(self, message: Message) -> None:
        self._connection.execute(
            """INSERT INTO messages
               (id, conversation_id, role, content, action, trace_json,
                client_request_id, response_to_message_id, tutoring_mode,
                tutoring_intent, learner_state_revision, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                message.id,
                message.conversation_id,
                message.role,
                message.content,
                message.action,
                message.trace.model_dump_json() if message.trace else None,
                message.client_request_id,
                message.response_to_message_id,
                message.tutoring_mode,
                message.tutoring_intent,
                message.learner_state_revision,
                message.created_at,
            ),
        )

    def _autonomous_action_for_trigger(
        self, trigger_id: str
    ) -> AutonomousActionV1 | None:
        row = self._connection.execute(
            """SELECT action_json FROM autonomous_actions
               WHERE proactive_trigger_id = ?""",
            (trigger_id,),
        ).fetchone()
        return (
            AutonomousActionV1.model_validate_json(row["action_json"])
            if row is not None
            else None
        )

    def _set_goal_opportunities_status(
        self,
        goal_id: str,
        status: AutonomousOpportunityStatus,
        *,
        changed_at: str,
    ) -> None:
        rows = self._connection.execute(
            """SELECT opportunity_id, opportunity_json
               FROM autonomous_opportunities
               WHERE goal_id = ? AND status IN (?, ?)""",
            (
                goal_id,
                AutonomousOpportunityStatus.PENDING.value,
                AutonomousOpportunityStatus.LEASED.value,
            ),
        ).fetchall()
        for row in rows:
            opportunity = ProactiveOpportunityV1.model_validate_json(
                row["opportunity_json"]
            ).model_copy(update={"status": status, "updated_at": changed_at})
            self._connection.execute(
                """UPDATE autonomous_opportunities SET status = ?,
                   opportunity_json = ?, updated_at = ? WHERE opportunity_id = ?""",
                (
                    opportunity.status.value,
                    opportunity.model_dump_json(),
                    changed_at,
                    opportunity.opportunity_id,
                ),
            )
            self._connection.execute(
                """DELETE FROM autonomy_execution_leases
                   WHERE opportunity_id = ?""",
                (opportunity.opportunity_id,),
            )

    def _link_autonomous_response(
        self,
        *,
        response_message: ProactiveMessage,
        student_message: Message,
        action: AutonomousActionV1 | None,
        learner_state: LearnerState | None,
        linked_at: str,
    ) -> None:
        existing = self._connection.execute(
            """SELECT student_message_id FROM autonomous_response_links
               WHERE proactive_message_id = ?""",
            (response_message.id,),
        ).fetchone()
        if existing is not None:
            if existing["student_message_id"] != student_message.id:
                raise ValueError("outreach message already has a different response")
            return
        self._connection.execute(
            """INSERT INTO autonomous_response_links
               (proactive_message_id, student_message_id, action_id, goal_id,
                course_id, release_id, linked_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                response_message.id,
                student_message.id,
                action.action_id if action is not None else None,
                action.goal_id if action is not None else None,
                response_message.course_id,
                response_message.release_id,
                linked_at,
            ),
        )
        if action is None:
            return
        row = self._connection.execute(
            "SELECT outcome_json FROM autonomous_outcomes WHERE action_id = ?",
            (action.action_id,),
        ).fetchone()
        if row is None:
            raise ValueError("autonomous action response is missing its outcome")
        outcome = AutonomousOutcomeV1.model_validate_json(row["outcome_json"])
        progress = max(outcome.goal_progress, 0.5)
        if learner_state is not None and learner_state.mastery_by_concept:
            strongest = max(
                learner_state.mastery_by_concept.values(),
                key=lambda item: (item.estimate, item.confidence, item.observation_count),
            )
            progress = max(
                progress,
                min(
                    1.0,
                    0.5 * strongest.estimate
                    + 0.3 * strongest.confidence
                    + 0.2 * min(1.0, strongest.observation_count / 2),
                ),
            )
        answered = outcome.model_copy(
            update={
                "kind": AutonomousOutcomeKind.ANSWERED,
                "learner_observation_id": student_message.id,
                "goal_progress": progress,
                "recorded_at": linked_at,
            }
        )
        self._connection.execute(
            """UPDATE autonomous_outcomes SET outcome_json = ?, recorded_at = ?
               WHERE action_id = ?""",
            (answered.model_dump_json(), linked_at, action.action_id),
        )

    @staticmethod
    def _message(row: sqlite3.Row) -> Message:
        value = dict(row)
        trace = value.pop("trace_json")
        value["trace"] = GenerationTrace.model_validate_json(trace) if trace else None
        return Message.model_validate(value)

    @staticmethod
    def _outreach_preference(row: sqlite3.Row) -> OutreachPreference:
        value = dict(row)
        value["enabled"] = bool(value["enabled"])
        value["private_destination"] = bool(value["private_destination"])
        return OutreachPreference.model_validate(value)

    def _insert_proactive_citations(self, citations: list[Citation]) -> None:
        self._connection.executemany(
            """INSERT INTO proactive_citations
               (id, message_id, course_id, release_id, source_artifact_id,
                source_document_id, source_version, title, locator,
                source_checksum, page, region_id, region_kind,
                bounding_box_json, crop_ref)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    citation.id,
                    citation.message_id,
                    citation.course_id,
                    citation.release_id,
                    citation.source_artifact_id,
                    citation.source_document_id,
                    citation.source_version,
                    citation.title,
                    citation.locator,
                    citation.source_checksum,
                    citation.page,
                    citation.region_id,
                    citation.region_kind,
                    (
                        json.dumps(citation.bounding_box)
                        if citation.bounding_box is not None
                        else None
                    ),
                    citation.crop_ref,
                )
                for citation in citations
            ],
        )

    @staticmethod
    def _citation(row: sqlite3.Row) -> Citation:
        values = dict(row)
        bounding_box_json = values.pop("bounding_box_json", None)
        values["bounding_box"] = (
            tuple(json.loads(bounding_box_json)) if bounding_box_json else None
        )
        return Citation.model_validate(values)

    def _cancel_release_outreach(self, release_id: str) -> None:
        changed_at = timestamp_now()
        self._connection.execute(
            """UPDATE proactive_triggers SET status = ?, updated_at = ?
               WHERE release_id = ? AND status = ?""",
            (
                ProactiveTriggerStatus.CANCELLED.value,
                changed_at,
                release_id,
                ProactiveTriggerStatus.PENDING.value,
            ),
        )
        self._connection.execute(
            """UPDATE proactive_messages SET status = ?
               WHERE release_id = ? AND status IN (?, ?)""",
            (
                ProactiveMessageStatus.CANCELLED.value,
                release_id,
                ProactiveMessageStatus.QUEUED.value,
                ProactiveMessageStatus.DELIVERED.value,
            ),
        )
        self._connection.execute(
            """UPDATE proactive_delivery_outbox SET status = ?, updated_at = ?
               WHERE message_id IN (
                   SELECT id FROM proactive_messages WHERE release_id = ?
               ) AND status = ?""",
            ("cancelled", changed_at, release_id, "pending"),
        )

    def _insert_audit_event(self, event: AuditEvent) -> None:
        self._connection.execute(
            """INSERT INTO audit_events
               (id, event_type, account_id, course_id, release_id,
                conversation_id, details_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.id,
                event.event_type,
                event.account_id,
                event.course_id,
                event.release_id,
                event.conversation_id,
                json.dumps(event.details, sort_keys=True),
                event.created_at,
            ),
        )

    @staticmethod
    def _audit_event(row: sqlite3.Row) -> AuditEvent:
        value = dict(row)
        value["details"] = json.loads(value.pop("details_json"))
        return AuditEvent.model_validate(value)


def _autonomy_boundary_payload(policy: PedagogicalPolicyV2) -> dict:
    """Separate immutable authority from reversible runtime controls."""

    return policy.model_dump(
        mode="python",
        exclude={
            "autonomy_enabled",
            "paused",
            "kill_switch",
            "updated_at",
        },
    )
