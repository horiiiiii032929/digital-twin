from scripts.judge_generator_qualification_v3 import conservative_cost, review_prompt
from scripts.review_generator_qualification_v2 import CHECK_FIELDS, STRESS_PROBES


def test_deepseek_review_prompt_names_citation_completeness_rule():
    payload = STRESS_PROBES[3]["payload"]

    prompt = review_prompt(payload)

    assert "citation_required is true" in prompt
    assert "lacks a cited source" in prompt
    assert all(field in prompt for field in CHECK_FIELDS)
    assert "deepseek" not in prompt.casefold()
    assert "deterministic" not in prompt.casefold()


def test_deepseek_review_cost_is_conservative_cache_miss_price():
    assert conservative_cost(1_000_000, 1_000_000) == 1.305
