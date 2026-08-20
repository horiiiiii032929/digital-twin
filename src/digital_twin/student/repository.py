from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Protocol

from src.digital_twin.grounding.models import DocumentChunk, GenerationTrace
from src.digital_twin.student.models import (
    Account,
    AccountRole,
    AuditEvent,
    Citation,
    Conversation,
    Course,
    CourseMembership,
    DigitalTwinRelease,
    Message,
    MembershipRole,
    ReleaseEvaluationStatus,
    StudentReleaseStatus,
)
from src.digital_twin.student.migrations import apply_migrations
from src.digital_twin.tutor_policy import TutorPolicy


class DuplicateTurnError(RuntimeError):
    """A concurrent request already claimed the conversation request ID."""


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

    def list_messages(self, conversation_id: str) -> list[Message]: ...

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
                        policy_json, status, evaluation_status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        release.id,
                        release.course_id,
                        release.profile_id,
                        release.profile_version,
                        release.policy_version,
                        release.policy.model_dump_json(),
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
                self._connection.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?",
                    (conversation.updated_at, conversation.id),
                )
        except sqlite3.IntegrityError as error:
            if "messages.conversation_id, messages.client_request_id" in str(error):
                raise DuplicateTurnError from error
            raise

    def list_citations(self, message_id: str) -> list[Citation]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM citations WHERE message_id = ? ORDER BY rowid",
                (message_id,),
            ).fetchall()
        citations: list[Citation] = []
        for row in rows:
            values = dict(row)
            bounding_box_json = values.pop("bounding_box_json", None)
            values["bounding_box"] = (
                tuple(json.loads(bounding_box_json)) if bounding_box_json else None
            )
            citations.append(Citation.model_validate(values))
        return citations

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
            cursor = self._connection.execute(
                "UPDATE releases SET status = ? WHERE id = ?",
                (StudentReleaseStatus.PUBLISHED.value, release_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("release publication update failed")

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
                client_request_id, response_to_message_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                message.id,
                message.conversation_id,
                message.role,
                message.content,
                message.action,
                message.trace.model_dump_json() if message.trace else None,
                message.client_request_id,
                message.response_to_message_id,
                message.created_at,
            ),
        )

    @staticmethod
    def _message(row: sqlite3.Row) -> Message:
        value = dict(row)
        trace = value.pop("trace_json")
        value["trace"] = GenerationTrace.model_validate_json(trace) if trace else None
        return Message.model_validate(value)

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
