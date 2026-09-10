"""Real generator integration; injected verdicts establish contracts, not quality."""
import pytest
from src.digital_twin.generation.audited_instruction import AuditedInstructionalGenerator
from src.digital_twin.generation.final_response_audit import QUARANTINE_TEXT
from src.digital_twin.generation.models import PolicyAction
from tests.test_compact_instruction_generation import runtime, generate, Client
from tests.test_final_response_audit import VersionedAudit, VersionedRepair


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["pass", "repair", "reject", "unchanged", "unknown-source", "unknown-cost"])
async def test_actual_delivery_is_bound_to_audit_and_reaudit(runtime, mode):
    rt = runtime[0]
    audit = VersionedAudit(rejects={1, 2} if mode == "reject" else {1} if mode in {"repair", "unchanged", "unknown-source"} else (), known=mode != "unknown-cost")
    repair = VersionedRepair(same=mode == "unchanged", invalid=mode == "unknown-source")
    draft = Client()
    tasks = []
    class Routed:
        async def chat(self, messages, task):
            tasks.append(task)
            if task == "final_response_quality_audit_v2":
                return await audit.chat(messages, task)
            if task == "final_response_issue_guided_repair_v2":
                return await repair.chat(messages, task)
            return await draft.chat(messages, "question_specific_compact_instruction")
    rt.tutoring.generator = AuditedInstructionalGenerator(Routed(), model_id="gpt-5.6-luna",
        bounded_contract_enabled=True, named_referent_context_enabled=True)
    answer = await generate(runtime)
    if mode in {"pass", "repair"}:
        assert answer.trace.policy_action == PolicyAction.ANSWER
        assert answer.trace.provider_model == ("gpt-5.6-sol" if mode == "repair" else "gpt-5.6-luna")
        assert "final-response-quality-audit-v2-required" in answer.trace.validation_scope
        assert len(audit.calls) == (2 if mode == "repair" else 1)
    else:
        assert answer.trace.policy_action == PolicyAction.SAFE_PROVIDER_FAILURE
        assert answer.content == QUARANTINE_TEXT
        assert not answer.citations
        assert "final_response_quarantined=" in answer.trace.validation_scope
    assert len(tasks) <= 4
    if mode == "unknown-cost":
        assert answer.trace.usage.approximate_cost_usd is None
        assert "audit_stage=audit_request; audit_code=identity_or_usage" in answer.trace.validation_scope
    else:
        assert answer.trace.usage.approximate_cost_usd > .0001


@pytest.mark.asyncio
async def test_recorded_roles_audit_real_persisted_student_and_tutor_history(runtime, tmp_path):
    """Exercise public-history adaptation and the real cost/schema serializer."""
    import json
    from scripts.recorded_generation_roles import create_recorded_generation_roles
    from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
    from tests.test_compact_instruction_generation import QUESTION
    rt = runtime[0]
    audit = VersionedAudit()
    seen_history = []
    class Draft(Client):
        async def chat(self, messages, task):
            return await super().chat(messages, "question_specific_compact_instruction")
    class Audit:
        async def chat(self, messages, task):
            snapshot = json.loads(messages[-1].content)
            seen_history.append(snapshot["context"]["learner_history"])
            return await audit.chat(messages, task)
    roles = create_recorded_generation_roles(
        experimental_tutoring_configuration("v18-luna-sol-medium"), tmp_path / "roles",
        maximum_calls=90, maximum_cost_usd=15,
        transport_factory=lambda role, config: Audit() if role == "revision" else Draft())
    rt.tutoring.generator = AuditedInstructionalGenerator(roles, model_id="gpt-5.6-luna",
        bounded_contract_enabled=True, named_referent_context_enabled=True)
    first = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id,
        content=QUESTION, client_request_id="audit-real-first")
    second = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id,
        content="My attempt: check epoch before sequence. " + QUESTION,
        client_request_id="audit-real-second")
    assert first.tutor_message.action == second.tutor_message.action == "answer"
    assert seen_history[0] == []
    assert seen_history[1] == [
        {"role": "user", "content": first.student_message.content},
        {"role": "assistant", "content": first.tutor_message.content},
    ]
    assert roles.role_clients["revision"].attempts == 2
    assert not roles.stopped
    assert all(row["usage"]["approximate_cost_usd"] is not None
        for row in roles.records if row["status"] == "completed")


@pytest.mark.parametrize("history", [[{"role": "system", "content": "bad"}],
    [{"role": "student", "content": "x", "private_metadata": "excluded"}]])
def test_audit_history_adapter_rejects_unknown_roles_and_fields(history):
    from src.digital_twin.generation.audited_instruction import audit_payload
    with pytest.raises(ValueError):
        audit_payload({"learner_history": history})


