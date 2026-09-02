"""Bounded learner-state and pedagogical-intent orchestration for T1 tutoring."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Protocol, TypedDict

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.digital_twin.generation import citation_matches_chunk
from src.digital_twin.grounding.models import (
    GenerationTrace,
    GenerationUsage,
    RetrievalHit,
    TutorAnswer,
)
from src.digital_twin.grounding.protocols import PostGenerationClaimValidator
from src.digital_twin.llm import LlmClient, LlmError, LlmIdentityDriftError, LlmMessage
from src.digital_twin.student.models import (
    AuditEvent,
    Conversation,
    DigitalTwinRelease,
)
from src.digital_twin.student.autonomy_models import (
    AgentTraceV2,
    AssessmentOutcome,
    AutonomousActionKind,
    CourseDomainModelV1,
    GroundedTutorResponseV2,
    LearnerBeliefStateV2,
    LearnerHypothesisV2,
    LearnerObservationV2,
    LearnerStateDeltaV2,
    PedagogicalPlanV2,
    ReactiveSemanticProposalV2,
    ReactiveTurnArtifactsV2,
    TurnPerceptionV2,
)
from src.digital_twin.student.learner_belief import (
    DeterministicEvidenceCountBeliefEstimator,
)
from src.digital_twin.tutor_policy import timestamp_now


class TutoringMode(str):
    """Stable runtime labels without coupling domain code to API settings."""

    T0 = "grounded-assistant"
    T1 = "bounded-tutoring-graph"
    T1_V2 = "governed-autonomous-tutoring-graph-v2.1"


class TutoringIntent(str):
    CLARIFY_REQUEST = "clarify_request"
    DIAGNOSE_UNDERSTANDING = "diagnose_understanding"
    ASK_NEXT_STEP = "ask_next_step"
    PROMPT_SELF_EXPLANATION = "prompt_self_explanation"
    GIVE_HINT = "give_hint"
    GIVE_ANALOGY_OR_EXAMPLE = "give_analogy_or_example"
    CORRECT_MISCONCEPTION = "correct_misconception"
    EXPLAIN_CONCEPT = "explain_concept"
    CHECK_UNDERSTANDING = "check_understanding"
    GIVE_RETRIEVAL_PRACTICE = "give_retrieval_practice"
    SUMMARIZE_PROGRESS = "summarize_progress"
    REFUSE_AND_REDIRECT = "refuse_and_redirect"
    ABSTAIN_NO_EVIDENCE = "abstain_no_evidence"
    CLOSE_OR_TRANSITION_OBJECTIVE = "close_or_transition_objective"


POLICY_ACTION_PRIORITY = {
    "answer": 0,
    "abstain": 1,
    "clarify": 2,
    "refuse": 3,
    "operational-failure": 4,
}


def resolve_policy_action(*actions: str) -> str:
    """Resolve competing proposals through the fixed fail-closed action lattice."""

    if not actions:
        return "answer"
    unknown = set(actions) - set(POLICY_ACTION_PRIORITY)
    if unknown:
        raise ValueError(f"unsupported policy actions: {sorted(unknown)}")
    return max(actions, key=POLICY_ACTION_PRIORITY.__getitem__)


def retrieval_boundary_intent(events: list[AuditEvent]) -> str | None:
    """Read a deterministic evidence-gate recommendation from audit events."""

    for event in reversed(events):
        if event.event_type != "evidence-sufficiency-assessed":
            continue
        recommendation = event.details.get("recommended_action")
        if recommendation == "clarify":
            return TutoringIntent.CLARIFY_REQUEST
        if recommendation == "abstain":
            return TutoringIntent.ABSTAIN_NO_EVIDENCE
    return None


def deterministic_policy_boundary_answer(intent: str) -> TutorAnswer | None:
    """Render a policy-owned response without invoking a model or fallback."""

    responses = {
        TutoringIntent.REFUSE_AND_REDIRECT: (
            "I cannot complete graded work for you. Share what you have tried, "
            "and I can help with one bounded next step.",
            "redirect-graded-work",
        ),
        TutoringIntent.ABSTAIN_NO_EVIDENCE: (
            "I do not have enough approved course evidence to support that "
            "response. Please refine the question or ask the instructor.",
            "no-evidence",
        ),
        TutoringIntent.CLARIFY_REQUEST: (
            "Which concept or step would you like to work through?",
            "clarify-request",
        ),
    }
    selected = responses.get(intent)
    if selected is None:
        return None
    content, action = selected
    return TutorAnswer(
        content=content,
        trace=GenerationTrace(
            generator_id="bounded-tutoring-graph-v1",
            provider_model="not-called",
            prompt_version="graph-policy-v1",
            policy_action=action,
            latency_ms=0,
            usage=GenerationUsage(),
        ),
    )


class TurnSignals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_type: str = Field(min_length=1)
    attempt_present: bool = False
    confusion: float = Field(default=0, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    engagement: float = Field(default=0.5, ge=0, le=1)
    ambiguous: bool = False
    misconception_observed: bool = False
    direct_solution_request: bool = False


class ConceptMastery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estimate: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0, ge=0, le=1)
    observation_count: int = Field(default=0, ge=0)


class LearnerState(BaseModel):
    """Privacy-minimized durable state; the raw transcript remains authoritative."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0.0"
    conversation_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    revision: int = Field(default=0, ge=0)
    turn_count: int = Field(default=0, ge=0)
    learning_objective: str | None = None
    concept_ids: list[str] = Field(default_factory=list)
    mastery_by_concept: dict[str, ConceptMastery] = Field(default_factory=dict)
    observed_misconceptions: list[str] = Field(default_factory=list)
    hypothesized_misconceptions: list[str] = Field(default_factory=list)
    latest_signals: TurnSignals | None = None
    prior_intent: str | None = None
    help_level: int = Field(default=0, ge=0, le=3)
    integrity_ceiling: str = "attempt-first"
    next_activity: str | None = None
    objective_complete: bool = False
    updated_at: str = Field(default_factory=timestamp_now)

    @model_validator(mode="after")
    def identifiers_and_collections_are_canonical(self) -> "LearnerState":
        if len(self.concept_ids) != len(set(self.concept_ids)):
            raise ValueError("learner-state concept IDs must be unique")
        if len(self.observed_misconceptions) != len(
            set(self.observed_misconceptions)
        ):
            raise ValueError("observed misconception IDs must be unique")
        if len(self.hypothesized_misconceptions) != len(
            set(self.hypothesized_misconceptions)
        ):
            raise ValueError("hypothesized misconception IDs must be unique")
        return self


class TutoringGraphInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    account_id: str = Field(min_length=1)
    conversation: Conversation
    release: DigitalTwinRelease
    student_message: str = Field(min_length=1)
    learner_state: LearnerState
    observed_at: str = Field(default_factory=timestamp_now, min_length=1)
    event_id: str | None = Field(default=None, min_length=1, max_length=128)
    learner_key: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    domain_model: CourseDomainModelV1 | None = None
    learner_belief: LearnerBeliefStateV2 | None = None
    assessment_outcome: AssessmentOutcome = AssessmentOutcome.NOT_ASSESSED
    assessment_confidence: float = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def authoritative_scope_must_match(self) -> "TutoringGraphInput":
        observed_at = datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("tutoring graph observation time must be timezone-aware")
        self.observed_at = observed_at.astimezone(UTC).replace(microsecond=0).isoformat()
        if (
            self.conversation.student_id != self.account_id
            or self.conversation.course_id != self.release.course_id
            or self.conversation.release_id != self.release.id
            or self.learner_state.conversation_id != self.conversation.id
            or self.learner_state.course_id != self.conversation.course_id
            or self.learner_state.release_id != self.conversation.release_id
        ):
            raise ValueError("tutoring graph input has inconsistent scope")
        if self.domain_model is not None and (
            self.domain_model.course_id != self.conversation.course_id
            or self.domain_model.release_id != self.conversation.release_id
        ):
            raise ValueError("tutoring domain model has inconsistent scope")
        if self.learner_belief is not None and (
            self.learner_key is None
            or self.learner_belief.learner_key != self.learner_key
            or self.learner_belief.course_id != self.conversation.course_id
            or self.learner_belief.release_id != self.conversation.release_id
        ):
            raise ValueError("V2 learner belief has inconsistent scope")
        return self


class TutoringGraphResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    answer: TutorAnswer
    hits: list[RetrievalHit]
    audit_events: list[AuditEvent]
    learner_state: LearnerState
    intent: str = Field(min_length=1)
    repair_count: int = Field(ge=0, le=1)
    validation_passed: bool
    failure_reason: str | None = None
    reactive_v2_artifacts: ReactiveTurnArtifactsV2 | None = None


class _GraphState(TypedDict):
    graph_input: TutoringGraphInput
    signals: TurnSignals | None
    learner_state: LearnerState
    hits: list[RetrievalHit]
    audit_events: list[AuditEvent]
    intent: str
    answer: TutorAnswer | None
    validation_passed: bool
    failure_reason: str | None
    repair_count: int


RetrieveStep = Callable[
    [TutoringGraphInput], tuple[list[RetrievalHit], list[AuditEvent]]
]
GenerateStep = Callable[
    [TutoringGraphInput, list[RetrievalHit], str, int, str | None],
    Awaitable[tuple[TutorAnswer, list[AuditEvent]]],
]
FallbackStep = Callable[[TutoringGraphInput, str, str | None], TutorAnswer]


class ReactiveSemanticPlanner(Protocol):
    model_id: str

    async def propose(
        self,
        *,
        message: str,
        perception: TurnPerceptionV2,
        concept_ids: list[str],
        belief: LearnerBeliefStateV2,
        evidence_keys: list[str],
        candidate_intent: str,
    ) -> ReactiveSemanticProposalV2: ...


class DeterministicReactiveSemanticPlanner:
    model_id = "deterministic/reactive-semantic-planner-v1"

    async def propose(
        self,
        *,
        message: str,
        perception: TurnPerceptionV2,
        concept_ids: list[str],
        belief: LearnerBeliefStateV2,
        evidence_keys: list[str],
        candidate_intent: str,
    ) -> ReactiveSemanticProposalV2:
        del message, belief, evidence_keys
        hypothesis_kind = None
        hypothesis_concept_id = None
        hypothesis_confidence = 0.0
        if concept_ids and perception.misconception_observed:
            hypothesis_kind = "misconception"
            hypothesis_concept_id = concept_ids[0]
            hypothesis_confidence = 0.65
        elif concept_ids and perception.confusion >= 0.7:
            hypothesis_kind = "low-confidence"
            hypothesis_concept_id = concept_ids[0]
            hypothesis_confidence = 0.55
        return ReactiveSemanticProposalV2(
            proposed_intent=candidate_intent,
            concept_ids=concept_ids,
            hypothesis_kind=hypothesis_kind,
            hypothesis_concept_id=hypothesis_concept_id,
            hypothesis_confidence=hypothesis_confidence,
            reason_code=f"deterministic-{candidate_intent.replace('_', '-')}",
        )


class LiveReactiveSemanticPlanner:
    """One structured semantic proposal with deterministic fallback and no retry."""

    def __init__(self, client: LlmClient, *, model_id: str) -> None:
        self.client = client
        self.model_id = model_id.strip()
        if not self.model_id:
            raise ValueError("reactive semantic planner model must not be blank")
        self.fallback = DeterministicReactiveSemanticPlanner()

    async def propose(
        self,
        *,
        message: str,
        perception: TurnPerceptionV2,
        concept_ids: list[str],
        belief: LearnerBeliefStateV2,
        evidence_keys: list[str],
        candidate_intent: str,
    ) -> ReactiveSemanticProposalV2:
        payload = {
            "instruction": (
                "Propose one pedagogical intent and at most one tentative learner "
                "hypothesis. Use only the supplied concept IDs. Do not change identity, "
                "policy, evidence, citations, release, state revision, or delivery."
            ),
            "student_message": message,
            "deterministic_perception": perception.model_dump(mode="json"),
            "allowed_concept_ids": concept_ids,
            "belief_evidence_counts": [
                {
                    "concept_id": item.concept_id,
                    "observations": item.observation_count,
                    "assessed": item.assessed_evidence_count,
                    "uncertainty": item.uncertainty,
                }
                for item in belief.concepts
                if item.concept_id in set(concept_ids)
            ],
            "evidence_range_count": len(evidence_keys),
            "deterministic_candidate_intent": candidate_intent,
        }
        try:
            response = await self.client.chat(
                [
                    LlmMessage(
                        role="system",
                        content=(
                            "Return only the requested structured semantic proposal. "
                            "Do not include chain-of-thought or personal data."
                        ),
                    ),
                    LlmMessage(
                        role="user",
                        content=json.dumps(payload, sort_keys=True),
                    ),
                ],
                task="reactive_tutoring_plan",
            )
            return ReactiveSemanticProposalV2.model_validate_json(response.content)
        except LlmIdentityDriftError:
            raise
        except (LlmError, ValueError):
            return await self.fallback.propose(
                message=message,
                perception=perception,
                concept_ids=concept_ids,
                belief=belief,
                evidence_keys=evidence_keys,
                candidate_intent=candidate_intent,
            )


class DeterministicTurnInterpreter:
    implementation_id = "deterministic-turn-interpreter-v1"

    _CONFUSION = re.compile(
        r"\b(confused|confusing|don't understand|do not understand|lost|stuck|why)\b",
        re.IGNORECASE,
    )
    _ATTEMPT = re.compile(
        r"\b(i tried|my attempt|because|therefore|so i|i think|i got|=)\b",
        re.IGNORECASE,
    )
    _MISCONCEPTION = re.compile(
        r"\b(i thought|isn't it|doesn't .* mean|must always|can never)\b",
        re.IGNORECASE,
    )
    _DIRECT_SOLUTION = re.compile(
        r"\b(final answer|full answer|complete solution|do my|solve my|write my|"
        r"give me the answer|finish my)\b",
        re.IGNORECASE,
    )
    _AMBIGUOUS = re.compile(
        r"^(what about (it|that)|explain (it|that)|why|help|i don't get it)[?.! ]*$",
        re.IGNORECASE,
    )

    def interpret(self, message: str) -> TurnSignals:
        normalized = message.strip()
        confusion = 0.8 if self._CONFUSION.search(normalized) else 0.1
        confidence = None
        if re.search(r"\b(i am sure|definitely|certain)\b", normalized, re.I):
            confidence = 0.9
        elif re.search(r"\b(i am not sure|maybe|perhaps)\b", normalized, re.I):
            confidence = 0.3
        return TurnSignals(
            request_type="learning",
            attempt_present=bool(self._ATTEMPT.search(normalized)),
            confusion=confusion,
            confidence=confidence,
            engagement=0.7 if len(normalized.split()) >= 5 else 0.4,
            ambiguous=bool(self._AMBIGUOUS.fullmatch(normalized)),
            misconception_observed=bool(self._MISCONCEPTION.search(normalized)),
            direct_solution_request=bool(self._DIRECT_SOLUTION.search(normalized)),
        )


class DeterministicIntentSelector:
    implementation_id = "deterministic-tutoring-intent-selector-v1"

    def select(
        self,
        signals: TurnSignals,
        learner_state: LearnerState,
        hits: list[RetrievalHit],
    ) -> str:
        if signals.direct_solution_request:
            return TutoringIntent.REFUSE_AND_REDIRECT
        if signals.ambiguous:
            return TutoringIntent.CLARIFY_REQUEST
        if not hits:
            return TutoringIntent.ABSTAIN_NO_EVIDENCE
        if signals.misconception_observed:
            return TutoringIntent.CORRECT_MISCONCEPTION
        if signals.confusion >= 0.7:
            if learner_state.help_level >= 2:
                return TutoringIntent.EXPLAIN_CONCEPT
            return TutoringIntent.GIVE_HINT
        if signals.attempt_present:
            return TutoringIntent.ASK_NEXT_STEP
        if learner_state.turn_count == 0:
            return TutoringIntent.DIAGNOSE_UNDERSTANDING
        return TutoringIntent.CHECK_UNDERSTANDING


