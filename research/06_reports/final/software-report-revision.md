# Latest revision pointer

The current 34-page monochrome manuscript and eleven-figure review are recorded
in [sdlc-visual-revision.md](sdlc-visual-revision.md). The dated entries below
preserve earlier editorial snapshots; their older pagination and six-figure
counts are not the current submission state.

# Software-centered report revision

Date: 6 September 2026  
Scope: report, diagrams and evidence navigation only; no runtime/API/type changes.

## Reader-facing change

The report now starts with requirements and an instructor-to-student walkthrough.
It explains what is configured, how publication binds it to a course, how a
student selects that course and how tutoring produces a saved response.
Architecture and decision tables follow those concrete operations. Evaluation
is organized by requirement, with cost, latency and trial chronology moved to
the appendices. Failed factual, pedagogical and evaluation gates remain in the
main results and conclusion.

The eight-field synthetic profile table comes from
`scripts/teaching_profile_responsiveness_packet.py`. Saved F21 and F03 outputs
come from `research/05_evaluation/dialogue-full-live-001-assistant-findings.json`.
They are illustrative outputs from different contexts, not a paired causal
profile experiment. No output was invented or executed for this revision.

## Implementation traceability

| Diagram or explanation | Inspected implementation |
| --- | --- |
| Role-specific entry and professor setup/delivery | `apps/web/src/App.tsx`, `apps/web/src/components/professor/professor-workspace.tsx`, `apps/web/src/hooks/use-onboarding-session.ts` |
| Course selection and compatible stored conversation | `apps/web/src/hooks/use-student-workspace.ts`, `services/api/app/routers/student.py` |
| Draft, preflight and publication binding | `src/digital_twin/student/publication.py`, `services/api/app/routers/publication.py` |
| Response and persistence boundary | `src/digital_twin/student/service.py` and the associated tutoring runtime |
| Eligibility, quiet hours and proactive outcomes | `src/digital_twin/student/autonomy_service.py`, `src/digital_twin/student/autonomy_runtime.py` |
| Trial profile settings | `scripts/teaching_profile_responsiveness_packet.py`, `scripts/run_operational_dialogue_development.py` |

Existing publication diagram conventions were retained. The new logical diagram
simplifies the earlier dense drawing; the original assets remain available.
The new activity figure is a summary of the worker's decisions, not a claim
that every listed guard runs in one function or in only one order.

## Archive construction and boundaries

The companion groups records into eight design families for navigation. This
editorial grouping does not pool their results or establish equivalent conditions.
Every one of the 470 registry rows has an entry, retaining the source status and
decision. There are 891 distinct linked evidence paths, including two secondary
machine summaries found through the readable records. Governance reconciliation
includes 296 decision-log/method-catalog table rows and 139 direct experiment or
learning documents; the two nested blank templates have explicit exclusion reasons.
There are 1,798 source allocations. Counts are recorded in
[design-appendix-coverage.json](design-appendix-coverage.json).

Configuration, metrics, provenance and limitations are bounded source extracts.
Candidate lists retain each listed candidate; displayed metric lists are bounded
and explicitly point to the full records for remaining fields. Structured floats
are shown to six significant figures in source units. Historical labels are
retained as claims of the original record, not independently revalidated here.
No raw ledgers, unpublished instructor materials or private student records were
copied into the manuscript or companion.

Related-record edges come from exact identifiers and resolved evidence links.
They preserve navigation between corrections and predecessors without treating
every reference as an invalidation. Missing direct plan links mean that execution
has not been established by this reconciliation; they do not prove nonexecution.

The preceding manuscript and PDF, construction scripts and final verification
outputs are preserved locally in
`reports/generated/software-report-restructure-20260906/`. The delivered LaTeX
and indices are the static, reviewable source snapshot. This review did not
rerun historical experiments or claim fresh software qualification.

## Final package verification

The main PDF has 16 pages: 10 pages of main text and AI disclosure, two of
references, and four of summary/publication/software appendices. The companion
has 324 pages. Every registered result ID and all 470 stable run destinations
are present in the companion. Indices contain one-based physical PDF pages;
all non-template source allocations resolve to a destination.

Four interpretation-correction pairs whose summaries used shortened names
were additionally resolved by reading the correction text and its predecessor.
They are recorded in [design-correction-map.json](design-correction-map.json)
and shown in both the original and correcting entries. Other cross-references
retain their weaker source-reference meaning.

