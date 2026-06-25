# Chat-led tutor policy extraction

Date: 2026-06-24
Issue: #2 `[S1 06/28] Chat-led tutor policy extraction`

## Purpose

This artifact defines the reusable tutor-policy schema that the AI-led
onboarding chat should extract from a professor conversation.

It does not define one real professor's final policy. The professor's actual
course, source permissions, grading boundaries, and teaching preferences should
be collected later through the onboarding chat. This document defines what the
chat must learn, how unresolved answers are represented, and which missing
answers block release.

## Why This Exists

The product direction is chat first. The professor should not begin by filling a
static settings form. Instead, the AI interviews the professor with concrete
teaching scenarios, converts the conversation into a draft tutor policy, and
asks follow-up questions when answers are vague or unsafe.

The policy schema is still necessary because the system needs a stable contract
between:

- the onboarding chat
- the generated pedagogical profile
- the response preview behavior
- the minimal prototype
- later evaluation against a generic tutor baseline

Implementation-facing terminology should prefer "pedagogical profile" or
"tutor policy" over vague "teaching style." See
[pedagogical-profile-foundations.md](../01_literature/pedagogical-profile-foundations.md)
for the research basis.

## Sprint 1 Scope

### In Scope

- Define fields the chat should extract.
- Distinguish safety/compliance blockers from reviewable pedagogy fields.
- Define safe defaults for unresolved blocker fields.
- Define follow-up behavior for vague or non-operational professor answers.
- Support a course-level policy for Sprint 1.

### Out of Scope

- Production database schema.
- Full adaptive interview engine.
- Full RAG implementation.
- Internet search implementation.
- Per-assignment or per-topic policy rules.
- Student-facing tutoring implementation.

## Policy Draft Status

The onboarding chat may produce a draft policy before every field is complete.
Each field should carry one of three statuses:

| Status | Meaning | Release impact |
| --- | --- | --- |
| `resolved` | The professor gave a usable answer. | Does not block release. |
| `needs_review` | A usable default or partial answer exists, but the professor should confirm or refine it. | Shows a warning; does not block release by itself. |
| `blocks_release` | The missing or unsafe answer affects release-critical source behavior, permissions, privacy, or final approval. | Tutor cannot be approved for student use. |

This keeps the chat productive without pretending the AI knows missing
professor intent.

## Release Blockers And Warnings

Only release-critical source, safety, privacy, and approval fields block approval
in Sprint 1. Academic-integrity behavior is still important, but unresolved
integrity policy uses a strict safe default and shows a warning rather than
blocking release.

| Field | What the chat must learn | Safe default while unresolved | Blocks release |
| --- | --- | --- | --- |
| `approved_source_permissions` | Which course materials the tutor may use. | No uploaded, private, transcript, or course-owned material may be used until approved. | Yes |
| `disallowed_private_sources` | Which materials must not be used. | Exclude private student data, consent records, raw transcripts, private forum exports, and unapproved instructor material. | Yes |
| `knowledge_source_policy` | Which release source strictness mode the tutor should use. | Preview may demonstrate `any_source_with_labels`, but no release mode is approved until the professor confirms it. | Yes |
| `academic_integrity_policy` | What help is allowed for graded work and assessments. | Strict no-full-answers behavior until the professor configures a different policy. | No; warning until confirmed |
| `sensitive_data_handling` | How student data, transcripts, consent records, and private course artifacts are handled. | Do not ingest or expose sensitive data unless explicit permission and consent are documented. | Yes |
| `professor_release_approval` | Whether the professor explicitly approves the tutor for student-facing use. | Draft only; not released. | Yes |

`course_scope_boundary` is optional for Sprint 1. It should be captured when the
professor provides it, but unresolved course scope should not block approval if
the source and integrity rules are already clear.

## Knowledge Source Policy

The tutor policy should represent source strictness as a professor-confirmed
release choice. `any_source_with_labels` is the recommended release mode, but it
does not become release-approved until the professor confirms it.

```yaml
knowledge_source_policy:
  source_strictness:
    status: blocks_release
    value: unresolved
    recommended_value: any_source_with_labels
    allowed_values:
      - course_only
      - trusted_only
      - any_source_with_labels
  preview_source_mode:
    value: any_source_with_labels
    note: used during preview while release source strictness is unresolved
  source_labels:
    - course-approved
    - professor-approved-external
    - system-suggested-trusted
    - unapproved-external
  trusted_source_allowlist:
    professor_defined: []
    derived_from_course_materials: []
  system_trusted_source_categories:
    - official_documentation
    - standards_or_security_bodies
    - university_pages
  external_sources_require_visible_labels: true
  policy_level: course
```

During preview, live web/search can be used to show the professor what external
source behavior looks like. Released tutor behavior must follow the confirmed
source strictness mode and label sources visibly.

## Reviewable Pedagogy Fields

