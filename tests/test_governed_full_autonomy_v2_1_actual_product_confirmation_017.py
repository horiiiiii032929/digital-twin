from __future__ import annotations

import json

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_confirmation_016 as package,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_confirmation_017 as runner,
)


def test_017_reuses_the_unopened_016_package_without_method_changes() -> None:
    instrument = json.loads(runner.INSTRUMENT.read_text(encoding="utf-8"))
    result = runner.validate_attempt()

    assert result["case_count"] == 820
    assert result["public_sha256"] == package.public_payload()["content_sha256"]
    assert result["hidden_gold_sha256"] == package.hidden_gold_payload()[
        "content_sha256"
    ]
    assert instrument["dataset"]["prior_public_canary_count"] == 2
    assert instrument["dataset"]["reused_after_attempt_016_hidden_gold_open_count"] == 0
    assert instrument["execution"]["canary_correction_only"] is True


def test_017_canary_exercises_the_autonomous_provider_path() -> None:
    assert runner.CONTEXT.canary_case_ids == (
        "release-grounded-h-e1-trajectory-001-t0-grounded-control-seed-1",
        "release-grounded-h-e1-trajectory-006-t1-v2-autonomous-seed-1",
    )
    assert runner.CONTEXT.expected_canary_models == {
        "t0-grounded-control": set(),
        "t1-v2-autonomous": {"gpt-5.6-luna"},
    }


def test_017_is_the_only_bounded_corrective_attempt() -> None:
    result = runner.validate_attempt()

    assert result["status"] == "frozen-pending-execution"
    assert result["provider_execution_authorized"] is True
    assert result["paid_execution_authorized"] is True


def test_017_preflight_accepts_authority_before_cleanliness_checks() -> None:
    result = runner.shared.preflight(context=runner.CONTEXT)

    assert "provider-execution-not-authorized" not in result["blockers"]
    assert "paid-execution-not-authorized" not in result["blockers"]
    assert "repository-freeze-authorization-missing" not in result["blockers"]
    assert result["provider_calls"] == 0
    assert result["hidden_gold_loaded"] is False
