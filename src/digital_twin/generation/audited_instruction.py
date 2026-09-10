"""Actual-runtime integration of the fallible V2 final-response audit."""
from src.digital_twin.llm import LlmError, LlmMalformedResponseError
from .contract_repair import ContractRepairInstructionalGenerator
from .factual_revision import _sum_usage
from .final_response_audit import (
    AUDIT_FAILURE_CODES, AUDIT_FAILURE_STAGES, audit_final_response, QUARANTINE_TEXT,
    public_schema_fields, _failure_code,
)


def audit_payload(payload):
    """Translate application history to the auditor's public role vocabulary."""
    history = []
    for row in payload.get("learner_history", []):
        if not isinstance(row, dict) or set(row) - {"role", "content", "action"}:
            raise ValueError("invalid application history")
        role = {"student": "user", "tutor": "assistant", "user": "user", "assistant": "assistant"}.get(row.get("role"))
        if role is None or not isinstance(row.get("content"), str):
            raise ValueError("invalid application history")
        history.append({"role": role, "content": row["content"]})
    return {**payload, "learner_history": history}


class AuditedInstructionalGenerator(ContractRepairInstructionalGenerator):
    def __init__(self, client, *, audit_model="gpt-5.6-sol", **kwargs):
        if audit_model not in {"gpt-5.6-sol", "gpt-5.6-luna"}:
            raise ValueError("undeclared final audit model")
        super().__init__(client, **kwargs)
        self.implementation_id = "question-specific-profile-grounded-v18"
        self.version = "v18-development"
        self.audit_model = audit_model

    async def _request_proposal(self, payload, *, evidence, started):
        draft = await super()._request_proposal(payload, evidence=evidence, started=started)
        def render(proposal):
            return self._compose(proposal, evidence=evidence, trace_args={
                "generator_id": self.implementation_id, "provider_model": draft.provider_model,
                "provider_revision": draft.provider_revision, "prompt_version": self.implementation_id,
                "started": started, "clock": self.clock, "usage": draft.usage}).content
        try:
            prepared = audit_payload(self._prepare_payload(payload))
        except ValueError as error:
            # The draft call has already completed. Preserve its accounting while
            # retaining the same malformed-response decision and public message.
            raise LlmMalformedResponseError(stage="audit_input_preparation",
                usage=draft.usage, provider_model=draft.provider_model,
                provider_revision=draft.provider_revision) from error
        result = await audit_final_response(proposal_json=draft.content,
            payload=prepared, render=render,
            audit_client=self.client, repair_client=self.client, mode="quality", prompt_version="v2", expected_model=self.audit_model)
        usage = _sum_usage(draft.usage, result.usage)
        if result.proposal_json is None:
            raise LlmMalformedResponseError(stage="final_response_quarantined", usage=usage,
                provider_model=draft.provider_model,
                diagnostics={"audit_reason": result.reason, "audit_calls": result.calls,
                    "audit_stage": result.failure_stage, "audit_code": result.failure_code,
                    "audit_fields": result.failure_fields})
        return draft.model_copy(update={"content": result.proposal_json, "usage": usage,
            "provider_model": self.audit_model if result.outcome == "repaired" else draft.provider_model,
            "provider_revision": None if result.outcome == "repaired" else draft.provider_revision})

    def _failure_answer(self, error, *, response, started):
        answer = super()._failure_answer(error, response=response, started=started)
        if getattr(error, "stage", None) == "final_response_quarantined":
            answer = answer.model_copy(update={"content": QUARANTINE_TEXT})
            reason = getattr(error, "diagnostics", {}).get("audit_reason")
            if reason not in {"audit_rejected", "unchanged_repair", "repair_rejected", "contract_or_provider_failure"}:
                reason = "unknown"
            diagnostics = getattr(error, "diagnostics", {})
            stage, code = diagnostics.get("audit_stage"), diagnostics.get("audit_code")
            detail = ""
            if stage in AUDIT_FAILURE_STAGES and code in AUDIT_FAILURE_CODES:
                detail = "; audit_stage=" + stage + "; audit_code=" + code
                fields = public_schema_fields(diagnostics.get("audit_fields"))
                if fields:
                    detail += "; audit_fields=" + ",".join(fields)
            if answer.trace is not None:
                answer = answer.model_copy(update={"trace": answer.trace.model_copy(update={
                    "validation_scope": (answer.trace.validation_scope or "")
                        + "; final_response_quarantined=" + reason + detail,
                })})
        elif isinstance(error, LlmError) and answer.trace is not None:
            # Initial provider failures never reach the audit diagnostic branch.
            # Retain a bounded code, without changing the fallback or retry policy.
            answer = answer.model_copy(update={"trace": answer.trace.model_copy(update={
                "validation_scope": (answer.trace.validation_scope or "")
                    + "; generation_failure=" + _failure_code(error),
            })})
        return answer

    def _compose(self, proposal, *, evidence, trace_args):
        answer = super()._compose(proposal, evidence=evidence, trace_args=trace_args)
        if answer.trace is not None:
            answer = answer.model_copy(update={"trace": answer.trace.model_copy(update={
                "validation_scope": (answer.trace.validation_scope or "") +
                    "; final-response-quality-audit-v2-required; fallible-model-assessment-not-certification"})})
        return answer
