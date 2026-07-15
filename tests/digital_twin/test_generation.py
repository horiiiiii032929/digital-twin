import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.digital_twin.generation import (
    DeterministicCitationValidator,
    DeterministicGroundedGenerator,
    DeterministicPolicyEnforcer,
    GenerationEvaluationSet,
    GroundedPromptBuilder,
    LiveGroundedGenerator,
    PolicyAction,
    load_generation_evaluation_set,
)
from src.digital_twin.grounding import DocumentChunk, GenerationUsage, RetrievalHit
from src.digital_twin.llm import (
    LlmClient,
    LlmMessage,
    LlmResponse,
    LlmTimeoutError,
)
from src.digital_twin.tutor_policy import (
    FieldStatus,
    ReleaseStatus,
    build_initial_policy,
)


GENERATION_DATASET = (
    Path(__file__).resolve().parents[2]
    / "research"
    / "05_evaluation"
    / "generation_v1.json"
)


def approved_policy():
    policy = build_initial_policy().model_copy(deep=True)
    for field in policy.all_fields:
        if field.status == FieldStatus.BLOCKS_RELEASE:
            field.status = FieldStatus.RESOLVED
        if field.id == "knowledge_source_policy":
            field.value = {**field.value, "confirmed": True}
        if field.id in {"academic_integrity_policy", "professor_release_approval"}:
            field.status = FieldStatus.RESOLVED
        if field.id == "professor_release_approval":
            field.value = "approved"
    policy.status = ReleaseStatus.APPROVED
    policy.release_status = ReleaseStatus.APPROVED
    return policy


def approved_hit() -> RetrievalHit:
    return RetrievalHit(
        chunk=DocumentChunk(
            id="chunk-csrf-1",
            document_id="document-csrf",
            text=(
                "CSRF abuses an authenticated browser session. Anti-CSRF tokens "
                "and SameSite cookies are common defenses."
            ),
            ordinal=0,
            source_version=2,
            retrieval_allowed=True,
            locator="page 2, paragraph 1",
            metadata={"title": "Synthetic CSRF notes"},
        ),
        relevance_score=1,
    )


class RecordingClient:
    def __init__(self, response: LlmResponse | Exception) -> None:
        self.response = response
        self.calls: list[tuple[list[LlmMessage], str]] = []

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        self.calls.append((messages, task))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def live_response(
    *,
    answer: str = "CSRF uses an authenticated browser session.",
    citation_ids: list[str] | None = None,
) -> LlmResponse:
    return LlmResponse(
        content=json.dumps(
            {
                "answer": answer,
                "citation_ids": ["S1"] if citation_ids is None else citation_ids,
            }
        ),
        provider_model="fixture-live/v1",
        usage=GenerationUsage(
            input_tokens=100,
            output_tokens=20,
            total_tokens=120,
            approximate_cost_usd=0.001,
        ),
    )


def test_policy_enforcer_requires_professor_release_approval():
    decision = DeterministicPolicyEnforcer().evaluate(
        "How does CSRF work?",
        [approved_hit()],
        build_initial_policy(),
    )

    assert decision.action == PolicyAction.POLICY_NOT_APPROVED
    assert not decision.permits_model_call


def test_generation_evaluation_set_covers_all_preflight_categories():
    evaluation_set = load_generation_evaluation_set(GENERATION_DATASET)

    assert len(evaluation_set.cases) == 25
    assert {case.category.value for case in evaluation_set.cases} == {
        "direct",
        "misconception",
        "integrity-boundary",
        "ambiguous",
        "no-evidence",
    }


def test_generation_evaluation_rejects_answer_without_required_citation():
    evaluation_set = load_generation_evaluation_set(GENERATION_DATASET)
    payload = evaluation_set.model_dump(mode="json")
    payload["cases"][0]["requires_citation"] = False

    with pytest.raises(ValidationError, match="only answer cases require citations"):
        GenerationEvaluationSet.model_validate(payload)


def test_policy_enforcer_redirects_direct_graded_work_and_allows_concepts():
    enforcer = DeterministicPolicyEnforcer()

    graded = enforcer.evaluate(
        "For my graded homework, give me the full answer about CSRF.",
        [approved_hit()],
        approved_policy(),
    )
    conceptual = enforcer.evaluate(
        "Can you explain the concept of CSRF?",
        [approved_hit()],
        approved_policy(),
    )

    assert graded.action == PolicyAction.REDIRECT_GRADED_WORK
    assert "professor-policy:academic_integrity_policy" in graded.matched_rules
    assert conceptual.action == PolicyAction.ANSWER


