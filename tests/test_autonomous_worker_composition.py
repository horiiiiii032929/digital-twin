from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import autonomous_tutoring_worker as worker
from services.api.app import experimental
from tests.api.test_experimental_app import configured_settings
from scripts.verify_deployable_foundation import _close_app
from tests.test_paired_pedagogy_development import InstructionalContractClient


def test_no_selector_preserves_incumbent_builder(monkeypatch):
    monkeypatch.delenv("APP_EXPERIMENTAL_TUTORING_CANDIDATE", raising=False)
    settings, sentinel = object(), object()
    monkeypatch.setattr(worker, "create_app", lambda **kwargs: sentinel if kwargs == {"settings": settings} else None)
    assert worker.build_worker_app(settings) is sentinel


def test_worker_delegates_exact_selector_and_settings_without_ui(monkeypatch):
    monkeypatch.setenv("APP_EXPERIMENTAL_TUTORING_CANDIDATE", "v10-sol-low")
    calls = []
    def builder(settings, candidate, **kwargs):
        calls.append((settings, candidate, kwargs))
        return "selected"
    monkeypatch.setattr(experimental, "build_experimental_app", builder)
    settings = object()
    assert worker.build_worker_app(settings) == "selected"
    assert calls == [(settings, "v10-sol-low", {"serve_web": False})]


def test_unknown_selector_is_rejected_by_shared_builder(tmp_path):
    with pytest.raises(ValueError, match="unknown experimental"):
        worker.build_worker_app(configured_settings(tmp_path), candidate="unknown")


def _selected_settings(tmp_path, database_path):
    root = Path(__file__).resolve().parents[1]
    return replace(configured_settings(tmp_path), database_path=database_path,
        learning_gap_hmac_secret=b"synthetic-worker-test-secret-32-bytes",
        student_profile_path=root / "research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json",
        t1_qualification_result_path=root / "research/05_evaluation/records/governed-full-autonomy-v2-1-final-release-binding-001.json")


@pytest.mark.asyncio
async def test_selected_worker_processes_persisted_job_using_actual_selected_service(tmp_path, monkeypatch):
    from tests.digital_twin.test_governed_autonomy import _autonomy_fixture, _goal_and_opportunity, NOW
    repository, fixture, setup_service, release, _ = _autonomy_fixture(tmp_path)
    _, opportunity = _goal_and_opportunity(setup_service, fixture, release)
    repository.close()
    original = experimental.build_experimental_app
    called_tasks = []
    class RecordedContractClient(InstructionalContractClient):
        async def chat(self, messages, task):
            called_tasks.append(task)
            return await super().chat(messages, task)
    def injected(settings, candidate, **kwargs):
        return original(settings, candidate, transport=RecordedContractClient(candidate), **kwargs)
    monkeypatch.setattr(experimental, "build_experimental_app", injected)
    app = worker.build_worker_app(_selected_settings(tmp_path, tmp_path / "autonomy.sqlite3"), candidate="v10")
    try:
        assert app.state.experimental_tutoring_configuration["observed_implementation_id"] == "question-specific-profile-grounded-v10"
        service = app.state.governed_autonomy_service
        service.clock = SimpleNamespace(now=lambda: NOW)
        before = app.state.student_repository.get_autonomous_opportunity(opportunity.opportunity_id)
        assert before.status.value == "pending"
        await worker._process_once(app, worker_id="selected-worker-once", batch_size=1)
        after = app.state.student_repository.get_autonomous_opportunity(opportunity.opportunity_id)
        assert after.status.value != "pending"
        assert app.state.governed_autonomy_service is service
        assert app.state.student_repository.list_autonomous_actions(fixture.course_a_id)
        assert called_tasks, "Due job must reach the selected planner, not only a pre-planner rejection"
    finally:
        _close_app(app)


def test_worker_rejects_selector_mode_mismatch_before_processing(tmp_path):
    from scripts.verify_deployable_foundation import _settings
    with pytest.raises(ValueError, match="matching governed tutoring"):
        worker.build_worker_app(_settings(tmp_path), candidate="v10")


