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

DIRECTION: Extend the approved Grounded AI Workspace. Desktop uses a 240px assigned-course rail, focused conversation canvas, and 420px citation panel. Mobile uses a compact course switcher and citation bottom sheet. The floating composer is the only elevated object.

MEMORABLE MOMENT: Selecting citation `[1]` keeps the answer in context while revealing the exact synthetic source title, page locator, source version, and current release boundary.

REFERENCE: `reports/generated/ui-redesign-issue-82-student-workspace/student-workspace-desktop-concept.png` and `student-workspace-mobile-concept.png`.

UNRESOLVED: Credentialed authentication, conversation listing across devices, real-course content, and human-usability validation remain outside this slice.
