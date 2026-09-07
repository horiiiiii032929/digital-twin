"""Versioned sidecar for known injected-timeout recovery; no quality rescoring.

Product TutorTurn does not expose atomic claims. The exact registered nonfactual
failure template permits a narrow no-claim determination; unknown text is not
accepted. Gold/mechanical scores stay unchanged.
"""
VERSION = "provider-failure-diagnostic-v1"
SAFE_GRAPH_TEXT = "I could not validate that tutoring response. Please restate the step you are working on or ask the instructor."


def diagnose_provider_failure(case: dict, summary: dict, ledger: list[dict]) -> dict:
    eligible = case.get("kind") == "provider-failure"
    if not eligible:
        return {"version": VERSION, "applicable": False, "operational_failure_handling_pass": None}
    response = case.get("response", {})
    case_id = case["id"]
    tied_timeout = case_id in summary.get("injected_failure_cases", []) and any(
        row.get("case") == case_id and row.get("status") == "failed"
        and row.get("error_code") == "timeout" for row in ledger)
    valid = (tied_timeout and response.get("action") == "safe-graph-failure"
             and response.get("text") == SAFE_GRAPH_TEXT
             and response.get("citations") == []
             and response.get("atomic_claims", []) == [])
    return {"version": VERSION, "applicable": True,
            "operational_failure_handling_pass": valid,
            "injected_timeout_tied": tied_timeout,
            "claims_evidence": "exact registered nonfactual failure template; no claim objects exposed by TutorTurn",
            "scope": "Operational closed failure only; original action/content score unchanged"}