@pytest.mark.parametrize("candidate,model,reasoning", [
    ("v10-luna-low", "gpt-5.6-luna", "low"),
    ("v10-luna-medium", "gpt-5.6-luna", "medium"),
    ("v10-sol-low", "gpt-5.6-sol", "low"),
    ("v11-luna-low", "gpt-5.6-luna", "low"),
    ("v12-luna-sol", "gpt-5.6-luna", "low"),
    ("v13-luna-sol", "gpt-5.6-luna", "low"),
    ("v17-luna-low", "gpt-5.6-luna", "low"),
    ("v18-luna-sol-medium", "gpt-5.6-luna", "low"),
    ("v19-luna-sol-medium", "gpt-5.6-luna", "low"),
    ("v19-luna-luna-medium", "gpt-5.6-luna", "low"),
])
def test_worker_actual_role_composition_matches_api_selector(tmp_path, candidate, model, reasoning):
    app = worker.build_worker_app(_selected_settings(tmp_path, tmp_path / "worker.sqlite3"), candidate=candidate)
    try:
        configuration = app.state.experimental_tutoring_configuration
        observed = {entry["role"]: entry for entry in configuration["observed_openai_transport_configurations"]}
        assert observed["planner"] == {"role": "planner", "model": "gpt-5.6-luna", "reasoning_effort": "low", "output_cap": 3000}
        assert observed["generation"] == {"role": "generation", "model": model, "reasoning_effort": reasoning, "output_cap": 3000}
        if candidate in {"v12-luna-sol", "v13-luna-sol"}:
            assert observed["revision"] == {"role": "revision", "model": "gpt-5.6-sol", "reasoning_effort": "low", "output_cap": 3000}
        if candidate == "v19-luna-luna-medium":
            assert observed["revision"] == {"role": "revision", "model": "gpt-5.6-luna", "reasoning_effort": "medium", "output_cap": 3000}
            assert app.state.student_service.generator.audit_model == "gpt-5.6-luna"
        assert app.state.student_service.generator.model_id == model
        assert configuration["observed_implementation_id"] == "question-specific-profile-grounded-" + candidate.split("-")[0]
        if candidate in {"v18-luna-sol-medium", "v19-luna-sol-medium"}:
            assert observed["revision"] == {"role": "revision", "model": "gpt-5.6-sol", "reasoning_effort": "medium", "output_cap": 3000}
    finally:
        _close_app(app)


