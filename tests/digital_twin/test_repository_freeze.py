from __future__ import annotations

import pytest

from src.digital_twin.repository_freeze import (
    BLOCKED_OPERATIONS,
    FREEZE_ID,
    RepositoryFreezeError,
    freeze_status,
    require_pre_evaluation_operation_allowed,
)


def test_repository_freeze_blocks_every_registered_operation() -> None:
    for operation in BLOCKED_OPERATIONS:
        with pytest.raises(RepositoryFreezeError, match=FREEZE_ID):
            require_pre_evaluation_operation_allowed(operation)


def test_repository_freeze_fails_closed_for_unknown_operation() -> None:
    with pytest.raises(RepositoryFreezeError, match="not registered"):
        require_pre_evaluation_operation_allowed("unknown")


def test_repository_freeze_status_is_explicit() -> None:
    status = freeze_status()

    assert status.freeze_id == FREEZE_ID
    assert status.active is True
    assert set(status.blocked_operations) == BLOCKED_OPERATIONS
