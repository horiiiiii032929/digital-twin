"""Governed V2.1 staging requires an exact evidence-gate declaration."""

from __future__ import annotations

import pytest

from services.api.app.config import EvidenceGateMode, _evidence_gate_binding_holds


def test_a_record_that_declares_the_same_gate_is_accepted() -> None:
    assert _evidence_gate_binding_holds(
        {"evidence_gate": "question-targeted-ambiguity-safe-v2"},
        EvidenceGateMode.QUESTION_TARGETED_AMBIGUITY_SAFE_V2,
    )


def test_a_record_that_declares_a_different_gate_is_refused() -> None:
    """The control this preserves: a covered gate is not a different gate."""

    assert not _evidence_gate_binding_holds(
        {"evidence_gate": "structured-lexical-v1"},
        EvidenceGateMode.QUESTION_TARGETED_AMBIGUITY_SAFE_V2,
    )


@pytest.mark.parametrize(
    "configuration", [{}, {"evidence_gate": None}, {"evidence_gate": "  "}]
)
def test_a_record_that_predates_the_field_fails_closed(
    configuration: dict[str, object],
) -> None:
    assert not _evidence_gate_binding_holds(
        configuration,
        EvidenceGateMode.QUESTION_TARGETED_AMBIGUITY_SAFE_V2,
    )
