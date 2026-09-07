"""Production-factory composition for fresh longitudinal development evaluation.

In live mode, students and elapsed time are simulated. Explicit client injection
also supports network-free contract tests, which are not live evidence.
Synthetic approved course fixtures
are installed directly; this adapter does not establish ingestion/publication UI
coverage. The historical 025 factory and results are unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from services.api.app.config import (
    AppSettings, AutonomyPlannerMode, EvidenceGateMode, GeneratorMode,
    StudentTutoringMode,
)
from services.api.app.factory import create_app
from src.digital_twin.evaluation.autonomy_contract import (
    AutonomyOperationalMetricsV1, AutonomyProviderCallV1,
)
from src.digital_twin.evaluation.autonomy_product_adapter import StudentProductAutonomyRuntimeV1
from src.digital_twin.evaluation.simulated_learner_v1 import ConceptCardV1
from src.digital_twin.llm import LlmClient
from src.digital_twin.student import (
    CourseTutoringRuntimeProfileV1, OutreachChannel, SQLiteStudentRepository,
    seed_synthetic_student_workflow, StudentReleaseStatus, TeachingProfileService,
)
from src.digital_twin.student.autonomy_models import AutonomousActionKind
from src.digital_twin.student.tutoring_graph import TutoringMode
from scripts.governed_full_autonomy_v2_1_hidden_state_runtime import _install_multi_concept_release

ROOT = Path(__file__).resolve().parents[1]
FINAL_PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json"
CONDITIONS = ("t1-v2-reactive", "t1-v2-autonomous")
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


def build_final_profile_runtime_factory(
    root: Path,
    condition: str,
    *,
    concept_cards: tuple[ConceptCardV1, ...],
    fixture_id: str,
    planner_client: LlmClient | None = None,
    teaching_profile_context_enabled: bool = False,
    question_specific_generation_enabled: bool = False,
    bounded_generation_contract_enabled: bool = False,
    named_referent_context_enabled: bool = False,
    instructional_moves_enabled: bool = False,
    instructional_continuation_enabled: bool = False,
    instructional_request_coverage_enabled: bool = False,
    instructional_compact_response_enabled: bool = False,
    instructional_profile_authority_enabled: bool = False,
    instructional_typed_response_enabled: bool = False,
    instructional_evidence_strength_enabled: bool = False,
    instructional_factual_revision_enabled: bool = False,
    instructional_bounded_revision_enabled: bool = False,
    instructional_conditional_revision_enabled: bool = False,
    experimental_generation_model_id: str | None = None,
    teaching_profile_values: dict | None = None,
    experimental_planner_model_id: str | None = None,
    maximum_case_cost_usd: float = 1.0,
    maximum_case_calls: int = 300,
    provider_max_concurrency: int = 1,
):
    """Return isolated production services with a budget retained across restart.

    An injected client can record provider evidence and enforce a run-wide cap.
    Without injection, create_app builds the ordinary selected OpenAI transport.
    No model calls occur while constructing or restarting the runtime.
    """
    model_modes = {"gpt-5.6-luna": AutonomyPlannerMode.OPENAI_GPT_5_6_LUNA_POLICY_VALUE,
        "gpt-5.6-terra": AutonomyPlannerMode.OPENAI_GPT_5_6_TERRA}
    if experimental_planner_model_id is not None and (
        experimental_planner_model_id not in model_modes or not question_specific_generation_enabled
        or condition != "t1-v2-reactive"):
        raise ValueError("model comparator requires an explicit known model and reactive generation candidate")
    if condition not in CONDITIONS:
        raise ValueError("unsupported final-profile condition")
    if not concept_cards or not fixture_id.strip():
        raise ValueError("fresh concept cards and fixture identifier are required")

    def factory(case, clock):
        case_root = root / hashlib.sha256(f"{condition}:{case.case_id}".encode()).hexdigest()[:20]
        case_root.mkdir(parents=True, exist_ok=True)
        database_path = case_root / "runtime.sqlite3"
        if database_path.exists():
            raise FileExistsError(f"exclusive runtime already exists: {database_path}")
        profile = json.loads(FINAL_PROFILE_PATH.read_text(encoding="utf-8"))
        shared_budget = None
        settings = AppSettings(
            database_path=database_path,
            data_root=case_root,
            student_profile_path=FINAL_PROFILE_PATH,
            generator_mode=GeneratorMode.DETERMINISTIC,
            evidence_gate_mode=EvidenceGateMode.DOMINANCE_SCOPED_AMBIGUITY_SAFE_V3,
            student_tutoring_mode=StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH,
            autonomy_planner_mode=model_modes[experimental_planner_model_id or "gpt-5.6-luna"],
            learning_gap_hmac_secret=b"synthetic-final-profile-evaluation-key",
            provider_max_calls_per_process=maximum_case_calls,
            provider_cost_cap_usd=maximum_case_cost_usd,
        )

        def open_app(repository):
            nonlocal shared_budget
            app = create_app(
                student_repository=repository, settings=settings, clock=clock,
                autonomy_planner_client=shared_budget or planner_client,
                teaching_profile_context_enabled=teaching_profile_context_enabled,
                question_specific_generation_enabled=question_specific_generation_enabled,
                bounded_generation_contract_enabled=bounded_generation_contract_enabled,
                named_referent_context_enabled=named_referent_context_enabled,
                instructional_moves_enabled=instructional_moves_enabled,
                instructional_continuation_enabled=instructional_continuation_enabled,
                instructional_request_coverage_enabled=instructional_request_coverage_enabled,
                instructional_compact_response_enabled=instructional_compact_response_enabled,
                instructional_profile_authority_enabled=instructional_profile_authority_enabled,
                instructional_typed_response_enabled=instructional_typed_response_enabled,
                instructional_evidence_strength_enabled=instructional_evidence_strength_enabled,
                instructional_factual_revision_enabled=instructional_factual_revision_enabled,
                instructional_bounded_revision_enabled=instructional_bounded_revision_enabled,
                instructional_conditional_revision_enabled=instructional_conditional_revision_enabled,
                experimental_generation_model_id=experimental_generation_model_id,
                provider_max_concurrency=provider_max_concurrency,
            )
            if shared_budget is None:
                shared_budget = app.state.autonomy_planner_budget
            return app

        repository = SQLiteStudentRepository(database_path)
        try:
            app = open_app(repository)
        except BaseException:
            repository.close()
            raise
        fixture = seed_synthetic_student_workflow(
            repository, profile_id=profile["profile_id"], profile_version=profile["profile_version"],
            source_namespace=f"{fixture_id}-{case.case_id}",
        )
        release, objectives = _install_multi_concept_release(
            repository, fixture, now=clock.now(), concept_cards=concept_cards, fixture_id=fixture_id,
        )
        if teaching_profile_values is not None:
            # A fresh approved profile/release is created for each matched arm.
            # Do not mutate the historical fixture or its immutable domain model.
            profiles = TeachingProfileService(repository)
            draft = profiles.create_draft(fixture.professor_id, fixture.course_a_id, teaching_profile_values)
            preview = profiles.preview(fixture.professor_id, fixture.course_a_id, draft.profile_id)
            approved = profiles.approve(fixture.professor_id, fixture.course_a_id, draft.profile_id,
                preview_sha256=preview.preview_sha256)
            previous_domain = repository.get_course_domain_model(release.id)
            release = release.model_copy(update={
                "id": f"{release.id}-profile-{approved.content_sha256[:12]}",
                "status": StudentReleaseStatus.DRAFT,
                "teaching_profile_id": approved.profile_id,
                "teaching_profile_sha256": approved.content_sha256,
            }, deep=True)
            repository.save_release(release)
            repository.publish_release(release.id)
            release = repository.get_release(release.id)
            if previous_domain is None or release is None:
                raise RuntimeError("fresh profile fixture lost release/domain binding")
            repository.save_course_domain_model(previous_domain.model_copy(update={
                "domain_model_id": f"{previous_domain.domain_model_id}-{approved.content_sha256[:12]}",
                "version": previous_domain.version + 1,
                "release_id": release.id,
                "release_sha256": hashlib.sha256(release.model_dump_json().encode()).hexdigest(),
            }, deep=True))
        repository.save_course_tutoring_runtime_profile(CourseTutoringRuntimeProfileV1(
            course_id=fixture.course_a_id, mode=TutoringMode.T1_V2, version=1,
            changed_by=fixture.professor_id,
            reason=f"Fresh final-profile longitudinal evaluation: {condition}.",
            updated_at=clock.now().isoformat(),
        ))
        app.state.proactive_outreach_service.update_preference(
            fixture.student_a_id, fixture.course_a_id, channel=OutreachChannel.IN_APP,
            enabled=True, timezone="UTC", quiet_hours_start="23:00", quiet_hours_end="02:00",
            max_messages_per_7_days=3,
        )
        app.state.governed_autonomy_service.set_policy(
            fixture.professor_id, fixture.course_a_id, approved_course_objectives=objectives,
            allowed_actions=ALLOWED_ACTIONS, autonomy_enabled=condition == "t1-v2-autonomous",
        )
        conversation = app.state.student_service.create_conversation(fixture.student_a_id, fixture.course_a_id)

        def build_runtime(current_app):
            def close(_runtime):
                for name in ("student_repository", "identity_repository", "ingestion_job_repository"):
                    getattr(current_app.state, name).close()

            def restart(runtime):
                close(runtime)
                return build_runtime(open_app(SQLiteStudentRepository(database_path)))

            async def collect_metrics(_runtime):
                rows = shared_budget.snapshot()["call_records"]
                records = [AutonomyProviderCallV1(**row) for row in rows]
                return AutonomyOperationalMetricsV1(
                    provider_calls=len(records), input_tokens=sum(r.input_tokens for r in records),
                    output_tokens=sum(r.output_tokens for r in records), total_tokens=sum(r.total_tokens for r in records),
                    provider_latency_ms=sum(r.latency_ms for r in records),
                    cost_usd=sum(r.reported_cost_usd or 0 for r in records), call_records=records,
                )

            return StudentProductAutonomyRuntimeV1(
                repository=current_app.state.student_repository, tutoring=current_app.state.student_service,
                autonomy=current_app.state.governed_autonomy_service, clock=clock,
                student_id=fixture.student_a_id, professor_id=fixture.professor_id,
                course_id=fixture.course_a_id, release_id=release.id, conversation_id=conversation.id,
                restart_runtime=restart, close_runtime=close, collect_metrics=collect_metrics,
            )

        return build_runtime(app)

    return factory
