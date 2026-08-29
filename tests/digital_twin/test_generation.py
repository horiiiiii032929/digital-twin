import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.evaluate_generation import (
    _arguments,
    _evaluation_mode,
    _external_provider_requires_acknowledgment,
    _paid_provider_called,
)
from src.digital_twin.generation import (
    BoundedPedagogicalPromptBuilder,
    ClarificationFirstGroundedPromptBuilder,
    ConservativeGroundedPromptBuilder,
    DeterministicCitationValidator,
    DeterministicGroundedGenerator,
    DeterministicPolicyEnforcer,
    GenerationEvaluationSet,
    GroundedPromptBuilder,
    LiveAtomicGroundedGenerator,
    LiveExtractiveBoundaryGroundedGenerator,
    LiveGroundedGenerator,
    PolicyAction,
    ExtractiveBoundaryGroundedPromptBuilder,
    StrictEvidenceGroundedPromptBuilder,
    authoritative_citation_for_chunk,
    citation_matches_chunk,
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
            field.value = {
                **field.value,
                "source_strictness": "any_source_with_labels",
                "confirmed": True,
            }
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


def test_policy_enforcer_rejects_malformed_approved_source_policy():
    policy = approved_policy()
    knowledge = next(
        field for field in policy.all_fields if field.id == "knowledge_source_policy"
    )
    knowledge.value = {
        **knowledge.value,
        "source_strictness": "unresolved",
        "confirmed": True,
    }

    decision = DeterministicPolicyEnforcer().evaluate(
        "How does CSRF work?",
        [approved_hit()],
        policy,
    )

    assert decision.action == PolicyAction.POLICY_NOT_APPROVED


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


def test_policy_enforcer_redirects_direct_graded_work_without_retrieval_hits():
    decision = DeterministicPolicyEnforcer().evaluate(
        "Give me the full answer for my graded assignment.",
        [],
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


def test_prompt_excludes_non_authoritative_search_description():
    hit = approved_hit()
    hit.chunk.metadata["search_description"] = (
        "Generated claim that must remain retrieval-only."
    )
    hit.chunk.metadata["description_is_authoritative"] = "false"

    prompt = GroundedPromptBuilder().build(
        "How does CSRF work?",
        [hit],
        approved_policy(),
    )

    assert "Generated claim" not in prompt.messages[1].content
    assert "authenticated browser session" in prompt.messages[1].content


def test_conservative_prompt_freezes_support_and_length_constraints():
    prompt = ConservativeGroundedPromptBuilder().build(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
    )

    assert prompt.version == "v2"
    assert "Use no outside facts" in prompt.messages[0].content
    assert "at most 120 words" in prompt.messages[0].content
    assert '"citation_ids"' in prompt.messages[0].content


def test_strict_evidence_prompt_forbids_development_failure_modes():
    prompt = StrictEvidenceGroundedPromptBuilder().build(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
    )

    assert prompt.version == "v3"
    assert "do not ask a follow-up question" in prompt.messages[0].content
    assert "implementation advice" in prompt.messages[0].content
    assert "student did not state" in prompt.messages[0].content
    assert "at most 60 words" in prompt.messages[0].content


def test_clarification_first_prompt_freezes_narrow_ambiguity_repair():
    prompt = ClarificationFirstGroundedPromptBuilder().build(
        "Can you explain the bridge?",
        [approved_hit()],
        approved_policy(),
    )

    assert prompt.version == "v4"
    assert "do not explain either meaning yet" in prompt.messages[0].content
    assert "beginning with 'Which meaning'" in prompt.messages[0].content
    assert "at most 60 words" in prompt.messages[0].content


def test_extractive_boundary_prompt_freezes_action_and_quote_contract():
    prompt = ExtractiveBoundaryGroundedPromptBuilder().build(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
    )

    assert prompt.version == "v5"
    assert "answer|abstain|clarify" in prompt.messages[0].content
    assert "copied exactly as one contiguous span" in prompt.messages[0].content
    assert "claim-[a-z0-9-]+" in prompt.messages[0].content


def test_bounded_pedagogical_prompt_carries_only_code_selected_plan():
    prompt = BoundedPedagogicalPromptBuilder().build_for_intent(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
        intent="give_hint",
        help_level=1,
        repair_reason=None,
    )
    payload = json.loads(prompt.messages[1].content)

    assert prompt.version == "t1-v1"
    assert payload["pedagogical_plan"] == {
        "help_level": 1,
        "intent": "give_hint",
        "repair_reason": None,
    }
    assert payload["approved_evidence"][0]["citation_id"] == "S1"
    assert "do not choose a different teaching move" in prompt.messages[0].content


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
async def test_deterministic_generator_applies_bounded_intent_without_changing_lineage():
    answer = await DeterministicGroundedGenerator().generate_for_intent(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
        intent="give_hint",
        help_level=1,
    )

    assert answer.content.startswith("Hint:")
    assert answer.citations == [authoritative_citation_for_chunk(approved_hit().chunk)]
    assert answer.trace is not None and answer.trace.policy_action == "answer"


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
async def test_live_atomic_generator_resolves_claim_and_citation_lineage():
    response = LlmResponse(
        content=json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "claim-csrf-session",
                        "text": "CSRF abuses an authenticated browser session.",
                        "citation_ids": ["S1"],
                    },
                    {
                        "claim_id": "claim-csrf-defense",
                        "text": "SameSite cookies are a common defense.",
                        "citation_ids": ["S1"],
                    },
                ]
            }
        ),
        provider_model="fixture-live/v1",
        usage=GenerationUsage(input_tokens=100, output_tokens=40, total_tokens=140),
    )
    client = RecordingClient(response)

    answer = await LiveAtomicGroundedGenerator(client).generate(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
    )

    assert client.calls[0][1] == "grounded_tutor_atomic_claims"
    assert [claim.claim_id for claim in answer.atomic_claims] == [
        "claim-csrf-session",
        "claim-csrf-defense",
    ]
    assert all(
        claim.evidence_hit_ids == ["chunk-csrf-1"]
        for claim in answer.atomic_claims
    )
    assert len(answer.citations) == 1
    assert answer.citations[0].source_id == "document-csrf"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "claims", "expected_action"),
    [
        (
            "answer",
            [
                {
                    "claim_id": "claim-csrf-session",
                    "text": "CSRF abuses an authenticated browser session.",
                    "citation_ids": ["S1"],
                }
            ],
            "answer",
        ),
        ("abstain", [], "no-evidence"),
        ("clarify", [], "clarify"),
    ],
)
async def test_extractive_boundary_generator_returns_bounded_actions(
    action,
    claims,
    expected_action,
):
    response = LlmResponse(
        content=json.dumps({"action": action, "claims": claims}),
        provider_model="fixture-live/v1",
    )
    answer = await LiveExtractiveBoundaryGroundedGenerator(
        RecordingClient(response),
        prompt_builder=ExtractiveBoundaryGroundedPromptBuilder(),
    ).generate(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
    )

    assert answer.trace is not None
    assert answer.trace.policy_action == expected_action
    assert bool(answer.atomic_claims) is (action == "answer")
    assert bool(answer.citations) is (action == "answer")