@pytest.mark.asyncio
@pytest.mark.parametrize("crash_after_delivery", [False, True])
@pytest.mark.parametrize("strategy_failure", [False, True])
@pytest.mark.parametrize("candidate", ["v19-luna-sol-medium", "v19-luna-luna-medium"])
async def test_post_report_worker_restart_preserves_single_delivery(tmp_path, monkeypatch, crash_after_delivery, strategy_failure, candidate):
    """Actual selected worker, SQLite reopen, lease expiry, and post-delivery crash."""
    from datetime import timedelta
    from src.digital_twin.clock import VirtualUtcClock
    from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
    from services.llm.experimental_role_routing import ExperimentalGenerationRoleRouter
    from scripts.run_mixed_source_recovery_development import SourceBoundContractClient
    from tests.digital_twin.test_governed_autonomy import _autonomy_fixture, _goal_and_opportunity, NOW
    repository, fixture, setup, release, _ = _autonomy_fixture(tmp_path)
    _, opportunity = _goal_and_opportunity(setup, fixture, release)
    repository.close()
    for name, value in {
        "APP_POST_REPORT_LEARNING": "assessed-count", "APP_POST_REPORT_PLANNER": "analytic-only",
        "APP_POST_REPORT_GOAL_RECOVERY": "true", "APP_POST_REPORT_MODEL_ASSESSMENT": "true",
        "APP_POST_REPORT_ASSESSMENT_VERSION": "v2", "APP_POST_REPORT_CONTEXT_RETRIEVAL": "true",
    }.items():
        monkeypatch.setenv(name, value)
    roles = experimental_tutoring_configuration(candidate)["role_configuration"]
    class WorkerContractClient(SourceBoundContractClient):
        def conservative_request_cost_usd(self, messages, task):
            return 0.001

        async def chat(self, messages, task):
            import json
            from src.digital_twin.llm import LlmResponse, LlmTimeoutError
            from src.digital_twin.grounding.models import GenerationUsage
            if task == "autonomous_tutoring_wording_strategy":
                self.calls += 1
                if strategy_failure:
                    raise LlmTimeoutError("synthetic strategy timeout")
                payload = json.loads(messages[-1].content)
                return LlmResponse(content=json.dumps({"schema_version": "1.0.0",
                    "opportunity_id": payload["opportunity_id"], "action": payload["action"],
                    "lead_style": "direct", "prompt_mode": "retrieve"}),
                    provider_model="gpt-5.6-luna", usage=GenerationUsage(approximate_cost_usd=0))
            raise AssertionError(f"Unexpected task in analytic proactive workflow: {task}")
    clients = {}
    for role, configuration in roles.items():
        client = WorkerContractClient(tmp_path / f"{role}.jsonl")
        client.experimental_transport_configuration = configuration
        clients[role] = client
    router = ExperimentalGenerationRoleRouter(planner_client=clients["planner"], generation_client=clients["generation"], revision_client=clients["revision"], role_configuration=roles)
    original = experimental.build_experimental_app
    monkeypatch.setattr(experimental, "build_experimental_app", lambda settings, candidate, **kw: original(settings, candidate, transport=router, **kw))
    settings = _selected_settings(tmp_path, tmp_path / "autonomy.sqlite3")
    app = worker.build_worker_app(settings, candidate=candidate)
    try:
        app.state.governed_autonomy_service.clock = VirtualUtcClock(NOW)
        assert app.state.post_report_learning_configuration["assessment"] == "source-bound-model-assessment-v2"
        assert app.state.governed_autonomy_service.graph.planner.implementation_id == "analytic-only-planner-v1"
        if crash_after_delivery:
            def crash(result):
                raise RuntimeError("synthetic post-delivery crash")
            monkeypatch.setattr(app.state.student_repository, "commit_autonomous_job", crash)
            with pytest.raises(RuntimeError, match="synthetic post-delivery crash"):
                await worker._process_once(app, worker_id="before-crash", batch_size=1)
        else:
            await worker._process_once(app, worker_id="before-restart", batch_size=1)
        assert len(app.state.proactive_outreach_service.list_inbox(fixture.student_a_id)) == 1
        lease = app.state.governed_autonomy_service.lease_seconds
    finally:
        _close_app(app)
    reopened = worker.build_worker_app(settings, candidate=candidate)
    try:
        reopened.state.governed_autonomy_service.clock = VirtualUtcClock(NOW + timedelta(seconds=lease + 1))
        await worker._process_once(reopened, worker_id="after-restart", batch_size=1)
        await worker._process_once(reopened, worker_id="replayed", batch_size=1)
        inbox = reopened.state.proactive_outreach_service.list_inbox(fixture.student_a_id)
        assert len(inbox) == 1
        actions = reopened.state.student_repository.list_autonomous_actions(fixture.course_a_id)
        matching = [a for a in actions if a.opportunity_id == opportunity.opportunity_id]
        assert len(matching) == 1 and matching[0].status.value == "delivered"
        # Proactive wording uses its bounded strategy path, not the reactive V19 generator.
        # Both bounded wording and the timeout fallback preserve one delivery.
        assert clients["generation"].calls == 0 and clients["revision"].calls == 0
        assert clients["planner"].calls > 0
        assert reopened.state.governed_autonomy_service.graph.planner.implementation_id == "analytic-only-planner-v1"
    finally:
        _close_app(reopened)
