"""Network-free paired comparison of learner estimators and timing policies.

This is the harness for run `successor-learner-timing-simulation-001`. It
drives simulated learners with hidden state through thirty virtual days under
every (estimator, policy) condition, scores calibration and intervention
quality against the hidden truth, and reports paired bootstrap intervals.
The engine side (estimator plus policy) never reads hidden state except in the
explicit `oracle` bound.
"""

from __future__ import annotations

import itertools
import json
import random
import statistics
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from src.digital_twin.evaluation.learner_simulator import (
    DEFAULT_CONCEPTS,
    MASTERY_THRESHOLD,
    PERSONAS,
    LearnerPersona,
    LearnerSimulator,
    MoveKind,
    SimulatorFamily,
)
from src.digital_twin.student.intervention_policies import (
    ConceptView,
    EligibilityConfig,
    EligibilityGate,
    InterventionDecision,
    PolicyInputs,
    SentMessage,
    TimingPolicy,
    TimingPolicyId,
    build_policy,
)
from src.digital_twin.student.learner_estimators import (
    AssessedObservation,
    EstimatorState,
    LearnerEstimator,
    build_estimator,
    log_loss,
)

ORIGIN = datetime(2026, 9, 7, 0, 0, tzinfo=UTC)
DECISION_HOUR_UTC = 10
DAYS = 30
DEVELOPMENT_SEEDS = tuple(range(1000, 1006))
HELD_OUT_SEEDS = tuple(range(2000, 2020))
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 20260902

ESTIMATOR_GRID: dict[str, list[dict[str, float]]] = {
    "count": [{}],
    "bkt": [
        {"p_init": p_init, "p_learn": p_learn, "p_forget_per_day": p_forget}
        for p_init in (0.3, 0.5)
        for p_learn in (0.1, 0.2, 0.3)
        for p_forget in (0.0, 0.02, 0.05)
    ],
    "pfa": [
        {"beta": beta, "gamma": gamma, "rho": rho, "decay_per_day": decay}
        for beta in (-1.2, -0.85, -0.4)
        for gamma in (0.5, 0.9, 1.3)
        for rho in (0.3, 0.5, 0.8)
        for decay in (0.0, 0.03, 0.08)
    ],
}

CONDITIONS: tuple[tuple[str, str], ...] = tuple(
    itertools.product(("count", "bkt", "pfa"), ("constant", "conditional", "value"))
) + (("count", "oracle"), ("count", "never"))


@dataclass
class LearnerRunResult:
    family: str
    persona: str
    seed: int
    estimator: str
    policy: str
    condition: str
    mse_vs_hidden: float
    brier_next_outcome: float | None
    log_loss_next_outcome: float | None
    ece_next_outcome: float | None
    auroc_next_outcome: float | None
    messages_sent: int
    wasted_interventions: int
    wasted_rate: float | None
    prompted_attempts: int
    follow_up_fraction: float | None
    eligibility_violations: int
    no_action_days: int
    final_hidden_mastery: float
    concepts_mastered_final: int
    reason_codes: dict[str, int] = field(default_factory=dict)


@dataclass
class _EngineState:
    estimator_state: EstimatorState
    history: list[SentMessage] = field(default_factory=list)
    last_observation: dict[str, datetime] = field(default_factory=dict)
    incorrect_streak: dict[str, int] = field(default_factory=dict)


def _instant(day: int) -> datetime:
    return ORIGIN + timedelta(days=day, hours=DECISION_HOUR_UTC)


def _views(estimator: LearnerEstimator, engine: _EngineState, now: datetime) -> tuple[ConceptView, ...]:
    views = []
    for concept_id in DEFAULT_CONCEPTS:
        last = engine.last_observation.get(concept_id)
        days = None if last is None else (now - last).total_seconds() / 86400.0
        views.append(
            ConceptView(
                concept_id=concept_id,
                estimate=estimator.estimate(engine.estimator_state, concept_id, now),
                days_since_last_observation=days,
                recent_incorrect_streak=engine.incorrect_streak.get(concept_id, 0),
            )
        )
    return tuple(views)


def _observe(estimator: LearnerEstimator, engine: _EngineState, concept_id: str, correct: bool, at: datetime) -> None:
    engine.estimator_state = estimator.update(
        engine.estimator_state, AssessedObservation(concept_id=concept_id, correct=correct, observed_at=at)
    )
    engine.last_observation[concept_id] = at
    engine.incorrect_streak[concept_id] = 0 if correct else engine.incorrect_streak.get(concept_id, 0) + 1


