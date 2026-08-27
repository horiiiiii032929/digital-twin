#!/usr/bin/env python3
"""Build the provider-free 500-case open benchmark development package."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_academic_factual_qa_open_10000 import SOURCE_PLAN_PATH  # noqa: E402
from scripts.construct_academic_factual_qa_open_10000 import (  # noqa: E402
    COURSE_IDS,
    DEVELOPMENT_CASES_PATH,
    DEVELOPMENT_CONTROL_CASES_PATH,
    DEVELOPMENT_CONTROL_GOLD_PATH,
    DEVELOPMENT_GOLD_PATH,
)
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.evaluation.factual_qa_dataset import (  # noqa: E402
    AuthoredClusterVariantsV1,
    ClusterDraftV1,
    DeterministicClusterTruthV1,
    SourceClusterV1,
    assemble_deterministic_verified_cluster,
    build_deterministic_cluster_truth_v2,
    normalize_question,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.provider_json import (  # noqa: E402
    DirectProviderJsonTransport,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    BOUNDED_PILOT_AUTHORIZATIONS,
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_ID = "academic-factual-qa-open-10000-deterministic-development-001"
INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_deterministic_development_001.json"
)
DIRECT_BINDING_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
    "academic_factual_qa_open_10000_direct_provider_binding_001.json"
)
AUTHOR_FAMILY = "deterministic-canonical-development-v2"
VERIFIER_FAMILY = "deterministic-exact-source-verifier-v2"
DEVELOPMENT_CLUSTER_COUNT = 100
DEVELOPMENT_CASE_COUNT = 500
CONTROL_CLUSTER_COUNT = 20
CONTROL_CASE_COUNT = 100


class DeterministicDevelopmentBuildError(RuntimeError):
    """Raised when the provider-free development package violates its freeze."""


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_hashed_record(path: Path, *, identifier_key: str, identifier: str) -> dict[str, Any]:
    value = _load(path)
    if value.get(identifier_key) != identifier:
        raise DeterministicDevelopmentBuildError(f"record identity drifted: {path.name}")
    expected = canonical_json_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != expected:
        raise DeterministicDevelopmentBuildError(f"record hash drifted: {path.name}")
    return value


def _instrument() -> dict[str, Any]:
    return _validate_hashed_record(
        INSTRUMENT_PATH, identifier_key="instrument_id", identifier=INSTRUMENT_ID
    )


def _direct_binding() -> dict[str, Any]:
    return _validate_hashed_record(
        DIRECT_BINDING_PATH,
        identifier_key="binding_id",
        identifier="academic-factual-qa-open-10000-direct-provider-binding-001",
    )


def _repo_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def _development_clusters() -> list[SourceClusterV1]:
    plan = _load(SOURCE_PLAN_PATH)
    rows = [
        SourceClusterV1.model_validate(row)
        for row in plan.get("clusters", [])
        if row.get("split") == "development"
    ]
    if len(rows) != DEVELOPMENT_CLUSTER_COUNT:
        raise DeterministicDevelopmentBuildError(
            f"development source plan has {len(rows)}/{DEVELOPMENT_CLUSTER_COUNT} clusters"
        )
    return rows


_CONTEXT_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "this",
        "to",
        "with",
    }
)


def _context_hint(cluster: SourceClusterV1, truth: DeterministicClusterTruthV1) -> str:
    excluded = {
        token
        for row in truth.questions
        for token in normalize_question(row.canonical_answer).split()
    }
    tokens: list[str] = []
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", cluster.text):
        token = raw.casefold()
        if token in _CONTEXT_STOPWORDS or token in excluded or token in tokens:
            continue
        tokens.append(token)
        if len(tokens) == 5:
            break
    if not tokens:
        tokens = [cluster.source_modality, cluster.course_id]
    return " ".join(tokens)


def _question_variants(
    clusters: list[SourceClusterV1],
    truths: dict[str, DeterministicClusterTruthV1],
) -> dict[str, list[dict[str, str]]]:
    variants = {
        cluster.cluster_id: [
            {"case_id": row.case_id, "question": row.canonical_question}
            for row in truths[cluster.cluster_id].questions
        ]
        for cluster in clusters
    }
    locations: dict[str, list[tuple[SourceClusterV1, int]]] = defaultdict(list)
    for cluster in clusters:
        for index, row in enumerate(variants[cluster.cluster_id]):
            locations[normalize_question(row["question"])].append((cluster, index))
    for duplicates in locations.values():
        if len(duplicates) < 2:
            continue
        for cluster, index in duplicates:
            row = variants[cluster.cluster_id][index]
            base = row["question"].rstrip("?")
            hint = _context_hint(cluster, truths[cluster.cluster_id])
            row["question"] = f"{base}, in the passage concerning {hint}?"
    normalized = [
        normalize_question(row["question"])
        for rows in variants.values()
        for row in rows
    ]
    if len(normalized) != len(set(normalized)):
        raise DeterministicDevelopmentBuildError(
            "deterministic disambiguation left normalized duplicate questions"
        )
    return variants


def _package(
    *, rows_key: str, rows: list[dict[str, Any]], split: str
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": f"academic-factual-qa-open-10000-v1-{split}",
        "construction_instrument_id": INSTRUMENT_ID,
        "construction_method": "deterministic-source-linked-v2",
        "canonical_wording_status": "development-template-not-final-naturalness-evidence",
        "split": split,
        "case_count": len(rows),
        rows_key: rows,
        "provider_calls": 0,
        "private_data_used": False,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    return payload


def build_packages() -> dict[str, Any]:
    instrument = _instrument()
    clusters = _development_clusters()
    truths = {
        cluster.cluster_id: build_deterministic_cluster_truth_v2(
            cluster, course_ids=COURSE_IDS
        )
        for cluster in clusters
    }
    variants = _question_variants(clusters, truths)
    cases: list[EvaluationCaseV1] = []
    gold: list[EvaluationGoldV1] = []
    for cluster in clusters:
        truth = truths[cluster.cluster_id]
        authored = AuthoredClusterVariantsV1(
            cluster_id=cluster.cluster_id,
            questions=variants[cluster.cluster_id],
        )
        verifier = ClusterDraftV1(
            cluster_id=cluster.cluster_id,
            questions=[
                {
                    "case_id": row.case_id,
                    "question": authored.questions[index].question,
                    "action": row.action,
                    "answer": row.canonical_answer,
                    "evidence_spans": [
                        span.model_dump(mode="json") for span in row.evidence_spans
                    ],
                    "boundary_reason": row.boundary_reason,
                }
                for index, row in enumerate(truth.questions)
            ],
        )
        assembly_cluster = cluster.model_copy(
            update={
                "author_family": AUTHOR_FAMILY,
                "verifier_family": VERIFIER_FAMILY,
            }
        )
        cluster_cases, cluster_gold = assemble_deterministic_verified_cluster(
            assembly_cluster, truth, authored, verifier
        )
        cases.extend(cluster_cases)
        gold.extend(cluster_gold)

    if len(cases) != DEVELOPMENT_CASE_COUNT or len(gold) != DEVELOPMENT_CASE_COUNT:
        raise DeterministicDevelopmentBuildError("development package size drifted")
    normalized = [normalize_question(row.question) for row in cases]
    duplicate_count = len(normalized) - len(set(normalized))
    if duplicate_count:
        raise DeterministicDevelopmentBuildError("development questions are duplicated")
    case_ids = {row.case_id for row in cases}
    if case_ids != {row.case_id for row in gold}:
        raise DeterministicDevelopmentBuildError("public-case and hidden-gold IDs differ")
    answerable = [row for row in gold if row.expected_action == EvaluationAction.ANSWER]
    boundary = [row for row in gold if row.expected_action != EvaluationAction.ANSWER]
    if len(answerable) != 400 or len(boundary) != 100:
        raise DeterministicDevelopmentBuildError("development action distribution drifted")
    if any(not row.claims for row in answerable) or any(row.claims for row in boundary):
        raise DeterministicDevelopmentBuildError("development lineage policy drifted")

    ordered_cases = sorted(cases, key=lambda row: row.case_id)
    ordered_gold = sorted(gold, key=lambda row: row.case_id)
    paired_cluster_ids = {row.cluster_id for row in ordered_cases[:CONTROL_CASE_COUNT]}
    if len(paired_cluster_ids) != CONTROL_CLUSTER_COUNT:
        paired_cluster_ids = {
            cluster.cluster_id
            for cluster in sorted(clusters, key=lambda row: row.cluster_id)[
                :CONTROL_CLUSTER_COUNT
            ]
        }
    paired_cases = [row for row in ordered_cases if row.cluster_id in paired_cluster_ids]
    paired_ids = {row.case_id for row in paired_cases}
    paired_gold = [row for row in ordered_gold if row.case_id in paired_ids]
    if len(paired_cases) != CONTROL_CASE_COUNT or len(paired_gold) != CONTROL_CASE_COUNT:
        raise DeterministicDevelopmentBuildError("control subset size drifted")

    packages = {
        "cases": _package(
            rows_key="cases",
            rows=[row.model_dump(mode="json") for row in ordered_cases],
            split="development",
        ),
        "gold": _package(
            rows_key="gold",
            rows=[row.model_dump(mode="json") for row in ordered_gold],
            split="development",
        ),
        "control_cases": _package(
            rows_key="cases",
            rows=[row.model_dump(mode="json") for row in paired_cases],
            split="development-control",
        ),
        "control_gold": _package(
            rows_key="gold",
            rows=[row.model_dump(mode="json") for row in paired_gold],
            split="development-control",
        ),
    }
    second_hashes = {
        key: canonical_json_sha256(
            {field: value for field, value in package.items() if field != "content_sha256"}
        )
        for key, package in packages.items()
    }
    if any(packages[key]["content_sha256"] != value for key, value in second_hashes.items()):
        raise DeterministicDevelopmentBuildError("package byte-stability check failed")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "instrument_sha256": instrument["content_sha256"],
        "case_count": len(cases),
        "control_case_count": len(paired_cases),
        "answerable_count": len(answerable),
        "boundary_count": len(boundary),
        "normalized_duplicate_count": duplicate_count,
        "course_distribution": dict(Counter(row.course_id for row in cases)),
        "slice_distribution": dict(Counter(row.slice for row in cases)),
        "provider_calls": 0,
        "final_cases_constructed": 0,
        "packages": packages,
    }


def _exclusive_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise DeterministicDevelopmentBuildError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_development_packages() -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "dataset_generation")
    result = build_packages()
    paths = {
        "cases": DEVELOPMENT_CASES_PATH,
        "gold": DEVELOPMENT_GOLD_PATH,
        "control_cases": DEVELOPMENT_CONTROL_CASES_PATH,
        "control_gold": DEVELOPMENT_CONTROL_GOLD_PATH,
    }
    if any(path.exists() for path in paths.values()):
        raise DeterministicDevelopmentBuildError("exclusive development output is used")
    for key, path in paths.items():
        _exclusive_json(path, result["packages"][key])
    return {
        **{key: value for key, value in result.items() if key != "packages"},
        "status": "completed-build-only",
        "outputs": {
            key: {
                "path": str(path.relative_to(ROOT)),
                "content_sha256": result["packages"][key]["content_sha256"],
            }
            for key, path in paths.items()
        },
    }


def validate_direct_provider_contracts() -> dict[str, Any]:
    binding = _direct_binding()
    providers = binding["providers"]
    if set(providers) != {"openai-gpt-5.4-mini", "mistral-small-4"}:
        raise DeterministicDevelopmentBuildError("direct provider set drifted")
    transports = {
        key: DirectProviderJsonTransport(value) for key, value in providers.items()
    }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["ok"],
        "properties": {"ok": {"type": "boolean"}},
    }
    payloads = {
        key: transport._payload(  # noqa: SLF001 - contract inspection is intentional
            system="Return the schema.",
            prompt="Return ok=true.",
            task="network-free-contract-simulation",
            schema=schema,
        )
        for key, transport in transports.items()
    }
    serialized = json.dumps(payloads, sort_keys=True)
    if "openrouter" in serialized.casefold() or "deepseek" in serialized.casefold():
        raise DeterministicDevelopmentBuildError("router path leaked into direct binding")
    return {
        "binding_id": binding["binding_id"],
        "status": "simulated-network-free",
        "providers": sorted(providers),
        "strict_schema_requested": all(
            "json_schema" in json.dumps(payload) for payload in payloads.values()
        ),
        "maximum_transport_retries": {
            key: value["maximum_transport_retries"] for key, value in providers.items()
        },
        "provider_calls": 0,
    }


def preflight() -> dict[str, Any]:
    instrument = _instrument()
    binding = _direct_binding()
    blockers: list[str] = []
    if not SOURCE_PLAN_PATH.is_file():
        blockers.append("source-plan-missing")
    if _repo_dirty():
        blockers.append("repository-dirty")
    operations = BOUNDED_PILOT_AUTHORIZATIONS.get(INSTRUMENT_ID, ())
    if "dataset_generation" not in operations:
        blockers.append("deterministic-construction-freeze-authorization-missing")
    output_paths = (
        DEVELOPMENT_CASES_PATH,
        DEVELOPMENT_GOLD_PATH,
        DEVELOPMENT_CONTROL_CASES_PATH,
        DEVELOPMENT_CONTROL_GOLD_PATH,
    )
    if not all(path.is_file() for path in output_paths):
        blockers.append("deterministic-development-package-incomplete")
    for provider in binding["providers"].values():
        name = provider["credential_environment_variable"]
        if not os.getenv(name, "").strip():
            blockers.append(f"{name.casefold()}-missing")
    authorization = binding["authorization"]
    for key in (
        "provider_execution_authorized",
        "paid_execution_authorized",
        "development_execution_authorized",
    ):
        if not authorization[key]:
            blockers.append(f"direct-binding-{key.replace('_', '-')}-false")
    if not instrument["authorization"][
        "development_product_execution_authorized"
    ]:
        blockers.append("instrument-development-product-execution-authorized-false")
    verified_at = datetime.fromisoformat(binding["verified_at"])
    age_hours = (
        datetime.now(timezone.utc) - verified_at.astimezone(timezone.utc)
    ).total_seconds() / 3600
    if age_hours < 0 or age_hours > binding["maximum_age_hours_for_execution"]:
        blockers.append("direct-provider-metadata-stale")
    if instrument["authorization"]["final_product_execution_authorized"]:
        blockers.append("final-product-execution-must-remain-unauthorized")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": sorted(set(blockers)),
        "provider_calls": 0,
        "credential_values_emitted": False,
        "final_product_execution_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate-direct-providers", action="store_true")
    mode.add_argument("--write-development", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    arguments = parser.parse_args()
    if arguments.write_development:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "dataset_generation")
        result = write_development_packages()
    elif arguments.simulate_direct_providers:
        result = validate_direct_provider_contracts()
    elif arguments.preflight:
        result = preflight()
    else:
        result = {
            **{key: value for key, value in build_packages().items() if key != "packages"},
            "direct_provider_contract": validate_direct_provider_contracts(),
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
