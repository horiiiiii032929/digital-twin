from datetime import UTC, datetime

import pytest
from pydantic import SecretStr, ValidationError

from src.digital_twin.student import (
    Conversation,
    DiscordWebhookDeliveryAdapter,
    DiscordWebhookRoute,
    EvidenceRecoveryMode,
    Message,
    OutreachChannel,
    ProactiveMessageStatus,
    ProactiveOutreachError,
    ProactiveOutreachService,
    ProactiveTriggerKind,
    ProactiveTriggerStatus,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    TeachingProfileDepth,
    TeachingProfileService,
    seed_synthetic_student_workflow,
)
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
)
from src.digital_twin.student.autonomy_service import GovernedAutonomyService


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


def _record_prior_no_evidence_turn(
    repository,
    fixture,
    *,
    question="Why is cache coherence needed for replicated processor data?",
):
    current = repository.get_release(fixture.release_a_id)
    previous = current.model_copy(
        update={
            "id": "release-a-v0-without-cache",
            "status": StudentReleaseStatus.WITHDRAWN,
            "chunks": [current.chunks[1]],
            "created_at": "2026-08-01T00:00:00+00:00",
        },
        deep=True,
    )
    repository.save_release(previous)
    conversation = repository.save_conversation(
        Conversation(
            id="conversation-prior-no-evidence",
            student_id=fixture.student_a_id,
            course_id=fixture.course_a_id,
            release_id=previous.id,
            created_at="2026-08-10T00:00:00+00:00",
            updated_at="2026-08-10T00:00:00+00:00",
        )
    )
    student_message = Message(
        id="message-prior-question",
        conversation_id=conversation.id,
        role="student",
        content=question,
        action="question",
        client_request_id="prior-no-evidence-request",
        created_at="2026-08-10T00:00:00+00:00",
    )
    tutor_message = Message(
        id="message-prior-no-evidence",
        conversation_id=conversation.id,
        role="tutor",
        content="I do not have enough approved evidence.",
        action="no-evidence",
        response_to_message_id=student_message.id,
        created_at="2026-08-10T00:00:01+00:00",
    )
    repository.save_turn(
        conversation,
        student_message,
        tutor_message,
        [],
        [],
    )
    return conversation


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
        enabled=True,
        routes={route.destination_ref: route},
        in_app_base_url="https://tutor.example.edu",
    )

    prepared = adapter.prepare(outbox, result.message.message)

    assert prepared.payload["allowed_mentions"] == {"parse": []}
    assert prepared.payload["flags"] == 4
    assert result.message.message.content not in prepared.payload["content"]
    assert "cache coherence" not in prepared.payload["content"].casefold()
    assert prepared.payload["content"].startswith(
        "You have a new private message from your AI course tutor."
    )
    assert "https://tutor.example.edu/student?" in prepared.payload["content"]
    assert "token-secret" not in repr(prepared)


def test_evidence_recovery_shadow_scan_proposes_only_genuinely_new_evidence(tmp_path):
    repository, fixture, service = _service(tmp_path)
    _enable_in_app(service, fixture)
    _record_prior_no_evidence_turn(repository, fixture)

    result = service.scan_evidence_recovery(
        fixture.professor_id,
        fixture.course_a_id,
        mode=EvidenceRecoveryMode.SHADOW,
        now=NOW,
    )

    assert result.proposed_count == 1
    assert result.no_action_count == 0
    assert result.trigger_count == 0
    assert result.provider_calls == 0
    assert result.decisions[0].source_chunk_id == "chunk-cache-synthetic"
    assert result.decisions[0].reason == "new-evidence-supported"
    assert repository.list_due_proactive_triggers(NOW.isoformat()) == []


