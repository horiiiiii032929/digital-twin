# Course Digital Twin Release

Status date: 2026-08-30

Issue #127 is the active P0 research item at `In Progress / Refine`. AFQC-105
selected atomic M2 retrieval, but AFQC-109's actual-product 500+100 run validly
failed with 44.25% fully grounded success, 89% boundary accuracy, and five
unsafe ambiguity releases. AFQC-110 built the single finite action-router and
targeted-atomic successor, but AFQC-111/112 exhausted its two permitted
execution attempts without reaching product case 1. Attempt 001 made zero
calls; attempt 002 completed 15 embeddings for USD 0.00057488 and then failed a
missing `binding_id` runtime contract. Authorization is revoked. The sealed
10,000 cases remain unopened and the qualified local R1 is unchanged.

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
- Proactive tutoring: #134 restores opt-in asynchronous initiation as a core
  product track. The deterministic private in-app vertical slice is build-only;
  external Discord delivery and real-student use remain disabled.
- Repository: PRs #130, #133, and #135 are merged. The correctness inventory
  and execution freeze remain active. PR #136 merged the direct OpenAI base;
  the action-router successor now covers 758/758 audited files and 116/116
  frozen entrypoints.
- Factual quality: #110 remains engineering-scale history. #127 is the active
  leakage-free actual-product evaluation. Atomic retrieval passed
  prospectively, but its first T0 product run validly failed. AFQC-110 has now
  terminated operationally invalid after its sole correction. No new quality
  estimate exists; authority is revoked and final 10,000+1,000 is unopened.
- Professor fidelity: fixed C0–C3 and explicit/inferred profile contracts are
  build-ready; professor guidance and calibration are pending.
- Deployment: local/container checks passed; public host/domain, trusted TLS,
  target-host restore, and walkthrough remain blocked.
- Multimodal grounding: region-aware foundations and original-region citations
  are retained, but no multimodal retrieval profile is selected; text remains
  the fallback.

## Release-critical order

1. Keep release goal #8 `In Progress` as the parent.
2. Preserve #127's completed retrieval Keep and actual-product Refine evidence.
3. Preserve AFQC-111/112 and make one explicit harness/method decision. Do not
   retry AFQC-110 or open sealed 10,000+1,000 execution.
4. Complete #105 from that leakage-free evidence and select the production
   grounding gate.
5. Preserve T0 and run #107's separately frozen T0/T1 confirmation.
6. Complete #132 and #134; keep Discord
   network delivery disabled until its privacy and operations gates pass.
7. Select a public host/domain and finish #88's trusted-HTTPS rehearsal.
8. Calibrate #24 professor behavior separately from factual/citation hard
   gates.
9. Run #9 and #25 against the same immutable deployed revision.
10. Run #10 only after the human-participant approval boundary is satisfied.
11. Package the final evidence, demo, report, and rollback/no-release decision
   in #13.

## Current blockers

| Blocker | Unblocks |
| --- | --- |
| Explicit post-AFQC-112 harness/method decision | A new valid #127 actual-product checkpoint |
| Professor profile-authoring response | Fidelity calibration |
| Leakage-free #127 development/final result | Production answerability-gate selection |
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
