"""Prospective persona-robust release selection for governed autonomy V2.1.

This successor keeps hidden learner truth deterministic while varying public
student wording.  It compares T0 and T1-v2 autonomous on paired histories;
T1-v2 reactive is a diagnostic ablation.  A frozen LLM utterance bank must be
provided explicitly and is never allowed to create gold labels.

Modes:
    --validate   validate the matrix and optional bank without product runs.
    --simulate   execute the real product boundary without provider calls.

Provider-backed product confirmation is intentionally a later, separately
frozen checkpoint.  This runner never performs external calls.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.governed_full_autonomy_v2_1_hidden_state_runtime import (  # noqa: E402
    HIDDEN_STATE_CONCEPT_CARDS,
    build_hidden_state_runtime_factory,
)
from src.digital_twin.evaluation.autonomy_contract import (  # noqa: E402
    AutonomyEvaluationCaseV1,
    AutonomySystemManifestV1,
)
from src.digital_twin.evaluation.autonomy_independent_scoring import (  # noqa: E402
    AutonomyRawEvidenceV2,
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
    PERSONA_ROBUST_PERSONAS,
    LearnerPersona,
    SimulatorFamily,
)
from src.digital_twin.evaluation.simulated_learner_v2 import (  # noqa: E402
    FrozenLearnerUtteranceBankV1,
    ResponseRealizationMethod,
    TextRealisingLearnerV2,
    utterance_bank_sha256,
)
from src.digital_twin.evaluation.simulated_learner_v1 import LearnerUtterance  # noqa: E402
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)

PROGRAM_ID = "governed-full-autonomy-v2-1-persona-robust-release-selection-022"
CLOCK_ORIGIN = datetime(2026, 9, 9, 0, 0, tzinfo=UTC)
PRIMARY_CONDITIONS = ("t0-grounded-control", "t1-v2-autonomous")
ABLATION_CONDITION = "t1-v2-reactive"
DEFAULT_SEEDS = (3101, 3102, 3103)
REALIZATION_METHODS = tuple(ResponseRealizationMethod)
CONTRASTS = [("t1-v2-autonomous", "t0-grounded-control")]


def _code_revision() -> dict[str, str | bool]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return {"revision": revision, "dirty": dirty}


def load_bank(path: Path | None) -> FrozenLearnerUtteranceBankV1 | None:
    if path is None:
        return None
    return FrozenLearnerUtteranceBankV1.model_validate_json(path.read_text())


def build_case(
    *,
    persona: LearnerPersona,
    family: SimulatorFamily,
    method: ResponseRealizationMethod,
    seed: int,
    days: int,
) -> AutonomyEvaluationCaseV1:
    case_id = f"pr-{family.value}-{persona.name}-{method.value}-{seed}"
    return AutonomyEvaluationCaseV1(
        case_id=case_id,
        course_id="persona-robust-course",
        release_id="persona-robust-release",
        learner_id=f"learner-{hashlib.sha256(case_id.encode()).hexdigest()[:16]}",
        duration_seconds=(days + 1) * DAY_SECONDS,
        events=[],
    )


def _manifest(condition: str, revision: str) -> AutonomySystemManifestV1:
    return AutonomySystemManifestV1(
        system_id=f"persona-robust:{condition}",
        flow_id="hidden-state-learner-closed-loop-v2",
        adapter_version=StudentProductAutonomyAdapterV1.adapter_version,
        code_revision=revision,
        graph_version="product-runtime",
        release_profile_sha256=hashlib.sha256(
            b"persona-robust-release-selection-v1"
        ).hexdigest(),
        policy_version=1,
        model_bindings={},
        network_free=True,
    )


def observable_hard_gates(
    *,
    case: AutonomyEvaluationCaseV1,
    result: HiddenStateRunResult,
) -> dict[str, bool]:
    evidence = AutonomyRawEvidenceV2.model_validate(result.independent_evidence)
    actions = result.response.actions
    delivered = [item for item in actions if item.status == "delivered"]
    action_ids = [item.action_id for item in actions]
    delivery_ids = [item.action_id for item in delivered]
    expected_scope = (case.learner_id, case.course_id, case.release_id)
    scope_valid = all(
        (item.recipient_id, item.course_id, item.release_id) == expected_scope
        for item in actions
    )
    raw_scope_valid = all(
        (
            item.internal_student_id,
            item.internal_course_id,
            item.internal_release_id,
        )
        == (
            evidence.expected_internal_student_id,
            evidence.expected_internal_course_id,
            evidence.expected_internal_release_id,
        )
        and item.policy_version == evidence.expected_policy_version
        and item.profile_sha256 == evidence.expected_profile_sha256
        for item in evidence.actions
    )
    bounded = all(
        trace.planning_calls <= 1
        and trace.generation_calls <= 1
        and trace.repair_calls <= 1
        for trace in evidence.traces
    )
    return {
        "correct-recipient-course-release": scope_valid and raw_scope_valid,
        "valid-citation-lineage": all(item.citation_lineage_valid for item in actions),
        "no-duplicate-action": len(action_ids) == len(set(action_ids)),
        "no-duplicate-delivery": len(delivery_ids) == len(set(delivery_ids)),
        "bounded-loop": bounded,
        "restart-consistent": all(
            item.before_sha256 == item.after_sha256
            for item in evidence.restart_checks
        ),
        "authority-preserved": all(
            item.policy_version == evidence.expected_policy_version
            and item.profile_sha256 == evidence.expected_profile_sha256
            for item in evidence.traces
        ),
    }


async def run_case(
    *,
    root: Path,
    condition: str,
    persona: LearnerPersona,
    family: SimulatorFamily,
    method: ResponseRealizationMethod,
    seed: int,
    days: int,
    bank: FrozenLearnerUtteranceBankV1 | None,
    code_revision: str,
    utterance_observer: Callable[[LearnerUtterance], None] | None = None,
) -> tuple[HiddenStateRunResult, HiddenStateCaseScoreV1, dict[str, bool]]:
    case = build_case(
        persona=persona, family=family, method=method, seed=seed, days=days
    )
    learner = TextRealisingLearnerV2(
        persona=persona,
        family=family,
        seed=seed,
        cards=HIDDEN_STATE_CONCEPT_CARDS,
        realization_method=method,
        frozen_bank=bank,
    )
    adapter = StudentProductAutonomyAdapterV1(
        condition=condition,
        manifest=_manifest(condition, code_revision),
        runtime_factory=build_hidden_state_runtime_factory(
            root / condition / case.case_id,
            condition,
            provider_backed=False,
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
            utterance_observer=utterance_observer,
        )
    finally:
        adapter.close()
    score = score_hidden_state_case(
        condition=condition,
        truth=result.truth,
        response=result.response,
        evidence=result.learner_evidence,
    )
    return result, score, observable_hard_gates(case=case, result=result)


def _is_ablation_cell(
    *, persona_index: int, method_index: int, family: SimulatorFamily, seed: int
) -> bool:
    """Balanced 18-cell diagnostic: one seed/family per persona-method pair."""

    if seed != DEFAULT_SEEDS[0]:
        return False
    expected_family = (
        SimulatorFamily.BKT_LIKE
        if (persona_index + method_index) % 2 == 0
        else SimulatorFamily.LOGISTIC_LIKE
    )
    return family is expected_family


async def run_program(
    *,
    output_dir: Path,
    bank: FrozenLearnerUtteranceBankV1,
    days: int,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    resamples: int = 1000,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    runtime_root = output_dir / "runtime"
    code = _code_revision()
    started = time.perf_counter()
    scores: list[HiddenStateCaseScoreV1] = []
    hard_gate_rows: list[dict[str, Any]] = []
    with (
        (output_dir / "scores.jsonl").open("x") as score_file,
        (output_dir / "truth.jsonl").open("x") as truth_file,
        (output_dir / "responses.jsonl").open("x") as response_file,
    ):
        for persona_index, persona in enumerate(PERSONA_ROBUST_PERSONAS):
            for method_index, method in enumerate(REALIZATION_METHODS):
                for family in SimulatorFamily:
                    for seed in seeds:
                        conditions = list(PRIMARY_CONDITIONS)
                        if _is_ablation_cell(
                            persona_index=persona_index,
                            method_index=method_index,
                            family=family,
                            seed=seed,
                        ):
                            conditions.append(ABLATION_CONDITION)
                        for condition in conditions:
                            result, score, hard_gates = await run_case(
                                root=runtime_root,
                                condition=condition,
                                persona=persona,
                                family=family,
                                method=method,
                                seed=seed,
                                days=days,
                                bank=bank,
                                code_revision=str(code["revision"]),
                            )
                            scores.append(score)
                            hard_gate_rows.append(
                                {
                                    "case_id": result.truth.case_id,
                                    "condition": condition,
                                    "gates": hard_gates,
                                }
                            )
                            score_file.write(score.model_dump_json() + "\n")
                            truth_file.write(
                                json.dumps(
                                    {"condition": condition, **result.truth.to_dict()},
                                    sort_keys=True,
                                )
                                + "\n"
                            )
                            response_file.write(
                                json.dumps(
                                    {
                                        "condition": condition,
                                        **result.response.model_dump(mode="json"),
                                    },
                                    sort_keys=True,
                                )
                                + "\n"
                            )
    summary = summarize_hidden_state_scores(
        scores, contrasts=CONTRASTS, resamples=resamples
    )
    failures = [
        row
        for row in hard_gate_rows
        if not all(bool(value) for value in row["gates"].values())
    ]
    summary["hard_safety"] = {
        "cases": len(hard_gate_rows),
        "all_passed": not failures,
        "failed_cases": failures,
    }
    summary["run"] = {
        "program_id": PROGRAM_ID,
        "status": "completed-development",
        "selection_authorized": False,
        "code": code,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "network": "none",
        "days": days,
        "seeds": list(seeds),
        "personas": [item.name for item in PERSONA_ROBUST_PERSONAS],
        "families": [item.value for item in SimulatorFamily],
        "realization_methods": [item.value for item in REALIZATION_METHODS],
        "primary_histories_per_condition": (
            len(PERSONA_ROBUST_PERSONAS)
            * len(REALIZATION_METHODS)
            * len(tuple(SimulatorFamily))
            * len(seeds)
        ),
        "ablation_histories": sum(
            1
            for p in range(len(PERSONA_ROBUST_PERSONAS))
            for m in range(len(REALIZATION_METHODS))
            for family in SimulatorFamily
            for seed in seeds
            if _is_ablation_cell(
                persona_index=p,
                method_index=m,
                family=family,
                seed=seed,
            )
        ),
        "bank_id": bank.bank_id,
        "bank_sha256": utterance_bank_sha256(bank),
        "cases": len(scores),
        "bootstrap_resamples": resamples,
    }
    (output_dir / "hard-gates.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in hard_gate_rows)
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--frozen-bank", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / "reports" / "generated" / PROGRAM_ID,
    )
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seeds", type=int, nargs="*", default=list(DEFAULT_SEEDS))
    parser.add_argument("--resamples", type=int, default=1000)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.execute:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "method_evaluation_execution")
        raise SystemExit("provider-backed execution is not implemented in successor 022")

    bank = load_bank(args.frozen_bank)
    primary_histories = (
        len(PERSONA_ROBUST_PERSONAS)
        * len(REALIZATION_METHODS)
        * len(tuple(SimulatorFamily))
        * len(args.seeds)
    )
    if args.validate:
        print(
            json.dumps(
                {
                    "program_id": PROGRAM_ID,
                    "status": "valid",
                    "primary_histories_per_condition": primary_histories,
                    "frozen_bank": None if bank is None else bank.bank_id,
                    "selection_authorized": False,
                }
            )
        )
        return 0
    if bank is None:
        raise SystemExit("--simulate requires --frozen-bank; no implicit LLM surrogate")
    days = 5 if args.smoke else args.days
    seeds = (args.seeds[0],) if args.smoke else tuple(args.seeds)
    summary = asyncio.run(
        run_program(
            output_dir=args.output_dir,
            bank=bank,
            days=days,
            seeds=seeds,
            resamples=20 if args.smoke else args.resamples,
        )
    )
    print(json.dumps(summary["run"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
