"""Offline V19 context/binding control; not a teaching-quality evaluation."""
import hashlib
import json

import pytest

from src.digital_twin.generation.instructional_source_state import SourceStateInstructionalGenerator
from tests.test_compact_instruction_generation import runtime, Client, QUESTION
from tests.test_final_response_audit import VersionedAudit


@pytest.mark.asyncio
async def test_seven_turns_keep_recent_history_and_exact_audit_bindings(runtime):
    rt = runtime[0]
    drafts, audits = [], []
    draft = Client()
    audit = VersionedAudit()

    class Routed:
        async def chat(self, messages, task):
            payload = json.loads(messages[-1].content)
            if task == "final_response_quality_audit_v2":
                audits.append(payload)
                response = await audit.chat(messages, task)
                return response.model_copy(update={"provider_model": "gpt-5.6-luna"})
            drafts.append(payload)
            return await draft.chat(messages, "question_specific_compact_instruction")

    rt.tutoring.generator = SourceStateInstructionalGenerator(
        Routed(), model_id="gpt-5.6-luna", audit_model="gpt-5.6-luna",
        bounded_contract_enabled=True, named_referent_context_enabled=True)
    history = []
    for i in range(7):
        result = await rt.tutoring.submit_message(rt.student_id, rt.conversation_id,
            content=f"{QUESTION} Visit {i+1}: Ari’s example — café.",
            client_request_id=f"context-control-{i}")
        assert result.tutor_message.action == "answer"
        assert drafts[-1]["learner_history"] == history[-10:]
        snapshot = audits[-1]
        assert snapshot["context"]["learner_history"] == [
            {"role": {"student": "user", "tutor": "assistant"}[r["role"]], "content": r["content"]}
            for r in history[-10:]
        ]
        canonical = json.dumps(snapshot["context"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        assert snapshot["context_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()
        assert snapshot["rendered_sha256"] == hashlib.sha256(result.tutor_message.content.encode()).hexdigest()
        history.extend([
            {"role": "student", "content": result.student_message.content, "action": result.student_message.action},
            {"role": "tutor", "content": result.tutor_message.content, "action": result.tutor_message.action},
        ])
    assert len(drafts) == len(audits) == 7  # no hidden additional retries
    assert len(audits[-1]["context"]["learner_history"]) == 10
