"""Experimental learning flags share one factory across API and worker."""
import pytest

from services.api.app import experimental
from services.api.app.post_report_configuration import post_report_runtime_flags
from services.api.app.runtime_identity import runtime_identity
from scripts import autonomous_tutoring_worker as worker
from scripts.verify_deployable_foundation import _close_app
from tests.test_autonomous_worker_composition import _selected_settings
from tests.test_paired_pedagogy_development import InstructionalContractClient


@pytest.mark.parametrize("key,value", [
    ("APP_POST_REPORT_LEARNING", "latest"), ("APP_POST_REPORT_PLANNER", "automatic"),
    ("APP_POST_REPORT_GOAL_RECOVERY", "yes"), ("APP_POST_REPORT_SOURCE_ASSESSMENT", "1"),
])
def test_invalid_selectors_fail_closed(key, value):
    with pytest.raises(ValueError, match=key):
        post_report_runtime_flags({key: value})


def test_no_flags_preserves_historical_composition():
    assert post_report_runtime_flags({}) == {}


@pytest.mark.parametrize("estimator", ["assessed-count", "assessed-decay", "assessed-bkt", "assessed-pfa"])
@pytest.mark.parametrize("assessment_version", ["v1", "v2"])
def test_api_worker_select_same_actual_learning_components(tmp_path, monkeypatch, estimator, assessment_version):
    monkeypatch.setenv("APP_POST_REPORT_LEARNING", estimator)
    monkeypatch.setenv("APP_POST_REPORT_PLANNER", "analytic-only")
    monkeypatch.setenv("APP_POST_REPORT_GOAL_RECOVERY", "true")
    monkeypatch.setenv("APP_POST_REPORT_SOURCE_ASSESSMENT", "true")
    monkeypatch.setenv("APP_POST_REPORT_MODEL_ASSESSMENT", "true")
    monkeypatch.setenv("APP_POST_REPORT_ASSESSMENT_VERSION", assessment_version)
    monkeypatch.setenv("APP_POST_REPORT_CONTEXT_RETRIEVAL", "true")
    original = experimental.build_experimental_app
    def injected(settings, candidate, **kwargs):
        return original(settings, candidate, transport=InstructionalContractClient(candidate), **kwargs)
    monkeypatch.setattr(experimental, "build_experimental_app", injected)
    settings = _selected_settings(tmp_path, tmp_path / "shared.sqlite3")
    api = injected(settings, "v10")
    background = worker.build_worker_app(settings, candidate="v10")
    try:
        assert runtime_identity(api)["composition_sha256"] == runtime_identity(background)["composition_sha256"]
        for app in (api, background):
            planner = app.state.governed_autonomy_service.graph.planner
            assert planner.implementation_id == "analytic-only-planner-v1"
            assert planner.state_card_resolver.estimator.implementation_id == app.state.post_report_learning_configuration["estimator"]
            assert app.state.student_service.autonomy_goal_manager.implementation_id == "objective-scoped-recovery-v1"
            assert app.state.student_service.tutoring_graph.source_bound_assessment_enabled
            assert app.state.student_service.tutoring_graph.source_bound_model_assessor.model_id == "gpt-5.6-luna"
            assert app.state.student_service.conversation_retrieval_enabled
            assert app.state.post_report_learning_configuration["assessment"] == "source-bound-model-assessment-" + assessment_version
        api.state.post_report_learning_configuration["secret"] = "must-not-expose"
        assert "must-not-expose" not in str(runtime_identity(api))
    finally:
        _close_app(api)
        _close_app(background)


def test_worker_rejects_learning_flags_without_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_POST_REPORT_LEARNING", "assessed-count")
    with pytest.raises(ValueError, match="explicit experimental"):
        worker.build_worker_app(_selected_settings(tmp_path, tmp_path / "unused.sqlite3"), candidate="")
