from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
IMAGE_DIGEST = re.compile(r"^FROM [^\s]+@sha256:[0-9a-f]{64}(?: AS \S+)?$")


def test_ci_third_party_actions_are_immutable_sha_pinned() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    uses = [
        step["uses"]
        for step in workflow["jobs"]["verify"]["steps"]
        if "uses" in step
    ]

    assert uses
    for reference in uses:
        _repository, revision = reference.rsplit("@", 1)
        assert FULL_SHA.fullmatch(revision)


def test_runtime_container_bases_are_digest_pinned_and_surface_is_minimal() -> None:
    dockerfile = (ROOT / "deploy/Dockerfile").read_text()
    from_lines = [line for line in dockerfile.splitlines() if line.startswith("FROM ")]

    assert len(from_lines) == 3
    assert all(IMAGE_DIGEST.fullmatch(line) for line in from_lines)
    assert "COPY scripts scripts" not in dockerfile
    assert "COPY research/05_evaluation/records research/05_evaluation/records" not in dockerfile
    for operational_script in (
        "backup_runtime.py",
        "bootstrap_admin.py",
        "manage_runtime_data.py",
        "restore_runtime.py",
        "run_ingestion_worker.py",
    ):
        assert (
            f"COPY scripts/{operational_script} scripts/{operational_script}"
            in dockerfile
        )
    assert (
        "COPY research/05_evaluation/records/"
        "autonomous-tutoring-r1-confirmation-002.json "
        "research/05_evaluation/records/"
        "autonomous-tutoring-r1-confirmation-002.json"
    ) in dockerfile
    assert (
        "COPY research/05_evaluation/records/"
        "governed-full-autonomy-v2-1-confirmation-001.json "
        "research/05_evaluation/records/"
        "governed-full-autonomy-v2-1-confirmation-001.json"
    ) in dockerfile


def test_historical_review_commands_do_not_bake_in_reproduction_confirmation() -> None:
    scripts = json.loads((ROOT / "package.json").read_text())["scripts"]

    for command_name in (
        "historical:prepare:professor-fidelity-anchor-review",
        "historical:finalize:professor-fidelity-anchor-review",
    ):
        assert "--confirm-historical-reproduction" not in scripts[command_name]


def test_vite_reads_the_documented_repository_root_environment() -> None:
    vite_config = (ROOT / "apps/web/vite.config.ts").read_text()

    assert "envDir: path.resolve(import.meta.dirname, '../..')" in vite_config


def test_vite_does_not_force_a_cyclic_vendor_bundle() -> None:
    vite_config = (ROOT / "apps/web/vite.config.ts").read_text()

    assert "codeSplitting" not in vite_config
    assert "name: 'vendor'" not in vite_config


def test_browser_qa_state_is_ignored_because_it_can_contain_session_cookies() -> None:
    gitignore = (ROOT / ".gitignore").read_text()

    assert ".playwright-cli/" in gitignore


def test_caddy_security_headers_include_transport_and_script_boundaries() -> None:
    caddyfile = (ROOT / "deploy/Caddyfile").read_text()

    assert 'Strict-Transport-Security "max-age=31536000"' in caddyfile
    assert "script-src 'self'" in caddyfile
    assert "object-src 'none'" in caddyfile
    assert "max_size 64MB" in caddyfile
