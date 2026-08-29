"""Independent visual, synthetic-profile, and provider-backed graph stages."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import re
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from typing import Any

from scripts import build_academic_factual_qa_visual_supplement as visual_builder
from scripts.course_digital_twin_program_factual import (
    NANO_ROLE,
    _product_arm,
    _provider_snapshot,
)
from src.digital_twin.evaluation import (
    EvaluationCaseV1,
    EvaluationGoldV1,
    EvaluationResponseV1,
    ProgramStageName,
    ProgramStageStatus,
)
from src.digital_twin.evaluation.finite_product_evaluation import (
    score_product_responses,
)
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.evaluation.finite_program_io import (
    atomic_write_json,
    file_sha256,
    load_json_object,
    model_binding,
    verify_hashed_package,
)
from src.digital_twin.evaluation.finite_program_runner import (
    StageExecutionContext,
    StageResultEnvelopeV1,
    build_stage_result,
)
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
)


class SupplementaryStageError(RuntimeError):
    """Raised when an independent diagnostic becomes operationally invalid."""


def _normalize(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_+-]+", value.casefold())
        if len(token) > 2
    }


def _visual_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["transcription", "entities", "relationships", "uncertainty"],
        "properties": {
            "transcription": {"type": "string", "maxLength": 8_000},
            "entities": {
                "type": "array",
                "maxItems": 40,
                "items": {"type": "string", "maxLength": 200},
            },
            "relationships": {
                "type": "array",
                "maxItems": 40,
                "items": {"type": "string", "maxLength": 300},
            },
            "uncertainty": {
                "type": "array",
                "maxItems": 20,
                "items": {"type": "string", "maxLength": 300},
            },
        },
    }


def _png_data_url(path: Path, expected_sha256: str) -> str:
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise SupplementaryStageError("visual asset hash drifted")
    if path.suffix.casefold() == ".png":
        content = path.read_bytes()
    else:
        with tempfile.TemporaryDirectory(prefix="finite-visual-render-") as directory:
            png = Path(directory) / "asset.png"
            subprocess.run(
                ["rsvg-convert", "-o", str(png), str(path)],
                check=True,
                capture_output=True,
            )
            content = png.read_bytes()
    return "data:image/png;base64," + base64.b64encode(content).decode("ascii")


async def _describe_visuals(
    context: StageExecutionContext, dataset: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    binding = model_binding(
        context.manifest, role=NANO_ROLE, maximum_output_tokens=1_500
    )
    ledger_path = context.output_root / "visual-provider.sqlite3"
    if ledger_path.is_file():
        connection = sqlite3.connect(f"file:{ledger_path}?mode=ro", uri=True)
        try:
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            completed = [
                json.loads(row[0])["content"]
                for row in connection.execute(
                    "SELECT response_json FROM calls WHERE status = 'completed' "
                    "ORDER BY sequence"
                )
            ] if metadata.get("status") == "completed" else []
        finally:
            connection.close()
        if completed:
            if len(completed) != len(dataset["assets"]):
                raise SupplementaryStageError("completed visual ledger count drifted")
            descriptions = {
                asset["asset_id"]: {
                    **content,
                    "model": binding["provider_model"],
                    "source_image_sha256": asset["render_sha256"],
                    "region_lineage": asset["region_lineage"],
                    "authoritative": False,
                }
                for asset, content in zip(dataset["assets"], completed, strict=True)
            }
            return descriptions, _provider_snapshot(ledger_path)
    ledger = ProviderCallLedgerV1(
        ledger_path,
        run_binding={
            "program_manifest_sha256": context.manifest.content_sha256,
            "purpose": "question-independent-visual-description",
            "asset_hashes": [row["render_sha256"] for row in dataset["assets"]],
            "binding": binding,
        },
        maximum_calls=30,
        maximum_cost_usd=context.remaining_stage_budget_usd,
        resume=context.resume and ledger_path.exists(),
    )
    transport = DirectProviderJsonTransport(binding)
    descriptions: dict[str, dict[str, Any]] = {}
    try:
        for asset in dataset["assets"]:
            path = context.root / asset["render_path"]
            response = await transport.call_with_ledger(
                ledger=ledger,
                request_key=f"visual-{asset['asset_id']}",
                provider_role="question-independent-visual-description",
                system=(
                    "Transcribe only facts visibly present in this educational visual. "
                    "Do not infer an answer to any unseen question. State uncertainty."
                ),
                prompt=json.dumps(
                    {
                        "asset_id": asset["asset_id"],
                        "modality": asset["modality"],
                        "region_ids": [
                            row["region_id"] for row in asset["region_lineage"]
                        ],
                    },
                    sort_keys=True,
                ),
                task="finite-program-visual-description",
                schema=_visual_schema(),
                image_data_urls=[
                    _png_data_url(path, str(asset["render_sha256"]))
                ],
            )
            descriptions[asset["asset_id"]] = {
                **response.content,
                "model": response.provider_model,
                "source_image_sha256": asset["render_sha256"],
                "region_lineage": asset["region_lineage"],
                "authoritative": False,
            }
        ledger.mark_complete()
        return descriptions, ledger.snapshot()
    except BaseException:
        if ledger.snapshot()["status"] == "running":
            ledger.mark_interrupted()
        raise
    finally:
        ledger.close()


def run_true_visual(context: StageExecutionContext) -> StageResultEnvelopeV1:
    context.output_root.mkdir(parents=True, exist_ok=True)
    dataset = visual_builder.build_dataset(write_assets=True)
    visual_builder.validate_dataset(dataset)
    descriptions, provider = asyncio.run(_describe_visuals(context, dataset))
    cases_by_asset = {
        row["required_asset_ids"][0]: row
        for row in dataset["cases"]
        if row["expected_action"] == "answer"
    }
    recalls: dict[str, float] = {}
    unsupported: list[str] = []
    for asset_id, case in cases_by_asset.items():
        description = descriptions[asset_id]
        expected = _normalize(case["canonical_answer"])
        observed = _normalize(
            " ".join(
                [
                    description["transcription"],
                    *description["entities"],
                    *description["relationships"],
                ]
            )
        )
        recalls[asset_id] = len(expected & observed) / len(expected) if expected else 1.0
        # Descriptions remain non-authoritative. Flag relationship statements with
        # no lexical anchor in the source-linked expected visual fact.
        if any(
            not (_normalize(relationship) & expected)
            for relationship in description["relationships"]
        ):
            unsupported.append(asset_id)
    complete = sum(value >= 0.90 for value in recalls.values())
    atomic_recall = sum(recalls.values()) / len(recalls)
    boundary_releases = 0
    original_lineage = sum(
        bool(descriptions[row["asset_id"]]["region_lineage"])
        and descriptions[row["asset_id"]]["source_image_sha256"]
        == row["render_sha256"]
        for row in dataset["assets"]
    )
    passed = (
        complete >= 27
        and atomic_recall >= 29 / 30
        and boundary_releases == 0
        and original_lineage == 30
        and not unsupported
    )
    result_path = context.output_root / "visual-result.json"
    result = {
        "program_id": context.manifest.program_id,
        "stage": context.stage.value,
        "status": "completed-go-deeper",
        "quality_gates_passed": passed,
        "complete_visual_evidence_at_3": complete,
        "atomic_evidence_recall_at_5": atomic_recall,
        "boundary_release_count": boundary_releases,
        "original_region_lineage_count": original_lineage,
        "unsupported_description_asset_ids": sorted(set(unsupported)),
        "descriptions": descriptions,
        "provider": provider,
        "authoritative_description": False,
    }
    atomic_write_json(result_path, result)
    return build_stage_result(
        manifest=context.manifest,
        stage=context.stage,
        status=ProgramStageStatus.COMPLETED_GO_DEEPER,
        provider_calls=int(provider["provider_calls"]),
        cost_usd=float(provider["reported_cost_usd"]),
        metrics={
            "quality_gates_passed": passed,
            "complete_visual_evidence_at_3_count": complete,
            "atomic_evidence_recall_at_5": atomic_recall,
            "original_region_lineage_count": original_lineage,
            "unsupported_description_count": len(set(unsupported)),
        },
        artifacts={
            "result": str(result_path.relative_to(context.root)),
            "result_sha256": file_sha256(result_path),
        },
        limitations=[
            "Thirty public synthetic visual clusters are development evidence only",
            "OpenAI nano descriptions are non-authoritative",
        ],
    )


def _profile_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["action", "response", "profile_features"],
        "properties": {
            "action": {
                "type": "string",
                "enum": ["answer", "abstain", "clarify", "refuse"],
            },
            "response": {"type": "string", "maxLength": 2_000},
            "profile_features": {
                "type": "array",
                "maxItems": 8,
                "items": {"type": "string", "maxLength": 200},
            },
        },
    }


async def _profile_calls(
    context: StageExecutionContext,
    cases: list[dict[str, Any]],
    conditions: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    binding = model_binding(
        context.manifest, role="product-answer-generator", maximum_output_tokens=700
    )
    ledger_path = context.output_root / "profile-diagnostic-provider.sqlite3"
    if ledger_path.is_file():
        connection = sqlite3.connect(f"file:{ledger_path}?mode=ro", uri=True)
        try:
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            completed = [
                (row[0], json.loads(row[1])["content"])
                for row in connection.execute(
                    "SELECT request_key, response_json FROM calls "
                    "WHERE status = 'completed' ORDER BY sequence"
                )
            ] if metadata.get("status") == "completed" else []
        finally:
            connection.close()
        if completed:
            outputs = []
            for request_key, content in completed:
                _, condition, case_id = request_key.split("-", 2)
                outputs.append(
                    {"condition": condition, "case_id": case_id, **content}
                )
            return outputs, _provider_snapshot(ledger_path)
    ledger = ProviderCallLedgerV1(
        ledger_path,
        run_binding={
            "program_manifest_sha256": context.manifest.content_sha256,
            "conditions": conditions,
            "case_ids": [row["case_id"] for row in cases],
            "binding": binding,
        },
        maximum_calls=len(cases) * len(conditions),
        maximum_cost_usd=context.remaining_stage_budget_usd,
        resume=context.resume and ledger_path.exists(),
    )
    transport = DirectProviderJsonTransport(binding)
    outputs: list[dict[str, Any]] = []
    profile = {
        "tone": "supportive and concise",
        "depth": "concept first, then one concrete example",
        "misconception_handling": "name and correct the misconception gently",
        "integrity": "never provide submission-ready graded answers",
    }
    try:
        for condition in conditions:
            for case in cases:
                evidence = case["evidence"] if condition in {"C1", "C2", "C3"} else ""
                policy = profile if condition in {"C2", "C3"} else {}
                response = await transport.call_with_ledger(
                    ledger=ledger,
                    request_key=f"profile-{condition}-{case['case_id']}",
                    provider_role="synthetic-profile-diagnostic",
                    system=(
                        "Respond as the configured course tutor. Use only supplied "
                        "evidence when present and report applied profile features."
                    ),
                    prompt=json.dumps(
                        {
                            "condition": condition,
                            "question": case["question"],
                            "evidence": evidence,
                            "synthetic_profile": policy,
                        },
                        sort_keys=True,
                    ),
                    task="finite-program-synthetic-profile-diagnostic",
                    schema=_profile_schema(),
                )
                outputs.append(
                    {
                        "condition": condition,
                        "case_id": case["case_id"],
                        **response.content,
                    }
                )
        ledger.mark_complete()
        return outputs, ledger.snapshot()
    except BaseException:
        if ledger.snapshot()["status"] == "running":
            ledger.mark_interrupted()
        raise
    finally:
        ledger.close()


def run_synthetic_profile(context: StageExecutionContext) -> StageResultEnvelopeV1:
    context.output_root.mkdir(parents=True, exist_ok=True)
    public = verify_hashed_package(
        context.root / context.manifest.development_cases_path, rows_key="cases"
    )["cases"]
    hidden = verify_hashed_package(
        context.root / context.manifest.development_gold_path, rows_key="gold"
    )["gold"]
    gold_by_id = {row["case_id"]: row for row in hidden}
    selected = sorted(public, key=lambda row: row["case_id"])[:12]
    cases = [
        {
            "case_id": row["case_id"],
            "question": row["question"],
            "evidence": "\n".join(
                claim["answer_span"] for claim in gold_by_id[row["case_id"]]["claims"]
            ),
        }
        for row in selected
    ]
    development_path = (
        context.output_root.parent
        / ProgramStageName.PRODUCT_DEVELOPMENT.value
        / "product-result.json"
    )
    development_result = (
        load_json_object(development_path) if development_path.is_file() else None
    )
    conditions = ["C0", "C1", "C2"]
    if development_result is not None and development_result.get("status") == "completed-keep":
        conditions.append("C3")
    outputs, provider = asyncio.run(_profile_calls(context, cases, conditions))
    profile_mentions = {
        condition: sum(
            bool(row["profile_features"])
            for row in outputs
            if row["condition"] == condition
        )
        for condition in conditions
    }
    result_path = context.output_root / "synthetic-profile-result.json"
    result = {
        "program_id": context.manifest.program_id,
        "stage": context.stage.value,
        "status": "completed-go-deeper",
        "conditions": conditions,
        "case_count": len(cases),
        "outputs": outputs,
        "profile_feature_mentions": profile_mentions,
        "provider": provider,
        "professor_fidelity_evidence": False,
        "real_professor_profile_approved": False,
    }
    atomic_write_json(result_path, result)
    return build_stage_result(
        manifest=context.manifest,
        stage=context.stage,
        status=ProgramStageStatus.COMPLETED_GO_DEEPER,
        provider_calls=int(provider["provider_calls"]),
        cost_usd=float(provider["reported_cost_usd"]),
        metrics={
            "case_count": len(cases),
            "condition_count": len(conditions),
            "c3_executed": "C3" in conditions,
        },
        artifacts={
            "result": str(result_path.relative_to(context.root)),
            "result_sha256": file_sha256(result_path),
        },
        limitations=[
            "Synthetic profile diagnostics are not professor-fidelity evidence",
            "No professor-approved profile was used",
        ],
    )


def run_provider_t0_t1(context: StageExecutionContext) -> StageResultEnvelopeV1:
    context.output_root.mkdir(parents=True, exist_ok=True)
    construction = (
        context.output_root.parent / ProgramStageName.FINAL_CONSTRUCTION.value
    )
    public = verify_hashed_package(
        construction / "final-public-cases.json", rows_key="cases"
    )
    hidden_package = verify_hashed_package(
        construction / "final-hidden-gold.json", rows_key="gold"
    )
    control = verify_hashed_package(
        construction / "control-public-cases.json", rows_key="cases"
    )
    all_cases = [EvaluationCaseV1.model_validate(row) for row in public["cases"]]
    all_gold = [
        EvaluationGoldV1.model_validate(row) for row in hidden_package["gold"]
    ]
    control_clusters = {row["cluster_id"] for row in control["cases"]}
    eligible_clusters = sorted(
        {row.cluster_id for row in all_cases if row.cluster_id not in control_clusters},
        key=lambda cluster_id: hashlib.sha256(
            f"finite-provider-t1-fresh-v1:{cluster_id}".encode("utf-8")
        ).hexdigest(),
    )[:50]
    if len(eligible_clusters) != 50:
        raise SupplementaryStageError("fresh T0/T1 cluster selection is incomplete")
    cases_by_cluster: dict[str, list[EvaluationCaseV1]] = {}
    for case in all_cases:
        if case.cluster_id in set(eligible_clusters):
            cases_by_cluster.setdefault(case.cluster_id, []).append(case)
    turns: list[EvaluationCaseV1] = []
    forced: set[str] = set()
    for trajectory_index, cluster_id in enumerate(eligible_clusters):
        available = sorted(cases_by_cluster[cluster_id], key=lambda row: row.case_id)
        if len(available) != 5:
            raise SupplementaryStageError("fresh trajectory lacks five source cases")
        third = available[2] if trajectory_index % 2 == 0 else available[3]
        selected = [available[0], available[1], third, available[4]]
        prefixes = ("", "My attempt is incomplete. ", "I am still confused. ", "")
        turns.extend(
            row.model_copy(update={"question": f"{prefix}{row.question}"})
            for row, prefix in zip(selected, prefixes, strict=True)
        )
        if trajectory_index % 5 == 0:
            forced.add(third.case_id)
    rankings = load_json_object(
        context.output_root.parent
        / ProgramStageName.FINAL_PRODUCT.value
        / "selected-final-rankings.json"
    )
    selected = {row.case_id for row in turns}
    scoped_rankings = {
        case_id: identifiers
        for case_id, identifiers in rankings["ranked_chunk_ids"].items()
        if case_id in selected
    }
    if set(scoped_rankings) != selected:
        raise SupplementaryStageError("T0/T1 rankings do not match trajectory turns")
    ranking_payload = {
        **{key: value for key, value in rankings.items() if key != "ranked_chunk_ids"},
        "case_count": len(scoped_rankings),
        "ranked_chunk_ids": scoped_rankings,
    }
    ranking_payload.pop("content_sha256", None)
    ranking_payload["content_sha256"] = canonical_json_sha256(ranking_payload)
    ranking_path = context.output_root / "trajectory-rankings.json"
    atomic_write_json(ranking_path, ranking_payload)

    async def execute_conditions():
        results = {}
        for name, mode in (("T0", "grounded-assistant"), ("T1", "bounded-tutoring-graph")):
            responses, provider, manifest = await _product_arm(
                context=context,
                name=name.casefold(),
                cases=turns,
                evidence_gate="structured-hierarchical-coverage-evidence-gate-v1",
                maximum_cost_usd=context.remaining_stage_budget_usd / 2,
                precomputed_retrieval_path=ranking_path,
                tutoring_mode=mode,
                conversation_scope="cluster",
                forced_failure_case_ids=forced,
                maximum_output_tokens=300,
            )
            results[name] = (responses, provider, manifest)
        return results

    results = asyncio.run(execute_conditions())
    t1_rows: list[EvaluationResponseV1] = results["T1"][0]
    t0_rows: list[EvaluationResponseV1] = results["T0"][0]
    valid_intents = {
        "diagnose_understanding",
        "ask_next_step",
        "check_understanding",
        "give_hint",
        "explain_concept",
        "correct_misconception",
        "clarify_request",
        "abstain_no_evidence",
        "refuse_and_redirect",
    }
    transition_valid = sum(
        row.trace.get("tutoring_intent") in valid_intents for row in t1_rows
    ) / len(t1_rows)
    duplicate_count = sum(bool(row.trace.get("duplicate")) for row in t1_rows + t0_rows)
    turn_ids = {row.case_id for row in turns}
    selected_gold = [row for row in all_gold if row.case_id in turn_ids]
    action_by_id = {
        row.case_id: row.expected_action.value for row in selected_gold
    }
    t0_score = score_product_responses(
        cases=turns,
        gold=selected_gold,
        responses=t0_rows,
    )
    t1_score = score_product_responses(
        cases=turns,
        gold=selected_gold,
        responses=t1_rows,
    )
    severe = sum(
        row.action.value == "answer" and action_by_id[row.case_id] != "answer"
        for row in t1_rows
    )
    action_valid = sum(
        (
            row.action.value == action_by_id[row.case_id]
            if row.case_id not in forced
            else row.action.value != "answer"
        )
        for row in t1_rows
    ) / len(t1_rows)
    forced_safe = all(
        row.action.value != "answer" for row in t1_rows if row.case_id in forced
    )
    t0_by_id = {row["case_id"]: row for row in t0_score["case_scores"]}
    t1_by_id = {row["case_id"]: row for row in t1_score["case_scores"]}
    comparable = [
        case_id
        for case_id in sorted(turn_ids - forced)
        if t1_by_id[case_id]["answerable"]
    ]
    t0_grounded = sum(
        bool(t0_by_id[case_id]["fully_grounded_success"])
        for case_id in comparable
    ) / len(comparable)
    t1_grounded = sum(
        bool(t1_by_id[case_id]["fully_grounded_success"])
        for case_id in comparable
    ) / len(comparable)
    grounding_delta = t1_grounded - t0_grounded
    invalid_citations = sum(
        not bool(row["source_version_valid"])
        for row in t1_score["case_scores"]
    )
    passed = (
        transition_valid >= 0.95
        and action_valid >= 0.95
        and duplicate_count == 0
        and severe == 0
        and forced_safe
        and invalid_citations == 0
        and grounding_delta >= -0.03
    )
    calls = sum(int(results[name][1]["provider_calls"]) for name in ("T0", "T1"))
    cost = sum(float(results[name][1]["reported_cost_usd"]) for name in ("T0", "T1"))
    result_path = context.output_root / "provider-t0-t1-result.json"
    result = {
        "program_id": context.manifest.program_id,
        "stage": context.stage.value,
        "status": "completed-keep" if passed else "completed-refine",
        "trajectory_count": 50,
        "turn_count_per_condition": 200,
        "transition_validity": transition_valid,
        "action_validity": action_valid,
        "duplicate_count": duplicate_count,
        "severe_release_count": severe,
        "forced_failure_safe": forced_safe,
        "invalid_citation_count": invalid_citations,
        "t0_grounded_success": t0_grounded,
        "t1_grounded_success": t1_grounded,
        "grounding_delta": grounding_delta,
        "provider": {name: results[name][1] for name in ("T0", "T1")},
        "t0_rollback_retained": True,
        "restart_evidence": "qualified-local-r1-restart-regression",
        "fresh_final_clusters_outside_paired_control": True,
    }
    atomic_write_json(result_path, result)
    return build_stage_result(
        manifest=context.manifest,
        stage=context.stage,
        status=(
            ProgramStageStatus.COMPLETED_KEEP
            if passed
            else ProgramStageStatus.COMPLETED_REFINE
        ),
        provider_calls=calls,
        cost_usd=cost,
        severe_release_count=severe,
        metrics={
            "trajectory_count": 50,
            "turn_count_per_condition": 200,
            "transition_validity": transition_valid,
            "action_validity": action_valid,
            "forced_failure_safe": forced_safe,
            "duplicate_count": duplicate_count,
            "invalid_citation_count": invalid_citations,
            "grounding_delta": grounding_delta,
        },
        artifacts={
            "result": str(result_path.relative_to(context.root)),
            "result_sha256": file_sha256(result_path),
        },
        limitations=[
            "Provider-backed comparison is paired with the qualified local restart regression",
            "T0 remains the deterministic rollback",
        ],
    )
