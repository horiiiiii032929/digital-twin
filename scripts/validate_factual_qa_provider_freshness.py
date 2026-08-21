#!/usr/bin/env python3
"""Validate frozen provider metadata and optionally compare it with live sources."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/factual_qa_v3_scale_pilot_100_003.json"
)
INSTRUMENT_ID = "factual-qa-v3-scale-pilot-100-003"
DEEPSEEK_URL = "https://api-docs.deepseek.com/quick_start/pricing/"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
DEEPSEEK_PRIVACY_URL = (
    "https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html"
)
OPENROUTER_PROVIDERS_URL = "https://openrouter.ai/providers"
MISTRAL_MODEL = "mistralai/mistral-small-2603"


class ProviderFreshnessError(ValueError):
    """Raised when a provider snapshot is stale, malformed, or mismatched."""


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            value = " ".join("".join(self._cell).split())
            self._row.append(value)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def _price(value: str) -> float:
    match = re.fullmatch(r"\$([0-9]+(?:\.[0-9]+)?)", value.strip())
    if match is None:
        raise ProviderFreshnessError(f"cannot parse provider price: {value!r}")
    return float(match.group(1))


def _numeric_size(value: str) -> int:
    match = re.fullmatch(r"([0-9]+)([MK])", value.strip(), re.IGNORECASE)
    if match is None:
        raise ProviderFreshnessError(f"cannot parse provider size: {value!r}")
    multiplier = 1_000_000 if match.group(2).upper() == "M" else 1024
    return int(match.group(1)) * multiplier


def parse_deepseek_pricing(html: str) -> dict[str, Any]:
    parser = _TableParser()
    parser.feed(html)
    rows = parser.rows
    version_row = next((row for row in rows if row and row[0] == "MODEL VERSION"), None)
    context_row = next((row for row in rows if row and row[0] == "CONTEXT LENGTH"), None)
    output_row = next((row for row in rows if row and row[0] == "MAX OUTPUT"), None)
    if version_row is None or len(version_row) < 3:
        raise ProviderFreshnessError("DeepSeek model revisions are absent")
    if context_row is None or len(context_row) < 2:
        raise ProviderFreshnessError("DeepSeek context length is absent")
    if output_row is None or len(output_row) < 2:
        raise ProviderFreshnessError("DeepSeek maximum output is absent")

    cache_miss_peak: list[float] | None = None
    output_peak: list[float] | None = None
    active_price: str | None = None
    for row in rows:
        joined = " | ".join(row)
        if "1M INPUT TOKENS (CACHE MISS)" in joined:
            active_price = "cache-miss"
            continue
        if "1M OUTPUT TOKENS" in joined:
            active_price = "output"
            continue
        if row and row[0] == "PEAK" and len(row) >= 3:
            values = [_price(row[-2]), _price(row[-1])]
            if active_price == "cache-miss":
                cache_miss_peak = values
            elif active_price == "output":
                output_peak = values
    if cache_miss_peak is None or output_peak is None:
        raise ProviderFreshnessError("DeepSeek peak pricing rows are absent")
    context_length = _numeric_size(context_row[-1])
    maximum_output_match = re.search(r"([0-9]+[MK])", output_row[-1])
    if maximum_output_match is None:
        raise ProviderFreshnessError("DeepSeek maximum output value is absent")
    maximum_output = _numeric_size(maximum_output_match.group(1))
    return {
        "source": DEEPSEEK_URL,
        "context_length": context_length,
        "maximum_output_tokens": maximum_output,
        "models": {
            "deepseek-v4-flash": {
                "documented_revision": version_row[-2],
                "peak_cache_miss_input_per_million_usd": cache_miss_peak[0],
                "peak_output_per_million_usd": output_peak[0],
            },
            "deepseek-v4-pro": {
                "documented_revision": version_row[-1],
                "peak_cache_miss_input_per_million_usd": cache_miss_peak[1],
                "peak_output_per_million_usd": output_peak[1],
            },
        },
    }


def parse_openrouter_models(payload: dict[str, Any]) -> dict[str, Any]:
    models = payload.get("data")
    if not isinstance(models, list):
        raise ProviderFreshnessError("OpenRouter model list is malformed")
    model = next(
        (item for item in models if isinstance(item, dict) and item.get("id") == MISTRAL_MODEL),
        None,
    )
    if model is None:
        raise ProviderFreshnessError(f"OpenRouter model is absent: {MISTRAL_MODEL}")
    pricing = model.get("pricing")
    if not isinstance(pricing, dict):
        raise ProviderFreshnessError("OpenRouter model pricing is absent")
    try:
        input_price = float(pricing["prompt"]) * 1_000_000
        output_price = float(pricing["completion"]) * 1_000_000
    except (KeyError, TypeError, ValueError) as error:
        raise ProviderFreshnessError("OpenRouter token prices are malformed") from error
    return {
        "source": OPENROUTER_MODELS_URL,
        "model": MISTRAL_MODEL,
        "name": model.get("name"),
        "context_length": model.get("context_length"),
        "input_per_million_usd": input_price,
        "output_per_million_usd": output_price,
    }


def parse_deepseek_retention_policy(html: str) -> dict[str, Any]:
    update_match = re.search(r"Last Update:\s*([^<]+)", html)
    if update_match is None:
        raise ProviderFreshnessError("DeepSeek privacy-policy date is absent")
    normalized = " ".join(re.sub(r"<[^>]+>", " ", html).split())
    if "as long as you have an account" not in normalized:
        raise ProviderFreshnessError("DeepSeek account-linked retention term is absent")
    if "People's Republic of China" not in normalized:
        raise ProviderFreshnessError("DeepSeek storage location is absent")
    return {
        "source": DEEPSEEK_PRIVACY_URL,
        "policy_last_update": update_match.group(1).strip(),
        "input_retention": "retained-as-long-as-account-and-as-otherwise-necessary",
        "storage_location": "People's Republic of China",
    }


def parse_openrouter_provider_retention(html: str) -> dict[str, Any]:
    parser = _TableParser()
    parser.feed(html)
    row = next((item for item in parser.rows if item and item[0] == "Mistral"), None)
    if row is None or len(row) < 3:
        raise ProviderFreshnessError("OpenRouter Mistral provider policy is absent")
    return {
        "source": OPENROUTER_PROVIDERS_URL,
        "provider": "Mistral",
        "trains_on_prompts": row[1].casefold() == "yes",
        "retention": row[2],
    }


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "digital-twin-evaluation-freshness/1"})
    with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed official URLs
        return response.read().decode("utf-8")


def fetch_live_provider_metadata() -> dict[str, Any]:
    deepseek = parse_deepseek_pricing(_fetch_text(DEEPSEEK_URL))
    openrouter_payload = json.loads(_fetch_text(OPENROUTER_MODELS_URL))
    return {
        "deepseek": deepseek,
        "deepseek_retention": parse_deepseek_retention_policy(
            _fetch_text(DEEPSEEK_PRIVACY_URL)
        ),
        "openrouter": parse_openrouter_models(openrouter_payload),
        "openrouter_retention": parse_openrouter_provider_retention(
            _fetch_text(OPENROUTER_PROVIDERS_URL)
        ),
    }


def load_instrument(path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    try:
        instrument = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProviderFreshnessError(f"cannot load instrument: {path}") from error
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise ProviderFreshnessError("unexpected freshness instrument ID")
    freshness = instrument.get("freshness")
    if not isinstance(freshness, dict):
        raise ProviderFreshnessError("instrument freshness snapshot is absent")
    if freshness.get("maximum_age_hours_for_paid_execution") != 24:
        raise ProviderFreshnessError("paid freshness window must be exactly 24 hours")
    if freshness.get("paid_preflight_requires_live_match") is not True:
        raise ProviderFreshnessError("paid preflight must require a live provider match")
    retention = freshness.get("retention_policy")
    if not isinstance(retention, dict) or set(retention) != {
        "deepseek",
        "openrouter_mistral_endpoint",
    }:
        raise ProviderFreshnessError("provider retention snapshot is absent")
    reviewer_routing = instrument["model_roles"]["independent_reviewer"].get(
        "provider_routing", {}
    )
    if reviewer_routing.get("allow_fallbacks") is not False:
        raise ProviderFreshnessError("reviewer fallbacks must remain disabled")
    return instrument


def snapshot_age_hours(
    instrument: dict[str, Any], *, now: datetime | None = None
) -> float:
    try:
        verified_at = datetime.fromisoformat(instrument["freshness"]["verified_at"])
    except (KeyError, TypeError, ValueError) as error:
        raise ProviderFreshnessError("freshness verified_at is invalid") from error
    if verified_at.tzinfo is None:
        raise ProviderFreshnessError("freshness verified_at must include a timezone")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    age = (current.astimezone(timezone.utc) - verified_at.astimezone(timezone.utc)).total_seconds() / 3600
    if age < 0:
        raise ProviderFreshnessError("freshness snapshot is dated in the future")
    return age


def compare_live_metadata(
    instrument: dict[str, Any], live: dict[str, Any]
) -> list[str]:
    failures: list[str] = []
    roles = instrument["model_roles"]
    deepseek = live["deepseek"]
    for role_name in ("author", "dispute_reviewer"):
        role = roles[role_name]
        model = role["provider_model"]
        current = deepseek["models"].get(model)
        if current is None:
            failures.append(f"missing-model:{model}")
            continue
        expected = {
            "documented_revision": role["documented_revision"],
            "peak_cache_miss_input_per_million_usd": role[
                "pricing_usd_per_million_input_tokens"
            ],
            "peak_output_per_million_usd": role[
                "pricing_usd_per_million_output_tokens"
            ],
        }
        if current != expected:
            failures.append(f"binding-drift:{model}")
    freshness = instrument["freshness"]
    if deepseek["context_length"] != freshness["deepseek_context_length"]:
        failures.append("deepseek-context-drift")
    if deepseek["maximum_output_tokens"] != freshness["deepseek_maximum_output_tokens"]:
        failures.append("deepseek-output-limit-drift")
    openrouter = live["openrouter"]
    reviewer = roles["independent_reviewer"]
    if openrouter["model"] != reviewer["provider_model"]:
        failures.append("openrouter-model-drift")
    if openrouter["context_length"] != freshness["openrouter_mistral_context_length"]:
        failures.append("openrouter-context-drift")
    if openrouter["input_per_million_usd"] != reviewer["pricing_usd_per_million_input_tokens"]:
        failures.append("openrouter-input-price-drift")
    if openrouter["output_per_million_usd"] != reviewer["pricing_usd_per_million_output_tokens"]:
        failures.append("openrouter-output-price-drift")
    expected_deepseek_retention = {
        "source": freshness["deepseek_privacy_source"],
        **freshness["retention_policy"]["deepseek"],
    }
    if live.get("deepseek_retention") != expected_deepseek_retention:
        failures.append("deepseek-retention-policy-drift")
    expected_openrouter_retention = {
        "source": freshness["openrouter_provider_policy_source"],
        "provider": freshness["retention_policy"]["openrouter_mistral_endpoint"][
            "provider"
        ],
        "trains_on_prompts": freshness["retention_policy"][
            "openrouter_mistral_endpoint"
        ]["trains_on_prompts"],
        "retention": freshness["retention_policy"]["openrouter_mistral_endpoint"][
            "retention"
        ],
    }
    if live.get("openrouter_retention") != expected_openrouter_retention:
        failures.append("openrouter-retention-policy-drift")
    return failures


def validate_snapshot(
    instrument: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    age = snapshot_age_hours(instrument, now=now)
    maximum = float(instrument["freshness"]["maximum_age_hours_for_paid_execution"])
    return {
        "instrument_id": instrument["instrument_id"],
        "snapshot_age_hours": age,
        "maximum_age_hours_for_paid_execution": maximum,
        "fresh_for_paid_execution": age <= maximum,
        "live_match_checked": False,
        "provider_or_model_called": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=INSTRUMENT_PATH)
    parser.add_argument("--live", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    instrument = load_instrument(arguments.instrument)
    result = validate_snapshot(instrument)
    if arguments.live:
        live = fetch_live_provider_metadata()
        failures = compare_live_metadata(instrument, live)
        result.update(
            {
                "live_match_checked": True,
                "live_match": not failures,
                "failures": failures,
                "live": live,
            }
        )
        if failures:
            print(json.dumps(result, indent=2, sort_keys=True))
            return 1
    result["status"] = "passed"
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
