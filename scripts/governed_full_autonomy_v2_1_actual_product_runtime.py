"""Actual-product fixture factory for the realistic-time autonomy evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from collections.abc import Callable

from services.llm import BudgetedLlmClient, LiteLlmClient, OpenAiResponsesClient
from src.digital_twin.action_router import DeterministicActionRouterV2
from src.digital_twin.evaluation import (
    AutonomyOperationalMetricsV1,
    AutonomyProviderCallV1,
    ProductEngineBindingV1,
)
from src.digital_twin.generation import (
    BoundedPedagogicalPromptBuilder,
    DeterministicGroundedGenerator,
    DeterministicPolicyEnforcer,
    LiveAtomicGroundedGenerator,
    DeterministicEvidenceSetGroundedGenerator,
)
from src.digital_twin.grounding import (
    AtomicClaimEvidenceValidator,
    CanonicalSourceAtomicClaimVerifier,
    ExactQuoteAtomicClaimVerifier,
    SourceSemanticEvidenceAtomGateV2,
    SourceSemanticEvidenceAtomGateV3,
    SourceSemanticEvidenceAtomRetrieverV1,
    StructuredLexicalCoverageEvidenceGate,
    materialize_semantic_evidence_atoms,
)
from src.digital_twin.grounding.models import AtomicAnswerClaim
from src.digital_twin.llm import LlmClient, LlmMessage, LlmResponse, LlmUnavailableError
from src.digital_twin.model_policy import (
    OPENAI_GPT_5_6_LUNA_MODEL,
    OPENAI_GPT_5_6_TERRA_MODEL,
    OPENAI_HIGH_VOLUME_MODEL,
)
from src.digital_twin.student import (
    CanonicalSourceRangeV1,
    CourseConceptV1,
    CourseDomainModelV1,
    CourseObjectiveV1,
    CourseTutoringRuntimeProfileV1,
    LearningGapPseudonymizer,
    OutreachChannel,
    ProactiveOutreachService,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentTutoringService,
    TeachingProfileDepth,
    TeachingProfileService,
    seed_synthetic_student_workflow,
)
from src.digital_twin.student.autonomy_models import AutonomousActionKind
from src.digital_twin.student.autonomy_runtime import (
    GovernedAutonomousTutoringGraph,
    LiveAutonomousPlanner,
)
from src.digital_twin.student.autonomy_service import (
    BoundedStrategyGroundedWordingGenerator,
    GovernedAutonomyService,
    RepositoryGroundedWordingGenerator,
)
from src.digital_twin.student.planning_architectures import (
    GuardedPolicyValuePlanner,
    LlmHierarchicalPlanningProvider,
)
from src.digital_twin.student.tutoring_graph import (
    DeterministicReactiveSemanticPlanner,
    LiveReactiveSemanticPlanner,
    TutoringMode,
)
from src.digital_twin.evaluation.autonomy_product_adapter import (
    StudentProductAutonomyRuntimeV1,
)

from scripts.build_governed_full_autonomy_v2_1_actual_product_evaluation_002 import (
    source_fixture,
    source_template_number,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = (
    ROOT / "research/05_evaluation/profiles/student-tutor-r1-openai-candidate-v1.json"
)
MODES = {
    "t0-grounded-control": TutoringMode.T0,
    "t1-v1-reactive-control": TutoringMode.T1,
    "t1-v2-reactive": TutoringMode.T1_V2,
    "t1-v2-autonomous": TutoringMode.T1_V2,
}
ALLOWED_ACTIONS = [
    AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION,
    AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE,
    AutonomousActionKind.RECOMMEND_APPROVED_SOURCE,
    AutonomousActionKind.ISSUE_RETRIEVAL_PRACTICE,
    AutonomousActionKind.SCHEDULE_FOLLOW_UP,
    AutonomousActionKind.SEND_IN_APP_CHECK_IN,
    AutonomousActionKind.SUMMARIZE_PROGRESS,
    AutonomousActionKind.CREATE_PROFESSOR_INSIGHT_DRAFT,
    AutonomousActionKind.NO_ACTION,
]


class _SwitchableClient:
    def __init__(self, delegate: LlmClient) -> None:
        self.delegate = delegate
        self.failed = False

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        if self.failed:
            raise LlmUnavailableError()
        return await self.delegate.chat(messages, task)


class _SwitchableGenerator:
    """Inject a deterministic provider outage without bypassing product code."""

    implementation_id = "evaluation-switchable-deterministic-generator"
    version = "v1"

    def __init__(self) -> None:
        self.delegate = DeterministicGroundedGenerator()
        self.failed = False

    async def generate(self, question, hits, policy):
        if self.failed:
            raise LlmUnavailableError()
        answer = await self.delegate.generate(question, hits, policy)
        return self._attach_exact_claim(answer, hits)

    async def generate_for_intent(
        self,
        question,
        hits,
        policy,
        *,
        intent,
        help_level,
        repair_reason=None,
    ):
        if self.failed:
            raise LlmUnavailableError()
        answer = await self.delegate.generate_for_intent(
            question,
            hits,
            policy,
            intent=intent,
            help_level=help_level,
            repair_reason=repair_reason,
        )
        return self._attach_exact_claim(answer, hits)

    @staticmethod
    def _attach_exact_claim(answer, hits):
        if (
            answer.atomic_claims
            or answer.trace is None
            or answer.trace.policy_action != "answer"
            or not hits
        ):
            return answer
        return answer.model_copy(
            update={
                "atomic_claims": [
                    AtomicAnswerClaim(
                        claim_id="claim-deterministic-evidence",
                        text=hits[0].chunk.text,
                        evidence_hit_ids=[hits[0].chunk.id],
                    )
                ]
            }
        )


class _SwitchableReactivePlanner:
    """Network-free stand-in that reproduces the provider failure boundary."""

    model_id = "evaluation/gpt-5.6-terra-stand-in"

    def __init__(self) -> None:
        self.delegate = DeterministicReactiveSemanticPlanner()
        self.failed = False

    async def propose(self, **kwargs):
        if self.failed:
            raise LlmUnavailableError()
        return await self.delegate.propose(**kwargs)


@dataclass(slots=True)
class _ProviderBundle:
    planner_switch: _SwitchableClient
    generator_switch: _SwitchableClient
    planner: BudgetedLlmClient
    generator: BudgetedLlmClient


def selected_h_e1_engine_binding() -> ProductEngineBindingV1:
    """Return the exact allocation selected by engine comparison 006."""

    return ProductEngineBindingV1(
        engine_id="h-e1",
        provider="openai-direct",
        planner_model=OPENAI_GPT_5_6_LUNA_MODEL,
        generator_model=OPENAI_GPT_5_6_LUNA_MODEL,
        planner_reasoning_effort="low",
        generator_reasoning_effort="low",
        maximum_output_tokens=500,
        input_price_usd_per_million=0.2,
        output_price_usd_per_million=1.2,
        credential_environment_variable="OPENAI_API_KEY",
        returned_identity_must_equal=OPENAI_GPT_5_6_LUNA_MODEL,
        dated_snapshot=False,
    )


def _provider_bundle(*, maximum_cost_usd: float) -> _ProviderBundle:
    return _provider_bundle_for_engine(
        maximum_cost_usd=maximum_cost_usd,
        engine=ProductEngineBindingV1(
            engine_id="e5",
            provider="openai-direct",
            planner_model=OPENAI_GPT_5_6_TERRA_MODEL,
            generator_model=OPENAI_HIGH_VOLUME_MODEL,
            planner_reasoning_effort="low",
            generator_reasoning_effort="none",
            maximum_output_tokens=600,
            input_price_usd_per_million=0.75,
            output_price_usd_per_million=4.5,
            credential_environment_variable="OPENAI_API_KEY",
            returned_identity_must_equal=OPENAI_HIGH_VOLUME_MODEL,
            dated_snapshot=False,
        ),
    )


def _engine_client(
    engine: ProductEngineBindingV1,
    *,
    role: str,
):
    model = engine.planner_model if role == "planner" else engine.generator_model
    reasoning = (
        engine.planner_reasoning_effort
        if role == "planner"
        else engine.generator_reasoning_effort
    )
    if engine.provider == "openai-direct":
        return OpenAiResponsesClient(
            model,
            timeout_seconds=30,
            max_output_tokens=engine.maximum_output_tokens,
            reasoning_effort=reasoning,
        )
    if engine.provider == "deepseek-direct":
        if model != "deepseek-v4-flash":
            raise ValueError("direct DeepSeek engine must use deepseek-v4-flash")
        return LiteLlmClient(
            "deepseek/deepseek-v4-flash",
            timeout_seconds=30,
            max_output_tokens=engine.maximum_output_tokens,
            temperature=0,
            response_format={"type": "json_object"},
            expected_provider_model="deepseek-v4-flash",
        )
    raise ValueError("deterministic engine does not construct provider clients")


def _provider_bundle_for_engine(
    *,
    maximum_cost_usd: float,
    engine: ProductEngineBindingV1,
) -> _ProviderBundle:
    if engine.provider == "deterministic":
        raise ValueError("deterministic engine cannot construct a provider bundle")
    per_role_cost = max(0.01, maximum_cost_usd / 2)
    planner_switch = _SwitchableClient(_engine_client(engine, role="planner"))
    generator_switch = _SwitchableClient(_engine_client(engine, role="generator"))
    return _ProviderBundle(
        planner_switch=planner_switch,
        generator_switch=generator_switch,
        planner=BudgetedLlmClient(
            planner_switch,
            max_calls=16,
            max_cost_usd=per_role_cost,
        ),
        generator=BudgetedLlmClient(
            generator_switch,
            max_calls=16,
            max_cost_usd=per_role_cost,
        ),
    )


def _metrics(bundle: _ProviderBundle | None) -> AutonomyOperationalMetricsV1:
    if bundle is None:
        return AutonomyOperationalMetricsV1()
    snapshots = (bundle.planner.snapshot(), bundle.generator.snapshot())
    records: list[AutonomyProviderCallV1] = []
    for snapshot in snapshots:
        for row in snapshot["call_records"]:
            records.append(
                AutonomyProviderCallV1(**{**row, "call_number": len(records) + 1})
            )
    return AutonomyOperationalMetricsV1(
        provider_calls=len(records),
        input_tokens=sum(row.input_tokens for row in records),
        output_tokens=sum(row.output_tokens for row in records),
        total_tokens=sum(row.total_tokens for row in records),
        provider_latency_ms=sum(row.latency_ms for row in records),
        cost_usd=sum(row.reported_cost_usd or 0 for row in records),
        call_records=records,
    )


def _install_release(
    repository,
    fixture,
    case,
    *,
    now: datetime,
    grounding_architecture_id: str,
    source_resolver: Callable[[str], dict[str, str]],
):
    source = source_resolver(case.case_id)
    source_label = source.get(
        "label", f"Protocol {source_template_number(case.case_id):03d}"
    )
    profiles = TeachingProfileService(repository)
    draft = profiles.create_draft(
        fixture.professor_id,
        fixture.course_a_id,
        {
            "tone": "Patient, precise, and encouraging",
            "depth": TeachingProfileDepth.BALANCED,
            "explanation_structure": ["diagnose", "hint", "check"],
            "example_preferences": ["versioned systems examples"],
            "misconception_handling": "Identify the misconception and ask for one corrected step.",
            "integrity_limits": "Require an attempt before assessed-work help.",
            "help_ladder": ["diagnostic question", "hint", "worked analogy"],
            "outreach_policy": "Private in-app follow-ups within approved limits.",
        },
    )
    preview = profiles.preview(
        fixture.professor_id, fixture.course_a_id, draft.profile_id
    )
    approved = profiles.approve(
        fixture.professor_id,
        fixture.course_a_id,
        draft.profile_id,
        preview_sha256=preview.preview_sha256,
    )
    current = repository.get_published_release(fixture.course_a_id)
    if current is None:
        raise RuntimeError("synthetic product fixture has no source release")
    source_sha = hashlib.sha256(source["statement"].encode("utf-8")).hexdigest()
    chunk = current.chunks[0].model_copy(
        update={
            "id": f"chunk-{source['source_id']}",
            "document_id": f"document-{source['source_id']}",
            "source_artifact_id": source["source_id"],
            "text": source["statement"],
            "content_hash": source_sha,
            "source_checksum": source_sha,
            "region_id": f"region-{source['source_id']}",
            "retrieval_allowed": True,
            "display_allowed": True,
            "locator": f"{source['source_id']} paragraph 1",
            "metadata": {
                **current.chunks[0].metadata,
                "course_id": fixture.course_a_id,
                "source_template": source["source_id"],
                "source_path": f"{source['source_id']}.md",
                "title": source_label,
                "parent_cluster_id": f"cluster-{source['source_id']}",
                "modality": "text",
                "char_start": "0",
                "char_end": str(len(source["statement"])),
            },
        },
        deep=True,
    )
    if grounding_architecture_id in {
        "ambiguity-safe-source-semantic-evidence-atoms-v2",
        "pedagogy-aware-source-semantic-evidence-atoms-v3",
    }:
        chunk = materialize_semantic_evidence_atoms([chunk])[0]
    release = current.model_copy(
        update={
            "id": "release-autonomy-product-evaluation-v2",
            "status": StudentReleaseStatus.DRAFT,
            "chunks": [chunk],
            "teaching_profile_id": approved.profile_id,
            "teaching_profile_sha256": approved.content_sha256,
            "created_at": now.isoformat(),
        },
        deep=True,
    )
    repository.save_release(release)
    repository.publish_release(release.id)
    repository.save_course_domain_model(
        CourseDomainModelV1(
            domain_model_id=f"domain-{source['source_id']}",
            course_id=fixture.course_a_id,
            release_id=release.id,
            release_sha256=hashlib.sha256(
                release.model_dump_json().encode("utf-8")
            ).hexdigest(),
            version=1,
            objectives=[
                CourseObjectiveV1(
                    objective_id=f"objective-{source['concept_id']}",
                    statement=source["objective"],
                    concept_ids=[source["concept_id"]],
                )
            ],
            concepts=[
                CourseConceptV1(
                    concept_id=source["concept_id"],
                    label=source_label,
                    description=source["statement"],
                    canonical_ranges=[
                        CanonicalSourceRangeV1(
                            source_artifact_id=chunk.source_artifact_id,
                            source_version=chunk.source_version,
                            source_sha256=source_sha,
                            locator=chunk.locator,
                            char_start=0,
                            char_end=len(chunk.text),
                        )
                    ],
                )
            ],
            approved_by=fixture.professor_id,
        )
    )
    return release, source


def build_runtime_factory(
    root: Path,
    condition: str,
    *,
    provider_backed: bool,
    maximum_case_cost_usd: float = 1.0,
    grounding_architecture_id: str = "legacy-structured-lexical-v1",
    source_resolver: Callable[[str], dict[str, str]] | None = None,
    engine_binding: ProductEngineBindingV1 | None = None,
    hybrid_safe_generation: bool = False,
    dependency_aware_provider_failure: bool = False,
    autonomy_architecture_id: str = "legacy-live-planner",
    bounded_strategy_generation: bool = False,
):
    """Return a per-case factory used only by the product evaluation adapter."""

    mode = MODES[condition]
    resolve_source = source_resolver or (
        lambda case_id: source_fixture(source_template_number(case_id))
    )

    def factory(case, clock):
        root.mkdir(parents=True, exist_ok=True)
        database_path = root / (
            hashlib.sha256(f"{condition}:{case.case_id}".encode()).hexdigest()[:20]
            + ".sqlite3"
        )
        repository = SQLiteStudentRepository(database_path)
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        fixture = seed_synthetic_student_workflow(
            repository,
            profile_id=str(profile["profile_id"]),
            profile_version=str(profile["profile_version"]),
            source_namespace=f"actual-product-evaluation-{case.case_id}",
        )
        release, source = _install_release(
            repository,
            fixture,
            case,
            now=clock.now(),
            grounding_architecture_id=grounding_architecture_id,
            source_resolver=resolve_source,
        )
        repository.save_course_tutoring_runtime_profile(
            CourseTutoringRuntimeProfileV1(
                course_id=fixture.course_a_id,
                mode=mode,
                version=1,
                changed_by=fixture.professor_id,
                reason=f"Evaluate {condition} through the actual product boundary.",
                updated_at=clock.now().isoformat(),
            )
        )
        validator = AtomicClaimEvidenceValidator(
            (
                CanonicalSourceAtomicClaimVerifier()
                if hybrid_safe_generation
                else ExactQuoteAtomicClaimVerifier()
            ),
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
            maximum_claims=8,
            evidence_limit=5,
        )
        if grounding_architecture_id == "legacy-structured-lexical-v1":
            evidence_gate = StructuredLexicalCoverageEvidenceGate()
            retriever_factory = None
        elif (
            grounding_architecture_id
            == "ambiguity-safe-source-semantic-evidence-atoms-v2"
        ):
            evidence_gate = SourceSemanticEvidenceAtomGateV2()

            def retriever_factory(chunks, _active_versions):
                return SourceSemanticEvidenceAtomRetrieverV1(
                    chunks,
                    candidate_limit=30,
                )

        elif (
            grounding_architecture_id
            == "pedagogy-aware-source-semantic-evidence-atoms-v3"
        ):
            evidence_gate = SourceSemanticEvidenceAtomGateV3()

            def retriever_factory(chunks, _active_versions):
                return SourceSemanticEvidenceAtomRetrieverV1(
                    chunks,
                    candidate_limit=30,
                )

        else:
            raise ValueError(
                f"unsupported grounding architecture: {grounding_architecture_id}"
            )
        selected_engine = engine_binding
        if selected_engine is not None and (
            provider_backed != (selected_engine.provider != "deterministic")
        ):
            raise ValueError("provider_backed and engine binding disagree")
        bundle = None
        if provider_backed:
            bundle = (
                _provider_bundle_for_engine(
                    maximum_cost_usd=maximum_case_cost_usd,
                    engine=selected_engine,
                )
                if selected_engine is not None
                else _provider_bundle(maximum_cost_usd=maximum_case_cost_usd)
            )
        planner_model = (
            selected_engine.planner_model
            if selected_engine is not None
            else OPENAI_GPT_5_6_TERRA_MODEL
        )
        generator_model = (
            selected_engine.generator_model
            if selected_engine is not None
            else OPENAI_HIGH_VOLUME_MODEL
        )
        deterministic_generator = _SwitchableGenerator() if bundle is None else None
        generator = deterministic_generator
        semantic_planner = None
        switchable_semantic_planner = None
        if bundle is not None:
            generator = (
                DeterministicEvidenceSetGroundedGenerator(
                    policy_enforcer=DeterministicPolicyEnforcer(
                        action_router=DeterministicActionRouterV2()
                    )
                )
                if hybrid_safe_generation
                else LiveAtomicGroundedGenerator(
                    bundle.generator,
                    prompt_builder=BoundedPedagogicalPromptBuilder(),
                    policy_enforcer=DeterministicPolicyEnforcer(
                        action_router=DeterministicActionRouterV2()
                    ),
                )
            )
            if mode == TutoringMode.T1_V2:
                semantic_planner = LiveReactiveSemanticPlanner(
                    bundle.planner,
                    model_id=planner_model,
                )
        elif mode == TutoringMode.T1_V2:
            switchable_semantic_planner = _SwitchableReactivePlanner()
            semantic_planner = switchable_semantic_planner

        def services(open_repository):
            outreach = ProactiveOutreachService(open_repository, clock=clock)
            proactive_graph = None
            if bundle is not None and condition == "t1-v2-autonomous":
                proactive_planner = (
                    GuardedPolicyValuePlanner(
                        proposal_provider=LlmHierarchicalPlanningProvider(
                            bundle.planner,
                            model_id=planner_model,
                        )
                    )
                    if autonomy_architecture_id
                    == "guarded-policy-value-planner-v2"
                    else LiveAutonomousPlanner(
                        bundle.planner,
                        model_id=planner_model,
                    )
                )
                proactive_generator = (
                    BoundedStrategyGroundedWordingGenerator(
                        open_repository,
                        bundle.generator,
                        model_id=generator_model,
                        claim_validator=validator,
                    )
                    if bounded_strategy_generation
                    else RepositoryGroundedWordingGenerator(
                        open_repository,
                        generator,
                        model_id=generator_model,
                        claim_validator=validator,
                    )
                )
                proactive_graph = GovernedAutonomousTutoringGraph(
                    planner=proactive_planner,
                    generator=proactive_generator,
                    checkpoint_database_path=str(database_path),
                )
            autonomy = GovernedAutonomyService(
                open_repository,
                outreach,
                graph=proactive_graph,
                clock=clock,
            )
            tutoring = StudentTutoringService(
                open_repository,
                profile_path=PROFILE_PATH,
                generator=generator,
                evidence_gate=evidence_gate,
                claim_evidence_validator=validator,
                tutoring_mode=mode,
                learning_gap_pseudonymizer=LearningGapPseudonymizer(
                    b"actual-product-evaluation-secret-32"
                ),
                reactive_semantic_planner=semantic_planner,
                retriever_factory=retriever_factory,
                clock=clock,
            )
            return outreach, autonomy, tutoring

        outreach, autonomy, tutoring = services(repository)
        outreach.update_preference(
            fixture.student_a_id,
            fixture.course_a_id,
            channel=OutreachChannel.IN_APP,
            enabled=True,
            timezone="UTC",
            quiet_hours_start="23:00",
            quiet_hours_end="02:00",
            max_messages_per_7_days=3,
        )
        autonomy.set_policy(
            fixture.professor_id,
            fixture.course_a_id,
            approved_course_objectives=[source["objective"]],
            allowed_actions=ALLOWED_ACTIONS,
            autonomy_enabled=condition == "t1-v2-autonomous",
        )
        conversation = tutoring.create_conversation(
            fixture.student_a_id, fixture.course_a_id
        )

        async def apply_control(runtime, event, now):
            if event.kind == "provider-failure":
                if not dependency_aware_provider_failure:
                    if bundle is not None:
                        bundle.planner_switch.failed = True
                        bundle.generator_switch.failed = True
                    else:
                        if deterministic_generator is None:
                            raise RuntimeError(
                                "deterministic failure injector is unavailable"
                            )
                        deterministic_generator.failed = True
                    current = runtime.repository.get_autonomy_policy(runtime.course_id)
                    runtime.autonomy.set_policy(
                        runtime.professor_id,
                        runtime.course_id,
                        approved_course_objectives=current.approved_course_objectives,
                        allowed_actions=current.allowed_actions,
                        autonomy_enabled=current.autonomy_enabled,
                        paused=True,
                    )
                    return
                if mode != TutoringMode.T1_V2:
                    return
                if bundle is not None:
                    bundle.planner_switch.failed = True
                else:
                    if switchable_semantic_planner is None:
                        raise RuntimeError(
                            "semantic planner failure injector is unavailable"
                        )
                    switchable_semantic_planner.failed = True
                current = runtime.repository.get_autonomy_policy(runtime.course_id)
                runtime.autonomy.set_policy(
                    runtime.professor_id,
                    runtime.course_id,
                    approved_course_objectives=current.approved_course_objectives,
                    allowed_actions=current.allowed_actions,
                    autonomy_enabled=current.autonomy_enabled,
                    paused=True,
                )
                return
            if event.kind == "membership-changed":
                membership = runtime.repository.get_membership(
                    runtime.student_id, runtime.course_id
                )
                if membership is None:
                    raise RuntimeError("evaluation membership disappeared")
                active = bool(event.payload.get("active", False))
                runtime.repository.save_membership(
                    membership.model_copy(update={"active": active})
                )
                if not active:
                    runtime.repository.cancel_autonomy_scope(
                        student_id=runtime.student_id,
                        course_id=runtime.course_id,
                        changed_at=now.isoformat(),
                    )
                return
            if event.kind in {"release-changed", "policy-changed"}:
                runtime.repository.cancel_autonomy_scope(
                    student_id=runtime.student_id,
                    course_id=runtime.course_id,
                    changed_at=now.isoformat(),
                )
                current = runtime.repository.get_autonomy_policy(runtime.course_id)
                runtime.autonomy.set_policy(
                    runtime.professor_id,
                    runtime.course_id,
                    approved_course_objectives=current.approved_course_objectives,
                    allowed_actions=current.allowed_actions,
                    autonomy_enabled=current.autonomy_enabled,
                    paused=True,
                    kill_switch=bool(event.payload.get("kill_switch", False)),
                )
                return
            raise ValueError(f"unsupported actual-product control event: {event.kind}")

        def build_runtime(open_repository, open_tutoring, open_autonomy):
            def restart(runtime):
                runtime.repository.close()
                reopened = SQLiteStudentRepository(database_path)
                _outreach, reopened_autonomy, reopened_tutoring = services(reopened)
                return build_runtime(reopened, reopened_tutoring, reopened_autonomy)

            async def collect_metrics(_runtime):
                return _metrics(bundle)

            return StudentProductAutonomyRuntimeV1(
                repository=open_repository,
                tutoring=open_tutoring,
                autonomy=open_autonomy,
                clock=clock,
                student_id=fixture.student_a_id,
                professor_id=fixture.professor_id,
                course_id=fixture.course_a_id,
                release_id=release.id,
                conversation_id=conversation.id,
                restart_runtime=restart,
                close_runtime=lambda runtime: runtime.repository.close(),
                apply_control_event=apply_control,
                collect_metrics=collect_metrics,
            )

        return build_runtime(repository, tutoring, autonomy)

    return factory
