from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from scripts import run_academic_factual_qa_open_reference_validation as runner
from scripts.build_academic_factual_qa_open_reference_validation import (
    CANDIDATE_ALLOCATION,
    TARGET_ALLOCATION,
    author_requests,
    build_reference_pool,
)
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_reference_questions import (
    ReferenceQuestionAuthorResponseV1,
    ReferenceQuestionCandidateAuthorResponseV1,
    ReferenceQuestionCandidateReviewResponseV1,
    ReferenceQuestionReviewerResponseV1,
    score_multi_candidate_reference_questions,
    score_reference_questions,
)


@pytest.fixture(scope="module")
def pool() -> dict[str, object]:
    return build_reference_pool()


def _score(
    pool: dict[str, object],
    authors: list[ReferenceQuestionAuthorResponseV1],
    reviewers: list[ReferenceQuestionReviewerResponseV1],
) -> dict[str, object]:
    return score_reference_questions(
        base_cases=[EvaluationCaseV1.model_validate(row) for row in pool["base_cases"]],
        gold=[EvaluationGoldV1.model_validate(row) for row in pool["gold"]],
        cluster_modalities={
            row["cluster_id"]: row["source_modality"] for row in pool["clusters"]
        },
        authors=authors,
        reviewers=reviewers,
        target_allocation=TARGET_ALLOCATION,
    )


def test_reference_pool_is_fresh_balanced_and_byte_stable(
    pool: dict[str, object],
) -> None:
    second = build_reference_pool()

    assert pool["content_sha256"] == second["content_sha256"]
    assert pool["candidate_cluster_count"] == 160
    assert pool["candidate_case_count"] == 800
    assert pool["target_cluster_count"] == 100
    assert pool["target_case_count"] == 500
    assert pool["candidate_allocation"] == CANDIDATE_ALLOCATION
    assert pool["target_allocation"] == TARGET_ALLOCATION
    assert pool["source_disjoint_from_checkpoint_007"] is True
    assert pool["provider_calls"] == 0
    assert pool["private_data_read"] is False
    assert pool["final_split_opened"] is False


def test_author_sees_truth_but_blind_reviewer_contract_does_not(
    pool: dict[str, object],
) -> None:
    requests = author_requests(pool)
    answerable = next(row for row in requests if row["expected_action"] == "answer")
    boundary = next(row for row in requests if row["expected_action"] != "answer")

    assert answerable["canonical_answer"]
    assert answerable["required_answer_spans"]
    assert boundary["canonical_answer"] is None
    assert boundary["required_answer_spans"] == []
    assert runner.validate()["status"] == "passed-build-only"


def test_network_free_simulation_selects_exact_complete_quota() -> None:
    result = runner.simulate()

    assert result["status"] == "simulated-network-free"
    assert result["decision"] == "completed-go-deeper"
    assert result["passed_case_count"] == 800
    assert result["selected_cluster_count"] == 100
    assert result["selected_case_count"] == 500
    assert result["allocation_shortfalls"] == {}
    assert result["provider_calls"] == 0
    assert result["product_calls"] == 0
    assert result["network_accessed"] is False


def test_blind_ambiguity_rejection_cannot_relax_modality_quota(
    pool: dict[str, object],
) -> None:
    _, authors, reviewers = runner._simulated_votes()  # noqa: SLF001
    os_table_clusters = {
        row["cluster_id"]
        for row in pool["clusters"]
        if row["course_id"] == "operating-systems"
        and row["source_modality"] == "structured-table"
    }
    assert len(os_table_clusters) == 3
    mutated = [
        row.model_copy(
            update={"unambiguous": False, "rationale": "Injected ambiguity."}
        )
        if row.case_id.rsplit("-q", 1)[0] in os_table_clusters
        and row.case_id.endswith("-q1")
        else row
        for row in reviewers
    ]

    result = _score(pool, authors, mutated)

    assert result["status"] == "completed-refine"
    assert result["allocation_shortfalls"] == {"operating-systems:structured-table": 1}
    assert result["selected_cluster_count"] == 99
    assert all(
        not row["passed"]
        for row in result["decisions"]
        if row["case_id"].rsplit("-q", 1)[0] in os_table_clusters
        and row["case_id"].endswith("-q1")
    )


