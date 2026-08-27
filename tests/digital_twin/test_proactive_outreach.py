from datetime import UTC, datetime

import pytest
from pydantic import SecretStr, ValidationError

from src.digital_twin.student import (
    DiscordWebhookDeliveryAdapter,
    DiscordWebhookRoute,
    OutreachChannel,
    ProactiveMessageStatus,
    ProactiveOutreachError,
    ProactiveOutreachService,
    ProactiveTriggerKind,
    ProactiveTriggerStatus,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    seed_synthetic_student_workflow,
)


NOW = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


def _service(tmp_path):
    repository = SQLiteStudentRepository(tmp_path / "proactive.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    return repository, fixture, ProactiveOutreachService(repository)


def _enable_in_app(service, fixture, **overrides):
    values = {
        "channel": OutreachChannel.IN_APP,
        "enabled": True,
        "timezone": "UTC",
        "quiet_hours_start": "23:00",
        "quiet_hours_end": "06:00",
        "max_messages_per_7_days": 3,
    }
    values.update(overrides)
    return service.update_preference(
        fixture.student_a_id,
        fixture.course_a_id,
        **values,
    )


def _schedule(service, fixture, **overrides):
    values = {
        "student_id": fixture.student_a_id,
        "channel": OutreachChannel.IN_APP,
        "kind": ProactiveTriggerKind.SCHEDULED_RETRIEVAL_PRACTICE,
        "scheduled_for": "2026-08-27T11:00:00+00:00",
        "expires_at": "2026-08-27T13:00:00+00:00",
        "topic": "Cache coherence check",
        "prompt": "In one sentence, why is cache coherence needed?",
        "source_chunk_id": "chunk-cache-synthetic",
        "idempotency_key": "proactive-test-1",
    }
    values.update(overrides)
    return service.schedule_trigger(
        fixture.professor_id,
        fixture.course_a_id,
        **values,
    )


def test_consent_defaults_fail_closed_and_records_suppression(tmp_path):
    repository, fixture, service = _service(tmp_path)
    trigger = _schedule(service, fixture)

    result = service.process_trigger(trigger.id, now=NOW)

    assert result.outcome == "suppressed"
    assert result.trigger.status == ProactiveTriggerStatus.SUPPRESSED
    assert result.trigger.suppression_reason == "consent-disabled"
    assert repository.list_proactive_messages(fixture.student_a_id) == []


def test_opted_in_in_app_trigger_delivers_once_with_source_lineage(tmp_path):
    repository, fixture, service = _service(tmp_path)
    _enable_in_app(service, fixture)
    trigger = _schedule(service, fixture)

    first = service.process_trigger(trigger.id, now=NOW)
    second = service.process_trigger(trigger.id, now=NOW)

    assert first.outcome == "delivered"
    assert first.message is not None
    assert first.message.message.status == ProactiveMessageStatus.DELIVERED
    assert first.message.message.channel == OutreachChannel.IN_APP
    assert first.message.citations[0].source_artifact_id == "source-cache-synthetic"
    assert second.outcome == "duplicate"
    assert second.message == first.message
    assert len(repository.list_proactive_messages(fixture.student_a_id)) == 1
    assert repository.list_delivery_outbox() == []


def test_student_can_read_then_dismiss_only_their_inbox_message(tmp_path):
    _, fixture, service = _service(tmp_path)
    _enable_in_app(service, fixture)
    trigger = _schedule(service, fixture)
    delivered = service.process_trigger(trigger.id, now=NOW)
    assert delivered.message is not None
    message_id = delivered.message.message.id

    assert len(service.list_inbox(fixture.student_a_id)) == 1
    read = service.mark_read(fixture.student_a_id, message_id)
    assert read.message.status == ProactiveMessageStatus.READ
    dismissed = service.dismiss(fixture.student_a_id, message_id)
    assert dismissed.message.status == ProactiveMessageStatus.DISMISSED
    assert service.list_inbox(fixture.student_a_id) == []
    with pytest.raises(ProactiveOutreachError, match="not yours"):
        service.mark_read(fixture.student_b_id, message_id)


def test_quiet_hours_defer_without_consuming_trigger(tmp_path):
    repository, fixture, service = _service(tmp_path)
    _enable_in_app(
        service,
        fixture,
        quiet_hours_start="11:00",
        quiet_hours_end="13:00",
    )
    trigger = _schedule(service, fixture)

    result = service.process_trigger(trigger.id, now=NOW)

    assert result.outcome == "deferred-quiet-hours"
    assert repository.get_proactive_trigger(trigger.id).status == ProactiveTriggerStatus.PENDING


def test_release_withdrawal_cancels_pending_trigger(tmp_path):
    repository, fixture, service = _service(tmp_path)
    _enable_in_app(service, fixture)
    trigger = _schedule(
        service,
        fixture,
        scheduled_for="2026-08-28T11:00:00+00:00",
        expires_at="2026-08-28T13:00:00+00:00",
    )

    repository.set_release_status(
        fixture.release_a_id, StudentReleaseStatus.WITHDRAWN
    )

    assert repository.get_proactive_trigger(trigger.id).status == ProactiveTriggerStatus.CANCELLED
    assert service.process_trigger(trigger.id, now=NOW).outcome == "suppressed"


def test_discord_requires_private_opaque_destination_and_only_queues(tmp_path):
    repository, fixture, service = _service(tmp_path)
    with pytest.raises(ValidationError, match="linked private destination"):
        service.update_preference(
            fixture.student_a_id,
            fixture.course_a_id,
            channel=OutreachChannel.DISCORD,
            enabled=True,
            timezone="UTC",
            quiet_hours_start="23:00",
            quiet_hours_end="06:00",
            max_messages_per_7_days=3,
            destination_ref="discord-private-a",
            private_destination=False,
        )
    service.update_preference(
        fixture.student_a_id,
        fixture.course_a_id,
        channel=OutreachChannel.DISCORD,
        enabled=True,
        timezone="UTC",
        quiet_hours_start="23:00",
        quiet_hours_end="06:00",
        max_messages_per_7_days=3,
        destination_ref="discord-private-a",
        private_destination=True,
    )
    trigger = _schedule(
        service,
        fixture,
        channel=OutreachChannel.DISCORD,
        idempotency_key="proactive-discord-1",
    )

    result = service.process_trigger(trigger.id, now=NOW)

    assert result.outcome == "queued"
    assert result.message is not None
    assert result.message.message.status == ProactiveMessageStatus.QUEUED
    outbox = repository.list_delivery_outbox()
    assert len(outbox) == 1
    adapter = DiscordWebhookDeliveryAdapter()
    with pytest.raises(ProactiveOutreachError, match="disabled"):
        adapter.prepare(outbox[0], result.message.message)


def test_discord_request_builder_suppresses_mentions_and_keeps_secret_masked(tmp_path):
    repository, fixture, service = _service(tmp_path)
    service.update_preference(
        fixture.student_a_id,
        fixture.course_a_id,
        channel=OutreachChannel.DISCORD,
        enabled=True,
        timezone="UTC",
        quiet_hours_start="23:00",
        quiet_hours_end="06:00",
        max_messages_per_7_days=3,
        destination_ref="discord-private-a",
        private_destination=True,
    )
    trigger = _schedule(
        service,
        fixture,
        channel=OutreachChannel.DISCORD,
        idempotency_key="proactive-discord-2",
    )
    result = service.process_trigger(trigger.id, now=NOW)
    assert result.message is not None
    outbox = repository.list_delivery_outbox()[0]
    route = DiscordWebhookRoute(
        destination_ref="discord-private-a",
        webhook_url=SecretStr("https://discord.com/api/webhooks/123/token-secret"),
        private_destination=True,
    )
    adapter = DiscordWebhookDeliveryAdapter(
        enabled=True, routes={route.destination_ref: route}
    )

    prepared = adapter.prepare(outbox, result.message.message)

    assert prepared.payload["allowed_mentions"] == {"parse": []}
    assert prepared.payload["flags"] == 4
    assert "token-secret" not in repr(prepared)
