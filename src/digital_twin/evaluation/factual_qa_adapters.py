"""Runtime adapters for the flow-independent factual-QA contract.

Kept separate from the pure schemas so retrieval and grounding modules can
import evaluation types without importing the student service package.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationAction,
    EvaluationAtomicClaimV1,
    EvaluationCaseV1,
    EvaluationCitationV1,
    EvaluationResponseV1,
    EvaluationUsageV1,
)
from src.digital_twin.student.models import Citation, TutorTurn


_TurnExecutor = Callable[[EvaluationCaseV1], Awaitable[TutorTurn]]
_CitationResolver = Callable[[Citation], EvaluationCitationV1]
_ClaimResolver = Callable[
    [EvaluationCaseV1, TutorTurn], list[EvaluationAtomicClaimV1]
]
_RetrievalResolver = Callable[
    [EvaluationCaseV1, TutorTurn], list[EvaluationCitationV1]
]


def normalize_product_action(action: str, answer: str) -> EvaluationAction:
    normalized = action.strip().casefold()
    if normalized == "answer":
        return (
            EvaluationAction.CLARIFY
            if answer.strip().casefold().startswith(("which ", "please clarify"))
            else EvaluationAction.ANSWER
        )
    if normalized in {"no-evidence", "safe-claim-validation-failure", "safe-failure"}:
        return EvaluationAction.ABSTAIN
    if normalized in {"redirect-graded-work", "refuse"}:
        return EvaluationAction.REFUSE
    if normalized == "clarify":
        return EvaluationAction.CLARIFY
    return EvaluationAction.OPERATIONAL_FAILURE


class StudentTutoringServiceAdapterV1:
    """Normalize an injected StudentTutoringService execution boundary."""

    adapter_version = "v1"

    def __init__(
        self,
        *,
        flow_id: str,
        execute_turn: _TurnExecutor,
        resolve_citation: _CitationResolver | None = None,
        resolve_claims: _ClaimResolver | None = None,
        resolve_retrieved: _RetrievalResolver | None = None,
    ) -> None:
        self.flow_id = flow_id
        self._execute_turn = execute_turn
        self._resolve_citation = resolve_citation or self._default_citation
        self._resolve_claims = resolve_claims or (lambda _case, _turn: [])
        self._resolve_retrieved = resolve_retrieved or (lambda _case, _turn: [])

    @staticmethod
    def _default_citation(row: Citation) -> EvaluationCitationV1:
        return EvaluationCitationV1(
            source_artifact_id=row.source_artifact_id,
            source_version=row.source_version,
            source_sha256=row.source_checksum,
            region_id=row.region_id,
        )

    async def evaluate(self, case: EvaluationCaseV1) -> EvaluationResponseV1:
        turn = await self._execute_turn(case)
        message = turn.tutor_message
        usage = message.trace.usage if message.trace is not None else None
        citations = [self._resolve_citation(row) for row in turn.citations]
        return EvaluationResponseV1(
            case_id=case.case_id,
            flow_id=self.flow_id,
            action=normalize_product_action(message.action, message.content),
            answer=message.content,
            atomic_claims=self._resolve_claims(case, turn),
            citations=citations,
            retrieved_evidence=self._resolve_retrieved(case, turn),
            operational_status="completed",
            provider_model=message.trace.provider_model if message.trace else None,
            provider_revision=message.trace.provider_revision if message.trace else None,
            usage=EvaluationUsageV1(
                input_tokens=usage.input_tokens if usage else 0,
                output_tokens=usage.output_tokens if usage else 0,
                cost_usd=(usage.approximate_cost_usd or 0.0) if usage else 0.0,
                latency_ms=message.trace.latency_ms if message.trace else 0.0,
            ),
            trace={
                "tutoring_mode": turn.tutoring_mode,
                "tutoring_intent": turn.tutoring_intent,
                "learner_state_revision": turn.learner_state_revision,
                "duplicate": turn.duplicate,
            },
        )


class AutonomousGraphEvaluationAdapterV1(StudentTutoringServiceAdapterV1):
    """The graph adapter uses the same external turn contract as T0."""


class AnyHitControlEvaluationAdapterV1(StudentTutoringServiceAdapterV1):
    """Marker adapter for a separately configured any-hit control service."""


class HttpTutorEvaluationAdapterV1:
    """Adapter for a deployed endpoint without coupling to its UI flow."""

    adapter_version = "v1"

    def __init__(
        self,
        *,
        flow_id: str,
        request: Callable[[dict[str, str]], Awaitable[dict[str, Any]]],
    ) -> None:
        self.flow_id = flow_id
        self._request = request

    async def evaluate(self, case: EvaluationCaseV1) -> EvaluationResponseV1:
        payload = await self._request(
            {"course_id": case.course_id, "question": case.question}
        )
        payload = {**payload, "case_id": case.case_id, "flow_id": self.flow_id}
        return EvaluationResponseV1.model_validate(payload)
