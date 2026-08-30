"""Shared I/O and exact OpenAI bindings for finite-program stage capsules."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from src.digital_twin.evaluation.finite_program import (
    ProgramManifestV1,
    canonical_sha256,
)


class FiniteProgramIoError(RuntimeError):
    """Raised when a stage package or model binding drifts."""


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FiniteProgramIoError(f"JSON package unavailable: {path.name}") from error
    if not isinstance(value, dict):
        raise FiniteProgramIoError(f"JSON root must be an object: {path.name}")
    return value


def verify_hashed_package(path: Path, *, rows_key: str) -> dict[str, Any]:
    payload = load_json_object(path)
    rows = payload.get(rows_key)
    expected = canonical_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if not isinstance(rows, list) or payload.get("content_sha256") != expected:
        raise FiniteProgramIoError(f"package hash or rows drifted: {path.name}")
    if payload.get("case_count") != len(rows):
        raise FiniteProgramIoError(f"package count drifted: {path.name}")
    return payload


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_binding(
    manifest: ProgramManifestV1,
    *,
    role: str,
    maximum_output_tokens: int,
    maximum_transport_retries: int = 0,
) -> dict[str, Any]:
    model = next((row for row in manifest.models if row.role == role), None)
    if model is None:
        raise FiniteProgramIoError(f"program model role is unavailable: {role}")
    return {
        "binding_id": f"{manifest.program_id}-{role}-v1",
        "provider": "openai",
        "provider_display_name": "OpenAI",
        "first_party_endpoint": True,
        "api_url": manifest.provider_endpoint,
        "credential_environment_variable": manifest.credential_environment_variable,
        "provider_model": model.model,
        "documented_revision": model.documented_revision,
        "reasoning_effort": "low",
        "max_output_tokens": maximum_output_tokens,
        "temperature": 0,
        "seed": 20260830,
        "timeout_seconds": 60,
        "maximum_transport_retries": maximum_transport_retries,
        "pricing_usd_per_million_input_tokens": (
            model.input_price_usd_per_million
        ),
        "pricing_usd_per_million_output_tokens": (
            model.output_price_usd_per_million
        ),
    }