@pytest.mark.asyncio
async def test_extractive_boundary_generator_rejects_claim_id_outside_schema_contract():
    response = LlmResponse(
        content=json.dumps(
            {
                "action": "answer",
                "claims": [
                    {
                        "claim_id": "c1",
                        "text": "CSRF abuses an authenticated browser session.",
                        "citation_ids": ["S1"],
                    }
                ],
            }
        ),
        provider_model="fixture-live/v1",
    )
    answer = await LiveExtractiveBoundaryGroundedGenerator(
        RecordingClient(response),
        prompt_builder=ExtractiveBoundaryGroundedPromptBuilder(),
    ).generate(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
    )

    assert answer.trace is not None
    assert answer.trace.policy_action == "safe-provider-failure"
    assert answer.atomic_claims == []


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
    assert answer.trace is not None
    assert answer.trace.policy_action == "safe-provider-failure"


@pytest.mark.asyncio
async def test_blank_live_answer_fails_closed():
    answer = await LiveGroundedGenerator(
        RecordingClient(live_response(answer="   "))
    ).generate(
        "How does CSRF work?",
        [approved_hit()],
        approved_policy(),
    )

    assert answer.citations == []
    assert answer.warnings == ["The tutor model returned an invalid grounded answer."]


def test_generation_evaluator_does_not_understate_external_provider_use():
    assert not _paid_provider_called(None)
    assert not _paid_provider_called("ollama/gemma3:4b")
    assert _paid_provider_called("provider/model-v1")
    assert _evaluation_mode(None) == "deterministic-control"
    assert _evaluation_mode("ollama/gemma3:4b") == "live-local-candidate"
    assert _evaluation_mode("provider/model-v1") == "live-external-candidate"


def test_generation_evaluator_requires_external_provider_acknowledgment(
    monkeypatch,
):
    assert _external_provider_requires_acknowledgment("provider/model-v1", False)
    monkeypatch.setattr(
        sys,
        "argv",
        ["evaluate_generation", "--model", "provider/model-v1"],
    )

    with pytest.raises(SystemExit, match="2"):
        _arguments()


@pytest.mark.parametrize("model", ("ollama/gemma3:4b", "ollama/qwen3:4b"))
def test_generation_evaluator_cannot_reproduce_prohibited_models(
    monkeypatch,
    model,
):
    monkeypatch.setattr(sys, "argv", ["evaluate_generation", "--model", model])

    with pytest.raises(SystemExit, match="2"):
        _arguments()


def test_generation_evaluator_accepts_explicit_external_provider_scope(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate_generation",
            "--model",
            "provider/model-v1",
            "--allow-external-provider",
        ],
    )

    arguments = _arguments()

    assert arguments.model == "provider/model-v1"
    assert arguments.allow_external_provider


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


def test_citation_lineage_match_rejects_altered_version_but_canonicalizes_title():
    hit = approved_hit()
    citation = authoritative_citation_for_chunk(hit.chunk)

    assert citation_matches_chunk(
        citation.model_copy(update={"title": "Untrusted presentation title"}),
        hit.chunk,
    )
    assert not citation_matches_chunk(
        citation.model_copy(update={"source_version": hit.chunk.source_version + 1}),
        hit.chunk,
    )
