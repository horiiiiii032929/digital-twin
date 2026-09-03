"""Governed V2.1 may start on a qualification record that predates the gate field.

Commit `1265830` added an evidence-gate binding to the V2.1 startup check, so a
release may only run a gate its qualification covered. That control is right,
but it compares against `selected_configuration["evidence_gate"]` with no
allowance for a record written before the field existed.

`governed-full-autonomy-v2-1-confirmation-001` is such a record. It is the only
run id V2.1 accepts, and it declares no evidence gate, so after `1265830` the
configuration qualified on 2026-09-02 could not start at all.

Enforce the binding when the record declares a gate, and record the gap when it
does not. A record that declares a different gate must still be refused.
"""

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


@pytest.mark.parametrize("configuration", [{}, {"evidence_gate": None}])
def test_a_record_that_predates_the_field_does_not_block_startup(
    configuration: dict[str, object],
) -> None:
    assert _evidence_gate_binding_holds(
        configuration,
        EvidenceGateMode.QUESTION_TARGETED_AMBIGUITY_SAFE_V2,
    )


def test_a_blank_declaration_is_treated_as_absent() -> None:
    assert _evidence_gate_binding_holds(
        {"evidence_gate": "  "},
        EvidenceGateMode.QUESTION_TARGETED_AMBIGUITY_SAFE_V2,
    )
