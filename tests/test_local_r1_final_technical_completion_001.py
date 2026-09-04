from scripts import run_local_r1_final_technical_completion_001 as runner
from scripts import run_true_visual_product_checkpoint as visual_runner


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


def test_visual_product_derives_display_title_without_changing_frozen_source() -> None:
    sources = visual_runner._load_hashed(visual_runner.SOURCES_PATH)

    assert all("title" not in asset for asset in sources["assets"])
    chunks = visual_runner._chunks_by_course(sources)

    assert sum(len(values) for values in chunks.values()) == 30
    assert all(
        isinstance(chunk.metadata.get("title"), str)
        and bool(chunk.metadata["title"].strip())
        for values in chunks.values()
        for chunk in values
    )
