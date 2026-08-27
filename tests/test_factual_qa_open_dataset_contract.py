from __future__ import annotations

import pytest

from src.digital_twin.evaluation import (
    ClusterDraftV1,
    DraftEvidenceSpanV1,
    DraftQuestionV1,
    EvaluationAction,
    EvaluationSplit,
    SourceClusterV1,
    assemble_verified_cluster,
)


def _cluster() -> SourceClusterV1:
    return SourceClusterV1(
        cluster_id="cluster-000001",
        source_family_id="family-001",
        course_id="operating-systems",
        source_artifact_id="artifact-001",
        source_version=1,
        source_sha256="a" * 64,
        source_path="content/processes.md",
        section_heading="Processes",
        char_start=100,
        char_end=151,
        text="A process is a program in execution. It has state.",
        source_modality="text",
        split=EvaluationSplit.DEVELOPMENT,
        answerable_slices=[
            "direct-factual",
            "paraphrased",
            "definition-explanation",
            "multi-evidence",
        ],
        boundary_slice="no-evidence",
        author_family="deepseek-v4",
        verifier_family="gemini-3.7",
        license_spdx="CC-BY-4.0",
        repository_url="https://example.test/course",
        repository_commit="b" * 40,
    )


def _draft() -> ClusterDraftV1:
    answer = "A process is a program in execution"
    span = DraftEvidenceSpanV1(
        quote=answer,
        relative_char_start=0,
        relative_char_end=len(answer),
    )
    return ClusterDraftV1(
        cluster_id="cluster-000001",
        questions=[
            DraftQuestionV1(
                case_id=f"cluster-000001-q{index}",
                question=f"Question form {index}: what is a process?",
                action=EvaluationAction.ANSWER,
                answer=answer,
                evidence_spans=[span],
            )
            for index in range(1, 5)
        ]
        + [
            DraftQuestionV1(
                case_id="cluster-000001-q5",
                question="Which scheduling algorithm is mandated here?",
                action=EvaluationAction.ABSTAIN,
                answer="The source does not establish a required algorithm.",
                boundary_reason="no-evidence",
            )
        ],
    )


def test_verified_cluster_emits_separate_public_cases_and_hidden_gold() -> None:
    cases, gold = assemble_verified_cluster(_cluster(), _draft(), _draft())

    assert len(cases) == len(gold) == 5
    assert set(cases[0].model_dump()) == {
        "schema_version",
        "case_id",
        "cluster_id",
        "source_family_id",
        "course_id",
        "question",
        "split",
        "slice",
        "author_family",
    }
    assert gold[0].claims[0].evidence_refs[0].char_start == 100
    assert gold[0].claims[0].evidence_refs[0].char_end == 135
    assert gold[-1].claims == []


def test_author_verifier_disagreement_is_rejected() -> None:
    verifier = _draft().model_copy(deep=True)
    verifier.questions[0].answer = "It has state"

    with pytest.raises(ValueError, match="answer or evidence disagreement"):
        assemble_verified_cluster(_cluster(), _draft(), verifier)


def test_non_exact_source_span_is_rejected() -> None:
    author = _draft().model_copy(deep=True)
    verifier = _draft().model_copy(deep=True)
    for draft in (author, verifier):
        draft.questions[0].evidence_spans[0].quote = "a program"

    with pytest.raises(ValueError, match="not exact"):
        assemble_verified_cluster(_cluster(), author, verifier)
