from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_worker_reuses_the_single_api_image_build() -> None:
    compose = yaml.safe_load((ROOT / "compose.staging.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert services["api"]["build"]["target"] == "api"
    assert services["worker"]["image"] == services["api"]["image"]
    assert "build" not in services["worker"]


def test_staging_services_share_only_the_durable_runtime_volume() -> None:
    compose = yaml.safe_load((ROOT / "compose.staging.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert services["api"]["volumes"] == ["runtime-data:/var/lib/digital-twin"]
    assert services["worker"]["volumes"] == ["runtime-data:/var/lib/digital-twin"]
    assert "runtime-data:/var/lib/digital-twin" not in services["web"]["volumes"]
