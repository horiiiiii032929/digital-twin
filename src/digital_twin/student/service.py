from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from src.digital_twin.evaluation import ComponentKind, load_release_profile
from src.digital_twin.generation import (
    DeterministicGroundedGenerator,
    citation_matches_chunk,
)
from src.digital_twin.grounding import (
    FallbackRetriever,
    RetrievalIndexError,
    RetrievalIndexStoreV1,
    build_retrieval_index_binding,
    build_selected_retriever,
)
from src.digital_twin.grounding.models import (
    GenerationTrace,
    GenerationUsage,
    RetrievalHit,
    TutorAnswer,
)
from src.digital_twin.grounding.protocols import (
    EvidenceSufficiencyGate,
    PostGenerationClaimValidator,
    TextEmbedder,
    TutorGenerator,
)
from src.digital_twin.student.models import (
    Account,
    AccountRole,
    AccountStatus,
    AuditEvent,
    Citation,
    Conversation,
    ConversationView,
    Course,
    DigitalTwinRelease,
    MembershipRole,
    Message,
    StudentCourse,
    StudentReleaseStatus,
    TutorTurn,
)
from src.digital_twin.student.learning_gap import (
    LearningGapEvidenceStatus,
    LearningGapPrivacyPolicyV1,
    LearningGapPseudonymizer,
    LearningGapSignalKind,
    LearningGapSignalV1,
    build_learning_gap_signal,
)
from src.digital_twin.student.repository import DuplicateTurnError, StudentRepository
from src.digital_twin.student.repository import LearnerStateConflictError
from src.digital_twin.student.tutoring_graph import (
    BoundedTutoringGraph,
    LearnerState,
    TutoringGraphInput,
    TutoringIntent,
    TutoringMode,
    initial_learner_state,
)
from src.digital_twin.tutor_policy import timestamp_now