def _independent_violation(now: datetime, concept_id: str, history: list[SentMessage], config: EligibilityConfig) -> bool:
    """Harness-side re-check from timestamps only, independent of the policy's gate."""

    recent = [m for m in history if now - timedelta(days=7) < m.sent_at <= now]
    if len(recent) >= config.max_messages_per_7_days:
        return True
    if any(m.concept_id == concept_id and now - m.sent_at < timedelta(hours=config.same_concept_cooldown_hours) for m in history):
        return True
    local_hour = (now + timedelta(hours=config.timezone_offset_hours)).hour
    return local_hour >= config.quiet_hours_start_local or local_hour < config.quiet_hours_end_local


def run_learner(
    *,
    persona: LearnerPersona,
    family: SimulatorFamily,
    seed: int,
    estimator: LearnerEstimator,
    policy: TimingPolicy,
    estimator_id: str,
    days: int = DAYS,
    eligibility: EligibilityConfig | None = None,
) -> LearnerRunResult:
    config = eligibility or EligibilityConfig()
    simulator = LearnerSimulator(persona=persona, family=family, seed=seed)
    engine = _EngineState(estimator_state=estimator.initial_state())
    squared_errors: list[float] = []
    predictions: list[tuple[float, bool]] = []
    messages = wasted = prompted = violations = no_action = 0
    reasons: dict[str, int] = {}

    for day in range(1, days + 1):
        simulator.advance_one_day()
        now = _instant(day)
        views = _views(estimator, engine, now)
        inputs = PolicyInputs(
            now=now,
            concepts=views,
            history=tuple(engine.history),
            prerequisite_order=DEFAULT_CONCEPTS,
            hidden_need=(lambda cid, d=day: simulator.needs_intervention(cid, d))
            if policy.policy_id is TimingPolicyId.ORACLE
            else None,
        )
        decision: InterventionDecision = policy.decide(inputs)
        reasons[decision.reason_code] = reasons.get(decision.reason_code, 0) + 1
        if decision.sends:
            assert decision.concept_id is not None and decision.move is not None
            if _independent_violation(now, decision.concept_id, engine.history, config):
                violations += 1
            messages += 1
            hidden = simulator.hidden_mastery(decision.concept_id)
            if hidden >= MASTERY_THRESHOLD or not simulator.is_receptive(day):
                wasted += 1
            engine.history.append(
                SentMessage(sent_at=now, concept_id=decision.concept_id, move=decision.move, reason_code=decision.reason_code)
            )
            estimate_before = estimator.estimate(engine.estimator_state, decision.concept_id, now).probability
            attempt = simulator.receive_intervention(decision.concept_id, MoveKind(decision.move))
            if attempt is not None:
                prompted += 1
                predictions.append((estimate_before, attempt.correct))
                _observe(estimator, engine, attempt.concept_id, attempt.correct, now + timedelta(minutes=30))
        else:
            no_action += 1

        activity = simulator.self_directed_activity()
        if activity is not None:
            at = now + timedelta(hours=4)
            estimate_before = estimator.estimate(engine.estimator_state, activity.concept_id, at).probability
            predictions.append((estimate_before, activity.correct))
            _observe(estimator, engine, activity.concept_id, activity.correct, at)

        end_of_day = now + timedelta(hours=8)
        for concept_id in DEFAULT_CONCEPTS:
            estimate = estimator.estimate(engine.estimator_state, concept_id, end_of_day).probability
            squared_errors.append((estimate - simulator.hidden_mastery(concept_id)) ** 2)

    final_masteries = [simulator.hidden_mastery(c) for c in DEFAULT_CONCEPTS]
    return LearnerRunResult(
        family=str(family),
        persona=persona.name,
        seed=seed,
        estimator=estimator_id,
        policy=str(policy.policy_id),
        condition=f"{estimator_id}+{policy.policy_id}",
        mse_vs_hidden=statistics.fmean(squared_errors),
        brier_next_outcome=_brier(predictions),
        log_loss_next_outcome=_mean_log_loss(predictions),
        ece_next_outcome=_ece(predictions),
        auroc_next_outcome=_auroc(predictions),
        messages_sent=messages,
        wasted_interventions=wasted,
        wasted_rate=(wasted / messages) if messages else None,
        prompted_attempts=prompted,
        follow_up_fraction=(prompted / messages) if messages else None,
        eligibility_violations=violations,
        no_action_days=no_action,
        final_hidden_mastery=statistics.fmean(final_masteries),
        concepts_mastered_final=sum(1 for m in final_masteries if m >= MASTERY_THRESHOLD),
        reason_codes=reasons,
    )


# ------------------------------------------------------------------ metrics
def _brier(predictions: list[tuple[float, bool]]) -> float | None:
    if not predictions:
        return None
    return statistics.fmean((p - float(y)) ** 2 for p, y in predictions)


def _mean_log_loss(predictions: list[tuple[float, bool]]) -> float | None:
    if not predictions:
        return None
    return statistics.fmean(log_loss(p, y) for p, y in predictions)


