from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_worker_reuses_the_single_api_image_build() -> None:
    compose = yaml.safe_load((ROOT / "compose.staging.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert services["api"]["build"]["target"] == "api"
    assert services["worker"]["image"] == services["api"]["image"]
    assert "build" not in services["worker"]
    assert (
        compose["x-runtime-environment"]["APP_EVIDENCE_GATE_MODE"]
        == "${APP_EVIDENCE_GATE_MODE:-unselected}"
    )


def test_staging_services_share_only_the_durable_runtime_volume() -> None:
    compose = yaml.safe_load((ROOT / "compose.staging.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert services["api"]["volumes"] == ["runtime-data:/var/lib/digital-twin"]
    assert services["worker"]["volumes"] == ["runtime-data:/var/lib/digital-twin"]
    assert "runtime-data:/var/lib/digital-twin" not in services["web"]["volumes"]


def test_staging_services_use_least_privilege_container_controls() -> None:
    compose = yaml.safe_load((ROOT / "compose.staging.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    for name in ("api", "worker", "web"):
        service = services[name]
        assert service["read_only"] is True
        assert service["init"] is True
        assert service["security_opt"] == ["no-new-privileges:true"]
        assert service["cap_drop"] == ["ALL"]
        assert service["pids_limit"] == 256
        assert service["tmpfs"] == ["/tmp:size=64m,mode=1777"]

    assert "cap_add" not in services["api"]
    assert "cap_add" not in services["worker"]
    assert services["web"]["cap_add"] == ["NET_BIND_SERVICE"]
