from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.validate_component_profile import validate_profile_evidence
from src.digital_twin.evaluation import (
    ComponentEvaluationRecord,
    ComponentKind,
    ComponentStatus,
    DecisionOutcome,
    EvaluationDecision,
    ImplementationRef,
    SystemReleaseProfile,
    load_evaluation_record,
    load_release_profile,
)
from src.digital_twin.grounding import (
    BM25Retriever,
    DocumentChunk,
    TermOverlapRetriever,
    UnsupportedRetrieverSelectionError,
    build_selected_retriever,
)


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = (
    ROOT / "research" / "05_evaluation" / "profiles" / "student-tutor-v0.json"
)
RETRIEVAL_RECORD_PATH = (
    ROOT / "research" / "05_evaluation" / "records" / "retrieval-v1.json"
)


def test_experimental_profile_covers_every_component_and_validates_evidence():
    profile = load_release_profile(PROFILE_PATH)

    summary = validate_profile_evidence(profile, root=ROOT)

    assert {entry.component for entry in profile.components} == set(ComponentKind)
    assert summary["status"] == "passed"
    assert summary["component_status_counts"] == {
        "selected": 5,
        "pending": 9,
        "disabled": 0,
    }
    assert summary["evaluated_components"] == ["retriever"]
    assert summary["selections"]["retriever"] == "bm25@v1"
    generator = next(
        entry
        for entry in profile.components
        if entry.component == ComponentKind.GENERATOR
    )
    assert generator.status == ComponentStatus.PENDING
    assert generator.implementation is None


def test_profile_rejects_an_incomplete_component_inventory():
    profile = load_release_profile(PROFILE_PATH)
    payload = profile.model_dump(mode="json")
    payload["components"] = payload["components"][:-1]

    with pytest.raises(ValidationError, match="missing components"):
        SystemReleaseProfile.model_validate(payload)


def test_evaluation_record_prevents_selecting_a_failed_hard_gate():
    record = load_evaluation_record(RETRIEVAL_RECORD_PATH)
    payload = record.model_dump(mode="json")
    selected = next(
        candidate
        for candidate in payload["candidates"]
        if candidate["implementation"]["implementation_id"] == "bm25"
    )
    selected["hard_gates"][0]["passed"] = False

    with pytest.raises(ValidationError, match="failed a hard gate"):
        ComponentEvaluationRecord.model_validate(payload)


def test_refine_decision_can_record_an_inconclusive_comparison():
    decision = EvaluationDecision(
        outcome=DecisionOutcome.REFINE,
        rationale="No candidate passed both quality metrics and hard gates.",
        limitations=["The benchmark needs a new held-out set."],
    )

    assert decision.selected_implementation_id is None


def test_metric_pass_state_cannot_disagree_with_threshold():
    record = load_evaluation_record(RETRIEVAL_RECORD_PATH)
    payload = record.model_dump(mode="json")
    selected = next(
        candidate
        for candidate in payload["candidates"]
        if candidate["implementation"]["implementation_id"] == "bm25"
    )
    selected["metrics"][0]["value"] = 0.1

    with pytest.raises(ValidationError, match="pass state"):
        ComponentEvaluationRecord.model_validate(payload)


def test_candidates_must_use_the_same_metric_and_gate_sets():
    record = load_evaluation_record(RETRIEVAL_RECORD_PATH)
    payload = record.model_dump(mode="json")
    payload["candidates"][1]["metrics"] = payload["candidates"][1]["metrics"][:-1]

    with pytest.raises(ValidationError, match="same metric set"):
        ComponentEvaluationRecord.model_validate(payload)


def test_profile_hard_gates_must_match_evaluation_record():
    profile = load_release_profile(PROFILE_PATH)
    payload = profile.model_dump(mode="json")
    retrieval = next(
        entry
        for entry in payload["components"]
        if entry["component"] == ComponentKind.RETRIEVER
    )
    retrieval["hard_gates"] = [*retrieval["hard_gates"], "undeclared-gate"]
    changed_profile = SystemReleaseProfile.model_validate(payload)

    with pytest.raises(ValueError, match="hard gates do not match"):
        validate_profile_evidence(changed_profile, root=ROOT)


def test_component_specific_factory_swaps_retriever_from_profile():
    profile = load_release_profile(PROFILE_PATH)
    selection = next(
        entry
        for entry in profile.components
        if entry.component == ComponentKind.RETRIEVER
    )
    chunks = [
        DocumentChunk(
            id="chunk-1",
            document_id="document-1",
            text="Synthetic cache evidence.",
            ordinal=0,
            retrieval_allowed=True,
        )
    ]

    selected = build_selected_retriever(selection, chunks)
    swapped = build_selected_retriever(
        selection.model_copy(
            update={
                "implementation": selection.control,
                "control": selection.implementation,
            }
        ),
        chunks,
    )

    assert isinstance(selected, BM25Retriever)
    assert isinstance(swapped, TermOverlapRetriever)


def test_component_specific_factory_rejects_an_unregistered_selection():
    profile = load_release_profile(PROFILE_PATH)
    selection = next(
        entry
        for entry in profile.components
        if entry.component == ComponentKind.RETRIEVER
    )
    unsupported = selection.model_copy(
        update={
            "implementation": ImplementationRef(
                implementation_id="embedding-retriever",
                version="v1",
            )
        }
    )

    with pytest.raises(UnsupportedRetrieverSelectionError, match="unsupported"):
        build_selected_retriever(unsupported, [])
