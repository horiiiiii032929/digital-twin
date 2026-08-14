from scripts.analyze_generator_qualification_v2 import corrected_record
from scripts.run_generator_qualification import _actual_action


def test_action_classifier_recognizes_targeted_meaning_question_only_in_ambiguity():
    answer = "There are two meanings. Which meaning are you asking about?"

    assert _actual_action("answer", answer, scenario_type="ambiguity") == "clarify"
    assert _actual_action("answer", answer, scenario_type="direct") == "answer"
    assert (
        _actual_action(
            "answer",
            "Bridge means a link or a review state.",
            scenario_type="ambiguity",
        )
        == "answer"
    )


def test_corrected_record_preserves_other_hard_checks():
    result = {
        "case_id": "case-1",
        "scenario_type": "ambiguity",
        "expected_action": "clarify",
        "actual_action": "answer",
        "answer": "Which meaning do you mean?",
        "completed": True,
        "required_terms_passed": True,
        "forbidden_terms_absent": True,
        "citation_source_identity_passed": False,
        "provider_identity_passed": True,
        "deterministic_checks_passed": False,
    }

    corrected = corrected_record(result)

    assert corrected["corrected_action"] == "clarify"
    assert corrected["corrected_pass"] is False
