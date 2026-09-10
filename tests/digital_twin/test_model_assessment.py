"""Contract and actual-turn tests; injected judgments are not semantic evidence."""
import json
import pytest
from src.digital_twin.student.model_assessment import SourceBoundModelAssessor, TASK, AttemptAssessmentProposal
from src.digital_twin.student.autonomy_models import AssessmentOutcome
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmResponse, LlmUnavailableError
from tests.digital_twin.test_source_assessment import scoped, SUPPORTED
from tests.digital_twin.test_goal_completion_scope import setup_two_goals, tutoring_service


def test_provider_registry_uses_the_exact_assessment_contract():
    from services.llm.openai_responses_client import OpenAiResponsesClient
    assert OpenAiResponsesClient._output_type(TASK) is AttemptAssessmentProposal
    assert OpenAiResponsesClient._schema(TASK)


class Client:
    def __init__(self, outcome="correct", mutation=None, error=None):
        self.outcome, self.mutation, self.error, self.calls = outcome, mutation, error, 0
    async def chat(self, messages, task):
        assert task == TASK
        self.calls += 1
        if self.error:
            raise self.error
        payload = json.loads(messages[-1].content)
        assert set(payload) == {"attempt", "target", "evidence"}
        reason = {"correct": "supported-complete", "partial": "supported-incomplete", "incorrect": "contradicted", "not-assessed": "ambiguous-attempt"}[self.outcome]
        value = {"outcome": self.outcome, "confidence": .8, "reason": reason,
            "quotations": [{"source_id": payload["evidence"][0]["source_id"], "text": payload["evidence"][0]["text"]}]}
        response = {"provider_model": "gpt-5.6-luna", "usage": GenerationUsage(approximate_cost_usd=.001), "content": value}
        if self.mutation:
            self.mutation(response)
        response["content"] = json.dumps(response["content"])
        return LlmResponse(**response)


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["correct", "incorrect", "partial", "not-assessed"])
async def test_declared_outcomes_require_exact_source_binding(scoped, outcome):
    client = Client(outcome)
    result = await SourceBoundModelAssessor(client).assess("I think " + SUPPORTED, ["cache-coherence"], *scoped)
    assert result.assessment.outcome.value == outcome
    assert bool(result.assessment.evidence_keys) == (outcome != "not-assessed")
    assert result.usage.approximate_cost_usd == .001
    assert client.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", ["wrong-model", "unknown-cost", "invented-quote", "unknown-source", "inconsistent", "low-confidence"])
async def test_invalid_judgment_does_not_become_learning_evidence(scoped, variant):
    def mutate(response):
        value = response["content"]
        if variant == "wrong-model": response["provider_model"] = "different-model"
        elif variant == "unknown-cost": response["usage"] = GenerationUsage()
        elif variant == "invented-quote": value["quotations"][0]["text"] = "Not in the approved source."
        elif variant == "unknown-source": value["quotations"][0]["source_id"] = "S999"
        elif variant == "inconsistent": value["reason"] = "contradicted"
        else: value["confidence"] = .1
    result = await SourceBoundModelAssessor(Client(mutation=mutate)).assess(SUPPORTED, ["cache-coherence"], *scoped)
    assert result.assessment.outcome == AssessmentOutcome.NOT_ASSESSED
    assert not result.assessment.evidence_keys
    if variant == "unknown-cost": assert result.usage.approximate_cost_usd is None


@pytest.mark.asyncio
async def test_provider_failure_preserves_unknown_cost(scoped):
    client = Client(error=LlmUnavailableError())
    result = await SourceBoundModelAssessor(client).assess(SUPPORTED, ["cache-coherence"], *scoped)
    assert result.assessment.outcome == AssessmentOutcome.NOT_ASSESSED
    assert result.usage.approximate_cost_usd is None
    assert result.provider_called


@pytest.mark.asyncio
async def test_ambiguous_or_wrong_release_does_not_call_provider(scoped):
    client = Client()
    assessor = SourceBoundModelAssessor(client)
    assert not (await assessor.assess(SUPPORTED, ["cache-coherence", "virtual-memory"], *scoped)).provider_called
    domain, release = scoped
    assert not (await assessor.assess(SUPPORTED, ["cache-coherence"], domain, release.model_copy(update={"id": "other"}))).provider_called
    assert client.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", ["permission", "superseded"])
async def test_excluded_source_is_never_sent_to_provider(scoped, variant):
    client = Client()
    domain, release = scoped
    if variant == "permission":
        release.chunks[0].retrieval_allowed = False
    else:
        release.chunks.append(release.chunks[0].model_copy(update={"id": "newer", "source_version": 2}))
    result = await SourceBoundModelAssessor(client).assess(SUPPORTED, ["cache-coherence"], domain, release)
    assert result.assessment.outcome == AssessmentOutcome.NOT_ASSESSED
    assert client.calls == 0


@pytest.mark.asyncio
async def test_actual_turn_persists_model_assessment_with_provenance(tmp_path):
    repo, fixture, goals = setup_two_goals(tmp_path, source_supported_target=True)
    try:
        service = tutoring_service(repo)
        client = Client("incorrect")
        service.tutoring_graph.source_bound_model_assessor = SourceBoundModelAssessor(client)
        c = service.create_conversation(fixture.student_a_id, fixture.course_a_id)
        await service.submit_message(fixture.student_a_id, c.id,
            content="I think cache coherence never keeps replicated processor data consistent.", client_request_id="semantic-attempt")
        rows = repo.list_learner_observations_v2(c.id)
        assert len(rows) == 1
        assert rows[0].assessment_outcome == AssessmentOutcome.INCORRECT
        assert rows[0].assessment_concept_ids == ["cache-coherence"]
        assert rows[0].evidence_keys
        assert client.calls == 1
    finally:
        repo.close()


@pytest.mark.asyncio
async def test_v2_rejects_a_target_not_in_approved_ranges_before_provider(scoped):
    domain, release = scoped
    domain.concepts[0].description = 'Every future operation is guaranteed to succeed.'
    client = Client('incorrect')
    result = await SourceBoundModelAssessor(client,version='v2').assess(
        'I think every future operation is guaranteed to succeed.', ['cache-coherence'],domain,release)
    assert result.assessment.outcome == AssessmentOutcome.NOT_ASSESSED
    assert result.assessment.reason == 'assessment-target-not-literally-supported'
    assert not result.provider_called and client.calls == 0


@pytest.mark.asyncio
async def test_v2_accepts_paraphrased_attempt_when_the_target_is_source_bound(scoped):
    client = Client('correct')
    assessor = SourceBoundModelAssessor(client,version='v2')
    result = await assessor.assess('I think cached copies agree with one another.', ['cache-coherence'],*scoped)
    assert result.assessment.outcome == AssessmentOutcome.CORRECT
    assert assessor.implementation_id == 'source-bound-model-assessment-v2'
    assert client.calls == 1


@pytest.mark.asyncio
async def test_short_unsupported_target_clause_cannot_be_ignored(scoped):
    domain, release = scoped
    domain.concepts[0].description += ' Everything succeeds.'
    client = Client('correct')
    result = await SourceBoundModelAssessor(client,version='v2').assess(SUPPORTED,
        ['cache-coherence'],domain,release)
    assert not result.provider_called
    assert result.assessment.outcome == AssessmentOutcome.NOT_ASSESSED
