# SDLC visual revision — 6 September 2026

Scope: English LaTeX, original vector figures, report evidence qualifications,
navigation and packaging. No application/API/type/runtime changes or new
experiments. The diagrams describe the inspected working tree, which includes
uncommitted prior implementation work, not only the HEAD commit.

## Editorial decisions

The previous figures used small labels, intersecting routes and mixed levels of
abstraction. The replacement keeps one principal question per view. All eleven
figures are monochrome; shapes, line styles, explicit labels and guards convey
meaning. The smallest diagram text is 9.8 pt before the approximately 1.003x
manuscript scaling. The PDFs contain vector text, not screenshots. Captions name the specific interaction or decision; symbol tutorials and
repeated diagram summaries have been removed.

| View | Question | Implementation / evidence checked |
| --- | --- | --- |
| 1. Course activity, swimlanes | Who configures, approves and uses a release? | `src/digital_twin/onboarding/`, `student/publication.py`, `student/service.py`, `student/proactive.py` |
| 2. Logical architecture | Which entry points, components and boundaries own work? | `services/`, `apps/`, domain services, repository contracts, configured provider adapters |
| 3. Tutoring sequence | What happens before a response and learner state commit? | `src/digital_twin/student/service.py`, `student/repository.py`; authority/revision checks, request identity and evidence branch |
| 4. Two state consumers | Is planning state the same as assessed student evidence? | `student/learner_belief.py`, `student/autonomy_control.py`, `student/planning_architectures.py`; counts and delivery/event proxy remain distinct |
| 5. Planner decision + Table 3 | When can a model replace the event fallback? | `student/planning_architectures.py`; permitted steps, analytic best and minimum 0.04 gain; worked hint 0.325 and question 0.267167 |
| 6. Proactive activity + Table 4 | How does one job reach delivery and end? | `student/autonomy_runtime.py`, `student/autonomy_service.py`, `student/proactive.py`, `student/repository.py`; lease, authorization, one repair, stable delivery key, separate job commit |
| 7. Goal state machine | What changes active to completed, expired or cancelled? | `student/autonomy_models.py`, `student/autonomy_control.py`, `student/repository.py`; three attempts blocks further work without changing active status; terminal states cannot reactivate |
| 8. Corpus-scale failure | Why can correct retrieval still cause clarification? | `academic-factual-qa-open-10000-winner-regression-001` and its recorded 100-case diagnostic; confirmation 024's single-chunk fixture did not exercise V3 ambiguity |
| 9. Simulation design | What does the candidate observe, and what does the scorer know? | `successor-learner-timing-simulation-001-summary`; 6 development seeds, 240 held-out histories per condition, 11 conditions, 30 virtual days; no text retrieval/generation |
| 10. Publication sequence | Which operations share the release transaction? | `student/publication.py`, `student/repository.py`; index preparation and post-publication observer are outside the commit |
| 11. Conceptual data | Which identities persist and which updates are derived? | `student/models.py`, `student/repository.py`, `student/autonomy_models.py`; grouped contracts are not a complete SQL schema |

Paths beginning `student/` are relative to `src/digital_twin/`.
The figures use C4 responsibility labels and selective UML sequence/activity/state
conventions, not a claim of a complete formally verified UML model. Original
wording, layout and implementation mapping are authored for this report.

The previous two-page diagram-contract appendix is no longer compiled. Repeated
design-family results are replaced by a navigation/disposition table; the main
comparisons and failure map retain the analysis. No registered trial is deleted.
Detailed operating measurements remain in the appendices.

## Large-test clarification

The records support a cumulative 10,000-case pipeline exercise, a separate
10,000-case product benchmark with a 1,000-case paired subset, and a later known-
benchmark regression. No 100,000-case execution was established in the inspected
records. They are now identified separately as L1, L1c, L2 and L3.

L1's later correction identifies reference-aware answer/citation construction;
its pipeline completion cannot be claimed as independent factual accuracy.

L3 contains an unresolved arithmetic contradiction. Its durable JSON summary
records 8,000 answerable cases, 1,669 total answer actions and 25.38% fully
grounded success. Both the inspected scorer and the scorer at recorded revision
`e1e00fb` require the correct answer action and average success over answerable
cases. The recorded answer count therefore bounds that rate at 20.8625%.
The report excludes 25.38% from performance comparisons, preserves the original
trial text, and adds a dated note directly above its companion entry. It does
not invent a corrected accuracy value or rerun/rescore the sealed benchmark.
The original response ledger was not found among the inspected local artifacts;
recorded action counts and gate decisions are explicitly attributed to the
retained summary. This is a report audit qualification, not a new experimental
run or an independently validated replacement result.

## Verification

- 474 registered trials and 1,810 source allocations retain destinations or an
  explicit exclusion reason; all trial identifiers and anchors remain unique.
- 19 bibliography entries are cited; twelve named cross-PDF study links resolve.
- 99 numerical checks reconcile the main comparison rows, lifecycle results,
  worked planner calculation and recorded large-test fields. The L3 contradiction
  remains explicitly excluded, not marked resolved by those checks.
- All eleven diagram PDFs are vector, monochrome and have in-bounds text at
  least 9.8 pt. The final main PDF is also checked for monochrome rendering.
- Main PDF: 35 pages. Companion: 326 pages. Both compile without layout,
  undefined-reference or bibliography warnings. Every main page and all changed
  companion pages are rendered for visual review.
- The source bundle is rebuilt separately; page text, destinations and rendered
  output are compared with the canonical PDFs before the submission manifest
  is refreshed.

QA outputs: `reports/generated/submission-review-20260906/verification.json`,
`numerical-verification.json`, and
`reports/generated/sdlc-visual-revision-20260906/visual-verification.json`.
The portable bundle contains active report sources and indices, not the raw
experimental data needed to rerun the studies.


## Final reader edit

Removed approximately 1,000 words of repeated/general prose and captions, plus
in-figure headers and symbol legends. Method, result denominators, unresolved
failures, AI-use disclosure and source references remain. Normal and blocked
activity paths end at UML activity-final nodes. Sequence diagrams use execution
specifications and final reply messages; no activity-final circles or object-
destruction crosses are added to persistent service lifelines. The outreach
conditions and goal-state view now share a page.

Final layout follow-up: the tutoring sequence is on page 6; the compact data
relationships diagram is on page 26, followed by the publication sequence on
page 27. Text size is unchanged. Operational status clarification is recorded
in docs/local-r1-runbook.md; the hash-bound component profile is unchanged.