def _ece(predictions: list[tuple[float, bool]], bins: int = 10) -> float | None:
    if not predictions:
        return None
    total = len(predictions)
    ece = 0.0
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        members = [(p, y) for p, y in predictions if low <= p < high or (index == bins - 1 and p == 1.0)]
        if not members:
            continue
        confidence = statistics.fmean(p for p, _ in members)
        accuracy = statistics.fmean(float(y) for _, y in members)
        ece += len(members) / total * abs(confidence - accuracy)
    return ece


def _auroc(predictions: list[tuple[float, bool]]) -> float | None:
    positives = [p for p, y in predictions if y]
    negatives = [p for p, y in predictions if not y]
    if not positives or not negatives:
        return None
    wins = 0.0
    for p in positives:
        for n in negatives:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(positives) * len(negatives))


# --------------------------------------------------------------- fitting
def fit_estimator_parameters(
    estimator_id: str,
    *,
    seeds: Iterable[int] = DEVELOPMENT_SEEDS,
    families: Iterable[SimulatorFamily] = tuple(SimulatorFamily),
    personas: Iterable[LearnerPersona] = PERSONAS,
    days: int = DAYS,
) -> tuple[dict[str, float], float]:
    """Choose grid parameters by observable next-outcome log loss on development seeds.

    Fitting uses only observable outcomes pooled across both families, never
    hidden mastery, and never the held-out seeds.
    """

    seeds = tuple(seeds)
    families = tuple(families)
    personas = tuple(personas)
    best: tuple[float, dict[str, float]] | None = None
    for parameters in ESTIMATOR_GRID[estimator_id]:
        estimator = build_estimator(estimator_id, **parameters)
        losses: list[float] = []
        for family, persona, seed in itertools.product(families, personas, seeds):
            result = run_learner(
                persona=persona,
                family=family,
                seed=seed,
                estimator=estimator,
                policy=build_policy("never"),
                estimator_id=estimator_id,
                days=days,
            )
            if result.log_loss_next_outcome is not None:
                losses.append(result.log_loss_next_outcome)
        score = statistics.fmean(losses) if losses else float("inf")
        if best is None or score < best[0]:
            best = (score, dict(parameters))
    assert best is not None
    return best[1], best[0]


# --------------------------------------------------------------- program
@dataclass
class ProgramConfig:
    seeds: tuple[int, ...] = HELD_OUT_SEEDS
    development_seeds: tuple[int, ...] = DEVELOPMENT_SEEDS
    families: tuple[SimulatorFamily, ...] = tuple(SimulatorFamily)
    personas: tuple[LearnerPersona, ...] = PERSONAS
    days: int = DAYS
    conditions: tuple[tuple[str, str], ...] = CONDITIONS
    fit_parameters: bool = True
    bootstrap_resamples: int = BOOTSTRAP_RESAMPLES


def run_program(config: ProgramConfig) -> dict[str, Any]:
    fitted: dict[str, dict[str, float]] = {}
    fit_scores: dict[str, float] = {}
    for estimator_id in ("count", "bkt", "pfa"):
        if config.fit_parameters:
            fitted[estimator_id], fit_scores[estimator_id] = fit_estimator_parameters(
                estimator_id,
                seeds=config.development_seeds,
                families=config.families,
                personas=config.personas,
                days=config.days,
            )
        else:
            fitted[estimator_id], fit_scores[estimator_id] = {}, float("nan")

    results: list[LearnerRunResult] = []
    for estimator_id, policy_id in config.conditions:
        estimator = build_estimator(estimator_id, **fitted[estimator_id])
        policy = build_policy(policy_id)
        for family, persona, seed in itertools.product(config.families, config.personas, config.seeds):
            results.append(
                run_learner(
                    persona=persona,
                    family=family,
                    seed=seed,
                    estimator=estimator,
                    policy=policy,
                    estimator_id=estimator_id,
                    days=config.days,
                )
            )

    summary = summarize(results, resamples=config.bootstrap_resamples)
    summary["fitted_parameters"] = fitted
    summary["development_fit_log_loss"] = fit_scores
    summary["config"] = {
        "seeds": list(config.seeds),
        "development_seeds": list(config.development_seeds),
        "families": [str(f) for f in config.families],
        "personas": [p.name for p in config.personas],
        "days": config.days,
        "conditions": [f"{e}+{p}" for e, p in config.conditions],
        "bootstrap_resamples": config.bootstrap_resamples,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }
    return {"summary": summary, "results": [asdict(r) for r in results]}


METRICS: tuple[str, ...] = (
    "mse_vs_hidden",
    "brier_next_outcome",
    "ece_next_outcome",
    "auroc_next_outcome",
    "wasted_rate",
    "follow_up_fraction",
    "messages_sent",
    "final_hidden_mastery",
    "concepts_mastered_final",
    "eligibility_violations",
)

