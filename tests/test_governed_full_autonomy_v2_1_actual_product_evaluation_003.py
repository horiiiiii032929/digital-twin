from datetime import UTC, datetime
import json

import pytest

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_003 as builder,
)
from scripts.governed_full_autonomy_v2_1_actual_product_runtime import (
    build_runtime_factory,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_evaluation_003 as runner,
)
from src.digital_twin.evaluation import run_autonomy_case, score_autonomy_case
from src.digital_twin.evaluation.autonomy_product_adapter import (
    StudentProductAutonomyAdapterV1,
)
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.grounding import (
    SourceSemanticEvidenceAtomGateV2,
    SourceSemanticEvidenceAtomRetrieverV1,
)


def test_successor_binds_selected_grounding_and_preserves_portfolio() -> None:
    result = builder.validate()
    instrument = json.loads(builder.INSTRUMENT.read_text(encoding="utf-8"))

    assert result["status"] == "passed-build-only"
    assert result["case_count"] == 820
    assert instrument["selected_grounding"]["architecture_id"] == (
        "ambiguity-safe-source-semantic-evidence-atoms-v2"
    )
    assert instrument["selected_grounding"]["rollback_architecture_id"] == (
        "source-semantic-evidence-atoms-v1"
    )
    assert instrument["execution"]["selected_retriever"] == (
        "source-semantic-evidence-atom-retriever-v1"
    )
    assert instrument["execution"]["selected_evidence_gate"] == (
        "source-semantic-evidence-atom-gate-v2"
    )


def test_successor_preflight_recognizes_revoked_authority() -> None:
    result = runner.preflight()

    assert result["status"] in {"blocked-not-authorized", "ready"}
    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
    assert "repository-freeze-authorization-missing" in result["blockers"]
    assert not any("keep-missing" in row for row in result["blockers"])
    assert result["provider_calls"] == 0
    assert result["hidden_gold_loaded"] is False


@pytest.mark.asyncio
async def test_selected_grounding_crosses_actual_product_service(tmp_path) -> None:
    condition, case, gold = next(
        row
        for row in builder.build_contract()
        if row[1].case_id == "trajectory-006-t1-v2-reactive-seed-1"
    )
    manifest = runner.shared._manifest(  # noqa: SLF001 - frozen harness seam
        condition,
        network_free=True,
        context=runner.CONTEXT,
    )
    probe_factory = build_runtime_factory(
        tmp_path / "probe",
        condition,
        provider_backed=False,
        grounding_architecture_id=(
            "ambiguity-safe-source-semantic-evidence-atoms-v2"
        ),
    )
    probe = probe_factory(
        case,
        VirtualUtcClock(datetime(2026, 9, 1, 12, 0, tzinfo=UTC)),
    )
    try:
        assert isinstance(probe.tutoring.evidence_gate, SourceSemanticEvidenceAtomGateV2)
        release = probe.repository.get_published_release(probe.course_id)
        assert release is not None
        assert isinstance(
            probe.tutoring.retriever_factory(release.chunks, {}),
            SourceSemanticEvidenceAtomRetrieverV1,
        )
    finally:
        probe.repository.close()

    adapter = StudentProductAutonomyAdapterV1(
        condition=condition,
        manifest=manifest,
        runtime_factory=build_runtime_factory(
            tmp_path / "run",
            condition,
            provider_backed=False,
            grounding_architecture_id=(
                "ambiguity-safe-source-semantic-evidence-atoms-v2"
            ),
        ),
        clock_origin=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
    )
    try:
        response = await run_autonomy_case(adapter, case)
        score = score_autonomy_case(case, gold, response)
    finally:
        adapter.close()

    assert score.hard_gates_passed, score.failure_codes
    assert response.provider_calls == 0
