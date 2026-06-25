# Chat-led response preview behavior

Date: 2026-06-24
Issue: #4 `[S1 06/28] Chat-led response preview behavior`

## Purpose

This artifact defines how a professor previews sample tutor behavior after the
onboarding chat generates a draft tutor policy.

The preview is a Course Digital Twin release-approval gate. Its main job is to
show whether the tutor can answer with inspectable grounding, visible source
labels, and enough professor control before students see it. It does not try to
prove tutoring effectiveness or replace a full evaluation study.

## Research claim

Professor approval should be based on inspecting grounded tutor behavior, not
only reading extracted tutor-policy fields. A Course Digital Twin is more
trustworthy when the professor can test representative prompts, inspect source
use, reject bad behavior, and revise policy through chat before release.

## Sprint 1 scope

### In scope

- Actual generated tutor responses from the current draft tutor policy.
- Live web/search during preview when external sources are needed.
- Configured-tutor preview as the primary view.
- Generic tutor output as an expandable contrast view.
- Source labels and expandable source audit.
- Core preview cases for external grounding, academic integrity, and one
  professor-authored custom prompt.
- Chat-based policy patch review after rejected preview behavior.
- Release checks tied to preview decisions.

### Out of scope

- Full production citation pipeline.
- Full automated source correctness or contradiction detection.
- Full tutoring-effectiveness evaluation.
- Student-facing UI implementation.
- Automated grading.
- Real student-data collection.

## Preview principles

- Preview supports professor approval of the Course Digital Twin, not only
  isolated response review.
- Preview validates behavior, not only fields.
- Preview remains inside the chat-led onboarding loop.
- The configured tutor response is the release candidate. Generic output is
  secondary evidence and should be expandable.
- Source behavior must be inspectable without making the answer unreadable.
- A rejected preview response blocks release.
- Source strictness must be confirmed before release.
- Academic-integrity behavior is configurable, but unresolved integrity policy
  uses a strict no-full-answers default and shows a warning rather than blocking
  release.

## Source strictness modes

The tutor policy should support three course-level source strictness modes:

| Mode | Meaning | Release behavior |
| --- | --- | --- |
| `course_only` | Use only professor-approved course materials. | External sources are not used in released tutor answers. |
| `trusted_only` | Use course materials plus trusted external source categories or approved allowlist entries. | Untrusted or unapproved sources are excluded. |
| `any_source_with_labels` | Any external source may be used if visibly labeled and auditable. | This is the recommended mode, but it must still be confirmed by the professor before release. |

During preview, unresolved source strictness uses `any_source_with_labels` so
the professor can inspect the most transparent external-source behavior. Release
remains blocked until the professor confirms the source strictness mode.

## Source labels

Every source used in a configured preview response should receive one of four
labels:

| Label | Meaning |
| --- | --- |
| `course-approved` | Source is approved course material. |
| `professor-approved-external` | Professor explicitly approved the external source, domain, source family, or source category. |
| `system-suggested-trusted` | System considers the source category high-trust, such as official documentation, standards or security bodies, or university pages. |
| `unapproved-external` | Source is external and not yet professor-approved or system-trusted. |

Unapproved external sources may appear in preview and may be allowed after
release under `any_source_with_labels`, but they must be visibly labeled.

## Trusted source policy

The trusted-source allowlist should be generous but inspectable. Entries can be:

- professor-defined domains, source families, or specific sources;
- system-suggested trusted categories;
- source families referenced by uploaded course materials.

System-suggested trusted sources may remain visible after release without
explicit professor approval only for high-trust categories:

- official documentation,
- standards or security bodies,
- university pages.

Blogs, videos, forums, news articles, and other lower-trust sources should be
labeled as `unapproved-external` unless the professor approves them.

## Required preview cases

Sprint 1 should use a core-plus-optional model. Required core cases are:

| Case | Prompt source | What it tests |
| --- | --- | --- |
| External-source grounding | System suggests a course-derived topic; professor can replace it. | Whether live search, source labels, and the audit make external grounding inspectable. |
| Academic integrity | System suggests a course-derived graded-work prompt; professor can replace it. | Whether the tutor follows the configured integrity policy or strict unresolved default. |
| Professor custom prompt | Professor writes the prompt and must choose a test tag. | Whether the professor can test the risk they personally care about before release. |

Professor custom prompts require one tag: `source_grounding`,
`academic_integrity`, `misconception`, `teaching_behavior`, `tone`, or `other`.

Optional cases can include source conflict, misconception correction, and normal
course-grounded conceptual questions. They should be available under a lightweight
"run more tests" path, not forced into the core onboarding flow.

## Preview response behavior

Each core case should generate an actual configured tutor response using the
current tutor policy. Mocked or scripted responses are not sufficient for the
Issue #4 behavior specification, though later prototype notes may explain any
temporary implementation gap.

The preview should show:

1. Student prompt.
2. Configured tutor response.
3. Source labels grouped at the end of the answer.
4. Expandable source audit.
5. Expandable generic tutor comparison.
6. Warnings, if obvious issues are detected.
7. Professor decision: accept or reject.

