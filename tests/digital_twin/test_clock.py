from datetime import UTC, datetime

import pytest

from src.digital_twin.clock import (
    SystemUtcClock,
    VirtualClockSnapshotV1,
    VirtualUtcClock,
    utc_timestamp,
)


ORIGIN = datetime(2026, 8, 31, 0, 0, tzinfo=UTC)


def test_system_clock_returns_aware_utc() -> None:
    instant = SystemUtcClock().now()

    assert instant.tzinfo is UTC
    assert instant.utcoffset().total_seconds() == 0


def test_virtual_clock_advances_and_restores_exactly() -> None:
    clock = VirtualUtcClock(ORIGIN)

    clock.advance_by(60)
    clock.advance_to(datetime(2026, 9, 1, 0, 0, tzinfo=UTC))
    snapshot = clock.snapshot()
    restored = VirtualUtcClock.restore(
        VirtualClockSnapshotV1.model_validate_json(snapshot.model_dump_json())
    )

    assert restored.now() == datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
    assert restored.snapshot() == snapshot


def test_virtual_clock_rejects_naive_and_backward_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        VirtualUtcClock(datetime(2026, 8, 31, 0, 0))

    clock = VirtualUtcClock(ORIGIN)
    clock.advance_by(1)

    with pytest.raises(ValueError, match="cannot move backward"):
        clock.advance_by(-1)
    with pytest.raises(ValueError, match="cannot move backward"):
        clock.advance_to(ORIGIN)


def test_utc_timestamp_uses_second_precision() -> None:
    assert utc_timestamp(ORIGIN.replace(microsecond=123_456)) == (
        "2026-08-31T00:00:00+00:00"
    )
