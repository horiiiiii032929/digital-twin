"""Tests for cross-course pilot uncertainty helpers."""

import random

from scripts.analyze_cross_course_retrieval_pilot import (
    bootstrap_mean_interval,
    exact_two_sided_sign_p_value,
)


def test_exact_sign_test_handles_one_sided_improvements() -> None:
    assert exact_two_sided_sign_p_value(6, 0) == 0.03125
    assert exact_two_sided_sign_p_value(1, 0) == 1.0
    assert exact_two_sided_sign_p_value(0, 0) == 1.0


def test_bootstrap_interval_is_seeded_and_bounded() -> None:
    interval = bootstrap_mean_interval(
        [0.0, 1.0, 1.0, 1.0],
        samples=1000,
        rng=random.Random(5106),
    )

    assert interval == [0.25, 1.0]