class BoundedTutoringGraph:
    """One-message graph with a fixed terminal path and at most one repair."""

    implementation_id = "bounded-tutoring-graph-v1"
    recursion_limit = 12

    def __init__(
        self,
        *,
        retrieve: RetrieveStep,
        generate: GenerateStep,
        fallback: FallbackStep,
        interpreter: DeterministicTurnInterpreter | None = None,
        selector: DeterministicIntentSelector | None = None,
    ) -> None:
        self.retrieve = retrieve
        self.generate = generate
        self.fallback = fallback
        self.interpreter = interpreter or DeterministicTurnInterpreter()
        self.selector = selector or DeterministicIntentSelector()
        self._graph = self._build_graph()

    async def run(self, graph_input: TutoringGraphInput) -> TutoringGraphResult:
        initial: _GraphState = {
            "graph_input": graph_input,
            "signals": None,
            "learner_state": graph_input.learner_state.model_copy(deep=True),
            "hits": [],
            "audit_events": [],
            "intent": TutoringIntent.CLARIFY_REQUEST,
            "answer": None,
            "validation_passed": False,
            "failure_reason": None,
            "repair_count": 0,
        }
        result = await self._graph.ainvoke(
            initial,
            config={"recursion_limit": self.recursion_limit},
        )
        answer = result["answer"]
        if answer is None:
            raise RuntimeError("tutoring graph terminated without an answer")
        return TutoringGraphResult(
            answer=answer,
            hits=result["hits"],
            audit_events=result["audit_events"],
            learner_state=result["learner_state"],
            intent=result["intent"],
            repair_count=result["repair_count"],
            validation_passed=result["validation_passed"],
            failure_reason=result["failure_reason"],
        )

    def _build_graph(self):
        graph = StateGraph(_GraphState)
        graph.add_node("interpret", self._interpret)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("select_intent", self._select_intent)
        graph.add_node("generate", self._generate)
        graph.add_node("validate", self._validate)
        graph.add_node("repair", self._repair)
        graph.add_node("validate_repair", self._validate)
        graph.add_node("fallback", self._fallback)
        graph.add_node("finalize", self._finalize)
        graph.add_edge(START, "interpret")
        graph.add_edge("interpret", "retrieve")
        graph.add_edge("retrieve", "select_intent")
        graph.add_edge("select_intent", "generate")
        graph.add_edge("generate", "validate")
        graph.add_conditional_edges(
            "validate",
            self._after_first_validation,
            {"pass": "finalize", "repair": "repair", "fallback": "fallback"},
        )
        graph.add_edge("repair", "validate_repair")
        graph.add_conditional_edges(
            "validate_repair",
            self._after_repair_validation,
            {"pass": "finalize", "fallback": "fallback"},
        )
        graph.add_edge("fallback", "finalize")
        graph.add_edge("finalize", END)
        return graph.compile()

    def _interpret(self, state: _GraphState) -> dict:
        signals = self.interpreter.interpret(state["graph_input"].student_message)
        learner_state = state["learner_state"].model_copy(deep=True)
        learner_state.latest_signals = signals
        if signals.confusion >= 0.7:
            learner_state.help_level = min(3, learner_state.help_level + 1)
        elif signals.attempt_present:
            learner_state.help_level = max(0, learner_state.help_level - 1)
        if signals.misconception_observed:
            marker = "latest-turn-stated-misconception"
            if marker not in learner_state.observed_misconceptions:
                learner_state.observed_misconceptions.append(marker)
        return {"signals": signals, "learner_state": learner_state}

    def _retrieve(self, state: _GraphState) -> dict:
        hits, events = self.retrieve(state["graph_input"])
        return {"hits": hits, "audit_events": [*state["audit_events"], *events]}

    def _select_intent(self, state: _GraphState) -> dict:
        signals = state["signals"]
        if signals is None:
            raise RuntimeError("intent selection requires turn signals")
        intent = self.selector.select(signals, state["learner_state"], state["hits"])
        evidence_intent = retrieval_boundary_intent(state["audit_events"])
        if evidence_intent is not None and intent != TutoringIntent.REFUSE_AND_REDIRECT:
            intent = evidence_intent
        return {"intent": intent}

    async def _generate(self, state: _GraphState) -> dict:
        answer, events = await self.generate(
            state["graph_input"],
            state["hits"],
            state["intent"],
            state["learner_state"].help_level,
            None,
        )
        return {"answer": answer, "audit_events": [*state["audit_events"], *events]}

    async def _repair(self, state: _GraphState) -> dict:
        answer, events = await self.generate(
            state["graph_input"],
            state["hits"],
            state["intent"],
            state["learner_state"].help_level,
            state["failure_reason"],
        )
        return {
            "answer": answer,
            "repair_count": 1,
            "audit_events": [*state["audit_events"], *events],
        }

    def _validate(self, state: _GraphState) -> dict:
        answer = state["answer"]
        reason = _validation_failure(answer, state["hits"])
        return {"validation_passed": reason is None, "failure_reason": reason}

    @staticmethod
    def _after_first_validation(state: _GraphState) -> str:
        if state["validation_passed"]:
            return "pass"
        answer = state["answer"]
        if answer is not None and answer.trace is not None and state["hits"]:
            return "repair"
        return "fallback"

    @staticmethod
    def _after_repair_validation(state: _GraphState) -> str:
        return "pass" if state["validation_passed"] else "fallback"

    def _fallback(self, state: _GraphState) -> dict:
        return {
            "answer": self.fallback(
                state["graph_input"], state["intent"], state["failure_reason"]
            ),
            "validation_passed": True,
        }

    def _finalize(self, state: _GraphState) -> dict:
        learner_state = state["learner_state"].model_copy(deep=True)
        signals = state["signals"]
        if signals is not None:
            learner_state = _update_mastery_from_turn(
                learner_state,
                signals,
                state["hits"],
            )
        learner_state.revision += 1
        learner_state.turn_count += 1
        learner_state.prior_intent = state["intent"]
        learner_state.next_activity = _next_activity(state["intent"])
        learner_state.updated_at = state["graph_input"].observed_at
        return {"learner_state": learner_state}


def initial_learner_state(
    conversation: Conversation,
    *,
    observed_at: str | None = None,
) -> LearnerState:
    return LearnerState(
        conversation_id=conversation.id,
        course_id=conversation.course_id,
        release_id=conversation.release_id,
        updated_at=observed_at or timestamp_now(),
    )


class _V2GraphState(TypedDict):
    event_id: str
    observed_at: str
    node_path: list[str]
    signals: TurnSignals | None
    perception: TurnPerceptionV2 | None
    concept_ids: list[str]
    observation: LearnerObservationV2 | None
    prior_belief_state: LearnerBeliefStateV2 | None
    belief_state: LearnerBeliefStateV2 | None
    state_delta: LearnerStateDeltaV2 | None
    learner_state: LearnerState
    hit_ids: list[str]
    evidence_keys: list[str]
    intent: str
    plan: PedagogicalPlanV2 | None
    semantic_proposal: ReactiveSemanticProposalV2 | None
    planning_calls: int
    answer: TutorAnswer | None
    audit_events: list[AuditEvent]
    repair_count: int
    validation_passed: bool
    failure_reason: str | None
    fast_path: bool


@dataclass
class _V2RuntimeContext:
    graph_input: TutoringGraphInput
    retrieve: RetrieveStep
    generate: GenerateStep
    fallback: FallbackStep
    hits: list[RetrievalHit] = field(default_factory=list)
    retrieval_events: list[AuditEvent] = field(default_factory=list)
    retrieval_loaded: bool = False

    def ensure_retrieval(self) -> tuple[list[RetrievalHit], list[AuditEvent]]:
        if not self.retrieval_loaded:
            self.hits, self.retrieval_events = self.retrieve(self.graph_input)
            self.retrieval_loaded = True
        return self.hits, self.retrieval_events


