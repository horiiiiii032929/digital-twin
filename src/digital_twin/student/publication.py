"""Publication controls for the local Digital Twin release boundary."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.onboarding.models import OnboardingSession
from src.digital_twin.student.models import (
    Account,
    AccountRole,
    AccountStatus,
    AuditEvent,
    Course,
    CourseMembership,
    DigitalTwinRelease,
    MembershipRole,
    ProfessorCourseView,
    ProfessorReleaseSummary,
    ReleaseEvaluationStatus,
    ReleasePreflightCheck,
    ReleasePreflightResult,
    StudentReleaseStatus,
)
from src.digital_twin.student.repository import StudentRepository
from src.digital_twin.tutor_policy import (
    KnowledgeSourcePolicy,
    ReleaseStatus,
    SourceLabel,
)


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
        evidence_sufficiency_ready: bool = False,
        teaching_profile_required: bool = False,
        post_publish_hook: Callable[[str, str], None] | None = None,
        retrieval_index_ready: Callable[[DigitalTwinRelease], bool] | None = None,
        retrieval_index_preparer: Callable[[DigitalTwinRelease], None] | None = None,
    ) -> None:
        self.repository = repository
        self.profile_id = profile_id
        self.profile_version = profile_version
        self.evidence_sufficiency_ready = evidence_sufficiency_ready
        self.teaching_profile_required = teaching_profile_required
        self.post_publish_hook = post_publish_hook
        if (retrieval_index_ready is None) != (retrieval_index_preparer is None):
            raise ValueError(
                "retrieval index readiness and preparation must be configured together"
            )
        self.retrieval_index_ready = retrieval_index_ready
        self.retrieval_index_preparer = retrieval_index_preparer

    def create_draft_from_onboarding(
        self,
        professor_id: str,
        course_id: str,
        session: OnboardingSession,
        *,
        chunks: list[DocumentChunk],
        profile_id: str,
        profile_version: str,
        teaching_profile_id: str | None = None,
        teaching_profile_sha256: str | None = None,
        release_id: str | None = None,
    ) -> DigitalTwinRelease:
        self._require_course_owner(professor_id, course_id)
        if session.course_id is None:
            raise PublicationError(
                "onboarding_course_required",
                "Bind the reviewed tutor setup to this course before creating a release.",
            )
        if session.course_id != course_id:
            raise PublicationError(
                "course_scope_violation",
                "The reviewed tutor setup belongs to a different course.",
            )
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
        identifier = release_id.strip() if release_id is not None else f"release-{uuid4()}"
        if not identifier:
            raise PublicationError(
                "release_id_required", "Release identifier cannot be empty."
            )
        if self.repository.get_release(identifier) is not None:
            raise PublicationError(
                "release_exists", "The release identifier already exists."
            )
        draft = DigitalTwinRelease(
            id=identifier,
            course_id=course_id,
            profile_id=profile_id,
            profile_version=profile_version,
            teaching_profile_id=teaching_profile_id,
            teaching_profile_sha256=teaching_profile_sha256,
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

    def create_course(
        self,
        professor_id: str,
        title: str,
        *,
        course_id: str | None = None,
    ) -> Course:
        self._require_active_professor(professor_id)
        normalized_title = title.strip()
        if not normalized_title:
            raise PublicationError("course_title_required", "Course title is required.")
        identifier = course_id.strip() if course_id is not None else f"course-{uuid4()}"
        if not identifier:
            raise PublicationError(
                "course_id_required", "Course identifier cannot be empty."
            )
        course = Course(
            id=identifier,
            title=normalized_title,
            owner_professor_id=professor_id,
        )
        if self.repository.get_course(course.id) is not None:
            raise PublicationError(
                "course_exists", "The course identifier already exists."
            )
        self.repository.save_course_with_owner(
            course,
            CourseMembership(
                account_id=professor_id,
                course_id=course.id,
                role=MembershipRole.PROFESSOR,
            ),
        )
        return course

    def list_courses(self, professor_id: str) -> list[ProfessorCourseView]:
        self._require_active_professor(professor_id)
        views: list[ProfessorCourseView] = []
        for course in self.repository.list_professor_courses(professor_id):
            students = [
                membership.account_id
                for membership in self.repository.list_course_memberships(course.id)
                if membership.role == MembershipRole.STUDENT and membership.active
            ]
            releases = [
                ProfessorReleaseSummary(
                    id=release.id,
                    course_id=release.course_id,
                    status=release.status,
                    evaluation_status=release.evaluation_status,
                    policy_version=release.policy_version,
                    chunk_count=len(release.chunks),
                    created_at=release.created_at,
                )
                for release in self.repository.list_course_releases(course.id)
            ]
            views.append(
                ProfessorCourseView(
                    course_id=course.id,
                    title=course.title,
                    student_account_ids=students,
                    releases=releases,
                )
            )
        return views

    def assign_student(
        self,
        professor_id: str,
        course_id: str,
        student_id: str,
    ) -> CourseMembership:
        self._require_course_owner(professor_id, course_id)
        student = self.repository.get_account(student_id)
        if student is None:
            raise PublicationError("account_not_found", "The student was not found.")
        if (
            student.status != AccountStatus.ACTIVE
            or student.role != AccountRole.STUDENT
        ):
            raise PublicationError(
                "student_role_required", "An active student account is required."
            )
        return self.repository.save_membership(
            CourseMembership(
                account_id=student.id,
                course_id=course_id,
                role=MembershipRole.STUDENT,
            )
        )

    def record_evaluation(
        self,
        professor_id: str,
        release_id: str,
        status: ReleaseEvaluationStatus,
    ) -> DigitalTwinRelease:
        release = self._require_owned_release(professor_id, release_id)
        self.repository.set_release_evaluation_status(release.id, status)
        return self._require_release(release.id)

    def run_preflight(
        self, professor_id: str, release_id: str
    ) -> ReleasePreflightResult:
        """Run deterministic release gates and persist their aggregate outcome."""

        release = self._require_owned_release(professor_id, release_id)
        index_preparation_failed = False
        if (
            self.retrieval_index_ready is not None
            and self.retrieval_index_preparer is not None
        ):
            try:
                self._prepare_retrieval_index(release)
            except PublicationError:
                index_preparation_failed = True
        checks = [
            ReleasePreflightCheck(
                id="active-profile",
                label="Selected component profile",
                passed=(
                    release.profile_id == self.profile_id
                    and release.profile_version == self.profile_version
                ),
                detail=(
                    f"Release uses {release.profile_id} {release.profile_version}; "
                    f"runtime expects {self.profile_id} {self.profile_version}."
                ),
            ),
            ReleasePreflightCheck(
                id="evidence-sufficiency",
                label="Evidence sufficiency selection",
                passed=self.evidence_sufficiency_ready,
                detail=(
                    "A product release requires a selected evidence-sufficiency "
                    "method; the runtime otherwise abstains before generation."
                ),
            ),
            ReleasePreflightCheck(
                id="approved-policy",
                label="Professor policy approval",
                passed=release.policy.release_status == ReleaseStatus.APPROVED,
                detail=(
                    "The policy has explicit professor approval."
                    if release.policy.release_status == ReleaseStatus.APPROVED
                    else "The policy still has unresolved review or approval blockers."
                ),
            ),
            ReleasePreflightCheck(
                id="approved-teaching-profile",
                label="Approved professor teaching profile",
                passed=(
                    not self.teaching_profile_required
                    or (
                        release.teaching_profile_id is not None
                        and release.teaching_profile_sha256 is not None
                    )
                ),
                detail=(
                    "The release is hash-bound to an explicitly approved teaching profile."
                    if release.teaching_profile_id is not None
                    else "The qualified autonomous profile requires professor-approved teaching behavior."
                ),
            ),
            ReleasePreflightCheck(
                id="approved-evidence",
                label="Approved retrieval evidence",
                passed=bool(release.chunks)
                and all(chunk.retrieval_allowed for chunk in release.chunks),
                detail=(
                    f"{len(release.chunks)} chunk(s) are included; every chunk must be approved for tutoring."
                ),
            ),
            ReleasePreflightCheck(
                id="course-scope",
                label="Course isolation",
                passed=bool(release.chunks)
                and all(
                    chunk.metadata.get("course_id") == release.course_id
                    for chunk in release.chunks
                ),
                detail="Every release chunk must carry the owning course identifier.",
            ),
            ReleasePreflightCheck(
                id="active-source-versions",
                label="Single active source version",
                passed=bool(release.chunks)
                and _source_versions_are_unambiguous(release.chunks),
                detail=(
                    "Every source artifact must contribute exactly one approved "
                    "version to the release."
                ),
            ),
            ReleasePreflightCheck(
                id="source-policy",
                label="Professor source policy",
                passed=bool(release.chunks)
                and _source_labels_match_policy(release.chunks, release.policy),
                detail=(
                    "Every release source must be explicitly approved and permitted "
                    "by the professor's selected source strictness."
                ),
            ),
            ReleasePreflightCheck(
                id="citation-lineage",
                label="Citation lineage",
                passed=bool(release.chunks)
                and all(
                    chunk.source_artifact_id
                    and chunk.source_checksum
                    and chunk.locator
                    and isinstance(chunk.metadata.get("title"), str)
                    and bool(chunk.metadata["title"].strip())
                    for chunk in release.chunks
                )
                and _citation_locations_are_unique(release.chunks),
                detail=(
                    "Every chunk must retain a source artifact, checksum, title, "
                    "and unambiguous locator."
                ),
            ),
        ]
        if self.retrieval_index_ready is not None:
            try:
                index_ready = (
                    not index_preparation_failed
                    and bool(self.retrieval_index_ready(release))
                )
            except Exception:
                index_ready = False
            checks.append(
                ReleasePreflightCheck(
                    id="retrieval-index",
                    label="Immutable retrieval index",
                    passed=index_ready,
                    detail=(
                        "The exact release-bound retrieval index is available."
                        if index_ready
                        else "Build and verify the exact release-bound retrieval index."
                    ),
                )
            )
        passed = all(check.passed for check in checks)
        evaluation_persisted = release.status != StudentReleaseStatus.PUBLISHED
        if evaluation_persisted:
            self.repository.set_release_evaluation_status(
                release.id,
                ReleaseEvaluationStatus.PASSED
                if passed
                else ReleaseEvaluationStatus.FAILED,
            )
        self.repository.save_audit_event(
            AuditEvent(
                id=f"audit-{uuid4()}",
                event_type="release.preflight_completed",
                account_id=professor_id,
                course_id=release.course_id,
                release_id=release.id,
                details={
                    "passed": passed,
                    "passed_checks": sum(check.passed for check in checks),
                    "total_checks": len(checks),
                    "evaluation_persisted": evaluation_persisted,
                },
            )
        )
        return ReleasePreflightResult(
            release_id=release.id,
            passed=passed,
            checks=checks,
        )

    def publish(self, professor_id: str, release_id: str) -> DigitalTwinRelease:
        release = self._require_owned_release(professor_id, release_id)
        self._require_publishable(release)
        self._prepare_retrieval_index(release)
        self.repository.publish_release(release.id)
        published = self._require_release(release.id)
        self._run_post_publish_hook(professor_id, published)
        return published

    def withdraw(self, professor_id: str, release_id: str) -> DigitalTwinRelease:
        release = self._require_owned_release(professor_id, release_id)
        if release.status != StudentReleaseStatus.PUBLISHED:
            raise PublicationError(
                "release_not_published",
                "Only the current published release can be withdrawn.",
            )
        self.repository.set_release_status(release.id, StudentReleaseStatus.WITHDRAWN)
        return self._require_release(release.id)

    def rollback(self, professor_id: str, release_id: str) -> DigitalTwinRelease:
        release = self._require_owned_release(professor_id, release_id)
        if release.status != StudentReleaseStatus.WITHDRAWN:
            raise PublicationError(
                "release_not_withdrawn",
                "Rollback requires a previously withdrawn release.",
            )
        self._require_publishable(release)
        self._prepare_retrieval_index(release)
        self.repository.publish_release(release.id)
        return self._require_release(release.id)

    def _run_post_publish_hook(
        self,
        professor_id: str,
        release: DigitalTwinRelease,
    ) -> None:
        """Observe a completed publication without changing its transaction result."""

        if self.post_publish_hook is None:
            return
        try:
            self.post_publish_hook(professor_id, release.course_id)
        except Exception as error:
            self.repository.save_audit_event(
                AuditEvent(
                    id=f"audit-{uuid4()}",
                    event_type="release.post_publish_hook_failed",
                    account_id=professor_id,
                    course_id=release.course_id,
                    release_id=release.id,
                    details={
                        "hook": "proactive-evidence-recovery-shadow",
                        "error_type": type(error).__name__,
                        "publication_preserved": True,
                    },
                )
            )

    def _prepare_retrieval_index(self, release: DigitalTwinRelease) -> None:
        if self.retrieval_index_preparer is None:
            return
        try:
            self.retrieval_index_preparer(release)
        except Exception as error:
            raise PublicationError(
                "retrieval_index_not_ready",
                "The immutable retrieval index could not be prepared for this release.",
            ) from error

    def _require_publishable(self, release: DigitalTwinRelease) -> None:
        if (
            release.profile_id != self.profile_id
            or release.profile_version != self.profile_version
        ):
            raise PublicationError(
                "profile_mismatch",
                "The release profile does not match the active component profile.",
            )
        if not self.evidence_sufficiency_ready:
            raise PublicationError(
                "evidence_sufficiency_required",
                "Select and configure an evidence-sufficiency method before publication.",
            )
        if self.teaching_profile_required and (
            release.teaching_profile_id is None
            or release.teaching_profile_sha256 is None
        ):
            raise PublicationError(
                "teaching_profile_required",
                "Attach an approved professor teaching profile before publication.",
            )
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
        if len({chunk.id for chunk in release.chunks}) != len(release.chunks):
            raise PublicationError(
                "source_scope_not_ready", "Release chunk identifiers must be unique."
            )
        if not _citation_locations_are_unique(release.chunks):
            raise PublicationError(
                "source_scope_not_ready",
                "Release citation locations must identify exactly one chunk.",
            )
        if not _source_versions_are_unambiguous(release.chunks):
            raise PublicationError(
                "source_scope_not_ready",
                "A release cannot mix versions of the same source artifact.",
            )
        if not _source_labels_match_policy(release.chunks, release.policy):
            raise PublicationError(
                "source_scope_not_ready",
                "Release sources do not satisfy the professor-approved source policy.",
            )
        if any(
            chunk.metadata.get("course_id") != release.course_id
            or not chunk.source_artifact_id
            or not chunk.source_checksum
            or not chunk.locator
            or not isinstance(chunk.metadata.get("title"), str)
            or not chunk.metadata["title"].strip()
            for chunk in release.chunks
        ):
            raise PublicationError(
                "source_scope_not_ready",
                "Release evidence must retain exact course scope and citation lineage.",
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
        self._require_active_professor(professor_id)
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

    def _require_active_professor(self, professor_id: str) -> Account:
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
        return account


def _validate_chunk_course_scope(chunks: list[DocumentChunk], course_id: str) -> None:
    seen_ids: set[str] = set()
    for chunk in chunks:
        chunk_course_id = chunk.metadata.get("course_id")
        if chunk.id in seen_ids or chunk_course_id != course_id:
            raise PublicationError(
                "course_scope_violation",
                "Release chunks must be unique and belong to the selected course.",
            )
        seen_ids.add(chunk.id)
    if not _citation_locations_are_unique(chunks):
        raise PublicationError(
            "course_scope_violation",
            "Release citation locations must identify exactly one chunk.",
        )


def _citation_locations_are_unique(chunks: list[DocumentChunk]) -> bool:
    locations = [
        (chunk.document_id, chunk.locator or f"chunk {chunk.ordinal + 1}")
        for chunk in chunks
    ]
    return len(locations) == len(set(locations))


def _source_versions_are_unambiguous(chunks: list[DocumentChunk]) -> bool:
    versions: dict[str, set[int]] = {}
    for chunk in chunks:
        source_id = chunk.source_artifact_id or chunk.document_id
        versions.setdefault(source_id, set()).add(chunk.source_version)
    return all(len(source_versions) == 1 for source_versions in versions.values())


def _source_labels_match_policy(chunks, policy) -> bool:
    field = next(
        (item for item in policy.all_fields if item.id == "knowledge_source_policy"),
        None,
    )
    if field is None or not isinstance(field.value, dict):
        return False
    try:
        source_policy = KnowledgeSourcePolicy.model_validate(field.value)
    except ValueError:
        return False
    allowed = {SourceLabel.COURSE_APPROVED}
    if source_policy.source_strictness != "course_only":
        allowed.update(
            {
                SourceLabel.PROFESSOR_APPROVED_EXTERNAL,
                SourceLabel.SYSTEM_SUGGESTED_TRUSTED,
            }
        )
    return all(chunk.source_label in allowed for chunk in chunks)
