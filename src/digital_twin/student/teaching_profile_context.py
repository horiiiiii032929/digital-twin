"""Explicit development candidate for approved teaching-profile prompt context."""
from __future__ import annotations

from .teaching_profile import TeachingProfileStatus

CANDIDATE_ID = "approved-teaching-profile-context-v1"
PROFILE_FIELDS = (
    "tone", "depth", "explanation_structure", "example_preferences",
    "misconception_handling", "integrity_limits", "help_ladder", "outreach_policy",
)


def profile_authorizes_release(repository, profile, release) -> bool:
    """Prior approval survives replacement only for its exact current release."""
    if (profile is None or release is None or not profile.approved_at or not profile.preview_sha256
            or profile.course_id != release.course_id
            or profile.profile_id != release.teaching_profile_id
            or profile.content_sha256 != release.teaching_profile_sha256):
        return False
    if profile.status == TeachingProfileStatus.APPROVED:
        return True
    if profile.status == TeachingProfileStatus.SUPERSEDED:
        current = repository.get_published_release(release.course_id)
        return current is not None and current.id == release.id and current.teaching_profile_id == profile.profile_id and current.teaching_profile_sha256 == profile.content_sha256
    return False


def approved_teaching_profile_context(repository, release) -> dict:
    """Load only the exact approved profile bound to a current course release.

    Identity and authority remain application-owned. The returned fields are
    pedagogical preferences, never authorization to bypass policy or evidence.
    """
    if release is None or not release.teaching_profile_id:
        raise ValueError("approved teaching-profile context is unavailable")
    profile = repository.get_teaching_profile(release.teaching_profile_id)
    if not profile_authorizes_release(repository, profile, release):
        raise ValueError("approved teaching-profile binding is no longer valid")
    data = profile.model_dump(mode="json")
    return {"configuration_id": CANDIDATE_ID, "content_sha256": profile.content_sha256,
        "preferences": {field: data[field] for field in PROFILE_FIELDS},
        "authority": "Preferences apply only within existing policy, evidence, consent, and allowed actions."}
