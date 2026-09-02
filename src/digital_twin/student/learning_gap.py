"""Privacy-preserving learning-gap signals and deterministic aggregation."""

from __future__ import annotations

import hashlib
import hmac
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_DIGEST = re.compile(r"[0-9a-f]{64}")
_TOPIC_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


class LearningGapSignalKind(StrEnum):
    CONFUSION = "confusion"
    MISCONCEPTION = "misconception"
    REPEATED_HELP = "repeated-help"
    NO_EVIDENCE = "no-evidence"
    VALIDATION_FALLBACK = "validation-fallback"
    INTEGRITY_REDIRECT = "integrity-redirect"


class LearningGapEvidenceStatus(StrEnum):
    SUPPORTED = "supported"
    NO_EVIDENCE = "no-evidence"
    VALIDATION_FALLBACK = "validation-fallback"
    CLARIFIED = "clarified"
    REFUSED = "refused"


class LearningGapPrivacyPolicyV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    minimum_distinct_learners: int = Field(default=5, ge=3, le=100)
    retention_days: int = Field(default=90, ge=1, le=365)


class LearningGapSignalV1(BaseModel):
    """A storage-safe event that contains no raw student content or direct IDs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    signal_id: str
    source_turn_key: str
    learner_key: str
    course_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    topic_key: str
    signal_kind: LearningGapSignalKind
    tutoring_intent: str = Field(min_length=1, max_length=80)
    help_level: int = Field(ge=0, le=3)
    confusion_band: Literal["low", "medium", "high"]
    evidence_status: LearningGapEvidenceStatus
    observed_at: str
    expires_at: str

    @field_validator("signal_id", "source_turn_key", "learner_key")
    @classmethod
    def pseudonymous_keys_must_be_sha256(cls, value: str) -> str:
        normalized = value.casefold()
        if _DIGEST.fullmatch(normalized) is None:
            raise ValueError("learning-gap pseudonymous keys must be SHA-256 digests")
        return normalized

    @field_validator("topic_key")
    @classmethod
    def topic_key_must_be_a_bounded_identifier(cls, value: str) -> str:
        if _TOPIC_KEY.fullmatch(value) is None:
            raise ValueError("topic_key must be a bounded course-taxonomy identifier")
        return value

    @field_validator("tutoring_intent")
    @classmethod
    def tutoring_intent_must_be_a_bounded_identifier(cls, value: str) -> str:
        if _TOPIC_KEY.fullmatch(value) is None:
            raise ValueError("tutoring_intent must be a bounded identifier")
        return value

    @field_validator("observed_at", "expires_at")
    @classmethod
    def timestamps_must_be_timezone_aware_utc(cls, value: str) -> str:
        return normalize_learning_gap_timestamp(value)

    @model_validator(mode="after")
    def retention_window_must_be_forward(self) -> "LearningGapSignalV1":
        observed = _parse_timestamp(self.observed_at)
        expires = _parse_timestamp(self.expires_at)
        if expires <= observed:
            raise ValueError("learning-gap signal must expire after observation")
        return self


class LearningGapAggregateV1(BaseModel):
    """Professor-visible aggregate; deliberately contains no learner keys."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    aggregate_id: str
    course_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    topic_key: str
    signal_kind: LearningGapSignalKind
    distinct_learners: int = Field(ge=3)
    signal_count: int = Field(ge=1)
    tutoring_intent_counts: dict[str, int]
    evidence_status_counts: dict[str, int]
    help_level_counts: dict[str, int]
    window_started_at: str
    window_ended_at: str
    computed_at: str
    limitations: list[str]

    @field_validator("aggregate_id")
    @classmethod
    def aggregate_id_must_be_sha256(cls, value: str) -> str:
        normalized = value.casefold()
        if _DIGEST.fullmatch(normalized) is None:
            raise ValueError("aggregate_id must be a SHA-256 digest")
        return normalized

    @field_validator("topic_key")
    @classmethod
    def topic_key_must_be_a_bounded_identifier(cls, value: str) -> str:
        if _TOPIC_KEY.fullmatch(value) is None:
            raise ValueError("topic_key must be a bounded course-taxonomy identifier")
        return value

    @model_validator(mode="after")
    def counts_and_window_must_be_consistent(self) -> "LearningGapAggregateV1":
        if self.distinct_learners > self.signal_count:
            raise ValueError("distinct learner count cannot exceed signal count")
        for counts in (
            self.tutoring_intent_counts,
            self.evidence_status_counts,
            self.help_level_counts,
        ):
            if not counts or any(value < 1 for value in counts.values()):
                raise ValueError("aggregate count maps must contain positive counts")
            if sum(counts.values()) != self.signal_count:
                raise ValueError("aggregate count maps must cover every signal")
        if _parse_timestamp(self.window_ended_at) < _parse_timestamp(
            self.window_started_at
        ):
            raise ValueError("aggregate window is reversed")
        return self