Both PDFs compiled without undefined references, missing characters or
overfull/underfull boxes. The main report's pages and representative companion
layouts were visually inspected; all pages were screened for off-page text.
The existing publication figure's PDF-version warning remains non-blocking.
Bibliography consistency (14 cited entries), local Markdown links, evaluation
record validation and the repository correctness inventory check passed.
No application test suite or paid model evaluation was rerun for this editorial
change.

## Evaluation explanation update

The subsequent [reader guide revision](evaluation-reader-guide.md) adds four
numbered equations, denominator definitions and concrete interpretations. The
current main PDF is 17 pages (11 main text/declaration, two references, four
appendices); the 324-page companion and its record coverage are unchanged.
The 16-page verification above records the preceding editorial snapshot.

## Autonomy and SDLC update

The [autonomy and SDLC review](sdlc-autonomy-review.md) adds explicit decision
ownership, event feedback and lifecycle traceability. Current pagination is
19 pages: 12 main/declaration, two references and five appendices. The companion
remains unchanged. Earlier pagination above records preceding snapshots.

## Professor-perspective revision

The [reader review](professor-reader-review.md) connects three questions to
results, adds evaluation-design provenance and a recorded autonomy example, and
shows the assessment correction as a concrete SDLC cycle. Pagination remains
19 pages with 12 main/declaration pages.

## Software decision review

The [decision audit](software-decision-review.md) strengthens the main design
table and adds a failure-mechanism appendix. The current main PDF has 21 pages
(13 main/declaration, two references and six appendix pages). Earlier counts
above remain historical snapshots.

## Diagram contract audit

The [complete visual audit](diagram-audit.md) rebuilds all six figures around
explicit responsibility, data and recovery boundaries. Eight tables and four
equations retain their evidence definitions. Current pagination is 24 pages
(13 main/declaration, two references, nine appendix pages).

## Submission revision: six-chapter software argument

The 6 September 2026 submission revision supersedes the earlier outline and
pagination above. The manuscript now has six chapters: objective and contribution,
course walkthrough, runtime design, comparative decisions, integrated verification,
and findings. It is split into active chapter inputs under chapters/ while
report.tex remains the canonical entry point.

The runtime chapter traces committed concept assessment separately from the
default planner adapter's delivery/event proxies. It defines evidence confidence,
objective-scoped completion and action utility, supplies a worked calculation,
and explains the worker-to-planner-to-delivery-to-later-response cycle. The
autonomy diagram was reconciled with those boundaries and regenerated.

The comparison chapter retains the agreed evidence-interface comparison,
guarded-planner study, full four-model-allocation grid, all nine estimator/timing
combinations and two bounds, and unsuccessful generation/visual candidates.
Study G explicitly identifies 654 actual model calls over 24 synthetic histories;
Study H is a separate deterministic, matched 72-history-per-arm lifecycle
regression. Historical 025 results remain alongside their later interpretation
correction. No runtime changes or new experiment runs were made in this revision.

Current output is 31 main-PDF pages: 16 main/declaration, two references and
13 appendix pages. The companion has 327 pages. It contains all 474 registered
rows, including the four recent goal-completion records. Reconciliation covers
897 linked evidence paths, 1,810 source allocations, 297 governance rows,
140 plan/learning documents, 116 related edges and five explicit correction pairs.
All 474 stable destinations exist; indices contain one-based physical PDF pages.

Final QA resolved all 17 citation keys, 55 unique LaTeX labels, eight named
cross-PDF study links, and every allocation destination. All pages in both PDFs
passed off-page text checks. All main-report pages and 22 representative
companion pages were visually inspected, including the four new trial entries,
family openings, governance tables and end pages. There were no overfull,
underfull, missing-character or undefined-reference warnings. Tectonic retained
non-blocking warnings about Graphviz PDF 1.7 assets in PDF 1.5 output.

The report-value reconciliation passed 87 numeric checks, including every cell
of the eleven-row learner/timing table. It prompted a wording correction:
BKT's constant-timing next-answer Brier difference is inconclusive, rather than
an exact absence of improvement. Evaluation-record validation passed for 399
machine records, 465 result summaries and two supporting summaries. These are
document/evidence checks; the earlier application tests are reported with their
original run and recheck boundaries.

Generated QA records, contact sheets and the report-value reconciliation are
retained under reports/generated/submission-review-20260906/. The portable
source bundle preserves the active LaTeX and index snapshot without raw logs.

The final 47-file source ZIP was extracted into a fresh temporary directory
and both PDFs compiled successfully there. Page counts, extracted page text,
named destinations and low-resolution renders of every page matched the
canonical PDFs. The output submission manifest records the final PDF and ZIP
hashes. The final local Markdown check passed 2,005 links.
