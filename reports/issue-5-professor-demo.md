# Issue #5 professor demo

Related issues:

- #5 `[S1 06/28] Minimal chat-led onboarding prototype`
- #6 `[S1 06/28] Professor review for chat-led onboarding`

Local demo artifact:

- Recommended: `reports/generated/onboarding-professor-review-smooth-demo.mp4`
- Fast Q&A process: `reports/generated/onboarding-qna-fast-demo-1_33x.mp4`
- Full walkthrough: `reports/generated/onboarding-professor-review-demo-2x.mp4`
- Original: `reports/generated/onboarding-professor-review-demo.webm`

The videos are generated locally and ignored by git through `reports/generated/*`.
Keep them there for local review, or upload the smooth MP4 manually to the
GitHub issue if a shareable GitHub-hosted artifact is needed.

## Demo storyline

For a quick professor message, use the fast Q&A process video first. It shows
the five-question chat-led onboarding interview and the generated policy tab in
under 20 seconds.

1. Start on the Professor Review Console after the demo session has been staged.
2. Show that release readiness is visible immediately: draft-only, blockers, and
   accepted preview count.
3. Show the synthetic syllabus metadata file approved as a course-approved
   source. No real course, instructor, or student data is used.
4. Show the completed AI-led instructor interview:
   - approved sources and private-source exclusions
   - teaching approach
   - academic-integrity boundary
   - misconception handling
   - professor rejection criteria
5. Show the generated tutor policy review surface, including release-blocking
   policy fields.
6. Show preview evidence with configured responses, source labels, warnings, and
   accept/reject decisions.
7. Show a professor custom prompt that has been accepted.
8. End on the approval checklist: preview items are accepted, but final release
   remains blocked until policy blockers and explicit professor approval are
   resolved.

## Professor review framing

The demo is meant to answer three questions:

- Is a chat-led interview a reasonable way for a professor to configure tutor
  behavior?
- Are the generated policy fields and preview cases understandable enough to
  review?
- Does the release gate make it clear that the tutor stays draft-only until the
  professor explicitly approves it?

## Current limitation to mention

Sprint 1 is still metadata-only and provider-neutral. It does not implement real
source ingestion, retrieval, authentication, persistence, or student-facing
tutoring yet.
