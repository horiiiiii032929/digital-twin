import math

from scripts.analyze_it5002_rapid_result import (
    _find_forbidden_keys,
    _mcnemar_exact,
    _wilson,
)


def test_mcnemar_exact_reports_symmetric_two_sided_probability() -> None:
    assert math.isclose(_mcnemar_exact(7, 0), 0.015625)
    assert _mcnemar_exact(0, 7) == _mcnemar_exact(7, 0)
    assert _mcnemar_exact(0, 0) == 1.0


def test_wilson_interval_contains_observed_ratio() -> None:
    interval = _wilson(19, 20)

    assert interval is not None
    assert interval[0] < 19 / 20 < interval[1]
    assert _wilson(0, 0) is None


def test_private_content_key_scan_reports_nested_paths() -> None:
    value = {"cases": [{"case_id": "case-001", "hits": [{"text": "private"}]}]}

    assert _find_forbidden_keys(value) == ["$.cases[0].hits[0].text"]
