"""Bounded JSON-only provider transport and replay-safe accounting.

The transport is intentionally evaluation-scoped.  Credentials are read only
at call time, raw responses remain in ignored SQLite ledgers, and callers must
provide a versioned binding with exact model and routing identities.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import time
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field


class ProviderJsonError(RuntimeError):
    """Raised when a provider call cannot produce valid bounded evidence."""


class ProviderJsonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: dict[str, Any]
    provider_model: str = Field(min_length=1)
    provider_revision: str | None = None
    endpoint_provider: str | None = None
    service_tier: str | None = None
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0, allow_inf_nan=False)
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
    request_id: str | None = None


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()


def _non_negative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProviderJsonError(f"provider returned invalid {field}")
    return value


class ProviderCallLedgerV1:
    """Exclusive, hash-bound SQLite call ledger with durable raw responses."""

    def __init__(
        self,
        path: Path,
        *,
        run_binding: dict[str, Any],
        maximum_calls: int,
        maximum_cost_usd: float,
        resume: bool,
    ) -> None:
        if maximum_calls < 1 or not math.isfinite(maximum_cost_usd) or maximum_cost_usd <= 0:
            raise ValueError("provider ledger limits must be positive")
        self.path = path
        self.maximum_calls = maximum_calls
        self.maximum_cost_usd = maximum_cost_usd
        expected = {
            "schema_version": "1",
            "run_binding_sha256": canonical_sha256(run_binding),
            "maximum_calls": str(maximum_calls),
            "maximum_cost_usd": str(maximum_cost_usd),
        }
        if resume and not path.is_file():
            raise ProviderJsonError("provider resume ledger does not exist")
        if not resume and path.exists():
            raise ProviderJsonError("provider ledger already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not resume:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        self.connection = sqlite3.connect(path, isolation_level=None)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS calls (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                request_key TEXT NOT NULL UNIQUE,
                request_sha256 TEXT NOT NULL,
                provider_role TEXT NOT NULL,
                status TEXT NOT NULL,
                response_json TEXT,
                failure_type TEXT,
                failure_detail TEXT,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0,
                latency_ms REAL NOT NULL DEFAULT 0
            )
            """
        )
        if resume:
            actual = dict(self.connection.execute("SELECT key, value FROM metadata"))
            if any(actual.get(key) != value for key, value in expected.items()):
                self.close()
                raise ProviderJsonError("provider resume binding drifted")
            if actual.get("status") not in {"running", "interrupted"}:
                self.close()
                raise ProviderJsonError("provider resume ledger is terminal")
            self._set_metadata("status", "running")
        else:
            with self.connection:
                for key, value in {**expected, "status": "running"}.items():
                    self.connection.execute(
                        "INSERT INTO metadata(key, value) VALUES (?, ?)", (key, value)
                    )

    def _set_metadata(self, key: str, value: str) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO metadata(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def totals(self) -> tuple[int, float]:
        row = self.connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(cost_usd), 0) FROM calls WHERE status != 'replayed'"
        ).fetchone()
        return int(row[0]), float(row[1])

    def replay(
        self, *, request_key: str, request_sha256: str
    ) -> ProviderJsonResponse | None:
        row = self.connection.execute(
            "SELECT request_sha256, status, response_json, failure_type "
            "FROM calls WHERE request_key = ?",
            (request_key,),
        ).fetchone()
        if row is None:
            return None
        if row[0] != request_sha256:
            raise ProviderJsonError(f"provider replay request drifted: {request_key}")
        if row[1] != "completed" or row[2] is None:
            raise ProviderJsonError(
                f"provider replay reached failed call {request_key}: {row[3]}"
            )
        return ProviderJsonResponse.model_validate_json(row[2])

    def reserve(self, *, estimated_cost_usd: float) -> None:
        status = dict(self.connection.execute("SELECT key, value FROM metadata")).get(
            "status"
        )
        if status != "running":
            raise ProviderJsonError("provider ledger is not running")
        calls, cost = self.totals()
        if calls >= self.maximum_calls:
            raise ProviderJsonError("provider call limit reached before request")
        if cost + estimated_cost_usd > self.maximum_cost_usd:
            raise ProviderJsonError("provider cost limit reached before request")

    def record_completed(
        self,
        *,
        request_key: str,
        request_sha256: str,
        provider_role: str,
        response: ProviderJsonResponse,
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO calls(
                    request_key, request_sha256, provider_role, status,
                    response_json, input_tokens, output_tokens, cost_usd, latency_ms
                ) VALUES (?, ?, ?, 'completed', ?, ?, ?, ?, ?)
                """,
                (
                    request_key,
                    request_sha256,
                    provider_role,
                    response.model_dump_json(),
                    response.input_tokens,
                    response.output_tokens,
                    response.cost_usd,
                    response.latency_ms,
                ),
            )
        _, cost = self.totals()
        if cost > self.maximum_cost_usd:
            self._set_metadata("status", "invalid-execution")
            raise ProviderJsonError("provider cost limit exceeded after request")

    def record_failed(
        self,
        *,
        request_key: str,
        request_sha256: str,
        provider_role: str,
        failure_type: str,
        failure_detail: str,
        latency_ms: float,
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO calls(
                    request_key, request_sha256, provider_role, status,
                    failure_type, failure_detail, latency_ms
                ) VALUES (?, ?, ?, 'failed', ?, ?, ?)
                """,
                (
                    request_key,
                    request_sha256,
                    provider_role,
                    failure_type,
                    failure_detail[:500],
                    latency_ms,
                ),
            )
        self._set_metadata("status", "invalid-execution")

    def mark_interrupted(self) -> None:
        self._set_metadata("status", "interrupted")

    def mark_complete(self) -> None:
        if dict(self.connection.execute("SELECT key, value FROM metadata")).get(
            "status"
        ) != "running":
            raise ProviderJsonError("cannot complete a non-running provider ledger")
        self._set_metadata("status", "completed")

    def snapshot(self) -> dict[str, Any]:
        metadata = dict(self.connection.execute("SELECT key, value FROM metadata"))
        calls, cost = self.totals()
        failures = self.connection.execute(
            "SELECT COUNT(*) FROM calls WHERE status = 'failed'"
        ).fetchone()[0]
        usage = self.connection.execute(
            "SELECT COALESCE(SUM(input_tokens), 0), COALESCE(SUM(output_tokens), 0), "
            "COALESCE(MAX(latency_ms), 0) FROM calls"
        ).fetchone()
        return {
            **metadata,
            "provider_calls": calls,
            "failed_calls": int(failures),
            "input_tokens": int(usage[0]),
            "output_tokens": int(usage[1]),
            "maximum_latency_ms": float(usage[2]),
            "reported_cost_usd": cost,
        }

    def close(self) -> None:
        self.connection.close()


