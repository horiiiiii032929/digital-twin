from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.digital_twin.student import (
    LearningGapEvidenceStatus,
    LearningGapPrivacyPolicyV1,
    LearningGapPseudonymizer,
    LearningGapSignalKind,
    SQLiteStudentRepository,
    aggregate_learning_gap_signals,
    build_course_improvement_drafts,
    build_learning_gap_signal,
    seed_synthetic_student_workflow,
)


OBSERVED_AT = "2026-08-27T00:00:00+00:00"
ACTIVE_AT = "2026-08-28T00:00:00+00:00"
EXPIRED_AT = "2026-12-01T00:00:00+00:00"


def _pseudonymizer() -> LearningGapPseudonymizer:
    return LearningGapPseudonymizer(b"synthetic-learning-gap-secret-32-bytes-minimum")


def _signal(
    *,
    account_id: str,
    tutor_message_id: str,
    course_id: str,
    release_id: str,
    topic_key: str = "concept:virtual-memory",
    signal_kind: LearningGapSignalKind = LearningGapSignalKind.CONFUSION,
    policy: LearningGapPrivacyPolicyV1 | None = None,
):
    return build_learning_gap_signal(
        pseudonymizer=_pseudonymizer(),
        policy=policy or LearningGapPrivacyPolicyV1(),
        account_id=account_id,
        tutor_message_id=tutor_message_id,
        course_id=course_id,
        release_id=release_id,
        topic_key=topic_key,
        signal_kind=signal_kind,
        tutoring_intent="give_hint",
        help_level=2,
        confusion=0.8,
        evidence_status=LearningGapEvidenceStatus.SUPPORTED,
        observed_at=OBSERVED_AT,
    )


def test_pseudonymization_is_deterministic_scoped_and_requires_a_strong_secret():
    with pytest.raises(ValueError, match="32 bytes"):
        LearningGapPseudonymizer(b"weak")

    pseudonymizer = _pseudonymizer()
    first = pseudonymizer.learner_key(course_id="course-a", account_id="student-a")

    assert first == pseudonymizer.learner_key(
        course_id="course-a", account_id="student-a"
    )
    assert first != pseudonymizer.learner_key(
        course_id="course-b", account_id="student-a"
    )
    assert first != pseudonymizer.learner_key(
        course_id="course-a", account_id="student-b"
    )


def test_signal_contract_excludes_raw_student_content_and_direct_ids():
    signal = _signal(
        account_id="student-private",
        tutor_message_id="message-private",
        course_id="course-a",
        release_id="release-a",
    )
    serialized = signal.model_dump_json()

    assert "student-private" not in serialized
    assert "message-private" not in serialized
    assert set(signal.model_dump()) == {
        "schema_version",
        "signal_id",
        "source_turn_key",
        "learner_key",
        "course_id",
        "release_id",
        "topic_key",
        "signal_kind",
        "tutoring_intent",
        "help_level",
        "confusion_band",
        "evidence_status",
        "observed_at",
        "expires_at",
    }
    with pytest.raises(ValidationError, match="extra_forbidden"):
        signal.__class__.model_validate(
            {**signal.model_dump(mode="json"), "student_message": "raw content"}
        )
    with pytest.raises(ValidationError, match="bounded identifier"):
        signal.__class__.model_validate(
            {
                **signal.model_dump(mode="json"),
                "tutoring_intent": "student said a private sentence",
            }
        )


def test_signal_timestamps_are_normalized_for_durable_comparison():
    signal = _signal(
        account_id="student-private",
        tutor_message_id="message-private",
        course_id="course-a",
        release_id="release-a",
    )
    shifted = signal.model_copy(
        update={
            "observed_at": "2026-08-27T08:00:00+08:00",
            "expires_at": "2026-11-25T08:00:00+08:00",
        }
    )
    normalized = signal.__class__.model_validate(shifted.model_dump())

    assert normalized.observed_at == OBSERVED_AT
    assert normalized.expires_at == "2026-11-25T00:00:00+00:00"