class StudentWorkflowError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class StudentTutoringService:
    def __init__(
        self,
        repository: StudentRepository,
        *,
        profile_path: Path,
        embedder: TextEmbedder | None = None,
        generator: TutorGenerator | None = None,
        evidence_gate: EvidenceSufficiencyGate | None = None,
        claim_evidence_validator: PostGenerationClaimValidator | None = None,
        tutoring_mode: str = TutoringMode.T0,
        retrieval_index_store: RetrievalIndexStoreV1 | None = None,
        retrieval_index_chunker_id: str = "page-bounded-heading-paragraph-chunker",
        retrieval_index_chunker_version: str = "v1",
        learning_gap_pseudonymizer: LearningGapPseudonymizer | None = None,
        learning_gap_policy: LearningGapPrivacyPolicyV1 | None = None,
    ) -> None:
        self.repository = repository
        profile = load_release_profile(profile_path)
        self.profile_id = profile.profile_id
        self.profile_version = profile.profile_version
        self.retriever_selection = next(
            entry
            for entry in profile.components
            if entry.component == ComponentKind.RETRIEVER
        )
        self.embedder = embedder
        self.generator = generator or DeterministicGroundedGenerator()
        self.evidence_gate = evidence_gate
        self.claim_evidence_validator = claim_evidence_validator
        self.retrieval_index_store = retrieval_index_store
        self.retrieval_index_chunker_id = retrieval_index_chunker_id
        self.retrieval_index_chunker_version = retrieval_index_chunker_version
        self.learning_gap_pseudonymizer = learning_gap_pseudonymizer
        self.learning_gap_policy = learning_gap_policy or LearningGapPrivacyPolicyV1()
        if tutoring_mode not in {TutoringMode.T0, TutoringMode.T1}:
            raise ValueError("unsupported student tutoring mode")
        self.tutoring_mode = tutoring_mode
        self._retrievers: dict[str, object] = {}
        self._retrieval_artifact_ids: dict[str, str] = {}
        self.tutoring_graph = (
            BoundedTutoringGraph(
                retrieve=self._graph_retrieve,
                generate=self._graph_generate,
                fallback=self._graph_fallback,
            )
            if self.tutoring_mode == TutoringMode.T1
            else None
        )

    def list_courses(self, account_id: str) -> list[StudentCourse]:
        self._require_student(account_id)
        return [
            StudentCourse(
                course_id=course.id,
                title=course.title,
                release_id=release.id,
                profile_id=release.profile_id,
                profile_version=release.profile_version,
            )
            for course, release in self.repository.list_student_courses(account_id)
        ]

    def create_conversation(self, account_id: str, course_id: str) -> Conversation:
        self._authorize_course(account_id, course_id)
        release = self.repository.get_published_release(course_id)
        if release is None:
            self._deny(
                "release_unavailable",
                "The course Digital Twin is not published.",
                account_id=account_id,
                course_id=course_id,
            )
        self._require_matching_profile(release)
        conversation = Conversation(
            id=f"conversation-{uuid4()}",
            student_id=account_id,
            course_id=course_id,
            release_id=release.id,
        )
        saved = self.repository.save_conversation(conversation)
        self.repository.save_audit_event(
            self._event(
                "conversation-created",
                account_id=account_id,
                course_id=course_id,
                release_id=release.id,
                conversation_id=saved.id,
                details={"profile_version": release.profile_version},
            )
        )
        return saved

    def get_conversation(
        self, account_id: str, conversation_id: str
    ) -> ConversationView:
        conversation = self._authorize_conversation(account_id, conversation_id)
        return ConversationView(
            conversation=conversation,
            messages=self.repository.list_messages(conversation.id),
        )

    async def submit_message(
        self,
        account_id: str,
        conversation_id: str,
        *,
        content: str,
        client_request_id: str,
    ) -> TutorTurn:
        content = content.strip()
        client_request_id = client_request_id.strip()
        if not content or not client_request_id:
            raise StudentWorkflowError(
                "invalid_message", "Message content and request ID are required."
            )
        conversation = self._authorize_conversation(account_id, conversation_id)
        existing = self.repository.find_turn(conversation.id, client_request_id)
        if existing is not None:
            student_message, tutor_message, citations = existing
            if student_message.content != content:
                self._deny(
                    "request_id_conflict",
                    "The request ID is already bound to a different student message.",
                    account_id=account_id,
                    course_id=conversation.course_id,
                    release_id=conversation.release_id,
                    conversation_id=conversation.id,
                )
            return TutorTurn(
                student_message=student_message,
                tutor_message=tutor_message,
                citations=citations,
                duplicate=True,
                tutoring_mode=tutor_message.tutoring_mode,
                tutoring_intent=tutor_message.tutoring_intent,
                learner_state_revision=tutor_message.learner_state_revision,
            )
        release = self._require_current_release(conversation, account_id)
        tutoring_intent: str | None = None
        learner_state: LearnerState | None = None
        expected_learner_state_revision: int | None = None
        if self.tutoring_graph is None:
            hits, retrieval_events = self._retrieve(
                release,
                account_id=account_id,
                conversation=conversation,
                question=content,
            )
            answer, generation_events = await self._generate(
                release,
                hits,
                content,
                account_id=account_id,
                conversation=conversation,
            )
        else:
            prior_state = self.repository.get_learner_state(conversation.id)
            if prior_state is None:
                prior_state = initial_learner_state(conversation)
            expected_learner_state_revision = prior_state.revision
            graph_result = await self.tutoring_graph.run(
                TutoringGraphInput(
                    account_id=account_id,
                    conversation=conversation,
                    release=release,
                    student_message=content,
                    learner_state=prior_state,
                )
            )
            hits = graph_result.hits
            retrieval_events = []
            generation_events = [
                *graph_result.audit_events,
                self._event(
                    "tutoring-graph-completed",
                    account_id=account_id,
                    course_id=conversation.course_id,
                    release_id=release.id,
                    conversation_id=conversation.id,
                    details={
                        "implementation": self.tutoring_graph.implementation_id,
                        "intent": graph_result.intent,
                        "repair_count": graph_result.repair_count,
                        "validation_passed": graph_result.validation_passed,
                        "failure_reason": graph_result.failure_reason,
                    },
                ),
            ]
            answer = graph_result.answer
            learner_state = graph_result.learner_state
            tutoring_intent = graph_result.intent
        answer, claim_validation_events = self._validate_answer_claims(
            answer,
            hits,
            account_id=account_id,
            conversation=conversation,
        )
        generation_events.extend(claim_validation_events)
        now = timestamp_now()
        student_message = Message(
            id=f"message-{uuid4()}",
            conversation_id=conversation.id,
            role="student",
            content=content,
            action="question",
            client_request_id=client_request_id,
            tutoring_mode=self.tutoring_mode,
            created_at=now,
        )
        tutor_message = Message(
            id=f"message-{uuid4()}",
            conversation_id=conversation.id,
            role="tutor",
            content=answer.content,
            action=answer.trace.policy_action if answer.trace else "safe-failure",
            trace=answer.trace,
            response_to_message_id=student_message.id,
            tutoring_mode=self.tutoring_mode,
            tutoring_intent=tutoring_intent,
            learner_state_revision=(
                learner_state.revision if learner_state is not None else None
            ),
            created_at=now,
        )
        citations, citation_failure = self._citations(
            answer,
            hits,
            tutor_message,
            conversation,
        )
        if citation_failure:
            tutor_message = self._safe_failure_message(
                tutor_message,
                "The tutor could not validate its source citations. Please try again.",
            )
            citations = []
            generation_events.append(
                self._event(
                    "citation-validation-failure",
                    account_id=account_id,
                    course_id=conversation.course_id,
                    release_id=release.id,
                    conversation_id=conversation.id,
                    details={"failure_type": "citation-not-in-presented-evidence"},
                )
            )
        conversation.updated_at = now
        completed = self._event(
            "student-turn-completed",
            account_id=account_id,
            course_id=conversation.course_id,
            release_id=release.id,
            conversation_id=conversation.id,
            details={
                "action": tutor_message.action,
                "citation_count": len(citations),
                "generator_id": (
                    tutor_message.trace.generator_id
                    if tutor_message.trace
                    else "safe-failure"
                ),
                "tutoring_mode": self.tutoring_mode,
                "tutoring_intent": tutoring_intent,
            },
        )
        learning_gap_signal = self._learning_gap_signal(
            account_id=account_id,
            conversation=conversation,
            tutor_message=tutor_message,
            hits=hits,
            learner_state=learner_state,
            tutoring_intent=tutoring_intent,
            observed_at=now,
        )
        try:
            self.repository.save_turn(
                conversation,
                student_message,
                tutor_message,
                citations,
                [*retrieval_events, *generation_events, completed],
                learner_state,
                expected_learner_state_revision,
                learning_gap_signal,
            )
        except DuplicateTurnError:
            existing = self.repository.find_turn(conversation.id, client_request_id)
            if existing is None:
                raise StudentWorkflowError(
                    "turn_persistence_conflict",
                    "The concurrent request could not be resolved safely.",
                )
            stored_student, stored_tutor, stored_citations = existing
            if stored_student.content != content:
                self._deny(
                    "request_id_conflict",
                    "The request ID is already bound to a different student message.",
                    account_id=account_id,
                    course_id=conversation.course_id,
                    release_id=conversation.release_id,
                    conversation_id=conversation.id,
                )
            return TutorTurn(
                student_message=stored_student,
                tutor_message=stored_tutor,
                citations=stored_citations,
                duplicate=True,
                tutoring_mode=stored_tutor.tutoring_mode,
                tutoring_intent=stored_tutor.tutoring_intent,
                learner_state_revision=stored_tutor.learner_state_revision,
            )
        except LearnerStateConflictError as error:
            raise StudentWorkflowError(
                "learner_state_conflict",
                "Another tutoring turn advanced this conversation. Please resend.",
            ) from error
        return TutorTurn(
            student_message=student_message,
            tutor_message=tutor_message,
            citations=citations,
            tutoring_mode=self.tutoring_mode,
            tutoring_intent=tutoring_intent,
            learner_state_revision=(
                learner_state.revision if learner_state is not None else None
            ),
        )

    def _learning_gap_signal(
        self,
        *,
        account_id: str,
        conversation: Conversation,
        tutor_message: Message,
        hits: list[RetrievalHit],
        learner_state: LearnerState | None,
        tutoring_intent: str | None,
        observed_at: str,
    ) -> LearningGapSignalV1 | None:
        """Build a content-free T1 signal that commits atomically with the turn."""

        if (
            self.tutoring_mode != TutoringMode.T1
            or self.learning_gap_pseudonymizer is None
            or learner_state is None
            or tutoring_intent is None
            or learner_state.latest_signals is None
        ):
            return None
        signals = learner_state.latest_signals
        action = tutor_message.action
        if action == "redirect-graded-work":
            signal_kind = LearningGapSignalKind.INTEGRITY_REDIRECT
            evidence_status = LearningGapEvidenceStatus.REFUSED
        elif action == "no-evidence" or not hits:
            signal_kind = LearningGapSignalKind.NO_EVIDENCE
            evidence_status = LearningGapEvidenceStatus.NO_EVIDENCE
        elif action.startswith("safe-"):
            signal_kind = LearningGapSignalKind.VALIDATION_FALLBACK
            evidence_status = LearningGapEvidenceStatus.VALIDATION_FALLBACK
        elif signals.misconception_observed:
            signal_kind = LearningGapSignalKind.MISCONCEPTION
            evidence_status = LearningGapEvidenceStatus.SUPPORTED
        elif signals.confusion >= 0.7:
            signal_kind = (
                LearningGapSignalKind.REPEATED_HELP
                if learner_state.help_level >= 2
                else LearningGapSignalKind.CONFUSION
            )
            evidence_status = LearningGapEvidenceStatus.SUPPORTED
        else:
            return None
        if hits:
            source_identity = hits[0].chunk.source_artifact_id or hits[0].chunk.document_id
            topic_key = "source-" + hashlib.sha256(
                source_identity.encode("utf-8")
            ).hexdigest()[:16]
        else:
            topic_key = "course-boundary"
        return build_learning_gap_signal(
            pseudonymizer=self.learning_gap_pseudonymizer,
            policy=self.learning_gap_policy,
            account_id=account_id,
            tutor_message_id=tutor_message.id,
            course_id=conversation.course_id,
            release_id=conversation.release_id,
            topic_key=topic_key,
            signal_kind=signal_kind,
            tutoring_intent=tutoring_intent.replace("_", "-"),
            help_level=learner_state.help_level,
            confusion=signals.confusion,
            evidence_status=evidence_status,
            observed_at=observed_at,
        )

    def list_citations(self, account_id: str, message_id: str) -> list[Citation]:
        message = self.repository.get_message(message_id)
        if message is None or message.role != "tutor":
            raise StudentWorkflowError("message_not_found", "Message was not found.")
        conversation = self._authorize_conversation(account_id, message.conversation_id)
        citations = self.repository.list_citations(message.id)
        if any(
            citation.course_id != conversation.course_id
            or citation.release_id != conversation.release_id
            for citation in citations
        ):
            self._deny(
                "citation_scope_violation",
                "Citation scope does not match the conversation.",
                account_id=account_id,
                course_id=conversation.course_id,
                release_id=conversation.release_id,
                conversation_id=conversation.id,
            )
        return citations

    def _require_student(self, account_id: str) -> Account:
        account = self.repository.get_account(account_id)
        if account is None:
            raise StudentWorkflowError("account_not_found", "Account was not found.")
        if account.status != AccountStatus.ACTIVE:
            self._deny(
                "account_inactive",
                "The account is inactive or revoked.",
                account_id=account.id,
            )
        if account.role != AccountRole.STUDENT:
            self._deny(
                "student_role_required",
                "A student account is required.",
                account_id=account.id,
            )
        return account

    def _authorize_course(self, account_id: str, course_id: str) -> Course:
        self._require_student(account_id)
        course = self.repository.get_course(course_id)
        membership = self.repository.get_membership(account_id, course_id)
        if (
            course is None
            or membership is None
            or not membership.active
            or membership.role != MembershipRole.STUDENT
        ):
            self._deny(
                "course_access_denied",
                "The student is not assigned to this course.",
                account_id=account_id,
                course_id=course_id,
            )
        return course

    def _authorize_conversation(
        self, account_id: str, conversation_id: str
    ) -> Conversation:
        self._require_student(account_id)
        conversation = self.repository.get_conversation(conversation_id)
        if conversation is None or conversation.student_id != account_id:
            self._deny(
                "conversation_access_denied",
                "The conversation is not available to this student.",
                account_id=account_id,
                conversation_id=conversation_id,
            )
        self._authorize_course(account_id, conversation.course_id)
        return conversation

    def _require_current_release(
        self, conversation: Conversation, account_id: str
    ) -> DigitalTwinRelease:
        release = self.repository.get_release(conversation.release_id)
        current_release = self.repository.get_published_release(conversation.course_id)
        if (
            release is None
            or release.course_id != conversation.course_id
            or release.status != StudentReleaseStatus.PUBLISHED
            or current_release is None
            or current_release.id != release.id
        ):
            self._deny(
                "release_unavailable",
                "The Digital Twin release has been withdrawn or replaced.",
                account_id=account_id,
                course_id=conversation.course_id,
                release_id=conversation.release_id,
                conversation_id=conversation.id,
            )
        self._require_matching_profile(release)
        return release

    def _require_matching_profile(self, release: DigitalTwinRelease) -> None:
        if (
            release.profile_id != self.profile_id
            or release.profile_version != self.profile_version
        ):
            raise StudentWorkflowError(
                "profile_mismatch",
                "The published release does not match the active component profile.",
            )

    def _retrieve(
        self,
        release: DigitalTwinRelease,
        *,
        account_id: str,
        conversation: Conversation,
        question: str,
    ) -> tuple[list[RetrievalHit], list[AuditEvent]]:
        if not question.strip():
            return [], []
        retriever = self._retrievers.get(release.id)
        if retriever is None:
            active_versions: dict[str, int] = {}
            for chunk in release.chunks:
                source_id = chunk.source_artifact_id or chunk.document_id
                active_versions[source_id] = max(
                    chunk.source_version,
                    active_versions.get(source_id, 0),
                )
            if self.retrieval_index_store is not None:
                try:
                    if self.embedder is None:
                        raise RetrievalIndexError(
                            "published dense index requires a query embedder"
                        )
                    implementation = self.retriever_selection.implementation
                    if implementation is None:
                        raise RetrievalIndexError(
                            "published dense index requires a selected retriever"
                        )
                    binding = build_retrieval_index_binding(
                        course_id=release.course_id,
                        release_id=release.id,
                        profile_id=release.profile_id,
                        profile_version=release.profile_version,
                        chunker_id=self.retrieval_index_chunker_id,
                        chunker_version=self.retrieval_index_chunker_version,
                        chunks=release.chunks,
                        configuration=implementation.configuration,
                    )
                    loaded = self.retrieval_index_store.load_bound(
                        binding,
                        self.embedder,
                    )
                    retriever = loaded.retriever
                    self._retrieval_artifact_ids[release.id] = (
                        loaded.manifest.artifact_id
                    )
                except RetrievalIndexError as error:
                    return [], [
                        self._event(
                            "retrieval-index-unavailable",
                            account_id=account_id,
                            course_id=conversation.course_id,
                            release_id=release.id,
                            conversation_id=conversation.id,
                            details={"failure_type": type(error).__name__},
                        )
                    ]
            else:
                retriever = build_selected_retriever(
                    self.retriever_selection,
                    release.chunks,
                    active_source_versions=active_versions,
                    embedder=self.embedder,
                )
            self._retrievers[release.id] = retriever
        fallback_before = (
            retriever.fallback_count if isinstance(retriever, FallbackRetriever) else 0
        )
        hits = retriever.retrieve(question, limit=5)
        events: list[AuditEvent] = []
        fallback_used = (
            isinstance(retriever, FallbackRetriever)
            and retriever.fallback_count > fallback_before
        )
        primary_available = (
            retriever.primary_available
            if isinstance(retriever, FallbackRetriever)
            else True
        )
        retrieval_details: dict[str, str | int | float | bool | None] = {
            "implementation": (
                retriever.fallback_implementation_id
                if isinstance(retriever, FallbackRetriever)
                and (fallback_used or not primary_available)
                else retriever.primary_implementation_id
                if isinstance(retriever, FallbackRetriever)
                else getattr(retriever, "implementation_id", "retriever")
            ),
            "primary_available": primary_available,
            "hit_count": len(hits),
        }
        artifact_id = self._retrieval_artifact_ids.get(release.id)
        if artifact_id is not None:
            retrieval_details["index_artifact_id"] = artifact_id
        events.append(
            self._event(
                "retrieval-completed",
                account_id=account_id,
                course_id=conversation.course_id,
                release_id=release.id,
                conversation_id=conversation.id,
                details=retrieval_details,
            )
        )
        if isinstance(retriever, FallbackRetriever) and fallback_used:
            events.append(
                self._event(
                    "retrieval-fallback",
                    account_id=account_id,
                    course_id=conversation.course_id,
                    release_id=release.id,
                    conversation_id=conversation.id,
                    details={
                        "primary": retriever.primary_implementation_id,
                        "fallback": retriever.fallback_implementation_id,
                        "failure_type": retriever.last_failure_type,
                    },
                )
            )
        if self.evidence_gate is None:
            events.append(
                self._event(
                    "evidence-sufficiency-blocked",
                    account_id=account_id,
                    course_id=conversation.course_id,
                    release_id=release.id,
                    conversation_id=conversation.id,
                    details={
                        "implementation": "unselected",
                        "candidate_hit_count": len(hits),
                        "sufficient": False,
                    },
                )
            )
            return [], events
        try:
            decision = self.evidence_gate.assess(question, hits)
        except (RuntimeError, ValueError, ValidationError) as error:
            events.append(
                self._event(
                    "evidence-sufficiency-failure",
                    account_id=account_id,
                    course_id=conversation.course_id,
                    release_id=release.id,
                    conversation_id=conversation.id,
                    details={
                        "implementation": getattr(
                            self.evidence_gate,
                            "implementation_id",
                            "evidence-gate",
                        ),
                        "failure_type": type(error).__name__,
                    },
                )
            )
            return [], events
        events.append(
            self._event(
                "evidence-sufficiency-assessed",
                account_id=account_id,
                course_id=conversation.course_id,
                release_id=release.id,
                conversation_id=conversation.id,
                details={
                    "implementation": getattr(
                        self.evidence_gate,
                        "implementation_id",
                        "evidence-gate",
                    ),
                    "candidate_hit_count": len(hits),
                    "sufficient": decision.sufficient,
                    "score": decision.score,
                    "selected_hit_count": len(decision.selected_hit_ids),
                },
            )
        )
        if not decision.sufficient:
            return [], events
        if not decision.selected_hit_ids:
            return hits, events
        eligible_by_id = {hit.chunk.id: hit for hit in hits}
        if not set(decision.selected_hit_ids).issubset(eligible_by_id):
            events.append(
                self._event(
                    "evidence-sufficiency-failure",
                    account_id=account_id,
                    course_id=conversation.course_id,
                    release_id=release.id,
                    conversation_id=conversation.id,
                    details={
                        "implementation": getattr(
                            self.evidence_gate,
                            "implementation_id",
                            "evidence-gate",
                        ),
                        "failure_type": "unknown-selected-hit",
                    },
                )
            )
            return [], events
        return [eligible_by_id[hit_id] for hit_id in decision.selected_hit_ids], events

    def _graph_retrieve(
        self, graph_input: TutoringGraphInput
    ) -> tuple[list[RetrievalHit], list[AuditEvent]]:
        return self._retrieve(
            graph_input.release,
            account_id=graph_input.account_id,
            conversation=graph_input.conversation,
            question=graph_input.student_message,
        )

    async def _graph_generate(
        self,
        graph_input: TutoringGraphInput,
        hits: list[RetrievalHit],
        intent: str,
        help_level: int,
        repair_reason: str | None,
    ) -> tuple[TutorAnswer, list[AuditEvent]]:
        short_circuit = self._graph_policy_answer(intent)
        if short_circuit is not None:
            return short_circuit, []
        generate_for_intent = getattr(self.generator, "generate_for_intent", None)
        if callable(generate_for_intent):
            try:
                answer = await generate_for_intent(
                    graph_input.student_message,
                    hits,
                    graph_input.release.policy,
                    intent=intent,
                    help_level=help_level,
                    repair_reason=repair_reason,
                )
                return answer, []
            except (RuntimeError, ValueError, ValidationError) as error:
                return self._generation_failure_answer(error), [
                    self._event(
                        "generation-failure",
                        account_id=graph_input.account_id,
                        course_id=graph_input.conversation.course_id,
                        release_id=graph_input.release.id,
                        conversation_id=graph_input.conversation.id,
                        details={"failure_type": type(error).__name__},
                    )
                ]
        return await self._generate(
            graph_input.release,
            hits,
            graph_input.student_message,
            account_id=graph_input.account_id,
            conversation=graph_input.conversation,
        )

    @staticmethod
    def _graph_policy_answer(intent: str) -> TutorAnswer | None:
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

    @staticmethod
    def _graph_fallback(
        graph_input: TutoringGraphInput,
        intent: str,
        failure_reason: str | None,
    ) -> TutorAnswer:
        del graph_input, intent, failure_reason
        return TutorAnswer(
            content=(
                "I could not validate that tutoring response. Please restate the "
                "step you are working on or ask the instructor."
            ),
            warnings=["The bounded tutoring graph used its safe fallback."],
            trace=GenerationTrace(
                generator_id="bounded-tutoring-graph-v1",
                provider_model="not-called",
                prompt_version="safe-fallback-v1",
                policy_action="safe-graph-failure",
                latency_ms=0,
                usage=GenerationUsage(),
            ),
        )

    async def _generate(
        self,
        release: DigitalTwinRelease,
        hits: list[RetrievalHit],
        question: str,
        *,
        account_id: str,
        conversation: Conversation,
    ) -> tuple[TutorAnswer, list[AuditEvent]]:
        try:
            return await self.generator.generate(question, hits, release.policy), []
        except (RuntimeError, ValueError, ValidationError) as error:
            answer = self._generation_failure_answer(error)
            event = self._event(
                "generation-failure",
                account_id=account_id,
                course_id=conversation.course_id,
                release_id=release.id,
                conversation_id=conversation.id,
                details={"failure_type": type(error).__name__},
            )
            return answer, [event]

    def _validate_answer_claims(
        self,
        answer: TutorAnswer,
        hits: list[RetrievalHit],
        *,
        account_id: str,
        conversation: Conversation,
    ) -> tuple[TutorAnswer, list[AuditEvent]]:
        """Apply the optional post-generation release boundary fail closed."""

        if (
            self.claim_evidence_validator is None
            or answer.trace is None
            or answer.trace.policy_action != "answer"
        ):
            return answer, []
        try:
            decision = self.claim_evidence_validator.validate(
                answer.atomic_claims,
                hits,
            )
        except (RuntimeError, ValueError, ValidationError) as error:
            decision = None
            failure_type = type(error).__name__
        else:
            failure_type = None

        details: dict[str, str | int | float | bool | None] = {
            "implementation": getattr(
                self.claim_evidence_validator,
                "implementation_id",
                "post-generation-claim-validator",
            ),
            "releasable": bool(decision and decision.releasable),
            "claim_count": decision.claim_count if decision is not None else 0,
            "supported_claim_count": (
                decision.supported_claim_count if decision is not None else 0
            ),
            "score": decision.score if decision is not None else 0.0,
            "validator_failure_type": failure_type,
        }
        event = self._event(
            "post-generation-claim-validation",
            account_id=account_id,
            course_id=conversation.course_id,
            release_id=conversation.release_id,
            conversation_id=conversation.id,
            details=details,
        )
        if decision is not None and decision.releasable:
            return answer, [event]

        trace = answer.trace.model_copy(
            update={"policy_action": "safe-claim-validation-failure"}
        )
        return (
            TutorAnswer(
                content=(
                    "The tutor could not verify every factual claim against the "
                    "approved course evidence. Please refine the question or ask "
                    "the instructor."
                ),
                warnings=["Post-generation claim validation failed safely."],
                trace=trace,
            ),
            [event],
        )

    def _generation_failure_answer(self, error: Exception) -> TutorAnswer:
        del error
        return TutorAnswer(
            content=(
                "The tutor could not produce a validated response. "
                "Please try again or ask the instructor."
            ),
            warnings=["Generation failed safely."],
            trace=GenerationTrace(
                generator_id=getattr(
                    self.generator, "implementation_id", "unknown-generator"
                ),
                provider_model="not-returned",
                prompt_version="not-returned",
                policy_action="safe-provider-failure",
                latency_ms=0,
                usage=GenerationUsage(),
            ),
        )

    def _citations(
        self,
        answer: TutorAnswer,
        hits: list[RetrievalHit],
        tutor_message: Message,
        conversation: Conversation,
    ) -> tuple[list[Citation], bool]:
        if (
            answer.trace is not None
            and answer.trace.policy_action == "answer"
            and not answer.citations
        ):
            return [], True
        citations: list[Citation] = []
        for source in answer.citations:
            matches = [
                hit.chunk for hit in hits if citation_matches_chunk(source, hit.chunk)
            ]
            if len(matches) != 1:
                return [], True
            chunk = matches[0]
            authoritative_title = chunk.metadata.get("title")
            if (
                not isinstance(authoritative_title, str)
                or not authoritative_title.strip()
            ):
                return [], True
            citations.append(
                Citation(
                    id=f"citation-{uuid4()}",
                    message_id=tutor_message.id,
                    course_id=conversation.course_id,
                    release_id=conversation.release_id,
                    source_artifact_id=chunk.source_artifact_id or chunk.document_id,
                    source_document_id=chunk.document_id,
                    source_version=chunk.source_version,
                    title=authoritative_title.strip(),
                    locator=chunk.locator or f"chunk {chunk.ordinal + 1}",
                    source_checksum=chunk.source_checksum,
                    page=chunk.page_start,
                    region_id=chunk.region_id,
                    region_kind=(
                        chunk.region_kind.value
                        if chunk.region_kind is not None
                        else None
                    ),
                    bounding_box=chunk.bounding_box,
                    crop_ref=chunk.crop_ref if chunk.display_allowed else None,
                )
            )
        return citations, False

    @staticmethod
    def _safe_failure_message(message: Message, content: str) -> Message:
        return message.model_copy(
            update={
                "content": content,
                "action": "safe-citation-failure",
                "trace": GenerationTrace(
                    generator_id=(
                        message.trace.generator_id
                        if message.trace
                        else "unknown-generator"
                    ),
                    provider_model="not-returned",
                    prompt_version="not-returned",
                    policy_action="safe-citation-failure",
                    latency_ms=0,
                    usage=GenerationUsage(),
                ),
            }
        )

    def _deny(
        self,
        code: str,
        message: str,
        *,
        account_id: str | None = None,
        course_id: str | None = None,
        release_id: str | None = None,
        conversation_id: str | None = None,
    ) -> None:
        self.repository.save_audit_event(
            self._event(
                "access-denied",
                account_id=account_id,
                course_id=course_id,
                release_id=release_id,
                conversation_id=conversation_id,
                details={"reason": code},
            )
        )
        raise StudentWorkflowError(code, message)

    @staticmethod
    def _event(
        event_type: str,
        *,
        account_id: str | None = None,
        course_id: str | None = None,
        release_id: str | None = None,
        conversation_id: str | None = None,
        details: dict[str, str | int | float | bool | None] | None = None,
    ) -> AuditEvent:
        return AuditEvent(
            id=f"audit-{uuid4()}",
            event_type=event_type,
            account_id=account_id,
            course_id=course_id,
            release_id=release_id,
            conversation_id=conversation_id,
            details=details or {},
        )
