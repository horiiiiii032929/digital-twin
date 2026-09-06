import hashlib
import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.run_final_profile_longitudinal import CARDS
from scripts.teaching_profile_responsiveness_packet import PROFILES, packet_manifest, score_style_choice
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.llm import LlmMalformedResponseError
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.student.autonomy_models import AutonomousEventKind, TurnPerceptionV2, LearnerBeliefStateV2
from src.digital_twin.student.teaching_profile import TeachingProfileStatus
from src.digital_twin.student.teaching_profile_context import approved_teaching_profile_context, PROFILE_FIELDS
from src.digital_twin.student.tutoring_graph import LiveReactiveSemanticPlanner


class CaptureClient:
    def __init__(self):
        self.calls = []

    async def chat(self, messages, task):
        self.calls.append((task, json.loads(messages[-1].content)))
        raise LlmMalformedResponseError(stage="network-free-context-test", usage=GenerationUsage(approximate_cost_usd=0))


def context(name, *, status=TeachingProfileStatus.APPROVED, bad_hash=False):
    values = PROFILES[name]
    digest = hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
    profile = SimpleNamespace(status=status, approved_at="2026-09-06T00:00:00Z", preview_sha256="a" * 64, profile_id=f"fresh-{name}", course_id="fresh-course", content_sha256=digest,
        model_dump=lambda **kwargs: values)
    repository = SimpleNamespace(get_teaching_profile=lambda _id: profile)
    release = SimpleNamespace(course_id="fresh-course", teaching_profile_id="fresh-" + name,
        teaching_profile_sha256="0" * 64 if bad_hash else digest)
    return approved_teaching_profile_context(repository, release)


@pytest.mark.parametrize("name", PROFILES)
def test_only_exact_approved_fields_are_exposed(name):
    result = context(name)
    assert set(result["preferences"]) == set(PROFILE_FIELDS)
    assert result["preferences"] == PROFILES[name]
    assert "profile_id" not in result


@pytest.mark.parametrize("kwargs", [{"status": TeachingProfileStatus.WITHDRAWN}, {"bad_hash": True}])
def test_withdrawn_or_mismatched_profile_is_rejected(kwargs):
    with pytest.raises(ValueError, match="binding"):
        context("socratic", **kwargs)


@pytest.mark.asyncio
async def test_reactive_prompt_control_is_invariant_candidate_carries_both_profiles():
    client = CaptureClient()
    planner = LiveReactiveSemanticPlanner(client, model_id="gpt-5.6-luna")
    arguments = dict(message="Why does checksum audit detect changes?",
        perception=TurnPerceptionV2(event_kind=AutonomousEventKind.STUDENT_MESSAGE, request_type="question"),
        concept_ids=[], belief=LearnerBeliefStateV2(learner_key="a" * 64, course_id="fresh-course", release_id="fresh-release"),
        evidence_keys=[], candidate_intent="explain_concept")
    for _name in PROFILES:
        await planner.propose(**arguments)
    assert client.calls[0] == client.calls[1]
    for name in PROFILES:
        await planner.propose(**arguments, teaching_profile_context=context(name))
    assert client.calls[2][1]["approved_teaching_profile"]["preferences"] == PROFILES["socratic"]
    assert client.calls[3][1]["approved_teaching_profile"]["preferences"] == PROFILES["explanatory"]


@pytest.mark.asyncio
async def test_candidate_factory_propagates_context_through_actual_reactive_service(tmp_path):
    client = CaptureClient()
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=CARDS,
        fixture_id="fresh-profile-plumbing", planner_client=client, teaching_profile_context_enabled=True)
    runtime = factory(SimpleNamespace(case_id="fresh-style-question"), VirtualUtcClock(datetime(2026, 9, 7, tzinfo=UTC)))
    try:
        await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
            content="I am confused about checksum audit and how it detects changed archived bytes. Why does it work?",
            client_request_id="fresh-message-001")
        assert client.calls
        task, payload = client.calls[0]
        assert task == "reactive_tutoring_intent"
        assert set(payload["approved_teaching_profile"]["preferences"]) == set(PROFILE_FIELDS)
    finally:
        runtime.close_runtime(runtime)


def test_packet_declares_control_and_no_real_fidelity_claim():
    assert packet_manifest()["conditions"][0] == "context-off"
    assert score_style_choice("socratic", "ask_next_step")
    assert not score_style_choice("socratic", "explain_concept")


