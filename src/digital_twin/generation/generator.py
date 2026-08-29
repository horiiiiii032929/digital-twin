import time
from collections.abc import Callable

from pydantic import ValidationError

from src.digital_twin.generation.citations import (
    DeterministicCitationValidator,
    resolve_atomic_claim_lineage,
)
from src.digital_twin.generation.models import (
    ModelBoundaryAction,
    ModelTutorOutput,
    ModelTutorOutputV2,
    ModelTutorOutputV3,
    PolicyAction,
)
from src.digital_twin.generation.policy import DeterministicPolicyEnforcer
from src.digital_twin.generation.prompt import GroundedPromptBuilder
from src.digital_twin.grounding.models import (
    GenerationTrace,
    GenerationUsage,
    RetrievalHit,
    TutorAnswer,
)
from src.digital_twin.llm import LlmClient, LlmError, LlmMalformedResponseError
from src.digital_twin.tutor_policy import TutorPolicy


_Clock = Callable[[], float]


class DeterministicGroundedGenerator:
    implementation_id = "deterministic-grounded-generator"
    version = "v1"

    def __init__(
        self,
        *,
        prompt_builder: GroundedPromptBuilder | None = None,
        policy_enforcer: DeterministicPolicyEnforcer | None = None,
        citation_validator: DeterministicCitationValidator | None = None,
        clock: _Clock = time.perf_counter,
    ) -> None:
        self.prompt_builder = prompt_builder or GroundedPromptBuilder()
        self.policy_enforcer = policy_enforcer or DeterministicPolicyEnforcer()
        self.citation_validator = citation_validator or DeterministicCitationValidator()
        self.clock = clock

    async def generate(
        self,
        question: str,
        hits: list[RetrievalHit],
        policy: TutorPolicy,
    ) -> TutorAnswer:
        started = self.clock()
        approved_hits = _approved_hits(hits)
        decision = self.policy_enforcer.evaluate(question, approved_hits, policy)
        short_circuit = _policy_answer(
            decision.action,
            generator_id=self.implementation_id,
            started=started,
            clock=self.clock,
        )
        if short_circuit is not None:
            return short_circuit

        prompt = self.prompt_builder.build(question, approved_hits, policy)
        citations = self.citation_validator.validate(["S1"], prompt.evidence)
        return TutorAnswer(
            content=f"Based on approved course evidence: {approved_hits[0].chunk.text}",
            citations=citations,
            trace=_trace(
                generator_id=self.implementation_id,
                provider_model="deterministic/v1",
                prompt_version=prompt.version,
                policy_action=decision.action,
                started=started,
                clock=self.clock,
            ),
        )
    async def generate_for_intent(
        self,
        question: str,
        hits: list[RetrievalHit],
        policy: TutorPolicy,
        *,
        intent: str,
        help_level: int,
        repair_reason: str | None = None,
    ) -> TutorAnswer:
        del repair_reason
        answer = await self.generate(question, hits, policy)
        if answer.trace is None or answer.trace.policy_action != PolicyAction.ANSWER:
            return answer
        evidence = _approved_hits(hits)[0].chunk.text
        content = _deterministic_pedagogical_response(intent, help_level, evidence)
        return answer.model_copy(update={"content": content})