class LearningGapAggregationResultV1(BaseModel):
    """Suppressed groups expose only their count, not sensitive small-cell details."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    course_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    minimum_distinct_learners: int = Field(ge=3)
    visible_aggregates: list[LearningGapAggregateV1]
    suppressed_group_count: int = Field(ge=0)
    computed_at: str


class CourseImprovementDraftV1(BaseModel):
    """A non-executable recommendation that requires later professor review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    proposal_id: str
    aggregate_id: str
    course_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    topic_key: str
    signal_kind: LearningGapSignalKind
    status: Literal["draft-awaiting-professor-review"] = (
        "draft-awaiting-professor-review"
    )
    observed_pattern: str = Field(min_length=1)
    suggested_follow_up: str = Field(min_length=1)
    distinct_learners: int = Field(ge=3)
    signal_count: int = Field(ge=1)
    created_at: str

    @field_validator("proposal_id", "aggregate_id")
    @classmethod
    def identifiers_must_be_sha256(cls, value: str) -> str:
        normalized = value.casefold()
        if _DIGEST.fullmatch(normalized) is None:
            raise ValueError("proposal identifiers must be SHA-256 digests")
        return normalized

    @field_validator("topic_key")
    @classmethod
    def topic_key_must_be_a_bounded_identifier(cls, value: str) -> str:
        if _TOPIC_KEY.fullmatch(value) is None:
            raise ValueError("topic_key must be a bounded course-taxonomy identifier")
        return value


class LearningGapPseudonymizer:
    """Derive unlinkable-at-rest keys without retaining direct student/turn IDs."""

    def __init__(self, secret: bytes) -> None:
        if len(secret) < 32:
            raise ValueError("learning-gap pseudonymization secret needs 32 bytes")
        self._secret = bytes(secret)

    def learner_key(self, *, course_id: str, account_id: str) -> str:
        return self._digest("learner", course_id, account_id)

    def source_turn_key(self, *, release_id: str, tutor_message_id: str) -> str:
        return self._digest("turn", release_id, tutor_message_id)

    def _digest(self, *parts: str) -> str:
        if any(not part for part in parts):
            raise ValueError("pseudonymization inputs must be non-empty")
        payload = "\x1f".join(parts).encode("utf-8")
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()


def build_learning_gap_signal(
    *,
    pseudonymizer: LearningGapPseudonymizer,
    policy: LearningGapPrivacyPolicyV1,
    account_id: str,
    tutor_message_id: str,
    course_id: str,
    release_id: str,
    topic_key: str,
    signal_kind: LearningGapSignalKind,
    tutoring_intent: str,
    help_level: int,
    confusion: float,
    evidence_status: LearningGapEvidenceStatus,
    observed_at: str,
) -> LearningGapSignalV1:
    """Convert transient trusted IDs into a privacy-minimized durable signal."""

    if not 0 <= confusion <= 1:
        raise ValueError("confusion must be between zero and one")
    learner_key = pseudonymizer.learner_key(course_id=course_id, account_id=account_id)
    source_turn_key = pseudonymizer.source_turn_key(
        release_id=release_id, tutor_message_id=tutor_message_id
    )
    observed = _parse_timestamp(observed_at)
    expires = observed + timedelta(days=policy.retention_days)
    signal_id = _sha256("signal", source_turn_key, topic_key, signal_kind.value)
    return LearningGapSignalV1(
        signal_id=signal_id,
        source_turn_key=source_turn_key,
        learner_key=learner_key,
        course_id=course_id,
        release_id=release_id,
        topic_key=topic_key,
        signal_kind=signal_kind,
        tutoring_intent=tutoring_intent,
        help_level=help_level,
        confusion_band=(
            "high" if confusion >= 0.7 else "medium" if confusion >= 0.4 else "low"
        ),
        evidence_status=evidence_status,
        observed_at=observed.isoformat(),
        expires_at=expires.isoformat(),
    )


