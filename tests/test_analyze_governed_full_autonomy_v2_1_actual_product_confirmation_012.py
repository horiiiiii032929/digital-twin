from scripts import (
    analyze_governed_full_autonomy_v2_1_actual_product_confirmation_012 as analysis,
)


def test_confirmation_012_analysis_correction_contract_uses_no_calls() -> None:
    result = analysis.validate_contract()

    assert result["proactive_case_count"] == 220
    assert result["provider_calls_added"] == 0
