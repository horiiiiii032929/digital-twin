from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.build_academic_factual_qa_confirmation_v2 import canonical_sha256
from scripts.build_academic_factual_qa_visual_supplement import (
    DATASET_PATH,
    build_dataset,
    validate_dataset,
)
from scripts.run_academic_factual_qa_visual_checkpoint import (
    PILOT_STAGE,
    QUALIFICATION_STAGE,
    SimulatedVisualProvider,
    _describe_all,
    _audit_outcome,
    _qualification_summary,
    _simulated_facts_for_synthetic,
    _simulated_facts_for_visual,
    preflight,
    run_stage,
    validate_checkpoint,
)
from src.digital_twin.evaluation.visual_description import (
    VisualDescription,
    VisualDescriptionError,
    VisualRegionLineage,
)


def test_visual_supplement_is_reproducible_balanced_and_parent_disjoint() -> None:
    committed = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    rebuilt = build_dataset(write_assets=False)

    assert rebuilt == committed
    validate_dataset(committed)
    assert committed["cluster_count"] == 30
    assert committed["case_count"] == 60
    assert committed["answerable_case_count"] == 30
    assert committed["boundary_case_count"] == 30
    assert {
        name: sum(row["modality"] == name for row in committed["assets"])
        for name in ("table", "diagram", "equation")
    } == {"table": 10, "diagram": 10, "equation": 10}


def test_visual_description_requires_original_hash_bound_region_lineage() -> None:
    digest = hashlib.sha256(b"image").hexdigest()
    region = VisualRegionLineage(
        source_id="source-1",
        asset_id="asset-1",
        region_id="region-1",
        image_sha256=digest,
        bbox=(0.0, 0.0, 1.0, 1.0),
    )
    description = VisualDescription(
        transcription="A visible label.",
        entities=("label",),
        relationships=("The label is above the arrow.",),
        uncertainty=(),
        provider_model="google/gemini-3.7-flash",
        provider_revision="google/gemini-3.7-flash-20260813",
        provider_name="Google",
        source_image_sha256=digest,
        region_lineage=(region,),
    )

    assert description.to_record()["region_lineage"][0]["region_id"] == "region-1"
    with pytest.raises(VisualDescriptionError, match="hashes differ"):
        VisualDescription(
            **{
                **description.__dict__,
                "source_image_sha256": hashlib.sha256(b"other").hexdigest(),
            }
        )
    with pytest.raises(VisualDescriptionError, match="relationships must be unique"):
        VisualDescription(
            **{
                **description.__dict__,
                "relationships": ("same", "same"),
            }
        )


def test_visual_preflight_is_network_free_and_fail_closed(tmp_path: Path) -> None:
    result = preflight(
        QUALIFICATION_STAGE,
        live=False,
        output=tmp_path / "qualification.json",
    )

    assert result["status"] == "blocked-not-authorized"
    assert "stage-not-authorized" in result["blockers"]
    assert "bounded-freeze-authorization-missing" in result["blockers"]
    assert "live-provider-metadata-not-current" in result["blockers"]
    assert result["provider_calls"] == 0


def test_visual_simulations_preserve_gates_and_never_select_profile(
    tmp_path: Path,
) -> None:
    checkpoint = validate_checkpoint()
    qualification = asyncio.run(
        run_stage(
            QUALIFICATION_STAGE,
            provider=SimulatedVisualProvider(
                _simulated_facts_for_synthetic(checkpoint["synthetic"])
            ),
            output=tmp_path / "qualification.json",
        )
    )
    pilot = asyncio.run(
        run_stage(
            PILOT_STAGE,
            provider=SimulatedVisualProvider(
                _simulated_facts_for_visual(checkpoint["dataset"])
            ),
            output=tmp_path / "pilot.json",
        )
    )

    assert qualification["status"] == "completed-keep"
    assert qualification["summary"]["visual_fact_recall"] == 1.0
    assert pilot["status"] in {"completed-go-deeper", "completed-refine"}
    assert pilot["summary"]["profile_selected"] is False
    assert pilot["summary"]["boundary_release_count"] == 0
    assert pilot["provider_calls"] == 30