def aggregate_learning_gap_signals(
    signals: list[LearningGapSignalV1],
    *,
    course_id: str,
    release_id: str,
    policy: LearningGapPrivacyPolicyV1,
    computed_at: str,
) -> LearningGapAggregationResultV1:
    """Aggregate active signals; reveal no details about a suppressed small cell."""

    now = _parse_timestamp(computed_at)
    unique: dict[str, LearningGapSignalV1] = {}
    for signal in signals:
        if signal.course_id != course_id or signal.release_id != release_id:
            raise ValueError("learning-gap aggregation received cross-scope signal")
        previous = unique.get(signal.signal_id)
        if previous is not None and previous != signal:
            raise ValueError("learning-gap signal identifier has conflicting content")
        unique[signal.signal_id] = signal

    grouped: dict[tuple[str, LearningGapSignalKind], list[LearningGapSignalV1]] = (
        defaultdict(list)
    )
    for signal in unique.values():
        if _parse_timestamp(signal.expires_at) > now:
            grouped[(signal.topic_key, signal.signal_kind)].append(signal)

    visible: list[LearningGapAggregateV1] = []
    suppressed = 0
    for (topic_key, signal_kind), group in sorted(
        grouped.items(), key=lambda item: (item[0][0], item[0][1].value)
    ):
        learner_count = len({signal.learner_key for signal in group})
        if learner_count < policy.minimum_distinct_learners:
            suppressed += 1
            continue
        group.sort(key=lambda signal: (signal.observed_at, signal.signal_id))
        aggregate_id = _sha256(
            "aggregate",
            course_id,
            release_id,
            topic_key,
            signal_kind.value,
            now.isoformat(),
        )
        visible.append(
            LearningGapAggregateV1(
                aggregate_id=aggregate_id,
                course_id=course_id,
                release_id=release_id,
                topic_key=topic_key,
                signal_kind=signal_kind,
                distinct_learners=learner_count,
                signal_count=len(group),
                tutoring_intent_counts=_ordered_counts(
                    signal.tutoring_intent for signal in group
                ),
                evidence_status_counts=_ordered_counts(
                    signal.evidence_status.value for signal in group
                ),
                help_level_counts=_ordered_counts(
                    str(signal.help_level) for signal in group
                ),
                window_started_at=group[0].observed_at,
                window_ended_at=group[-1].observed_at,
                computed_at=now.isoformat(),
                limitations=[
                    "Counts describe bounded tutor signals, not verified learning outcomes.",
                    "No raw student interaction or student-level drill-down is available.",
                ],
            )
        )
    return LearningGapAggregationResultV1(
        course_id=course_id,
        release_id=release_id,
        minimum_distinct_learners=policy.minimum_distinct_learners,
        visible_aggregates=visible,
        suppressed_group_count=suppressed,
        computed_at=now.isoformat(),
    )


def build_course_improvement_drafts(
    result: LearningGapAggregationResultV1,
) -> list[CourseImprovementDraftV1]:
    """Create deterministic, non-executable drafts from visible aggregates."""

    drafts: list[CourseImprovementDraftV1] = []
    for aggregate in result.visible_aggregates:
        if (
            aggregate.course_id != result.course_id
            or aggregate.release_id != result.release_id
        ):
            raise ValueError("course-improvement draft received cross-scope aggregate")
        follow_up = {
            LearningGapSignalKind.CONFUSION: (
                "Review whether the topic needs a clearer explanation or example."
            ),
            LearningGapSignalKind.MISCONCEPTION: (
                "Review a contrastive explanation and misconception check for this topic."
            ),
            LearningGapSignalKind.REPEATED_HELP: (
                "Review the scaffolding sequence and add bounded intermediate practice."
            ),
            LearningGapSignalKind.NO_EVIDENCE: (
                "Review source coverage before adding or revising course material."
            ),
            LearningGapSignalKind.VALIDATION_FALLBACK: (
                "Inspect grounding failures before changing retrieval or generation policy."
            ),
            LearningGapSignalKind.INTEGRITY_REDIRECT: (
                "Review whether the academic-integrity guidance is clear for this topic."
            ),
        }[aggregate.signal_kind]
        drafts.append(
            CourseImprovementDraftV1(
                # Proposal identity is stable across repeated reads of the same
                # active aggregate.  ``aggregate_id`` includes ``computed_at``
                # and therefore cannot be used as a review capability token.
                proposal_id=_sha256(
                    "proposal",
                    aggregate.course_id,
                    aggregate.release_id,
                    aggregate.topic_key,
                    aggregate.signal_kind.value,
                    aggregate.window_started_at,
                    aggregate.window_ended_at,
                    str(aggregate.distinct_learners),
                    str(aggregate.signal_count),
                ),
                aggregate_id=aggregate.aggregate_id,
                course_id=aggregate.course_id,
                release_id=aggregate.release_id,
                topic_key=aggregate.topic_key,
                signal_kind=aggregate.signal_kind,
                observed_pattern=(
                    f"{aggregate.signal_count} bounded {aggregate.signal_kind.value} "
                    f"signals across {aggregate.distinct_learners} learners."
                ),
                suggested_follow_up=follow_up,
                distinct_learners=aggregate.distinct_learners,
                signal_count=aggregate.signal_count,
                created_at=result.computed_at,
            )
        )
    return drafts


def _ordered_counts(values: Iterable[str]) -> dict[str, int]:
    counts = Counter(values)
    return {key: counts[key] for key in sorted(counts)}


def _sha256(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("timestamp must be ISO 8601") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


def normalize_learning_gap_timestamp(value: str) -> str:
    """Normalize a timezone-aware ISO timestamp for durable lexical comparison."""

    return _parse_timestamp(value).isoformat()