def test_repository_persists_idempotently_and_enforces_release_scope(tmp_path):
    repository = SQLiteStudentRepository(tmp_path / "learning-gap.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    signal = _signal(
        account_id=fixture.student_a_id,
        tutor_message_id="tutor-message-1",
        course_id=fixture.course_a_id,
        release_id=fixture.release_a_id,
    )

    assert repository.save_learning_gap_signal(signal) is True
    assert repository.save_learning_gap_signal(signal) is False
    assert repository.list_learning_gap_signals(
        fixture.course_a_id, fixture.release_a_id, active_at=ACTIVE_AT
    ) == [signal]

    conflict = signal.model_copy(update={"help_level": 3})
    with pytest.raises(ValueError, match="idempotency conflict"):
        repository.save_learning_gap_signal(conflict)
    with pytest.raises(ValueError, match="cross-course"):
        repository.save_learning_gap_signal(
            _signal(
                account_id=fixture.student_a_id,
                tutor_message_id="tutor-message-2",
                course_id=fixture.course_b_id,
                release_id=fixture.release_a_id,
            )
        )
    with pytest.raises(ValueError, match="cross-course"):
        repository.list_learning_gap_signals(
            fixture.course_b_id, fixture.release_a_id, active_at=ACTIVE_AT
        )
    repository.close()


def test_expired_signals_are_hidden_and_deletable(tmp_path):
    repository = SQLiteStudentRepository(tmp_path / "learning-gap.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    policy = LearningGapPrivacyPolicyV1(retention_days=1)
    signal = _signal(
        account_id=fixture.student_a_id,
        tutor_message_id="tutor-message-expiring",
        course_id=fixture.course_a_id,
        release_id=fixture.release_a_id,
        policy=policy,
    )
    repository.save_learning_gap_signal(signal)

    assert repository.list_learning_gap_signals(
        fixture.course_a_id,
        fixture.release_a_id,
        active_at="2026-08-29T00:00:00+00:00",
    ) == []
    assert repository.delete_expired_learning_gap_signals(
        expired_at=EXPIRED_AT
    ) == 1
    assert repository.delete_expired_learning_gap_signals(
        expired_at=EXPIRED_AT
    ) == 0
    repository.close()


def test_aggregation_suppresses_small_cells_without_exposing_group_details():
    policy = LearningGapPrivacyPolicyV1(minimum_distinct_learners=5)
    signals = [
        _signal(
            account_id=f"student-{index}",
            tutor_message_id=f"message-{index}",
            course_id="course-a",
            release_id="release-a",
            policy=policy,
        )
        for index in range(4)
    ]

    result = aggregate_learning_gap_signals(
        signals,
        course_id="course-a",
        release_id="release-a",
        policy=policy,
        computed_at=ACTIVE_AT,
    )

    assert result.visible_aggregates == []
    assert result.suppressed_group_count == 1
    serialized = result.model_dump_json()
    assert "concept:virtual-memory" not in serialized
    assert "learner_key" not in serialized


def test_visible_aggregate_and_draft_are_deterministic_and_non_executable():
    policy = LearningGapPrivacyPolicyV1(minimum_distinct_learners=5)
    signals = [
        _signal(
            account_id=f"student-{index}",
            tutor_message_id=f"message-{index}",
            course_id="course-a",
            release_id="release-a",
            policy=policy,
        )
        for index in range(5)
    ]
    signals.append(signals[0])

    result = aggregate_learning_gap_signals(
        signals,
        course_id="course-a",
        release_id="release-a",
        policy=policy,
        computed_at=ACTIVE_AT,
    )
    aggregate = result.visible_aggregates[0]
    drafts = build_course_improvement_drafts(result)

    assert aggregate.distinct_learners == 5
    assert aggregate.signal_count == 5
    assert aggregate.tutoring_intent_counts == {"give_hint": 5}
    assert "learner_key" not in aggregate.model_dump()
    assert len(drafts) == 1
    assert drafts == build_course_improvement_drafts(result)
    assert drafts[0].status == "draft-awaiting-professor-review"
    assert "publish" not in drafts[0].model_dump()
    assert "policy" not in drafts[0].model_dump()


def test_aggregation_rejects_cross_scope_signals():
    policy = LearningGapPrivacyPolicyV1(minimum_distinct_learners=3)
    signal = _signal(
        account_id="student-a",
        tutor_message_id="message-a",
        course_id="course-b",
        release_id="release-b",
        policy=policy,
    )

    with pytest.raises(ValueError, match="cross-scope"):
        aggregate_learning_gap_signals(
            [signal],
            course_id="course-a",
            release_id="release-a",
            policy=policy,
            computed_at=ACTIVE_AT,
        )
