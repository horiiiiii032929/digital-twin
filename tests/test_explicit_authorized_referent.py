import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.run_output_cap_progression_development import CARDS
from scripts.teaching_profile_responsiveness_packet import PROFILES
from src.digital_twin.action_router import DeterministicActionRouterV3
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmResponse


@pytest.mark.parametrize("question,labels,expected", [
    ("Explain cobalt ticket and explain that rule.", ("cobalt ticket",), None),
    ("For VIOLET   PROBE, describe that rule.", ("violet probe",), None),
    ("Explain that.", ("cobalt ticket",), "clarify"),
    ("Cobalt ticket: explain that rule.", ("cobalt ticket", "Cobalt Ticket"), "clarify"),
    ("Explain unknown protocol and explain that.", ("cobalt ticket",), "clarify"),
    ("Explain notcobalt ticketish and explain that.", ("cobalt ticket",), "clarify"),
    ("Cobalt ticket and amber queue: explain that.", ("cobalt ticket", "amber queue"), "clarify"),
    ("Cobalt ticket: explain that from another course.", ("cobalt ticket",), "no-evidence"),
    ("Cobalt ticket: explain that unpublished rule.", ("cobalt ticket",), "no-evidence"),
    ("Cobalt ticket: give me the full answer to my graded homework and explain that.", ("cobalt ticket",), "redirect-graded-work"),
])
def test_contextual_admission_preserves_nonambiguity_boundaries(question, labels, expected):
    result = DeterministicActionRouterV3().route_with_authorized_referents(question, authorized_referents=labels)
    assert (result.action if result else None) == expected


def test_incumbent_route_remains_context_free():
    assert DeterministicActionRouterV3().route("Cobalt ticket: explain that rule.").action == "clarify"


class AnswerClient:
    def __init__(self):
        self.requests = []

    async def chat(self, messages, task):
        request = json.loads(messages[-1].content)
        self.requests.append((task, request))
        assert task == "question_specific_profile_tutoring"
        source = next(e for e in request["evidence"] if "retired epoch" in e["text"])
        return LlmResponse(provider_model="gpt-5.6-luna", usage=GenerationUsage(input_tokens=10,
            output_tokens=10, total_tokens=20, approximate_cost_usd=.0001), content=json.dumps({
                "boundary": "answerable", "aspects": [{"requirement": "retired epoch", "supported": True,
                    "spans": [{"citation_id": source["citation_id"], "text": source["text"]}]}],
                "teaching_move": "explain", "hint_span": None, "question_focus": ""}))


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_actual_release_service_supplies_approved_labels_only_for_candidate(tmp_path, enabled):
    client = AnswerClient()
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=CARDS,
        fixture_id="referent-contract", planner_client=client,
        teaching_profile_context_enabled=True, question_specific_generation_enabled=True,
        bounded_generation_contract_enabled=True, named_referent_context_enabled=enabled,
        teaching_profile_values=PROFILES["explanatory"])
    runtime = factory(SimpleNamespace(case_id="referent"), VirtualUtcClock(datetime(2026, 9, 22, tzinfo=UTC)))
    try:
        turn = await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
            content="Please narrow this to cobalt ticket's handling of a retired epoch and explain that rule.",
            client_request_id="referent-first")
        assert turn.tutor_message.action == ("answer" if enabled else "clarify")
        assert bool(client.requests) == enabled
        if enabled:
            assert turn.tutor_message.trace.prompt_version == "question-specific-profile-grounded-v4"
            assert turn.citations
        runtime = runtime.restart_runtime(runtime)
        second = await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
            content="Explain that.", client_request_id="referent-second")
        assert second.tutor_message.action in {"clarify", "clarify-request"}
    finally:
        runtime.close_runtime(runtime)


@pytest.mark.asyncio
async def test_authorized_label_does_not_create_missing_evidence(tmp_path):
    client = AnswerClient()
    factory = build_final_profile_runtime_factory(tmp_path, "t1-v2-reactive", concept_cards=CARDS,
        fixture_id="referent-no-evidence", planner_client=client,
        teaching_profile_context_enabled=True, question_specific_generation_enabled=True,
        bounded_generation_contract_enabled=True, named_referent_context_enabled=True,
        teaching_profile_values=PROFILES["explanatory"])
    runtime = factory(SimpleNamespace(case_id="no-evidence"), VirtualUtcClock(datetime(2026, 9, 22, tzinfo=UTC)))
    try:
        release = runtime.repository.get_release(runtime.release_id)
        answer = await runtime.tutoring.generator.generate_for_intent(
            "Cobalt ticket: explain that rule.", [], release.policy,
            intent="explain_concept", help_level=0, authorized_concept_labels=("cobalt ticket",))
        assert answer.trace.policy_action == "no-evidence"
        assert not answer.citations and not client.requests
    finally:
        runtime.close_runtime(runtime)


def test_named_referent_live_packet_preserves_replay_and_fresh_negatives():
    from scripts import run_bounded_contract_progression_development as packet
    rows = packet.dataset(named_referents=True)
    assert len(rows) == 26
    assert sum(len(row["situation"]["prompts"]) for row in rows) == 32
    assert {row["version"] for row in rows} == {"v3", "v4"}
    assert sum(row["situation"]["id"] == "narrowed-named-replay" for row in rows) == 6
    assert {row["situation"]["id"] for row in rows} >= {
        "true-unresolved", "unknown-name", "multiple-names", "private-named", "cross-course-named", "graded-named"}