class LiveGroundedGenerator:
    implementation_id = "live-provider-generator"
    version = "v1"

    def __init__(
        self,
        client: LlmClient,
        *,
        prompt_builder: GroundedPromptBuilder | None = None,
        policy_enforcer: DeterministicPolicyEnforcer | None = None,
        citation_validator: DeterministicCitationValidator | None = None,
        clock: _Clock = time.perf_counter,
    ) -> None:
        self.client = client
        self.prompt_builder = prompt_builder or GroundedPromptBuilder()
        self.policy_enforcer = policy_enforcer or DeterministicPolicyEnforcer()
        self.citation_validator = citation_validator or DeterministicCitationValidator()
        self.clock = clock

    async def generate(
        self,
        question: str,
        hits: list[RetrievalHit],
        policy: TutorPolicy,
    ) -> TutorAnswer:
        started = self.clock()
        approved_hits = _approved_hits(hits)
        decision = self.policy_enforcer.evaluate(question, approved_hits, policy)
        short_circuit = _policy_answer(
            decision.action,
            generator_id=self.implementation_id,
            started=started,
            clock=self.clock,
        )
        if short_circuit is not None:
            return short_circuit

        prompt = self.prompt_builder.build(question, approved_hits, policy)
        try:
            response = await self.client.chat(
                prompt.messages,
                task="grounded_tutor_answer",
            )
        except LlmError as error:
            return _provider_failure(error, started=started, clock=self.clock)

        try:
            output = ModelTutorOutput.model_validate_json(response.content)
            citations = self.citation_validator.validate(
                output.citation_ids,
                prompt.evidence,
            )
        except (ValidationError, ValueError):
            return _provider_failure(
                LlmMalformedResponseError(),
                started=started,
                clock=self.clock,
                provider_model=response.provider_model,
                usage=response.usage,
            )

        return TutorAnswer(
            content=output.answer,
            citations=citations,
            trace=_trace(
                generator_id=self.implementation_id,
                provider_model=response.provider_model,
                provider_revision=response.provider_revision,
                prompt_version=prompt.version,
                policy_action=decision.action,
                started=started,
                clock=self.clock,
                usage=response.usage,
            ),
        )

    async def generate_for_intent(
        self,
        question: str,
        hits: list[RetrievalHit],
        policy: TutorPolicy,
        *,
        intent: str,
        help_level: int,
        repair_reason: str | None = None,
    ) -> TutorAnswer:
        build_for_intent = getattr(self.prompt_builder, "build_for_intent", None)
        if not callable(build_for_intent):
            raise ValueError("live T1 generation requires a pedagogical prompt builder")
        started = self.clock()
        approved_hits = _approved_hits(hits)
        decision = self.policy_enforcer.evaluate(question, approved_hits, policy)
        short_circuit = _policy_answer(
            decision.action,
            generator_id=self.implementation_id,
            started=started,
            clock=self.clock,
        )
        if short_circuit is not None:
            return short_circuit
        prompt = build_for_intent(
            question,
            approved_hits,
            policy,
            intent=intent,
            help_level=help_level,
            repair_reason=repair_reason,
        )
        try:
            response = await self.client.chat(
                prompt.messages,
                task="bounded_pedagogical_tutor_answer",
            )
        except LlmError as error:
            return _provider_failure(error, started=started, clock=self.clock)
        try:
            output = ModelTutorOutput.model_validate_json(response.content)
            citations = self.citation_validator.validate(
                output.citation_ids,
                prompt.evidence,
            )
        except (ValidationError, ValueError):
            return _provider_failure(
                LlmMalformedResponseError(),
                started=started,
                clock=self.clock,
                provider_model=response.provider_model,
                usage=response.usage,
            )
        return TutorAnswer(
            content=output.answer,
            citations=citations,
            trace=_trace(
                generator_id=self.implementation_id,
                provider_model=response.provider_model,
                provider_revision=response.provider_revision,
                prompt_version=prompt.version,
                policy_action=decision.action,
                started=started,
                clock=self.clock,
                usage=response.usage,
            ),
        )


class LiveAtomicGroundedGenerator(LiveGroundedGenerator):
    """Prospective live generator with server-resolved atomic claim lineage."""

    implementation_id = "live-atomic-grounded-generator"
    version = "v1"

    async def generate(
        self,
        question: str,
        hits: list[RetrievalHit],
        policy: TutorPolicy,
    ) -> TutorAnswer:
        started = self.clock()
        approved_hits = _approved_hits(hits)
        decision = self.policy_enforcer.evaluate(question, approved_hits, policy)
        short_circuit = _policy_answer(
            decision.action,
            generator_id=self.implementation_id,
            started=started,
            clock=self.clock,
        )
        if short_circuit is not None:
            return short_circuit

        prompt = self.prompt_builder.build(question, approved_hits, policy)
        try:
            response = await self.client.chat(
                prompt.messages,
                task="grounded_tutor_atomic_claims",
            )
        except LlmError as error:
            return _provider_failure(error, started=started, clock=self.clock)

        try:
            output = ModelTutorOutputV2.model_validate_json(response.content)
            citation_ids = list(
                dict.fromkeys(
                    citation_id
                    for claim in output.claims
                    for citation_id in claim.citation_ids
                )
            )
            citations = self.citation_validator.validate(
                citation_ids,
                prompt.evidence,
            )
            claims = resolve_atomic_claim_lineage(output, prompt.evidence)
        except (ValidationError, ValueError):
            return _provider_failure(
                LlmMalformedResponseError(),
                started=started,
                clock=self.clock,
                provider_model=response.provider_model,
                usage=response.usage,
            )

        return TutorAnswer(
            content=" ".join(claim.text for claim in claims),
            citations=citations,
            atomic_claims=claims,
            trace=_trace(
                generator_id=self.implementation_id,
                provider_model=response.provider_model,
                provider_revision=response.provider_revision,
                prompt_version=prompt.version,
                policy_action=decision.action,
                started=started,
                clock=self.clock,
                usage=response.usage,
            ),
        )


    async def generate_for_intent(
        self,
        question: str,
        hits: list[RetrievalHit],
        policy: TutorPolicy,
        *,
        intent: str,
        help_level: int,
        repair_reason: str | None = None,
    ) -> TutorAnswer:
        build_for_intent = getattr(self.prompt_builder, "build_for_intent", None)
        if not callable(build_for_intent):
            raise ValueError("live T1 generation requires a pedagogical prompt builder")
        started = self.clock()
        approved_hits = _approved_hits(hits)
        decision = self.policy_enforcer.evaluate(question, approved_hits, policy)
        short_circuit = _policy_answer(
            decision.action,
            generator_id=self.implementation_id,
            started=started,
            clock=self.clock,
        )
        if short_circuit is not None:
            return short_circuit
        prompt = build_for_intent(
            question,
            approved_hits,
            policy,
            intent=intent,
            help_level=help_level,
            repair_reason=repair_reason,
        )
        try:
            response = await self.client.chat(
                prompt.messages,
                task="bounded_pedagogical_tutor_answer",
            )
        except LlmError as error:
            return _provider_failure(error, started=started, clock=self.clock)
        try:
            output = ModelTutorOutput.model_validate_json(response.content)
            citations = self.citation_validator.validate(
                output.citation_ids,
                prompt.evidence,
            )
        except (ValidationError, ValueError):
            return _provider_failure(
                LlmMalformedResponseError(),
                started=started,
                clock=self.clock,
                provider_model=response.provider_model,
                usage=response.usage,
            )
        return TutorAnswer(
            content=output.answer,
            citations=citations,
            trace=_trace(
                generator_id=self.implementation_id,
                provider_model=response.provider_model,
                provider_revision=response.provider_revision,
                prompt_version=prompt.version,
                policy_action=decision.action,
                started=started,
                clock=self.clock,
                usage=response.usage,
            ),
        )


