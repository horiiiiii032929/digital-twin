import sqlite3

import pytest
from pydantic import ValidationError

from src.digital_twin.identity import IdentityService
from src.digital_twin.identity.models import CredentialRecord, SessionRecord
from src.digital_twin.identity.repository import SQLiteIdentityRepository
from src.digital_twin.student.fixtures import seed_synthetic_student_workflow
from src.digital_twin.student.migrations import DEFAULT_MIGRATIONS, current_schema_version
from src.digital_twin.student.models import (
    AccountRole,
    AccountStatus,
    Conversation,
    Course,
    CourseMembership,
    DigitalTwinRelease,
    MembershipRole,
    ReleaseEvaluationStatus,
    StudentReleaseStatus,
)
from src.digital_twin.student.repository import SQLiteStudentRepository


def test_identity_repository_uses_the_versioned_complete_schema(tmp_path):
    repository = SQLiteIdentityRepository(tmp_path / "identity.sqlite3")

    assert current_schema_version(repository._connection) == len(DEFAULT_MIGRATIONS)
    assert repository._connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'accounts'"
    ).fetchone() is not None
    repository.close()


def test_updating_account_preserves_identity_and_course_relationships(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    students = SQLiteStudentRepository(path)
    fixture = seed_synthetic_student_workflow(students)
    identities = SQLiteIdentityRepository(path)
    identities.save_credential(
        CredentialRecord(
            account_id=fixture.student_a_id,
            email="student@example.test",
            normalized_email="student@example.test",
            display_name="Synthetic Student",
            password_hash="synthetic-hash",
            created_at="2026-08-19T00:00:00+00:00",
            updated_at="2026-08-19T00:00:00+00:00",
        )
    )
    identities.save_session(
        SessionRecord(
            token_digest="a" * 64,
            account_id=fixture.student_a_id,
            created_at="2026-08-19T00:00:00+00:00",
            expires_at="2026-08-20T00:00:00+00:00",
            last_seen_at="2026-08-19T00:00:00+00:00",
        )
    )

    account = students.get_account(fixture.student_a_id)
    assert account is not None
    students.save_account(account.model_copy(update={"status": AccountStatus.REVOKED}))

    assert identities.get_credential(fixture.student_a_id) is not None
    assert identities.get_session("a" * 64) is not None
    assert students.get_membership(fixture.student_a_id, fixture.course_a_id) is not None
    assert students.get_course(fixture.course_a_id) is not None
    identities.close()
    students.close()


def test_updating_course_preserves_memberships(tmp_path):
    students = SQLiteStudentRepository(tmp_path / "runtime.sqlite3")
    fixture = seed_synthetic_student_workflow(students)
    course = students.get_course(fixture.course_a_id)
    assert course is not None

    students.save_course(course.model_copy(update={"title": "Updated course title"}))

    assert students.get_course(fixture.course_a_id).title == "Updated course title"
    assert students.get_membership(fixture.student_a_id, fixture.course_a_id) is not None
    students.close()


def test_release_content_is_immutable_and_conversation_is_preserved(tmp_path):
    students = SQLiteStudentRepository(tmp_path / "runtime.sqlite3")
    fixture = seed_synthetic_student_workflow(students)
    conversation = Conversation(
        id="conversation-synthetic",
        student_id=fixture.student_a_id,
        course_id=fixture.course_a_id,
        release_id=fixture.release_a_id,
    )
    students.save_conversation(conversation)
    release = students.get_release(fixture.release_a_id)
    assert release is not None

    with pytest.raises(ValueError, match="immutable"):
        students.save_release(release.model_copy(update={"profile_version": "v2"}))

    assert students.get_release(fixture.release_a_id).profile_version == "v1"
    assert students.get_conversation(conversation.id) == conversation
    students.close()


def test_release_cannot_be_moved_between_courses(tmp_path):
    students = SQLiteStudentRepository(tmp_path / "runtime.sqlite3")
    fixture = seed_synthetic_student_workflow(students)
    release = students.get_release(fixture.release_a_id)
    assert release is not None

    with pytest.raises(ValueError, match="immutable"):
        students.save_release(release.model_copy(update={"course_id": fixture.course_b_id}))

    assert students.get_release(fixture.release_a_id).course_id == fixture.course_a_id
    students.close()


def test_identity_records_reject_noncanonical_or_impossible_state():
    with pytest.raises(ValidationError, match="normalized_email"):
        CredentialRecord(
            account_id="account",
            email="Person@Example.test",
            normalized_email="different@example.test",
            display_name="Person",
            password_hash="synthetic-hash",
            created_at="2026-08-19T00:00:00+00:00",
            updated_at="2026-08-19T00:00:00+00:00",
        )
    with pytest.raises(ValidationError, match="SHA-256"):
        SessionRecord(
            token_digest="g" * 64,
            account_id="account",
            created_at="2026-08-19T00:00:00+00:00",
            expires_at="2026-08-20T00:00:00+00:00",
            last_seen_at="2026-08-19T00:00:00+00:00",
        )
    with pytest.raises(ValidationError, match="expiry"):
        SessionRecord(
            token_digest="a" * 64,
            account_id="account",
            created_at="2026-08-20T00:00:00+00:00",
            expires_at="2026-08-19T00:00:00+00:00",
            last_seen_at="2026-08-20T00:00:00+00:00",
        )


def test_release_defaults_to_draft_and_published_state_requires_passed_evaluation(
    tmp_path,
):
    students = SQLiteStudentRepository(tmp_path / "runtime.sqlite3")
    fixture = seed_synthetic_student_workflow(students)
    release = students.get_release(fixture.release_a_id)
    assert release is not None
    payload = release.model_dump(mode="python", exclude={"status", "evaluation_status"})

    assert DigitalTwinRelease.model_validate(payload).status == StudentReleaseStatus.DRAFT
    with pytest.raises(ValidationError, match="passed evaluation"):
        DigitalTwinRelease.model_validate(
            {
                **payload,
                "status": StudentReleaseStatus.PUBLISHED,
                "evaluation_status": ReleaseEvaluationStatus.PENDING,
            }
        )
    students.close()


def test_repository_cannot_bypass_release_publication_gate(tmp_path):
    students = SQLiteStudentRepository(tmp_path / "runtime.sqlite3")
    fixture = seed_synthetic_student_workflow(students)
    release = students.get_release(fixture.withdrawn_release_id)
    assert release is not None
    draft = release.model_copy(
        update={
            "id": "release-not-evaluated",
            "status": StudentReleaseStatus.DRAFT,
            "evaluation_status": ReleaseEvaluationStatus.PENDING,
        }
    )
    students.save_release(draft)

    with pytest.raises(ValidationError, match="passed evaluation"):
        students.publish_release(draft.id)
    with pytest.raises(ValueError, match="publish_release"):
        students.set_release_status(draft.id, StudentReleaseStatus.PUBLISHED)
    with pytest.raises(ValueError, match="retain passed evaluation"):
        students.set_release_evaluation_status(
            fixture.release_a_id, ReleaseEvaluationStatus.FAILED
        )
    assert students.get_release(draft.id).status == StudentReleaseStatus.DRAFT
    students.close()


def test_repository_preserves_identity_and_course_role_boundaries(tmp_path):
    students = SQLiteStudentRepository(tmp_path / "runtime.sqlite3")
    fixture = seed_synthetic_student_workflow(students)
    student = students.get_account(fixture.student_a_id)
    course = students.get_course(fixture.course_a_id)
    assert student is not None and course is not None

    with pytest.raises(ValueError, match="account role is immutable"):
        students.save_account(student.model_copy(update={"role": AccountRole.PROFESSOR}))
    with pytest.raises(ValueError, match="course ownership is immutable"):
        students.save_course(
            course.model_copy(update={"owner_professor_id": fixture.student_a_id})
        )
    with pytest.raises(ValueError, match="role are inconsistent"):
        students.save_membership(
            CourseMembership(
                account_id=fixture.student_a_id,
                course_id=fixture.course_a_id,
                role=MembershipRole.PROFESSOR,
            )
        )
    students.close()


def test_course_and_owner_membership_are_created_atomically(tmp_path):
    students = SQLiteStudentRepository(tmp_path / "runtime.sqlite3")
    fixture = seed_synthetic_student_workflow(students)
    course = Course(
        id="course-atomic",
        title="Atomic course",
        owner_professor_id=fixture.professor_id,
    )
    membership = CourseMembership(
        account_id=fixture.professor_id,
        course_id=course.id,
        role=MembershipRole.PROFESSOR,
    )
    students._connection.execute(
        """CREATE TRIGGER synthetic_membership_failure
           BEFORE INSERT ON memberships
           WHEN NEW.course_id = 'course-atomic'
           BEGIN SELECT RAISE(ABORT, 'synthetic membership failure'); END"""
    )

    with pytest.raises(sqlite3.IntegrityError, match="synthetic membership failure"):
        students.save_course_with_owner(course, membership)

    assert students.get_course(course.id) is None
    students.close()


def test_account_and_credential_provisioning_is_atomic(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    students = SQLiteStudentRepository(path)
    identities = SQLiteIdentityRepository(path)
    service = IdentityService(identities, students)
    identities._connection.execute(
        """CREATE TRIGGER synthetic_credential_failure
           BEFORE INSERT ON identity_credentials
           WHEN NEW.account_id = 'account-atomic'
           BEGIN SELECT RAISE(ABORT, 'synthetic credential failure'); END"""
    )

    with pytest.raises(sqlite3.IntegrityError, match="synthetic credential failure"):
        service.provision_account(
            account_id="account-atomic",
            email="atomic@example.test",
            display_name="Atomic User",
            role=AccountRole.STUDENT,
            password="Atomic-password-42",
        )

    assert students.get_account("account-atomic") is None
    identities.close()
    students.close()


def test_password_change_and_session_revocation_are_atomic(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    students = SQLiteStudentRepository(path)
    fixture = seed_synthetic_student_workflow(students)
    identities = SQLiteIdentityRepository(path)
    service = IdentityService(identities, students)
    service.provision_account(
        account_id=fixture.student_a_id,
        email="student@example.test",
        display_name="Synthetic Student",
        role=AccountRole.STUDENT,
        password="Student-password-42",
    )
    issued = service.login("student@example.test", "Student-password-42")
    original = identities.get_credential(fixture.student_a_id)
    assert original is not None
    identities._connection.execute(
        """CREATE TRIGGER synthetic_session_revoke_failure
           BEFORE UPDATE OF revoked_at ON identity_sessions
           BEGIN SELECT RAISE(ABORT, 'synthetic session failure'); END"""
    )

    with pytest.raises(sqlite3.IntegrityError, match="synthetic session failure"):
        service.change_password(
            fixture.student_a_id,
            current_password="Student-password-42",
            new_password="Student-new-password-43",
        )

    assert identities.get_credential(fixture.student_a_id).password_hash == (
        original.password_hash
    )
    assert service.authenticate(issued.token).account_id == fixture.student_a_id
    identities.close()
    students.close()


def test_repositories_revalidate_models_copied_with_unchecked_updates(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    students = SQLiteStudentRepository(path)
    fixture = seed_synthetic_student_workflow(students)
    release = students.get_release(fixture.release_a_id)
    assert release is not None
    invalid_release = release.model_copy(
        update={
            "id": "release-invalid-copy",
            "evaluation_status": ReleaseEvaluationStatus.PENDING,
        }
    )

    with pytest.raises(ValidationError, match="passed evaluation"):
        students.save_release(invalid_release)

    identities = SQLiteIdentityRepository(path)
    credential = CredentialRecord(
        account_id=fixture.student_a_id,
        email="student@example.test",
        normalized_email="student@example.test",
        display_name="Student",
        password_hash="synthetic-hash",
        created_at="2026-08-19T00:00:00+00:00",
        updated_at="2026-08-19T00:00:00+00:00",
    )
    invalid_credential = credential.model_copy(
        update={"normalized_email": "different@example.test"}
    )
    with pytest.raises(ValidationError, match="normalized_email"):
        identities.save_credential(invalid_credential)
    identities.close()
    students.close()
