"""Validate or execute the frozen synthetic generator qualification.

Development execution is external-provider work and requires an explicit flag
plus the environment-owned credential. Held-out execution has an additional
one-time confirmation and accepts exactly one prompt condition.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import statistics
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.llm import LiteLlmClient
from src.digital_twin.generation import (
    ConservativeGroundedPromptBuilder,
    GroundedPromptBuilder,
    LiveGroundedGenerator,
    StrictEvidenceGroundedPromptBuilder,
)
from src.digital_twin.grounding import DocumentChunk, RetrievalHit
from src.digital_twin.tutor_policy import (
    FieldStatus,
    ReleaseStatus,
    build_initial_policy,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/generator_qualification_v1.json"
)
FREEZE_PATH = ROOT / "research/05_evaluation/generator_qualification_v1_freeze.json"
HELDOUT_LEDGER_PATH = (
    ROOT / "data/processed/generator_qualification_v1/heldout_access.json"
)
PROMPTS = {
    "P0": GroundedPromptBuilder,
    "P1": ConservativeGroundedPromptBuilder,
    "P2": StrictEvidenceGroundedPromptBuilder,
}


class GeneratorQualificationError(ValueError):
    """Raised when the qualification boundary is incomplete or has drifted."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GeneratorQualificationError(f"cannot load JSON: {path}") from error
    if not isinstance(value, dict):
        raise GeneratorQualificationError(f"JSON root must be an object: {path}")
    return value


