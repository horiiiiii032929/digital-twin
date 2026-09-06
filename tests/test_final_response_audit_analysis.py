"""Independent analysis checks; no fabricated metrics are evaluation evidence."""

import pytest

from scripts import analyze_final_response_audit as a


def judgment(useful=False, critical=False, uncertain=False):
    return dict(
        useful=useful, critical=critical, uncertain=uncertain, reason="test judgment"
    )


def row(i, pair, family, before, after):
    return {
        "id": str(i),
        "pair_id": pair,
        "family": family,
        "C0": judgment(before),
        "C1": judgment(after),
        "C2": judgment(after),
    }


def test_whole_pair_resampling_preserves_anticorrelated_differences():
    rows = [
        row(0, "p1", "f", False, True),
        row(1, "p1", "f", True, False),
        row(2, "p2", "f", False, True),
        row(3, "p2", "f", True, False),
    ]
    result = a.bootstrap(rows, repeats=1000)
    assert result["difference"] == 0 and result["ci95"] == [0, 0]
    assert result == a.bootstrap(rows, repeats=1000)


def test_stratification_does_not_mix_families():
    rows = [
        row(0, "p1", "up", False, True),
        row(1, "p1", "up", False, True),
        row(2, "p2", "down", True, False),
        row(3, "p2", "down", True, False),
    ]
    assert a.bootstrap(rows, repeats=100)["ci95"] == [0, 0]


def test_exposed_pairs_may_both_be_useful():
    rows = [row(0, "p", "f", True, True), row(1, "p", "f", True, True)]
    assert a.bootstrap(rows, repeats=20)["difference"] == 0


@pytest.mark.parametrize(
    "bad",
    [
        judgment(True, True),
        judgment(True, False, True),
        {"useful": 1, "critical": False, "uncertain": False, "reason": "x"},
    ],
)
def test_invalid_useful_labels_rejected(bad):
    with pytest.raises(ValueError):
        a.validate_judgment(bad)


def test_uncertainty_stays_in_useful_denominator():
    rows = [row(0, "p", "f", True, True), row(1, "p", "f", True, False)]
    rows[1]["C2"] = judgment(uncertain=True)
    result = a.aggregate(rows, "C2")
    assert result == {
        "n": 2,
        "useful": 1,
        "critical": 0,
        "uncertain": 1,
        "useful_rate": 0.5,
    }


def test_unknown_support_not_silently_negative_and_operational_not_truepositive():
    rows = [{"id": str(i)} for i in range(5)]
    raw = {
        str(i): {"C1": {"reason": reason}}
        for i, reason in enumerate(
            [
                "audit_rejected",
                "audit_rejected",
                "audit_pass",
                "contract_or_provider_failure",
                "audit_rejected",
            ]
        )
    }
    labels = {
        str(i): {"factual_support_defect": lab}
        for i, lab in enumerate([True, None, None, True, False])
    }
    r = a.support_detection(rows, raw, labels)
    assert r["unknown_labels"] == 2 and r["operational_nondecisions"] == 1
    assert (
        r["precision_known_decisions"] == 0.5 and r["recall_known_all_defects"] == 0.5
    )
    assert r["conservative_precision_unknown_positives_as_clean"] == pytest.approx(
        1 / 3
    )
    assert r[
        "conservative_recall_unknown_negative_or_operational_as_defects"
    ] == pytest.approx(1 / 3)


def test_missing_or_duplicate_cases_rejected():
    for rows in [[{"id": "a"}], [{"id": "a"}, {"id": "a"}]]:
        with pytest.raises(ValueError):
            a.index(rows, ["a", "b"], "test")


def test_malformed_audit_observations_retained_as_no_parseable_units():
    for content in ["oops", "null", "[]", '{"entries":null}']:
        assert a.audit_entries(content) == []


def test_reached_union_and_semantic_denominators_exclude_different_failures():
    rows = [row(i, f"p{i // 2}", "family", True, i == 0) for i in range(4)]
    raw = {
        "0": {"C1": {"reason": "audit_pass"}, "C2": {"reason": "audit_pass"}},
        "1": {
            "C1": {"reason": "audit_rejected"},
            "C2": {"reason": "contract_or_provider_failure"},
        },
        "2": {
            "C1": {"reason": "audit_pass"},
            "C2": {"reason": "provider-or-request-failure"},
        },
        "3": {
            "C1": {"reason": "provider-or-request-failure"},
            "C2": {"reason": "provider-or-request-failure"},
        },
    }
    records = {
        "audit": [
            {"case": f"{i}/{arm}/initial_audit/audit"}
            for i, arm in [(0, "C1"), (0, "C2"), (1, "C1"), (1, "C2"), (2, "C1")]
        ],
        "repair": [],
    }
    result = a.execution_slices(rows, raw, records)
    assert result["reached_inputs"] == 3 and result["not_reached_inputs"] == 1
    assert result["metrics_on_reached_union"]["C2"]["n"] == 3
    assert result["arms"]["C1"]["completed_semantic_decisions"] == 3
    assert result["arms"]["C2"]["provider_reached_inputs"] == 2
    assert result["arms"]["C2"]["completed_semantic_decisions"] == 1
    assert result["arms"]["C2"]["useful_baseline_lost_on_reached"] == 2
    assert result["arms"]["C2"]["useful_baseline_lost_on_completed_decisions"] == 0