The answer should not add verbose in-line explanations every time it uses
non-course knowledge. The grouped source labels and expandable audit are the
disclosure layer.

## Source audit

The expanded source audit should show:

- source title,
- URL,
- source type,
- source label,
- which claim or answer part the source supports,
- conflict status against available course material,
- why search selected the source.

The default answer view can stay compact. Source labels appear grouped at the
end; claim-to-source detail lives in the expanded audit.

## Warnings

Sprint 1 should avoid pretending it has a reliable automated judge. The system
may show warnings for obvious issues, but the professor makes the final decision.

Allowed warnings:

- external source used without citation or audit entry,
- source type not approved or not trusted,
- possible course/external conflict detected,
- academic-integrity prompt appears to receive a full solution,
- no course comparison available for conflict checking.

Warnings do not automatically fail the preview. A professor rejection blocks
release.

## Source conflicts

If course material and an external source appear to conflict, the tutor should
show both framings and make the course context clear. A conflict does not
automatically fail preview if the response clearly explains the difference and
tells the student which framing applies for this course.

The professor should be able to revise both:

- source rules, such as approving, rejecting, or changing trust for the external
  source; and
- teaching policy, such as telling the tutor how to explain disputed material in
  this course.

Sprint 1 conflict detection is only a lightweight warning based on available
course snippets and external-source claims. It is not a full contradiction
engine.

## Professor decisions

Each core preview case has two primary decisions:

| Decision | Meaning | Release impact |
| --- | --- | --- |
| Accept | The professor accepts this response as evidence for release review. | Case is marked accepted for the current policy version. |
| Reject | The professor does not accept this response. | Release is blocked until the professor confirms a policy or source change, reruns the affected required preview case, and accepts the new result. |

Reject can be one click. A reason is not required to block release.

If the professor wants to revise and unblock the response, the chat should ask
for one reason category:

- source or citation problem,
- wrong or unsupported answer,
- conflict with course material,
- violates academic-integrity policy,
- teaching behavior mismatch,
- tone or wording problem,
- other.

The onboarding chat then maps that category and any optional explanation to a
candidate policy patch. The professor may edit the patch in natural language,
but the system should still display the affected structured policy fields before
the professor confirms the change.

Policy patches can update:

- source permissions or source strictness;
- trusted or disallowed source lists;
- academic-integrity rules;
- teaching approach or tutoring moves;
- tone guidance;
- professor rejection criteria.

The professor must confirm the policy patch before it updates the tutor policy.
After confirmation, the system creates a new tutor policy version and marks any
preview evidence from earlier policy versions as historical, not current release
evidence.

## Rerun behavior

After a policy patch, the affected required preview case must be rerun and
accepted before Course Digital Twin release can be unblocked. Any other required
preview case touched by the changed policy field should also be rerun before
release approval. The professor can continue previewing the draft Digital Twin,
but cannot approve it for student-facing release while a required rerun is
unresolved.

## Evidence snapshot

Each preview result should save:

- preview prompt,
- configured tutor answer,
- source list,
- source labels,
- timestamp,
- tutor policy version,
- professor decision.
- whether the result is current release evidence or historical evidence from a
  superseded policy version.

The evidence snapshot is intentionally lighter than a full search log. It is
enough for Sprint 1 professor review and later implementation planning.

## Approval checklist signals

Before deployment approval, the setup flow should show:

- source strictness confirmed,
- external-source preview accepted,
- academic-integrity preview accepted or warning acknowledged,
- professor custom prompt accepted,
- no rejected preview response remains unresolved,
- no required rerun remains unresolved after a policy patch,
- source labels and audit were visible,
- final professor release approval recorded.

Accepting preview cases does not release the Course Digital Twin by itself.
Release also requires the remaining safety, source, sensitive-data, and approval
checks from the tutor policy and setup flow.

## Limitations

Sprint 1 preview does not prove that sources are correct, that conflicts are
fully detected, or that tutoring improves learning outcomes. It tests a narrower
research claim: whether the professor can inspect grounded tutor behavior,
reject unacceptable outputs, and revise the tutor policy before release.

## Acceptance criteria trace

| Issue criterion | How this artifact satisfies it |
| --- | --- |
| Preview supports professor validation before release. | Defines required core cases, professor accept/reject decisions, source strictness confirmation, and release checklist signals. |
| Preview can reveal teaching style, grounding, and policy problems. | Emphasizes grounded behavior, source labels, expandable audit, warnings, custom prompt tags, and conflict handling. |
| Revision loop routes back through chat or generated-policy correction. | Reject-to-revision flow maps reason categories to structured policy patches that the professor can edit, confirm, rerun, and accept before release is unblocked. |
| Preview behavior supports the minimal onboarding prototype. | Specifies the minimum generated-response, source-label, audit, decision, and evidence behavior needed for Issue #5. |

## Related artifacts

- `research/02_requirements/instructor-onboarding.md`
- `research/02_requirements/chat-led-tutor-policy-extraction.md`
- `research/02_requirements/chat-led-instructor-setup-flow.md`
- `docs/privacy-and-ethics.md`
- `research/05_evaluation/rubric.md`
