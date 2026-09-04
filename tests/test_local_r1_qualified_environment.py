from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUALIFIED_ENV = ROOT / "deploy/local-r1.qualified.env.example"


def _values() -> dict[str, str]:
    return {
        key: value
        for line in QUALIFIED_ENV.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
        for key, value in [line.split("=", 1)]
    }


def test_qualified_environment_pins_exact_release_composition() -> None:
    values = _values()

    assert values["APP_GENERATOR_MODE"] == "deterministic"
    assert values["APP_EVIDENCE_GATE_MODE"] == "dominance-scoped-ambiguity-safe-v3"
    assert values["APP_STUDENT_PROFILE_PATH"].endswith(
        "/student-tutor-r1-local-candidate-v3.json"
    )
    assert values["APP_STUDENT_TUTORING_MODE"] == (
        "governed-autonomous-tutoring-graph-v2.1"
    )
    assert values["APP_AUTONOMY_PLANNER_MODE"] == (
        "openai-gpt-5.6-luna-policy-value"
    )
    assert values["APP_T1_QUALIFICATION_RESULT_PATH"].endswith(
        "/governed-full-autonomy-v2-1-release-binding-correction-001.json"
    )


def test_qualified_environment_contains_no_committed_credentials() -> None:
    values = _values()

    assert values["OPENAI_API_KEY"] == ""
    assert values["APP_LEARNING_GAP_HMAC_SECRET"].startswith("replace-with-")
    assert all(
        values[key].startswith("replace-with-")
        for key in (
            "BOOTSTRAP_ADMIN_PASSWORD",
            "STAGING_ADMIN_PASSWORD",
            "STAGING_PROFESSOR_PASSWORD",
            "STAGING_STUDENT_PASSWORD",
        )
    )
