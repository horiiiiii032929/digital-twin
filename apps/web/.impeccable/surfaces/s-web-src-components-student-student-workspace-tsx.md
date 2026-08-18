---
version: 1
slug: "s-web-src-components-student-student-workspace-tsx"
primary_target: "apps/web/src/components/student/student-workspace.tsx"
related_targets: ["apps/web/src/hooks/use-student-workspace.ts","apps/web/src/lib/api/student.ts","apps/web/src/App.tsx"]
---

SCOPE: Student tutoring workspace at `/student`; Operate mode. The professor console remains a separate role surface.

AUDIENCE AND JOB: A student with a synthetic local account selects an assigned published course, starts or restores one release-bound conversation, asks a question, and inspects validated source lineage.

TASK AND PROOF: Course availability and release binding precede chat. Every normal answer can expose citation title, locator, source version, and current-release lineage. Safe failures are explicit and actionable. Server state is authoritative; local storage remembers only conversation identifiers.

CONSTRAINTS: Use only existing `/api/student` behavior and synthetic fixture data. Do not imply credentialed identity, live ingestion, streaming, model selection, web search, human usability, learning outcomes, or production readiness. Preserve role/course/release isolation and failed input.

DIRECTION: Use the shared conversation-first grounded workspace. Desktop uses a 216px truthful course rail and a wide conversation canvas; citation lineage opens in a 384-408px contextual inspector only after an inline citation action. Mobile uses a menu sheet and citation bottom sheet. The floating composer is the only elevated object.

MEMORABLE MOMENT: Selecting citation `[1]` preserves the answer position and opens the exact synthetic source title, page locator, source version, and current release boundary; closing it restores the full-width conversation.

REFERENCE: `reports/generated/ui-redesign-product-wide/composition-c-accepted.png`; the earlier issue #82 concepts remain historical evidence, not the current layout authority.

UNRESOLVED: Credentialed authentication, conversation listing across devices, real-course content, and human-usability validation remain outside this slice.
