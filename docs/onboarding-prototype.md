# Chat-led onboarding prototype

The Sprint 1 onboarding prototype now covers the full professor review loop
described in the research artifacts while staying provider-neutral.

This page preserves the scope of the Sprint 1 onboarding component. The later
bounded student and release-publication implementation is documented in
[student-workflow.md](student-workflow.md); it does not turn the metadata-only
onboarding UI into production authentication, ingestion, or administration.

## Professor review console

Issue [#80](https://github.com/horiiiiii032929/digital-twin/issues/80)
restructures the existing features as a familiar LLM-style professor workspace.
The UI has one five-stage route—Sources, Interview, Policy, Preview, and
Approval—plus a natural setup conversation, an adjacent structured review tool,
and an Activity view. Release status, recommended action, blockers, evidence
snapshots, and workflow trace remain inspectable without turning the prototype
into a report or hiding professor authority.

The redesign does not add a model, integration, data source, release action, or
research claim. It preserves the existing API/controller boundary and remains
an experimental demonstration. Automated and rendered engineering checks are
documented in
[the issue #80 implementation report](../reports/issue-80-professor-console-redesign.md);
human usability and professor approval remain untested.

Populated review states use progressive disclosure: policy fields and preview
cases are reviewed one at a time, each action has a field- or case-specific
accessible name, completed approval checks are separated from the remaining
queue, and switching stages returns the inspector to its summary rather than
preserving an unrelated scroll position.

## Synthetic supervisor walkthrough

Prepare the bounded student fixture, then run both local applications:

```bash
npm run prepare:supervisor-demo
npm run dev:api
npm run dev:web
```

Open <http://localhost:5173/?demo=supervisor>. Each load creates a fresh
in-memory professor session containing five synthetic interview answers, one
approved metadata-only synthetic source, 16 policy fields, three preview cases,
and the ten-item approval checklist. The route opens at Policy so a supervisor
can inspect the meaningful review state immediately. It contains no source file
contents, private course data, student records, professor approval, or
production release.

Use the **Student tutor** link to inspect the separately seeded synthetic
published release, ask or restore the cache-coherence question, and open citation
`[1]` to see source version, page locator, and current-release lineage. The
professor onboarding session and the student release remain separate prototype
boundaries; this walkthrough does not claim that the onboarding UI published the
student release.

## Sprint 1 defaults

- Local course uploads are metadata-only. The browser records file name, MIME
  type, size, permission status, source label, sensitivity flag, and notes. File
  contents are not read, parsed, stored, or committed.
- Preview grounding uses a deterministic local trusted-source catalog. It does
  not call live search or a provider SDK.
- State uses a repository protocol with an in-memory FastAPI implementation.
- Source labels are auditable: `course-approved`,
  `professor-approved-external`, `system-suggested-trusted`, and
  `unapproved-external`.
- The implemented agent roles are documented in
  [agents/README.md](agents/README.md): onboarding orchestration, source
  governance, tutor policy, preview evidence, and revision review.

## Reviewer flow

1. Start the API with `npm run dev:api` and the web app with `npm run dev:web`.
2. Add synthetic course-material metadata in Source Inventory.
3. Approve or exclude each source. Sensitive-looking names default to excluded.
4. Answer the five interview prompts with synthetic instructor answers.
5. Review generated policy fields, including source strictness, private-source
   exclusions, sensitive-data handling, feedback, proactive support, examples,
   rejection criteria, and tone guidance.
6. Inspect preview evidence. The configured response is primary; generic output
   and source audit are expandable.
7. Accept or reject preview cases. Rejected cases block release until accepted
   or revised.
8. Add a custom preview prompt and choose one required tag.
9. Send post-generation chat feedback to create a revision proposal, then
   confirm or discard it.
10. Complete the approval checklist. Release status becomes `approved` only
    after source, policy, preview, and professor approval blockers are clear.

## Out of scope

The professor onboarding component does not implement production ingestion,
authentication, durable session persistence, live retrieval, LMS integration,
or live search. The separate bounded student workflow is synthetic and is
documented in [student-workflow.md](student-workflow.md).