def validate_assets(instrument_path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    instrument = load_json(instrument_path)
    freeze = load_json(FREEZE_PATH)
    _validate_instrument(instrument)
    expected_freeze_instrument = instrument.get(
        "dataset_freeze_instrument_id",
        instrument["instrument_id"],
    )
    if freeze.get("instrument_id") != expected_freeze_instrument:
        raise GeneratorQualificationError("freeze manifest instrument mismatch")
    if freeze.get("heldout_access_state") != "sealed-unopened":
        raise GeneratorQualificationError("held-out generator split is not sealed")

    datasets = {}
    development_families = set()
    for split, expected_count in (("development", 48), ("heldout", 104)):
        record = freeze.get("splits", {}).get(split, {})
        path = ROOT / str(record.get("path", ""))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != record.get("sha256"):
            raise GeneratorQualificationError(f"{split} dataset hash drifted")
        if record.get("case_count") != expected_count:
            raise GeneratorQualificationError(f"{split} manifest count drifted")
        expected_status = "approved" if split == "development" else "sealed"
        if record.get("dataset_status") != expected_status:
            raise GeneratorQualificationError(f"{split} manifest status drifted")
        expected_per_scenario = 6 if split == "development" else 13
        if any(
            record.get("scenario_counts", {}).get(scenario) != expected_per_scenario
            for scenario in instrument["dataset"]["scenario_types"]
        ):
            raise GeneratorQualificationError(f"{split} manifest slices drifted")
        if record.get("semantic_validation") != "passed-at-seal":
            raise GeneratorQualificationError(
                f"{split} semantic seal evidence is missing"
            )
        dataset = None
        if split == "development":
            dataset = load_json(path)
            _validate_dataset(dataset, split=split, expected_count=expected_count)
            development_families = {case["case_family_id"] for case in dataset["cases"]}
        datasets[split] = {
            "path": path,
            "dataset": dataset,
            "sha256": digest,
            "case_count": expected_count,
            "status": expected_status,
        }
    if not development_families:
        raise GeneratorQualificationError("development case families are missing")

    return {"instrument": instrument, "freeze": freeze, "datasets": datasets}


def _validate_instrument(instrument: dict[str, Any]) -> None:
    if instrument.get("schema_version") != 1:
        raise GeneratorQualificationError("unsupported instrument schema")
    instrument_id = instrument.get("instrument_id")
    if instrument_id not in {
        "generator-qualification-v1",
        "generator-qualification-v1-development-attempt-002",
        "generator-qualification-v1-development-stability-001",
        "generator-qualification-v1-heldout-001",
    }:
        raise GeneratorQualificationError("unexpected instrument id")
    if instrument.get("status") != "frozen-pending-execution":
        raise GeneratorQualificationError("instrument is not frozen for execution")
    binding = instrument.get("candidate_binding", {})
    expected = {
        "litellm_model": "deepseek/deepseek-v4-flash",
        "provider_model": "deepseek-v4-flash",
        "data_boundary": "synthetic-public-only",
    }
    for field, value in expected.items():
        if binding.get(field) != value:
            raise GeneratorQualificationError(f"candidate binding drifted: {field}")
    decoding = binding.get("decoding", {})
    if decoding.get("thinking") != "disabled":
        raise GeneratorQualificationError("thinking mode must remain disabled")
    if decoding.get("temperature") != 0 or decoding.get("max_attempts") != 1:
        raise GeneratorQualificationError("decoding or retry policy drifted")
    prompt_ids = [item.get("condition_id") for item in instrument["prompt_candidates"]]
    expected_prompts = (
        ["P0", "P1"] if instrument_id == "generator-qualification-v1" else ["P2"]
    )
    if prompt_ids != expected_prompts:
        raise GeneratorQualificationError("prompt candidates drifted")
    if instrument.get("budget", {}).get("cumulative_issue_cap_usd") != 10:
        raise GeneratorQualificationError("external cost cap drifted")


def _validate_dataset(
    dataset: dict[str, Any], *, split: str, expected_count: int
) -> None:
    if dataset.get("schema_version") != "1.0.0":
        raise GeneratorQualificationError(f"{split} schema mismatch")
    if dataset.get("dataset_id") != "generator-qualification-v1":
        raise GeneratorQualificationError(f"{split} dataset id mismatch")
    if dataset.get("split") != split:
        raise GeneratorQualificationError(f"{split} split mismatch")
    expected_status = "approved" if split == "development" else "sealed"
    if dataset.get("dataset_status") != expected_status:
        raise GeneratorQualificationError(f"{split} status mismatch")
    boundary = dataset.get("data_boundary", {})
    if boundary.get("content_class") != "synthetic_public":
        raise GeneratorQualificationError(f"{split} is not synthetic-public")
    if boundary.get("private_course_text") is not False:
        raise GeneratorQualificationError(f"{split} private-data boundary failed")
    cases = dataset.get("cases")
    if not isinstance(cases, list) or len(cases) != expected_count:
        raise GeneratorQualificationError(f"{split} case count mismatch")
    identifiers = [case.get("case_id") for case in cases]
    if len(identifiers) != len(set(identifiers)):
        raise GeneratorQualificationError(f"{split} duplicate case ids")
    expected_per_scenario = 6 if split == "development" else 13
    for scenario in (
        "direct",
        "paraphrase",
        "misconception",
        "multi_evidence",
        "ambiguity",
        "no_evidence",
        "assessed_work",
        "permission_version",
    ):
        count = sum(case.get("scenario_type") == scenario for case in cases)
        if count != expected_per_scenario:
            raise GeneratorQualificationError(
                f"{split} scenario imbalance for {scenario}: {count}"
            )
    for case in cases:
        _validate_case(case)


def _validate_case(case: dict[str, Any]) -> None:
    evidence = case.get("candidate_evidence")
    if not isinstance(evidence, list) or not evidence:
        raise GeneratorQualificationError(f"missing evidence: {case.get('case_id')}")
    evidence_ids = [item.get("evidence_id") for item in evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise GeneratorQualificationError(f"duplicate evidence: {case['case_id']}")
    presented = [item for item in evidence if item.get("presented")]
    if any(
        item.get("permission") != "approved" or item.get("active") is not True
        for item in presented
    ):
        raise GeneratorQualificationError(
            f"unsafe evidence presented: {case['case_id']}"
        )
    action = case.get("expected_action")
    if action not in {"answer", "clarify", "abstain", "redirect"}:
        raise GeneratorQualificationError(f"invalid action: {case['case_id']}")
    if case.get("citation_required") != (action == "answer"):
        raise GeneratorQualificationError(
            f"citation expectation mismatch: {case['case_id']}"
        )
    if action == "abstain" and presented:
        raise GeneratorQualificationError(
            f"abstention case has presented evidence: {case['case_id']}"
        )


def build_preflight(assets: dict[str, Any]) -> dict[str, Any]:
    instrument = assets["instrument"]
    credential_name = instrument["candidate_binding"]["credential_environment_variable"]
    credential_present = bool(os.environ.get(credential_name, "").strip())
    return {
        "run_type": "generator-qualification-v1-preflight",
        "status": (
            "ready-for-development-execution"
            if credential_present
            else "blocked-missing-provider-credential"
        ),
        "instrument_id": instrument["instrument_id"],
        "binding": instrument["candidate_binding"],
        "prompt_conditions": [
            item["condition_id"] for item in instrument["prompt_candidates"]
        ],
        "datasets": {
            split: {
                "path": str(record["path"].relative_to(ROOT)),
                "sha256": record["sha256"],
                "case_count": record["case_count"],
                "status": record["status"],
            }
            for split, record in assets["datasets"].items()
        },
        "credential_environment_variable": credential_name,
        "credential_present": credential_present,
        "credential_value_emitted": False,
        "private_text_emitted": False,
        "external_call_enabled": False,
        "heldout_execution_enabled": False,
        "code_revision": _code_revision(),
        "working_tree_dirty": _working_tree_dirty(),
    }


async def execute(
    assets: dict[str, Any],
    *,
    split: str,
    prompt_conditions: list[str],
) -> dict[str, Any]:
    instrument = assets["instrument"]
    dataset = assets["datasets"][split]["dataset"]
    if split == "heldout":
        _open_heldout_once(assets)
        dataset = load_json(assets["datasets"][split]["path"])
        _validate_dataset(dataset, split="heldout", expected_count=104)
    if dataset is None:
        raise GeneratorQualificationError(f"{split} dataset is unavailable")
    binding = instrument["candidate_binding"]
    decoding = binding["decoding"]
    stop_cap = instrument["budget"][f"{split}_stop_cap_usd"]
    client = LiteLlmClient(
        binding["litellm_model"],
        timeout_seconds=decoding["timeout_seconds"],
        max_output_tokens=decoding["max_output_tokens"],
        response_format={"type": "json_object"},
        provider_options={"extra_body": {"thinking": {"type": "disabled"}}},
    )
    policy = _approved_synthetic_policy()
    results = []
    cumulative_cost = 0.0
    for prompt_condition in prompt_conditions:
        prompt_builder = PROMPTS[prompt_condition]()
        generator = LiveGroundedGenerator(client, prompt_builder=prompt_builder)
        for case in dataset["cases"]:
            answer = await generator.generate(
                case["question"],
                _hits(case),
                policy,
            )
            trace = answer.trace
            if trace is None:
                raise GeneratorQualificationError("generator omitted trace")
            case_cost = trace.usage.approximate_cost_usd
            if trace.provider_model != "not-called" and case_cost is None:
                raise GeneratorQualificationError(
                    "provider call returned no cost; stopped before further calls"
                )
            cumulative_cost += case_cost or 0.0
            record = _case_result(
                case,
                prompt_condition=prompt_condition,
                answer=answer,
                expected_provider_model=binding["provider_model"],
                expected_provider_revision=binding.get("expected_provider_revision"),
            )
            results.append(record)
            if cumulative_cost >= stop_cap:
                raise GeneratorQualificationError(
                    f"{split} cost stop cap reached: USD {cumulative_cost:.6f}"
                )
    latencies = [item["latency_ms"] for item in results]
    return {
        "run_type": "generator-qualification-v1",
        "status": "development-output-review-required",
        "instrument_id": instrument["instrument_id"],
        "split": split,
        "dataset_sha256": assets["datasets"][split]["sha256"],
        "binding": binding,
        "prompt_conditions": prompt_conditions,
        "case_attempts": len(results),
        "completed_attempts": sum(item["completed"] for item in results),
        "deterministic_check_passes": sum(
            item["deterministic_checks_passed"] for item in results
        ),
        "cumulative_cost_usd": cumulative_cost,
        "input_tokens": sum(item["usage"]["input_tokens"] for item in results),
        "output_tokens": sum(item["usage"]["output_tokens"] for item in results),
        "latency_p50_ms": statistics.median(latencies) if latencies else None,
        "latency_p95_ms": _percentile(latencies, 0.95),
        "provider_revisions": sorted(
            {
                item["provider_revision"]
                for item in results
                if item["provider_revision"] is not None
            }
        ),
        "private_course_external_calls": 0,
        "review_required": True,
        "results": results,
        "code_revision": _code_revision(),
        "working_tree_dirty": _working_tree_dirty(),
    }


def _hits(case: dict[str, Any]) -> list[RetrievalHit]:
    hits = []
    for index, item in enumerate(case["candidate_evidence"]):
        if not item["presented"]:
            continue
        hits.append(
            RetrievalHit(
                chunk=DocumentChunk(
                    id=f"{case['case_id']}-{item['evidence_id']}",
                    document_id=item["source_id"],
                    text=item["text"],
                    ordinal=index,
                    source_version=item["source_version"],
                    retrieval_allowed=True,
                    locator=item["locator"],
                    metadata={"title": f"Synthetic {case['topic_stratum']}"},
                ),
                relevance_score=1.0 - index * 0.01,
            )
        )
    return hits


def _case_result(
    case,
    *,
    prompt_condition,
    answer,
    expected_provider_model,
    expected_provider_revision=None,
):
    trace = answer.trace
    lowered = answer.content.casefold()
    expected_action = case["expected_action"]
    actual_action = _actual_action(
        trace.policy_action,
        lowered,
        scenario_type=case["scenario_type"],
    )
    required_terms_passed = all(
        all(_term_present(term, lowered) for term in group)
        for group in case["required_claim_term_groups"]
    )
    forbidden_terms_absent = all(
        term.casefold() not in lowered for term in case["forbidden_answer_terms"]
    )
    presented_sources = {
        item["source_id"] for item in case["candidate_evidence"] if item["presented"]
    }
    citation_sources = {citation.source_id for citation in answer.citations}
    citation_identity_passed = citation_sources.issubset(presented_sources) and (
        bool(citation_sources) if case["citation_required"] else True
    )
    provider_called = trace.provider_model != "not-called"
    provider_identity_passed = not provider_called or (
        trace.provider_model == expected_provider_model
        and trace.provider_revision is not None
        and (
            expected_provider_revision is None
            or trace.provider_revision == expected_provider_revision
        )
    )
    completed = not answer.warnings or not provider_called
    deterministic_checks_passed = all(
        (
            completed,
            actual_action == expected_action,
            required_terms_passed,
            forbidden_terms_absent,
            citation_identity_passed,
            provider_identity_passed,
        )
    )
    return {
        "case_id": case["case_id"],
        "scenario_type": case["scenario_type"],
        "prompt_condition": prompt_condition,
        "expected_action": expected_action,
        "actual_action": actual_action,
        "answer": answer.content,
        "citation_sources": sorted(citation_sources),
        "warnings": answer.warnings,
        "provider_model": trace.provider_model,
        "provider_revision": trace.provider_revision,
        "latency_ms": trace.latency_ms,
        "usage": trace.usage.model_dump(mode="json"),
        "completed": completed,
        "required_terms_passed": required_terms_passed,
        "forbidden_terms_absent": forbidden_terms_absent,
        "citation_identity_passed": citation_identity_passed,
        "provider_identity_passed": provider_identity_passed,
        "deterministic_checks_passed": deterministic_checks_passed,
        "human_review": {
            "status": "pending",
            "required_claim_recall": None,
            "supported_claim_precision": None,
            "citation_correctness": None,
            "citation_completeness": None,
            "pedagogy": None,
        },
    }


def _actual_action(
    policy_action: str,
    answer: str,
    *,
    scenario_type: str,
) -> str:
    answer = answer.casefold()
    if policy_action == "redirect-graded-work":
        return "redirect"
    if policy_action == "no-evidence":
        return "abstain"
    clarification_markers = (
        "which context",
        "which context are",
        "what context",
        "whether you're asking",
        "whether you are asking",
        "could you clarify which context",
    )
    if scenario_type == "ambiguity" and any(
        marker in answer for marker in clarification_markers
    ):
        return "clarify"
    return "answer"


def _term_present(term: str, answer: str) -> bool:
    normalized = term.casefold()
    if normalized in answer:
        return True
    if normalized.endswith("ed"):
        stem = normalized[:-2]
        return any(form in answer for form in (stem, f"{stem}s", f"{stem}es"))
    return False


def _approved_synthetic_policy():
    policy = build_initial_policy().model_copy(deep=True)
    for field in policy.all_fields:
        if field.status == FieldStatus.BLOCKS_RELEASE:
            field.status = FieldStatus.RESOLVED
        if field.id == "knowledge_source_policy":
            field.value = {**field.value, "confirmed": True}
        if field.id in {"academic_integrity_policy", "professor_release_approval"}:
            field.status = FieldStatus.RESOLVED
        if field.id == "professor_release_approval":
            field.value = "approved"
    policy.status = ReleaseStatus.APPROVED
    policy.release_status = ReleaseStatus.APPROVED
    return policy


def _open_heldout_once(assets: dict[str, Any]) -> None:
    HELDOUT_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    ledger = {
        "instrument_id": assets["instrument"]["instrument_id"],
        "dataset_sha256": assets["datasets"]["heldout"]["sha256"],
        "opened_at": datetime.now(UTC).isoformat(),
        "state": "opened-for-one-time-run",
        "rerun_allowed": False,
        "code_revision": _code_revision(),
    }
    try:
        with HELDOUT_LEDGER_PATH.open("x", encoding="utf-8") as stream:
            json.dump(ledger, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except FileExistsError as error:
        raise GeneratorQualificationError(
            "held-out access ledger already exists; rerun is prohibited"
        ) from error


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * quantile) - 1))
    return ordered[index]


