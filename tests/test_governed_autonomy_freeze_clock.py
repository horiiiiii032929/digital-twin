from datetime import UTC, datetime

import pytest

from scripts.run_governed_full_autonomy_product_freeze import simulate
from src.digital_twin.clock import SystemUtcClock


@pytest.mark.asyncio
async def test_fixed_rehearsal_does_not_expire_with_wall_clock(monkeypatch):
    monkeypatch.setattr(SystemUtcClock, "now", lambda self: datetime(2040, 1, 1, tzinfo=UTC))
    result = await simulate()
    assert result["status"] == "passed"
    assert result["autonomy"]["simulated_days"] == 7
    assert result["provider_calls"] == 0
