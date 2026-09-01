import json

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_008 as predecessor,
)
from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_009 as builder,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_evaluation_009 as runner,
)


def test_fresh_confirmation_is_source_disjoint_and_unauthorized() -> None:
    result = builder.validate()
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))

    assert result["status"] == "passed-frozen-provider-unauthorized"
    assert result["case_count"] == 820
    assert result["source_family_count"] == 50
    assert result["source_disjoint_from_attempt_008"] is True
    assert instrument["authority"]["provider_execution_authorized"] is False
    assert instrument["authority"]["paid_execution_authorized"] is False


def test_fresh_confirmation_changes_cases_and_gold_without_changing_gates() -> None:
    current_public = builder.public_payload()
    current_gold = builder.hidden_gold_payload()
    prior_public = predecessor.public_payload()
    prior_gold = predecessor.hidden_gold_payload()

    assert current_public["content_sha256"] != prior_public["content_sha256"]
    assert current_gold["content_sha256"] != prior_gold["content_sha256"]
    assert current_public["case_count"] == prior_public["case_count"] == 820
    assert current_gold["case_count"] == prior_gold["case_count"] == 820


def test_fresh_confirmation_preflight_fails_closed_before_authorization() -> None:
    result = runner.preflight()

    assert result["status"] == "blocked-not-authorized"
    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
    assert "provider-metadata-refresh-required" not in result["blockers"]
    assert "repository-freeze-authorization-missing" in result["blockers"]
    assert result["provider_calls"] == 0
