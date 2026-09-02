# Evaluation result: local-r1-governed-v2-1-release-qualification-002

## Decision

**Keep** the exact governed V2.1 local Compose release and retain T0 as the
immediate rollback. This is a qualified local release, not a hosted-production
or real-learning claim.

## Frozen identity

- Date: 2026-09-02
- Code revision: `b4d25faf317d90001376bfed843f26cac8aa390d`
- API image: `sha256:a44ea7c9a6098b9340e63d82bee154d9ec8c7996a5c0581d7568ac8978545a9b`
- Web image: `sha256:4722c937e88fd4dd0635f60c14b3fe172818118e764cb46edc72ce9cedc59478`
- Release profile SHA-256: `43da7e1bd1ae07343427e52f3e617ccdd5d49a1aa221fd6855d89d7ce527209d`
- Runtime: governed autonomous tutoring graph V2.1 with deterministic
  evidence-set generation, ambiguity-safe question-targeted evidence, complex-
  turn Terra planning, and T0 rollback
- Data: synthetic identities and open demonstration material only

## Method and root-cause corrections

The live qualification exercised invitation, sessions, course creation,
asynchronous PDF ingestion, policy and teaching-profile approval, publication,
a release-bound domain model, consented scheduled outreach, V2.1 tutoring,
original-region citations, and privacy-thresholded learning-gap review.

The first V2.1 journey exposed two product-contract defects rather than a model
quality failure. Region-aware ingestion supplied both a precise text region and
an explicit selected-text page fallback; the ambiguity gate incorrectly treated
the aggregate page as an independent competing claim. The graph then rendered a
valid `clarify` boundary through its operational-failure fallback. The fixes
prefer precise regions over explicit page fallbacks and render policy-owned
`clarify`, `abstain`, and `refuse` actions without a model or failure path.
Focused regressions were added before the final live run.

A second operational defect appeared during rollback: the inactive Terra
planner setting prevented T0 startup. Configuration now validates credentials
only for an active V2 planner, preserving the promised one-setting rollback.
The restart verifier also gained a bounded readiness wait and durable output for
resume evidence; it does not retry product or provider calls.

## Results

- Final local HTTPS journey: **25/25**.
- Restart persistence: **6/6**.
- Checksum-verified clean restore in a separate Compose project: **6/6**.
- T0 rollback: **3/3**.
- Governed V2.1 restoration: **3/3**.
- Live API p95: **5.755 ms** across 25 measured requests.
- Ingestion queue-to-complete: **1,080.021 ms**.
- Desktop and 390px professor/student visual QA: no console errors, horizontal
  overflow, or unlabeled button/input controls.
- External provider calls during the live operational journey: **0**; the
  deterministic call ledger remained inspectable.
- Backup SHA-256: `c48552fac031c3d6883542dda2770f44a78ce83bfdbb6d467b4eed9756e035a6`.

## Durable local evidence

The unrestricted operational artifacts remain ignored:

- `reports/generated/local-r1-v21-live-journey.json`
- `reports/generated/local-r1-v21-restart-journey.json`
- `reports/generated/local-r1-v21-restore-journey.json`
- `reports/generated/local-r1-v21-t0-rollback.json`
- `reports/generated/local-r1-v21-v2-restore.json`
- `reports/generated/local-r1-v21-runtime-backup.zip`

## Limitations

The system is qualified only on the development Mac through internal-CA HTTPS.
Synthetic/model-assisted evidence does not prove real-professor fidelity,
real-student usability, or improved learning. Durable public hosting, true
visual reasoning, and external human evaluation remain separate work.
