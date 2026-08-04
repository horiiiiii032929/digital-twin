from pydantic import BaseModel

from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.student.models import (
    Account,
    AccountRole,
    AccountStatus,
    Course,
    CourseMembership,
    DigitalTwinRelease,
    MembershipRole,
    StudentReleaseStatus,
)
from src.digital_twin.student.repository import StudentRepository
from src.digital_twin.tutor_policy import (
    FieldStatus,
    ReleaseStatus,
    SourceLabel,
    TutorPolicy,
    build_initial_policy,
)


class SyntheticStudentFixture(BaseModel):
    professor_id: str = "professor-synthetic"
    student_a_id: str = "student-a-synthetic"
    student_b_id: str = "student-b-synthetic"
    revoked_student_id: str = "student-revoked-synthetic"
    course_a_id: str = "course-a-synthetic"
    course_b_id: str = "course-b-synthetic"
    release_a_id: str = "release-a-v1-synthetic"
    release_b_id: str = "release-b-v1-synthetic"
    withdrawn_release_id: str = "release-a-v0-withdrawn-synthetic"


def approved_synthetic_policy() -> TutorPolicy:
    policy = build_initial_policy()
    for field in policy.all_fields:
        field.status = FieldStatus.RESOLVED
        if field.id == "professor_release_approval":
            field.value = "approved"
        elif field.id == "knowledge_source_policy" and isinstance(field.value, dict):
            field.value = {
                **field.value,
                "confirmed": True,
                "source_strictness": "course_only",
            }
    policy.status = ReleaseStatus.APPROVED
    policy.release_status = ReleaseStatus.APPROVED
    return policy


def seed_synthetic_student_workflow(
    repository: StudentRepository,
) -> SyntheticStudentFixture:
    fixture = SyntheticStudentFixture()
    accounts = [
        Account(id=fixture.professor_id, role=AccountRole.PROFESSOR),
        Account(id=fixture.student_a_id, role=AccountRole.STUDENT),
        Account(id=fixture.student_b_id, role=AccountRole.STUDENT),
        Account(
            id=fixture.revoked_student_id,
            role=AccountRole.STUDENT,
            status=AccountStatus.REVOKED,
        ),
    ]
    for account in accounts:
        repository.save_account(account)

    course_a = Course(
        id=fixture.course_a_id,
        title="Synthetic systems course",
        owner_professor_id=fixture.professor_id,
    )
    course_b = Course(
        id=fixture.course_b_id,
        title="Synthetic policy course",
        owner_professor_id=fixture.professor_id,
    )
    repository.save_course(course_a)
    repository.save_course(course_b)
    for membership in [
        CourseMembership(
            account_id=fixture.professor_id,
            course_id=fixture.course_a_id,
            role=MembershipRole.PROFESSOR,
        ),
        CourseMembership(
            account_id=fixture.professor_id,
            course_id=fixture.course_b_id,
            role=MembershipRole.PROFESSOR,
        ),
        CourseMembership(
            account_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            role=MembershipRole.STUDENT,
        ),
        CourseMembership(
            account_id=fixture.student_b_id,
            course_id=fixture.course_b_id,
            role=MembershipRole.STUDENT,
        ),
        CourseMembership(
            account_id=fixture.revoked_student_id,
            course_id=fixture.course_a_id,
            role=MembershipRole.STUDENT,
        ),
    ]:
        repository.save_membership(membership)

    policy = approved_synthetic_policy()
    release_a = DigitalTwinRelease(
        id=fixture.release_a_id,
        course_id=fixture.course_a_id,
        profile_id="student-tutor",
        profile_version="v1",
        policy_version=1,
        policy=policy,
        chunks=[
            _chunk(
                "cache",
                "document-cache",
                "Cache coherence keeps replicated processor data consistent.",
                "page 2",
                fixture.course_a_id,
            ),
            _chunk(
                "memory",
                "document-memory",
                "Virtual memory maps process addresses to physical memory pages.",
                "page 4",
                fixture.course_a_id,
            ),
        ],
    )
    release_b = DigitalTwinRelease(
        id=fixture.release_b_id,
        course_id=fixture.course_b_id,
        profile_id="student-tutor",
        profile_version="v1",
        policy_version=1,
        policy=policy,
        chunks=[
            _chunk(
                "policy",
                "document-policy",
                "A release policy defines approval and withdrawal controls.",
                "section 1",
                fixture.course_b_id,
            )
        ],
    )
    withdrawn = release_a.model_copy(
        update={
            "id": fixture.withdrawn_release_id,
            "status": StudentReleaseStatus.WITHDRAWN,
            "created_at": "2026-08-01T00:00:00+00:00",
        },
        deep=True,
    )
    repository.save_release(withdrawn)
    repository.save_release(release_a)
    repository.save_release(release_b)
    return fixture


def _chunk(
    identifier: str,
    document_id: str,
    text: str,
    locator: str,
    course_id: str,
) -> DocumentChunk:
    return DocumentChunk(
        id=f"chunk-{identifier}-synthetic",
        document_id=document_id,
        text=text,
        ordinal=0,
        source_artifact_id=f"source-{identifier}-synthetic",
        source_version=1,
        source_label=SourceLabel.COURSE_APPROVED,
        locator=locator,
        retrieval_allowed=True,
        metadata={"title": f"Synthetic {identifier} notes", "course_id": course_id},
    )
