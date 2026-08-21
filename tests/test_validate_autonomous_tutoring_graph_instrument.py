import json

from scripts.validate_autonomous_tutoring_graph_instrument import (
    DEFAULT_PATH,
    validate_instrument,
)


def test_autonomous_tutoring_graph_instrument_is_valid():
    payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))

    assert validate_instrument(payload) == []


def test_autonomous_tutoring_graph_instrument_fails_closed_on_authorization():
    payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
    payload["execution"]["provider_calls_authorized"] = True

    assert "provider calls enabled" in validate_instrument(payload)
