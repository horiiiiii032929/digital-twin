"""Governed deterministic generation accepts the gate the evidence selected.

The runtime pinned this pairing to `question-targeted-ambiguity-safe-v2` by
name. `product-evidence-gate-selection-004` then promoted
`dominance-scoped-ambiguity-safe-v3`, which is that same gate with its
ambiguity contest scoped to the leaders that actually tie -- 50.00% fully
grounded factual success against 36.80%, with severe unsupported releases and
operational failures zero in both arms.

The check stays: governed deterministic generation still refuses a gate outside
the qualified pairing. Only the set of qualified gates grew, and it grew by
evidence rather than by convenience.
"""

from __future__ import annotations

import pytest

from services.api.app.config import (
    EvidenceGateMode,
    GOVERNED_DETERMINISTIC_EVIDENCE_GATES,
)


def test_the_previously_pinned_gate_is_still_accepted() -> None:
    assert (
        EvidenceGateMode.QUESTION_TARGETED_AMBIGUITY_SAFE_V2
        in GOVERNED_DETERMINISTIC_EVIDENCE_GATES
    )


def test_the_promoted_successor_is_accepted() -> None:
    assert (
        EvidenceGateMode.DOMINANCE_SCOPED_AMBIGUITY_SAFE_V3
        in GOVERNED_DETERMINISTIC_EVIDENCE_GATES
    )


@pytest.mark.parametrize(
    "mode",
    [
        EvidenceGateMode.UNSELECTED,
        EvidenceGateMode.STRUCTURED_LEXICAL_V1,
        EvidenceGateMode.AMBIGUITY_SAFE_STRUCTURED_LEXICAL_V1,
    ],
)
def test_unqualified_gates_are_still_refused(mode: EvidenceGateMode) -> None:
    """The binding is narrowed by evidence, not removed."""

    assert mode not in GOVERNED_DETERMINISTIC_EVIDENCE_GATES