@pytest.mark.asyncio
async def test_both_proactive_prompts_receive_profile_context(tmp_path):
    from src.digital_twin.student.autonomy_models import AutonomousActionKind
    from src.digital_twin.student.planning_architectures import LlmHierarchicalPlanningProvider, PlanningStateCardV1

    client = CaptureClient()
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-autonomous", concept_cards=CARDS,
        fixture_id="fresh-proactive-profile", planner_client=client, teaching_profile_context_enabled=True)
    runtime = factory(SimpleNamespace(case_id="fresh-proactive-case"), VirtualUtcClock(datetime(2026, 9, 7, tzinfo=UTC)))
    try:
        release = runtime.repository.get_release(runtime.release_id)
        opportunity = SimpleNamespace(release_id=release.id, opportunity_id="fresh-opportunity",
            event_kind=AutonomousEventKind.REPEATED_CONFUSION, concept_id=CARDS[0].concept_id)
        job = SimpleNamespace(opportunity=opportunity, goal=None, evidence_chunk_ids=[release.chunks[0].id],
            evidence_keys=["fresh-evidence"], evidence_complete=True, evidence_unique=True,
            evidence_current=True, evidence_authorized=True, teaching_profile_context=None)
        plan = SimpleNamespace(action=AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE)
        hierarchical = LlmHierarchicalPlanningProvider(client, model_id="gpt-5.6-luna")
        for profile_context in (None, context("socratic"), context("explanatory")):
            job.teaching_profile_context = profile_context
            with pytest.raises(LlmMalformedResponseError):
                await hierarchical.propose(job=job, state_card=PlanningStateCardV1(),
                    eligible_actions=(plan.action,), maximum_episode_steps=1)
            await runtime.autonomy.graph.generator.generate(job, plan)
        assert "approved_teaching_profile" not in client.calls[0][1]
        assert "approved_teaching_profile" not in client.calls[1][1]
        for offset, name in ((2, "socratic"), (4, "explanatory")):
            for _, payload in client.calls[offset:offset + 2]:
                assert payload["approved_teaching_profile"]["preferences"] == PROFILES[name]
    finally:
        runtime.close_runtime(runtime)


@pytest.mark.parametrize("name", PROFILES)
def test_matched_profile_fixture_is_approved_and_release_bound(tmp_path, name):
    client = CaptureClient()
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=CARDS,
        fixture_id="fresh-matched-profile", planner_client=client, teaching_profile_values=PROFILES[name],
        teaching_profile_context_enabled=True)
    runtime = factory(SimpleNamespace(case_id="fresh-" + name), VirtualUtcClock(datetime(2026, 9, 7, tzinfo=UTC)))
    try:
        release = runtime.repository.get_release(runtime.release_id)
        profile = runtime.repository.get_teaching_profile(release.teaching_profile_id)
        assert profile.status == TeachingProfileStatus.APPROVED
        assert approved_teaching_profile_context(runtime.repository, release)["preferences"] == PROFILES[name]
        assert runtime.repository.get_course_domain_model(release.id).release_id == release.id
        runtime = runtime.restart_runtime(runtime)
        assert approved_teaching_profile_context(runtime.repository,
            runtime.repository.get_release(runtime.release_id))["preferences"] == PROFILES[name]
        assert client.calls == []
    finally:
        runtime.close_runtime(runtime)


@pytest.mark.asyncio
async def test_withdrawn_bound_profile_stops_candidate_before_model_call(tmp_path):
    from src.digital_twin.student import TeachingProfileService
    from src.digital_twin.student.service import StudentWorkflowError
    client = CaptureClient()
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=CARDS,
        fixture_id="fresh-revocation-profile", planner_client=client, teaching_profile_values=PROFILES["socratic"],
        teaching_profile_context_enabled=True)
    runtime = factory(SimpleNamespace(case_id="fresh-revocation"), VirtualUtcClock(datetime(2026, 9, 7, tzinfo=UTC)))
    try:
        release = runtime.repository.get_release(runtime.release_id)
        TeachingProfileService(runtime.repository).withdraw(runtime.professor_id, runtime.course_id,
            release.teaching_profile_id)
        before_messages = runtime.repository.list_messages(runtime.conversation_id)
        with pytest.raises(StudentWorkflowError) as rejected:
            await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
                content="I am confused about checksum audit and how it detects changed archived bytes. Why does it work?",
                client_request_id="revoked-profile-question")
        assert rejected.value.code == "teaching_profile_unavailable"
        assert runtime.repository.list_messages(runtime.conversation_id) == before_messages
        assert client.calls == []
    finally:
        runtime.close_runtime(runtime)
