from __future__ import annotations

import json

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_003 as predecessor,
)
from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_004 as builder,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_evaluation_004 as runner,
)


def test_correction_changes_only_dataset_identity_and_schema_transport() -> None:
    result = builder.validate()
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))

    assert result["status"] == "passed-terminal"
    assert result["case_count"] == 820
    assert [
        (condition, case.model_dump(mode="json"), gold.model_dump(mode="json"))
        for condition, case, gold in builder.build_contract()
    ] == [
        (condition, case.model_dump(mode="json"), gold.model_dump(mode="json"))
        for condition, case, gold in predecessor.build_contract()
    ]
    assert instrument["harness_correction"]["changed_surface"] == [
        "provider-json-schema-transport"
    ]
    assert instrument["harness_correction"]["method_changed"] is False
    assert instrument["harness_correction"]["gates_changed"] is False


def test_correction_preflight_is_terminal_and_authority_is_revoked() -> None:
    result = runner.preflight()

    assert result["status"] == "blocked-not-authorized"
    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
    assert "repository-freeze-authorization-missing" in result["blockers"]
    assert result["provider_calls"] == 0
    assert result["hidden_gold_loaded"] is False