class LiveExtractiveBoundaryGroundedGenerator(LiveGroundedGenerator):
    """Boundary-aware generator whose releasable facts remain extractive."""

    implementation_id = "live-extractive-boundary-grounded-generator"
    version = "v1"

    async def generate(
        self,
        question: str,
        hits: list[RetrievalHit],
        policy: TutorPolicy,
    ) -> TutorAnswer:
        started = self.clock()
        approved_hits = _approved_hits(hits)
        decision = self.policy_enforcer.evaluate(question, approved_hits, policy)
        short_circuit = _policy_answer(
            decision.action,
            generator_id=self.implementation_id,
            started=started,
            clock=self.clock,
        )
        if short_circuit is not None:
            return short_circuit

        prompt = self.prompt_builder.build(question, approved_hits, policy)
        try:
            response = await self.client.chat(
                prompt.messages,
                task="grounded_tutor_extractive_boundary",
            )
        except LlmError as error:
            return _provider_failure(error, started=started, clock=self.clock)

        try:
            output = ModelTutorOutputV3.model_validate_json(response.content)
            if output.action != ModelBoundaryAction.ANSWER:
                action = (
                    PolicyAction.CLARIFY
                    if output.action == ModelBoundaryAction.CLARIFY
                    else PolicyAction.NO_EVIDENCE
                )
                content = (
                    "Which concept or referent do you mean?"
                    if action == PolicyAction.CLARIFY
                    else "I do not have enough approved course evidence to answer that question."
                )
                return TutorAnswer(
                    content=content,
                    trace=_trace(
                        generator_id=self.implementation_id,
                        provider_model=response.provider_model,
                        provider_revision=response.provider_revision,
                        prompt_version=prompt.version,
                        policy_action=action,
                        started=started,
                        clock=self.clock,
                        usage=response.usage,
                    ),
                )
            citation_ids = list(
                dict.fromkeys(
                    citation_id
                    for claim in output.claims
                    for citation_id in claim.citation_ids
                )
            )
            citations = self.citation_validator.validate(citation_ids, prompt.evidence)
            claims = resolve_atomic_claim_lineage(output, prompt.evidence)
        except (ValidationError, ValueError):
            return _provider_failure(
                LlmMalformedResponseError(),
                started=started,
                clock=self.clock,
                provider_model=response.provider_model,
                usage=response.usage,
            )

        return TutorAnswer(
            content=" ".join(claim.text for claim in claims),
            citations=citations,
            atomic_claims=claims,
            trace=_trace(
                generator_id=self.implementation_id,
                provider_model=response.provider_model,
                provider_revision=response.provider_revision,
                prompt_version=prompt.version,
                policy_action=PolicyAction.ANSWER,
                started=started,
                clock=self.clock,
                usage=response.usage,
            ),
        )


def _approved_hits(hits: list[RetrievalHit]) -> list[RetrievalHit]:
    return [hit for hit in hits if hit.chunk.retrieval_allowed]


