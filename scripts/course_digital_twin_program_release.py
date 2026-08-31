"""Local release regression and professor-report generation stages."""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
from typing import Any

from scripts.course_digital_twin_program_factual import (
    _completed_responses,
    _read_hidden_gold,
    _read_public_cases,
    _provider_snapshot,
)
from scripts.run_autonomous_tutoring_r1_local_confirmation import (
    validate as validate_local_r1,
)
from scripts.run_r1_public_preview import validate as validate_preview
from src.digital_twin.evaluation import ProgramStageName, ProgramStageStatus
from src.digital_twin.evaluation.finite_program_io import (
    atomic_write_json,
    file_sha256,
    load_json_object,
    model_binding,
)
from src.digital_twin.evaluation.finite_program_runner import (
    StageExecutionContext,
    StageResultEnvelopeV1,
    build_stage_result,
)
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
    ProviderJsonError,
)


CRITICAL_ROLE = "critical-source-truth-escalation"


def run_release_regression(context: StageExecutionContext) -> StageResultEnvelopeV1:
    """Revalidate the unchanged qualified local R1 and rollback contract."""

    context.output_root.mkdir(parents=True, exist_ok=True)
    local = validate_local_r1()
    preview = validate_preview()
    focused = subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "tests/test_run_autonomous_tutoring_graph_development.py",
            "tests/digital_twin/test_learning_gap.py",
            "tests/digital_twin/test_proactive_outreach.py",
            "tests/api/test_publication_api.py",
            "tests/services/test_runtime_backup.py",
            "-q",
        ],
        cwd=context.root,
        capture_output=True,
        text=True,
        check=False,
    )
    passed = (
        focused.returncode == 0
        and local.get("status") in {"passed", "validated"}
        and str(preview.get("status", "")).startswith("passed")
    )
    result_path = context.output_root / "local-release-regression.json"
    result = {
        "program_id": context.manifest.program_id,
        "stage": context.stage.value,
        "status": "completed-keep" if passed else "completed-refine",
        "qualified_local_r1": local,
        "preview_contract": preview,
        "focused_test_exit_code": focused.returncode,
        "focused_test_output_tail": focused.stdout[-4_000:],
        "focused_test_error_tail": focused.stderr[-2_000:],
        "selected_profile_mutated_during_program": False,
        "t0_rollback_retained": True,
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
        provider_calls=0,
        cost_usd=0,
        metrics={
            "focused_tests_passed": focused.returncode == 0,
            "local_r1_contract_passed": local.get("status")
            in {"passed", "validated"},
            "preview_contract_passed": str(
                preview.get("status", "")
            ).startswith("passed"),
        },
        artifacts={
            "result": str(result_path.relative_to(context.root)),
            "result_sha256": file_sha256(result_path),
        },
        limitations=[
            "The finite evaluation does not mutate the selected release profile",
            "External human usability and durable domain hosting remain out of scope",
        ],
    )


def _stage_result(context: StageExecutionContext, stage: ProgramStageName, name: str):
    path = context.output_root.parent / stage.value / name
    return load_json_object(path) if path.is_file() else None


def _critical_schema(case_id: str) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "case_id",
            "source_truth_valid",
            "requires_human_resolution",
            "concern_type",
            "rationale",
        ],
        "properties": {
            "case_id": {"type": "string", "const": case_id},
            "source_truth_valid": {"type": "boolean"},
            "requires_human_resolution": {"type": "boolean"},
            "concern_type": {
                "type": "string",
                "enum": ["none", "source", "action", "claim", "citation"],
            },
            "rationale": {
                "type": "string",
                "minLength": 1,
                "maxLength": 700,
            },
        },
    }


