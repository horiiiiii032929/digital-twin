"""Tests for the network-free wording-requirements discovery."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.build_governed_full_autonomy_v2_1_persona_wording_requirements_022 import (
    LearnerWordingRequirementsV1,
    discover_requirements,
)
from src.digital_twin.evaluation.learner_simulator import PERSONA_ROBUST_PERSONAS


def test_discovery_uses_real_boundary_and_emits_semantic_unique_keys(
    tmp_path: Path,
) -> None:
    package = asyncio.run(
        discover_requirements(
            runtime_root=tmp_path,
            days=2,
            personas=(PERSONA_ROBUST_PERSONAS[0],),
            seeds=(3101,),
            code_revision="a" * 40,
        )
    )

    assert package.discovery_history_count == 5
    assert package.requirement_count > 0
    assert package.provider_calls == 0
    assert not package.private_data_used
    assert all(item.key for item in package.requirements)
    assert all(item.canonical_text for item in package.requirements)
    assert len({item.key for item in package.requirements}) == package.requirement_count


def test_requirements_hash_drift_fails_closed(tmp_path: Path) -> None:
    package = asyncio.run(
        discover_requirements(
            runtime_root=tmp_path,
            days=1,
            personas=(PERSONA_ROBUST_PERSONAS[0],),
            seeds=(3101,),
            code_revision="b" * 40,
        )
    )
    payload = package.model_dump(mode="json")
    payload["requirements"][0]["canonical_text"] += " changed"

    with pytest.raises(ValidationError, match="content hash drifted"):
        LearnerWordingRequirementsV1.model_validate(payload)
