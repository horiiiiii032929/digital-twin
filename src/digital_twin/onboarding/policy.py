from src.digital_twin.tutor_policy import (
    FieldStatus,
    KnowledgeSourcePolicy,
    PolicyField,
    ReleaseStatus,
    TutorPolicy,
)


def _build_policy(answers: dict[str, str]) -> TutorPolicy:
    knowledge_policy = KnowledgeSourcePolicy().model_dump(mode="json")
    return TutorPolicy(
        status=ReleaseStatus.DRAFT,
        release_status=ReleaseStatus.BLOCKED,
        safety_compliance=[
            PolicyField(
                id="approved_source_permissions",
                label="Approved source permissions",
                status=FieldStatus.RESOLVED,
                value=answers["source_permissions"],
            ),
            PolicyField(
                id="knowledge_source_policy",
                label="Knowledge source policy",
                status=FieldStatus.BLOCKS_RELEASE,
                value=knowledge_policy,
                safe_default=(
                    "Preview may use any_source_with_labels, but release requires "
                    "an explicit source strictness confirmation."
                ),
            ),
            PolicyField(
                id="disallowed_private_sources",
                label="Disallowed private sources",
                status=FieldStatus.BLOCKS_RELEASE,
                value=[
                    "private student data",
                    "consent records",
                    "raw transcripts",
                    "private forum exports",
                    "unapproved instructor material",
                ],
                safe_default=(
                    "Exclude private student data, consent records, raw transcripts, "
                    "private forum exports, and unapproved instructor material."
                ),
            ),
            PolicyField(
                id="academic_integrity_policy",
                label="Academic integrity policy",
                status=FieldStatus.NEEDS_REVIEW,
                value=answers["academic_integrity"],
                warning="Professor should confirm this before student release.",
            ),
            PolicyField(
                id="sensitive_data_handling",
                label="Sensitive data handling",
                status=FieldStatus.BLOCKS_RELEASE,
                value=(
                    "No student data, consent records, or private transcripts are "
                    "approved in Sprint 1."
                ),
                safe_default="Use synthetic examples only.",
            ),
        ],
        pedagogy=[
            PolicyField(
                id="teaching_approach",
                label="Teaching approach",
                status=FieldStatus.RESOLVED,
                value=answers["teaching_approach"],
            ),
            PolicyField(
                id="misconception_handling",
                label="Misconception handling",
                status=FieldStatus.RESOLVED,
                value=answers["misconception_handling"],
            ),
            PolicyField(
                id="tutoring_moves",
                label="Tutoring moves",
                status=FieldStatus.NEEDS_REVIEW,
                value=["hints", "prompts", "misconception_correction"],
            ),
            PolicyField(
                id="feedback_policy",
                label="Feedback policy",
                status=FieldStatus.NEEDS_REVIEW,
                value="process feedback with concise task-level correction",
            ),
            PolicyField(
                id="proactive_support",
                label="Proactive support",
                status=FieldStatus.NEEDS_REVIEW,
                value="short checks when useful; no unsolicited practice plan",
            ),
            PolicyField(
                id="course_scope_boundary",
                label="Course scope boundary",
                status=FieldStatus.NEEDS_REVIEW,
                value="stay within approved course topics and visibly label external grounding",
            ),
            PolicyField(
                id="preferred_examples",
                label="Preferred examples",
                status=FieldStatus.NEEDS_REVIEW,
                value=["course-provided examples", "small analogous examples"],
            ),
            PolicyField(
                id="approval_criteria",
                label="Professor rejection criteria",
                status=FieldStatus.RESOLVED,
                value=answers["approval_criteria"],
            ),
            PolicyField(
                id="rejection_criteria",
                label="Rejection criteria",
                status=FieldStatus.RESOLVED,
                value=answers["approval_criteria"],
            ),
            PolicyField(
                id="tone_guidance",
                label="Tone guidance",
                status=FieldStatus.NEEDS_REVIEW,
                value="clear, concise, and professor-reviewable",
            ),
        ],
        professor_review=[
            PolicyField(
                id="professor_release_approval",
                label="Professor release approval",
                status=FieldStatus.BLOCKS_RELEASE,
                value="pending",
                safe_default="Tutor remains draft-only until explicitly approved.",
            )
        ],
    )




def find_policy_field(policy: TutorPolicy, field_id: str) -> PolicyField | None:
    return next((field for field in policy.all_fields if field.id == field_id), None)
