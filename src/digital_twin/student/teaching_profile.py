"""Explicit, professor-approved teaching-profile lifecycle for R1."""

from __future__ import annotations

from enum import StrEnum
import hashlib
import json
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.digital_twin.tutor_policy import timestamp_now


class TeachingProfileStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


class TeachingProfileDepth(StrEnum):
    CONCISE = "concise"
    BALANCED = "balanced"
    DETAILED = "detailed"


class TeachingProfileV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    profile_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    status: TeachingProfileStatus = TeachingProfileStatus.DRAFT
    tone: str = Field(min_length=1, max_length=240)
    depth: TeachingProfileDepth
    explanation_structure: list[str] = Field(min_length=1, max_length=6)
    example_preferences: list[str] = Field(default_factory=list, max_length=8)
    misconception_handling: str = Field(min_length=1, max_length=1_000)
    integrity_limits: str = Field(min_length=1, max_length=1_000)
    help_ladder: list[str] = Field(min_length=2, max_length=6)
    outreach_policy: str = Field(min_length=1, max_length=1_000)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    preview_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    created_at: str = Field(default_factory=timestamp_now)
    approved_at: str | None = None
    withdrawn_at: str | None = None

    @field_validator(
        "tone", "misconception_handling", "integrity_limits", "outreach_policy"
    )
    @classmethod
    def text_must_be_trimmed(cls, value: str) -> str:
        normalized = value.strip()
        if normalized != value or not normalized:
            raise ValueError("teaching-profile text must be non-blank and trimmed")
        return value

    @field_validator("explanation_structure", "example_preferences", "help_ladder")
    @classmethod
    def lists_must_be_unique_and_trimmed(cls, value: list[str]) -> list[str]:
        if any(not item.strip() or item.strip() != item for item in value):
            raise ValueError("teaching-profile list items must be trimmed")
        if len(value) != len(set(value)):
            raise ValueError("teaching-profile list items must be unique")
        return value

    @model_validator(mode="after")
    def lifecycle_fields_must_match_status(self) -> "TeachingProfileV1":
        if self.status == TeachingProfileStatus.APPROVED and (
            self.approved_at is None or self.preview_sha256 is None
        ):
            raise ValueError("approved profile requires approval and preview binding")
        if self.status == TeachingProfileStatus.WITHDRAWN and self.withdrawn_at is None:
            raise ValueError("withdrawn profile requires a withdrawal timestamp")
        return self


class TeachingProfilePreviewCaseV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    student_situation: str
    expected_behavior: str