def _code_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _working_tree_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=INSTRUMENT_PATH)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--split", choices=("development", "heldout"), default="development"
    )
    parser.add_argument("--prompt-condition", action="append", choices=tuple(PROMPTS))
    parser.add_argument("--allow-external-provider", action="store_true")
    parser.add_argument("--confirm-heldout-once", action="store_true")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.execute and not arguments.allow_external_provider:
        parser.error("execution requires --allow-external-provider")
    if arguments.execute and arguments.output is None:
        parser.error("execution requires --output under the ignored run boundary")
    if arguments.split == "heldout" and not arguments.confirm_heldout_once:
        parser.error("held-out access requires --confirm-heldout-once")
    if arguments.split == "heldout" and len(arguments.prompt_condition or []) != 1:
        parser.error("held-out execution requires exactly one frozen prompt condition")
    return arguments


def main() -> None:
    arguments = _arguments()
    assets = validate_assets(arguments.instrument)
    instrument = assets["instrument"]
    allowed_conditions = {
        item["condition_id"] for item in instrument["prompt_candidates"]
    }
    requested_conditions = arguments.prompt_condition or sorted(allowed_conditions)
    if not set(requested_conditions).issubset(allowed_conditions):
        raise SystemExit("prompt condition is not frozen in the selected instrument")
    if arguments.split == "heldout" and instrument["instrument_id"] not in {
        "generator-qualification-v1",
        "generator-qualification-v1-heldout-001",
    }:
        raise SystemExit(
            "selected instrument is development-only; held-out remains sealed"
        )
    if not arguments.execute:
        payload = build_preflight(assets)
    else:
        credential_name = assets["instrument"]["candidate_binding"][
            "credential_environment_variable"
        ]
        if not os.environ.get(credential_name, "").strip():
            raise SystemExit(f"missing environment credential: {credential_name}")
        payload = asyncio.run(
            execute(
                assets,
                split=arguments.split,
                prompt_conditions=requested_conditions,
            )
        )
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if arguments.output is None:
        print(rendered, end="")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
