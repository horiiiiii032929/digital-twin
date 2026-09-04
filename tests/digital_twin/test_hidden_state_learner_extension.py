"""Tests for the hidden-state learner extension of the autonomy evaluation."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest

from scripts.governed_full_autonomy_v2_1_hidden_state_runtime import (
    HIDDEN_STATE_CONCEPT_CARDS,
)
from scripts.run_governed_full_autonomy_v2_1_hidden_state_learner_014 import (
    CONTRASTS,
    run_case,
)
from src.digital_twin.evaluation.autonomy_learning_scoring import (
    summarize_hidden_state_scores,
)
from src.digital_twin.evaluation.learner_simulator import PERSONAS, SimulatorFamily
from src.digital_twin.evaluation.simulated_learner_v1 import TextRealisingLearnerV1
from src.digital_twin.student.autonomy_models import (
    AssessmentOutcome,
    CanonicalSourceRangeV1,
    CourseConceptV1,
    CourseDomainModelV1,
    CourseObjectiveV1,
)
from src.digital_twin.student.tutoring_graph import (
    DeterministicTurnInterpreter,
    _assess_attempt,
    _assessment_concepts,
    _attribute_concepts,
)


def _domain_model() -> CourseDomainModelV1:
    concepts = []
    objectives = []
    for card in HIDDEN_STATE_CONCEPT_CARDS:
        sha = hashlib.sha256(card.description.encode()).hexdigest()
        concepts.append(
            CourseConceptV1(
                concept_id=card.concept_id,
                label=card.label,
                description=card.description,
                canonical_ranges=[
                    CanonicalSourceRangeV1(
                        source_artifact_id=f"source-{card.concept_id}",
                        source_version=1,
                        source_sha256=sha,
                        locator="paragraph 1",
                        char_start=0,
                        char_end=len(card.description),
                    )
                ],
            )
        )
        objectives.append(
            CourseObjectiveV1(
                objective_id=f"objective-{card.concept_id}",
                statement=card.objective,
                concept_ids=[card.concept_id],
            )
        )
    return CourseDomainModelV1(
        domain_model_id="domain-test",
        course_id="course",
        release_id="release",
        release_sha256="0" * 64,
        version=1,
        objectives=objectives,
        concepts=concepts,
        approved_by="professor",
    )


def test_learner_text_has_the_intended_lexical_properties() -> None:
    """Correct attempts grade correct on their concept; incorrect grade incorrect on the same concept."""

    domain = _domain_model()
    learner = TextRealisingLearnerV1(
        persona=PERSONAS[0], family=SimulatorFamily.BKT_LIKE, seed=1, cards=HIDDEN_STATE_CONCEPT_CARDS
    )
    interpreter = DeterministicTurnInterpreter()
    seen_correct = seen_incorrect = False
    for _ in range(60):
        learner.advance_one_day()
        utterance = learner.self_directed_utterance()
        if utterance is None:
            continue
        signals = interpreter.interpret(utterance.text)
        assert signals.attempt_present
        concept_ids = _attribute_concepts(utterance.text, domain)
        assert concept_ids[0] == utterance.concept_id
        assessment_concept_ids = _assessment_concepts(utterance.text, domain)
        assert assessment_concept_ids == [utterance.concept_id]
        outcome, _ = _assess_attempt(utterance.text, assessment_concept_ids, domain)
        if utterance.hidden_correct:
            assert outcome is AssessmentOutcome.CORRECT
            seen_correct = True
        else:
            assert outcome is AssessmentOutcome.INCORRECT
            seen_incorrect = True
    assert seen_correct and seen_incorrect
    misconception = learner.misconception_statement(HIDDEN_STATE_CONCEPT_CARDS[1].concept_id)
    assert interpreter.interpret(misconception.text).misconception_observed
    assert _attribute_concepts(misconception.text, domain)[0] == HIDDEN_STATE_CONCEPT_CARDS[1].concept_id


def test_runtime_assessment_scope_does_not_dilute_a_correct_multi_concept_turn() -> None:
    domain = _domain_model()
    message = (
        "My attempt on lease ordering: Lease ordering grants each replica a bounded "
        "lease token so updates apply in lease sequence, expired leases are renewed "
        "before commit, and stale holders are fenced by the sequence number."
    )

    attributed = _attribute_concepts(message, domain)
    assessed = _assessment_concepts(message, domain)

    assert len(attributed) > 1
    assert assessed == ["concept-lease-ordering"]
    assert _assess_attempt(message, assessed, domain)[0] is AssessmentOutcome.CORRECT


@pytest.mark.parametrize("condition", ["t0-grounded-control", "t1-v2-autonomous"])
def test_closed_loop_driver_runs_the_real_product(tmp_path: Path, condition: str) -> None:
    result, score = asyncio.run(
        run_case(
            root=tmp_path,
            condition=condition,
            persona=PERSONAS[0],
            family=SimulatorFamily.LOGISTIC_LIKE,
            seed=2000,
            days=8,
        )
    )
    assert result.response.operational_status == "completed"
    assert result.response.provider_calls == 0
    assert score.attempt_turns >= 1
    assert score.quiet_hour_violations == 0
    assert score.frequency_violations == 0
    assert score.cooldown_violations == 0
    assert score.restart_count == 0  # restart day is 15, beyond an 8-day run
    assert len(result.truth.days) == 8
    if condition == "t1-v2-autonomous":
        assert result.learner_evidence.observations, "v2 planes should record observations"
        assert score.attribution_accuracy is not None
    else:
        assert score.mse_vs_hidden is not None


def test_summary_reports_conditions_and_paired_contrasts(tmp_path: Path) -> None:
    scores = []
    for condition in ("t0-grounded-control", "t1-v2-autonomous"):
        _result, score = asyncio.run(
            run_case(
                root=tmp_path,
                condition=condition,
                persona=PERSONAS[1],
                family=SimulatorFamily.BKT_LIKE,
                seed=2001,
                days=4,
            )
        )
        scores.append(score)
    summary = summarize_hidden_state_scores(scores, contrasts=CONTRASTS, resamples=10)
    assert set(summary["aggregate"]) == {"t0-grounded-control", "t1-v2-autonomous"}
    contrast = summary["paired_contrasts"]["t1-v2-autonomous vs t0-grounded-control"]
    assert contrast["mse_vs_hidden"]["n_pairs"] == 1
