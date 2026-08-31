"""UTC clock contracts shared by production services and finite simulations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator


def require_utc(value: datetime, *, label: str = "clock time") -> datetime:
    """Return an aware UTC instant and reject ambiguous naive datetimes."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value.astimezone(UTC)


def utc_timestamp(value: datetime) -> str:
    """Serialize one UTC instant using the repository's second precision."""

    return require_utc(value).replace(microsecond=0).isoformat()


@runtime_checkable
class UtcClock(Protocol):
    """Authoritative source of wall-clock time for one runtime."""

    def now(self) -> datetime:
        """Return a timezone-aware UTC instant."""


class SystemUtcClock:
    """Production clock backed by the operating system UTC clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class VirtualClockSnapshotV1(BaseModel):
    """Serializable binding used for deterministic interruption and resume."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    origin: datetime
    current: datetime
    timezone: str = "UTC"
    advance_history_seconds: list[int] = Field(default_factory=list)

    @field_validator("origin", "current")
    @classmethod
    def instant_must_be_aware_utc(cls, value: datetime) -> datetime:
        return require_utc(value, label="virtual clock snapshot instant")


class VirtualUtcClock:
    """Monotonic wall clock for tests and evaluation only.

    The production factory never selects this implementation. Evaluation code
    must pass it explicitly to the product service constructors it drives.
    """

    def __init__(self, origin: datetime) -> None:
        instant = require_utc(origin, label="virtual clock origin")
        self._origin = instant
        self._current = instant
        self._advance_history_seconds: list[int] = []
        self._lock = RLock()

    @property
    def origin(self) -> datetime:
        return self._origin

    def now(self) -> datetime:
        with self._lock:
            return self._current

    def advance_by(self, seconds: int) -> datetime:
        if isinstance(seconds, bool) or not isinstance(seconds, int):
            raise TypeError("virtual clock advancement must be whole seconds")
        if seconds < 0:
            raise ValueError("virtual clock cannot move backward")
        with self._lock:
            self._current += timedelta(seconds=seconds)
            self._advance_history_seconds.append(seconds)
            return self._current

    def advance_to(self, instant: datetime) -> datetime:
        target = require_utc(instant, label="virtual clock target")
        with self._lock:
            if target < self._current:
                raise ValueError("virtual clock cannot move backward")
            delta = target - self._current
            seconds = int(delta.total_seconds())
            if self._current + timedelta(seconds=seconds) != target:
                raise ValueError("virtual clock target must use whole-second precision")
            self._current = target
            self._advance_history_seconds.append(seconds)
            return self._current

    def snapshot(self) -> VirtualClockSnapshotV1:
        with self._lock:
            return VirtualClockSnapshotV1(
                origin=self._origin,
                current=self._current,
                advance_history_seconds=list(self._advance_history_seconds),
            )

    @classmethod
    def restore(cls, snapshot: VirtualClockSnapshotV1) -> "VirtualUtcClock":
        clock = cls(snapshot.origin)
        with clock._lock:
            clock._current = snapshot.current
            clock._advance_history_seconds = list(snapshot.advance_history_seconds)
        return clock
