# Course Digital Twin Release

Status date: 2026-08-28

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
  checkpoint 005 now covers 644/644 audited files and 96/96 frozen entrypoints.
- Factual quality: #110 remains engineering-scale history. #127 is the active
  leakage-free product evaluation. Its OpenAI-only checkpoint first qualifies
  GPT-5.4 on 40 controls, then conditionally runs 500 candidate and 100 control
  cases. AFQC-050 authorized this path once, but both calibration attempts
  stopped after their first exact GPT-5.4 batch on evaluator-contract
  inconsistencies. AFQC-052 revokes authority; the 500+100 product run and
  sealed 10,000 cases remain unopened. AFQC-055 preserves calibration 004 as
  invalid after three exact GPT-5.4 calls because one clarify vote omitted its
  mandatory boundary reason. Authority is revoked, hidden labels stayed closed,
  and AFQC-056 replaces it with deterministic-primary checkpoint 004. AFQC-058
  preserves its valid wording-stage Refine result: 452/500 accepted variants,
  48 canonical fallbacks, 50/50 exact calls, USD 0.555499, and zero T0 product
  calls. AFQC-059/060 reuse that immutable mixed package and build product-only
  checkpoint 005 with no new wording stage. Its five network-free outcomes pass;
  the 500+100 product run and sealed 10,000 cases remain unauthorized.
- Professor fidelity: fixed C0–C3 and explicit/inferred profile contracts are
  build-ready; professor guidance and calibration are pending.
- Deployment: local/container checks passed; public host/domain, trusted TLS,
  target-host restore, and walkthrough remain blocked.
- Multimodal grounding: region-aware foundations and original-region citations
  are retained, but no multimodal retrieval profile is selected; text remains
  the fallback.

## Release-critical order

1. Keep release goal #8 `In Progress` as the parent.
2. Separately authorize checkpoint 005's 500-case candidate plus paired
   100-case control; authorize the sealed 10,000 cases only after a complete
   development pass.
3. Complete #105 from that leakage-free evidence and select the production
   grounding gate.
4. Preserve T0 and run #107's separately frozen T0/T1 confirmation.
5. Complete #132 and #134; keep Discord
   network delivery disabled until its privacy and operations gates pass.
6. Select a public host/domain and finish #88's trusted-HTTPS rehearsal.
7. Calibrate #24 professor behavior separately from factual/citation hard
   gates.
8. Run #9 and #25 against the same immutable deployed revision.
9. Run #10 only after the human-participant approval boundary is satisfied.
10. Package the final evidence, demo, report, and rollback/no-release decision
   in #13.

## Current blockers

| Blocker | Unblocks |
| --- | --- |
| Explicit authorization for product checkpoint 005 | #127 T0 development execution |
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
