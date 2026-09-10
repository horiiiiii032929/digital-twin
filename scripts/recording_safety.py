"""Refuse recording mutations unless the isolated synthetic factory responds."""

import httpx

RECORDING_ORIGIN = "http://127.0.0.1:8018"
CONTROL_HEADERS = {"X-Recording-Control": "local-synthetic-only"}


def require_recording_runtime(client=None):
    if client is None:
        with httpx.Client(base_url=RECORDING_ORIGIN, trust_env=False, timeout=5) as local:
            return require_recording_runtime(local)
    response = client.get("/__recording/state", headers=CONTROL_HEADERS)
    response.raise_for_status()
    payload = response.json()
    if payload.get("recording_runtime") not in {"synthetic-deterministic-v1", "synthetic-model-backed-v4"}:
        raise RuntimeError("Expected an explicitly named isolated synthetic recording factory.")
    return payload
