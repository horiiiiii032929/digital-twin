"""The local R1 stack must be able to start the configuration it qualified.

`local-r1-governed-v2-1-release-qualification-002` recorded Keep for governed
V2.1 with the question-targeted ambiguity-safe gate on revision `b4d25fa`.
Commit `1265830` later replaced the runtime environment's `${VAR:-default}`
forms with literals, so `.env.local-r1` stopped reaching the containers and the
qualified configuration could no longer be started at all.

These tests pin both halves of the fix: every runtime selector is overridable,
and every default is exactly what the literal pinned, so a stack started with
no environment file behaves as it does today.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "compose.local-r1.yml"

# The literal each key was pinned to by commit 1265830. Restoring override
# capability must not change any of them.
RUNTIME_SELECTORS = {
    "APP_GENERATOR_MODE": "deterministic",
    "APP_EVIDENCE_GATE_MODE": "structured-lexical-v1",
    "APP_STUDENT_TUTORING_MODE": "bounded-tutoring-graph",
    "APP_AUTONOMY_PLANNER_MODE": "deterministic",
    "APP_STUDENT_PROFILE_PATH": (
        "/app/research/05_evaluation/profiles/student-tutor-r1-local-candidate-v1.json"
    ),
    "APP_T1_QUALIFICATION_RESULT_PATH": (
        "/app/research/05_evaluation/records/autonomous-tutoring-r1-confirmation-002.json"
    ),
}


def _declaration(key: str) -> str:
    text = COMPOSE.read_text(encoding="utf-8")
    match = re.search(rf"^\s*{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"{key} is not declared in {COMPOSE.name}")
    return match.group(1).strip()


@pytest.mark.parametrize("key", sorted(RUNTIME_SELECTORS))
def test_runtime_selector_is_overridable(key: str) -> None:
    """A literal here cannot be overridden, so the qualified stack cannot start."""

    assert _declaration(key).startswith("${"), (
        f"{key} is pinned to a literal; .env.local-r1 cannot reach the container"
    )


@pytest.mark.parametrize("key,default", sorted(RUNTIME_SELECTORS.items()))
def test_runtime_selector_default_is_unchanged(key: str, default: str) -> None:
    """Restoring override capability must not change what an unset stack runs."""

    assert _declaration(key) == "${" + key + ":-" + default + "}"


def test_the_qualified_configuration_can_be_selected() -> None:
    """The exact selections the 2026-09-02 qualification ran must be reachable."""

    text = COMPOSE.read_text(encoding="utf-8")
    for key in ("APP_EVIDENCE_GATE_MODE", "APP_STUDENT_TUTORING_MODE"):
        assert f"${{{key}:-" in text
