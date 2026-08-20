"""Run the bounded 40-case source-linked factual-QA v3 oracle pilot.

The run measures a dataset-construction method, not a model leaderboard. Exact
synthetic source facts and citation lineage remain authoritative; model reviews
are independent diagnostics and can only send cases to audit or quarantine.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pymupdf
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_factual_qa_quality_pilot import (
    AUTHOR_SCHEMA,
    REVIEW_SCHEMA,
    DeepSeekJsonTransport,
    FactualQaPilotError,
    OllamaJsonTransport,
    _author_prompt,
    _author_system_prompt,
    _call_record,
    _installed_ollama_digest,
    _review_prompt,
    _review_system_prompt,
    _source_context,
    deterministic_case_checks,
    load_json,
    sha256_file,
    validate_review,
)
from services.embeddings import Qwen3TextEmbedder
from src.digital_twin.evaluation import ComponentKind, load_release_profile
from src.digital_twin.grounding import (
    LocalCourseSourceIngestionService,
    build_selected_retriever,
)
from src.digital_twin.grounding.models import SourcePermissions
from src.digital_twin.model_policy import (
    LOCAL_GENERAL_MODEL,
    LOCAL_GENERAL_MODEL_DIGEST,
    require_registered_current_model,
)
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/factual_qa_v3_oracle_pilot_001.json"
)
PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
EMBEDDING_ROOT = (
    ROOT / "data/external/huggingface/hub/models--Qwen--Qwen3-Embedding-0.6B/"
    "snapshots/97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
)
DEFAULT_OUTPUT = ROOT / "reports/generated/factual-qa-v3-oracle-pilot-001.json"
PILOT_ID = "factual-qa-v3-oracle-pilot-001"
ANSWER_ACTION = "answer"
BOUNDARY_ACTIONS = {"abstain", "clarify", "refuse"}


def validate_assets(instrument_path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    instrument = load_json(instrument_path)
    if instrument.get("instrument_id") != PILOT_ID:
        raise FactualQaPilotError("unexpected v3 oracle pilot instrument")
    if instrument.get("status") != "frozen-pending-execution":
        raise FactualQaPilotError("v3 oracle pilot is not frozen")
    if instrument.get("model_leaderboard") is not False:
        raise FactualQaPilotError("pilot must not be configured as a leaderboard")
    execution = instrument.get("execution", {})
    if (
        execution.get("author_call_limit") != 40
        or execution.get("independent_reviewer_call_limit") != 40
        or execution.get("dispute_reviewer_call_limit") != 10
        or execution.get("concurrency") != 1
        or execution.get("retry_attempts") != 0
        or execution.get("cost_stop_usd") != 1.0
    ):
        raise FactualQaPilotError("v3 oracle pilot execution boundary drifted")

    roles = instrument.get("model_roles", {})
    expected = {
        "author": "deepseek-v4-flash",
        "independent_reviewer": LOCAL_GENERAL_MODEL,
        "dispute_reviewer": "deepseek-v4-pro",
    }
    for role, expected_model in expected.items():
        binding = roles.get(role, {})
        actual = binding.get("provider_model", binding.get("model"))
        require_registered_current_model(str(actual or ""))
        if actual != expected_model:
            raise FactualQaPilotError(f"v3 pilot model binding drifted: {role}")
    if roles["independent_reviewer"].get("model_digest") != LOCAL_GENERAL_MODEL_DIGEST:
        raise FactualQaPilotError("local reviewer digest drifted")
    excluded = {str(item).casefold() for item in instrument.get("excluded_models", [])}
    if not {"gemma", "claude", "qwen3:4b", "qwen3.5:4b"}.issubset(excluded):
        raise FactualQaPilotError("retired/prohibited model exclusions drifted")

    base_record = instrument["base_corpus"]
    base_path = ROOT / base_record["path"]
    if sha256_file(base_path) != base_record["sha256"]:
        raise FactualQaPilotError("base factual-QA corpus hash drifted")
    base = load_json(base_path)
    corpus = _expanded_corpus(base, instrument)
    if len(corpus["case_blueprints"]) != 40:
        raise FactualQaPilotError("v3 oracle pilot must contain exactly 40 cases")
    _validate_case_design(corpus)
    return {
        "instrument": instrument,
        "instrument_path": instrument_path,
        "base_path": base_path,
        "base_sha256": base_record["sha256"],
        "corpus": corpus,
    }


def _expanded_corpus(
    base: dict[str, Any], instrument: dict[str, Any]
) -> dict[str, Any]:
    corpus = json.loads(json.dumps(base))
    source_map = {item["source_unit_id"]: item for item in corpus["source_units"]}
    variants: list[dict[str, Any]] = []
    for offset, source_id in enumerate(
        instrument["case_design"]["variant_source_unit_ids"], start=25
    ):
        source = source_map[source_id]
        claim = source["claims"][1]
        variants.append(
            {
                "blueprint_id": f"fqa-v{offset:02d}",
                "slice": "direct-text" if offset % 2 else "paraphrase-text",
                "course_id": source["course_id"],
                "expected_action": ANSWER_ACTION,
                "evidence_unit_ids": [source_id],
                "target_claim_ids": [claim["claim_id"]],
                "question_intent": (
                    "Ask one concise factual question answered specifically by this "
                    f"claim without copying it verbatim: {claim['text']}"
                ),
                "difficulty": "medium",
            }
        )
    variants.append(instrument["case_design"]["additional_boundary_case"])
    corpus["case_blueprints"].extend(variants)
    corpus["corpus_id"] = "factual-qa-v3-oracle-pilot-corpus-001"
    corpus["status"] = "approved-synthetic-pilot"
    return corpus


def _validate_case_design(corpus: dict[str, Any]) -> None:
    source_map = {item["source_unit_id"]: item for item in corpus["source_units"]}
    ids = [item["blueprint_id"] for item in corpus["case_blueprints"]]
    if len(ids) != len(set(ids)):
        raise FactualQaPilotError("v3 pilot blueprint IDs are not unique")
    for case in corpus["case_blueprints"]:
        if case["expected_action"] not in {ANSWER_ACTION, *BOUNDARY_ACTIONS}:
            raise FactualQaPilotError("v3 pilot case action is invalid")
        evidence = case.get("evidence_unit_ids", [])
        if any(source_id not in source_map for source_id in evidence):
            raise FactualQaPilotError("v3 pilot case references an unknown source")
        if case["expected_action"] == ANSWER_ACTION and not evidence:
            raise FactualQaPilotError("answer case requires evidence")
        if case["expected_action"] in {"abstain", "refuse"} and evidence:
            raise FactualQaPilotError(
                "abstain/refuse case cannot carry answer evidence"
            )


def build_preflight(assets: dict[str, Any], *, ollama_url: str) -> dict[str, Any]:
    instrument = assets["instrument"]
    local = instrument["model_roles"]["independent_reviewer"]
    installed = _installed_ollama_digest(local["model"], ollama_url=ollama_url)
    return {
        "run_type": "factual-qa-v3-oracle-pilot-preflight",
        "instrument_id": PILOT_ID,
        "status": "ready"
        if (
            bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
            and installed is not None
            and LOCAL_GENERAL_MODEL_DIGEST.startswith(installed)
            and EMBEDDING_ROOT.is_dir()
        )
        else "blocked",
        "case_count": len(assets["corpus"]["case_blueprints"]),
        "deepseek_credential_present": bool(os.getenv("DEEPSEEK_API_KEY", "").strip()),
        "credential_value_emitted": False,
        "local_reviewer_model": local["model"],
        "local_reviewer_installed_digest": installed,
        "local_reviewer_ready": bool(
            installed and LOCAL_GENERAL_MODEL_DIGEST.startswith(installed)
        ),
        "embedding_model_ready": EMBEDDING_ROOT.is_dir(),
        "external_call_enabled": False,
        "private_data_read": False,
        "private_data_emitted": False,
        "cost_stop_usd": instrument["execution"]["cost_stop_usd"],
        "scale_authorized": False,
    }


def _build_product_corpus(
    corpus: dict[str, Any], temporary_root: Path
) -> tuple[dict[str, list[Any]], dict[str, dict[int, str]], dict[str, Any]]:
    by_course: dict[str, list[dict[str, Any]]] = {}
    for source in corpus["source_units"]:
        by_course.setdefault(source["course_id"], []).append(source)

    chunks_by_course: dict[str, list[Any]] = {}
    page_sources: dict[str, dict[int, str]] = {}
    warnings: list[str] = []
    for course_id, sources in sorted(by_course.items()):
        pdf_bytes, mapping = _render_course_pdf(course_id, sources)
        service = LocalCourseSourceIngestionService(
            temporary_root / "sources",
            temporary_root / "regions",
        )
        result = service.ingest_pdf(
            pdf_bytes,
            course_id=course_id,
            artifact_id=f"oracle-{course_id}",
            title=f"Synthetic oracle material for {course_id}",
            version=1,
            professor_id="synthetic-professor",
            permissions=SourcePermissions(
                processing_allowed=True,
                tutoring_allowed=True,
                display_allowed=True,
            ),
        )
        chunks_by_course[course_id] = result.chunks
        page_sources[course_id] = mapping
        warnings.extend(result.bundle.processing_warnings)
    return (
        chunks_by_course,
        page_sources,
        {
            "courses": len(by_course),
            "pdfs_ingested": len(chunks_by_course),
            "pdf_ingestion_rate": len(chunks_by_course) / len(by_course),
            "chunks": sum(len(items) for items in chunks_by_course.values()),
            "processing_warnings": warnings,
        },
    )


def _render_course_pdf(
    course_id: str, sources: list[dict[str, Any]]
) -> tuple[bytes, dict[int, str]]:
    document = pymupdf.open()
    mapping: dict[int, str] = {}
    try:
        for page_number, source in enumerate(sources, start=1):
            page = document.new_page(width=595, height=842)
            mapping[page_number] = source["source_unit_id"]
            heading = f"{course_id} — {source['locator']}"
            page.insert_textbox(
                pymupdf.Rect(54, 48, 541, 100),
                heading,
                fontsize=15,
                fontname="helv",
            )
            y_start = 120
            if source["modality"] != "text":
                page.insert_textbox(
                    pymupdf.Rect(54, y_start, 541, y_start + 28),
                    f"Controlled {source['modality']} fixture",
                    fontsize=11,
                    fontname="helv",
                )
                y_start += 38
                _place_visual_fixture(page, ROOT / source["path"], y_start=y_start)
                y_start += 300
                label = "Approved accessibility description: "
            else:
                label = "Approved course text: "
            page.insert_textbox(
                pymupdf.Rect(54, y_start, 541, 790),
                label + source["evidence_text"],
                fontsize=11,
                lineheight=1.25,
                fontname="helv",
            )
        return document.tobytes(garbage=4, deflate=True), mapping
    finally:
        document.close()


def _place_visual_fixture(
    page: pymupdf.Page, source_path: Path, *, y_start: float
) -> None:
    if not source_path.is_file():
        raise FactualQaPilotError(f"visual fixture is missing: {source_path}")
    source = pymupdf.open(source_path)
    converted = None
    try:
        converted = pymupdf.open("pdf", source.convert_to_pdf())
        page.show_pdf_page(
            pymupdf.Rect(85, y_start, 510, min(y_start + 270, 650)),
            converted,
            0,
            keep_proportion=True,
        )
    finally:
        if converted is not None:
            converted.close()
        source.close()


def _selected_retrieval(
    chunks_by_course: dict[str, list[Any]],
) -> tuple[dict[str, Any], Qwen3TextEmbedder]:
    profile = load_release_profile(PROFILE_PATH)
    selection = next(
        entry
        for entry in profile.components
        if entry.component == ComponentKind.RETRIEVER
    )
    configuration = selection.implementation.configuration  # type: ignore[union-attr]
    embedder = Qwen3TextEmbedder(
        EMBEDDING_ROOT,
        instruction=str(configuration["query_instruction"]),
        device=str(configuration["device"]),
        dtype=str(configuration["dtype"]),
        batch_size=int(configuration["embedding_batch_size"]),
        max_length=int(configuration["embedding_max_length"]),
        model_name=str(configuration["embedding_model"]),
        model_revision=str(configuration["embedding_revision"]),
    )
    retrievers = {
        course_id: build_selected_retriever(
            selection,
            chunks,
            embedder=embedder,
            allow_control_fallback=False,
        )
        for course_id, chunks in chunks_by_course.items()
    }
    return retrievers, embedder


async def execute(assets: dict[str, Any], *, ollama_url: str) -> dict[str, Any]:
    instrument = assets["instrument"]
    corpus = assets["corpus"]
    source_map = {item["source_unit_id"]: item for item in corpus["source_units"]}
    author = DeepSeekJsonTransport(instrument["model_roles"]["author"])
    independent = OllamaJsonTransport(
        instrument["model_roles"]["independent_reviewer"], url=ollama_url
    )
    dispute = DeepSeekJsonTransport(instrument["model_roles"]["dispute_reviewer"])
    call_counts = {"author": 0, "independent": 0, "dispute": 0}
    external_cost = 0.0
    started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="fqa-v3-oracle-pilot-") as name:
        chunks_by_course, page_sources, ingestion = _build_product_corpus(
            corpus, Path(name)
        )
        retrievers, embedder = _selected_retrieval(chunks_by_course)
        results: list[dict[str, Any]] = []
        for blueprint in corpus["case_blueprints"]:
            context = _source_context(blueprint, source_map=source_map)
            author_call = await author.call_json(
                system=_author_system_prompt(),
                prompt=_author_prompt(blueprint, source_context=context),
                task="factual_qa_v3_source_linked_authoring",
                schema=AUTHOR_SCHEMA,
            )
            call_counts["author"] += 1
            external_cost += author_call.approximate_cost_usd
            _enforce_cost(instrument, external_cost)
            authored = author_call.value
            deterministic = deterministic_case_checks(
                blueprint, authored, source_map=source_map
            )
            if blueprint.get("target_claim_ids"):
                target_ok = set(authored.get("selected_claim_ids", [])) == set(
                    blueprint["target_claim_ids"]
                )
                deterministic["checks"]["target_claims_exact"] = target_ok
                deterministic["passed"] = all(deterministic["checks"].values())

            review_call = await independent.call_json(
                system=_review_system_prompt(),
                prompt=_review_prompt(
                    blueprint, authored=authored, source_context=context
                ),
                task="factual_qa_v3_independent_review",
                schema=REVIEW_SCHEMA,
            )
            call_counts["independent"] += 1
            review = validate_review(review_call.value)

            retrieval = _retrieval_record(
                blueprint,
                question=str(authored.get("question", "")),
                retriever=retrievers[blueprint["course_id"]],
                page_sources=page_sources[blueprint["course_id"]],
            )
            dispute_call = None
            dispute_review = None
            if (
                review["verdict"] != ("accept" if deterministic["passed"] else "reject")
                and call_counts["dispute"]
                < instrument["execution"]["dispute_reviewer_call_limit"]
            ):
                dispute_call = await dispute.call_json(
                    system=_review_system_prompt(),
                    prompt=_review_prompt(
                        blueprint, authored=authored, source_context=context
                    ),
                    task="factual_qa_v3_dispute_review",
                    schema=REVIEW_SCHEMA,
                )
                call_counts["dispute"] += 1
                external_cost += dispute_call.approximate_cost_usd
                _enforce_cost(instrument, external_cost)
                dispute_review = validate_review(dispute_call.value)

            results.append(
                {
                    "blueprint_id": blueprint["blueprint_id"],
                    "slice": blueprint["slice"],
                    "course_id": blueprint["course_id"],
                    "expected_action": blueprint["expected_action"],
                    "evidence_unit_ids": blueprint.get("evidence_unit_ids", []),
                    "distractor_unit_ids": blueprint.get("distractor_unit_ids", []),
                    "authored_case": authored,
                    "deterministic": deterministic,
                    "retrieval": retrieval,
                    "independent_review": review,
                    "dispute_review": dispute_review,
                    "author_call": _call_record(author_call),
                    "independent_review_call": _call_record(review_call),
                    "dispute_review_call": _call_record(dispute_call),
                    "retained": deterministic["passed"],
                    "human_audit_priority": (
                        not deterministic["passed"]
                        or review["verdict"]
                        != ("accept" if deterministic["passed"] else "reject")
                        or blueprint["slice"]
                        in {
                            "multimodal",
                            "multi-evidence-text",
                            "adversarial-integrity",
                        }
                    ),
                }
            )

        summary = _analyze(
            instrument,
            results,
            ingestion=ingestion,
            external_cost=external_cost,
        )
        audit_packet = _audit_packet(results, sample_size=8)
        return {
            "run_type": PILOT_ID,
            "status": summary["status"],
            "method_version": instrument["method_version"],
            "instrument_path": str(assets["instrument_path"].relative_to(ROOT)),
            "instrument_sha256": sha256_file(assets["instrument_path"]),
            "base_corpus_path": str(assets["base_path"].relative_to(ROOT)),
            "base_corpus_sha256": assets["base_sha256"],
            "data_boundary": instrument["case_design"]["data_boundary"],
            "private_data_read": False,
            "private_data_emitted": False,
            "call_counts": call_counts,
            "ingestion": ingestion,
            "retrieval_provider": {
                "implementation": "qwen3-hybrid-v1",
                "embedding_model": embedder.model_name,
                "embedding_revision": embedder.model_revision,
                "execution": embedder.execution,
                "model_load_seconds": embedder.model_load_seconds,
                "usage": embedder.usage_snapshot().model_dump(mode="json"),
            },
            "elapsed_seconds": time.perf_counter() - started,
            "summary": summary,
            "results": results,
            "human_audit_packet": audit_packet,
        }


def _retrieval_record(
    blueprint: dict[str, Any],
    *,
    question: str,
    retriever: Any,
    page_sources: dict[int, str],
) -> dict[str, Any]:
    if blueprint["expected_action"] != ANSWER_ACTION:
        return {
            "applicable": False,
            "all_evidence_at_3": None,
            "evidence_recall_at_5": None,
            "retrieved_source_unit_ids": [],
        }
    hits = retriever.retrieve(question, limit=5)
    retrieved = [
        page_sources.get(hit.chunk.page_start or -1, "unknown") for hit in hits
    ]
    required = set(blueprint["evidence_unit_ids"])
    top3 = set(retrieved[:3])
    top5 = set(retrieved[:5])
    return {
        "applicable": True,
        "all_evidence_at_3": required.issubset(top3),
        "evidence_recall_at_5": len(required & top5) / len(required),
        "retrieved_source_unit_ids": retrieved,
    }


def _analyze(
    instrument: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    ingestion: dict[str, Any],
    external_cost: float,
) -> dict[str, Any]:
    total = len(results)
    answerable = [item for item in results if item["expected_action"] == ANSWER_ACTION]
    boundary = [item for item in results if item["expected_action"] in BOUNDARY_ACTIONS]
    multimodal = [item for item in results if item["slice"] == "multimodal"]
    deterministic_passes = sum(item["deterministic"]["passed"] for item in results)
    boundary_passes = sum(
        item["authored_case"].get("action") == item["expected_action"]
        for item in boundary
    )
    agreements = sum(
        item["independent_review"]["verdict"]
        == ("accept" if item["deterministic"]["passed"] else "reject")
        for item in results
    )
    all3 = sum(item["retrieval"]["all_evidence_at_3"] is True for item in answerable)
    recall5 = [item["retrieval"]["evidence_recall_at_5"] for item in answerable]
    multimodal3 = sum(
        item["retrieval"]["all_evidence_at_3"] is True for item in multimodal
    )
    leakage = sum(
        bool(
            set(item.get("distractor_unit_ids", []))
            & {
                citation.get("source_unit_id")
                for citation in item["authored_case"].get("citations", [])
                if isinstance(citation, dict)
            }
        )
        for item in results
    )
    revisions = {
        item["author_call"]["provider_revision"]
        for item in results
        if item["author_call"] is not None
    }
    model_identity_stable = (
        all(
            item["author_call"]
            and item["author_call"]["provider_model"] == "deepseek-v4-flash"
            and item["independent_review_call"]
            and item["independent_review_call"]["provider_model"] == LOCAL_GENERAL_MODEL
            for item in results
        )
        and None not in revisions
        and "" not in revisions
        and len(revisions) == 1
    )
    metrics = {
        "pdf_ingestion_rate": ingestion["pdf_ingestion_rate"],
        "source_integrity_rate": 1.0,
        "author_completion_rate": sum(bool(item["authored_case"]) for item in results)
        / total,
        "deterministic_provenance_rate": deterministic_passes / total,
        "boundary_action_rate": boundary_passes / len(boundary),
        "all_evidence_at_3": all3 / len(answerable),
        "evidence_recall_at_5": statistics.fmean(recall5),
        "multimodal_all_evidence_at_3": multimodal3 / len(multimodal),
        "independent_review_completion_rate": sum(
            bool(item["independent_review"]) for item in results
        )
        / total,
        "deterministic_independent_agreement_rate": agreements / total,
        "cross_course_leakage_count": leakage,
        "private_data_calls": 0,
        "external_cost_usd": external_cost,
        "model_identity_stable": model_identity_stable,
    }
    gates = instrument["quality_gates"]
    gate_results = {
        "pdf_ingestion_rate": metrics["pdf_ingestion_rate"]
        >= gates["pdf_ingestion_rate_min"],
        "source_integrity_rate": metrics["source_integrity_rate"]
        >= gates["source_integrity_rate_min"],
        "author_completion_rate": metrics["author_completion_rate"]
        >= gates["author_completion_rate_min"],
        "deterministic_provenance_rate": metrics["deterministic_provenance_rate"]
        >= gates["deterministic_provenance_rate_min"],
        "boundary_action_rate": metrics["boundary_action_rate"]
        >= gates["boundary_action_rate_min"],
        "all_evidence_at_3": metrics["all_evidence_at_3"]
        >= gates["all_evidence_at_3_min"],
        "evidence_recall_at_5": metrics["evidence_recall_at_5"]
        >= gates["evidence_recall_at_5_min"],
        "multimodal_all_evidence_at_3": metrics["multimodal_all_evidence_at_3"]
        >= gates["multimodal_all_evidence_at_3_min"],
        "independent_review_completion_rate": metrics[
            "independent_review_completion_rate"
        ]
        >= gates["independent_review_completion_rate_min"],
        "cross_course_leakage_count": metrics["cross_course_leakage_count"]
        <= gates["cross_course_leakage_count_max"],
        "private_data_calls": metrics["private_data_calls"]
        <= gates["private_data_calls_max"],
        "external_cost_usd": metrics["external_cost_usd"]
        <= gates["external_cost_usd_max"],
        "model_identity_stable": metrics["model_identity_stable"]
        is gates["model_identity_stable_required"],
    }
    passed = all(gate_results.values())
    return {
        "status": "machine-gates-passed-human-audit-required"
        if passed
        else "machine-gates-failed-refine",
        "decision": "human-audit-required" if passed else "refine-method",
        "machine_gates_passed": passed,
        "scale_authorized": False,
        "case_count": total,
        "answerable_cases": len(answerable),
        "boundary_cases": len(boundary),
        "retained_cases": deterministic_passes,
        "quarantined_cases": total - deterministic_passes,
        "metrics": metrics,
        "gate_results": gate_results,
        "failed_gates": sorted(
            name for name, value in gate_results.items() if not value
        ),
        "slice_counts": dict(
            sorted(Counter(item["slice"] for item in results).items())
        ),
    }


def _audit_packet(
    results: list[dict[str, Any]], *, sample_size: int
) -> list[dict[str, Any]]:
    prioritized = sorted(
        results,
        key=lambda item: (
            not item["human_audit_priority"],
            item["slice"]
            not in {"multimodal", "multi-evidence-text", "adversarial-integrity"},
            item["blueprint_id"],
        ),
    )
    selected_items: list[dict[str, Any]] = []
    seen_slices: set[str] = set()
    for item in prioritized:
        if item["slice"] not in seen_slices:
            selected_items.append(item)
            seen_slices.add(item["slice"])
        if len(selected_items) == sample_size:
            break
    selected_ids = {item["blueprint_id"] for item in selected_items}
    for item in prioritized:
        if item["blueprint_id"] not in selected_ids:
            selected_items.append(item)
            selected_ids.add(item["blueprint_id"])
        if len(selected_items) == sample_size:
            break
    return [
        {
            "blueprint_id": item["blueprint_id"],
            "slice": item["slice"],
            "question": item["authored_case"].get("question"),
            "answer": item["authored_case"].get("answer"),
            "action": item["authored_case"].get("action"),
            "citations": item["authored_case"].get("citations"),
            "deterministic": item["deterministic"],
            "retrieval": item["retrieval"],
            "independent_review": item["independent_review"],
            "requested_checks": [
                "question_clarity",
                "answer_or_action_correctness",
                "complete_source_support",
                "citation_lineage",
                "source_page_verification",
            ],
        }
        for item in selected_items
    ]


def _enforce_cost(instrument: dict[str, Any], cost: float) -> None:
    if cost > instrument["execution"]["cost_stop_usd"]:
        raise FactualQaPilotError(f"cost stop reached: USD {cost:.6f}")


def _write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
    except FileExistsError as error:
        raise FactualQaPilotError(
            f"refusing to overwrite run output: {path}"
        ) from error


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=INSTRUMENT_PATH)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-deepseek", action="store_true")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434/api/generate")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    if arguments.execute and not arguments.allow_deepseek:
        parser.error("execution requires --allow-deepseek")
    return arguments


def main() -> None:
    arguments = _arguments()
    instrument_path = (
        arguments.instrument
        if arguments.instrument.is_absolute()
        else ROOT / arguments.instrument
    )
    output_path = (
        arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
    )
    load_dotenv(ROOT / ".env", override=False)
    assets = validate_assets(instrument_path)
    preflight = build_preflight(assets, ollama_url=arguments.ollama_url)
    if not arguments.execute:
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return
    require_bounded_pilot_operation_allowed(PILOT_ID)
    if preflight["status"] != "ready":
        raise FactualQaPilotError("v3 oracle pilot preflight is blocked")
    result = asyncio.run(execute(assets, ollama_url=arguments.ollama_url))
    _write_json_exclusive(output_path, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "decision": result["summary"]["decision"],
                "machine_gates_passed": result["summary"]["machine_gates_passed"],
                "failed_gates": result["summary"]["failed_gates"],
                "metrics": result["summary"]["metrics"],
                "output": str(output_path.relative_to(ROOT)),
                "scale_authorized": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
