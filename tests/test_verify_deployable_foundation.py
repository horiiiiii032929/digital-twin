from scripts.verify_deployable_foundation import run_acceptance


def test_current_deployable_foundation_acceptance_passes() -> None:
    result = run_acceptance()

    assert result["run_id"] == (
        "deployable-product-foundation-v7-post-correctness-requalification-001"
    )
    assert result["decision"] == "go-deeper"
    assert result["passed_checks"] == result["total_checks"] == 42
    assert result["failures"] == []
    assert result["network_calls"] == 0
    assert result["private_data_used"] is False