class GovernedReactiveTutoringGraphV2:
    """Independent V2.1 graph with sanitized node-level durable checkpoints."""

    implementation_id = "governed-reactive-tutoring-graph-v2.1"
    recursion_limit = 12

    def __init__(
        self,
        *,
        retrieve: RetrieveStep,
        generate: GenerateStep,
        fallback: FallbackStep,
        evidence_gate_configured: bool,
        claim_validator: PostGenerationClaimValidator,
        checkpoint_database_path: str,
        generator_model_id: str = "deterministic-grounded-generator",
        semantic_planner: ReactiveSemanticPlanner | None = None,
        interpreter: DeterministicTurnInterpreter | None = None,
        selector: DeterministicIntentSelector | None = None,
        belief_estimator: DeterministicEvidenceCountBeliefEstimator | None = None,
    ) -> None:
        if not evidence_gate_configured:
            raise ValueError("T1-v2 requires a selected evidence-sufficiency gate")
        if claim_validator is None:
            raise ValueError("T1-v2 requires an atomic-claim validator")
        if not checkpoint_database_path.strip():
            raise ValueError("T1-v2 requires a checkpoint database path")
        self.retrieve = retrieve
        self.generate = generate
        self.fallback = fallback
        self.claim_validator = claim_validator
        self.checkpoint_database_path = checkpoint_database_path
        self.generator_model_id = generator_model_id.strip()
        if not self.generator_model_id:
            raise ValueError("T1-v2 requires a requested generator model identity")
        self.semantic_planner = semantic_planner or DeterministicReactiveSemanticPlanner()
        self.interpreter = interpreter or DeterministicTurnInterpreter()
        self.selector = selector or DeterministicIntentSelector()
        self.belief_estimator = belief_estimator or DeterministicEvidenceCountBeliefEstimator()
        self._builder = self._build_graph()

    async def run(self, graph_input: TutoringGraphInput) -> TutoringGraphResult:
        if (
            graph_input.event_id is None
            or graph_input.learner_key is None
            or graph_input.domain_model is None
            or graph_input.learner_belief is None
        ):
            raise ValueError("T1-v2 input requires event, learner, domain, and belief bindings")
        context = _V2RuntimeContext(
            graph_input=graph_input,
            retrieve=self.retrieve,
            generate=self.generate,
            fallback=self.fallback,
        )
        initial: _V2GraphState = {
            "event_id": graph_input.event_id,
            "observed_at": graph_input.observed_at,
            "node_path": [],
            "signals": None,
            "perception": None,
            "concept_ids": [],
            "observation": None,
            "prior_belief_state": graph_input.learner_belief,
            "belief_state": graph_input.learner_belief,
            "state_delta": None,
            "learner_state": graph_input.learner_state.model_copy(deep=True),
            "hit_ids": [],
            "evidence_keys": [],
            "intent": TutoringIntent.CLARIFY_REQUEST,
            "plan": None,
            "semantic_proposal": None,
            "planning_calls": 0,
            "answer": None,
            "audit_events": [],
            "repair_count": 0,
            "validation_passed": False,
            "failure_reason": None,
            "fast_path": False,
        }
        config = {
            "configurable": {
                "thread_id": graph_input.event_id,
            },
            "recursion_limit": self.recursion_limit,
        }
        serializer = JsonPlusSerializer(
            allowed_msgpack_modules=[
                ("src.digital_twin.student.tutoring_graph", "TurnSignals"),
                ("src.digital_twin.student.tutoring_graph", "LearnerState"),
                ("src.digital_twin.student.autonomy_models", "AutonomousEventKind"),
                ("src.digital_twin.student.autonomy_models", "AssessmentOutcome"),
                ("src.digital_twin.student.autonomy_models", "AutonomousActionKind"),
                ("src.digital_twin.student.autonomy_models", "TurnPerceptionV2"),
                ("src.digital_twin.student.autonomy_models", "LearnerObservationV2"),
                ("src.digital_twin.student.autonomy_models", "ConceptAttributionV2"),
                ("src.digital_twin.student.autonomy_models", "LearnerHypothesisV2"),
                ("src.digital_twin.student.autonomy_models", "LearnerBeliefStateV2"),
                ("src.digital_twin.student.autonomy_models", "LearnerStateDeltaV2"),
                ("src.digital_twin.student.autonomy_models", "PedagogicalPlanV2"),
                ("src.digital_twin.student.autonomy_models", "ReactiveSemanticProposalV2"),
                ("src.digital_twin.student.autonomy_models", "LearnerHypothesisV2"),
                ("src.digital_twin.grounding.models", "TutorAnswer"),
                ("src.digital_twin.grounding.models", "GenerationTrace"),
                ("src.digital_twin.grounding.models", "GenerationUsage"),
                ("src.digital_twin.grounding.models", "SourceCitation"),
                ("src.digital_twin.grounding.models", "AtomicAnswerClaim"),
                ("src.digital_twin.student.models", "AuditEvent"),
            ]
        )
        async with aiosqlite.connect(self.checkpoint_database_path) as connection:
            saver = AsyncSqliteSaver(connection, serde=serializer)
            await saver.setup()
            graph = self._builder.compile(checkpointer=saver)
            snapshot = await graph.aget_state(config)
            restart_count = 0
            if snapshot.values:
                restart_count = 1
                if snapshot.next:
                    result = await graph.ainvoke(None, config=config, context=context)
                else:
                    result = snapshot.values
            else:
                result = await graph.ainvoke(initial, config=config, context=context)
            checkpoint_ids = []
            async for item in saver.alist(config, limit=32):
                checkpoint_id = item.config.get("configurable", {}).get("checkpoint_id")
                if checkpoint_id and checkpoint_id not in checkpoint_ids:
                    checkpoint_ids.append(str(checkpoint_id))

        answer = result["answer"]
        observation = result["observation"]
        belief = result["belief_state"]
        delta = result["state_delta"]
        plan = result["plan"]
        if any(item is None for item in (answer, observation, belief, plan)):
            raise RuntimeError("T1-v2 graph terminated without required artifacts")
        state_committed = result["failure_reason"] is None
        if state_committed and delta is None:
            raise RuntimeError("successful T1-v2 graph omitted its learner-state delta")
        # Reconstruct durable lineage from the already-authoritative citations.
        # This deliberately does not depend on the ephemeral retrieval context,
        # which is absent when a job resumes after a later node checkpoint.
        response = _grounded_response_v2(answer, plan)
        provider_trace = answer.trace
        usage = provider_trace.usage if provider_trace is not None else None
        generation_calls = await self._provider_generation_call_count(
            graph_input.event_id
        )
        trace = AgentTraceV2(
            trace_id=f"trace-{graph_input.event_id}",
            event_id=graph_input.event_id,
            learner_key=graph_input.learner_key,
            course_id=graph_input.conversation.course_id,
            release_id=graph_input.conversation.release_id,
            graph_version=self.implementation_id,
            policy_version=1,
            profile_sha256=(
                graph_input.release.teaching_profile_sha256 or "0" * 64
            ),
            planner_model=self.semantic_planner.model_id,
            generator_requested_model=self.generator_model_id,
            generator_model=provider_trace.provider_model if provider_trace else None,
            fast_path=bool(result["fast_path"]),
            planning_calls=result["planning_calls"],
            generation_calls=generation_calls,
            repair_calls=result["repair_count"],
            provider_input_tokens=usage.input_tokens if usage else 0,
            provider_output_tokens=usage.output_tokens if usage else 0,
            provider_cost_usd=(usage.approximate_cost_usd or 0) if usage else 0,
            provider_latency_ms=provider_trace.latency_ms if provider_trace else 0,
            input_state_revision=(
                delta.previous_revision if state_committed and delta is not None else belief.revision
            ),
            output_state_revision=(
                delta.next_revision if state_committed and delta is not None else belief.revision
            ),
            node_path=result["node_path"],
            checkpoint_ids=checkpoint_ids,
            restart_count=restart_count,
            decision_reason=result["failure_reason"] or plan.reason_code,
            validation_results={
                "graph-validation": bool(
                    result["validation_passed"] and state_committed
                ),
                "evidence-present": bool(result.get("evidence_keys")),
                "atomic-claim-validation": bool(
                    result["validation_passed"] and state_committed
                ),
            },
            started_at=graph_input.observed_at,
            completed_at=graph_input.observed_at,
        )
        artifacts = ReactiveTurnArtifactsV2(
            conversation_id=graph_input.conversation.id,
            observation=observation,
            state_committed=state_committed,
            belief_state=belief if state_committed else None,
            state_delta=delta if state_committed else None,
            plan=plan,
            response=response,
            trace=trace,
        )
        return TutoringGraphResult(
            answer=answer,
            hits=context.hits,
            audit_events=result["audit_events"],
            learner_state=result["learner_state"],
            intent=result["intent"],
            repair_count=result["repair_count"],
            validation_passed=result["validation_passed"],
            failure_reason=result["failure_reason"],
            reactive_v2_artifacts=artifacts,
        )

    async def _provider_generation_call_count(self, event_id: str) -> int:
        if self.generator_model_id.startswith("deterministic/"):
            return 0
        async with aiosqlite.connect(self.checkpoint_database_path) as connection:
            cursor = await connection.execute(
                """SELECT COUNT(*) FROM tutoring_model_calls_v2
                   WHERE event_id = ? AND stage IN ('generate', 'repair')""",
                (event_id,),
            )
            row = await cursor.fetchone()
        return min(1, int(row[0] if row is not None else 0))

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(_V2GraphState, context_schema=_V2RuntimeContext)
        graph.add_node("bind_scope", self._bind_scope)
        graph.add_node("perceive_turn", self._perceive_turn)
        graph.add_node("update_learner_belief", self._update_learner_belief)
        graph.add_node("retrieve_verify_evidence", self._retrieve_verify_evidence)
        graph.add_node("plan_pedagogy", self._plan_pedagogy)
        graph.add_node("generate", self._generate)
        graph.add_node("validate", self._validate)
        graph.add_node("repair", self._repair)
        graph.add_node("validate_repair", self._validate)
        graph.add_node("safe_fallback", self._safe_fallback)
        graph.add_node("atomic_commit_boundary", self._atomic_commit_boundary)
        graph.add_edge(START, "bind_scope")
        graph.add_edge("bind_scope", "perceive_turn")
        graph.add_edge("perceive_turn", "update_learner_belief")
        graph.add_edge("update_learner_belief", "retrieve_verify_evidence")
        graph.add_edge("retrieve_verify_evidence", "plan_pedagogy")
        graph.add_conditional_edges(
            "plan_pedagogy",
            self._after_plan,
            {"generate": "generate", "fallback": "safe_fallback"},
        )
        graph.add_edge("generate", "validate")
        graph.add_conditional_edges(
            "validate",
            self._after_first_validation,
            {"pass": "atomic_commit_boundary", "repair": "repair", "fallback": "safe_fallback"},
        )
        graph.add_edge("repair", "validate_repair")
        graph.add_conditional_edges(
            "validate_repair",
            self._after_repair_validation,
            {"pass": "atomic_commit_boundary", "fallback": "safe_fallback"},
        )
        graph.add_edge("safe_fallback", "atomic_commit_boundary")
        graph.add_edge("atomic_commit_boundary", END)
        return graph

    @staticmethod
    def _path(state: _V2GraphState, node: str) -> list[str]:
        return [*state["node_path"], node]

    def _bind_scope(self, state: _V2GraphState, runtime: Runtime[_V2RuntimeContext]) -> dict:
        graph_input = runtime.context.graph_input
        if graph_input.domain_model is None or graph_input.learner_belief is None:
            raise ValueError("T1-v2 scope is not fully bound")
        return {
            "node_path": [
                *state["node_path"],
                "bind_scope",
                "hard_policy_prefilter",
            ]
        }

    def _perceive_turn(
        self, state: _V2GraphState, runtime: Runtime[_V2RuntimeContext]
    ) -> dict:
        signals = self.interpreter.interpret(runtime.context.graph_input.student_message)
        perception = TurnPerceptionV2(
            event_kind="student-message",
            **signals.model_dump(mode="python"),
        )
        learner_state = state["learner_state"].model_copy(deep=True)
        learner_state.latest_signals = signals
        if signals.confusion >= 0.7:
            learner_state.help_level = min(3, learner_state.help_level + 1)
        elif signals.attempt_present:
            learner_state.help_level = max(0, learner_state.help_level - 1)
        updates = {
            "signals": signals,
            "perception": perception,
            "learner_state": learner_state,
            "node_path": self._path(state, "perceive_turn"),
        }
        observed = self._validate_observation({**state, **updates}, runtime)
        return {**updates, **observed}

    def _validate_observation(
        self, state: _V2GraphState, runtime: Runtime[_V2RuntimeContext]
    ) -> dict:
        graph_input = runtime.context.graph_input
        perception = state["perception"]
        if perception is None or graph_input.domain_model is None or graph_input.learner_key is None:
            raise RuntimeError("validated observation requires bound perception and domain")
        concept_ids = _attribute_concepts(
            graph_input.student_message,
            graph_input.domain_model,
        )
        source_turn_key = hashlib.sha256(
            f"{graph_input.release.id}:{state['event_id']}".encode("utf-8")
        ).hexdigest()
        assessment_outcome = graph_input.assessment_outcome
        assessment_confidence = graph_input.assessment_confidence
        if (
            assessment_outcome == AssessmentOutcome.NOT_ASSESSED
            and perception.attempt_present
        ):
            assessment_outcome, assessment_confidence = _assess_attempt(
                graph_input.student_message,
                concept_ids,
                graph_input.domain_model,
            )
        observation = LearnerObservationV2(
            observation_id=state["event_id"],
            learner_key=graph_input.learner_key,
            course_id=graph_input.conversation.course_id,
            release_id=graph_input.conversation.release_id,
            event_kind="student-message",
            concept_ids=concept_ids,
            perception=perception,
            assessment_outcome=assessment_outcome,
            assessment_confidence=assessment_confidence,
            source_turn_key=source_turn_key,
        )
        return {
            "concept_ids": concept_ids,
            "observation": observation,
            "node_path": self._path(state, "validate_observation"),
        }

    def _update_learner_belief(self, state: _V2GraphState) -> dict:
        observation = state["observation"]
        belief = state["belief_state"]
        if observation is None or belief is None:
            raise RuntimeError("belief update requires validated observation")
        next_belief, delta = self.belief_estimator.revise(belief, observation)
        updates = {
            "belief_state": next_belief,
            "state_delta": delta,
            "node_path": self._path(state, "update_learner_belief"),
        }
        constrained = self._merge_action_constraints({**state, **updates})
        return {**updates, **constrained}

    def _merge_action_constraints(self, state: _V2GraphState) -> dict:
        signals = state["signals"]
        if signals is None:
            raise RuntimeError("action constraints require turn perception")
        proposals = ["answer"]
        if signals.direct_solution_request:
            proposals.append("refuse")
        if signals.ambiguous:
            proposals.append("clarify")
        policy_action = resolve_policy_action(*proposals)
        if policy_action == "refuse":
            intent = TutoringIntent.REFUSE_AND_REDIRECT
        elif policy_action == "clarify":
            intent = TutoringIntent.CLARIFY_REQUEST
        else:
            intent = "pending-evidence"
        return {
            "intent": intent,
            "node_path": self._path(state, "merge_action_constraints"),
        }

    def _retrieve_verify_evidence(
        self, state: _V2GraphState, runtime: Runtime[_V2RuntimeContext]
    ) -> dict:
        hits, events = runtime.context.ensure_retrieval()
        signals = state["signals"]
        if signals is None:
            raise RuntimeError("retrieval requires turn perception")
        intent = state["intent"]
        if intent == "pending-evidence":
            intent = (
                retrieval_boundary_intent(events)
                or self.selector.select(signals, state["learner_state"], hits)
            )
        evidence_keys = [_source_range_key(hit) for hit in hits]
        return {
            "hit_ids": [hit.chunk.id for hit in hits],
            "evidence_keys": evidence_keys,
            "intent": intent,
            "audit_events": [*state["audit_events"], *events],
            "node_path": self._path(state, "retrieve_verify_evidence"),
        }

    async def _plan_pedagogy(
        self,
        state: _V2GraphState,
        runtime: Runtime[_V2RuntimeContext],
    ) -> dict:
        intent = state["intent"]
        signals = state["signals"]
        perception = state["perception"]
        belief = state["belief_state"]
        observation = state["observation"]
        if signals is None or perception is None or belief is None or observation is None:
            raise RuntimeError("pedagogical planning requires perception and belief")
        semantic_required = bool(
            intent not in {
                TutoringIntent.REFUSE_AND_REDIRECT,
                TutoringIntent.CLARIFY_REQUEST,
                TutoringIntent.ABSTAIN_NO_EVIDENCE,
            }
            and (
                signals.misconception_observed
                or signals.confusion >= 0.7
                or signals.attempt_present
            )
        )
        proposal = None
        planning_calls = 0
        if semantic_required:
            proposal, failure_reason = await self._semantic_plan_once(
                state,
                runtime,
                candidate_intent=intent,
            )
            planning_calls = int(
                not self.semantic_planner.model_id.startswith("deterministic/")
            )
            if proposal is None:
                return {
                    "failure_reason": failure_reason,
                    "plan": _failed_pedagogical_plan(failure_reason or "semantic-plan-failed"),
                    "planning_calls": planning_calls,
                    "fast_path": False,
                    "node_path": self._path(state, "plan_pedagogy"),
                }
            known_concepts = set(state["concept_ids"])
            if (
                not set(proposal.concept_ids).issubset(known_concepts)
                or proposal.hypothesis_concept_id not in known_concepts | {None}
            ):
                return {
                    "failure_reason": "semantic-plan-concept-out-of-scope",
                    "plan": _failed_pedagogical_plan(
                        "semantic-plan-concept-out-of-scope"
                    ),
                    "semantic_proposal": proposal,
                    "planning_calls": planning_calls,
                    "fast_path": False,
                    "node_path": self._path(state, "plan_pedagogy"),
                }
            intent = proposal.proposed_intent
            if proposal.hypothesis_kind and proposal.hypothesis_concept_id:
                hypothesis = LearnerHypothesisV2(
                    hypothesis_id=f"hypothesis-{state['event_id']}",
                    concept_id=proposal.hypothesis_concept_id,
                    kind=proposal.hypothesis_kind,
                    probability=proposal.hypothesis_confidence,
                    observation_ids=[state["event_id"]],
                    expires_at=(
                        datetime.fromisoformat(observation.observed_at)
                        .astimezone(UTC)
                        + timedelta(days=7)
                    ).isoformat(),
                )
                hypotheses = [
                    item
                    for item in belief.hypotheses
                    if item.hypothesis_id != hypothesis.hypothesis_id
                ]
                belief = belief.model_copy(
                    update={"hypotheses": [*hypotheses, hypothesis]}
                )
        action = _action_for_intent(intent)
        answer_allowed = intent not in {
            TutoringIntent.REFUSE_AND_REDIRECT,
            TutoringIntent.CLARIFY_REQUEST,
            TutoringIntent.ABSTAIN_NO_EVIDENCE,
        }
        plan = PedagogicalPlanV2(
            action=action,
            reason_code=f"intent-{intent.replace('_', '-')}",
            expected_learner_action=_next_activity(intent),
            required_evidence_keys=state["evidence_keys"] if answer_allowed else [],
            outcome_observation="Observe the learner's next durable course event.",
            stop_condition="Stop after one response and atomic state commit.",
            replan_condition="Replan only after a new event or due wake-up.",
        )
        fast_path = answer_allowed and not semantic_required
        return {
            "belief_state": belief,
            "intent": intent,
            "plan": plan,
            "semantic_proposal": proposal,
            "planning_calls": planning_calls,
            "fast_path": fast_path,
            "node_path": self._path(state, "plan_pedagogy"),
        }

    async def _semantic_plan_once(
        self,
        state: _V2GraphState,
        runtime: Runtime[_V2RuntimeContext],
        *,
        candidate_intent: str,
    ) -> tuple[ReactiveSemanticProposalV2 | None, str | None]:
        graph_input = runtime.context.graph_input
        perception = state["perception"]
        belief = state["belief_state"]
        if perception is None or belief is None:
            raise RuntimeError("semantic planning requires perception and belief")
        if self.semantic_planner.model_id.startswith("deterministic/"):
            proposal = await self.semantic_planner.propose(
                message=graph_input.student_message,
                perception=perception,
                concept_ids=state["concept_ids"],
                belief=belief,
                evidence_keys=state["evidence_keys"],
                candidate_intent=candidate_intent,
            )
            return proposal, None
        request_payload = {
            "event_id": state["event_id"],
            "message": graph_input.student_message,
            "perception": perception.model_dump(mode="json"),
            "concept_ids": state["concept_ids"],
            "belief_revision": belief.revision,
            "evidence_keys": state["evidence_keys"],
            "candidate_intent": candidate_intent,
            "planner_model": self.semantic_planner.model_id,
        }
        request_sha256 = hashlib.sha256(
            json.dumps(
                request_payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        stage = "semantic-plan"
        async with aiosqlite.connect(self.checkpoint_database_path) as connection:
            await connection.execute("BEGIN IMMEDIATE")
            cursor = await connection.execute(
                """SELECT request_sha256, status, output_json
                   FROM tutoring_model_calls_v2
                   WHERE event_id = ? AND stage = ?""",
                (state["event_id"], stage),
            )
            row = await cursor.fetchone()
            if row is not None:
                await connection.commit()
                if row[0] != request_sha256:
                    raise RuntimeError("T1-v2 semantic-plan resume binding changed")
                if row[1] == "completed" and row[2] is not None:
                    return ReactiveSemanticProposalV2.model_validate_json(row[2]), None
                return None, "operational-provider-call-outcome-uncertain"
            await connection.execute(
                """INSERT INTO tutoring_model_calls_v2(
                       event_id, stage, conversation_id, request_sha256, status,
                       started_at
                   ) VALUES (?, ?, ?, ?, 'started', ?)""",
                (
                    state["event_id"],
                    stage,
                    graph_input.conversation.id,
                    request_sha256,
                    graph_input.observed_at,
                ),
            )
            await connection.commit()
        try:
            proposal = await self.semantic_planner.propose(
                message=graph_input.student_message,
                perception=perception,
                concept_ids=state["concept_ids"],
                belief=belief,
                evidence_keys=state["evidence_keys"],
                candidate_intent=candidate_intent,
            )
        except Exception as error:
            async with aiosqlite.connect(self.checkpoint_database_path) as connection:
                await connection.execute(
                    """UPDATE tutoring_model_calls_v2
                       SET status = 'failed', failure_code = ?, completed_at = ?
                       WHERE event_id = ? AND stage = ?""",
                    (
                        type(error).__name__,
                        graph_input.observed_at,
                        state["event_id"],
                        stage,
                    ),
                )
                await connection.commit()
            return None, "operational-provider-failure"
        async with aiosqlite.connect(self.checkpoint_database_path) as connection:
            await connection.execute(
                """UPDATE tutoring_model_calls_v2
                   SET status = 'completed', output_json = ?, audit_events_json = '[]',
                       completed_at = ?
                   WHERE event_id = ? AND stage = ?""",
                (
                    proposal.model_dump_json(),
                    graph_input.observed_at,
                    state["event_id"],
                    stage,
                ),
            )
            await connection.commit()
        return proposal, None

    @staticmethod
    def _after_plan(state: _V2GraphState) -> str:
        return "fallback" if state["failure_reason"] else "generate"

    async def _generate(
        self, state: _V2GraphState, runtime: Runtime[_V2RuntimeContext]
    ) -> dict:
        graph_input = runtime.context.graph_input
        hits, _ = runtime.context.ensure_retrieval()
        if state["intent"] in {
            TutoringIntent.REFUSE_AND_REDIRECT,
            TutoringIntent.CLARIFY_REQUEST,
            TutoringIntent.ABSTAIN_NO_EVIDENCE,
        }:
            answer = deterministic_policy_boundary_answer(state["intent"])
            if answer is None:
                raise RuntimeError("policy boundary intent has no deterministic response")
            events: list[AuditEvent] = []
        else:
            answer, events, failure_reason = await self._generate_once(
                state,
                runtime,
                stage="generate",
                repair_reason=None,
            )
            if answer is None:
                answer = runtime.context.fallback(
                    graph_input,
                    state["intent"],
                    failure_reason,
                )
                events = []
        return {
            "answer": answer,
            "audit_events": [*state["audit_events"], *events],
            "failure_reason": (
                failure_reason if state["intent"] not in {
                    TutoringIntent.REFUSE_AND_REDIRECT,
                    TutoringIntent.CLARIFY_REQUEST,
                    TutoringIntent.ABSTAIN_NO_EVIDENCE,
                } else None
            ),
            "node_path": self._path(state, "generate"),
        }

    def _validate(
        self, state: _V2GraphState, runtime: Runtime[_V2RuntimeContext]
    ) -> dict:
        hits, _ = runtime.context.ensure_retrieval()
        reason = state["failure_reason"] or _validation_failure(state["answer"], hits)
        answer = state["answer"]
        if (
            reason is None
            and answer is not None
            and answer.trace is not None
            and answer.trace.policy_action == "answer"
        ):
            try:
                decision = self.claim_validator.validate(answer.atomic_claims, hits)
            except (RuntimeError, ValueError):
                reason = "atomic-claim-validator-failure"
            else:
                if not decision.releasable:
                    reason = "atomic-claim-lineage-invalid"
        return {
            "validation_passed": reason is None,
            "failure_reason": reason,
            "node_path": self._path(state, "validate"),
        }

    @staticmethod
    def _after_first_validation(state: _V2GraphState) -> str:
        if state["validation_passed"]:
            return "pass"
        if (state["failure_reason"] or "").startswith("operational-provider-"):
            return "fallback"
        answer = state["answer"]
        if answer is not None and answer.trace is not None and state["hit_ids"]:
            return "repair"
        return "fallback"

    async def _repair(
        self, state: _V2GraphState, runtime: Runtime[_V2RuntimeContext]
    ) -> dict:
        answer, events, failure_reason = await self._generate_once(
            state,
            runtime,
            stage="repair",
            repair_reason=state["failure_reason"],
        )
        if answer is None:
            answer = runtime.context.fallback(
                runtime.context.graph_input,
                state["intent"],
                failure_reason,
            )
        return {
            "answer": answer,
            "repair_count": 1,
            "audit_events": [*state["audit_events"], *events],
            "failure_reason": failure_reason,
            "node_path": self._path(state, "repair"),
        }

    async def _generate_once(
        self,
        state: _V2GraphState,
        runtime: Runtime[_V2RuntimeContext],
        *,
        stage: str,
        repair_reason: str | None,
    ) -> tuple[TutorAnswer | None, list[AuditEvent], str | None]:
        """Persist the call boundary so a restart never repeats an uncertain call.

        A completed result is replayed from the sanitized ledger. If a process
        disappears after reserving a call but before persisting its response,
        the next process fails closed instead of sending the request again.
        """

        graph_input = runtime.context.graph_input
        hits, _ = runtime.context.ensure_retrieval()
        request_sha256 = hashlib.sha256(
            json.dumps(
                {
                    "event_id": state["event_id"],
                    "stage": stage,
                    "message": graph_input.student_message,
                    "hit_ids": [hit.chunk.id for hit in hits],
                    "intent": state["intent"],
                    "help_level": state["learner_state"].help_level,
                    "repair_reason": repair_reason,
                    "generator_model": self.generator_model_id,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        async with aiosqlite.connect(self.checkpoint_database_path) as connection:
            await connection.execute("BEGIN IMMEDIATE")
            cursor = await connection.execute(
                """SELECT request_sha256, status, output_json, audit_events_json
                   FROM tutoring_model_calls_v2
                   WHERE event_id = ? AND stage = ?""",
                (state["event_id"], stage),
            )
            row = await cursor.fetchone()
            if row is not None:
                await connection.commit()
                if row[0] != request_sha256:
                    raise RuntimeError("T1-v2 model-call resume binding changed")
                if row[1] == "completed" and row[2] is not None:
                    answer = TutorAnswer.model_validate_json(row[2])
                    events = [
                        AuditEvent.model_validate(item)
                        for item in json.loads(row[3] or "[]")
                    ]
                    return answer, events, None
                return None, [], "operational-provider-call-outcome-uncertain"
            await connection.execute(
                """INSERT INTO tutoring_model_calls_v2(
                       event_id, stage, conversation_id, request_sha256, status,
                       started_at
                   ) VALUES (?, ?, ?, ?, 'started', ?)""",
                (
                    state["event_id"],
                    stage,
                    graph_input.conversation.id,
                    request_sha256,
                    graph_input.observed_at,
                ),
            )
            await connection.commit()
        try:
            answer, events = await runtime.context.generate(
                graph_input,
                hits,
                state["intent"],
                state["learner_state"].help_level,
                repair_reason,
            )
        except Exception as error:
            async with aiosqlite.connect(self.checkpoint_database_path) as connection:
                await connection.execute(
                    """UPDATE tutoring_model_calls_v2
                       SET status = 'failed', failure_code = ?, completed_at = ?
                       WHERE event_id = ? AND stage = ?""",
                    (
                        type(error).__name__,
                        graph_input.observed_at,
                        state["event_id"],
                        stage,
                    ),
                )
                await connection.commit()
            return None, [], "operational-provider-failure"
        async with aiosqlite.connect(self.checkpoint_database_path) as connection:
            await connection.execute(
                """UPDATE tutoring_model_calls_v2
                   SET status = 'completed', output_json = ?, audit_events_json = ?,
                       completed_at = ?
                   WHERE event_id = ? AND stage = ?""",
                (
                    answer.model_dump_json(),
                    json.dumps(
                        [event.model_dump(mode="json") for event in events],
                        sort_keys=True,
                    ),
                    graph_input.observed_at,
                    state["event_id"],
                    stage,
                ),
            )
            await connection.commit()
        return answer, events, None

    @staticmethod
    def _after_repair_validation(state: _V2GraphState) -> str:
        return "pass" if state["validation_passed"] else "fallback"

    def _safe_fallback(
        self, state: _V2GraphState, runtime: Runtime[_V2RuntimeContext]
    ) -> dict:
        answer = runtime.context.fallback(
            runtime.context.graph_input,
            state["intent"],
            state["failure_reason"],
        )
        return {
            "answer": answer,
            "validation_passed": True,
            "node_path": self._path(state, "safe_fallback"),
        }

    def _atomic_commit_boundary(self, state: _V2GraphState) -> dict:
        if state["failure_reason"] is not None:
            return {
                "belief_state": state["prior_belief_state"],
                "state_delta": None,
                "node_path": self._path(state, "atomic_commit_boundary"),
            }
        learner_state = state["learner_state"].model_copy(deep=True)
        learner_state.revision += 1
        learner_state.turn_count += 1
        learner_state.prior_intent = state["intent"]
        learner_state.next_activity = _next_activity(state["intent"])
        learner_state.updated_at = state["observed_at"]
        # V2 does not write mastery estimates into the historical V1 field.
        learner_state.mastery_by_concept = {}
        learner_state.objective_complete = False
        return {
            "learner_state": learner_state,
            "node_path": self._path(state, "atomic_commit_boundary"),
        }


def _attribute_concepts(
    message: str,
    domain_model: CourseDomainModelV1,
) -> list[str]:
    """Map a turn to approved concepts without allowing a model to invent IDs."""

    tokens = set(re.findall(r"[a-z0-9][a-z0-9_-]+", message.casefold()))
    ranked: list[tuple[int, str]] = []
    for concept in domain_model.concepts:
        concept_tokens = set(
            re.findall(
                r"[a-z0-9][a-z0-9_-]+",
                f"{concept.label} {concept.description}".casefold(),
            )
        )
        ranked.append((len(tokens & concept_tokens), concept.concept_id))
    selected = [concept_id for score, concept_id in sorted(ranked, reverse=True) if score > 0]
    if not selected:
        selected = list(domain_model.objectives[0].concept_ids)
    return selected[:3]


def _assess_attempt(
    message: str,
    concept_ids: list[str],
    domain_model: CourseDomainModelV1,
) -> tuple[AssessmentOutcome, float]:
    """Conservative lexical baseline for explicitly attempted explanations."""

    stopwords = {
        "about", "after", "also", "because", "from", "have", "into", "that",
        "their", "them", "then", "there", "these", "they", "this", "with",
    }
    observed = {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9_-]+", message.casefold())
        if len(token) >= 4 and token not in stopwords
    }
    expected: set[str] = set()
    selected = set(concept_ids)
    for concept in domain_model.concepts:
        if concept.concept_id not in selected:
            continue
        expected.update(
            token
            for token in re.findall(
                r"[a-z0-9][a-z0-9_-]+",
                f"{concept.label} {concept.description}".casefold(),
            )
            if len(token) >= 4 and token not in stopwords
        )
    if not expected:
        return AssessmentOutcome.NOT_ASSESSED, 0
    overlap = len(observed & expected) / len(expected)
    if overlap >= 0.45:
        return AssessmentOutcome.CORRECT, min(0.95, 0.6 + overlap / 3)
    if overlap >= 0.20:
        return AssessmentOutcome.PARTIAL, min(0.80, 0.4 + overlap)
    return AssessmentOutcome.INCORRECT, 0.65


def _source_range_key(hit: RetrievalHit) -> str:
    chunk = hit.chunk
    return ":".join(
        (
            chunk.source_artifact_id or chunk.document_id,
            str(chunk.source_version),
            chunk.source_checksum or chunk.content_hash or "missing-checksum",
            chunk.locator or f"chunk {chunk.ordinal + 1}",
        )
    )


def _action_for_intent(intent: str) -> AutonomousActionKind:
    return {
        TutoringIntent.CLARIFY_REQUEST: AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
        TutoringIntent.DIAGNOSE_UNDERSTANDING: AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
        TutoringIntent.ASK_NEXT_STEP: AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
        TutoringIntent.PROMPT_SELF_EXPLANATION: AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
        TutoringIntent.GIVE_HINT: AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE,
        TutoringIntent.GIVE_ANALOGY_OR_EXAMPLE: AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE,
        TutoringIntent.CORRECT_MISCONCEPTION: AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE,
        TutoringIntent.EXPLAIN_CONCEPT: AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE,
        TutoringIntent.CHECK_UNDERSTANDING: AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
        TutoringIntent.GIVE_RETRIEVAL_PRACTICE: AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE,
        TutoringIntent.SUMMARIZE_PROGRESS: AutonomousActionKind.SUMMARIZE_PROGRESS,
        TutoringIntent.REFUSE_AND_REDIRECT: AutonomousActionKind.NO_ACTION,
        TutoringIntent.ABSTAIN_NO_EVIDENCE: AutonomousActionKind.NO_ACTION,
    }.get(intent, AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE)


def _failed_pedagogical_plan(reason: str) -> PedagogicalPlanV2:
    return PedagogicalPlanV2(
        action=AutonomousActionKind.NO_ACTION,
        reason_code=reason,
        stop_condition="Stop without advancing learner state.",
        replan_condition="Wait for a new durable event.",
    )


def _grounded_response_v2(
    answer: TutorAnswer,
    plan: PedagogicalPlanV2,
) -> GroundedTutorResponseV2:
    raw_action = answer.trace.policy_action if answer.trace is not None else "no-action"
    policy_action = {
        "answer": "answer",
        "clarify": "clarify",
        "clarify-request": "clarify",
        "no-evidence": "abstain",
        "abstain": "abstain",
        "redirect-graded-work": "refuse",
        "refuse": "refuse",
    }.get(raw_action, "no-action")
    if policy_action != "answer":
        return GroundedTutorResponseV2(
            action=plan.action,
            content=answer.content,
            policy_action=policy_action,
        )
    return GroundedTutorResponseV2(
        action=plan.action,
        content=answer.content,
        atomic_claims=[claim.text for claim in answer.atomic_claims],
        citation_ids=[
            f"{citation.source_artifact_id or citation.source_id}:{citation.locator}"
            for citation in answer.citations
        ],
        source_range_keys=[
            ":".join(
                (
                    citation.source_artifact_id or citation.source_id,
                    str(citation.source_version or 1),
                    citation.source_checksum or "missing-checksum",
                    citation.locator,
                )
            )
            for citation in answer.citations
        ],
        policy_action="answer",
    )


def _update_mastery_from_turn(
    learner_state: LearnerState,
    signals: TurnSignals,
    hits: list[RetrievalHit],
) -> LearnerState:
    """Update a conservative, observable learner estimate without model authority."""

    if not hits or signals.ambiguous or signals.direct_solution_request:
        learner_state.objective_complete = False
        return learner_state
    if signals.misconception_observed:
        observed_mastery = 0.15
    elif signals.confusion >= 0.7:
        observed_mastery = 0.30
    elif signals.attempt_present:
        observed_mastery = 0.85
    else:
        observed_mastery = 0.55
    concept_ids: list[str] = []
    for hit in hits[:3]:
        concept_id = (hit.chunk.source_artifact_id or hit.chunk.document_id)[:128]
        if concept_id in concept_ids:
            continue
        concept_ids.append(concept_id)
        prior = learner_state.mastery_by_concept.get(concept_id, ConceptMastery())
        count = prior.observation_count + 1
        estimate = (
            prior.estimate * prior.observation_count + observed_mastery
        ) / count
        confidence = min(1.0, prior.confidence + 0.30)
        learner_state.mastery_by_concept[concept_id] = ConceptMastery(
            estimate=estimate,
            confidence=confidence,
            observation_count=count,
        )
        if concept_id not in learner_state.concept_ids:
            learner_state.concept_ids.append(concept_id)
    learner_state.learning_objective = (
        learner_state.learning_objective
        or (f"Develop source-grounded understanding of {concept_ids[0]}" if concept_ids else None)
    )
    learner_state.objective_complete = bool(
        signals.attempt_present
        and signals.confusion < 0.40
        and not signals.misconception_observed
        and any(
            mastery.estimate >= 0.80
            and mastery.confidence >= 0.60
            and mastery.observation_count >= 2
            for concept_id, mastery in learner_state.mastery_by_concept.items()
            if concept_id in concept_ids
        )
    )
    return learner_state


def _validation_failure(
    answer: TutorAnswer | None,
    hits: list[RetrievalHit],
) -> str | None:
    if answer is None or not answer.content.strip() or answer.trace is None:
        return "invalid-response-contract"
    if answer.trace.policy_action.startswith("safe-"):
        return "operational-provider-failure"
    if answer.trace.policy_action == "answer":
        if not answer.citations:
            return "answer-missing-citation"
        for citation in answer.citations:
            matches = [
                hit for hit in hits if citation_matches_chunk(citation, hit.chunk)
            ]
            if len(matches) != 1:
                return "citation-not-in-presented-evidence"
    elif answer.citations:
        return "non-answer-returned-citations"
    return None


@lru_cache(maxsize=32)
def _next_activity(intent: str) -> str:
    return {
        TutoringIntent.CLARIFY_REQUEST: "clarify the learning request",
        TutoringIntent.DIAGNOSE_UNDERSTANDING: "respond to the diagnostic prompt",
        TutoringIntent.ASK_NEXT_STEP: "show the next reasoning step",
        TutoringIntent.GIVE_HINT: "apply the hint",
        TutoringIntent.CORRECT_MISCONCEPTION: "restate the corrected concept",
        TutoringIntent.EXPLAIN_CONCEPT: "check the explanation against the question",
        TutoringIntent.CHECK_UNDERSTANDING: "answer the understanding check",
        TutoringIntent.REFUSE_AND_REDIRECT: "share an attempt for bounded help",
        TutoringIntent.ABSTAIN_NO_EVIDENCE: "ask the instructor or refine the question",
    }.get(intent, "continue the current learning objective")
