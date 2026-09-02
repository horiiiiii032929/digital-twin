from __future__ import annotations

import pytest

from src.digital_twin.repository_freeze import (
    BLOCKED_OPERATIONS,
    BOUNDED_PILOT_AUTHORIZATIONS,
    FREEZE_ID,
    RepositoryFreezeError,
    freeze_status,
    require_pre_evaluation_operation_allowed,
    require_bounded_pilot_operation_allowed,
)


def test_repository_freeze_blocks_every_registered_operation() -> None:
    for operation in BLOCKED_OPERATIONS:
        with pytest.raises(RepositoryFreezeError, match=FREEZE_ID):
            require_pre_evaluation_operation_allowed(operation)


def test_repository_freeze_fails_closed_for_unknown_operation() -> None:
    with pytest.raises(RepositoryFreezeError, match="not registered"):
        require_pre_evaluation_operation_allowed("unknown")


def test_repository_freeze_status_is_explicit() -> None:
    status = freeze_status()

    assert status.freeze_id == FREEZE_ID
    assert status.active is True
    assert set(status.blocked_operations) == BLOCKED_OPERATIONS


def test_only_exact_reviewed_runs_have_bounded_authorization() -> None:
    pilot_ids = {
        "academic-factual-qa-open-10000-deterministic-development-001",
        "academic-factual-qa-open-10000-reference-aggregate-007",
        "course-digital-twin-whole-system-architecture-development-freeze-001",
        "course-digital-twin-whole-system-architecture-round-1-001",
        "course-digital-twin-whole-system-architecture-round-2-001",
        "course-digital-twin-whole-system-architecture-round-3-001",
        "governed-full-autonomy-v2-1-grounding-successor-011",
        "successor-architecture-development-fold-003-single-case-001",
    }

    for pilot_id in pilot_ids:
        require_bounded_pilot_operation_allowed(pilot_id)

    assert set(BOUNDED_PILOT_AUTHORIZATIONS) == pilot_ids
    assert BOUNDED_PILOT_AUTHORIZATIONS[
        "academic-factual-qa-open-10000-deterministic-development-001"
    ] == ("dataset_generation",)
    assert BOUNDED_PILOT_AUTHORIZATIONS[
        "academic-factual-qa-open-10000-reference-aggregate-007"
    ] == ("dataset_generation",)
    assert BOUNDED_PILOT_AUTHORIZATIONS[
        "governed-full-autonomy-v2-1-grounding-successor-011"
    ] == ("dataset_generation", "method_evaluation_execution")
    assert BOUNDED_PILOT_AUTHORIZATIONS[
        "successor-architecture-development-fold-003-single-case-001"
    ] == ("external_model_evaluation", "method_evaluation_execution")
    for instrument_id in (
        "course-digital-twin-autonomous-long-run-001",
        "academic-factual-qa-grounding-selection-002",
        "governed-full-autonomy-v2-1-actual-product-evaluation-002",
        "governed-full-autonomy-v2-1-actual-product-evaluation-003",
        "governed-full-autonomy-v2-1-actual-product-evaluation-004",
        "governed-full-autonomy-v2-1-actual-product-evaluation-005",
        "academic-factual-qa-source-semantic-atoms-successor-001",
        "academic-factual-qa-source-semantic-atom-comparison-001",
        "academic-factual-qa-source-semantic-atom-failure-validity-audit-001",
        "academic-factual-qa-ambiguity-safe-comparison-001",
        "academic-factual-qa-ambiguity-safe-comparison-002",
        "governed-full-autonomy-v2-1-cross-engine-evaluation-010",
        "successor-architecture-development-fold-001",
        "successor-architecture-development-fold-001-attempt-002",
        "successor-architecture-development-fold-002-single-case-001",
        "successor-architecture-development-fold-002-single-case-attempt-002",
    ):
        with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
            require_bounded_pilot_operation_allowed(
                instrument_id, "external_model_evaluation"
            )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "course-digital-twin-evaluation-program-011",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "academic-factual-qa-open-10000-reference-question-validation-006",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "course-digital-twin-evaluation-program-010",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "course-digital-twin-evaluation-program-009",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "course-digital-twin-evaluation-program-008",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "course-digital-twin-evaluation-program-007",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "course-digital-twin-evaluation-program-006",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "course-digital-twin-evaluation-program-004",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "course-digital-twin-evaluation-program-003",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "course-digital-twin-evaluation-program-002",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "course-digital-twin-nonhuman-evaluation-program-002",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "academic-factual-qa-api-retrieval-selection-001",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "course-digital-twin-evaluation-program-001",
            "method_evaluation_execution",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "academic-factual-qa-r1-model-cascade-001",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "academic-factual-qa-open-10000-reference-question-validation-001",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "academic-factual-qa-open-10000-reference-question-validation-002",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "academic-factual-qa-open-10000-development-product-checkpoint-007",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "academic-factual-qa-open-10000-development-product-checkpoint-006",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "retrieval-index-lifecycle-development-001",
            "local_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "academic-factual-qa-open-10000-development-product-checkpoint-005",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "academic-factual-qa-open-10000-deterministic-development-002",
            "dataset_generation",
        )
    with pytest.raises(RepositoryFreezeError, match="not authorized"):
        require_bounded_pilot_operation_allowed(
            "academic-factual-qa-open-10000-deterministic-development-001",
            "external_model_evaluation",
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "academic-factual-qa-open-10000-v1", "dataset_generation"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("academic-factual-qa-confirmation-002")
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("factual-qa-v3-oracle-pilot-001")
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "academic-factual-qa-end-to-end-pilot-002"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("factual-qa-v3-oracle-pilot-002")
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "evidence-sufficiency-v2-deterministic-audit-001"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "evidence-sufficiency-v2-independent-review-002"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "evidence-sufficiency-v2-independent-review-003"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "evidence-sufficiency-v2-independent-review-004"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "evidence-sufficiency-v2-independent-review-006"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "evidence-sufficiency-v2-independent-review-007"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "evidence-sufficiency-v2-independent-review-008"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "autonomous-tutoring-graph-development-001"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("proactive-outreach-a1-development-001")
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "proactive-outreach-a1-shadow-confirmation-002"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("factual-qa-v3-scale-rehearsal-001")
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("factual-qa-v3-scale-rehearsal-002")
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("factual-qa-v3-scale-rehearsal-003")
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("factual-qa-v3-scale-rehearsal-004")
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("factual-qa-v3-scale-rehearsal-005")
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("factual-qa-v3-scale-rehearsal-006")
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "factual-qa-v3-reviewer-qualification-006"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "factual-qa-v3-reviewer-qualification-007"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("factual-qa-v3-scale-pilot-100-001")
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("factual-qa-v3-scale-pilot-100-002")
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("factual-qa-v3-scale-pilot-100-003")
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "factual-qa-v3-scale-checkpoint-1000-001"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "factual-qa-v3-scale-checkpoint-1000-002"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed(
            "factual-qa-v3-scale-completion-10000-001"
        )
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        require_bounded_pilot_operation_allowed("factual-qa-v3-10000-pipeline-001")