The following fields shape tutor quality and instructor alignment, but they do
not block release in Sprint 1 if unresolved. They should appear in the generated
policy summary as `resolved` or `needs_review`.

| Field | Expected values or structure | Purpose |
| --- | --- | --- |
| `teaching_approach` | `direct`, `guided`, or `balanced` | Controls whether the tutor explains first, asks guiding questions first, or mixes both. |
| `tutoring_moves` | Allowed set from `hints`, `prompts`, `analogous_examples`, `contrastive_examples`, `misconception_correction`, `partial_structure` | Defines how the tutor may help without over-completing student work. |
| `engagement_target` | `answer`, `self_explanation`, `practice`, or `interaction` | Controls whether the tutor simply answers or asks the student to reason, apply, or practice. |
| `feedback_policy` | `task_feedback`, `process_feedback`, `self_regulation_feedback` | Defines what kind of feedback the tutor should give. |
| `proactive_support` | `none`, `retrieval_practice`, `spaced_review`, `short_checks`, or `targeted_practice` | Defines whether the tutor may suggest practice or follow-up work. |
| `course_scope_boundary` | Free text plus optional included/excluded topics | Defines topic boundaries if the professor wants explicit course scope rules. |
| `preferred_examples` | Free text list | Captures examples, analogies, or applications the professor wants the tutor to reuse. |
| `rejection_criteria` | Free text list | Captures reasons the professor would revise or reject a tutor response. |
| `tone_guidance` | Free text with behavioral examples | Captures communication preferences without treating personality as the core policy. |

## Interview Logic

The onboarding chat should ask scenario-based questions instead of abstract
personality questions. A good question asks the professor to decide what the
tutor should do in a concrete teaching or policy situation.

Core interview areas:

1. Source permissions: "Which materials may the tutor rely on for this course?"
2. External knowledge: "Should the tutor use only approved course materials, or
   should it use trusted external sources or any external source with visible
   labels?"
3. Academic integrity: "If a student asks for the full answer to graded work,
   what should the tutor do?"
4. Sensitive data: "Are transcripts, forum posts, student questions, or consent
   records allowed for this prototype?"
5. Teaching approach: "Should the tutor explain first, ask guiding questions
   first, or balance both?"
6. Misconception handling: "When a student has a wrong idea, should the tutor
   correct directly, ask them to reconsider, or show a contrastive example?"
7. Feedback and practice: "Should the tutor give practice checks or only answer
   direct student questions?"
8. Approval criteria: "What would make you reject a tutor response before
   students see it?"

## Follow-Up Rules

The chat should ask a follow-up when an answer is too vague, contradictory,
unsafe, or not actionable.

Examples of answers that require follow-up:

- "Be helpful."
- "Do not cheat."
- "Use common sense."
- "Teach like me."
- "Use all my materials."
- "Use the internet if needed."
- "Make it friendly."

The follow-up should force an operational choice. For example:

> "Do not cheat" is too vague for a tutor policy. For graded work, should the
> tutor refuse, ask what the student tried first, give hints only, show a
> similar example, or provide partial structure?

## Draft Policy Shape

The generated policy should be readable by a professor and structured enough
for implementation.

```yaml
tutor_policy:
  status: draft
  release_status: blocked
  blockers:
    - approved_source_permissions
    - knowledge_source_policy.source_strictness
  safety_compliance:
    approved_source_permissions:
      status: blocks_release
      value: unresolved
      safe_default: no private or course-owned material used until approved
    knowledge_source_policy:
      status: blocks_release
      value:
        source_strictness: unresolved
        recommended_value: any_source_with_labels
        preview_source_mode: any_source_with_labels
        source_labels:
          - course-approved
          - professor-approved-external
          - system-suggested-trusted
          - unapproved-external
    academic_integrity_policy:
      status: needs_review
      value: unresolved
      warning: professor has not configured graded-work help
      safe_default: strict no full graded-work answers
  pedagogy:
    teaching_approach:
      status: needs_review
      value: balanced
    tutoring_moves:
      status: needs_review
      value:
        - hints
        - prompts
        - misconception_correction
    proactive_support:
      status: needs_review
      value: none
  professor_review:
    status: blocks_release
    decision: pending
```

## Approval Rule

The tutor may be previewed while the policy is still in draft status. It cannot
be released to students until:

1. all release blockers are resolved,
2. source strictness is explicitly confirmed,
3. unresolved academic-integrity warnings are configured or acknowledged,
4. the professor has reviewed the generated policy and response preview, and
5. the professor gives an explicit approve decision.

## Sprint 1 Evidence

This issue is complete when the repository contains:

- this tutor-policy extraction specification,
- a clear list of blocker and non-blocker fields,
- safe defaults for unresolved blocker fields,
- follow-up behavior for vague professor answers, and
- enough structure for the setup flow, preview behavior, and prototype tickets
  to use this as their foundation.
