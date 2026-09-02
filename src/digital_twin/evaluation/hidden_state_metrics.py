"""Shared calibration and paired-comparison metrics for hidden-state evaluation.

Used by the network-free successor simulation and by the product-facing
simulated-learner driver so that both score with identical code.
"""

from __future__ import annotations

import random
import statistics
from math import log
from typing import Any, Callable, Sequence

Prediction = tuple[float, bool]


def brier_score(predictions: Sequence[Prediction]) -> float | None:
    if not predictions:
        return None
    return statistics.fmean((p - float(y)) ** 2 for p, y in predictions)


def log_loss(probability: float, outcome: bool) -> float:
    clipped = min(max(probability, 1e-6), 1 - 1e-6)
    return -log(clipped) if outcome else -log(1.0 - clipped)


def mean_log_loss(predictions: Sequence[Prediction]) -> float | None:
    if not predictions:
        return None
    return statistics.fmean(log_loss(p, y) for p, y in predictions)


def expected_calibration_error(predictions: Sequence[Prediction], bins: int = 10) -> float | None:
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


def auroc(predictions: Sequence[Prediction]) -> float | None:
    positives = [p for p, y in predictions if y]
    negatives = [p for p, y in predictions if not y]
    if not positives or not negatives:
        return None
    wins = 0.0
    for p in positives:
        for n in negatives:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(positives) * len(negatives))


def paired_bootstrap_difference(
    candidate: Sequence[Any],
    control: Sequence[Any],
    *,
    value: Callable[[Any], float | None],
    key: Callable[[Any], Any],
    resamples: int = 1000,
    seed: str = "paired-bootstrap",
) -> dict[str, Any]:
    """Candidate-minus-control paired difference with a percentile interval."""

    control_by_key = {key(item): item for item in control}
    pairs: list[float] = []
    for item in candidate:
        other = control_by_key.get(key(item))
        if other is None:
            continue
        a, b = value(item), value(other)
        if a is None or b is None:
            continue
        pairs.append(float(a) - float(b))
    if not pairs:
        return {"n_pairs": 0, "mean_difference": None, "ci95": None}
    rng = random.Random(seed)
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
