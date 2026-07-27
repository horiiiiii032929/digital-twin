"""Shared, budget-bounded transport for Jina retrieval APIs."""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


JinaPostJson = Callable[
    [str, Mapping[str, str], Mapping[str, Any], float],
    dict[str, Any],
]


class JinaAPIError(RuntimeError):
    """Sanitized provider failure that never includes request content or secrets."""


class JinaBudgetExceeded(RuntimeError):
    """Raised before a request would exceed the declared provider budget."""


@dataclass
class JinaUsageLedger:
    """Track provider requests and enforce a conservative input-token cost cap."""

    max_cost_usd: float
    price_per_million_input_tokens_usd: float = 0.05
    input_tokens: int = 0
    request_count: int = 0

    def __post_init__(self) -> None:
        if self.max_cost_usd <= 0:
            raise ValueError("max_cost_usd must be positive")
        if self.price_per_million_input_tokens_usd <= 0:
            raise ValueError("input-token price must be positive")

    @property
    def approximate_cost_usd(self) -> float:
        return (
            self.input_tokens
            * self.price_per_million_input_tokens_usd
            / 1_000_000
        )

    def require_capacity(self, estimated_input_tokens: int) -> None:
        projected = self.input_tokens + estimated_input_tokens
        projected_cost = (
            projected
            * self.price_per_million_input_tokens_usd
            / 1_000_000
        )
        if projected_cost > self.max_cost_usd:
            raise JinaBudgetExceeded(
                "provider request blocked before exceeding the declared cost cap"
            )

    def record(self, response: Mapping[str, Any], estimated_input_tokens: int) -> None:
        usage = response.get("usage")
        actual = None
        if isinstance(usage, Mapping):
            for key in ("prompt_tokens", "input_tokens", "total_tokens"):
                value = usage.get(key)
                if isinstance(value, int) and value >= 0:
                    actual = value
                    break
        self.input_tokens += actual if actual is not None else estimated_input_tokens
        self.request_count += 1


def estimate_input_tokens(*values: str) -> int:
    """Return a conservative provider-independent estimate for budget gating."""

    return max(1, math.ceil(sum(len(value) for value in values) / 3))


def jina_headers(api_key: str) -> dict[str, str]:
    if not api_key.strip():
        raise ValueError("Jina API key is required")
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
        raise JinaAPIError(
            f"Jina API returned HTTP {error.code}; request_id={request_id}"
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise JinaAPIError("Jina API request failed before a response") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise JinaAPIError("Jina API returned malformed JSON") from error
    if not isinstance(payload, dict):
        raise JinaAPIError("Jina API returned an unexpected response shape")
    return payload