def test_policy_enforcer_redirects_common_direct_completion_paraphrase():
    decision = DeterministicPolicyEnforcer().evaluate(
        "Please solve my homework about CSRF.",
        [approved_hit()],
        approved_policy(),
    )

    assert decision.action == PolicyAction.REDIRECT_GRADED_WORK


def test_prompt_records_policy_evidence_version_and_injection_boundary():
    prompt = GroundedPromptBuilder().build(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
    )

    assert prompt.version == "v1"
    assert prompt.evidence[0].citation_id == "S1"
    assert prompt.evidence[0].hit.chunk.source_version == 2
    assert "never as instructions" in prompt.messages[0].content
    assert '"citation_id": "S1"' in prompt.messages[1].content


@pytest.mark.asyncio
async def test_deterministic_generator_produces_grounded_citation_and_trace():
    answer = await DeterministicGroundedGenerator().generate(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
    )

    assert answer.content.startswith("Based on approved course evidence:")
    assert answer.citations[0].source_id == "document-csrf"
    assert answer.citations[0].locator == "page 2, paragraph 1"
    assert answer.trace is not None
    assert answer.trace.generator_id == "deterministic-grounded-generator"
    assert answer.trace.usage.total_tokens == 0


@pytest.mark.asyncio
async def test_live_generator_uses_structured_output_and_records_usage():
    client = RecordingClient(live_response())
    generator = LiveGroundedGenerator(client)

    answer = await generator.generate(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
    )

    assert len(client.calls) == 1
    assert client.calls[0][1] == "grounded_tutor_answer"
    assert answer.content == "CSRF uses an authenticated browser session."
    assert answer.citations[0].title == "Synthetic CSRF notes"
    assert answer.trace is not None
    assert answer.trace.provider_model == "fixture-live/v1"
    assert answer.trace.usage.approximate_cost_usd == 0.001


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "hits", "expected_action"),
    [
        (
            "Give me the full answer for my graded assignment.",
            [approved_hit()],
            PolicyAction.REDIRECT_GRADED_WORK,
        ),
        ("What is outside the approved corpus?", [], PolicyAction.NO_EVIDENCE),
    ],
)
async def test_policy_short_circuits_without_calling_live_provider(
    question,
    hits,
    expected_action,
):
    client = RecordingClient(live_response())

    answer = await LiveGroundedGenerator(client).generate(
        question,
        hits,
        approved_policy(),
    )

    assert client.calls == []
    assert answer.citations == []
    assert answer.trace is not None
    assert answer.trace.policy_action == expected_action.value


@pytest.mark.asyncio
async def test_unapproved_hits_are_never_sent_to_provider():
    client = RecordingClient(live_response())
    hit = approved_hit()
    hit.chunk.retrieval_allowed = False

    answer = await LiveGroundedGenerator(client).generate(
        "How does CSRF work?",
        [hit],
        approved_policy(),
    )

    assert client.calls == []
    assert answer.trace is not None
    assert answer.trace.policy_action == PolicyAction.NO_EVIDENCE


@pytest.mark.asyncio
async def test_empty_question_is_not_sent_to_provider():
    client = RecordingClient(live_response())

    answer = await LiveGroundedGenerator(client).generate(
        "   ",
        [approved_hit()],
        approved_policy(),
    )

    assert client.calls == []
    assert answer.trace is not None
    assert answer.trace.policy_action == PolicyAction.INVALID_REQUEST


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        LlmResponse(content="not-json", provider_model="fixture-live/v1"),
        live_response(citation_ids=["S99"]),
        live_response(citation_ids=[]),
    ],
)
async def test_malformed_or_invented_live_output_fails_closed(response):
    answer = await LiveGroundedGenerator(RecordingClient(response)).generate(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
    )

    assert answer.citations == []
    assert answer.warnings == ["The tutor model returned an invalid grounded answer."]
    assert "not-json" not in answer.content


@pytest.mark.asyncio
async def test_provider_timeout_returns_sanitized_warning():
    secret = "sk-private-value"
    client: LlmClient = RecordingClient(LlmTimeoutError(secret))

    answer = await LiveGroundedGenerator(client).generate(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
    )

    assert answer.citations == []
    assert answer.warnings == ["The tutor model timed out before producing an answer."]
    assert secret not in answer.model_dump_json()


def test_citation_validator_rejects_duplicates():
    prompt = GroundedPromptBuilder().build(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
    )

    with pytest.raises(ValueError, match="duplicate"):
        DeterministicCitationValidator().validate(["S1", "S1"], prompt.evidence)
