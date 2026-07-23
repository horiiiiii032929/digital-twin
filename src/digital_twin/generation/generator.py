import time
from collections.abc import Callable

from pydantic import ValidationError

from src.digital_twin.generation.citations import DeterministicCitationValidator
from src.digital_twin.generation.models import ModelTutorOutput, PolicyAction
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
                prompt_version=prompt.version,
                policy_action=decision.action,
                started=started,
                clock=self.clock,
                usage=response.usage,
            ),
        )


def _approved_hits(hits: list[RetrievalHit]) -> list[RetrievalHit]:
    return [hit for hit in hits if hit.chunk.retrieval_allowed]


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
            policy_action=PolicyAction.ANSWER,
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
    usage: GenerationUsage | None = None,
) -> GenerationTrace:
    return GenerationTrace(
        generator_id=generator_id,
        provider_model=provider_model,
        prompt_version=prompt_version,
        policy_action=policy_action.value,
        latency_ms=max(0.0, (clock() - started) * 1000),
        usage=usage or GenerationUsage(),
    )