PRIMARY_CONTRASTS: tuple[tuple[str, str], ...] = (
    ("bkt+constant", "count+constant"),
    ("pfa+constant", "count+constant"),
    ("count+conditional", "count+constant"),
    ("count+value", "count+constant"),
    ("bkt+conditional", "count+constant"),
    ("bkt+value", "count+constant"),
    ("bkt+value", "bkt+conditional"),
    ("pfa+value", "pfa+conditional"),
    ("pfa+value", "count+constant"),
)


def _mean(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return statistics.fmean(present) if present else None


def summarize(results: list[LearnerRunResult], *, resamples: int = BOOTSTRAP_RESAMPLES) -> dict[str, Any]:
    by_condition: dict[str, list[LearnerRunResult]] = {}
    for result in results:
        by_condition.setdefault(result.condition, []).append(result)

    aggregate: dict[str, dict[str, Any]] = {}
    for condition, items in sorted(by_condition.items()):
        row: dict[str, Any] = {"n_learners": len(items)}
        for metric in METRICS:
            row[metric] = _mean([getattr(r, metric) for r in items])
        for family in sorted({r.family for r in items}):
            family_items = [r for r in items if r.family == family]
            row[f"mse_vs_hidden[{family}]"] = _mean([r.mse_vs_hidden for r in family_items])
            row[f"wasted_rate[{family}]"] = _mean([r.wasted_rate for r in family_items])
        row["reason_codes"] = _merge_counts([r.reason_codes for r in items])
        aggregate[condition] = row

    contrasts: dict[str, dict[str, Any]] = {}
    for candidate, control in PRIMARY_CONTRASTS:
        if candidate not in by_condition or control not in by_condition:
            continue
        contrasts[f"{candidate} vs {control}"] = {
            metric: paired_bootstrap(by_condition[candidate], by_condition[control], metric, resamples=resamples)
            for metric in ("mse_vs_hidden", "brier_next_outcome", "wasted_rate", "follow_up_fraction", "final_hidden_mastery", "messages_sent")
        }
    return {"aggregate": aggregate, "paired_contrasts": contrasts}


def _merge_counts(rows: list[dict[str, int]]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for row in rows:
        for key, value in row.items():
            merged[key] = merged.get(key, 0) + value
    return dict(sorted(merged.items()))


def paired_bootstrap(
    candidate: list[LearnerRunResult],
    control: list[LearnerRunResult],
    metric: str,
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Paired difference (candidate minus control) by learner with a percentile interval."""

    key = lambda r: (r.family, r.persona, r.seed)  # noqa: E731
    control_by_key = {key(r): r for r in control}
    pairs: list[float] = []
    for item in candidate:
        other = control_by_key.get(key(item))
        if other is None:
            continue
        a, b = getattr(item, metric), getattr(other, metric)
        if a is None or b is None:
            continue
        pairs.append(float(a) - float(b))
    if not pairs:
        return {"n_pairs": 0, "mean_difference": None, "ci95": None}
    rng = random.Random(f"{seed}:{metric}:{candidate[0].condition}:{control[0].condition}")
    means = []
    for _ in range(resamples):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        means.append(statistics.fmean(sample))
    means.sort()
    low = means[int(0.025 * (resamples - 1))]
    high = means[int(0.975 * (resamples - 1))]
    return {
        "n_pairs": len(pairs),
        "mean_difference": statistics.fmean(pairs),
        "ci95": [low, high],
        "lower_bound_excludes_zero": (low > 0) or (high < 0),
    }


def write_outputs(program: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(program["summary"], indent=2, sort_keys=True))
    with (output_dir / "per_learner.jsonl").open("w") as handle:
        for row in program["results"]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    (output_dir / "summary.md").write_text(render_markdown(program["summary"]))


def render_markdown(summary: dict[str, Any]) -> str:
    lines = ["| Condition | n | MSE vs hidden | Brier next | ECE | AUROC | Msgs | Wasted rate | Follow-up | Final mastery | Violations |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for condition, row in summary["aggregate"].items():
        lines.append(
            "| {c} | {n} | {mse} | {brier} | {ece} | {auroc} | {msgs} | {wasted} | {follow} | {mastery} | {viol} |".format(
                c=condition,
                n=row["n_learners"],
                mse=_fmt(row["mse_vs_hidden"]),
                brier=_fmt(row["brier_next_outcome"]),
                ece=_fmt(row["ece_next_outcome"]),
                auroc=_fmt(row["auroc_next_outcome"]),
                msgs=_fmt(row["messages_sent"], 1),
                wasted=_fmt(row["wasted_rate"]),
                follow=_fmt(row["follow_up_fraction"]),
                mastery=_fmt(row["final_hidden_mastery"]),
                viol=_fmt(row["eligibility_violations"], 2),
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


def _fmt(value: float | None, digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"
