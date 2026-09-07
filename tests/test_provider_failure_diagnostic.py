import copy

import pytest

from scripts.provider_failure_diagnostic import SAFE_GRAPH_TEXT, diagnose_provider_failure


def fixtures():
    return ({"id": "candidate:timeout", "kind": "provider-failure", "response": {
        "action": "safe-graph-failure", "text": SAFE_GRAPH_TEXT, "citations": []}},
        {"injected_failure_cases": ["candidate:timeout"]},
        [{"case": "candidate:timeout", "status": "failed", "error_code": "timeout"}])


def test_registered_closed_failure_has_separate_diagnostic():
    case, summary, ledger = fixtures()
    result = diagnose_provider_failure(case, summary, ledger)
    assert result["operational_failure_handling_pass"]
    assert "score" not in case


@pytest.mark.parametrize("field,value", [("action", "answer"), ("citations", None),
    ("citations", [{"id": "invented"}]), ("atomic_claims", [{"text": "claim"}]),
    ("text", ""), ("text", SAFE_GRAPH_TEXT + " The answer is 42.")])
def test_answer_claims_citations_and_unregistered_text_never_pass(field, value):
    case, summary, ledger = fixtures()
    case["response"][field] = value
    assert not diagnose_provider_failure(case, summary, ledger)["operational_failure_handling_pass"]


def test_timeout_must_be_explicitly_injected_and_ledger_tied():
    case, summary, ledger = fixtures()
    assert not diagnose_provider_failure(case, {}, ledger)["operational_failure_handling_pass"]
    assert not diagnose_provider_failure(case, summary, [])["operational_failure_handling_pass"]
    malformed = copy.deepcopy(ledger)
    malformed[0]["error_code"] = "malformed-response"
    assert not diagnose_provider_failure(case, summary, malformed)["operational_failure_handling_pass"]
    case["kind"] = "privacy"
    assert diagnose_provider_failure(case, summary, ledger)["operational_failure_handling_pass"] is None
