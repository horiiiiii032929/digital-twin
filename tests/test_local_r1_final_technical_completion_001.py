from scripts import run_local_r1_final_technical_completion_001 as runner


def test_program_validation_binds_both_children() -> None:
    result = runner.validate()

    assert result["status"] == "passed-build-only"
    assert result["known_benchmark_10000_touched"] is False
    assert set(result["children"]) == {
        "true-visual-product-checkpoint-001",
        "professor-fidelity-proxy-c0-c3-002",
    }


def test_program_simulation_is_network_free() -> None:
    result = runner.simulate()

    assert result["status"] == "passed-network-free-simulation"
    assert result["provider_calls"] == 0
    assert result["known_benchmark_10000_touched"] is False