class TeachingProfilePreviewV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    profile_id: str
    profile_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cases: list[TeachingProfilePreviewCaseV1] = Field(min_length=10, max_length=10)
    preview_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def teaching_profile_content_sha256(values: dict) -> str:
    authoritative = {
        key: values[key]
        for key in (
            "course_id",
            "version",
            "tone",
            "depth",
            "explanation_structure",
            "example_preferences",
            "misconception_handling",
            "integrity_limits",
            "help_ladder",
            "outreach_policy",
        )
    }
    return hashlib.sha256(
        json.dumps(
            authoritative, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()


def build_teaching_profile_preview(profile: TeachingProfileV1) -> TeachingProfilePreviewV1:
    situations = (
        ("direct-question", "Answer directly at the approved depth and cite evidence."),
        ("partial-attempt", "Acknowledge the attempt and give the next bounded hint."),
        ("misconception", profile.misconception_handling),
        ("repeated-confusion", "Move one step up the approved help ladder."),
        ("ambiguous-question", "Ask one focused clarification question."),
        ("no-evidence", "Abstain and explain what evidence is missing."),
        ("assessed-work", profile.integrity_limits),
        ("request-for-example", "Use an approved example preference when possible."),
        ("proactive-review", profile.outreach_policy),
        ("provider-failure", "Fail closed without inventing academic content."),
    )
    cases = [
        TeachingProfilePreviewCaseV1(
            case_id=f"profile-preview-{index:02d}",
            student_situation=situation,
            expected_behavior=behavior,
        )
        for index, (situation, behavior) in enumerate(situations, start=1)
    ]
    payload = {
        "profile_id": profile.profile_id,
        "profile_content_sha256": profile.content_sha256,
        "cases": [row.model_dump(mode="json") for row in cases],
    }
    preview_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return TeachingProfilePreviewV1(**payload, preview_sha256=preview_hash)


def new_teaching_profile(*, course_id: str, version: int, values: dict) -> TeachingProfileV1:
    payload = {"course_id": course_id, "version": version, **values}
    return TeachingProfileV1(
        profile_id=f"teaching-profile-{uuid4()}",
        **payload,
        content_sha256=teaching_profile_content_sha256(payload),
    )


class TeachingProfileError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class TeachingProfileService:
    """Professor-owned lifecycle; models cannot mutate or activate profiles."""

    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def _authorize(self, professor_id: str, course_id: str) -> None:
        course = self.repository.get_course(course_id)
        membership = self.repository.get_membership(professor_id, course_id)
        if (
            course is None
            or course.owner_professor_id != professor_id
            or membership is None
            or membership.role.value != "professor"
            or not membership.active
        ):
            raise TeachingProfileError(
                "course_forbidden", "Only the course owner may manage its teaching profile."
            )

    def list(self, professor_id: str, course_id: str) -> list[TeachingProfileV1]:
        self._authorize(professor_id, course_id)
        return self.repository.list_teaching_profiles(course_id)

    def require_approved(
        self, professor_id: str, course_id: str, profile_id: str
    ) -> TeachingProfileV1:
        """Resolve a profile that the owning professor explicitly approved."""

        self._authorize(professor_id, course_id)
        profile = self.repository.get_teaching_profile(profile_id)
        if profile is None or profile.course_id != course_id:
            raise TeachingProfileError(
                "teaching_profile_not_found", "The teaching profile was not found."
            )
        if profile.status != TeachingProfileStatus.APPROVED:
            raise TeachingProfileError(
                "teaching_profile_not_approved",
                "Only an approved teaching profile can be attached to a release.",
            )
        return profile

    def create_draft(
        self, professor_id: str, course_id: str, values: dict
    ) -> TeachingProfileV1:
        self._authorize(professor_id, course_id)
        profiles = self.repository.list_teaching_profiles(course_id)
        version = max((profile.version for profile in profiles), default=0) + 1
        try:
            profile = new_teaching_profile(
                course_id=course_id, version=version, values=values
            )
            return self.repository.save_teaching_profile(profile)
        except (TypeError, ValueError) as error:
            raise TeachingProfileError(
                "teaching_profile_invalid", str(error)
            ) from error

    def preview(
        self, professor_id: str, course_id: str, profile_id: str
    ) -> TeachingProfilePreviewV1:
        self._authorize(professor_id, course_id)
        profile = self.repository.get_teaching_profile(profile_id)
        if profile is None or profile.course_id != course_id:
            raise TeachingProfileError(
                "teaching_profile_not_found", "The teaching profile was not found."
            )
        if profile.status != TeachingProfileStatus.DRAFT:
            raise TeachingProfileError(
                "teaching_profile_not_draft", "Only a draft profile can be previewed."
            )
        return build_teaching_profile_preview(profile)

    def approve(
        self,
        professor_id: str,
        course_id: str,
        profile_id: str,
        *,
        preview_sha256: str,
    ) -> TeachingProfileV1:
        preview = self.preview(professor_id, course_id, profile_id)
        if preview.preview_sha256 != preview_sha256:
            raise TeachingProfileError(
                "teaching_profile_preview_drifted",
                "Approval must bind to the current ten-case preview.",
            )
        changed_at = timestamp_now()
        for current in self.repository.list_teaching_profiles(course_id):
            if current.status == TeachingProfileStatus.APPROVED:
                self.repository.set_teaching_profile_status(
                    current.profile_id,
                    TeachingProfileStatus.SUPERSEDED,
                    preview_sha256=None,
                    changed_at=changed_at,
                )
        return self.repository.set_teaching_profile_status(
            profile_id,
            TeachingProfileStatus.APPROVED,
            preview_sha256=preview_sha256,
            changed_at=changed_at,
        )

    def withdraw(
        self, professor_id: str, course_id: str, profile_id: str
    ) -> TeachingProfileV1:
        self._authorize(professor_id, course_id)
        profile = self.repository.get_teaching_profile(profile_id)
        if profile is None or profile.course_id != course_id:
            raise TeachingProfileError(
                "teaching_profile_not_found", "The teaching profile was not found."
            )
        if profile.status not in {
            TeachingProfileStatus.DRAFT,
            TeachingProfileStatus.APPROVED,
        }:
            raise TeachingProfileError(
                "teaching_profile_not_withdrawable",
                "The teaching profile cannot be withdrawn from its current state.",
            )
        return self.repository.set_teaching_profile_status(
            profile_id,
            TeachingProfileStatus.WITHDRAWN,
            preview_sha256=None,
            changed_at=timestamp_now(),
        )
