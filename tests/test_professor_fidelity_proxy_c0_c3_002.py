from copy import deepcopy

from scripts import run_professor_fidelity_proxy_c0_c3_002 as runner


def _contexts():
    dataset = runner._load(runner.DATASET_PATH)
    retrieval = runner._retrieval_contexts(dataset)
    return dataset, {
        (case["case_id"], condition): runner._condition_context(
            case, condition, retrieval
        )
        for case in dataset["cases"]
        for condition in runner.CONDITIONS
    }


def test_validate_preserves_synthetic_claim_boundary() -> None:
    result = runner.validate()

    assert result["status"] == "passed-build-only"
    assert result["condition_count"] == 4
    assert result["real_professor_fidelity_claim"] is False
    assert result["provider_execution_authorized"] is False


def test_network_free_simulation_exercises_passing_harness() -> None:
    result = runner.simulate()

    assert result["status"] == "passed-network-free-simulation"
    assert result["hard_gate_simulation_passed"] is True
    assert result["subjective_gate_simulation_passed"] is True
    assert result["response_count"] == 48
    assert result["review_count"] == 24
    assert result["provider_calls"] == 0


def test_c3_context_uses_public_question_retrieval_not_gold() -> None:
    dataset, contexts = _contexts()
    case = next(row for row in dataset["cases"] if row["case_id"] == "pfp-001")
    context = contexts[(case["case_id"], "C3")]

    assert "canonical_answer" not in context
    assert set(context) == {"required_action", "evidence", "decision_reason"}
    assert all(
        set(row) == {"source_id", "locator", "fact"} for row in context["evidence"]
    )


def test_hard_gate_rejects_unknown_citation() -> None:
    dataset, actual = _contexts()
    contexts = dict(actual)
    for case in dataset["cases"]:
        contexts[(case["case_id"], "C3")] = runner._condition_context(
            case,
            "C2",
            runner._retrieval_contexts(dataset),
        )
    outputs = runner._simulated_outputs(dataset, contexts)
    broken = deepcopy(outputs)
    row = next(
        value
        for value in broken
        if value["case_id"] == "pfp-001" and value["condition"] == "C2"
    )
    row["citations"] = [{"source_id": "unknown", "locator": "unknown"}]

    result = runner._hard_gate_metrics(dataset, broken, contexts)

    assert result["passed"] is False
    assert result["conditions"]["C2"]["citation"] == 1


def test_generator_schema_forbids_authoritative_extra_fields() -> None:
    schema = runner._generator_schema("pfp-001", "C2")

    assert schema["additionalProperties"] is False
    assert schema["properties"]["case_id"]["const"] == "pfp-001"
    assert schema["properties"]["condition"]["const"] == "C2"
