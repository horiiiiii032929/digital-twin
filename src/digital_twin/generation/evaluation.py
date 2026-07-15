import time
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from src.digital_twin.generation.models import PolicyAction
from src.digital_twin.grounding import GenerationUsage, Retriever, TutorGenerator
from src.digital_twin.tutor_policy import TutorPolicy


class GenerationCaseCategory(StrEnum):
    DIRECT = "direct"
    MISCONCEPTION = "misconception"
    INTEGRITY_BOUNDARY = "integrity-boundary"
    AMBIGUOUS = "ambiguous"
    NO_EVIDENCE = "no-evidence"


class GenerationEvaluationCase(BaseModel):
    id: str = Field(min_length=1)
    category: GenerationCaseCategory
    question: str = Field(min_length=1)
    expected_action: PolicyAction
    requires_citation: bool
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def citation_expectation_matches_action(self) -> "GenerationEvaluationCase":
        if self.requires_citation != (self.expected_action == PolicyAction.ANSWER):
            raise ValueError("only answer cases require citations")
        if (
            self.category == GenerationCaseCategory.NO_EVIDENCE
            and self.expected_action != PolicyAction.NO_EVIDENCE
        ):
            raise ValueError("no-evidence cases require the no-evidence action")
        return self


class GenerationEvaluationSet(BaseModel):
    version: str = Field(min_length=1)
    corpus_version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    cases: list[GenerationEvaluationCase] = Field(min_length=20)

    @model_validator(mode="after")
    def case_identifiers_must_be_unique(self) -> "GenerationEvaluationSet":
        identifiers = [case.id for case in self.cases]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("generation case identifiers must be unique")
        return self


class GenerationCaseResult(BaseModel):
    case_id: str
    category: GenerationCaseCategory
    expected_action: PolicyAction
    actual_action: str
    answer_content: str
    provider_model: str
    policy_action_correct: bool
    citation_valid: bool
    provider_suppressed_when_required: bool
    latency_ms: float = Field(ge=0)
    usage: GenerationUsage
    warnings: list[str]


class GenerationEvaluationSummary(BaseModel):
    generator: str
    dataset_version: str
    corpus_version: str
    case_count: int = Field(ge=0)
    policy_action_accuracy: float = Field(ge=0, le=1)
    citation_validity: float = Field(ge=0, le=1)
    graded_work_redirect_accuracy: float = Field(ge=0, le=1)
    no_evidence_accuracy: float = Field(ge=0, le=1)
    provider_suppression_accuracy: float = Field(ge=0, le=1)
    mean_latency_ms: float = Field(ge=0)
    total_input_tokens: int = Field(ge=0)
    total_output_tokens: int = Field(ge=0)
    approximate_cost_usd: float | None = Field(default=None, ge=0)
    failures_by_category: dict[str, int]
    cases: list[GenerationCaseResult]


def load_generation_evaluation_set(path: Path) -> GenerationEvaluationSet:
    return GenerationEvaluationSet.model_validate_json(path.read_text(encoding="utf-8"))


async def evaluate_generator(
    name: str,
    generator: TutorGenerator,
    retriever: Retriever,
    policy: TutorPolicy,
    evaluation_set: GenerationEvaluationSet,
) -> GenerationEvaluationSummary:
    results: list[GenerationCaseResult] = []
    for case in evaluation_set.cases:
        hits = retriever.retrieve(case.question, limit=5)
        started = time.perf_counter()
        answer = await generator.generate(case.question, hits, policy)
        latency_ms = (time.perf_counter() - started) * 1000
        actual_action = (
            answer.trace.policy_action
            if answer.trace is not None
            else _infer_action(answer.citations, hits)
        )
        citations_valid = _citations_match_hits(answer.citations, hits)
        citation_valid = (
            citations_valid and bool(answer.citations)
            if case.requires_citation
            else not answer.citations
        )
        should_suppress = case.expected_action != PolicyAction.ANSWER
        provider_suppressed = (
            not should_suppress
            or answer.trace is not None
            and answer.trace.provider_model == "not-called"
        )
        results.append(
            GenerationCaseResult(
                case_id=case.id,
                category=case.category,
                expected_action=case.expected_action,
                actual_action=actual_action,
                answer_content=answer.content,
                provider_model=(
                    answer.trace.provider_model
                    if answer.trace is not None
                    else "not-recorded"
                ),
                policy_action_correct=actual_action == case.expected_action.value,
                citation_valid=citation_valid,
                provider_suppressed_when_required=provider_suppressed,
                latency_ms=latency_ms,
                usage=(
                    answer.trace.usage
                    if answer.trace is not None
                    else GenerationUsage()
                ),
                warnings=answer.warnings,
            )
        )

    graded = [
        result
        for result in results
        if result.expected_action == PolicyAction.REDIRECT_GRADED_WORK
    ]
    no_evidence = [
        result
        for result in results
        if result.expected_action == PolicyAction.NO_EVIDENCE
    ]
    suppression_required = [
        result for result in results if result.expected_action != PolicyAction.ANSWER
    ]
    failures: dict[str, int] = {}
    for result in results:
        if not (
            result.policy_action_correct
            and result.citation_valid
            and result.provider_suppressed_when_required
        ):
            key = result.category.value
            failures[key] = failures.get(key, 0) + 1
    costs = [
        result.usage.approximate_cost_usd
        for result in results
        if result.usage.approximate_cost_usd is not None
    ]
    return GenerationEvaluationSummary(
        generator=name,
        dataset_version=evaluation_set.version,
        corpus_version=evaluation_set.corpus_version,
        case_count=len(results),
        policy_action_accuracy=_mean(
            [result.policy_action_correct for result in results]
        ),
        citation_validity=_mean([result.citation_valid for result in results]),
        graded_work_redirect_accuracy=_mean(
            [result.policy_action_correct for result in graded]
        ),
        no_evidence_accuracy=_mean(
            [result.policy_action_correct for result in no_evidence]
        ),
        provider_suppression_accuracy=_mean(
            [
                result.provider_suppressed_when_required
                for result in suppression_required
            ]
        ),
        mean_latency_ms=(
            sum(result.latency_ms for result in results) / len(results)
            if results
            else 0
        ),
        total_input_tokens=sum(result.usage.input_tokens for result in results),
        total_output_tokens=sum(result.usage.output_tokens for result in results),
        approximate_cost_usd=sum(costs) if costs else None,
        failures_by_category=failures,
        cases=results,
    )


def _infer_action(citations, hits) -> str:
    if not hits and not citations:
        return PolicyAction.NO_EVIDENCE.value
    return PolicyAction.ANSWER.value


def _citations_match_hits(citations, hits) -> bool:
    relationships = {
        (hit.chunk.document_id, hit.chunk.locator or f"chunk {hit.chunk.ordinal + 1}")
        for hit in hits
    }
    return all(
        (citation.source_id, citation.locator) in relationships
        for citation in citations
    )


def _mean(values: list[bool]) -> float:
    return sum(values) / len(values) if values else 1.0
