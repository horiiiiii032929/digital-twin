# Course Digital Twin Release

Status date: 2026-08-21

This Project tracks one parent outcome: release an invite-only Course Digital
Twin that professors can govern and authorized students can use for persistent,
citation-grounded tutoring. Benchmarks and component experiments are supporting
evidence, not competing end goals.

## Release stages

- **R0 — Local baseline:** reviewed UX and locally qualified package; retained
  as rollback evidence.
- **R1 — Hosted release candidate:** one immutable revision passes trusted
  HTTPS, credentialed roles, grounding, operations, restore, and rollback.
- **R2 — Invite-only pilot:** approved professors and students complete core
  workflows after consent, privacy, and supervisor gates.
- **R3 — Final project release:** code, configuration, evidence, demo, report,
  limitations, and release/no-release decision are reproducible.

## Current position

- Product UX: merged baseline from PR #83; synthetic flows pass, human
  usability is not yet established.
- Repository: 462/462 execution-relevant files audited; 707 Python and 46 web
  tests passed; the execution freeze remains active.
- Factual quality: draft PR #103 builds 10,000 deterministic truth packages
  and passes the 222-call network-free pilot-003 simulation. Paid pilot 003,
  1,000-case, and 9,000-case stages are unauthorized.
- Professor fidelity: fixed C0–C3 and explicit/inferred profile contracts are
  build-ready; professor guidance and calibration are pending.
- Deployment: local/container checks passed; public host/domain, trusted TLS,
  target-host restore, and walkthrough remain blocked.
- Multimodal grounding: region-aware foundations and original-region citations
  are retained, but no multimodal retrieval profile is selected; text remains
  the fallback.

## Release-critical order

1. Keep release goal #8 `In Progress` as the parent.
2. Review PR #103 and interpret professor guidance before separately
   authorizing one paid factual-QA pilot.
3. Select a public host/domain and finish #88's trusted-HTTPS rehearsal.
4. Calibrate #24 professor behavior separately from factual/citation hard
   gates.
5. Run #9 and #25 against the same immutable deployed revision.
6. Run #10 only after the human-participant approval boundary is satisfied.
7. Package the final evidence, demo, report, and rollback/no-release decision
   in #13.

## Current blockers

| Blocker | Unblocks |
| --- | --- |
| Professor dataset-method response | Pilot-003 method freeze |
| Professor profile-authoring response | Fidelity calibration |
| Explicit paid-run authorization after fresh provider checks | Pilot 003 |
| Public host and domain | Target-host deployment and operations |
| Consent/privacy/supervisor approval | Invite-only human pilot |

## Operating rules

- Every result remains registered, including failures and invalid runs.
- Deterministic source and citation checks are authoritative; model review is
  advisory.
- No private course/student data, credentials, `.env`, raw Vault files, or
  unrestricted outputs enter GitHub.
- No model, pricing, routing, or retention metadata older than 24 hours may
  authorize a paid run.
- No held-out, paid, 1,000-case, or 10,000-case execution occurs without its
  own explicit authorization.
- A failed release hard gate produces `Refine`, `Go Deeper`, `Drop`, or an
  explicit no-release decision; it is never hidden by the schedule.

The operational source is `docs/release-plan.md`; the product definition is
`research/00_admin/2026-08-18-real-world-product-scope.md`.
