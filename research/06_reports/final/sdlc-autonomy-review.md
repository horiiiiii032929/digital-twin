# Autonomy and SDLC reader review

Date: 6 September 2026. Scope: report and figure changes only.

## Findings and revisions

The previous activity diagram omitted the later-event feedback path and did not
separate worker scheduling, planner proposals and application delivery authority.
The revised Section 4.2 defines goals and opportunities, the observer's event
heuristics, action eligibility, selected and alternative planners, validation,
repair bounds, in-app delivery, persistence and termination. Its illustrative
trace is explicitly not a new experiment or invented observed output.

The SDLC argument previously left readers to connect requirements, component
choices, tests and operations. Section 5.1 now explains that connection; Appendix
D maps six lifecycle stages to retained artifacts and acceptance boundaries.
Application correctness, candidate quality and educational acceptance remain
separate. The report does not claim that retrospective stage mapping proves a
prospectively completed linear process or a production deployment.

## Implementation traceability

| Explanation | Inspected source |
| --- | --- |
| Default 30-second poll; observer followed by due processing | `scripts/autonomous_tutoring_worker.py` |
| Two overlapping-concept confusion observations at 0.7; default 72-hour inactivity; leases | `src/digital_twin/student/autonomy_service.py` |
| Event/policy intersection and deterministic fallback | `src/digital_twin/student/autonomy_eligibility.py`, `src/digital_twin/student/autonomy_runtime.py` |
| H+E1 composition; bounded wording; guarded value-model agreement and default 0.04 margin | `services/api/app/factory.py`, `src/digital_twin/student/planning_architectures.py`, `src/digital_twin/student/autonomy_service.py` |
| One proposal, generation and at most one repair; uncertain-call stop | `src/digital_twin/student/autonomy_runtime.py` |
| In-app delivery, stable retry key and delivery status | `src/digital_twin/student/autonomy_service.py`, `src/digital_twin/student/proactive.py` |
| Default three-attempt, seven-day goals and assessed-evidence lifecycle | `src/digital_twin/student/autonomy_control.py`, `src/digital_twin/student/service.py` |
| Requirements and change acceptance | `docs/quality-and-learning-plan.md`, `research/05_evaluation/result-registry.md`, `research/05_evaluation/profiles/` |
| Deployment, backup/restore and rollback scope | `docs/local-r1-runbook.md` |

These defaults identify code behavior, not empirically optimal teaching values.
The goal manager uses heuristic assessment summaries; the report does not equate
a completed software goal with demonstrated student mastery. Model selection is
configuration-dependent. The diagram abstracts storage details and does not
claim a distributed transaction over all graph state and delivery records.

## Verification

Existing governed-autonomy tests: 42 passed (five dependency deprecation warnings).
Command: `.venv/bin/python -m pytest tests/digital_twin/test_governed_autonomy.py -q`.
Coverage includes consent withdrawal, restart and duplicate delivery, student
response linkage, goal expiry, kill switch, pause/resume and attempt limits.
These checks corroborate the described control flow; they are not a fresh
provider evaluation or a complete system acceptance test.

The main PDF has 19 pages: 12 main text/declaration, two references and five
appendices. The detailed trial companion and its 470-result snapshot are
unchanged. Compiler diagnostics, local Markdown links and PDF text bounds were
checked; changed figure and table pages were visually inspected. Before/after
artifacts and logs are retained locally under
`reports/generated/sdlc-reader-revision-20260906/`.
