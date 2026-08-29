from scripts import run_academic_factual_qa_r1_model_cascade as cascade


def test_completed_cascade_is_revoked_and_still_exactly_four_models_and_200_cases():
    result = cascade.validate()

    assert result["status"] == "passed-build-only"
    assert result["paid_execution_authorized"] is False
    assert result["development_case_count"] == 500
    assert result["screening_case_count"] == 200
    assert result["candidate_models"] == [
        "gpt-5.4-mini-2026-03-17",
        "gpt-5.6-luna",
        "gpt-5.6-terra",
        "gpt-5.6-sol",
    ]
    assert result["provider_calls"] == 0


def test_cascade_simulation_is_finite_and_never_authorizes_final_set():
    passed = cascade.simulate(scenario="pass")
    failed = cascade.simulate(scenario="no-model-passes")

    assert passed["full_model_count"] == 2
    assert passed["control_case_count"] == 100
    assert passed["sealed_final_execution_authorized"] is False
    assert failed["full_model_count"] == 0
    assert failed["fallback"] == "deterministic-grounded-generator"
    assert failed["provider_calls"] == 0


def test_empty_index_directories_are_not_reported_as_materialized(tmp_path):
    for name in ("active", "artifacts", "bindings"):
        (tmp_path / name).mkdir()

    assert cascade._retrieval_index_materialized(tmp_path) is False  # noqa: SLF001

    for index in range(4):
        (tmp_path / "bindings" / f"course-{index}.json").write_text("{}")
        artifact = tmp_path / "artifacts" / f"artifact-{index}"
        artifact.mkdir()
        (artifact / "manifest.json").write_text("{}")

    assert cascade._retrieval_index_materialized(tmp_path) is True  # noqa: SLF001


def test_screening_selection_matches_every_frozen_slice_quota():
    selected = cascade._screening_cases(cascade._development_cases())  # noqa: SLF001
    targets = cascade._load(cascade.INSTRUMENT_PATH)["screening"][  # noqa: SLF001
        "slice_targets"
    ]

    assert {
        name: sum(row.slice == name for row in selected) for name in targets
    } == targets


def test_candidate_and_control_manifests_bind_different_explicit_gates():
    candidate = cascade._candidate_manifests()[0]  # noqa: SLF001
    structured = cascade._manifest(candidate, stage="screening", control=False)  # noqa: SLF001
    control = cascade._manifest(candidate, stage="control", control=True)  # noqa: SLF001

    assert structured.evidence_gate == "structured-lexical-coverage-evidence-gate-v1"
    assert "candidate" in structured.flow_id
    assert control.evidence_gate == "any-hit-evidence-gate-v1"
    assert "control" in control.flow_id


def _passing_result(
    candidate_id: str,
    *,
    grounded_success: float,
    lower: float,
    upper: float,
    latency: float,
    cost: float,
):
    metrics = {
        "fully_grounded_factual_success": grounded_success,
        "action_accuracy_answerable": 1.0,
        "boundary_action_accuracy": 1.0,
        "atomic_claim_precision": 1.0,
        "atomic_claim_recall": 1.0,
        "citation_precision": 1.0,
        "citation_recall": 1.0,
        "source_version_validity": 1.0,
    }
    return {
        "candidate": {"candidate_id": candidate_id},
        "summary": {
            "metrics": metrics,
            "fully_grounded_source_family_interval": {
                "lower_95": lower,
                "upper_95": upper,
            },
            "severe_unsupported_release_count": 0,
            "latency_ms_p95": latency,
            "cost_usd": cost,
        },
    }


def test_practical_equivalence_prefers_latency_then_cost():
    highest = _passing_result(
        "highest",
        grounded_success=0.98,
        lower=0.95,
        upper=1.0,
        latency=900,
        cost=1.0,
    )
    faster = _passing_result(
        "faster",
        grounded_success=0.965,
        lower=0.94,
        upper=0.99,
        latency=300,
        cost=2.0,
    )
    too_far_below = _passing_result(
        "too-far-below",
        grounded_success=0.95,
        lower=0.90,
        upper=0.94,
        latency=10,
        cost=0.01,
    )

    selected = cascade._select_passing(  # noqa: SLF001
        [highest, faster, too_far_below]
    )

    assert selected["candidate"]["candidate_id"] == "faster"