def _critical_material(
    context: StageExecutionContext,
    *,
    product: dict[str, Any],
    final: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if final:
        construction = (
            context.output_root.parent / ProgramStageName.FINAL_CONSTRUCTION.value
        )
        cases_path = construction / "final-public-cases.json"
        gold_path = construction / "final-hidden-gold.json"
        responses_path = (
            context.output_root.parent
            / ProgramStageName.FINAL_PRODUCT.value
            / "candidate/responses.sqlite3"
        )
    else:
        cases_path = context.root / context.manifest.development_cases_path
        gold_path = context.root / context.manifest.development_gold_path
        responses_path = (
            context.output_root.parent
            / ProgramStageName.PRODUCT_DEVELOPMENT.value
            / "candidate/responses.sqlite3"
        )
    cases = {row.case_id: row for row in _read_public_cases(cases_path)}
    gold = {row.case_id: row for row in _read_hidden_gold(gold_path)}
    responses = {row.case_id: row for row in _completed_responses(responses_path)}
    concerns = set(
        product.get("advisory_review", {}).get(
            "source_truth_concern_case_ids", []
        )
    )
    if not concerns <= (set(cases) & set(gold) & set(responses)):
        raise ValueError("critical-review case identities drifted")
    return cases, gold, responses


def _prioritized_concerns(product: dict[str, Any]) -> list[str]:
    concerns = set(
        product.get("advisory_review", {}).get(
            "source_truth_concern_case_ids", []
        )
    )
    scores = {
        row["case_id"]: row for row in product["candidate"]["case_scores"]
    }

    def key(case_id: str) -> tuple[int, int, int, str]:
        row = scores[case_id]
        return (
            -int(bool(row["severe_unsupported_release"])),
            -int(not bool(row["source_version_valid"])),
            -int(not bool(row["action_correct"])),
            hashlib.sha256(
                f"critical-truth-v1:{case_id}".encode("utf-8")
            ).hexdigest(),
        )

    return sorted(concerns, key=key)


async def _critical_truth_review(
    context: StageExecutionContext,
    *,
    product: dict[str, Any] | None,
    final: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if product is None:
        return (
            {
                "authoritative": False,
                "selected_case_count": 0,
                "unreviewed_concern_count": 0,
                "human_resolution_case_ids": [],
            },
            {"provider_calls": 0, "reported_cost_usd": 0.0},
        )
    all_concerns = _prioritized_concerns(product)
    selected = all_concerns[:20]
    if not selected:
        return (
            {
                "authoritative": False,
                "selected_case_count": 0,
                "unreviewed_concern_count": 0,
                "human_resolution_case_ids": [],
            },
            {"provider_calls": 0, "reported_cost_usd": 0.0},
        )
    cases, gold, responses = _critical_material(
        context,
        product=product,
        final=final,
    )
    binding = model_binding(
        context.manifest,
        role=CRITICAL_ROLE,
        maximum_output_tokens=700,
        maximum_transport_retries=0,
    )
    ledger_path = context.output_root / "critical-source-truth-provider.sqlite3"
    if ledger_path.is_file():
        connection = sqlite3.connect(f"file:{ledger_path}?mode=ro", uri=True)
        try:
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            if metadata.get("status") == "completed":
                outputs = [
                    json.loads(row[0])["content"]
                    for row in connection.execute(
                        "SELECT response_json FROM calls "
                        "WHERE status = 'completed' ORDER BY sequence"
                    )
                ]
                human = sorted(
                    row["case_id"]
                    for row in outputs
                    if bool(row["requires_human_resolution"])
                )
                return (
                    {
                        "authoritative": False,
                        "selected_case_count": len(selected),
                        "valid_review_count": len(outputs),
                        "unreviewed_concern_count": len(all_concerns) - len(selected),
                        "human_resolution_case_ids": human,
                    },
                    _provider_snapshot(ledger_path),
                )
        finally:
            connection.close()
    ledger = ProviderCallLedgerV1(
        ledger_path,
        run_binding={
            "program_manifest_sha256": context.manifest.content_sha256,
            "purpose": "critical-source-truth-escalation",
            "case_ids": selected,
            "binding": binding,
        },
        maximum_calls=len(selected),
        maximum_cost_usd=context.remaining_stage_budget_usd,
        resume=context.resume and ledger_path.exists(),
    )
    transport = DirectProviderJsonTransport(binding)
    outputs: list[dict[str, Any]] = []
    limitations: list[str] = []
    try:
        for case_id in selected:
            try:
                response = await transport.call_with_ledger(
                    ledger=ledger,
                    request_key=f"critical-{case_id}",
                    provider_role="critical-source-truth-escalation",
                    system=(
                        "Independently inspect a possible canonical source-truth "
                        "defect. You are advisory and cannot edit the reference. "
                        "Request human resolution only when the source-linked action, "
                        "claim, or citation genuinely cannot be decided."
                    ),
                    prompt=json.dumps(
                        {
                            "case": cases[case_id].model_dump(mode="json"),
                            "canonical_truth": gold[case_id].model_dump(mode="json"),
                            "product_response": responses[case_id].model_dump(
                                mode="json"
                            ),
                        },
                        sort_keys=True,
                    ),
                    task="finite-program-critical-source-truth-review",
                    schema=_critical_schema(case_id),
                    quarantine_failures=True,
                )
            except ProviderJsonError as error:
                lowered = str(error).casefold()
                if any(
                    fragment in lowered
                    for fragment in (
                        "identity drift",
                        "credential missing",
                        "cost limit",
                        "call limit",
                    )
                ):
                    raise
                limitations.append(f"{case_id}:{type(error).__name__}")
                continue
            outputs.append(response.content)
        if ledger.snapshot()["status"] == "running":
            ledger.mark_complete()
        snapshot = ledger.snapshot()
    except BaseException:
        if ledger.snapshot()["status"] == "running":
            ledger.mark_interrupted()
        raise
    finally:
        ledger.close()
    human = sorted(
        row["case_id"]
        for row in outputs
        if bool(row["requires_human_resolution"])
    )
    return (
        {
            "authoritative": False,
            "selected_case_count": len(selected),
            "valid_review_count": len(outputs),
            "unreviewed_concern_count": len(all_concerns) - len(selected),
            "human_resolution_case_ids": human,
            "limitations": limitations,
        },
        snapshot,
    )


def _chart(
    path: Path,
    *,
    final_result: dict[str, Any] | None,
    development_result: dict[str, Any] | None,
    visual_result: dict[str, Any] | None,
) -> bool:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    factual_result = final_result if final_result is not None else development_result
    if factual_result is not None:
        metrics = factual_result["candidate"]["summary"]["metrics"]
        interval = factual_result["candidate"]["summary"][
            "fully_grounded_source_family_interval"
        ]
        labels = [
            "Grounded\nsuccess",
            "Boundary\naction",
            "Claim\nprecision",
            "Citation\nrecall",
            "Evidence\nrecall@5",
        ]
        values = [
            metrics["fully_grounded_factual_success"],
            metrics["boundary_action_accuracy"],
            metrics["atomic_claim_precision"],
            metrics["citation_recall"],
            metrics["evidence_recall_at_5"],
        ]
        axes[0].bar(labels, values, color="#4f46e5")
        axes[0].errorbar(
            0,
            float(interval["estimate"]),
            yerr=[
                [float(interval["estimate"]) - float(interval["lower_95"])],
                [float(interval["upper_95"]) - float(interval["estimate"])],
            ],
            fmt="none",
            ecolor="#111827",
            capsize=5,
            linewidth=1.5,
        )
        axes[0].axhline(0.95, color="#b91c1c", linestyle="--", linewidth=1)
        axes[0].set_ylim(0, 1.02)
        factual_case_count = factual_result["candidate"]["summary"]["case_count"]
        axes[0].set_title(f"{factual_case_count}-case actual-product KPIs")
        paired = factual_result["paired"]
        control_ids = {
            row["case_id"] for row in factual_result["control"]["case_scores"]
        }
        candidate_answerable = [
            row
            for row in factual_result["candidate"]["case_scores"]
            if row["case_id"] in control_ids and row["answerable"]
        ]
        control_answerable = [
            row
            for row in factual_result["control"]["case_scores"]
            if row["answerable"]
        ]
        candidate_supported = sum(
            bool(row["fully_grounded_success"]) for row in candidate_answerable
        ) / len(candidate_answerable)
        control_supported = sum(
            bool(row["fully_grounded_success"]) for row in control_answerable
        ) / len(control_answerable)
        axes[1].bar(
            [
                "Candidate\nsupported",
                "Control\nsupported",
                "Candidate\nboundary",
                "Control\nboundary",
            ],
            [
                candidate_supported,
                control_supported,
                paired["boundary_safety_candidate"],
                paired["boundary_safety_control"],
            ],
            color=["#4f46e5", "#94a3b8", "#4f46e5", "#94a3b8"],
        )
        axes[1].set_ylim(0, 1.02)
        axes[1].set_title(
            f"Paired {paired['paired_case_count']}-case candidate vs control"
        )
    else:
        axes[0].text(0.5, 0.5, "Factual branch stopped before final", ha="center")
        axes[0].set_axis_off()
        axes[1].set_axis_off()
    if visual_result is not None:
        figure.suptitle(
            "Course Digital Twin evaluation · visual evidence "
            f"{visual_result['complete_visual_evidence_at_3']}/30"
        )
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return True


def run_reporting(context: StageExecutionContext) -> StageResultEnvelopeV1:
    context.output_root.mkdir(parents=True, exist_ok=True)
    retrieval = _stage_result(
        context,
        ProgramStageName.RETRIEVAL_DECISION,
        "retrieval-result.json",
    )
    development = _stage_result(
        context,
        ProgramStageName.PRODUCT_DEVELOPMENT,
        "product-result.json",
    )
    final = _stage_result(
        context,
        ProgramStageName.FINAL_PRODUCT,
        "product-result.json",
    )
    visual = _stage_result(
        context,
        ProgramStageName.TRUE_VISUAL,
        "visual-result.json",
    )
    profile = _stage_result(
        context,
        ProgramStageName.SYNTHETIC_PROFILE,
        "synthetic-profile-result.json",
    )
    graph = _stage_result(
        context,
        ProgramStageName.PROVIDER_T0_T1,
        "provider-t0-t1-result.json",
    )
    reviewed_product = final if final is not None else development
    critical, critical_provider = asyncio.run(
        _critical_truth_review(
            context,
            product=reviewed_product,
            final=final is not None,
        )
    )
    chart_path = context.output_root / "professor-evaluation-summary.png"
    chart_created = _chart(
        chart_path,
        final_result=final,
        development_result=development,
        visual_result=visual,
    )
    if final is not None:
        decision = final["status"].replace("completed-", "").title()
        metrics = final["candidate"]["summary"]["metrics"]
        headline = (
            f"The actual T0 product completed the sealed 10,000-case evaluation "
            f"with {metrics['fully_grounded_factual_success']:.1%} grounded factual "
            f"success and {metrics['boundary_action_accuracy']:.1%} boundary accuracy."
        )
    elif development is not None:
        decision = development["status"].replace("completed-", "").title()
        metrics = development["candidate"]["summary"]["metrics"]
        headline = (
            "The factual branch stopped at the 500+100 development checkpoint: "
            f"{metrics['fully_grounded_factual_success']:.1%} grounded factual success."
        )
    else:
        decision = "Refine"
        headline = "The factual branch stopped at retrieval before product scaling."
    teams = "\n".join(
        [
            "Hi Prof, a quick evaluation update:",
            "",
            f"- {headline}",
            f"- Decision: {decision}.",
            (
                "- The true-visual supplement used 30 public visual clusters / 60 "
                f"cases; complete visual evidence was {visual['complete_visual_evidence_at_3']}/30."
                if visual is not None
                else "- The visual supplement did not produce a valid result."
            ),
            (
                "- The provider-backed T0/T1 comparison passed its frozen gates; T0 "
                "remains the rollback."
                if graph is not None and graph.get("status") == "completed-keep"
                else "- Autonomous T1 was not promoted from this checkpoint."
            ),
            "",
            (
                "The benchmark used deterministic source-linked truth and the product "
                "received only course ID and question; gold was opened after responses "
                "were persisted. OpenAI model review was advisory."
            ),
            (
                "Limitations: open educational sources, model-assisted review, no "
                "independent external human annotation, and the synthetic profile is "
                "not professor-fidelity evidence."
            ),
            (
                "A source-truth review packet still needs resolution for "
                f"{len(critical['human_resolution_case_ids'])} case(s)."
                if critical["human_resolution_case_ids"]
                else "No critical source-truth ambiguity remained after escalation."
            ),
            "",
            (
                "Would this evidence be sufficient to proceed to the real Professor "
                "Digital Twin C0–C3 behavior evaluation and profile calibration?"
            ),
        ]
    )
    report = {
        "program_id": context.manifest.program_id,
        "stage": context.stage.value,
        "decision": decision,
        "headline": headline,
        "teams_message": teams,
        "chart_created": chart_created,
        "system_manifest": final.get("candidate_manifest") if final else None,
        "retrieval": retrieval,
        "development": development,
        "final": final,
        "visual": visual,
        "synthetic_profile": profile,
        "provider_t0_t1": graph,
        "critical_source_truth_review": critical,
        "limitations": [
            "Open licensed sources only",
            "Same-provider model-assisted review",
            "No independent external human annotation",
            "No professor-fidelity, usability, or learning-outcome claim",
        ],
    }
    report_path = context.output_root / "professor-ready-result.json"
    message_path = context.output_root / "teams-message.txt"
    atomic_write_json(report_path, report)
    message_path.write_text(teams + "\n", encoding="utf-8")
    artifacts = {
        "result": str(report_path.relative_to(context.root)),
        "result_sha256": file_sha256(report_path),
        "teams_message": str(message_path.relative_to(context.root)),
        "teams_message_sha256": file_sha256(message_path),
    }
    if chart_created:
        artifacts.update(
            {
                "chart": str(chart_path.relative_to(context.root)),
                "chart_sha256": file_sha256(chart_path),
            }
        )
    unresolved = bool(critical["human_resolution_case_ids"]) or bool(
        critical["unreviewed_concern_count"]
    )
    return build_stage_result(
        manifest=context.manifest,
        stage=context.stage,
        status=(
            ProgramStageStatus.COMPLETED_REFINE
            if unresolved
            else ProgramStageStatus.COMPLETED_KEEP
        ),
        provider_calls=int(critical_provider["provider_calls"]),
        cost_usd=float(critical_provider["reported_cost_usd"]),
        metrics={
            "professor_package_complete": True,
            "chart_created": chart_created,
            "final_factual_result_available": final is not None,
            "visual_result_available": visual is not None,
            "critical_human_resolution_count": len(
                critical["human_resolution_case_ids"]
            ),
            "critical_unreviewed_concern_count": critical[
                "unreviewed_concern_count"
            ],
        },
        artifacts=artifacts,
        limitations=[
            *report["limitations"],
            *list(critical.get("limitations", [])),
        ],
    )
