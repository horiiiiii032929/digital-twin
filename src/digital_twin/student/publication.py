"""Publication controls for the local Digital Twin release boundary."""

from __future__ import annotations

from uuid import uuid4

from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.onboarding.models import OnboardingSession
from src.digital_twin.student.models import (
    AccountRole,
    AccountStatus,
    Course,
    DigitalTwinRelease,
    MembershipRole,
    ReleaseEvaluationStatus,
    StudentReleaseStatus,
)
from src.digital_twin.student.repository import StudentRepository
from src.digital_twin.tutor_policy import ReleaseStatus


class PublicationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ReleaseLifecycleService:
    """Create and operate immutable-content releases with explicit gates."""

    def __init__(
        self,
        repository: StudentRepository,
        *,
        profile_id: str = "student-tutor",
        profile_version: str = "v1",
    ) -> None:
        self.repository = repository
        self.profile_id = profile_id
        self.profile_version = profile_version

    def create_draft_from_onboarding(
        self,
        professor_id: str,
        course_id: str,
        session: OnboardingSession,
        *,
        chunks: list[DocumentChunk],
        profile_id: str,
        profile_version: str,
        release_id: str | None = None,
    ) -> DigitalTwinRelease:
        self._require_course_owner(professor_id, course_id)
        if session.policy is None:
            raise PublicationError(
                "policy_not_ready",
                "Complete the onboarding interview before creating a release draft.",
            )
        if profile_id != self.profile_id or profile_version != self.profile_version:
            raise PublicationError(
                "profile_mismatch",
                "The release profile does not match the active component profile.",
            )
        _validate_chunk_course_scope(chunks, course_id)
        draft = DigitalTwinRelease(
            id=release_id or f"release-{uuid4()}",
            course_id=course_id,
            profile_id=profile_id,
            profile_version=profile_version,
            policy_version=session.policy_version,
            policy=session.policy,
            chunks=[chunk.model_copy(deep=True) for chunk in chunks],
            status=StudentReleaseStatus.DRAFT,
            evaluation_status=ReleaseEvaluationStatus.PENDING,
        )
        return self.repository.save_release(draft)

    def authorize_source_ingestion(self, professor_id: str, course_id: str) -> None:
        """Apply the same ownership boundary before source bytes are processed."""

        self._require_course_owner(professor_id, course_id)

    def record_evaluation(
        self,
        professor_id: str,
        release_id: str,
        status: ReleaseEvaluationStatus,
    ) -> DigitalTwinRelease:
        release = self._require_owned_release(professor_id, release_id)
        self.repository.set_release_evaluation_status(release.id, status)
        return self._require_release(release.id)

    def publish(self, professor_id: str, release_id: str) -> DigitalTwinRelease:
        release = self._require_owned_release(professor_id, release_id)
        self._require_publishable(release)
        self.repository.publish_release(release.id)
        return self._require_release(release.id)

    def withdraw(self, professor_id: str, release_id: str) -> DigitalTwinRelease:
        release = self._require_owned_release(professor_id, release_id)
        if release.status != StudentReleaseStatus.PUBLISHED:
            raise PublicationError(
                "release_not_published",
                "Only the current published release can be withdrawn.",
            )
        self.repository.set_release_status(
            release.id, StudentReleaseStatus.WITHDRAWN
        )
        return self._require_release(release.id)

    def rollback(self, professor_id: str, release_id: str) -> DigitalTwinRelease:
        release = self._require_owned_release(professor_id, release_id)
        if release.status != StudentReleaseStatus.WITHDRAWN:
            raise PublicationError(
                "release_not_withdrawn",
                "Rollback requires a previously withdrawn release.",
            )
        self._require_publishable(release)
        self.repository.publish_release(release.id)
        return self._require_release(release.id)

    def _require_publishable(self, release: DigitalTwinRelease) -> None:
        if release.evaluation_status == ReleaseEvaluationStatus.PENDING:
            raise PublicationError(
                "evaluation_required",
                "A release must pass evaluation before publication.",
            )
        if release.evaluation_status == ReleaseEvaluationStatus.FAILED:
            raise PublicationError(
                "evaluation_failed",
                "The release failed evaluation and cannot be published.",
            )
        if release.policy.release_status != ReleaseStatus.APPROVED:
            raise PublicationError(
                "release_blocked",
                "Resolve all professor policy and preview blockers before publication.",
            )
        if not release.chunks or any(
            not chunk.retrieval_allowed for chunk in release.chunks
        ):
            raise PublicationError(
                "source_scope_not_ready",
                "A published release requires at least one approved tutoring chunk.",
            )

    def _require_owned_release(
        self, professor_id: str, release_id: str
    ) -> DigitalTwinRelease:
        release = self._require_release(release_id)
        self._require_course_owner(professor_id, release.course_id)
        return release

    def _require_release(self, release_id: str) -> DigitalTwinRelease:
        release = self.repository.get_release(release_id)
        if release is None:
            raise PublicationError("release_not_found", "The release was not found.")
        return release

    def _require_course_owner(self, professor_id: str, course_id: str) -> Course:
        account = self.repository.get_account(professor_id)
        if account is None:
            raise PublicationError(
                "account_not_found", "The professor account was not found."
            )
        if account.status != AccountStatus.ACTIVE:
            raise PublicationError(
                "account_inactive", "The professor account is inactive or revoked."
            )
        if account.role != AccountRole.PROFESSOR:
            raise PublicationError(
                "professor_role_required", "A professor account is required."
            )
        course = self.repository.get_course(course_id)
        membership = self.repository.get_membership(professor_id, course_id)
        if (
            course is None
            or course.owner_professor_id != professor_id
            or membership is None
            or not membership.active
            or membership.role != MembershipRole.PROFESSOR
        ):
            raise PublicationError(
                "course_access_denied",
                "The professor does not own or manage this course.",
            )
        return course


def _validate_chunk_course_scope(chunks: list[DocumentChunk], course_id: str) -> None:
    for chunk in chunks:
        chunk_course_id = chunk.metadata.get("course_id")
        if chunk_course_id is not None and chunk_course_id != course_id:
            raise PublicationError(
                "course_scope_violation",
                "A release chunk belongs to a different course.",
            )
