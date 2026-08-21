from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from scripts.validate_factual_qa_provider_freshness import (
    ProviderFreshnessError,
    compare_live_metadata,
    load_instrument,
    parse_deepseek_pricing,
    parse_deepseek_retention_policy,
    parse_openrouter_models,
    parse_openrouter_provider_retention,
    snapshot_age_hours,
    validate_snapshot,
)


DEEPSEEK_HTML = """
<table>
  <tr><td>MODEL VERSION</td><td>DeepSeek-V4-Flash-0731</td><td>DeepSeek-V4-Pro-0813</td></tr>
  <tr><td>CONTEXT LENGTH</td><td>1M</td></tr>
  <tr><td>MAX OUTPUT</td><td>MAXIMUM: 384K</td></tr>
  <tr><td>1M INPUT TOKENS (CACHE MISS)</td><td>OFF-PEAK</td><td>$0.22</td><td>$0.66</td></tr>
  <tr><td>PEAK</td><td>$0.44</td><td>$1.32</td></tr>
  <tr><td>1M OUTPUT TOKENS</td><td>OFF-PEAK</td><td>$0.66</td><td>$1.98</td></tr>
  <tr><td>PEAK</td><td>$1.32</td><td>$3.96</td></tr>
</table>
"""

DEEPSEEK_PRIVACY_HTML = """
<p>Last Update: Feb 10, 2026</p>
<h4>How Long Do We Keep Your Personal Data</h4>
<p>We keep this Personal Data for as long as you have an account.</p>
<p>We store it in the People's Republic of China.</p>
"""

OPENROUTER_PROVIDERS_HTML = """
<table><tr><td>Mistral</td><td>No</td><td>30 day retention</td><td>Yes</td><td>France</td></tr></table>
"""


def _live() -> dict:
    return {
        "deepseek": parse_deepseek_pricing(DEEPSEEK_HTML),
        "deepseek_retention": parse_deepseek_retention_policy(
            DEEPSEEK_PRIVACY_HTML
        ),
        "openrouter": parse_openrouter_models(
            {
                "data": [
                    {
                        "id": "mistralai/mistral-small-2603",
                        "name": "Mistral: Mistral Small 4",
                        "context_length": 262_144,
                        "pricing": {
                            "prompt": "0.00000015",
                            "completion": "0.0000006",
                        },
                    }
                ]
            }
        ),
        "openrouter_retention": parse_openrouter_provider_retention(
            OPENROUTER_PROVIDERS_HTML
        ),
    }


def test_current_snapshot_uses_conservative_live_prices() -> None:
    instrument = load_instrument()

    assert instrument["model_roles"]["author"]["pricing_usd_per_million_input_tokens"] == 0.44
    assert instrument["model_roles"]["author"]["pricing_usd_per_million_output_tokens"] == 1.32
    assert instrument["model_roles"]["dispute_reviewer"]["pricing_usd_per_million_input_tokens"] == 1.32
    assert instrument["model_roles"]["dispute_reviewer"]["pricing_usd_per_million_output_tokens"] == 3.96
    assert compare_live_metadata(instrument, _live()) == []


def test_deepseek_and_openrouter_parsers_capture_identity_price_and_limits() -> None:
    live = _live()

    assert live["deepseek"]["context_length"] == 1_000_000
    assert live["deepseek"]["maximum_output_tokens"] == 393_216
    assert live["deepseek"]["models"]["deepseek-v4-flash"] == {
        "documented_revision": "DeepSeek-V4-Flash-0731",
        "peak_cache_miss_input_per_million_usd": 0.44,
        "peak_output_per_million_usd": 1.32,
    }
    assert live["openrouter"]["model"] == "mistralai/mistral-small-2603"
    assert live["openrouter"]["input_per_million_usd"] == pytest.approx(0.15)
    assert live["openrouter"]["output_per_million_usd"] == pytest.approx(0.6)
    assert live["deepseek_retention"]["policy_last_update"] == "Feb 10, 2026"
    assert live["openrouter_retention"] == {
        "source": "https://openrouter.ai/providers",
        "provider": "Mistral",
        "trains_on_prompts": False,
        "retention": "30 day retention",
    }


def test_live_price_or_model_drift_fails_closed() -> None:
    instrument = load_instrument()
    live = _live()
    live["deepseek"]["models"]["deepseek-v4-flash"][
        "peak_output_per_million_usd"
    ] = 9.99
    live["openrouter"]["model"] = "mistralai/replacement"

    assert compare_live_metadata(instrument, live) == [
        "binding-drift:deepseek-v4-flash",
        "openrouter-model-drift",
    ]


def test_live_retention_policy_drift_fails_closed() -> None:
    instrument = load_instrument()
    live = _live()
    live["deepseek_retention"]["policy_last_update"] = "changed"
    live["openrouter_retention"]["retention"] = "changed"

    assert compare_live_metadata(instrument, live) == [
        "deepseek-retention-policy-drift",
        "openrouter-retention-policy-drift",
    ]


def test_snapshot_expires_after_exactly_24_hours() -> None:
    instrument = load_instrument()
    verified = datetime.fromisoformat(instrument["freshness"]["verified_at"])

    assert validate_snapshot(
        instrument, now=verified + timedelta(hours=24)
    )["fresh_for_paid_execution"] is True
    assert validate_snapshot(
        instrument, now=verified + timedelta(hours=24, seconds=1)
    )["fresh_for_paid_execution"] is False


def test_future_dated_snapshot_is_rejected() -> None:
    instrument = deepcopy(load_instrument())
    instrument["freshness"]["verified_at"] = (
        datetime.now(timezone.utc) + timedelta(hours=1)
    ).isoformat()

    with pytest.raises(ProviderFreshnessError, match="future"):
        snapshot_age_hours(instrument, now=datetime.now(timezone.utc))
