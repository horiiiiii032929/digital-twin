"""Check that the longitudinal audit does not create evidence by pooling it."""
import json
import sqlite3
import socket
import sys

import pytest

from scripts.run_goal_completion_scope import audit_completions, target_ready
from scripts import run_goal_completion_scope as runner


def attribution(concept, correct=2, confidence=0.5):
    return {"concept_id": concept, "correct_evidence_count": correct,
            "incorrect_evidence_count": 0, "attribution_confidence": confidence}


def test_oracle_requires_all_targets_and_confidence():
    assert not target_ready([], {"a": attribution("a")})
    assert not target_ready(["a", "b"], {"a": attribution("a")})
    assert not target_ready(["a"], {"a": attribution("a", confidence=0.49)})
    assert target_ready(["a", "b"], {"a": attribution("a"), "b": attribution("b")})


@pytest.mark.parametrize("scenario,expected", [
    ("complete", True), ("uncommitted", False), ("future", False),
    ("different-conversations", False), ("wrong-student", False),
    ("wrong-release", False), ("later-contradiction", False),
])
def test_audit_uses_scoped_committed_snapshots(tmp_path, scenario, expected):
    connection = sqlite3.connect(tmp_path / "runtime.sqlite3")
    connection.executescript("""
        CREATE TABLE autonomous_goals(status TEXT, goal_json TEXT);
        CREATE TABLE course_domain_models(release_id TEXT, model_json TEXT);
        CREATE TABLE conversations(id TEXT, student_id TEXT);
        CREATE TABLE learner_state_deltas_v2(conversation_id TEXT, next_revision INTEGER, observation_id TEXT);
        CREATE TABLE learner_observations_v2(observation_id TEXT, course_id TEXT, release_id TEXT, observation_json TEXT);
        CREATE TABLE learner_concept_attributions_v2(conversation_id TEXT, revision INTEGER, concept_id TEXT, attribution_json TEXT);
    """)
    goal = {"goal_id": "goal", "student_id": "student", "course_id": "course",
            "release_id": "release", "approved_course_objective": "objective",
            "updated_at": "2026-09-08T00:00:00+00:00"}
    connection.execute("INSERT INTO autonomous_goals VALUES (?, ?)", ("completed", json.dumps(goal)))
    connection.execute("INSERT INTO course_domain_models VALUES (?, ?)", (
        "release", json.dumps({"objectives": [{"statement": "objective", "concept_ids": ["a", "b"]}]})))
    for index, concepts in enumerate((["a"], ["b"]) if scenario == "different-conversations" else (["a", "b"],)):
        conv, obs = f"conv-{index}", f"obs-{index}"
        connection.execute("INSERT INTO conversations VALUES (?, ?)", (conv, "other" if scenario == "wrong-student" else "student"))
        connection.execute("INSERT INTO learner_observations_v2 VALUES (?, ?, ?, ?)", (
            obs, "course", "other" if scenario == "wrong-release" else "release",
            json.dumps({"observed_at": "2026-09-09T00:00:00+00:00" if scenario == "future" else "2026-09-07T00:00:00+00:00"})))
        if scenario != "uncommitted":
            connection.execute("INSERT INTO learner_state_deltas_v2 VALUES (?, 1, ?)", (conv, obs))
        for concept in concepts:
            connection.execute("INSERT INTO learner_concept_attributions_v2 VALUES (?, 1, ?, ?)", (conv, concept, json.dumps(attribution(concept))))
        if scenario == "later-contradiction":
            connection.execute("INSERT INTO learner_observations_v2 VALUES ('later', 'course', 'release', ?)", (json.dumps({"observed_at": goal["updated_at"]}),))
            connection.execute("INSERT INTO learner_state_deltas_v2 VALUES (?, 2, 'later')", (conv,))
            for concept in concepts:
                value = {**attribution(concept), "incorrect_evidence_count": 1}
                connection.execute("INSERT INTO learner_concept_attributions_v2 VALUES (?, 2, ?, ?)", (conv, concept, json.dumps(value)))
    connection.commit()
    connection.close()
    audit = audit_completions(tmp_path)
    assert audit["completed"] == 1
    assert audit["records"][0]["supported"] is expected


@pytest.mark.asyncio
async def test_regression_entrypoint_disallows_provider_and_network(tmp_path, monkeypatch):
    class DriverReached(Exception):
        pass

    async def driver(**kwargs):
        assert kwargs["provider_backed"] is False
        with pytest.raises(AssertionError, match="external network forbidden"):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.connect(("127.0.0.1", 9))
        raise DriverReached

    monkeypatch.setattr(runner, "source_files", lambda: [])
    monkeypatch.setattr(runner, "run_program", driver)
    with pytest.raises(DriverReached):
        await runner.run("candidate", tmp_path / "exclusive")


def test_regression_cli_has_no_provider_execution_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["goal-scope", "--arm", "candidate", "--output-dir", str(tmp_path), "--execute"])
    with pytest.raises(SystemExit) as error:
        runner.main()
    assert error.value.code == 2
