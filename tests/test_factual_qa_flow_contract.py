from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.digital_twin.evaluation import (
    CanonicalEvidenceRefV1,
    EvaluationAction,
    EvaluationAtomicClaimV1,
    EvaluationCaseV1,
    EvaluationCitationV1,
    EvaluationClaimV1,
    EvaluationGoldV1,
    EvaluationResponseV1,
    EvaluationSplit,
    evidence_ranges_overlap,
    score_case,
    source_family_bootstrap_interval,
)
from src.digital_twin.evaluation.factual_qa_adapters import (
    HttpTutorEvaluationAdapterV1,
    StudentTutoringServiceAdapterV1,
)
from src.digital_twin.student.models import Citation, Message, TutorTurn


SOURCE_HASH = "a" * 64


def _case(*, case_id: str = "case-001", family: str = "family-001") -> EvaluationCaseV1:
    return EvaluationCaseV1(
        case_id=case_id,
        cluster_id="cluster-001",
        source_family_id=family,
        course_id="course-001",
        question="What is a process?",
        split=EvaluationSplit.DEVELOPMENT,
        slice="direct-factual",
        author_family="deterministic-control",
    )


def _reference() -> CanonicalEvidenceRefV1:
    return CanonicalEvidenceRefV1(
        source_artifact_id="source-001",
        source_version=1,
        source_sha256=SOURCE_HASH,
        char_start=20,
        char_end=60,
    )


def _gold() -> EvaluationGoldV1:
    return EvaluationGoldV1(
        case_id="case-001",
        expected_action=EvaluationAction.ANSWER,
        canonical_answer="a process is a program in execution",
        claims=[
            EvaluationClaimV1(
                claim_id="claim-001",
                answer_span="a program in execution",
                evidence_refs=[_reference()],
            )
        ],
    )


def _response(*, citation: EvaluationCitationV1 | None = None) -> EvaluationResponseV1:
    return EvaluationResponseV1(
        case_id="case-001",
        flow_id="t0-candidate",
        action=EvaluationAction.ANSWER,
        answer="A process is a program in execution.",
        atomic_claims=[
            EvaluationAtomicClaimV1(
                text="A process is a program in execution.",
                citations=[citation] if citation else [],
            )
        ],
        citations=[citation] if citation else [],
        operational_status="completed",
    )


def test_case_contract_rejects_gold_fields() -> None:
    payload = _case().model_dump(mode="json")
    payload["expected_action"] = "answer"
    with pytest.raises(ValidationError):
        EvaluationCaseV1.model_validate(payload)


def test_text_evidence_requires_canonical_range_overlap() -> None:
    unresolved = EvaluationCitationV1(
        source_artifact_id="source-001",
        source_version=1,
        source_sha256=SOURCE_HASH,
    )
    overlapping = unresolved.model_copy(update={"char_start": 35, "char_end": 70})
    different_chunk_same_source = unresolved.model_copy(
        update={"char_start": 80, "char_end": 100}
    )

    assert evidence_ranges_overlap(_reference(), unresolved) is False
    assert evidence_ranges_overlap(_reference(), overlapping) is True
    assert evidence_ranges_overlap(_reference(), different_chunk_same_source) is False


def test_flow_independent_score_accepts_range_mapped_citation() -> None:
    citation = EvaluationCitationV1(
        source_artifact_id="source-001",
        source_version=1,
        source_sha256=SOURCE_HASH,
        char_start=25,
        char_end=55,
    )
    score = score_case(_case(), _gold(), _response(citation=citation))

    assert score.fully_grounded_success is True
    assert score.citation_precision == 1
    assert score.citation_recall == 1


def test_same_source_wrong_range_does_not_pass_citation_gate() -> None:
    citation = EvaluationCitationV1(
        source_artifact_id="source-001",
        source_version=1,
        source_sha256=SOURCE_HASH,
        char_start=100,
        char_end=120,
    )
    score = score_case(_case(), _gold(), _response(citation=citation))

    assert score.fully_grounded_success is False
    assert score.citation_recall == 0


@pytest.mark.asyncio
async def test_t0_adapter_uses_injected_lineage_and_claim_mapping() -> None:
    student_message = Message(
        id="student-001",
        conversation_id="conversation-001",
        role="student",
        content="What is a process?",
        action="ask",
    )
    tutor_message = Message(
        id="tutor-001",
        conversation_id="conversation-001",
        role="tutor",
        content="A process is a program in execution.",
        action="answer",
    )
    citation = Citation(
        id="citation-001",
        message_id="tutor-001",
        course_id="course-001",
        release_id="release-001",
        source_artifact_id="source-001",
        source_document_id="document-001",
        source_version=1,
        title="Processes",
        locator="section 1",
        source_checksum=SOURCE_HASH,
    )
    turn = TutorTurn(
        student_message=student_message,
        tutor_message=tutor_message,
        citations=[citation],
    )

    async def execute(_case: EvaluationCaseV1) -> TutorTurn:
        return turn

    adapter = StudentTutoringServiceAdapterV1(
        flow_id="t0-candidate",
        execute_turn=execute,
        resolve_citation=lambda row: EvaluationCitationV1(
            source_artifact_id=row.source_artifact_id,
            source_version=row.source_version,
            source_sha256=row.source_checksum,
            char_start=20,
            char_end=60,
        ),
        resolve_claims=lambda _case, _turn: [
            EvaluationAtomicClaimV1(
                text="A process is a program in execution.",
                citations=[],
            )
        ],
    )
    response = await adapter.evaluate(_case())

    assert response.action == EvaluationAction.ANSWER
    assert response.atomic_claims[0].text.startswith("A process")
    assert response.citations[0].char_start == 20


@pytest.mark.asyncio
async def test_http_adapter_sends_only_course_and_question() -> None:
    observed: dict[str, str] = {}

    async def request(payload: dict[str, str]) -> dict[str, object]:
        observed.update(payload)
        return {
            "action": "abstain",
            "answer": "I do not have enough approved evidence.",
            "atomic_claims": [],
            "citations": [],
            "operational_status": "completed",
        }

    response = await HttpTutorEvaluationAdapterV1(
        flow_id="deployed-v1", request=request
    ).evaluate(_case())

    assert observed == {
        "course_id": "course-001",
        "question": "What is a process?",
    }
    assert response.flow_id == "deployed-v1"


def test_bootstrap_uses_source_families_not_case_rows() -> None:
    citation = EvaluationCitationV1(
        source_artifact_id="source-001",
        source_version=1,
        source_sha256=SOURCE_HASH,
        char_start=20,
        char_end=60,
    )
    first = score_case(_case(family="family-a"), _gold(), _response(citation=citation))
    second = first.model_copy(
        update={
            "case_id": "case-002",
            "source_family_id": "family-b",
            "fully_grounded_success": False,
        }
    )
    interval = source_family_bootstrap_interval(
        [first, second], field="fully_grounded_success", replicates=100, seed=7
    )

    assert interval["source_family_count"] == 2
    assert interval["estimate"] == 0.5
