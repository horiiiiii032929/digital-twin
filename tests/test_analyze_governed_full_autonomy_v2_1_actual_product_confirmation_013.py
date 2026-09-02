from scripts import (
    analyze_governed_full_autonomy_v2_1_actual_product_confirmation_013 as analysis,
)


def test_confirmation_013_reference_correction_is_exact_and_no_call() -> None:
    result = analysis.validate_contract()

    assert result["corrected_reference_count"] == 30
    assert result["provider_calls_added"] == 0
    assert result["correction_scope"] == (
        "provider-failure-v2-safe-deterministic-fallback"
    )
