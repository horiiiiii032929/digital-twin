#!/usr/bin/env python3
"""Execute public factual-QA inputs without importing or reading hidden gold."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Callable
from datetime import datetime, timezone

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationResponseV1,
    EvaluationSplit,
    SystemUnderTestManifestV1,
    TutorEvaluationAdapterV1,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    ResponseLedgerV1,
    canonical_json_sha256,
    execute_cases,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    BOUNDED_PILOT_AUTHORIZATIONS,
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_ID = "academic-factual-qa-open-10000-v1"
INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_open_10000_v1.json"
)
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
DEFAULT_CASES = DATASET_ROOT / "academic_factual_qa_open_10000_v1_cases.json"
DEFAULT_MANIFEST = (
    ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_open_10000_v1_t0_candidate_manifest.json"
)
DEFAULT_OUTPUT = (
    ROOT / "reports/generated/academic-factual-qa-open-10000-v1-responses.sqlite3"
)
DEFAULT_PROVIDER_LEDGER = (
    ROOT / "reports/generated/academic-factual-qa-open-10000-v1-provider.sqlite3"
)
DEFAULT_STATE = (
    ROOT / "reports/generated/academic-factual-qa-open-10000-v1-product-state.sqlite3"
)
PROVIDER_BINDING_PATH = (
    ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_open_10000_provider_binding_002.json"
)


class OpenBenchmarkExecutionError(RuntimeError):
    """Raised when a live run would violate the execution boundary."""


class _NetworkFreeAdapter:
    adapter_version = "v1"

    def __init__(self, flow_id: str) -> None:
        self.flow_id = flow_id

    async def evaluate(self, case: EvaluationCaseV1) -> EvaluationResponseV1:
        return EvaluationResponseV1(
            case_id=case.case_id,
            flow_id=self.flow_id,
            action=EvaluationAction.ABSTAIN,
            answer="Network-free simulation does not release a factual answer.",
            operational_status="simulated",
            provider_model="not-called",
            trace={"simulation": True},
        )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _load_public_cases(path: Path) -> tuple[dict[str, Any], list[EvaluationCaseV1]]:
    payload = _load_json(path)
    allowed = {
        "schema_version",
        "dataset_id",
        "split",
        "case_count",
        "cases",
        "content_sha256",
    }
    if set(payload) - allowed:
        raise OpenBenchmarkExecutionError("public input package contains forbidden fields")
    rows = [EvaluationCaseV1.model_validate(row) for row in payload.get("cases", [])]
    if payload.get("case_count") != len(rows):
        raise OpenBenchmarkExecutionError("public input case count drifted")
    expected_hash = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != expected_hash:
        raise OpenBenchmarkExecutionError("public input package hash drifted")
    return payload, rows


def _load_manifest(path: Path) -> SystemUnderTestManifestV1:
    return SystemUnderTestManifestV1.model_validate(_load_json(path))


def _load_adapter(
    factory_path: str,
    *,
    manifest: SystemUnderTestManifestV1,
    cases: list[EvaluationCaseV1],
    runtime: dict[str, Any],
) -> TutorEvaluationAdapterV1:
    module_name, separator, function_name = factory_path.partition(":")
    if not separator or not module_name or not function_name:
        raise OpenBenchmarkExecutionError(
            "adapter factory must use the module:function form"
        )
    factory: Callable[..., TutorEvaluationAdapterV1] = getattr(
        importlib.import_module(module_name), function_name
    )
    adapter = factory(manifest=manifest, cases=cases, runtime=runtime)
    if adapter.flow_id != manifest.flow_id or adapter.adapter_version != manifest.adapter_version:
        raise OpenBenchmarkExecutionError("adapter and system manifest identities differ")
    return adapter


def validate_contract() -> dict[str, Any]:
    instrument = _load_json(INSTRUMENT_PATH)
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise OpenBenchmarkExecutionError("instrument identity drifted")
    execution = instrument["execution"]
    if execution["response_process_can_import_gold_module"]:
        raise OpenBenchmarkExecutionError("response process gold-import boundary drifted")
    if execution["response_process_can_load_gold_path"]:
        raise OpenBenchmarkExecutionError("response process gold-path boundary drifted")
    if not execution["atomic_sqlite_checkpoints"] or not execution[
        "exclusive_output_creation"
    ]:
        raise OpenBenchmarkExecutionError("response persistence contract drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed",
        "public_case_fields": sorted(EvaluationCaseV1.model_fields),
        "provider_calls": 0,
        "reference_answers_loaded": False,
    }


def preflight(
    *,
    stage: str,
    cases_path: Path,
    manifest_path: Path,
    output: Path,
    provider_ledger: Path,
    state_path: Path,
    resume: bool,
) -> dict[str, Any]:
    validate_contract()
    instrument = _load_json(INSTRUMENT_PATH)
    blockers: list[str] = []
    if instrument["allocation"]["status"] != "frozen-approved":
        blockers.append("source-allocation-not-approved")
    required_authorities = [
        "provider_execution_authorized",
        "paid_execution_authorized",
    ]
    if stage == "development":
        required_authorities.append("development_execution_authorized")
    else:
        required_authorities.append("final_execution_authorized")
    for key in required_authorities:
        if not instrument["execution"][key]:
            blockers.append(f"{key.replace('_', '-')}-false")
    if INSTRUMENT_ID not in BOUNDED_PILOT_AUTHORIZATIONS:
        blockers.append("bounded-freeze-authorization-missing")
    if not cases_path.is_file():
        blockers.append("public-input-package-missing")
    if not manifest_path.is_file():
        blockers.append("system-manifest-missing")
    if _repo_dirty():
        blockers.append("working-tree-dirty")
    if not os.getenv("DEEPSEEK_API_KEY", "").strip():
        blockers.append("deepseek-credential-missing")
    if not PROVIDER_BINDING_PATH.is_file():
        blockers.append("provider-binding-missing")
    else:
        binding = _load_json(PROVIDER_BINDING_PATH)
        try:
            expected_binding_hash = canonical_json_sha256(
                {
                    key: value
                    for key, value in binding.items()
                    if key != "content_sha256"
                }
            )
            if binding.get("content_sha256") != expected_binding_hash:
                blockers.append("provider-binding-hash-drifted")
            binding_authorization = binding.get("authorization", {})
            binding_keys = [
                "provider_execution_authorized",
                "paid_execution_authorized",
                (
                    "development_execution_authorized"
                    if stage == "development"
                    else "final_execution_authorized"
                ),
            ]
            for key in binding_keys:
                if not binding_authorization.get(key, False):
                    blockers.append(
                        f"provider-binding-{key.replace('_', '-')}-false"
                    )
            verified_at = datetime.fromisoformat(binding["verified_at"])
            age = (
                datetime.now(timezone.utc) - verified_at.astimezone(timezone.utc)
            ).total_seconds() / 3600
            if age > instrument["execution"]["provider_metadata_freshness_hours"]:
                blockers.append("provider-metadata-stale")
        except (KeyError, TypeError, ValueError):
            blockers.append("provider-binding-invalid")
    runtime_outputs = (output, provider_ledger, state_path)
    if resume:
        for path in runtime_outputs:
            if not path.is_file():
                blockers.append(f"resume-{path.stem}-missing")
    else:
        for path in runtime_outputs:
            if path.exists():
                blockers.append(f"exclusive-{path.stem}-used")
    return {
        "instrument_id": INSTRUMENT_ID,
        "stage": stage,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "provider_calls": 0,
        "reference_answers_loaded": False,
        "credential_values_emitted": False,
    }


def _simulated_cases() -> list[EvaluationCaseV1]:
    return [
        EvaluationCaseV1(
            case_id=f"simulation-{index:02d}",
            cluster_id=f"simulation-cluster-{index:02d}",
            source_family_id=f"simulation-family-{index:02d}",
            course_id="simulation-course",
            question=f"Synthetic public question {index}?",
            split=EvaluationSplit.DEVELOPMENT,
            slice="direct-factual" if index % 2 == 0 else "no-evidence",
            author_family="network-free-fixture",
        )
        for index in range(10)
    ]


async def simulate() -> dict[str, Any]:
    cases = _simulated_cases()
    manifests = [
        SystemUnderTestManifestV1(
            flow_id=flow_id,
            adapter_version="v1",
            code_revision=_repo_revision(),
            profile_sha256="0" * 64,
            retriever="network-free-fixture",
            generator="network-free-fixture",
            policy="network-free-fixture",
            evidence_gate="network-free-fixture",
        )
        for flow_id in ("t0", "t1-graph", "t2-graph", "http", "any-hit-control")
    ]
    snapshots: list[dict[str, str | int]] = []
    with tempfile.TemporaryDirectory(prefix="academic-open-10000-simulation-") as directory:
        root = Path(directory)
        for manifest in manifests:
            ledger = ResponseLedgerV1(
                root / f"{manifest.flow_id}.sqlite3",
                cases_sha256=canonical_json_sha256(
                    [row.model_dump(mode="json") for row in cases]
                ),
                system_manifest_sha256=canonical_json_sha256(
                    manifest.model_dump(mode="json")
                ),
                run_configuration_sha256="0" * 64,
                resume=False,
            )
            try:
                snapshots.append(
                    await execute_cases(
                        cases=cases,
                        adapter=_NetworkFreeAdapter(manifest.flow_id),
                        manifest=manifest,
                        ledger=ledger,
                    )
                )
            finally:
                ledger.close()
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "simulated-network-free",
        "adapter_count": len(manifests),
        "case_count_per_adapter": len(cases),
        "snapshots": snapshots,
        "provider_calls": 0,
        "reference_answers_loaded": False,
    }


async def execute(
    *,
    cases_path: Path,
    manifest_path: Path,
    output: Path,
    adapter_factory: str,
    provider_ledger: Path,
    state_path: Path,
    resume: bool,
) -> dict[str, Any]:
    public_package, cases = _load_public_cases(cases_path)
    manifest = _load_manifest(manifest_path)
    runtime = {
        "instrument_id": INSTRUMENT_ID,
        "cases_sha256": public_package["content_sha256"],
        "code_revision": _repo_revision(),
        "provider_ledger_path": str(provider_ledger),
        "state_path": str(state_path),
        "resume": resume,
    }
    adapter = _load_adapter(
        adapter_factory, manifest=manifest, cases=cases, runtime=runtime
    )
    run_configuration = {
        "instrument_id": INSTRUMENT_ID,
        "dataset_id": public_package["dataset_id"],
        "split": public_package["split"],
        "code_revision": _repo_revision(),
        "manifest": manifest.model_dump(mode="json"),
        "zero_retries": True,
    }
    ledger = ResponseLedgerV1(
        output,
        cases_sha256=public_package["content_sha256"],
        system_manifest_sha256=canonical_json_sha256(
            manifest.model_dump(mode="json")
        ),
        run_configuration_sha256=canonical_json_sha256(run_configuration),
        resume=resume,
    )
    try:
        snapshot = await execute_cases(
            cases=cases, adapter=adapter, manifest=manifest, ledger=ledger
        )
    finally:
        ledger.close()
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "responses-completed",
        "ledger": snapshot,
        "reference_answers_loaded": False,
    }


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--stage", choices=("development", "final"), default="development")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--provider-ledger", type=Path, default=DEFAULT_PROVIDER_LEDGER)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--adapter-factory")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
        ready = preflight(
            stage=arguments.stage,
            cases_path=arguments.cases,
            manifest_path=arguments.manifest,
            output=arguments.output,
            provider_ledger=arguments.provider_ledger,
            state_path=arguments.state_path,
            resume=arguments.resume,
        )
        if ready["status"] != "ready":
            raise OpenBenchmarkExecutionError(
                f"live response execution is blocked: {ready['blockers']}"
            )
        if not arguments.adapter_factory:
            parser.error("--execute requires --adapter-factory module:function")
        result = asyncio.run(
            execute(
                cases_path=arguments.cases,
                manifest_path=arguments.manifest,
                output=arguments.output,
                adapter_factory=arguments.adapter_factory,
                provider_ledger=arguments.provider_ledger,
                state_path=arguments.state_path,
                resume=arguments.resume,
            )
        )
    elif arguments.preflight:
        result = preflight(
            stage=arguments.stage,
            cases_path=arguments.cases,
            manifest_path=arguments.manifest,
            output=arguments.output,
            provider_ledger=arguments.provider_ledger,
            state_path=arguments.state_path,
            resume=arguments.resume,
        )
    elif arguments.simulate:
        result = asyncio.run(simulate())
    else:
        result = validate_contract()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
