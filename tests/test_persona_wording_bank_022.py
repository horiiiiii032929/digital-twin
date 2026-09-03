"""Tests for the bounded OpenAI persona-wording bank stage."""

from __future__ import annotations

import json

from scripts.build_governed_full_autonomy_v2_1_persona_wording_requirements_022 import (
    load_requirements,
)
from scripts.run_governed_full_autonomy_v2_1_persona_wording_bank_022 import (
    REQUIREMENTS_PATH,
    _parse_rows,
    _prompt,
    _schema,
    preflight,
    validate,
)


def test_validate_binds_all_requirements_to_forty_six_calls() -> None:
    result = validate()

    assert result["requirement_count"] == 1104
    assert result["batch_count"] == 46
    assert result["provider_calls"] == 0
    assert not result["provider_execution_authorized"]


def test_prompt_exposes_wording_only_and_schema_has_no_gold_fields() -> None:
    requirement = load_requirements(REQUIREMENTS_PATH).requirements[0]
    system, prompt = _prompt([requirement])
    payload = json.loads(prompt)

    assert "Change wording only" in system
    assert set(payload["items"][0]) == {
        "key",
        "persona",
        "persona_style",
        "utterance_kind",
        "concept_id",
        "canonical_text",
    }
    assert "hidden_correct" not in prompt
    assert set(_schema()["properties"]["items"]["items"]["properties"]) == {
        "key",
        "text",
    }


def test_parser_matches_by_key_and_quarantines_semantic_drift() -> None:
    requirement = next(
        row
        for row in load_requirements(REQUIREMENTS_PATH).requirements
        if row.kind == "question"
    )
    accepted, rejected = _parse_rows(
        content={
            "items": [
                {
                    "key": requirement.key,
                    "text": requirement.canonical_text,
                }
            ]
        },
        expected=[requirement],
    )
    assert len(accepted) == 1
    assert rejected == []

    accepted, rejected = _parse_rows(
        content={"items": [{"key": requirement.key, "text": "What is this?"}]},
        expected=[requirement],
    )
    assert accepted == []
    assert rejected[0]["reason"] == "missing-concept-anchor"


def test_preflight_is_blocked_until_frozen_authorization(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-only")
    monkeypatch.setattr(
        "scripts.run_governed_full_autonomy_v2_1_persona_wording_bank_022._dirty",
        lambda: False,
    )
    result = preflight(resume=False)

    assert result["status"] == "blocked"
    assert "instrument-not-frozen" in result["blockers"]
    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
