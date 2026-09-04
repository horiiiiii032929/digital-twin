"""Flow-independent packet and scoring helpers for professor-fidelity proxies."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import random
from typing import Any, Iterable


CONDITIONS = ("C0", "C1", "C2", "C3")
HARD_GATES = (
    "factual_correctness",
    "citation_grounding",
    "safety",
    "boundary_action",
)
FIDELITY_DIMENSIONS = (
    "teaching_style",
    "explanation_depth",
    "example_policy",
    "misconception_handling",
    "academic_integrity",
)
VALID_ACTIONS = {"answer", "abstain", "clarify", "refuse"}


class ProfessorFidelityProxyError(ValueError):
    """Raised when a proxy packet cannot support an interpretable comparison."""


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()


def validate_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    cases = dataset.get("cases")
    if not isinstance(cases, list) or len(cases) != 12:
        raise ProfessorFidelityProxyError("proxy packet must contain exactly 12 cases")
    ids = [row.get("case_id") for row in cases]
    if len(set(ids)) != len(ids) or not all(isinstance(value, str) for value in ids):
        raise ProfessorFidelityProxyError("proxy case IDs must be unique strings")
    if tuple(dataset.get("conditions", [])) != CONDITIONS:
        raise ProfessorFidelityProxyError("C0-C3 condition contract drifted")
    if tuple(dataset.get("hard_gates", [])) != HARD_GATES:
        raise ProfessorFidelityProxyError("hard-gate contract drifted")
    if tuple(dataset.get("fidelity_dimensions", [])) != FIDELITY_DIMENSIONS:
        raise ProfessorFidelityProxyError("fidelity-dimension contract drifted")
    if dataset.get("private_data_used") is not False:
        raise ProfessorFidelityProxyError("proxy packet must remain synthetic/public")
    if dataset.get("real_professor_reference") is not False:
        raise ProfessorFidelityProxyError("synthetic packet cannot be a professor reference")
    for case in cases:
        action = case.get("expected_action")
        if action not in VALID_ACTIONS:
            raise ProfessorFidelityProxyError("unknown expected action")
        evidence = case.get("evidence")
        if not isinstance(evidence, dict):
            raise ProfessorFidelityProxyError("case evidence contract is absent")
        if action == "answer" and not all(
            str(evidence.get(key, "")).strip() for key in ("source_id", "locator", "quote")
        ):
            raise ProfessorFidelityProxyError("answerable case lacks source lineage")
        focus = case.get("focus_dimensions")
        if (
            not isinstance(focus, list)
            or not focus
            or len(focus) != len(set(focus))
            or not set(focus) <= set(FIDELITY_DIMENSIONS)
        ):
            raise ProfessorFidelityProxyError("case fidelity focus is invalid")
    return {
        "dataset_id": dataset["dataset_id"],
        "case_count": len(cases),
        "answerable_count": sum(row["expected_action"] == "answer" for row in cases),
        "boundary_count": sum(row["expected_action"] != "answer" for row in cases),
        "dataset_sha256": canonical_sha256(dataset),
    }


def validate_instrument(instrument: dict[str, Any]) -> dict[str, Any]:
    conditions = instrument.get("conditions")
    if not isinstance(conditions, list) or tuple(
        row.get("condition_id") for row in conditions
    ) != CONDITIONS:
        raise ProfessorFidelityProxyError("instrument condition order drifted")
    by_id = {row["condition_id"]: row for row in conditions}
    if by_id["C0"] != {"condition_id": "C0", "evidence": "none", "policy": "generic"}:
        raise ProfessorFidelityProxyError("C0 baseline drifted")
    if by_id["C1"]["evidence"] != by_id["C2"]["evidence"] or by_id["C1"]["policy"] == by_id["C2"]["policy"]:
        raise ProfessorFidelityProxyError("C1-C2 isolation contract drifted")
    if by_id["C2"]["policy"] != by_id["C3"]["policy"] or by_id["C3"]["evidence"] == "oracle":
        raise ProfessorFidelityProxyError("C2-C3 retrieval contrast drifted")
    boundary = instrument.get("decision_boundary", {})
    if (
        boundary.get("real_professor_fidelity_claim_allowed") is not False
        or boundary.get("professor_approval_required_for_reference") is not True
        or instrument.get("llm_review_authority") != "advisory"
        or instrument.get("hard_gate_authority") != "deterministic"
        or instrument.get("provider_execution_authorized") is not False
    ):
        raise ProfessorFidelityProxyError("proxy authority boundary drifted")
    return {
        "instrument_id": instrument["instrument_id"],
        "instrument_sha256": canonical_sha256(instrument),
    }


def build_blinded_packet(
    dataset: dict[str, Any],
    responses: Iterable[dict[str, Any]],
    *,
    seed: int,
) -> dict[str, Any]:
    validate_dataset(dataset)
    response_rows = list(responses)
    expected_keys = {
        (case["case_id"], condition)
        for case in dataset["cases"]
        for condition in CONDITIONS
    }
    observed_keys = {
        (row.get("case_id"), row.get("condition")) for row in response_rows
    }
    if len(response_rows) != 48 or observed_keys != expected_keys:
        raise ProfessorFidelityProxyError("response portfolio must cover C0-C3 exactly once")
    response_counts = Counter(
        (row.get("case_id"), row.get("condition")) for row in response_rows
    )
    if any(count != 1 for count in response_counts.values()):
        raise ProfessorFidelityProxyError("response portfolio contains duplicates")
    by_key = {(row["case_id"], row["condition"]): row for row in response_rows}
    rng = random.Random(seed)
    items: list[dict[str, Any]] = []
    mapping: dict[str, dict[str, str]] = {}
    case_by_id = {row["case_id"]: row for row in dataset["cases"]}
    for case_id in sorted(case_by_id):
        aliases = ["A", "B", "C", "D"]
        shuffled = list(CONDITIONS)
        rng.shuffle(shuffled)
        item_id = f"proxy-{case_id}"
        mapping[item_id] = dict(zip(aliases, shuffled, strict=True))
        case = case_by_id[case_id]
        items.append(
            {
                "item_id": item_id,
                "question": case["question"],
                "expected_action": case["expected_action"],
                "focus_dimensions": case["focus_dimensions"],
                "responses": [
                    {
                        "alias": alias,
                        "action": by_key[(case_id, condition)]["action"],
                        "text": by_key[(case_id, condition)]["text"],
                        "citations": by_key[(case_id, condition)].get("citations", []),
                    }
                    for alias, condition in mapping[item_id].items()
                ],
            }
        )
    return {
        "schema_version": "1.0.0",
        "packet_id": "professor-fidelity-proxy-blinded-001",
        "dataset_id": dataset["dataset_id"],
        "seed": seed,
        "items": items,
        "mapping": mapping,
        "real_professor_reference": False,
    }


def score_reviews(
    packet: dict[str, Any], reviews: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    mapping = packet.get("mapping")
    if not isinstance(mapping, dict) or len(mapping) != 12:
        raise ProfessorFidelityProxyError("blinded mapping is incomplete")
    rows = list(reviews)
    reviewers = sorted({str(row.get("reviewer_id")) for row in rows})
    if len(reviewers) < 2:
        raise ProfessorFidelityProxyError("at least two LLM reviewer configurations are required")
    expected = {(reviewer, item_id) for reviewer in reviewers for item_id in mapping}
    observed = {(str(row.get("reviewer_id")), row.get("item_id")) for row in rows}
    if len(rows) != len(expected) or observed != expected:
        raise ProfessorFidelityProxyError("review portfolio is incomplete or duplicated")
    preference_counts: Counter[str] = Counter()
    for row in rows:
        item_mapping = mapping[row["item_id"]]
        preference = row.get("preferred_alias")
        if preference not in item_mapping:
            raise ProfessorFidelityProxyError("review preference alias is invalid")
        ratings = row.get("ratings")
        if not isinstance(ratings, dict) or set(ratings) != set(FIDELITY_DIMENSIONS):
            raise ProfessorFidelityProxyError("review ratings are incomplete")
        if any(not isinstance(value, int) or not 1 <= value <= 5 for value in ratings.values()):
            raise ProfessorFidelityProxyError("review rating must be an integer from 1 to 5")
        preference_counts[item_mapping[preference]] += 1
    return {
        "status": "completed-go-deeper",
        "reviewer_count": len(reviewers),
        "review_count": len(rows),
        "preferred_condition_counts": dict(sorted(preference_counts.items())),
        "claim_boundary": {
            "synthetic_llm_proxy": True,
            "real_professor_fidelity": False,
            "real_professor_approval_required": True,
        },
    }
