import json

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_confirmation_016 as builder,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_confirmation_016 as runner,
)


def test_confirmation_016_is_fresh_and_provider_unauthorized() -> None:
    result = builder.validate()
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))

    assert result["status"] == "reviewed-provider-unauthorized"
    assert result["provider_execution_authorized"] is False
    assert result["paid_execution_authorized"] is False
    assert result["case_count"] == 820
    assert result["source_family_count"] == 50
    assert result["source_disjoint_from_confirmations_012_through_015"] is True
    assert result["instructional_wording_family_disjoint_from_confirmation_015"] is True
    assert instrument["dataset"]["source_family_range"] == [301, 350]


def test_confirmation_016_uses_v3_grounding_and_reference_action_gates() -> None:
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))

    assert runner.CONTEXT.runtime_grounding_architecture_id == (
        "pedagogy-aware-source-semantic-evidence-atoms-v3"
    )
    assert instrument["execution"]["selected_evidence_gate"] == (
        "source-semantic-evidence-atom-gate-v3"
    )
    assert instrument["hard_gates"]["overall_reference_action_accuracy_min"] == 0.95
    assert instrument["hard_gates"][
        "per_condition_reference_action_accuracy_min"
    ] == 0.95


def test_confirmation_016_has_five_fresh_confusion_phrasings() -> None:
    phrasings = {
        event.payload["message"]
        for _condition, case, _gold in builder.build_contract()
        for event in case.events
        if event.kind == "student-message"
        and event.payload.get("turn_kind") == "confusion"
    }

    assert len(phrasings) == 50
    assert all("Resilient tutoring procedure" in value for value in phrasings)


def test_confirmation_016_preflight_fails_closed_without_authority() -> None:
    result = runner.shared.preflight(context=runner.CONTEXT)

    assert result["status"] == "blocked-not-authorized"
    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
    assert "repository-freeze-authorization-missing" in result["blockers"]
    assert result["provider_calls"] == 0
    assert result["hidden_gold_loaded"] is False