def test_duplicate_questions_are_rejected_before_selection(
    pool: dict[str, object],
) -> None:
    _, authors, reviewers = runner._simulated_votes()  # noqa: SLF001
    mutated = deepcopy(authors)
    duplicate = "What exact source claim answers this independently reviewed question?"
    mutated[0] = mutated[0].model_copy(update={"question": duplicate})
    mutated[1] = mutated[1].model_copy(update={"question": duplicate})

    result = _score(pool, mutated, reviewers)

    assert result["normalized_duplicate_count"] == 1
    failed = {
        row["case_id"]
        for row in result["decisions"]
        if "exact-duplicate" in row["reasons"]
    }
    assert failed == {mutated[0].case_id, mutated[1].case_id}


def test_preflight_is_blocked_after_authority_revocation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(runner, "_repo_dirty", lambda: False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-redacted")
    attempt = replace(
        runner.ATTEMPT_001,
        ledger_path=tmp_path / "unused.sqlite3",
        result_path=tmp_path / "unused.json",
    )
    result = runner.preflight(attempt=attempt)

    assert result["status"] == "blocked-not-authorized"
    assert (
        "freeze-external_model_evaluation-authorization-missing" in result["blockers"]
    )
    assert "instrument-provider-execution-authorized-false" in result["blockers"]
    assert "binding-provider-execution-authorized-false" in result["blockers"]
    assert result["provider_calls"] == 0
    assert result["product_calls"] == 0
    assert result["final_split_opened"] is False


def test_attempt_002_aligns_provider_schema_with_local_question_invariant() -> None:
    result = runner.validate(attempt=runner.ATTEMPT_002)
    question_schema = runner._author_schema(20, attempt=runner.ATTEMPT_002)[  # noqa: SLF001
        "properties"
    ]["items"]["items"]["properties"]["question"]

    assert result["status"] == "passed-build-only"
    assert result["author_question_pattern"] == r"\?$"
    assert question_schema["pattern"] == r"\?$"
    assert (
        "pattern"
        not in runner._author_schema(20)["properties"]["items"][  # noqa: SLF001
            "items"
        ]["properties"]["question"]
    )
    ReferenceQuestionAuthorResponseV1(
        case_id="aligned-case",
        question="Which exact claim does the source establish?",
    )
    with pytest.raises(ValueError, match="question mark"):
        ReferenceQuestionAuthorResponseV1(
            case_id="misaligned-case",
            question="The source establishes the exact requested claim",
        )


def test_attempt_002_has_fresh_outputs_and_revoked_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(runner, "_repo_dirty", lambda: False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-redacted")
    attempt = replace(
        runner.ATTEMPT_002,
        ledger_path=tmp_path / "attempt-002.sqlite3",
        result_path=tmp_path / "attempt-002-result.json",
    )

    simulation = runner.simulate(attempt=attempt)
    preflight = runner.preflight(attempt=attempt)

    assert attempt.ledger_path != runner.ATTEMPT_001.ledger_path
    assert attempt.result_path != runner.ATTEMPT_001.result_path
    assert simulation["selected_cluster_count"] == 100
    assert simulation["selected_case_count"] == 500
    assert preflight["status"] == "blocked-not-authorized"
    assert (
        "freeze-external_model_evaluation-authorization-missing"
        in preflight["blockers"]
    )
    assert "instrument-provider-execution-authorized-false" in preflight["blockers"]
    assert "binding-provider-execution-authorized-false" in preflight["blockers"]
    assert preflight["provider_calls"] == 0
    assert preflight["product_calls"] == 0
    assert preflight["final_split_opened"] is False


def test_attempt_003_matches_unique_response_ids_without_array_order() -> None:
    expected_ids = ["case-a", "case-b"]
    authors = runner._parse_authors(  # noqa: SLF001
        {
            "items": [
                {"case_id": "case-b", "question": "What does source B establish?"},
                {"case_id": "case-a", "question": "What does source A establish?"},
            ]
        },
        expected_ids,
    )
    reviews = runner._parse_reviews(  # noqa: SLF001
        {
            "items": [
                {
                    "case_id": "case-b",
                    "predicted_action": "abstain",
                    "recovered_answer_spans": [],
                    "unambiguous": True,
                    "natural_student_question": True,
                    "gold_hint_leak": False,
                    "rationale": "Source B has no answer.",
                },
                {
                    "case_id": "case-a",
                    "predicted_action": "answer",
                    "recovered_answer_spans": ["Source A answer."],
                    "unambiguous": True,
                    "natural_student_question": True,
                    "gold_hint_leak": False,
                    "rationale": "Source A uniquely supports the answer.",
                },
            ]
        },
        expected_ids,
    )

    assert [row.case_id for row in authors] == expected_ids
    assert [row.case_id for row in reviews] == expected_ids


def test_attempt_003_rejects_duplicate_or_unknown_response_ids() -> None:
    with pytest.raises(runner.ReferenceQuestionCheckpointError, match="duplicated"):
        runner._parse_authors(  # noqa: SLF001
            {
                "items": [
                    {"case_id": "case-a", "question": "What does source A establish?"},
                    {
                        "case_id": "case-a",
                        "question": "What else does source A establish?",
                    },
                ]
            },
            ["case-a", "case-b"],
        )


def test_attempt_004_uses_three_candidates_and_deterministic_boundaries() -> None:
    result = runner.validate(
        require_unauthorized=False,
        attempt=runner.ATTEMPT_004,
    )
    simulation = runner.simulate(attempt=runner.ATTEMPT_004)
    author_schema = runner._candidate_author_schema(16)  # noqa: SLF001

    assert result["multi_candidate_answerable"] is True
    assert (
        author_schema["properties"]["items"]["items"]["properties"]["questions"][
            "minItems"
        ]
        == 3
    )
    assert simulation["decision"] == "completed-go-deeper"
    assert simulation["selected_cluster_count"] == 100
    assert simulation["selected_case_count"] == 500


def test_attempt_004_can_select_a_later_blind_validated_candidate() -> None:
    pool, cases, gold, authors, reviewers = runner._simulated_multi_candidate_votes()  # noqa: SLF001
    first_case_id = authors[0].case_id
    mutated = [
        ReferenceQuestionCandidateReviewResponseV1(
            **{
                **row.model_dump(),
                "predicted_action": "abstain",
                "recovered_answer_spans": [],
                "rationale": "Injected first-candidate failure.",
            }
        )
        if row.candidate_id == f"{first_case_id}-candidate-1"
        else row
        for row in reviewers
    ]
    result = score_multi_candidate_reference_questions(
        canonical_cases=cases,
        gold=gold,
        cluster_modalities={
            row["cluster_id"]: row["source_modality"] for row in pool["clusters"]
        },
        authors=authors,
        reviewers=mutated,
        target_allocation=TARGET_ALLOCATION,
    )

    assert result["status"] == "completed-go-deeper"
    selected = {row["case_id"]: row for row in result["selected_cases"]}
    assert selected[first_case_id]["question"].endswith("form 2?")
    with pytest.raises(runner.ReferenceQuestionCheckpointError, match="set drifted"):
        runner._parse_authors(  # noqa: SLF001
            {
                "items": [
                    {"case_id": "case-a", "question": "What does source A establish?"},
                    {"case_id": "case-c", "question": "What does source C establish?"},
                ]
            },
            ["case-a", "case-b"],
        )


def test_duplicate_candidates_are_recorded_as_quality_failures() -> None:
    pool, cases, gold, authors, reviewers = runner._simulated_multi_candidate_votes()  # noqa: SLF001
    first = authors[0]
    duplicate = ReferenceQuestionCandidateAuthorResponseV1(
        case_id=first.case_id,
        questions=[first.questions[0], first.questions[0], first.questions[2]],
    )
    result = score_multi_candidate_reference_questions(
        canonical_cases=cases,
        gold=gold,
        cluster_modalities={
            row["cluster_id"]: row["source_modality"] for row in pool["clusters"]
        },
        authors=[duplicate, *authors[1:]],
        reviewers=reviewers,
        target_allocation=TARGET_ALLOCATION,
    )

    duplicated = {
        row["candidate_id"]: row
        for row in result["decisions"]
        if row["case_id"] == first.case_id
    }
    assert (
        "duplicate-candidate" in duplicated[f"{first.case_id}-candidate-1"]["reasons"]
    )
    assert (
        "duplicate-candidate" in duplicated[f"{first.case_id}-candidate-2"]["reasons"]
    )
    assert result["status"] == "completed-go-deeper"
