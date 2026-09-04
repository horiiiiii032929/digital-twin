from pathlib import Path

import pytest

from scripts.run_governed_full_autonomy_v2_1_multi_concept_confirmation_025 import (
    CONCEPT_CARDS,
    _decision,
    _run,
    _validate_design,
)


def test_confirmation_025_is_fresh_and_has_72_cases():
    design = _validate_design()

    assert design["status"] == "valid"
    assert design["network_free"] is True
    assert design["cases"] == 72
    assert len(CONCEPT_CARDS) == 6


def test_confirmation_025_decision_requires_every_gate():
    row = {
        "attribution_accuracy": 1.0,
        "assessment_agreement": 0.96,
        "attempts_recognised": 1.0,
        "quiet_hour_violations": 0.0,
        "frequency_violations": 0.0,
        "cooldown_violations": 0.0,
        "provider_calls": 0.0,
    }
    summary = {"aggregate": {condition: dict(row) for condition in ("t1-v2-reactive", "t1-v2-autonomous")}}

    assert _decision(summary)[0] == "completed-keep"
    summary["aggregate"]["t1-v2-autonomous"]["assessment_agreement"] = 0.94
    assert _decision(summary)[0] == "completed-refine"


@pytest.mark.asyncio
async def test_confirmation_025_smoke_uses_exclusive_output(tmp_path: Path):
    output = tmp_path / "smoke"
    result = await _run(output, smoke=True)

    assert result["decision"] in {"completed-keep", "completed-refine"}
    assert (output / "decision.json").is_file()
    with pytest.raises(FileExistsError):
        await _run(output, smoke=True)