class OpenAiCompatibleJsonTransport:
    """Exact-route transport for DeepSeek direct and OpenRouter providers."""

    def __init__(self, binding: dict[str, Any]) -> None:
        self.binding = binding

    def estimated_cost(self, *, prompt: str) -> float:
        estimated_input = math.ceil(len(prompt) / 4)
        return (
            estimated_input
            * float(self.binding["pricing_usd_per_million_input_tokens"])
            + int(self.binding["max_output_tokens"])
            * float(self.binding["pricing_usd_per_million_output_tokens"])
        ) / 1_000_000

    async def call(
        self,
        *,
        system: str,
        prompt: str,
        task: str,
        schema: dict[str, Any],
    ) -> ProviderJsonResponse:
        credential_name = self.binding["credential_environment_variable"]
        api_key = os.getenv(credential_name, "").strip()
        if not api_key:
            raise ProviderJsonError(f"credential missing: {credential_name}")
        provider = self.binding["provider"]
        payload: dict[str, Any] = {
            "model": self.binding["provider_model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.binding["max_output_tokens"],
            "temperature": self.binding["temperature"],
            "metadata": {"task": task},
        }
        if provider == "openrouter":
            payload.update(
                {
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "academic_factual_qa_dataset_output",
                            "strict": True,
                            "schema": schema,
                        },
                    },
                    "provider": self.binding["routing"],
                    "usage": {"include": True},
                    "seed": self.binding["seed"],
                }
            )
            requested_service_tier = self.binding.get("requested_service_tier")
            if requested_service_tier is not None:
                payload["service_tier"] = requested_service_tier
        else:
            payload.update(
                {
                    "response_format": {"type": "json_object"},
                    "thinking": {"type": "disabled"},
                    "user_id": self.binding["provider_user_id"],
                }
            )
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/horiiiiii032929/digital-twin",
            "X-OpenRouter-Metadata": "enabled",
            "X-OpenRouter-Title": "Course Digital Twin evaluation",
        }
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(float(self.binding["timeout_seconds"]))
            ) as client:
                response = await client.post(
                    self.binding["api_url"], headers=headers, json=payload
                )
        except httpx.TimeoutException as error:
            raise ProviderJsonError("provider timeout") from error
        except httpx.HTTPError as error:
            raise ProviderJsonError("provider network failure") from error
        latency_ms = (time.perf_counter() - started) * 1000
        request_id = response.headers.get("x-request-id")
        try:
            value = response.json()
        except ValueError as error:
            raise ProviderJsonError("provider returned non-JSON HTTP content") from error
        if response.is_error or not isinstance(value, dict) or value.get("error"):
            error_value = value.get("error") if isinstance(value, dict) else None
            detail = (
                str(error_value.get("message"))[:300]
                if isinstance(error_value, dict)
                else f"HTTP {response.status_code}"
            )
            raise ProviderJsonError(f"provider HTTP failure: {detail}")
        model = value.get("model")
        if model != self.binding["provider_model"]:
            raise ProviderJsonError(
                "provider response model identity drifted: "
                f"expected={self.binding['provider_model']!r} observed={model!r}"
            )
        endpoint_provider = value.get("provider")
        service_tier = value.get("service_tier")
        if provider == "openrouter":
            if endpoint_provider not in self.binding["runtime_provider_names"]:
                raise ProviderJsonError(
                    "OpenRouter endpoint provider identity drifted: "
                    f"observed={endpoint_provider!r}"
                )
            if service_tier not in self.binding["runtime_service_tiers"]:
                raise ProviderJsonError(
                    f"OpenRouter service tier drifted: observed={service_tier!r}"
                )
        revision = value.get("system_fingerprint")
        if self.binding.get("require_provider_revision") and not isinstance(
            revision, str
        ):
            raise ProviderJsonError("provider response omitted required revision")
        expected_revision = self.binding.get("expected_provider_revision")
        if expected_revision is not None and revision != expected_revision:
            raise ProviderJsonError(
                "provider response revision identity drifted: "
                f"expected={expected_revision!r} observed={revision!r}"
            )
        choices = value.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise ProviderJsonError("provider response choices drifted")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ProviderJsonError("provider response content is empty")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as error:
            raise ProviderJsonError("provider response content is malformed JSON") from error
        if not isinstance(parsed, dict):
            raise ProviderJsonError("provider response JSON root is not an object")
        usage = value.get("usage") if isinstance(value.get("usage"), dict) else {}
        input_tokens = _non_negative_int(usage.get("prompt_tokens", 0), "prompt tokens")
        output_tokens = _non_negative_int(
            usage.get("completion_tokens", 0), "completion tokens"
        )
        calculated = (
            input_tokens
            * float(self.binding["pricing_usd_per_million_input_tokens"])
            + output_tokens
            * float(self.binding["pricing_usd_per_million_output_tokens"])
        ) / 1_000_000
        reported = usage.get("cost", calculated) if provider == "openrouter" else calculated
        if isinstance(reported, bool) or not isinstance(reported, (int, float)):
            raise ProviderJsonError("provider response cost accounting is invalid")
        return ProviderJsonResponse(
            content=parsed,
            provider_model=model,
            provider_revision=revision if isinstance(revision, str) else None,
            endpoint_provider=(
                endpoint_provider if isinstance(endpoint_provider, str) else None
            ),
            service_tier=service_tier if isinstance(service_tier, str) else None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=float(reported),
            latency_ms=latency_ms,
            request_id=request_id,
        )

    async def call_with_ledger(
        self,
        *,
        ledger: ProviderCallLedgerV1,
        request_key: str,
        provider_role: str,
        system: str,
        prompt: str,
        task: str,
        schema: dict[str, Any],
    ) -> ProviderJsonResponse:
        request = {
            "binding_id": self.binding["binding_id"],
            "request_key": request_key,
            "system": system,
            "prompt": prompt,
            "task": task,
            "schema": schema,
        }
        request_sha256 = canonical_sha256(request)
        replayed = ledger.replay(
            request_key=request_key, request_sha256=request_sha256
        )
        if replayed is not None:
            return replayed
        ledger.reserve(estimated_cost_usd=self.estimated_cost(prompt=prompt))
        started = time.perf_counter()
        try:
            result = await self.call(
                system=system, prompt=prompt, task=task, schema=schema
            )
        except Exception as error:
            ledger.record_failed(
                request_key=request_key,
                request_sha256=request_sha256,
                provider_role=provider_role,
                failure_type=type(error).__name__,
                failure_detail=str(error),
                latency_ms=(time.perf_counter() - started) * 1000,
            )
            raise
        ledger.record_completed(
            request_key=request_key,
            request_sha256=request_sha256,
            provider_role=provider_role,
            response=result,
        )
        return result
