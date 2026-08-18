# Chat-led onboarding prototype

The Sprint 1 onboarding prototype now covers the full professor review loop
described in the research artifacts while staying provider-neutral.

This page preserves the scope of the Sprint 1 onboarding component. The later
bounded student and release-publication implementation is documented in
[student-workflow.md](student-workflow.md); it does not turn the metadata-only
onboarding UI into production authentication, ingestion, or administration.

## Professor review console

Issue [#80](https://github.com/horiiiiii032929/digital-twin/issues/80)
restructures the existing features as an evidence-led release dossier. The UI
has one five-stage route—Sources, Interview, Policy, Preview, and Approval—plus
one active workbench and an adjacent review-context rail. Release status,
recommended action, blockers, evidence snapshots, and workflow trace remain
visible without duplicating navigation or turning chat into the whole product.

The redesign does not add a model, integration, data source, release action, or
research claim. It preserves the existing API/controller boundary and remains
an experimental demonstration. Automated and rendered engineering checks are
documented in
[the issue #80 implementation report](../reports/issue-80-professor-console-redesign.md);
human usability and professor approval remain untested.

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

This prototype does not implement production ingestion, authentication,
database persistence, RAG, LMS integration, live search, or student-facing
tutoring.
