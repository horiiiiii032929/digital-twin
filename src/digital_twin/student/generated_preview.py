"""Owned immutable generated samples; approval never runs generation again."""

import hashlib
import json
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .teaching_profile import TeachingProfileError, TeachingProfileStatus
from src.digital_twin.tutor_policy import timestamp_now


def canonical_sha(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()


class GeneratedPreviewCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(min_length=1, max_length=80)
    student_messages: list[str] = Field(min_length=1, max_length=3)


class GeneratedPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1, max_length=128)
    ingestion_job_ids: list[str] = Field(min_length=1, max_length=16)
    concept_label: str = Field(min_length=1, max_length=200)
    concept_description: str = Field(min_length=1, max_length=1000)
    objective: str = Field(min_length=1, max_length=500)
    cases: list[GeneratedPreviewCase] = Field(min_length=1, max_length=4)


class GeneratedPreviewApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    decisions: list[dict[str, str]] = Field(min_length=1, max_length=4)


class GeneratedProfilePreviewService:
    def __init__(self, profiles, *, runner, configuration):
        self.profiles = profiles
        self.repository = profiles.repository
        self.runner = runner
        self.configuration = configuration

    def _profile(self, owner, course, profile_id):
        self.profiles._authorize(owner, course)
        profile = self.repository.get_teaching_profile(profile_id)
        if profile is None or profile.course_id != course:
            raise TeachingProfileError(
                "teaching_profile_not_found", "Teaching profile not found."
            )
        return profile

    def list(self, owner, course, profile_id):
        self._profile(owner, course, profile_id)
        return self.repository.list_generated_profile_previews(course, profile_id)

    def get(self, owner, course, profile_id, artifact_id):
        for artifact in self.list(owner, course, profile_id):
            if artifact["artifact_id"] == artifact_id:
                stored_hash = artifact["artifact_sha256"]
                content = {
                    k: v
                    for k, v in artifact.items()
                    if k not in {"artifact_sha256", "review_status"}
                }
                if canonical_sha(content) != stored_hash:
                    raise TeachingProfileError(
                        "generated_preview_tampered",
                        "Saved preview hash no longer matches.",
                    )
                return artifact
        raise TeachingProfileError(
            "generated_preview_not_found", "Generated preview not found."
        )

    def _bindings(self, profile, snapshot):
        composition = self.configuration()
        return {
            "profile_sha256": profile.content_sha256,
            "source_sha256": canonical_sha(snapshot),
            "configuration_sha256": canonical_sha(composition),
            "composition": composition,
            "sources": snapshot["chunks"],
            "scope": "isolated-single-concept-preview",
        }

    async def create(self, owner, course, profile_id, request, *, resolve_snapshot):
        profile = self._profile(owner, course, profile_id)
        if profile.status != TeachingProfileStatus.DRAFT:
            raise TeachingProfileError(
                "teaching_profile_not_draft", "Generate samples for a draft profile."
            )
        if len({case.case_id for case in request.cases}) != len(request.cases) or any(
            not message.strip() or len(message) > 2000
            for case in request.cases
            for message in case.student_messages
        ):
            raise TeachingProfileError(
                "generated_preview_invalid",
                "Use unique cases and nonblank messages up to 2000 characters.",
            )
        snapshot = resolve_snapshot(request)
        artifact = {
            "artifact_id": f"generated-preview-{uuid4()}",
            "profile_id": profile_id,
            "created_at": timestamp_now(),
            "bindings": self._bindings(profile, snapshot),
            "request": request.model_dump(mode="json"),
            "status": "failed",
            "cases": [],
            "usage": {
                "max_calls": 60,
                "max_cost_usd": 9.6,
                "actual_calls": 0,
                "known_cost_usd": None,
                "unknown_cost_calls": 0,
            },
            "error_code": None,
        }
        try:
            result = await self.runner(
                owner=owner,
                course_id=course,
                profile=profile,
                snapshot=snapshot,
                request=request,
            )
            artifact.update(result)
        except Exception as error:
            artifact["error_code"] = type(error).__name__
        artifact["artifact_sha256"] = canonical_sha(artifact)
        artifact["review_status"] = "unreviewed"
        return self.repository.save_generated_profile_preview(
            artifact, course_id=course, owner_id=owner
        )

    def approve(
        self, owner, course, profile_id, artifact_id, request, *, resolve_snapshot
    ):
        profile = self._profile(owner, course, profile_id)
        artifact = self.get(owner, course, profile_id, artifact_id)
        if profile.status == TeachingProfileStatus.WITHDRAWN:
            raise TeachingProfileError(
                "teaching_profile_withdrawn",
                "Withdrawn profiles cannot be approved again.",
            )
        if artifact["artifact_sha256"] != request.artifact_sha256:
            raise TeachingProfileError(
                "generated_preview_tampered",
                "Approval must match the displayed artifact.",
            )
        current = self._bindings(
            profile,
            resolve_snapshot(
                GeneratedPreviewRequest.model_validate(artifact["request"])
            ),
        )
        if current != artifact["bindings"]:
            raise TeachingProfileError(
                "generated_preview_stale",
                "Profile, sources or composition changed; create a new preview.",
            )
        decisions = request.decisions
        expected = {case["case_id"] for case in artifact["cases"]}
        if (
            len(decisions) != len(expected)
            or {d.get("case_id") for d in decisions} != expected
            or any(
                set(d) != {"case_id", "decision"}
                or d["decision"] not in {"accept", "revise"}
                for d in decisions
            )
        ):
            raise TeachingProfileError(
                "generated_preview_decisions_required",
                "Review every displayed case exactly once.",
            )
        accepted = all(d["decision"] == "accept" for d in decisions)
        if accepted and (
            artifact["status"] != "complete"
            or artifact["usage"]["known_cost_usd"] is None
        ):
            raise TeachingProfileError(
                "generated_preview_incomplete",
                "Incomplete or unaccounted previews cannot be approved.",
            )
        if artifact["review_status"] != "unreviewed":
            self.repository.record_generated_profile_review(
                artifact_id,
                request.artifact_sha256,
                decisions,
                "accepted" if accepted else "needs_revision",
                timestamp_now(),
            )
            return artifact
        if accepted:
            self.repository.approve_teaching_profile_atomic(
                profile_id,
                preview_sha256=request.artifact_sha256,
                changed_at=timestamp_now(),
                generated_review=(artifact_id, decisions),
            )
        else:
            self.repository.record_generated_profile_review(
                artifact_id,
                request.artifact_sha256,
                decisions,
                "needs_revision",
                timestamp_now(),
            )
        return self.get(owner, course, profile_id, artifact_id)
