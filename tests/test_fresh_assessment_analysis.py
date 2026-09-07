import pytest

from scripts.analyze_fresh_assessment_comparison import paired_statistics, reviewed_cases


def fixture_packet():
    return {"contexts": [{"id": f"{family}-{pair}-{adequate}",
                          "pair_id": f"{family}-{pair}", "family": family,
                          "gold": {"draft_adequate": adequate}}
                         for family in ("support", "pedagogy") for pair in range(2)
                         for adequate in (True, False)]}


def fixture_review(packet, useful):
    return {"cases": [{"id": row["id"], "useful": useful, "critical": False,
                       "uncertain": False, "reason": "Explicit synthetic test judgment"}
                      for row in packet["contexts"]]}


def test_paired_bootstrap_keeps_scenario_and_family_boundaries():
    packet = fixture_packet()
    baseline = reviewed_cases(packet, fixture_review(packet, False))
    candidate = reviewed_cases(packet, fixture_review(packet, True))
    result = paired_statistics(packet, baseline, candidate, repeats=100)
    assert result["scenario_pairs"] == 4
    assert result["family_pair_counts"] == {"pedagogy": 2, "support": 2}
    assert result["useful_difference_percentage_points"] == 100
    assert result["exploratory_95_percentile_interval"] == [100, 100]
    assert len(result["improved_ids"]) == 8
    assert result["regressed_ids"] == []
    # Opposite effects on the two drafts of each scenario cancel in every
    # cluster draw; sampling individual drafts would invent uncertainty here.
    for row in packet["contexts"]:
        baseline[row["id"]]["useful"] = row["gold"]["draft_adequate"]
        candidate[row["id"]]["useful"] = not row["gold"]["draft_adequate"]
    assert paired_statistics(packet, baseline, candidate, repeats=100)["exploratory_95_percentile_interval"] == [0, 0]


def test_review_cannot_drop_uncertainty_or_duplicate_favorable_case():
    packet = fixture_packet()
    review = fixture_review(packet, True)
    review["cases"][0]["uncertain"] = True
    with pytest.raises(ValueError, match="cannot qualify"):
        reviewed_cases(packet, review)
    review = fixture_review(packet, True)
    review["cases"][-1] = review["cases"][0]
    with pytest.raises(ValueError, match="exactly once"):
        reviewed_cases(packet, review)
    complete = reviewed_cases(packet, fixture_review(packet, True))
    with pytest.raises(ValueError, match="adequate and flawed"):
        paired_statistics({"contexts": packet["contexts"][:-1]}, complete, complete, repeats=10)
