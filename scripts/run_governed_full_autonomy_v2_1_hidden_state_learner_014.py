"""Hidden-state learner extension of the governed autonomy evaluation (014).

Extends program 010's frozen contracts with the dimensions the successor
study found missing: learner-state calibration against hidden truth,
perception accuracy (concept attribution and attempt assessment), and
proactive quality and timing measured from hidden receptivity and delivered
timestamps. The real product services are driven through the same adapter
as 010 by a closed-loop simulated learner.

Modes:
    --validate   build cases and check contracts (no product run)
    --simulate   network-free run with the deterministic engine (default)
    --execute    provider-backed run; refuses until a bounded authorization
                 for PROGRAM_ID exists in the repository freeze registry

Usage:
    uv run python scripts/run_governed_full_autonomy_v2_1_hidden_state_learner_014.py --simulate
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from src.digital_twin.evaluation.autonomy_contract import (  # noqa: E402
    AutonomyEvaluationCaseV1,
    AutonomySystemManifestV1,
)
from src.digital_twin.evaluation.autonomy_learner_driver import (  # noqa: E402
    DAY_SECONDS,
    DriverScheduleV1,
    HiddenStateRunResult,
    run_hidden_state_learner_case,
)
from src.digital_twin.evaluation.autonomy_learning_scoring import (  # noqa: E402
    HiddenStateCaseScoreV1,
    score_hidden_state_case,
    summarize_hidden_state_scores,
)
from src.digital_twin.evaluation.autonomy_product_adapter import (  # noqa: E402
    StudentProductAutonomyAdapterV1,
)
from src.digital_twin.evaluation.learner_simulator import (  # noqa: E402
    PERSONAS,
    LearnerPersona,
    SimulatorFamily,
)
from src.digital_twin.evaluation.simulated_learner_v1 import (  # noqa: E402
    TextRealisingLearnerV1,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)
from scripts.governed_full_autonomy_v2_1_hidden_state_runtime import (  # noqa: E402
    HIDDEN_STATE_CONCEPT_CARDS,
    build_hidden_state_runtime_factory,
)

PROGRAM_ID = "governed-full-autonomy-v2-1-hidden-state-learner-extension-014"
CLOCK_ORIGIN = datetime(2026, 9, 7, 0, 0, tzinfo=UTC)
CONDITIONS: tuple[str, ...] = (
    "t0-grounded-control",
    "t1-v1-reactive-control",
    "t1-v2-reactive",
    "t1-v2-autonomous",
)
DEFAULT_SEEDS = (2000, 2001, 2002)
CONTRASTS = [
    ("t1-v2-autonomous", "t0-grounded-control"),
    ("t1-v2-autonomous", "t1-v1-reactive-control"),
    ("t1-v2-reactive", "t1-v1-reactive-control"),
    ("t1-v2-autonomous", "t1-v2-reactive"),
]


def _code_revision() -> dict[str, str | bool]:
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, check=True, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=REPOSITORY_ROOT, check=True, capture_output=True, text=True).stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"revision": "unknown", "dirty": True}
    return {"revision": revision, "dirty": dirty}


def build_case(*, persona: LearnerPersona, family: SimulatorFamily, seed: int, days: int) -> AutonomyEvaluationCaseV1:
    case_id = f"hs-{family.value}-{persona.name}-{seed}"
    return AutonomyEvaluationCaseV1(
        case_id=case_id,
        course_id="hidden-state-course",
        release_id="hidden-state-release",
        learner_id=f"learner-{hashlib.sha256(case_id.encode()).hexdigest()[:16]}",
        duration_seconds=(days + 1) * DAY_SECONDS,
        events=[],
    )


def _manifest(condition: str, *, network_free: bool, code_revision: str) -> AutonomySystemManifestV1:
    return AutonomySystemManifestV1(
        system_id=f"actual-product:{condition}",
        flow_id="hidden-state-learner-closed-loop-v1",
        adapter_version=StudentProductAutonomyAdapterV1.adapter_version,
        code_revision=code_revision,
        graph_version="product-runtime",
        release_profile_sha256=hashlib.sha256(b"hidden-state-learner-v1").hexdigest(),
        policy_version=1,
        model_bindings={} if network_free else {"engine": "pending-authorization"},
        network_free=network_free,
    )


async def run_case(
    *,
    root: Path,
    condition: str,
    persona: LearnerPersona,
    family: SimulatorFamily,
    seed: int,
    days: int,
    provider_backed: bool = False,
    code_revision: str = "unknown",
) -> tuple[HiddenStateRunResult, HiddenStateCaseScoreV1]:
    case = build_case(persona=persona, family=family, seed=seed, days=days)
    learner = TextRealisingLearnerV1(persona=persona, family=family, seed=seed, cards=HIDDEN_STATE_CONCEPT_CARDS)
    adapter = StudentProductAutonomyAdapterV1(
        condition=condition,
        manifest=_manifest(condition, network_free=not provider_backed, code_revision=code_revision),
        runtime_factory=build_hidden_state_runtime_factory(
            root / condition / case.case_id, condition, provider_backed=provider_backed
        ),
        clock_origin=CLOCK_ORIGIN,
    )
    try:
        result = await run_hidden_state_learner_case(
            adapter,
            case,
            learner,
            schedule=DriverScheduleV1(days=days),
            clock_origin=CLOCK_ORIGIN,
        )
    finally:
        adapter.close()
    score = score_hidden_state_case(
        condition=condition,
        truth=result.truth,
        response=result.response,
        evidence=result.learner_evidence,
    )
    return result, score


async def run_program(
    *,
    output_dir: Path,
    conditions: tuple[str, ...],
    personas: tuple[LearnerPersona, ...],
    families: tuple[SimulatorFamily, ...],
    seeds: tuple[int, ...],
    days: int,
    provider_backed: bool,
    resamples: int,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_root = output_dir / "runtime"
    code = _code_revision()
    scores: list[HiddenStateCaseScoreV1] = []
    started = time.perf_counter()
    with (output_dir / "scores.jsonl").open("w") as score_file, (output_dir / "truth.jsonl").open("w") as truth_file, (output_dir / "responses.jsonl").open("w") as response_file:
        for condition in conditions:
            for family in families:
                for persona in personas:
                    for seed in seeds:
                        result, score = await run_case(
                            root=runtime_root,
                            condition=condition,
                            persona=persona,
                            family=family,
                            seed=seed,
                            days=days,
                            provider_backed=provider_backed,
                            code_revision=str(code["revision"]),
                        )
                        scores.append(score)
                        score_file.write(score.model_dump_json() + "\n")
                        truth_file.write(json.dumps({"condition": condition, **result.truth.to_dict()}, sort_keys=True) + "\n")
                        response_file.write(json.dumps({"condition": condition, **result.response.model_dump(mode="json")}, sort_keys=True) + "\n")
    summary = summarize_hidden_state_scores(scores, contrasts=CONTRASTS, resamples=resamples)
    summary["run"] = {
        "program_id": PROGRAM_ID,
        "code": code,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "network": "none" if not provider_backed else "provider",
        "conditions": list(conditions),
        "personas": [p.name for p in personas],
        "families": [f.value for f in families],
        "seeds": list(seeds),
        "days": days,
        "cases": len(scores),
        "bootstrap_resamples": resamples,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    (output_dir / "summary.md").write_text(render_markdown(summary))
    return summary


def render_markdown(summary: dict) -> str:
    lines = [
        "| Condition | n | Attrib. acc. | Assess. agree | Attempts recog. | MSE vs hidden | AUROC | Msgs | Wasted | Follow-up | Final mastery | Quiet/Freq/Cooldown viol. | Calls |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for condition, row in summary["aggregate"].items():
        lines.append(
            "| {c} | {n} | {aa} | {ag} | {ar} | {mse} | {auroc} | {msgs} | {w} | {f} | {m} | {q}/{fr}/{cd} | {calls} |".format(
                c=condition,
                n=row["n_cases"],
                aa=_fmt(row["attribution_accuracy"]),
                ag=_fmt(row["assessment_agreement"]),
                ar=_fmt(row["attempts_recognised"]),
                mse=_fmt(row["mse_vs_hidden"]),
                auroc=_fmt(row["auroc_next_outcome"]),
                msgs=_fmt(row["messages_delivered"], 1),
                w=_fmt(row["wasted_rate"]),
                f=_fmt(row["follow_up_fraction"]),
                m=_fmt(row["final_hidden_mastery"]),
                q=_fmt(row["quiet_hour_violations"], 2),
                fr=_fmt(row["frequency_violations"], 2),
                cd=_fmt(row["cooldown_violations"], 2),
                calls=_fmt(row["provider_calls"], 1),
            )
        )
    lines.append("")
    lines.append("| Contrast | Metric | n pairs | Mean diff | 95% CI |")
    lines.append("| --- | --- | --- | --- | --- |")
    for contrast, metrics in summary["paired_contrasts"].items():
        for metric, stats in metrics.items():
            if stats["n_pairs"] == 0:
                continue
            lines.append(
                f"| {contrast} | {metric} | {stats['n_pairs']} | {_fmt(stats['mean_difference'], 4)} | [{_fmt(stats['ci95'][0], 4)}, {_fmt(stats['ci95'][1], 4)}] |"
            )
    return "\n".join(lines) + "\n"


def _fmt(value, digits: int = 3) -> str:
    return "n/a" if value is None else f"{float(value):.{digits}f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--execute", action="store_true", help="provider-backed; requires bounded authorization")
    parser.add_argument("--output-dir", type=Path, default=REPOSITORY_ROOT / "reports" / "generated" / PROGRAM_ID)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seeds", type=int, nargs="*", default=list(DEFAULT_SEEDS))
    parser.add_argument("--personas", nargs="*", default=[p.name for p in PERSONAS])
    parser.add_argument("--conditions", nargs="*", default=list(CONDITIONS))
    parser.add_argument("--resamples", type=int, default=1000)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.execute:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "method_evaluation_execution")
        raise SystemExit("provider-backed execution is not wired in this revision; use --simulate")

    personas = tuple(p for p in PERSONAS if p.name in set(args.personas))
    seeds = tuple(args.seeds)
    days = args.days
    conditions = tuple(args.conditions)
    resamples = args.resamples
    if args.smoke:
        personas, seeds, days, resamples = personas[:1], seeds[:1], 6, 20

    if args.validate:
        for persona in personas:
            for family in SimulatorFamily:
                for seed in seeds:
                    build_case(persona=persona, family=family, seed=seed, days=days)
        print(json.dumps({"program_id": PROGRAM_ID, "status": "valid", "cases_per_condition": len(personas) * 2 * len(seeds)}))
        return 0

    summary = asyncio.run(
        run_program(
            output_dir=args.output_dir,
            conditions=conditions,
            personas=personas,
            families=tuple(SimulatorFamily),
            seeds=seeds,
            days=days,
            provider_backed=False,
            resamples=resamples,
        )
    )
    print(json.dumps(summary["run"], indent=2))
    print((args.output_dir / "summary.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