def _deterministic_pedagogical_response(
    intent: str,
    help_level: int,
    evidence: str,
) -> str:
    lead = {
        "diagnose_understanding": "Start by identifying the part you already understand.",
        "ask_next_step": "What would your next reasoning step be?",
        "prompt_self_explanation": "Explain this relationship in your own words.",
        "give_hint": "Hint: focus on this approved course statement.",
        "give_analogy_or_example": "Use this approved course statement as the example.",
        "correct_misconception": "Recheck the misconception against this course statement.",
        "explain_concept": "Here is the relevant course explanation.",
        "check_understanding": "Use this statement, then explain what it implies.",
        "give_retrieval_practice": "Recall the key relationship before checking this statement.",
        "summarize_progress": "The relevant course point is this.",
        "close_or_transition_objective": "Use this final check before moving on.",
    }.get(intent, "Work from this approved course statement.")
    scaffold = " Try one step yourself." if help_level < 3 else " Compare it directly with your current reasoning."
    return f"{lead} {evidence}{scaffold}"


def _policy_answer(
    action: PolicyAction,
    *,
    generator_id: str,
    started: float,
    clock: _Clock,
) -> TutorAnswer | None:
    if action == PolicyAction.NO_EVIDENCE:
        return TutorAnswer(
            content=(
                "I do not have approved course evidence for that question. "
                "Please ask about the available course material or ask the instructor."
            ),
            warnings=["No approved source evidence was retrieved."],
            trace=_trace(
                generator_id=generator_id,
                provider_model="not-called",
                prompt_version="not-built",
                policy_action=action,
                started=started,
                clock=clock,
            ),
        )
    if action == PolicyAction.POLICY_NOT_APPROVED:
        return TutorAnswer(
            content=(
                "This tutor is not available because its professor policy has not "
                "been approved for student release."
            ),
            warnings=["Professor-approved tutor policy is required."],
            trace=_trace(
                generator_id=generator_id,
                provider_model="not-called",
                prompt_version="not-built",
                policy_action=action,
                started=started,
                clock=clock,
            ),
        )
    if action == PolicyAction.INVALID_REQUEST:
        return TutorAnswer(
            content="Please enter a course question so I can help.",
            warnings=["An empty question cannot be sent to the tutor model."],
            trace=_trace(
                generator_id=generator_id,
                provider_model="not-called",
                prompt_version="not-built",
                policy_action=action,
                started=started,
                clock=clock,
            ),
        )
    if action == PolicyAction.REDIRECT_GRADED_WORK:
        return TutorAnswer(
            content=(
                "I cannot complete graded work for you. Tell me what you have tried, "
                "and I can offer a hint or explain the underlying concept."
            ),
            warnings=["Academic-integrity policy redirected this request."],
            trace=_trace(
                generator_id=generator_id,
                provider_model="not-called",
                prompt_version="not-built",
                policy_action=action,
                started=started,
                clock=clock,
            ),
        )
    return None


def _provider_failure(
    error: LlmError,
    *,
    started: float,
    clock: _Clock,
    provider_model: str = "not-returned",
    usage: GenerationUsage | None = None,
) -> TutorAnswer:
    messages = {
        "timeout": "The tutor model timed out before producing an answer.",
        "authentication": "Live generation is not configured correctly.",
        "configuration": "Live generation is not configured correctly.",
        "unavailable": "The tutor model is temporarily unavailable.",
        "budget-exceeded": "The tutor model usage budget has been reached.",
        "malformed-response": "The tutor model returned an invalid grounded answer.",
    }
    warning = messages.get(error.code, "The tutor model could not produce an answer.")
    return TutorAnswer(
        content=f"{warning} Please try again or ask the instructor.",
        warnings=[warning],
        trace=_trace(
            generator_id=LiveGroundedGenerator.implementation_id,
            provider_model=provider_model,
            prompt_version=GroundedPromptBuilder.version,
            policy_action=PolicyAction.SAFE_PROVIDER_FAILURE,
            started=started,
            clock=clock,
            usage=usage,
        ),
    )


def _trace(
    *,
    generator_id: str,
    provider_model: str,
    prompt_version: str,
    policy_action: PolicyAction,
    started: float,
    clock: _Clock,
    provider_revision: str | None = None,
    usage: GenerationUsage | None = None,
) -> GenerationTrace:
    return GenerationTrace(
        generator_id=generator_id,
        provider_model=provider_model,
        provider_revision=provider_revision,
        prompt_version=prompt_version,
        policy_action=policy_action.value,
        latency_ms=max(0.0, (clock() - started) * 1000),
        usage=usage or GenerationUsage(),
    )
