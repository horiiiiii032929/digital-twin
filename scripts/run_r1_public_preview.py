#!/usr/bin/env python3
"""Start or stop the bounded R1 Cloudflare Quick Tunnel preview."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import time

from dotenv import load_dotenv

from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "compose.preview.yml"
GENERATED_URL = ROOT / "reports/generated/r1-preview-url.txt"
URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


class PreviewError(RuntimeError):
    pass


def _compose(*arguments: str, environment: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), *arguments],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def validate() -> dict[str, object]:
    if not COMPOSE.is_file():
        raise PreviewError("preview Compose file is missing")
    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "config", "--quiet"],
        cwd=ROOT,
        check=True,
    )
    return {
        "status": "passed-build-only",
        "quick_tunnel": True,
        "durable_production_claim": False,
        "sse_enabled": False,
        "provider_call_cap": 250,
        "provider_cost_cap_usd": 5,
    }


def _wait_for_url(environment: dict[str, str]) -> str:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        logs = _compose("logs", "--no-color", "tunnel", environment=environment)
        matches = URL_PATTERN.findall(logs)
        if matches:
            return matches[-1]
        time.sleep(2)
    raise PreviewError("Cloudflare Quick Tunnel did not publish a URL within 90 seconds")


def start(*, build: bool) -> dict[str, object]:
    validate()
    environment = dict(os.environ)
    if environment.get("APP_STUDENT_TUTORING_MODE") == "bounded-tutoring-graph":
        if len(environment.get("APP_LEARNING_GAP_HMAC_SECRET", "").encode()) < 32:
            raise PreviewError("T1 preview requires a 32-byte learning-gap HMAC secret")
    origin_arguments = ["up", "-d"]
    if build:
        origin_arguments.append("--build")
    origin_arguments.extend(["api", "ingestion-worker", "outreach-worker", "web"])
    _compose(*origin_arguments, environment=environment)
    _compose("up", "-d", "tunnel", environment=environment)
    public_url = _wait_for_url(environment)
    environment["DEMO_PUBLIC_ORIGIN"] = public_url
    _compose(
        "up",
        "-d",
        "--force-recreate",
        "api",
        "ingestion-worker",
        "outreach-worker",
        environment=environment,
    )
    GENERATED_URL.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_URL.write_text(public_url + "\n", encoding="utf-8")
    return {
        "status": "running-public-demo",
        "url": public_url,
        "origin_rebound": True,
        "production_sla": False,
    }


def stop() -> dict[str, object]:
    _compose("down")
    return {"status": "stopped", "runtime_data_removed": False}


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--start", action="store_true")
    mode.add_argument("--stop", action="store_true")
    parser.add_argument("--no-build", action="store_true")
    arguments = parser.parse_args()
    if arguments.start:
        require_bounded_pilot_operation_allowed(
            "r1-public-preview-001", "method_evaluation_execution"
        )
        result = start(build=not arguments.no_build)
    elif arguments.stop:
        result = stop()
    else:
        result = validate()
    import json

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
