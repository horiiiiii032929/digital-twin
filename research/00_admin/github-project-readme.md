# Course Digital Twin Release

Status date: 2026-08-30

Issue #127 is the active P0 research item at `In Progress / Refine`. AFQC-100
completed the exact API-first M0–M6 comparison on 300 cases. No method passed:
the best result was 38.7% complete evidence@3 and 44.7% Recall@5, boundary
accuracy was 96.9%, and one severe ambiguity release occurred. The 83-call,
USD 0.0593379 authority is revoked. The next Project transition is one joint
source-registration, reference-question, and retrieval-matching redesign on a
fresh source-disjoint tranche. The qualified local R1 is unchanged.

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
  the retrieval-index successor now covers 717/717 audited files and 105/105
  frozen entrypoints.
- Factual quality: #110 remains engineering-scale history. #127 is the active
  leakage-free actual-product evaluation. AFQC-094 preserves the finite
  program as invalid after local Qwen3 materialization failed twice before any
  provider or product call. AFQC-095 now selects an API-first retrieval
  successor: BM25, direct OpenAI small/large dense and hybrid retrieval,
  deterministic hierarchy, and bounded API reranking were compared on 300
  development cases. Source registration, vectors, citation ranges, hidden
  gold, and scoring stayed repository-owned. The result is valid `Refine`, no
  method is selected, and 500+100 plus sealed 10,000+1,000 remain closed.
- Professor fidelity: fixed C0–C3 and explicit/inferred profile contracts are
  build-ready; professor guidance and calibration are pending.
- Deployment: local/container checks passed; public host/domain, trusted TLS,
  target-host restore, and walkthrough remain blocked.
- Multimodal grounding: region-aware foundations and original-region citations
  are retained, but no multimodal retrieval profile is selected; text remains
  the fallback.

## Release-critical order

1. Keep release goal #8 `In Progress` as the parent.
2. Preserve #127's completed API-first comparison and its unfavorable result.
3. Build one joint structured-source, context-complete question, and retrieval
   successor, then confirm it on a fresh source-disjoint tranche. Only its pass
   may prepare 500+100; only a complete development pass may prepare sealed
   10,000+1,000 execution.
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
| Joint source/question/indexing successor and fresh confirmation | Passing #127 retrieval-method decision |
| Passing fresh #127 result plus successor authorization | #127 T0 500+100 development execution |
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
