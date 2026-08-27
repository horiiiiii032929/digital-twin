#!/usr/bin/env python3
"""Construct source-linked benchmark cases with bounded multi-model assistance."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_academic_factual_qa_open_10000 import (  # noqa: E402
    INSTRUMENT_ID,
    INSTRUMENT_PATH,
    SOURCE_PLAN_PATH,
)
from src.digital_twin.evaluation.factual_qa_dataset import (  # noqa: E402
    AuthoredClusterVariantsV1,
    ClusterDraftV1,
    DeterministicClusterTruthV1,
    SourceClusterV1,
    assemble_deterministic_verified_cluster,
    build_deterministic_cluster_truth,
    normalize_question,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.provider_json import (  # noqa: E402
    OpenAiCompatibleJsonTransport,
    ProviderCallLedgerV1,
    ProviderJsonResponse,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    BOUNDED_PILOT_AUTHORIZATIONS,
    require_bounded_pilot_operation_allowed,
)


BINDING_PATH = (
    ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_open_10000_provider_binding_002.json"
)
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
DEVELOPMENT_CASES_PATH = (
    DATASET_ROOT / "academic_factual_qa_open_10000_v1_development_cases.json"
)
DEVELOPMENT_GOLD_PATH = (
    DATASET_ROOT / "academic_factual_qa_open_10000_v1_development_gold.json"
)
DEVELOPMENT_CONTROL_CASES_PATH = (
    DATASET_ROOT
    / "academic_factual_qa_open_10000_v1_development_control_cases.json"
)
DEVELOPMENT_CONTROL_GOLD_PATH = (
    DATASET_ROOT
    / "academic_factual_qa_open_10000_v1_development_control_gold.json"
)
FINAL_CASES_PATH = DATASET_ROOT / "academic_factual_qa_open_10000_v1_final_cases.json"
FINAL_GOLD_PATH = DATASET_ROOT / "academic_factual_qa_open_10000_v1_final_gold.json"
DEFAULT_LEDGER = (
    ROOT
    / "data/interim/academic_factual_qa_open_10000_v1_development_construction_attempt_002.sqlite3"
)
DEVELOPMENT_MAXIMUM_CALLS = 202
FINAL_MAXIMUM_CALLS = 4002
CONSTRUCTION_COST_STOP_USD = 3.0
FRESHNESS_HOURS = 24
COURSE_IDS = (
    "operating-systems",
    "computer-networking",
    "data-structures",
    "python-programming",
)


class ConstructionError(RuntimeError):
    """Raised when construction is incomplete, invalid, or unauthorized."""


AUTHOR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["cluster_id", "questions"],
    "properties": {
        "cluster_id": {"type": "string"},
        "questions": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["case_id", "question"],
                "properties": {
                    "case_id": {"type": "string"},
                    "question": {"type": "string"},
                },
            },
        },
    },
}

EVIDENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["quote", "relative_char_start", "relative_char_end"],
    "properties": {
        "quote": {"type": "string"},
        "relative_char_start": {"type": "integer"},
        "relative_char_end": {"type": "integer"},
    },
}

VERIFIER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["cluster_id", "questions"],
    "properties": {
        "cluster_id": {"type": "string"},
        "questions": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "case_id",
                    "question",
                    "action",
                    "answer",
                    "evidence_spans",
                    "boundary_reason",
                ],
                "properties": {
                    "case_id": {"type": "string"},
                    "question": {"type": "string"},
                    "action": {
                        "type": "string",
                        "enum": ["answer", "abstain", "clarify", "refuse"],
                    },
                    "answer": {"type": "string"},
                    "evidence_spans": {
                        "type": "array",
                        "items": EVIDENCE_SCHEMA,
                    },
                    "boundary_reason": {"type": ["string", "null"]},
                },
            },
        },
    },
}

CANARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["canary_id", "ok"],
    "properties": {
        "canary_id": {"type": "string"},
        "ok": {"type": "boolean"},
    },
}


def _load(path: Path) -> dict[str, Any]:
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


def _binding() -> dict[str, Any]:
    value = _load(BINDING_PATH)
    expected = canonical_json_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != expected:
        raise ConstructionError("construction provider binding hash drifted")
    return value


def _binding_age_hours(binding: dict[str, Any]) -> float:
    verified = datetime.fromisoformat(binding["verified_at"])
    if verified.tzinfo is None:
        raise ConstructionError("provider binding timestamp lacks a timezone")
    return (datetime.now(timezone.utc) - verified.astimezone(timezone.utc)).total_seconds() / 3600


def _stage_paths(stage: str) -> tuple[Path, Path]:
    return (
        (DEVELOPMENT_CASES_PATH, DEVELOPMENT_GOLD_PATH)
        if stage == "development"
        else (FINAL_CASES_PATH, FINAL_GOLD_PATH)
    )


def _stage_clusters(stage: str) -> list[SourceClusterV1]:
    plan = _load(SOURCE_PLAN_PATH)
    rows = [
        SourceClusterV1.model_validate(row)
        for row in plan.get("clusters", [])
        if row.get("split") == stage
    ]
    expected = 100 if stage == "development" else 2000
    if len(rows) != expected:
        raise ConstructionError(
            f"source plan contains {len(rows)}/{expected} {stage} clusters"
        )
    return rows


def _truth(cluster: SourceClusterV1) -> DeterministicClusterTruthV1:
    return build_deterministic_cluster_truth(cluster, course_ids=COURSE_IDS)


def _author_prompt(
    cluster: SourceClusterV1, truth: DeterministicClusterTruthV1
) -> str:
    requirements: list[dict[str, Any]] = []
    for index, row in enumerate(truth.questions):
        requirement: dict[str, Any] = {
            "case_id": row.case_id,
            "slice": (
                cluster.answerable_slices[index]
                if index < 4
                else cluster.boundary_slice
            ),
            "target_course_id": row.target_course_id,
            "required_action": row.action.value,
            "canonical_fallback_question": row.canonical_question,
        }
        if row.action.value == "answer":
            requirement["target_answer_spans"] = [
                span.quote for span in row.evidence_spans
            ]
        else:
            requirement["boundary_reason"] = row.boundary_reason
        requirements.append(requirement)
    return json.dumps(
        {
            "task": "Write exactly one natural, self-contained question for each requirement.",
            "constraints": [
                "Preserve every case_id exactly.",
                "For answerable cases, the designated exact source span must fully answer the question.",
                "Do not copy the answer span into the question.",
                "Do not add facts, answers, citations, or metadata.",
                "For boundary cases, preserve the required action and boundary reason.",
                "Return only the JSON object required by the schema.",
            ],
            "cluster_id": cluster.cluster_id,
            "source_course_id": cluster.course_id,
            "section_heading": cluster.section_heading,
            "source_text": cluster.text,
            "requirements": requirements,
        },
        sort_keys=True,
    )


def _verifier_prompt(
    cluster: SourceClusterV1,
    authored: AuthoredClusterVariantsV1,
) -> str:
    truth = _truth(cluster)
    evidence_candidates = []
    seen_ranges: set[tuple[int, int]] = set()
    for row in truth.questions:
        for span in row.evidence_spans:
            relationship = (span.relative_char_start, span.relative_char_end)
            if relationship not in seen_ranges:
                seen_ranges.add(relationship)
                evidence_candidates.append(span.model_dump(mode="json"))
    return json.dumps(
        {
            "task": "Independently answer or classify each question using only the stated target-course boundary and source text.",
            "constraints": [
                "Do not infer the author model's answer.",
                "For an answer action, copy the complete shortest exact source span or spans needed and give their exact zero-based character offsets within source_text.",
                "Choose only from evidence_candidates; they contain possible exact spans but do not identify which question they answer.",
                "The answer must be the evidence quote, or the quotes joined by one space when multiple spans are required.",
                "Use abstain when the target course evidence does not establish the answer.",
                "Use clarify for an unresolved referent or ambiguity.",
                "Use refuse for a request for submission-ready graded work.",
                "For a boundary action, copy its boundary_response_contract exactly as answer, return no evidence spans, and set boundary_reason to the matching slice name.",
                "Repeat each question verbatim in the question field.",
                "Return only the JSON object required by the schema.",
            ],
            "cluster_id": cluster.cluster_id,
            "source_course_id": cluster.course_id,
            "source_text": cluster.text,
            "evidence_candidates": evidence_candidates,
            "questions": [row.model_dump(mode="json") for row in authored.questions],
            "target_courses": {
                row.case_id: truth.questions[index].target_course_id
                for index, row in enumerate(authored.questions)
            },
            "required_evidence_span_counts": {
                row.case_id: len(truth.questions[index].evidence_spans)
                for index, row in enumerate(authored.questions)
            },
            "boundary_slices": {
                row.case_id: cluster.boundary_slice
                for row in authored.questions
                if row.case_id.endswith("-q5")
            },
            "boundary_response_contracts": {
                row.case_id: truth.questions[index].canonical_answer
                for index, row in enumerate(authored.questions)
                if row.case_id.endswith("-q5")
            },
        },
        sort_keys=True,
    )


def _transports(binding: dict[str, Any]) -> dict[str, OpenAiCompatibleJsonTransport]:
    return {
        family: OpenAiCompatibleJsonTransport(provider_binding)
        for family, provider_binding in binding["providers"].items()
    }


async def _call(
    *,
    transport: OpenAiCompatibleJsonTransport,
    ledger: ProviderCallLedgerV1,
    request_key: str,
    role: str,
    prompt: str,
    schema: dict[str, Any],
) -> ProviderJsonResponse:
    return await transport.call_with_ledger(
        ledger=ledger,
        request_key=request_key,
        provider_role=role,
        system=(
            "You construct auditable educational evaluation data. Follow the source "
            "and JSON contract exactly; do not add markdown or commentary."
        ),
        prompt=prompt,
        task="academic_factual_qa_dataset",
        schema=schema,
    )


async def _canaries(
    transports: dict[str, OpenAiCompatibleJsonTransport],
    ledger: ProviderCallLedgerV1,
) -> None:
    for family, transport in sorted(transports.items()):
        canary_id = f"{INSTRUMENT_ID}-{family}-canary"
        response = await _call(
            transport=transport,
            ledger=ledger,
            request_key=f"canary:{family}",
            role="canary",
            prompt=json.dumps(
                {
                    "instruction": "Return the exact canary identifier and ok=true.",
                    "canary_id": canary_id,
                }
            ),
            schema=CANARY_SCHEMA,
        )
        if response.content != {"canary_id": canary_id, "ok": True}:
            raise ConstructionError(f"{family} canary content drifted")


def _parse_authored(value: dict[str, Any]) -> AuthoredClusterVariantsV1:
    try:
        return AuthoredClusterVariantsV1.model_validate(value)
    except ValidationError as error:
        raise ConstructionError("author response violates the construction schema") from error


def _parse_verifier(value: dict[str, Any]) -> ClusterDraftV1:
    try:
        return ClusterDraftV1.model_validate(value)
    except ValidationError as error:
        raise ConstructionError("verifier response violates the construction schema") from error


def _near_duplicate_pairs(questions: list[tuple[str, str]]) -> list[dict[str, Any]]:
    tokenized = {
        case_id: set(normalize_question(question).split())
        for case_id, question in questions
    }
    rows: list[dict[str, Any]] = []
    identifiers = sorted(tokenized)
    for left_index, left_id in enumerate(identifiers):
        left = tokenized[left_id]
        for right_id in identifiers[left_index + 1 :]:
            right = tokenized[right_id]
            union = left | right
            similarity = len(left & right) / len(union) if union else 1.0
            if similarity >= 0.9:
                rows.append(
                    {
                        "left_case_id": left_id,
                        "right_case_id": right_id,
                        "token_jaccard": round(similarity, 6),
                    }
                )
    return rows


def _package(
    *,
    stage: str,
    rows_key: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": f"academic-factual-qa-open-10000-v1-{stage}",
        "split": stage,
        "case_count": len(rows),
        rows_key: rows,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    return payload


def _exclusive_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise ConstructionError(f"construction output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


async def execute(
    *,
    stage: str,
    ledger_path: Path,
    resume: bool,
) -> dict[str, Any]:
    binding = _binding()
    clusters = _stage_clusters(stage)
    maximum_calls = (
        DEVELOPMENT_MAXIMUM_CALLS if stage == "development" else FINAL_MAXIMUM_CALLS
    )
    run_binding = {
        "instrument_id": INSTRUMENT_ID,
        "stage": stage,
        "source_plan_sha256": _load(SOURCE_PLAN_PATH)["content_sha256"],
        "provider_binding_sha256": binding["content_sha256"],
        "code_revision": _repo_revision(),
        "cluster_ids": [row.cluster_id for row in clusters],
    }
    ledger = ProviderCallLedgerV1(
        ledger_path,
        run_binding=run_binding,
        maximum_calls=maximum_calls,
        maximum_cost_usd=CONSTRUCTION_COST_STOP_USD,
        resume=resume,
    )
    cases: list[Any] = []
    gold: list[Any] = []
    rejected: list[dict[str, str]] = []
    try:
        transports = _transports(binding)
        await _canaries(transports, ledger)
        for cluster in clusters:
            truth = _truth(cluster)
            author_response = await _call(
                transport=transports[cluster.author_family],
                ledger=ledger,
                request_key=f"{cluster.cluster_id}:author",
                role="author",
                prompt=_author_prompt(cluster, truth),
                schema=AUTHOR_SCHEMA,
            )
            authored = _parse_authored(author_response.content)
            verifier_response = await _call(
                transport=transports[cluster.verifier_family],
                ledger=ledger,
                request_key=f"{cluster.cluster_id}:verifier",
                role="verifier",
                prompt=_verifier_prompt(cluster, authored),
                schema=VERIFIER_SCHEMA,
            )
            verifier = _parse_verifier(verifier_response.content)
            try:
                cluster_cases, cluster_gold = assemble_deterministic_verified_cluster(
                    cluster, truth, authored, verifier
                )
            except ValueError as error:
                rejected.append(
                    {
                        "cluster_id": cluster.cluster_id,
                        "reason": str(error)[:300],
                    }
                )
                continue
            cases.extend(cluster_cases)
            gold.extend(cluster_gold)

        expected = len(clusters) * 5
        normalized = [normalize_question(row.question) for row in cases]
        duplicate_count = sum(
            count - 1 for count in Counter(normalized).values() if count > 1
        )
        near_duplicates = _near_duplicate_pairs(
            [(row.case_id, row.question) for row in cases]
        )
        if rejected or len(cases) != expected or duplicate_count:
            ledger.mark_complete()
            return {
                "instrument_id": INSTRUMENT_ID,
                "stage": stage,
                "status": "completed-refine",
                "accepted_cluster_count": len(cases) // 5,
                "rejected_cluster_count": len(rejected),
                "case_count": len(cases),
                "expected_case_count": expected,
                "exact_duplicate_count": duplicate_count,
                "near_duplicate_pair_count": len(near_duplicates),
                "rejections": rejected,
                "provider_ledger": ledger.snapshot(),
            }

        cases_path, gold_path = _stage_paths(stage)
        cases_payload = _package(
            stage=stage,
            rows_key="cases",
            rows=[row.model_dump(mode="json") for row in cases],
        )
        gold_payload = _package(
            stage=stage,
            rows_key="gold",
            rows=[row.model_dump(mode="json") for row in gold],
        )
        _exclusive_json(cases_path, cases_payload)
        _exclusive_json(gold_path, gold_payload)
        control_details: dict[str, Any] = {}
        if stage == "development":
            paired_cluster_ids = {
                row.cluster_id for row in sorted(cases, key=lambda row: row.case_id)[:100]
            }
            if len(paired_cluster_ids) != 20:
                paired_cluster_ids = {
                    row.cluster_id
                    for row in sorted(
                        {row.cluster_id: row for row in cases}.values(),
                        key=lambda row: row.cluster_id,
                    )[:20]
                }
            paired_cases = [row for row in cases if row.cluster_id in paired_cluster_ids]
            paired_gold = [
                row for row in gold if row.case_id in {case.case_id for case in paired_cases}
            ]
            if len(paired_cases) != 100 or len(paired_gold) != 100:
                raise ConstructionError("development control subset must contain 20 clusters")
            control_cases_payload = _package(
                stage="development-control",
                rows_key="cases",
                rows=[row.model_dump(mode="json") for row in paired_cases],
            )
            control_gold_payload = _package(
                stage="development-control",
                rows_key="gold",
                rows=[row.model_dump(mode="json") for row in paired_gold],
            )
            _exclusive_json(DEVELOPMENT_CONTROL_CASES_PATH, control_cases_payload)
            _exclusive_json(DEVELOPMENT_CONTROL_GOLD_PATH, control_gold_payload)
            control_details = {
                "control_case_count": 100,
                "control_cluster_count": 20,
                "control_cases_sha256": control_cases_payload["content_sha256"],
                "control_gold_sha256": control_gold_payload["content_sha256"],
            }
        ledger.mark_complete()
        return {
            "instrument_id": INSTRUMENT_ID,
            "stage": stage,
            "status": "completed-keep",
            "accepted_cluster_count": len(clusters),
            "case_count": len(cases),
            "answerable_count": sum(row.expected_action.value == "answer" for row in gold),
            "boundary_count": sum(row.expected_action.value != "answer" for row in gold),
            "exact_duplicate_count": duplicate_count,
            "near_duplicate_pair_count": len(near_duplicates),
            "near_duplicate_pairs": near_duplicates,
            "course_distribution": dict(Counter(row.course_id for row in cases)),
            "slice_distribution": dict(Counter(row.slice for row in cases)),
            "author_distribution": dict(Counter(row.author_family for row in cases)),
            "public_cases_path": str(cases_path),
            "public_cases_sha256": cases_payload["content_sha256"],
            "hidden_gold_path": str(gold_path),
            "hidden_gold_sha256": gold_payload["content_sha256"],
            "provider_ledger": ledger.snapshot(),
            "private_data_read": False,
            **control_details,
        }
    except BaseException:
        if ledger.snapshot().get("status") == "running":
            ledger.mark_interrupted()
        raise
    finally:
        ledger.close()


class _SimulatedTransport:
    def __init__(self, family: str) -> None:
        self.family = family

    async def call_with_ledger(self, **kwargs: Any) -> ProviderJsonResponse:
        prompt = json.loads(kwargs["prompt"])
        if "canary_id" in prompt:
            content = {"canary_id": prompt["canary_id"], "ok": True}
        elif "requirements" in prompt:
            content = {
                "cluster_id": prompt["cluster_id"],
                "questions": [
                    {
                        "case_id": row["case_id"],
                        "question": row["canonical_fallback_question"],
                    }
                    for row in prompt["requirements"]
                ],
            }
        else:
            raise AssertionError("simulation verifier is assembled separately")
        return ProviderJsonResponse(
            content=content,
            provider_model=self.family,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0,
            latency_ms=0,
        )


def simulate() -> dict[str, Any]:
    from scripts.build_academic_factual_qa_open_10000 import build_recommended_source_plan

    cluster = SourceClusterV1.model_validate(
        next(
            row
            for row in build_recommended_source_plan()["clusters"]
            if row["split"] == "development"
        )
    )
    truth = _truth(cluster)
    authored = AuthoredClusterVariantsV1(
        cluster_id=cluster.cluster_id,
        questions=[
            {"case_id": row.case_id, "question": row.canonical_question}
            for row in truth.questions
        ],
    )
    verifier = ClusterDraftV1(
        cluster_id=cluster.cluster_id,
        questions=[
            {
                "case_id": row.case_id,
                "question": authored.questions[index].question,
                "action": row.action,
                "answer": row.canonical_answer,
                "evidence_spans": [span.model_dump() for span in row.evidence_spans],
                "boundary_reason": row.boundary_reason,
            }
            for index, row in enumerate(truth.questions)
        ],
    )
    cases, gold = assemble_deterministic_verified_cluster(
        cluster, truth, authored, verifier
    )
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "simulated-network-free",
        "case_count": len(cases),
        "gold_count": len(gold),
        "provider_calls": 0,
        "deterministic_truth_authoritative": True,
    }


def preflight(*, stage: str, ledger_path: Path, resume: bool) -> dict[str, Any]:
    blockers: list[str] = []
    if not SOURCE_PLAN_PATH.is_file():
        blockers.append("source-plan-missing")
    if not BINDING_PATH.is_file():
        blockers.append("provider-binding-missing")
        binding: dict[str, Any] | None = None
    else:
        try:
            binding = _binding()
            if _binding_age_hours(binding) > FRESHNESS_HOURS:
                blockers.append("provider-metadata-stale")
        except (ConstructionError, ValueError, KeyError):
            binding = None
            blockers.append("provider-binding-invalid")
    instrument = _load(INSTRUMENT_PATH)
    execution = instrument["execution"]
    for key in (
        "dataset_construction_authorized",
        "provider_execution_authorized",
        "paid_execution_authorized",
    ):
        if not execution[key]:
            blockers.append(f"{key.replace('_', '-')}-false")
    operations = BOUNDED_PILOT_AUTHORIZATIONS.get(INSTRUMENT_ID, ())
    if "dataset_generation" not in operations:
        blockers.append("bounded-dataset-authorization-missing")
    if _repo_dirty():
        blockers.append("working-tree-dirty")
    if binding is not None:
        binding_authorization = binding.get("authorization", {})
        binding_keys = [
            "dataset_construction_authorized",
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
                blockers.append(f"provider-binding-{key.replace('_', '-')}-false")
        for provider in binding["providers"].values():
            if not os.getenv(provider["credential_environment_variable"], "").strip():
                blockers.append(
                    f"{provider['credential_environment_variable'].casefold()}-missing"
                )
    cases_path, gold_path = _stage_paths(stage)
    outputs = [cases_path, gold_path]
    if stage == "development":
        outputs.extend(
            [DEVELOPMENT_CONTROL_CASES_PATH, DEVELOPMENT_CONTROL_GOLD_PATH]
        )
    if any(path.exists() for path in outputs):
        blockers.append("exclusive-dataset-output-used")
    if resume and not ledger_path.is_file():
        blockers.append("resume-ledger-missing")
    if not resume and ledger_path.exists():
        blockers.append("exclusive-ledger-output-used")
    return {
        "instrument_id": INSTRUMENT_ID,
        "stage": stage,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": sorted(set(blockers)),
        "provider_calls": 0,
        "credential_values_emitted": False,
        "final_product_execution_authorized": execution["final_execution_authorized"],
    }


def validate() -> dict[str, Any]:
    if set(AUTHOR_SCHEMA["properties"]) != {"cluster_id", "questions"}:
        raise ConstructionError("author schema drifted")
    if "expected_action" in json.dumps(AUTHOR_SCHEMA):
        raise ConstructionError("author output schema may not define source truth")
    binding = _binding()
    deepseek = binding["providers"]["deepseek-v4-flash"]
    if (
        deepseek["provider_model"] != "deepseek-v4-flash"
        or deepseek.get("expected_provider_revision") is not None
        or deepseek.get("require_provider_revision") is not True
        or deepseek.get("runtime_revision_policy")
        != "required-recorded-diagnostic-not-selection-gate"
    ):
        raise ConstructionError("DeepSeek successor identity policy drifted")
    gemini = binding["providers"]["gemini-3.7-flash"]
    if (
        gemini["provider_model"] != "google/gemini-3.7-flash"
        or gemini.get("requested_service_tier") != "default"
        or gemini.get("routing", {}).get("allow_fallbacks") is not False
        or gemini.get("routing", {}).get("order") != ["Google AI Studio"]
    ):
        raise ConstructionError("Gemini exact default-tier route drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed",
        "development_maximum_calls": DEVELOPMENT_MAXIMUM_CALLS,
        "final_maximum_calls": FINAL_MAXIMUM_CALLS,
        "emergency_cost_stop_usd": CONSTRUCTION_COST_STOP_USD,
        "provider_calls": 0,
        "deterministic_truth_authoritative": True,
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
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "dataset_generation")
        readiness = preflight(
            stage=arguments.stage,
            ledger_path=arguments.ledger,
            resume=arguments.resume,
        )
        if readiness["status"] != "ready":
            raise ConstructionError(f"construction is blocked: {readiness['blockers']}")
        result = asyncio.run(
            execute(
                stage=arguments.stage,
                ledger_path=arguments.ledger,
                resume=arguments.resume,
            )
        )
    elif arguments.preflight:
        result = preflight(
            stage=arguments.stage,
            ledger_path=arguments.ledger,
            resume=arguments.resume,
        )
    elif arguments.simulate:
        result = simulate()
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
