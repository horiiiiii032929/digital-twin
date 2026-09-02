"""Multi-concept actual-product fixture for the hidden-state learner extension.

Reuses the provider bundles, switchable deterministic generator, modes, and
allowed actions of the 010 runtime unchanged, and installs a release whose
domain model carries several concepts with one approved chunk each, so that a
simulated learner's attempts on different concepts can be told apart by the
product's lexical attribution.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path

from src.digital_twin.evaluation import ProductEngineBindingV1
from src.digital_twin.evaluation.autonomy_product_adapter import (
    StudentProductAutonomyRuntimeV1,
)
from src.digital_twin.evaluation.simulated_learner_v1 import ConceptCardV1
from src.digital_twin.generation import (
    BoundedPedagogicalPromptBuilder,
    DeterministicPolicyEnforcer,
    LiveAtomicGroundedGenerator,
)
from src.digital_twin.action_router import DeterministicActionRouterV2
from src.digital_twin.grounding import (
    AtomicClaimEvidenceValidator,
    ExactQuoteAtomicClaimVerifier,
    StructuredLexicalCoverageEvidenceGate,
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
from src.digital_twin.student.autonomy_runtime import (
    GovernedAutonomousTutoringGraph,
    LiveAutonomousPlanner,
)
from src.digital_twin.student.autonomy_service import (
    GovernedAutonomyService,
    RepositoryGroundedWordingGenerator,
)
from src.digital_twin.student.tutoring_graph import LiveReactiveSemanticPlanner, TutoringMode

import scripts.governed_full_autonomy_v2_1_actual_product_runtime as base

ROOT = Path(__file__).resolve().parents[1]

# Six approved concepts with disjoint technical vocabularies. Descriptions are
# the approved source text; a correct attempt restates one of them.
HIDDEN_STATE_CONCEPT_CARDS: tuple[ConceptCardV1, ...] = (
    ConceptCardV1(
        "concept-lease-ordering",
        "lease ordering",
        "Lease ordering grants each replica a bounded lease token so updates apply in lease sequence, expired leases are renewed before commit, and stale holders are fenced by the sequence number.",
        "Explain how lease ordering sequences replica updates.",
    ),
    ConceptCardV1(
        "concept-vector-stamps",
        "vector stamps",
        "Vector stamps attach a per-node counter array to every write so concurrent writes are detected when neither stamp dominates, and dominated stamps are discarded during merge.",
        "Explain how vector stamps detect concurrent writes.",
    ),
    ConceptCardV1(
        "concept-quorum-reads",
        "quorum reads",
        "Quorum reads collect responses from a majority of storage nodes, compare version digests, repair lagging nodes with the newest digest, and return the value only after the majority agrees.",
        "Explain how quorum reads return a consistent value.",
    ),
    ConceptCardV1(
        "concept-snapshot-isolation",
        "snapshot isolation",
        "Snapshot isolation gives each transaction a frozen view at its start timestamp, validates write sets at commit, and aborts the later transaction when two overlapping transactions modify the same row.",
        "Explain how snapshot isolation resolves overlapping transactions.",
    ),
    ConceptCardV1(
        "concept-gossip-repair",
        "gossip repair",
        "Gossip repair pairs random peers periodically, exchanges Merkle tree hashes for key ranges, and streams only the divergent ranges so background anti-entropy converges without a coordinator.",
        "Explain how gossip repair converges divergent replicas.",
    ),
    ConceptCardV1(
        "concept-backpressure-windows",
        "backpressure windows",
        "Backpressure windows limit in-flight requests per producer with a credit window, shrink the credit when consumer queues exceed a watermark, and grow it again as drained acknowledgements arrive.",
        "Explain how backpressure windows regulate producers.",
    ),
)


def _install_multi_concept_release(repository, fixture, *, now: datetime):
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
    preview = profiles.preview(fixture.professor_id, fixture.course_a_id, draft.profile_id)
    approved = profiles.approve(
        fixture.professor_id,
        fixture.course_a_id,
        draft.profile_id,
        preview_sha256=preview.preview_sha256,
    )
    current = repository.get_published_release(fixture.course_a_id)
    if current is None:
        raise RuntimeError("synthetic product fixture has no source release")
    template = current.chunks[0]
    chunks = []
    concepts = []
    objectives = []
    for index, card in enumerate(HIDDEN_STATE_CONCEPT_CARDS, start=1):
        source_id = f"hidden-source-{index:02d}"
        sha = hashlib.sha256(card.description.encode("utf-8")).hexdigest()
        chunk = template.model_copy(
            update={
                "id": f"chunk-{source_id}",
                "document_id": f"document-{source_id}",
                "source_artifact_id": source_id,
                "text": card.description,
                "content_hash": sha,
                "source_checksum": sha,
                "region_id": f"region-{source_id}",
                "retrieval_allowed": True,
                "display_allowed": True,
                "locator": f"{source_id} paragraph 1",
                "metadata": {
                    **template.metadata,
                    "course_id": fixture.course_a_id,
                    "source_template": source_id,
                    "source_path": f"{source_id}.md",
                    "title": card.label.title(),
                    "parent_cluster_id": f"cluster-{source_id}",
                    "modality": "text",
                    "char_start": "0",
                    "char_end": str(len(card.description)),
                },
            },
            deep=True,
        )
        chunks.append(chunk)
        concepts.append(
            CourseConceptV1(
                concept_id=card.concept_id,
                label=card.label,
                description=card.description,
                prerequisite_concept_ids=(
                    [HIDDEN_STATE_CONCEPT_CARDS[index - 2].concept_id] if index > 1 else []
                ),
                canonical_ranges=[
                    CanonicalSourceRangeV1(
                        source_artifact_id=chunk.source_artifact_id,
                        source_version=chunk.source_version,
                        source_sha256=sha,
                        locator=chunk.locator,
                        char_start=0,
                        char_end=len(chunk.text),
                    )
                ],
            )
        )
        objectives.append(
            CourseObjectiveV1(
                objective_id=f"objective-{card.concept_id}",
                statement=card.objective,
                concept_ids=[card.concept_id],
            )
        )
    release = current.model_copy(
        update={
            "id": "release-hidden-state-learner-v1",
            "status": StudentReleaseStatus.DRAFT,
            "chunks": chunks,
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
            domain_model_id="domain-hidden-state-learner-v1",
            course_id=fixture.course_a_id,
            release_id=release.id,
            release_sha256=hashlib.sha256(release.model_dump_json().encode("utf-8")).hexdigest(),
            version=1,
            objectives=objectives,
            concepts=concepts,
            approved_by=fixture.professor_id,
        )
    )
    return release, [card.objective for card in HIDDEN_STATE_CONCEPT_CARDS]


def build_hidden_state_runtime_factory(
    root: Path,
    condition: str,
    *,
    provider_backed: bool,
    maximum_case_cost_usd: float = 1.0,
    engine_binding: ProductEngineBindingV1 | None = None,
):
    """Per-case factory for the hidden-state learner extension (multi-concept)."""

    mode = base.MODES[condition]

    def factory(case, clock):
        root.mkdir(parents=True, exist_ok=True)
        database_path = root / (
            hashlib.sha256(f"{condition}:{case.case_id}".encode()).hexdigest()[:20] + ".sqlite3"
        )
        repository = SQLiteStudentRepository(database_path)
        profile = json.loads(base.PROFILE_PATH.read_text(encoding="utf-8"))
        fixture = seed_synthetic_student_workflow(
            repository,
            profile_id=str(profile["profile_id"]),
            profile_version=str(profile["profile_version"]),
            source_namespace=f"hidden-state-learner-{case.case_id}",
        )
        release, objectives = _install_multi_concept_release(repository, fixture, now=clock.now())
        repository.save_course_tutoring_runtime_profile(
            CourseTutoringRuntimeProfileV1(
                course_id=fixture.course_a_id,
                mode=mode,
                version=1,
                changed_by=fixture.professor_id,
                reason=f"Evaluate {condition} with a hidden-state learner.",
                updated_at=clock.now().isoformat(),
            )
        )
        validator = AtomicClaimEvidenceValidator(
            ExactQuoteAtomicClaimVerifier(),
            minimum_entailment=1.0,
            maximum_contradiction=0.0,
            maximum_claims=8,
            evidence_limit=5,
        )
        evidence_gate = StructuredLexicalCoverageEvidenceGate()
        selected_engine = engine_binding
        if selected_engine is not None and (
            provider_backed != (selected_engine.provider != "deterministic")
        ):
            raise ValueError("provider_backed and engine binding disagree")
        bundle = None
        if provider_backed:
            bundle = (
                base._provider_bundle_for_engine(
                    maximum_cost_usd=maximum_case_cost_usd, engine=selected_engine
                )
                if selected_engine is not None
                else base._provider_bundle(maximum_cost_usd=maximum_case_cost_usd)
            )
        planner_model = (
            selected_engine.planner_model
            if selected_engine is not None
            else base.OPENAI_GPT_5_6_TERRA_MODEL
        )
        generator_model = (
            selected_engine.generator_model
            if selected_engine is not None
            else base.OPENAI_HIGH_VOLUME_MODEL
        )
        deterministic_generator = base._SwitchableGenerator() if bundle is None else None
        generator = deterministic_generator
        semantic_planner = None
        if bundle is not None:
            generator = LiveAtomicGroundedGenerator(
                bundle.generator,
                prompt_builder=BoundedPedagogicalPromptBuilder(),
                policy_enforcer=DeterministicPolicyEnforcer(
                    action_router=DeterministicActionRouterV2()
                ),
            )
            if mode == TutoringMode.T1_V2:
                semantic_planner = LiveReactiveSemanticPlanner(bundle.planner, model_id=planner_model)

        def services(open_repository):
            outreach = ProactiveOutreachService(open_repository, clock=clock)
            proactive_graph = None
            if bundle is not None and condition == "t1-v2-autonomous":
                proactive_graph = GovernedAutonomousTutoringGraph(
                    planner=LiveAutonomousPlanner(bundle.planner, model_id=planner_model),
                    generator=RepositoryGroundedWordingGenerator(
                        open_repository,
                        generator,
                        model_id=generator_model,
                        claim_validator=validator,
                    ),
                    checkpoint_database_path=str(database_path),
                )
            autonomy = GovernedAutonomyService(
                open_repository, outreach, graph=proactive_graph, clock=clock
            )
            tutoring = StudentTutoringService(
                open_repository,
                profile_path=base.PROFILE_PATH,
                generator=generator,
                evidence_gate=evidence_gate,
                claim_evidence_validator=validator,
                tutoring_mode=mode,
                learning_gap_pseudonymizer=LearningGapPseudonymizer(
                    b"hidden-state-learner-evaluation-secret"
                ),
                reactive_semantic_planner=semantic_planner,
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
            approved_course_objectives=objectives,
            allowed_actions=base.ALLOWED_ACTIONS,
            autonomy_enabled=condition == "t1-v2-autonomous",
        )
        conversation = tutoring.create_conversation(fixture.student_a_id, fixture.course_a_id)

        async def apply_control(runtime, event, now):
            if event.kind == "provider-failure":
                if bundle is not None:
                    bundle.planner_switch.failed = True
                    bundle.generator_switch.failed = True
                elif deterministic_generator is not None:
                    deterministic_generator.failed = True
                return
            raise ValueError(f"unsupported hidden-state control event: {event.kind}")

        def build_runtime(open_repository, open_tutoring, open_autonomy):
            def restart(runtime):
                runtime.repository.close()
                reopened = SQLiteStudentRepository(database_path)
                _outreach, reopened_autonomy, reopened_tutoring = services(reopened)
                return build_runtime(reopened, reopened_tutoring, reopened_autonomy)

            async def collect_metrics(_runtime):
                return base._metrics(bundle)

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