def test_uncovered_visual_fact_requires_explicit_codex_audit(tmp_path: Path) -> None:
    checkpoint = validate_checkpoint()
    ledger = asyncio.run(
        run_stage(
            QUALIFICATION_STAGE,
            provider=SimulatedVisualProvider(
                _simulated_facts_for_synthetic(checkpoint["synthetic"])
            ),
            output=tmp_path / "qualification.json",
        )
    )
    changed = deepcopy(ledger)
    changed["descriptions"][0]["description"]["relationships"] = (
        *changed["descriptions"][0]["description"]["relationships"],
        "Quantum teleportation is guaranteed.",
    )
    summary = _qualification_summary(changed, checkpoint["synthetic"])

    assert summary["decision"] is None
    assert summary["fact_audit_complete"] is False
    assert len(summary["unsupported_fact_audit_candidates"]) == 1
    candidate = summary["unsupported_fact_audit_candidates"][0]
    audit = {
        "stage": QUALIFICATION_STAGE,
        "decisions": [
            {
                "asset_id": candidate["asset_id"],
                "fact_sha256": candidate["fact_sha256"],
                "verdict": "unsupported",
            }
        ],
    }
    outcome = _audit_outcome(
        summary["unsupported_fact_audit_candidates"],
        audit,
        stage=QUALIFICATION_STAGE,
    )
    assert outcome == {"complete": True, "unsupported_count": 1, "audited_count": 1}


def test_visual_description_ledger_resumes_without_repeating_completed_assets(
    tmp_path: Path,
) -> None:
    checkpoint = validate_checkpoint()
    facts = _simulated_facts_for_synthetic(checkpoint["synthetic"])

    class InterruptingProvider(SimulatedVisualProvider):
        def __init__(self):
            super().__init__(facts)
            self.calls = 0

        async def describe(self, **kwargs):
            self.calls += 1
            if self.calls == 3:
                raise KeyboardInterrupt()
            return await super().describe(**kwargs)

    output = tmp_path / "qualification-ledger.json"
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(
            _describe_all(
                stage=QUALIFICATION_STAGE,
                assets=checkpoint["synthetic"]["source_assets"],
                provider=InterruptingProvider(),
                output=output,
                maximum_calls=9,
                hard_stop=1.0,
                binding_sha256=checkpoint["binding"]["content_sha256"],
                source_sha256=canonical_sha256(checkpoint["synthetic"]),
            )
        )
    interrupted = json.loads(output.read_text(encoding="utf-8"))
    assert interrupted["provider_calls"] == 2
    resumed_provider = SimulatedVisualProvider(facts)
    completed = asyncio.run(
        _describe_all(
            stage=QUALIFICATION_STAGE,
            assets=checkpoint["synthetic"]["source_assets"],
            provider=resumed_provider,
            output=output,
            maximum_calls=9,
            hard_stop=1.0,
            binding_sha256=checkpoint["binding"]["content_sha256"],
            source_sha256=interrupted["source_sha256"],
            resume=True,
        )
    )
    assert completed["provider_calls"] == 9
    assert completed["resume_count"] == 1
    assert len(completed["descriptions"]) == 9


def test_visual_description_ledger_stops_before_call_at_budget_boundary(
    tmp_path: Path,
) -> None:
    checkpoint = validate_checkpoint()

    class FailIfCalledProvider(SimulatedVisualProvider):
        def __init__(self):
            super().__init__({})
            self.calls = 0

        async def describe(self, **kwargs):
            self.calls += 1
            raise AssertionError("budget stop must occur before provider transport")

    provider = FailIfCalledProvider()
    ledger = asyncio.run(
        _describe_all(
            stage=QUALIFICATION_STAGE,
            assets=checkpoint["synthetic"]["source_assets"],
            provider=provider,
            output=tmp_path / "qualification-ledger.json",
            maximum_calls=9,
            hard_stop=0.0,
            binding_sha256=checkpoint["binding"]["content_sha256"],
            source_sha256=canonical_sha256(checkpoint["synthetic"]),
        )
    )

    assert provider.calls == 0
    assert ledger["status"] == "invalid-execution"
    assert ledger["provider_calls"] == 0
    assert ledger["failures"] == ["pre-call-budget-stop"]
