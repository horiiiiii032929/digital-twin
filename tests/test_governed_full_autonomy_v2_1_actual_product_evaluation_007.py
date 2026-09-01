from __future__ import annotations

import json

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_006 as predecessor,
)
from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_007 as builder,
)


def test_successor_changes_prompt_binding_not_evaluation_contract() -> None:
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
    correction = instrument["runtime_correction"]
    assert correction["version"] == "bounded-prompt-schema-alignment-v1"
    assert correction["cases_changed"] is False
    assert correction["gold_changed"] is False
    assert correction["gates_changed"] is False
    assert correction["model_roles_changed"] is False
