import json
from pathlib import Path

from src.digital_twin.action_router import DeterministicActionRouterV2


ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
CASES_PATH = (
    DATASET_ROOT
    / "academic-factual-qa-action-router-product-development-001-cases.json"
)
GOLD_PATH = (
    DATASET_ROOT
    / "academic-factual-qa-action-router-product-development-001-gold.json"
)
ACTION_MAP = {
    "redirect-graded-work": "refuse",
    "clarify": "clarify",
    "no-evidence": "abstain",
}


def test_v2_routes_all_500_fresh_development_actions_without_gold_at_runtime():
    cases = json.loads(CASES_PATH.read_text())["cases"]
    gold = {
        item["case_id"]: item
        for item in json.loads(GOLD_PATH.read_text())["gold"]
    }
    router = DeterministicActionRouterV2()
    decisions = {}

    for case in cases:
        route = router.route(case["question"])
        decisions[case["case_id"]] = ACTION_MAP.get(
            route.action if route is not None else "", "answer"
        )

    assert len(decisions) == 500
    assert decisions == {
        case_id: item["expected_action"] for case_id, item in gold.items()
    }


def test_v2_action_router_never_imports_hidden_gold():
    source = (ROOT / "src/digital_twin/action_router.py").read_text()

    assert "05_evaluation" not in source
    assert "expected_action" not in source
    assert "canonical_answer" not in source
