"""Source assessment must abstain on unsupported or ambiguous explanations."""
import pytest

from src.digital_twin.student.autonomy_models import AssessmentOutcome
from src.digital_twin.student.source_assessment import assess_source_bound_attempt
from tests.digital_twin.test_goal_completion_scope import setup_two_goals, ATTEMPT

SUPPORTED = "Cache coherence keeps replicated processor data consistent."


@pytest.fixture
def scoped(tmp_path):
    repository, _, goals = setup_two_goals(tmp_path, source_supported_target=True)
    try:
        yield (repository.get_course_domain_model(goals[0].release_id),
               repository.get_release(goals[0].release_id))
    finally:
        repository.close()


def assess(message, scoped, concepts=None):
    return assess_source_bound_attempt(message, concepts or ["cache-coherence"], *scoped)


def test_supported_literal_statement_carries_source_evidence(scoped):
    result = assess("I think " + SUPPORTED, scoped)
    assert result.outcome == AssessmentOutcome.CORRECT
    assert result.evidence_keys


@pytest.mark.parametrize("message", [
    "Cache coherence never keeps replicated processor data consistent.",
    SUPPORTED + " Therefore every program executes without synchronization.",
    SUPPORTED + " This is not true.",
    SUPPORTED + " Is this right?", "Maybe " + SUPPORTED,
    "Coherence helps cores agree on their cached data.", ATTEMPT,
])
def test_negation_additional_claims_and_paraphrases_abstain(scoped, message):
    result = assess(message, scoped)
    assert result.outcome == AssessmentOutcome.NOT_ASSESSED
    assert not result.evidence_keys


def test_description_cannot_supply_its_own_missing_gold(scoped):
    domain, release = scoped
    domain.concepts[0].description += " Invalidation prevents cached copies from diverging."
    result = assess(ATTEMPT, (domain, release))
    assert result.reason == "assessment-target-not-literally-supported"


@pytest.mark.parametrize("variant", ["foreign-release", "wrong-checksum", "outside-range", "empty-range", "ambiguous", "not-permitted", "superseded"])
def test_only_exact_approved_text_range_can_support_assessment(scoped, variant):
    domain, release = scoped
    concepts = ["cache-coherence"]
    if variant == "foreign-release":
        release = release.model_copy(update={"id": "other"})
    elif variant == "wrong-checksum":
        domain.concepts[0].canonical_ranges[0].source_sha256 = "f" * 64
    elif variant == "outside-range":
        domain.concepts[0].canonical_ranges[0].char_start = 10
    elif variant == "empty-range":
        domain.concepts[0].canonical_ranges[0].char_end = 10000
    elif variant == "not-permitted":
        release.chunks[0].retrieval_allowed = False
    elif variant == "superseded":
        release.chunks.append(release.chunks[0].model_copy(update={"id": "newer", "source_version": 2}))
    else:
        concepts.append("virtual-memory")
    result = assess(SUPPORTED, (domain, release), concepts)
    assert result.outcome == AssessmentOutcome.NOT_ASSESSED
