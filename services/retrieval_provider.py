"""Shared sanitized transport, usage, and budget controls for retrieval APIs."""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.digital_twin.evaluation.retrieval_qualification import ProviderUsage


PostJson = Callable[
    [str, Mapping[str, str], Mapping[str, Any], float],
    dict[str, Any],
]


class RetrievalProviderError(RuntimeError):
    """Sanitized provider failure that excludes content and credentials."""


class RetrievalBudgetExceeded(RuntimeError):
    """Raised before a hosted request would exceed the prospective cap."""


@dataclass
class RetrievalUsageLedger:
    max_cost_usd: float
    price_per_million_input_tokens_usd: float
    request_count: int = 0
    input_items: int = 0
    input_characters: int = 0
    input_tokens: int = 0
    retry_count: int = 0
    failure_count: int = 0
    cache_hits: int = 0

    def __post_init__(self) -> None:
        if self.max_cost_usd < 0:
            raise ValueError("max_cost_usd cannot be negative")
        if self.price_per_million_input_tokens_usd < 0:
            raise ValueError("input-token price cannot be negative")
        if self.price_per_million_input_tokens_usd and not self.max_cost_usd:
            raise ValueError("priced usage requires a positive cost cap")

    @property
    def approximate_cost_usd(self) -> float:
        return self.input_tokens * self.price_per_million_input_tokens_usd / 1_000_000

    def require_capacity(self, estimated_input_tokens: int) -> None:
        if estimated_input_tokens < 0:
            raise ValueError("estimated input tokens cannot be negative")
        projected_tokens = self.input_tokens + estimated_input_tokens
        projected_cost = (
            projected_tokens * self.price_per_million_input_tokens_usd / 1_000_000
        )
        if projected_cost > self.max_cost_usd:
            raise RetrievalBudgetExceeded(
                "provider request blocked before exceeding the declared cost cap"
            )

    def record(
        self,
        *,
        values: Sequence[str],
        estimated_input_tokens: int,
        response: Mapping[str, Any] | None = None,
    ) -> None:
        actual_tokens = _response_input_tokens(response) if response else None
        self.request_count += 1
        self.input_items += len(values)
        self.input_characters += sum(len(value) for value in values)
        self.input_tokens += (
            actual_tokens if actual_tokens is not None else estimated_input_tokens
        )

    def record_failure(self) -> None:
        self.failure_count += 1

    def usage_snapshot(self) -> ProviderUsage:
        return ProviderUsage(
            request_count=self.request_count,
            input_items=self.input_items,
            input_characters=self.input_characters,
            input_tokens=self.input_tokens,
            retry_count=self.retry_count,
            failure_count=self.failure_count,
            cache_hits=self.cache_hits,
            approximate_cost_usd=self.approximate_cost_usd,
        )


def estimate_input_tokens(*values: str) -> int:
    """Conservatively estimate tokens for pre-request budget enforcement."""

    return max(1, math.ceil(sum(len(value) for value in values) / 3))


def bearer_headers(api_key: str) -> dict[str, str]:
    if not api_key.strip():
        raise ValueError("retrieval provider API key is required")
    return {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "User-Agent": "digital-twin-retrieval-evaluation/1.0",
    }


def post_json(
    url: str,
    headers: Mapping[str, str],
    body: Mapping[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=dict(headers),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        request_id = error.headers.get("x-request-id", "not-returned")
        raise RetrievalProviderError(
            f"retrieval API returned HTTP {error.code}; request_id={request_id}"
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RetrievalProviderError(
            "retrieval API request failed before a response"
        ) from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RetrievalProviderError("retrieval API returned malformed JSON") from error
    if not isinstance(payload, dict):
        raise RetrievalProviderError(
            "retrieval API returned an unexpected response shape"
        )
    return payload


def _response_input_tokens(response: Mapping[str, Any]) -> int | None:
    usage = response.get("usage")
    if not isinstance(usage, Mapping):
        return None
    for key in ("prompt_tokens", "input_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int) and value >= 0:
            return value
    return None
