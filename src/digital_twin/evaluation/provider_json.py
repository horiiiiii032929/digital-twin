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
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
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
    attempt_count: int = Field(default=1, ge=1)
    recovered_transport_failures: list[str] = Field(default_factory=list)


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
        maximum_transport_retries_total: int | None = None,
    ) -> None:
        if maximum_calls < 1 or not math.isfinite(maximum_cost_usd) or maximum_cost_usd <= 0:
            raise ValueError("provider ledger limits must be positive")
        if (
            maximum_transport_retries_total is not None
            and (
                isinstance(maximum_transport_retries_total, bool)
                or maximum_transport_retries_total < 0
            )
        ):
            raise ValueError("provider transport retry cap must be non-negative")
        self.path = path
        self.maximum_calls = maximum_calls
        self.maximum_cost_usd = maximum_cost_usd
        self.maximum_transport_retries_total = maximum_transport_retries_total
        expected = {
            "schema_version": "1",
            "run_binding_sha256": canonical_sha256(run_binding),
            "maximum_calls": str(maximum_calls),
            "maximum_cost_usd": str(maximum_cost_usd),
        }
        if maximum_transport_retries_total is not None:
            expected["maximum_transport_retries_total"] = str(
                maximum_transport_retries_total
            )
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
                latency_ms REAL NOT NULL DEFAULT 0,
                attempt_count INTEGER NOT NULL DEFAULT 1,
                recovered_transport_failures_json TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        columns = {
            row[1]
            for row in self.connection.execute("PRAGMA table_info(calls)")
        }
        if "attempt_count" not in columns:
            self.connection.execute(
                "ALTER TABLE calls ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 1"
            )
        if "recovered_transport_failures_json" not in columns:
            self.connection.execute(
                "ALTER TABLE calls ADD COLUMN recovered_transport_failures_json "
                "TEXT NOT NULL DEFAULT '[]'"
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

    def remaining_transport_retries(self) -> int | None:
        """Return the retry attempts still available to the next logical call."""

        if self.maximum_transport_retries_total is None:
            return None
        used = int(
            self.connection.execute(
                "SELECT COALESCE(SUM(attempt_count - 1), 0) FROM calls"
            ).fetchone()[0]
        )
        return max(0, self.maximum_transport_retries_total - used)

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
                    response_json, input_tokens, output_tokens, cost_usd, latency_ms,
                    attempt_count, recovered_transport_failures_json
                ) VALUES (?, ?, ?, 'completed', ?, ?, ?, ?, ?, ?, ?)
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
                    response.attempt_count,
                    json.dumps(response.recovered_transport_failures),
                ),
            )
        _, cost = self.totals()
        if cost > self.maximum_cost_usd:
            self._set_metadata("status", "invalid-execution")
            raise ProviderJsonError("provider cost limit exceeded after request")
        if self.maximum_transport_retries_total is not None:
            recovered = self.snapshot()["recovered_transport_failures"]
            if recovered > self.maximum_transport_retries_total:
                self._set_metadata("status", "invalid-execution")
                raise ProviderJsonError(
                    "provider transport retry cap exceeded after request"
                )

    def record_failed(
        self,
        *,
        request_key: str,
        request_sha256: str,
        provider_role: str,
        failure_type: str,
        failure_detail: str,
        latency_ms: float,
        terminal: bool = True,
        attempt_count: int = 1,
        recovered_transport_failures: list[str] | None = None,
    ) -> None:
        if attempt_count < 1:
            raise ValueError("failed provider attempt count must be positive")
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO calls(
                    request_key, request_sha256, provider_role, status,
                    failure_type, failure_detail, latency_ms, attempt_count,
                    recovered_transport_failures_json
                ) VALUES (?, ?, ?, 'failed', ?, ?, ?, ?, ?)
                """,
                (
                    request_key,
                    request_sha256,
                    provider_role,
                    failure_type,
                    failure_detail[:500],
                    latency_ms,
                    attempt_count,
                    json.dumps(recovered_transport_failures or []),
                ),
            )
        if terminal:
            self._set_metadata("status", "invalid-execution")

    def mark_interrupted(self) -> None:
        self._set_metadata("status", "interrupted")

    def mark_invalid_execution(self) -> None:
        """Close a running ledger after a deterministic harness failure."""

        self._set_metadata("status", "invalid-execution")

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
        attempt_usage = self.connection.execute(
            "SELECT COALESCE(SUM(attempt_count), 0), "
            "COALESCE(SUM(attempt_count - 1), 0) FROM calls"
        ).fetchone()
        return {
            **metadata,
            "provider_calls": calls,
            "provider_attempts": int(attempt_usage[0]),
            "recovered_transport_failures": int(attempt_usage[1]),
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
        one_attempt = (
            estimated_input
            * float(self.binding["pricing_usd_per_million_input_tokens"])
            + int(self.binding["max_output_tokens"])
            * float(self.binding["pricing_usd_per_million_output_tokens"])
        ) / 1_000_000
        return one_attempt * (1 + int(self.binding["maximum_transport_retries"]))

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
        quarantine_failures: bool = False,
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
                terminal=not quarantine_failures,
            )
            raise
        ledger.record_completed(
            request_key=request_key,
            request_sha256=request_sha256,
            provider_role=provider_role,
            response=result,
        )
        return result


class _RetryableDirectProviderError(ProviderJsonError):
    """A direct first-party transport failure eligible for a bounded retry."""

    def __init__(
        self,
        message: str,
        *,
        attempt_count: int = 1,
        recovered_transport_failures: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.attempt_count = attempt_count
        self.recovered_transport_failures = recovered_transport_failures or []


class DirectProviderJsonTransport:
    """Strict-schema transport for direct OpenAI and Mistral endpoints.

    Provider routing is impossible by construction: a binding names one
    first-party URL and one exact model. Only timeout, connection, HTTP 429, and
    HTTP 5xx failures may be retried. Malformed JSON, schema drift, refusal, and
    model-identity drift are terminal.
    """

    SUPPORTED_PROVIDERS = frozenset({"openai", "mistral"})

    def __init__(self, binding: dict[str, Any]) -> None:
        if binding.get("provider") not in self.SUPPORTED_PROVIDERS:
            raise ProviderJsonError("unsupported direct provider binding")
        if not binding.get("first_party_endpoint", False):
            raise ProviderJsonError("direct provider binding is not first-party")
        retries = binding.get("maximum_transport_retries", 0)
        if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
            raise ProviderJsonError("direct provider retry limit is invalid")
        self.binding = binding

    def estimated_cost(self, *, prompt: str) -> float:
        estimated_input = math.ceil(len(prompt) / 4)
        one_attempt = (
            estimated_input
            * float(self.binding["pricing_usd_per_million_input_tokens"])
            + int(self.binding["max_output_tokens"])
            * float(self.binding["pricing_usd_per_million_output_tokens"])
        ) / 1_000_000
        return one_attempt * (1 + int(self.binding["maximum_transport_retries"]))

    def _payload(
        self,
        *,
        system: str,
        prompt: str,
        task: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        provider = self.binding["provider"]
        if provider == "openai":
            return {
                "model": self.binding["provider_model"],
                "store": False,
                "input": [
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system}],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}],
                    },
                ],
                "max_output_tokens": self.binding["max_output_tokens"],
                "reasoning": {"effort": self.binding["reasoning_effort"]},
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "academic_factual_qa_output",
                        "strict": True,
                        "schema": schema,
                    }
                },
                "metadata": {"task": task},
            }
        return {
            "model": self.binding["provider_model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.binding["max_output_tokens"],
            "temperature": self.binding["temperature"],
            "random_seed": self.binding["seed"],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "academic_factual_qa_output",
                    "strict": True,
                    "schema": schema,
                },
            },
        }

    def _headers(self, api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _provider_error_detail(value: Any, status_code: int) -> str:
        if isinstance(value, dict):
            error = value.get("error")
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                return error["message"][:300]
            if isinstance(error, str):
                return error[:300]
        return f"HTTP {status_code}"

    async def _post_once(
        self,
        *,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(float(self.binding["timeout_seconds"]))
            ) as client:
                response = await client.post(
                    self.binding["api_url"], headers=headers, json=payload
                )
        except httpx.TimeoutException as error:
            raise _RetryableDirectProviderError("direct provider timeout") from error
        except httpx.HTTPError as error:
            raise _RetryableDirectProviderError(
                "direct provider connection failure"
            ) from error
        if response.status_code == 429 or response.status_code >= 500:
            raise _RetryableDirectProviderError(
                f"direct provider retryable HTTP {response.status_code}"
            )
        return response

    def _parse_openai_content(self, value: dict[str, Any]) -> str:
        if value.get("status") != "completed":
            raise ProviderJsonError("OpenAI response did not complete")
        texts: list[str] = []
        for output in value.get("output", []):
            if not isinstance(output, dict) or output.get("type") != "message":
                continue
            for part in output.get("content", []):
                if isinstance(part, dict) and part.get("type") == "refusal":
                    raise ProviderJsonError("OpenAI response was refused")
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        texts.append(text)
        if len(texts) != 1:
            raise ProviderJsonError("OpenAI response output-text structure drifted")
        return texts[0]

    @staticmethod
    def _parse_mistral_content(value: dict[str, Any]) -> str:
        choices = value.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise ProviderJsonError("Mistral response choices drifted")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ProviderJsonError("Mistral response content is empty")
        return content

    async def call(
        self,
        *,
        system: str,
        prompt: str,
        task: str,
        schema: dict[str, Any],
        maximum_transport_retries: int | None = None,
    ) -> ProviderJsonResponse:
        credential_name = self.binding["credential_environment_variable"]
        api_key = os.getenv(credential_name, "").strip()
        if not api_key:
            raise ProviderJsonError(f"credential missing: {credential_name}")
        payload = self._payload(
            system=system, prompt=prompt, task=task, schema=schema
        )
        headers = self._headers(api_key)
        recovered: list[str] = []
        started = time.perf_counter()
        response: httpx.Response | None = None
        request_retry_limit = int(self.binding["maximum_transport_retries"])
        if maximum_transport_retries is not None:
            request_retry_limit = min(
                request_retry_limit, maximum_transport_retries
            )
        maximum_attempts = 1 + request_retry_limit
        for attempt in range(1, maximum_attempts + 1):
            try:
                response = await self._post_once(headers=headers, payload=payload)
                break
            except _RetryableDirectProviderError as error:
                if attempt == maximum_attempts:
                    raise _RetryableDirectProviderError(
                        str(error),
                        attempt_count=attempt,
                        recovered_transport_failures=recovered,
                    ) from error
                recovered.append(str(error))
        if response is None:
            raise ProviderJsonError("direct provider returned no response")
        latency_ms = (time.perf_counter() - started) * 1000
        request_id = response.headers.get("x-request-id")
        try:
            value = response.json()
        except ValueError as error:
            raise ProviderJsonError("direct provider returned non-JSON HTTP content") from error
        if not isinstance(value, dict):
            raise ProviderJsonError("direct provider HTTP JSON root is not an object")
        if response.is_error or value.get("error"):
            detail = self._provider_error_detail(value, response.status_code)
            raise ProviderJsonError(f"direct provider HTTP failure: {detail}")
        model = value.get("model")
        if model != self.binding["provider_model"]:
            raise ProviderJsonError(
                "direct provider model identity drifted: "
                f"expected={self.binding['provider_model']!r} observed={model!r}"
            )
        content = (
            self._parse_openai_content(value)
            if self.binding["provider"] == "openai"
            else self._parse_mistral_content(value)
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as error:
            raise ProviderJsonError("direct provider content is malformed JSON") from error
        if not isinstance(parsed, dict):
            raise ProviderJsonError("direct provider content root is not an object")
        try:
            Draft202012Validator(schema).validate(parsed)
        except JsonSchemaValidationError as error:
            raise ProviderJsonError(
                f"direct provider content violates schema: {error.message[:240]}"
            ) from error
        usage = value.get("usage") if isinstance(value.get("usage"), dict) else {}
        input_key = (
            "input_tokens" if self.binding["provider"] == "openai" else "prompt_tokens"
        )
        output_key = (
            "output_tokens"
            if self.binding["provider"] == "openai"
            else "completion_tokens"
        )
        input_tokens = _non_negative_int(usage.get(input_key), "input tokens")
        output_tokens = _non_negative_int(usage.get(output_key), "output tokens")
        cost = (
            input_tokens
            * float(self.binding["pricing_usd_per_million_input_tokens"])
            + output_tokens
            * float(self.binding["pricing_usd_per_million_output_tokens"])
        ) / 1_000_000
        return ProviderJsonResponse(
            content=parsed,
            provider_model=model,
            provider_revision=self.binding["documented_revision"],
            endpoint_provider=self.binding["provider_display_name"],
            service_tier=(
                value.get("service_tier")
                if isinstance(value.get("service_tier"), str)
                else None
            ),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            request_id=request_id,
            attempt_count=1 + len(recovered),
            recovered_transport_failures=recovered,
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
        quarantine_failures: bool = False,
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
                system=system,
                prompt=prompt,
                task=task,
                schema=schema,
                maximum_transport_retries=ledger.remaining_transport_retries(),
            )
        except Exception as error:
            ledger.record_failed(
                request_key=request_key,
                request_sha256=request_sha256,
                provider_role=provider_role,
                failure_type=type(error).__name__,
                failure_detail=str(error),
                latency_ms=(time.perf_counter() - started) * 1000,
                terminal=not quarantine_failures,
                attempt_count=int(getattr(error, "attempt_count", 1)),
                recovered_transport_failures=list(
                    getattr(error, "recovered_transport_failures", [])
                ),
            )
            raise
        ledger.record_completed(
            request_key=request_key,
            request_sha256=request_sha256,
            provider_role=provider_role,
            response=result,
        )
        return result
