from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Mapping
from urllib.parse import urlsplit
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

from src.digital_twin.student.models import (
    AccountRole,
    AccountStatus,
    AuditEvent,
    Citation,
    DeliveryOutboxItem,
    MembershipRole,
    OutreachChannel,
    OutreachPreference,
    ProactiveMessage,
    ProactiveMessageStatus,
    ProactiveMessageView,
    ProactiveProcessResult,
    ProactiveTrigger,
    ProactiveTriggerKind,
    ProactiveTriggerStatus,
    StudentReleaseStatus,
)
from src.digital_twin.student.repository import StudentRepository
from src.digital_twin.tutor_policy import timestamp_now


class ProactiveOutreachError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DiscordWebhookRoute(BaseModel):
    destination_ref: str = Field(min_length=1, max_length=128)
    webhook_url: SecretStr
    private_destination: bool

    @field_validator("destination_ref")
    @classmethod
    def destination_ref_must_be_opaque(cls, value: str) -> str:
        if "://" in value or not re.fullmatch(r"[A-Za-z0-9._:-]+", value):
            raise ValueError("Discord destination_ref must be opaque")
        return value

    @model_validator(mode="after")
    def webhook_must_be_an_official_private_route(self) -> "DiscordWebhookRoute":
        parsed = urlsplit(self.webhook_url.get_secret_value())
        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"discord.com", "www.discord.com"}
            or not re.fullmatch(r"/api(?:/v\d+)?/webhooks/\d+/[^/]+", parsed.path)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ValueError("Discord route must use an official HTTPS webhook URL")
        if not self.private_destination:
            raise ValueError("student-specific Discord delivery must be private")
        return self


class DiscordPreparedRequest(BaseModel):
    webhook_url: SecretStr
    payload: dict[str, object]


