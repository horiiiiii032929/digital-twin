from __future__ import annotations

import json

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_007 as predecessor,
)
from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_008 as builder,
)


def test_successor_changes_execution_bounds_not_evaluation_contract() -> None:
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
    correction = instrument["execution_correction"]
    assert correction["version"] == "projected-call-cap-and-concurrency-v1"
    assert correction["cases_changed"] is False
    assert correction["gold_changed"] is False
    assert correction["gates_changed"] is False
    assert instrument["authority"]["maximum_provider_calls"] == 10000
    assert instrument["execution"]["maximum_concurrency"] == 8
