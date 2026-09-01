from __future__ import annotations

import json

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_005 as predecessor,
)
from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_006 as builder,
)


def test_successor_changes_diagnostics_not_evaluated_contract() -> None:
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
    correction = instrument["diagnostic_correction"]
    assert correction["version"] == "privacy-safe-responses-diagnostics-v1"
    assert correction["evaluated_method_changed"] is False
    assert correction["raw_provider_output_retained"] is False
    assert correction["provider_usage_retained_on_malformed"] is True
    assert result["provider_execution_authorized"] is False
    assert result["paid_execution_authorized"] is False
