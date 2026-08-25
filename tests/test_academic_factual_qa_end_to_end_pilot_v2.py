from __future__ import annotations

import asyncio
import json
from pathlib import Path

from scripts.run_academic_factual_qa_end_to_end_pilot_v2 import (
    DEFAULT_INSTRUMENT,
    execute_development,
    preflight,
    validate_instrument,
)


def test_v2_instrument_freezes_fair_network_free_development_comparison() -> None:
    instrument = validate_instrument(DEFAULT_INSTRUMENT)
    readiness = preflight(instrument)

    assert readiness["status"] in {
        "ready-network-free-development",
        "blocked-dirty-worktree",
    }
    assert isinstance(readiness["dirty_state"], bool)
    assert readiness["provider_calls"] == 0
    assert instrument["fairness_contract"]["paired_case_ids"] is True
    assert instrument["fairness_contract"]["selection_permitted"] is False
    assert instrument["decision_rule"]["failure_blocks_promotion_not_development"] is True


def test_v2_development_run_is_paired_leakage_free_and_passes_fixed_gates() -> None:
    result = asyncio.run(execute_development(validate_instrument(DEFAULT_INSTRUMENT)))
    by_condition = {
        row["condition_id"]: row for row in result["condition_summaries"]
    }

    assert result["status"] == "completed-go-deeper"
    assert result["provider_calls"] == result["paid_cost_usd"] == 0
    assert result["private_data_read"] is False
    assert result["independent_gold_opened"] is False
    assert result["heldout_opened"] is False
    assert result["method_selected"] is result["product_promoted"] is False
    assert result["paired_draft_comparison"] == {
        "paired_question_count": 160,
        "mismatch_count": 0,
    }
    assert all(result["development_gate_results"].values())

    control = by_condition["T0-ANY-HIT-V2-CONTROL"]
    candidate = by_condition["T0-TWO-BOUNDARY-ATOMIC-CANDIDATE"]
    assert control["unsupported_release_rate"]["estimate"] > 0
    assert control["citation_precision"] < 1
    assert candidate["unsupported_release_rate"]["estimate"] == 0
    assert candidate["supported_answer_retention"]["estimate"] == 1
    assert candidate["expected_claim_complete_rate"]["estimate"] == 1
    assert candidate["citation_precision"] == candidate["citation_recall"] == 1


def test_v2_runner_writes_exclusive_full_result(tmp_path: Path) -> None:
    result = asyncio.run(execute_development(validate_instrument(DEFAULT_INSTRUMENT)))
    output = tmp_path / "result.json"
    output.write_text(json.dumps(result), encoding="utf-8")

    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert len(loaded["case_results"]) == 480
    assert {row["condition_id"] for row in loaded["case_results"]} == {
        "T0-ANY-HIT-V2-CONTROL",
        "T0-STRUCTURED-COVERAGE-ABLATION",
        "T0-TWO-BOUNDARY-ATOMIC-CANDIDATE",
    }