@pytest.mark.asyncio
@pytest.mark.parametrize('wrong_identity', [False, True])
async def test_cheap_revision_is_explicit_and_identity_drift_is_withheld(runtime, wrong_identity):
    from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
    selection=experimental_tutoring_configuration('v19-luna-luna-medium')
    assert selection['role_configuration']['revision']=={'model':'gpt-5.6-luna','output_cap':3000,'reasoning_effort':'medium'}
    assert experimental_tutoring_configuration('v19-luna-sol-medium')['role_configuration']['revision']['model']=='gpt-5.6-sol'
    audit=VersionedAudit(rejects={1});repair=VersionedRepair();draft=Client()
    class Routed:
        role_configuration=selection['role_configuration']
        async def chat(self,messages,task):
            if task=='final_response_quality_audit_v2':
                answer=await audit.chat(messages,task)
            elif task=='final_response_issue_guided_repair_v2':
                answer=await repair.chat(messages,task)
            else:return await draft.chat(messages,'question_specific_compact_instruction')
            return answer.model_copy(update={'provider_model':'gpt-5.6-sol' if wrong_identity else 'gpt-5.6-luna'})
    runtime[0].tutoring.generator=AuditedInstructionalGenerator(Routed(),model_id='gpt-5.6-luna',audit_model='gpt-5.6-luna',bounded_contract_enabled=True,named_referent_context_enabled=True)
    answer=await generate(runtime)
    if wrong_identity:
        assert answer.trace.policy_action==PolicyAction.SAFE_PROVIDER_FAILURE
        assert not answer.citations
    else:
        assert answer.trace.policy_action==PolicyAction.ANSWER
        assert answer.trace.provider_model=='gpt-5.6-luna'
        assert len(audit.calls)==2


@pytest.mark.asyncio
async def test_invalid_audit_history_preserves_completed_draft_usage(runtime):
    from tests.test_compact_instruction_generation import QUESTION
    rt, draft, release, hits = runtime
    calls = []
    class Routed:
        async def chat(self, messages, task):
            calls.append(task)
            return await draft.chat(messages, "question_specific_compact_instruction")
    rt.tutoring.generator = AuditedInstructionalGenerator(Routed(), model_id="gpt-5.6-luna",
        bounded_contract_enabled=True, named_referent_context_enabled=True)
    answer = await rt.tutoring.generator.generate_for_intent(QUESTION, hits, release.policy,
        intent="explain_concept", help_level=0,
        teaching_profile_context={"preferences": {"tone": "plain"}},
        learner_history=[{"role": "system", "content": "PRIVATE_INVALID_HISTORY"}])
    assert len(calls) == 1
    assert answer.trace.policy_action == PolicyAction.SAFE_PROVIDER_FAILURE
    assert not answer.citations
    assert answer.content == "The tutor model returned an invalid grounded answer. Please try again or ask the instructor."
    assert answer.trace.usage.total_tokens == 20
    assert answer.trace.usage.approximate_cost_usd == .0001
    assert answer.trace.provider_model == "gpt-5.6-luna"
    assert "PRIVATE_INVALID_HISTORY" not in answer.model_dump_json()


@pytest.mark.asyncio
async def test_audit_schema_field_survives_into_public_failure_trace(runtime):
    from src.digital_twin.llm import LlmMalformedResponseError
    from src.digital_twin.grounding.models import GenerationUsage
    draft = Client()
    calls = []
    class Routed:
        async def chat(self, messages, task):
            calls.append(task)
            if task == 'final_response_quality_audit_v2':
                raise LlmMalformedResponseError(stage='schema-validation',
                    usage=GenerationUsage(input_tokens=4, output_tokens=3, total_tokens=7,
                                          approximate_cost_usd=.0002),
                    diagnostics={'schema_errors': [
                        {'location': ['entries', 0], 'type': 'value_error'},
                        {'location': ['PRIVATE_FIELD'], 'type': 'extra_forbidden'},
                    ]})
            return await draft.chat(messages, 'question_specific_compact_instruction')
    runtime[0].tutoring.generator = AuditedInstructionalGenerator(Routed(), model_id='gpt-5.6-luna',
        bounded_contract_enabled=True, named_referent_context_enabled=True)
    answer = await generate(runtime)
    assert len(calls) == 2 and answer.trace.policy_action == PolicyAction.SAFE_PROVIDER_FAILURE
    assert answer.content == QUARANTINE_TEXT and not answer.citations
    assert answer.trace.usage.total_tokens == 27
    assert answer.trace.usage.approximate_cost_usd == pytest.approx(.0003)
    assert 'audit_fields=entries.0:value_error,_:extra_forbidden' in answer.trace.validation_scope
    assert 'PRIVATE_FIELD' not in answer.model_dump_json()