def test_governed_observer_materializes_evidence_recovery_once(tmp_path):
    repository, fixture, outreach = _service(tmp_path)
    _enable_in_app(outreach, fixture)
    prior = _record_prior_no_evidence_turn(repository, fixture)
    profiles = TeachingProfileService(repository)
    draft = profiles.create_draft(
        fixture.professor_id,
        fixture.course_a_id,
        {
            "tone": "Patient and precise",
            "depth": TeachingProfileDepth.BALANCED,
            "explanation_structure": ["diagnose", "hint", "check"],
            "example_preferences": ["systems examples"],
            "misconception_handling": "Ask for a corrected next step.",
            "integrity_limits": "Require an attempt before assessed-work help.",
            "help_ladder": ["diagnostic question", "hint"],
            "outreach_policy": "Use private in-app follow-ups.",
        },
    )
    preview = profiles.preview(
        fixture.professor_id,
        fixture.course_a_id,
        draft.profile_id,
    )
    approved = profiles.approve(
        fixture.professor_id,
        fixture.course_a_id,
        draft.profile_id,
        preview_sha256=preview.preview_sha256,
    )
    current = repository.get_published_release(fixture.course_a_id)
    governed_release = current.model_copy(
        update={
            "id": "release-a-governed-recovery",
            "status": StudentReleaseStatus.DRAFT,
            "teaching_profile_id": approved.profile_id,
            "teaching_profile_sha256": approved.content_sha256,
            "created_at": "2026-08-27T10:00:00+00:00",
        },
        deep=True,
    )
    repository.save_release(governed_release)
    repository.publish_release(governed_release.id)
    autonomy = GovernedAutonomyService(repository, outreach)
    autonomy.set_policy(
        fixture.professor_id,
        fixture.course_a_id,
        approved_course_objectives=[
            "Explain why cache coherence protects replicated processor data."
        ],
        allowed_actions=[AutonomousActionKind.RECOMMEND_APPROVED_SOURCE],
        autonomy_enabled=True,
    )

    first = autonomy.observe_evidence_recovery(
        fixture.professor_id,
        fixture.course_a_id,
        now=NOW,
    )
    second = autonomy.observe_evidence_recovery(
        fixture.professor_id,
        fixture.course_a_id,
        now=NOW,
    )
    due = repository.list_due_autonomous_opportunities(NOW.isoformat())

    assert first.opportunities_created == 1
    assert second.opportunities_created == 0
    assert len(due) == 1
    assert due[0].event_kind == AutonomousEventKind.EVIDENCE_RECOVERED
    assert due[0].supporting_observation_ids == [
        "message-prior-question",
        "message-prior-no-evidence",
    ]
    assert due[0].release_id == governed_release.id
    assert prior.release_id != due[0].release_id


def test_evidence_recovery_active_mode_is_gated_and_idempotent(tmp_path):
    repository, fixture, shadow_service = _service(tmp_path)
    _enable_in_app(shadow_service, fixture)
    _record_prior_no_evidence_turn(repository, fixture)

    with pytest.raises(ProactiveOutreachError, match="not authorized"):
        shadow_service.scan_evidence_recovery(
            fixture.professor_id,
            fixture.course_a_id,
            mode=EvidenceRecoveryMode.ACTIVE,
            now=NOW,
        )

    active_service = ProactiveOutreachService(
        repository, evidence_recovery_active=True
    )
    first = active_service.scan_evidence_recovery(
        fixture.professor_id,
        fixture.course_a_id,
        mode=EvidenceRecoveryMode.ACTIVE,
        now=NOW,
    )
    second = active_service.scan_evidence_recovery(
        fixture.professor_id,
        fixture.course_a_id,
        mode=EvidenceRecoveryMode.ACTIVE,
        now=NOW,
    )

    assert first.proposed_count == 1
    assert first.trigger_count == 1
    assert first.decisions[0].trigger_id is not None
    assert second.duplicate_count == 1
    assert second.trigger_count == 0
    delivered = active_service.process_trigger(
        first.decisions[0].trigger_id, now=NOW
    )
    assert delivered.outcome == "delivered"
    assert delivered.message is not None
    assert delivered.message.citations[0].source_document_id == "document-cache"


def test_evidence_recovery_treats_missing_consent_and_unchanged_evidence_as_no_action(
    tmp_path,
):
    repository, fixture, service = _service(tmp_path)
    _record_prior_no_evidence_turn(repository, fixture)

    without_consent = service.scan_evidence_recovery(
        fixture.professor_id,
        fixture.course_a_id,
        now=NOW,
    )
    assert without_consent.no_action_count == 1
    assert without_consent.decisions[0].reason == "consent-disabled"

    _enable_in_app(service, fixture)
    second_repository, second_fixture, second_service = _service(tmp_path / "same")
    _enable_in_app(second_service, second_fixture)
    _record_prior_no_evidence_turn(
        second_repository,
        second_fixture,
        question="How does virtual memory map process addresses to physical pages?",
    )
    unchanged = second_service.scan_evidence_recovery(
        second_fixture.professor_id,
        second_fixture.course_a_id,
        now=NOW,
    )
    assert unchanged.no_action_count == 1
    assert unchanged.decisions[0].reason == "insufficient-new-evidence"
