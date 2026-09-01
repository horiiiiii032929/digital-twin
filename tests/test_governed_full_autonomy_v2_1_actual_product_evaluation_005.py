from __future__ import annotations

import json

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_004 as predecessor,
)
from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_005 as builder,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_evaluation_005 as runner,
)


def test_retry_changes_only_dataset_identity() -> None:
    result = builder.validate()
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))

    assert result["status"] == "passed-frozen-pending-execution"
    assert result["case_count"] == 820
    assert [
        (condition, case.model_dump(mode="json"), gold.model_dump(mode="json"))
        for condition, case, gold in builder.build_contract()
    ] == [
        (condition, case.model_dump(mode="json"), gold.model_dump(mode="json"))
        for condition, case, gold in predecessor.build_contract()
    ]
    assert instrument["execution_retry"]["changed_surface"] == []
    assert instrument["execution_retry"]["method_changed"] is False
    assert instrument["execution_retry"]["gates_changed"] is False


def test_retry_preflight_has_exact_authority() -> None:
    result = runner.preflight()

    assert result["status"] in {"blocked-not-authorized", "ready"}
    assert "provider-execution-not-authorized" not in result["blockers"]
    assert "paid-execution-not-authorized" not in result["blockers"]
    assert "repository-freeze-authorization-missing" not in result["blockers"]
    assert result["provider_calls"] == 0
    assert result["hidden_gold_loaded"] is False
