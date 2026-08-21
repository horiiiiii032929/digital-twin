"""Bounded learner-state and pedagogical-intent orchestration for T1 tutoring."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.digital_twin.generation import citation_matches_chunk
from src.digital_twin.grounding.models import RetrievalHit, TutorAnswer
from src.digital_twin.student.models import (
    AuditEvent,
    Conversation,
    DigitalTwinRelease,
)
from src.digital_twin.tutor_policy import timestamp_now


class TutoringMode(str):
    """Stable runtime labels without coupling domain code to API settings."""

    T0 = "grounded-assistant"
    T1 = "bounded-tutoring-graph"


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

    @model_validator(mode="after")
    def authoritative_scope_must_match(self) -> "TutoringGraphInput":
        if (
            self.conversation.student_id != self.account_id
            or self.conversation.course_id != self.release.course_id
            or self.conversation.release_id != self.release.id
            or self.learner_state.conversation_id != self.conversation.id
            or self.learner_state.course_id != self.conversation.course_id
            or self.learner_state.release_id != self.conversation.release_id
        ):
            raise ValueError("tutoring graph input has inconsistent scope")
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
        if not hits:
            return TutoringIntent.ABSTAIN_NO_EVIDENCE
        if signals.ambiguous:
            return TutoringIntent.CLARIFY_REQUEST
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
        learner_state.revision += 1
        learner_state.turn_count += 1
        learner_state.prior_intent = state["intent"]
        learner_state.next_activity = _next_activity(state["intent"])
        learner_state.updated_at = timestamp_now()
        return {"learner_state": learner_state}


def initial_learner_state(conversation: Conversation) -> LearnerState:
    return LearnerState(
        conversation_id=conversation.id,
        course_id=conversation.course_id,
        release_id=conversation.release_id,
    )


def _validation_failure(
    answer: TutorAnswer | None,
    hits: list[RetrievalHit],
) -> str | None:
    if answer is None or not answer.content.strip() or answer.trace is None:
        return "invalid-response-contract"
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
