# Issue 80 professor console redesign

Issue: [#80 Redesign professor review console UX/UI](https://github.com/horiiiiii032929/digital-twin/issues/80)

Date: 2026-08-18

Baseline: `2071c8b999621b9d567442ca492d6c372e23b1bd`

Candidate: `codex/redesign-professor-console`

Engineering disposition: **Ready for professor/user review. Do not call this a
human-usability result.**

## Decision question

Can the existing professor workflow be reorganized so release state, the next
decision, supporting evidence, and professor authority are easier to follow
without changing the onboarding API, introducing unsupported features, or
weakening any release gate?

## Compared directions

- **Baseline:** neutral card-and-tab console at the technical-freeze revision.
- **Candidate A:** evidence-led academic decision sheet.
- **Candidate B:** dense proof desk; rejected because it suggested unsupported
  evidence-library and export functions.
- **Candidate C:** release workbench; useful two-pane focus, but too visually
  heavy as a complete direction.
- **Selected candidate:** A+C, named **The Course Release Dossier**—an
  evidence-led dossier with a focused workbench and restrained status-only
  color.

## Implemented result

- Replaced duplicate setup-map and tab navigation with one keyboard-accessible
  five-stage route: Sources, Interview, Policy, Preview, and Approval.
- Added one active workbench and one adjacent review-context rail containing
  release readiness, blockers, evidence snapshots, and workflow trace.
- Reworked interview messages, source decisions, policy fields, preview cases,
  revisions, and approval items as ruled review records rather than nested
  cards.
- Preserved all existing controller actions and API contracts. No model,
  integration, course data, analytics, export, or release capability was added.
- Corrected local readiness derivation so pending/excluded source metadata is
  not counted as approved, and unresolved policy, preview, and checklist data
  independently marks its stage blocked.
- Applied the independent Impeccable finish review: desktop route/context rails
  now remain sticky, the duplicate readiness block was removed from the evidence
  rail, and mobile headers, route rows, chat height, and release labels were
  compacted without hiding the release state or next decision.

## Engineering evaluation

The flow under test was: app loads → professor completes the five interview
prompts → policy, preview, and approval surfaces render → route selection and
release context update without runtime errors.

| Check | Result |
| --- | --- |
| Page identity and meaningful content | Pass: meaningful title, release ledger, five-stage route, active workbench, and review context |
| Functional parity | Pass: all five existing stages and revision/approval actions remain wired to the existing controller |
| State derivation regression tests | Pass: 18 frontend tests, including pending-source and unresolved-stage cases |
| Repository regression suite | Pass: 299 Python tests, frontend tests, validators, lint, and production build via `npm run check` |
| Impeccable deterministic audit | Pass: zero findings after the final changed-target scan |
| Rendered desktop check | Pass at 1280×720; no page-level horizontal overflow, framework overlay, console error, or console warning |
| Interaction check | Pass: route selection works; five suggested answers generate the policy and update blocked/complete stage states |
| Responsive implementation review | Pass at code level after finish review: the route becomes horizontally scrollable, the three-region workbench stacks, narrow headers and chat become content-driven, and release labels remain explicit below the `xl` breakpoint |
| Human usability | Not run |
| Professor preference/approval | Pending |

The in-app browser could render the desktop app but did not expose viewport
emulation in this run. Therefore the candidate does not claim new measured
mobile usability; a short real-device or narrow-window visual check remains a
review task before closing #80.

## Evidence and limitations

Local, ignored visual artifacts are stored under
`reports/generated/ui-redesign-issue-80/`, including three explored directions
and the final desktop policy-state screenshot. The candidate uses only
synthetic demonstration data.

This result supports engineering correctness and a review-ready visual
candidate only. It does not establish faster task completion, lower error rate,
accessibility conformance, human usability, professor satisfaction, pedagogy,
learning outcomes, or production readiness.

## Next decision

Ask the user/professor to review the candidate at desktop and a narrow mobile
width. Mark #80 **Keep** only if the five-stage route, information density, and
evidence rail are understandable without explanation; otherwise record the
specific friction and refine the candidate.