class DiscordWebhookDeliveryAdapter:
    """Disabled-by-default request builder; network transport is a later gate."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        routes: Mapping[str, DiscordWebhookRoute] | None = None,
    ) -> None:
        self.enabled = enabled
        self.routes = dict(routes or {})

    def prepare(
        self, item: DeliveryOutboxItem, message: ProactiveMessage
    ) -> DiscordPreparedRequest:
        if not self.enabled:
            raise ProactiveOutreachError(
                "discord_delivery_disabled",
                "Discord delivery is disabled until separately configured.",
            )
        if item.channel != OutreachChannel.DISCORD or message.channel != item.channel:
            raise ProactiveOutreachError(
                "discord_delivery_scope_invalid",
                "The delivery record is not bound to Discord.",
            )
        route = self.routes.get(item.destination_ref)
        if route is None or route.destination_ref != item.destination_ref:
            raise ProactiveOutreachError(
                "discord_destination_unavailable",
                "The linked private Discord destination is unavailable.",
            )
        return DiscordPreparedRequest(
            webhook_url=route.webhook_url,
            payload={
                "content": message.content[:2_000],
                "allowed_mentions": {"parse": []},
                "flags": 4,
            },
        )


class ProactiveOutreachService:
    """Deterministic consent, trigger, and in-app delivery authority."""

    def __init__(self, repository: StudentRepository) -> None:
        self.repository = repository

    def list_preferences(
        self, account_id: str, course_id: str
    ) -> list[OutreachPreference]:
        self._authorize_student(account_id, course_id)
        return self.repository.list_outreach_preferences(account_id, course_id)

    def update_preference(
        self,
        account_id: str,
        course_id: str,
        *,
        channel: OutreachChannel,
        enabled: bool,
        timezone: str,
        quiet_hours_start: str,
        quiet_hours_end: str,
        max_messages_per_7_days: int,
        snoozed_until: str | None = None,
        destination_ref: str | None = None,
        private_destination: bool = False,
    ) -> OutreachPreference:
        self._authorize_student(account_id, course_id)
        if snoozed_until is not None:
            _parse_instant(snoozed_until, "snoozed_until")
        preference = OutreachPreference(
            student_id=account_id,
            course_id=course_id,
            channel=channel,
            enabled=enabled,
            timezone=timezone,
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end,
            max_messages_per_7_days=max_messages_per_7_days,
            snoozed_until=snoozed_until,
            destination_ref=destination_ref,
            private_destination=private_destination,
        )
        saved = self.repository.save_outreach_preference(preference)
        self.repository.save_audit_event(
            self._event(
                "outreach-preference-updated",
                account_id=account_id,
                course_id=course_id,
                details={
                    "channel": channel.value,
                    "enabled": enabled,
                    "private_destination": private_destination,
                },
            )
        )
        return saved

    def schedule_trigger(
        self,
        professor_id: str,
        course_id: str,
        *,
        student_id: str,
        channel: OutreachChannel,
        kind: ProactiveTriggerKind,
        scheduled_for: str,
        expires_at: str,
        topic: str,
        prompt: str,
        source_chunk_id: str,
        idempotency_key: str,
    ) -> ProactiveTrigger:
        release = self._authorize_professor_schedule(
            professor_id, student_id, course_id
        )
        scheduled = _parse_instant(scheduled_for, "scheduled_for")
        expiry = _parse_instant(expires_at, "expires_at")
        normalized_key = idempotency_key.strip()
        normalized_topic = topic.strip()
        normalized_prompt = prompt.strip()
        if not normalized_key or not normalized_topic or not normalized_prompt:
            raise ProactiveOutreachError(
                "trigger_content_invalid",
                "Trigger key, topic, and prompt must contain text.",
            )
        if expiry <= scheduled or expiry - scheduled > timedelta(days=90):
            raise ProactiveOutreachError(
                "trigger_window_invalid",
                "The trigger expiry must be after delivery and within 90 days.",
            )
        chunk = next((item for item in release.chunks if item.id == source_chunk_id), None)
        if chunk is None or not chunk.retrieval_allowed:
            raise ProactiveOutreachError(
                "trigger_evidence_invalid",
                "The trigger must reference retrievable evidence in the published release.",
            )
        existing = self.repository.find_proactive_trigger_by_key(normalized_key)
        candidate_fields = {
            "professor_id": professor_id,
            "student_id": student_id,
            "course_id": course_id,
            "release_id": release.id,
            "channel": channel,
            "kind": kind,
            "scheduled_for": scheduled.isoformat(),
            "expires_at": expiry.isoformat(),
            "topic": normalized_topic,
            "prompt": normalized_prompt,
            "source_chunk_id": source_chunk_id,
        }
        if existing is not None:
            if any(getattr(existing, key) != value for key, value in candidate_fields.items()):
                raise ProactiveOutreachError(
                    "trigger_idempotency_conflict",
                    "The idempotency key is already bound to another trigger.",
                )
            return existing
        trigger = ProactiveTrigger(
            id=f"proactive-trigger-{uuid4()}",
            idempotency_key=normalized_key,
            **candidate_fields,
        )
        saved = self.repository.save_proactive_trigger(trigger)
        self.repository.save_audit_event(
            self._event(
                "proactive-trigger-scheduled",
                account_id=professor_id,
                course_id=course_id,
                release_id=release.id,
                details={
                    "trigger_id": saved.id,
                    "student_id": student_id,
                    "channel": channel.value,
                    "kind": kind.value,
                },
            )
        )
        return saved

    def process_due(
        self, *, now: datetime | None = None, limit: int = 100
    ) -> list[ProactiveProcessResult]:
        instant = _as_utc(now or datetime.now(UTC))
        return [
            self.process_trigger(trigger.id, now=instant)
            for trigger in self.repository.list_due_proactive_triggers(
                instant.isoformat(), limit=limit
            )
        ]

    def process_trigger(
        self, trigger_id: str, *, now: datetime | None = None
    ) -> ProactiveProcessResult:
        instant = _as_utc(now or datetime.now(UTC))
        trigger = self.repository.get_proactive_trigger(trigger_id)
        if trigger is None:
            raise ProactiveOutreachError(
                "proactive_trigger_not_found", "The proactive trigger was not found."
            )
        if trigger.status != ProactiveTriggerStatus.PENDING:
            message = self.repository.get_proactive_message_for_trigger(trigger.id)
            return ProactiveProcessResult(
                outcome=(
                    "duplicate"
                    if trigger.status == ProactiveTriggerStatus.MATERIALIZED
                    else "suppressed"
                ),
                trigger=trigger,
                message=self._view(message) if message else None,
            )
        scheduled = _parse_instant(trigger.scheduled_for, "scheduled_for")
        if scheduled > instant:
            return ProactiveProcessResult(outcome="not-due", trigger=trigger)
        if _parse_instant(trigger.expires_at, "expires_at") <= instant:
            return self._suppress(trigger, "expired", instant)

        live_reason = self._live_suppression_reason(trigger)
        if live_reason is not None:
            return self._suppress(trigger, live_reason, instant)
        preference = self.repository.get_outreach_preference(
            trigger.student_id, trigger.course_id, trigger.channel
        )
        if preference is None or not preference.enabled:
            return self._suppress(trigger, "consent-disabled", instant)
        if preference.snoozed_until is not None and (
            _parse_instant(preference.snoozed_until, "snoozed_until") > instant
        ):
            return self._suppress(trigger, "student-snoozed", instant)
        if _inside_quiet_hours(instant, preference):
            return ProactiveProcessResult(
                outcome="deferred-quiet-hours", trigger=trigger
            )
        since = (instant - timedelta(days=7)).isoformat()
        if self.repository.count_recent_proactive_messages(
            trigger.student_id, trigger.course_id, since=since
        ) >= preference.max_messages_per_7_days:
            return self._suppress(trigger, "frequency-cap", instant)

        release = self.repository.get_release(trigger.release_id)
        if release is None:
            return self._suppress(trigger, "release-unavailable", instant)
        chunk = next(
            (item for item in release.chunks if item.id == trigger.source_chunk_id),
            None,
        )
        if chunk is None or not chunk.retrieval_allowed:
            return self._suppress(trigger, "evidence-unavailable", instant)
        title = chunk.metadata.get("title")
        if not isinstance(title, str) or not title.strip():
            return self._suppress(trigger, "evidence-title-missing", instant)

        created_at = instant.isoformat()
        message = ProactiveMessage(
            id=f"proactive-message-{uuid4()}",
            trigger_id=trigger.id,
            student_id=trigger.student_id,
            course_id=trigger.course_id,
            release_id=trigger.release_id,
            channel=trigger.channel,
            content=f"{trigger.topic.strip()}\n\n{trigger.prompt.strip()}",
            status=(
                ProactiveMessageStatus.DELIVERED
                if trigger.channel == OutreachChannel.IN_APP
                else ProactiveMessageStatus.QUEUED
            ),
            created_at=created_at,
        )
        citation = Citation(
            id=f"proactive-citation-{uuid4()}",
            message_id=message.id,
            course_id=trigger.course_id,
            release_id=trigger.release_id,
            source_artifact_id=chunk.source_artifact_id or chunk.document_id,
            source_document_id=chunk.document_id,
            source_version=chunk.source_version,
            title=title.strip(),
            locator=chunk.locator or f"chunk {chunk.ordinal + 1}",
            source_checksum=chunk.source_checksum,
            page=chunk.page_start,
            region_id=chunk.region_id,
            region_kind=(chunk.region_kind.value if chunk.region_kind else None),
            bounding_box=chunk.bounding_box,
            crop_ref=chunk.crop_ref if chunk.display_allowed else None,
        )
        outbox_item = None
        if trigger.channel == OutreachChannel.DISCORD:
            if not preference.destination_ref or not preference.private_destination:
                return self._suppress(trigger, "private-destination-required", instant)
            outbox_item = DeliveryOutboxItem(
                id=f"proactive-delivery-{uuid4()}",
                message_id=message.id,
                channel=trigger.channel,
                destination_ref=preference.destination_ref,
                available_at=created_at,
                created_at=created_at,
                updated_at=created_at,
            )
        inserted = self.repository.materialize_proactive_message(
            trigger,
            message,
            [citation],
            outbox_item,
            self._event(
                "proactive-message-materialized",
                account_id=trigger.student_id,
                course_id=trigger.course_id,
                release_id=trigger.release_id,
                details={
                    "trigger_id": trigger.id,
                    "message_id": message.id,
                    "channel": trigger.channel.value,
                },
            ),
        )
        current_trigger = self.repository.get_proactive_trigger(trigger.id) or trigger
        if not inserted:
            current = self.repository.get_proactive_message_for_trigger(trigger.id)
            return ProactiveProcessResult(
                outcome="duplicate",
                trigger=current_trigger,
                message=self._view(current) if current else None,
            )
        return ProactiveProcessResult(
            outcome=(
                "delivered"
                if trigger.channel == OutreachChannel.IN_APP
                else "queued"
            ),
            trigger=current_trigger,
            message=self._view(message),
        )

    def list_inbox(
        self, account_id: str, *, course_id: str | None = None
    ) -> list[ProactiveMessageView]:
        self._require_student(account_id)
        if course_id is not None:
            self._authorize_student(account_id, course_id)
        messages = self.repository.list_proactive_messages(
            account_id, course_id=course_id
        )
        return [
            self._view(message)
            for message in messages
            if message.channel == OutreachChannel.IN_APP
            and message.status
            in {ProactiveMessageStatus.DELIVERED, ProactiveMessageStatus.READ}
        ]

    def mark_read(self, account_id: str, message_id: str) -> ProactiveMessageView:
        return self._change_message(account_id, message_id, ProactiveMessageStatus.READ)

    def dismiss(self, account_id: str, message_id: str) -> ProactiveMessageView:
        return self._change_message(
            account_id, message_id, ProactiveMessageStatus.DISMISSED
        )

    def _change_message(
        self,
        account_id: str,
        message_id: str,
        status: ProactiveMessageStatus,
    ) -> ProactiveMessageView:
        message = self.repository.get_proactive_message(message_id)
        if message is None:
            raise ProactiveOutreachError(
                "proactive_message_not_found", "The proactive message was not found."
            )
        if message.student_id != account_id:
            raise ProactiveOutreachError(
                "proactive_message_forbidden", "This proactive message is not yours."
            )
        self._authorize_student(account_id, message.course_id)
        try:
            updated = self.repository.set_proactive_message_status(
                message.id, status, changed_at=timestamp_now()
            )
        except ValueError as error:
            raise ProactiveOutreachError(
                "proactive_message_state_invalid",
                "The proactive message cannot change from its current state.",
            ) from error
        return self._view(updated)

    def _view(self, message: ProactiveMessage) -> ProactiveMessageView:
        return ProactiveMessageView(
            message=message,
            citations=self.repository.list_proactive_citations(message.id),
        )

    def _suppress(
        self, trigger: ProactiveTrigger, reason: str, now: datetime
    ) -> ProactiveProcessResult:
        updated = self.repository.set_proactive_trigger_status(
            trigger.id,
            ProactiveTriggerStatus.SUPPRESSED,
            suppression_reason=reason,
            updated_at=now.isoformat(),
        )
        self.repository.save_audit_event(
            self._event(
                "proactive-trigger-suppressed",
                account_id=trigger.student_id,
                course_id=trigger.course_id,
                release_id=trigger.release_id,
                details={"trigger_id": trigger.id, "reason": reason},
            )
        )
        return ProactiveProcessResult(outcome="suppressed", trigger=updated)

    def _live_suppression_reason(self, trigger: ProactiveTrigger) -> str | None:
        account = self.repository.get_account(trigger.student_id)
        if (
            account is None
            or account.role != AccountRole.STUDENT
            or account.status != AccountStatus.ACTIVE
        ):
            return "student-inactive"
        membership = self.repository.get_membership(
            trigger.student_id, trigger.course_id
        )
        if (
            membership is None
            or not membership.active
            or membership.role != MembershipRole.STUDENT
        ):
            return "membership-inactive"
        release = self.repository.get_published_release(trigger.course_id)
        if (
            release is None
            or release.id != trigger.release_id
            or release.status != StudentReleaseStatus.PUBLISHED
        ):
            return "release-unavailable"
        return None

    def _authorize_professor_schedule(self, professor_id: str, student_id: str, course_id: str):
        professor = self.repository.get_account(professor_id)
        course = self.repository.get_course(course_id)
        if (
            professor is None
            or professor.role != AccountRole.PROFESSOR
            or professor.status != AccountStatus.ACTIVE
            or course is None
            or course.owner_professor_id != professor_id
        ):
            raise ProactiveOutreachError(
                "professor_course_forbidden",
                "Only the active course owner may schedule proactive tutoring.",
            )
        self._authorize_student(student_id, course_id)
        release = self.repository.get_published_release(course_id)
        if release is None:
            raise ProactiveOutreachError(
                "release_unavailable", "The course Digital Twin is not published."
            )
        return release

    def _authorize_student(self, account_id: str, course_id: str) -> None:
        self._require_student(account_id)
        membership = self.repository.get_membership(account_id, course_id)
        if (
            membership is None
            or membership.role != MembershipRole.STUDENT
            or not membership.active
        ):
            raise ProactiveOutreachError(
                "course_forbidden", "The student is not active in this course."
            )

    def _require_student(self, account_id: str) -> None:
        account = self.repository.get_account(account_id)
        if account is None:
            raise ProactiveOutreachError(
                "account_not_found", "The student account was not found."
            )
        if account.role != AccountRole.STUDENT or account.status != AccountStatus.ACTIVE:
            raise ProactiveOutreachError(
                "student_account_required", "An active student account is required."
            )

    @staticmethod
    def _event(
        event_type: str,
        *,
        account_id: str | None,
        course_id: str | None,
        release_id: str | None = None,
        details: dict[str, str | int | float | bool | None],
    ) -> AuditEvent:
        return AuditEvent(
            id=f"audit-{uuid4()}",
            event_type=event_type,
            account_id=account_id,
            course_id=course_id,
            release_id=release_id,
            details=details,
        )


def _parse_instant(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ProactiveOutreachError(
            "timestamp_invalid", f"{label} must be an ISO-8601 timestamp."
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ProactiveOutreachError(
            "timestamp_invalid", f"{label} must include a timezone offset."
        )
    return parsed.astimezone(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("proactive processing time must be timezone-aware")
    return value.astimezone(UTC)


def _inside_quiet_hours(now: datetime, preference: OutreachPreference) -> bool:
    local = now.astimezone(ZoneInfo(preference.timezone))
    current = local.hour * 60 + local.minute
    start_hour, start_minute = map(int, preference.quiet_hours_start.split(":"))
    end_hour, end_minute = map(int, preference.quiet_hours_end.split(":"))
    start = start_hour * 60 + start_minute
    end = end_hour * 60 + end_minute
    if start == end:
        return False
    if start < end:
        return start <= current < end
    return current >= start or current < end
