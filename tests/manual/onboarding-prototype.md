# Manual verification: onboarding prototype

Use only synthetic file names and synthetic professor answers.

## Commands

- `npm run test:api`
- `npm run test:web`
- `npm run lint:web`
- `npm run build:web`
- `npm run dev:api`
- `npm run dev:web`

## Flow checklist

1. Open the web app at `http://localhost:5173`.
2. Add metadata for `week-01-slides.pdf`; approve it as `course-approved`.
3. Add metadata for `private-student-forum-export.json`; confirm it defaults to
   excluded and sensitive.
4. Answer the interview with synthetic policy choices:
   - Use syllabus, slides, assignments, and rubrics only.
   - Balance concise explanations with guiding questions.
   - Ask what the student tried first, then give hints.
   - Correct directly, then show a contrastive example.
   - Reject answers that complete graded work or cite unapproved sources.
5. Confirm the policy review shows source, privacy, integrity, pedagogy,
   feedback, proactive support, examples, rejection criteria, tone, and approval
   fields.
6. Open generic comparison and source audit for a preview case.
7. Reject the academic-integrity preview with a synthetic reason.
8. In chat, send: `This gives away too much homework help; require one guiding
   question before hints.`
9. Confirm the generated revision proposal and verify preview evidence updates
   to policy version 2.
10. Add a custom preview prompt with a required tag and accept it.
11. Accept all remaining preview cases.
12. Complete blocking approval checklist items.
13. Confirm release status is not approved until all source, policy, preview,
   and professor approval blockers are resolved.
14. Confirm no real professor, course, student, consent, transcript, or raw
   dataset content is committed.
