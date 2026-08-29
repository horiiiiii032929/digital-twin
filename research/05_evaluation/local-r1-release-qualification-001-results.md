# Evaluation result: local-r1-release-qualification-001

## Run identity

- Date: 2026-08-29
- Implementation revision: `c235e5633d58191cf10bca797dbc669814037b85`
- API image: `sha256:f82047ad5c6c59b176f6b479a16e652dda2593cb4dc8a301e8e309304bb54a9f`
- Web image: `sha256:7c13df6cd830238358dfdaf4dbee535fd8bdbfed3aed2d6b10551142f4f024e3`
- Environment: isolated local Docker Compose through internal-CA HTTPS
- Data boundary: synthetic accounts and open demonstration evidence only
- Generator: `deterministic/v1`; zero external model calls
- Tutoring mode: bounded T1 graph with one-setting T0 rollback

## Decision question

Does one immutable local R1 revision complete the invite-only professor and
student workflows safely through HTTPS, survive restart and clean restore, and
retain an immediately verified T0 rollback?

## Method

A fresh Compose project on `https://localhost:9443` ran the API, ingestion
worker, outreach worker, and web/Caddy images. The live verifier created only
synthetic accounts and material, then exercised invitation and sessions,
course creation, asynchronous ingestion, professor policy and teaching-profile
approval, publication, student outreach consent, professor-scheduled cited A0
outreach, T1 tutoring, original citation-region access, and privacy-thresholded
learning-gap review.

The same project was restarted and rechecked. A checksum-verified schema-v12
backup containing seven data files was then restored into a fresh Compose
project and rechecked. Finally, the qualification project was switched to T0
and back to T1 using the single runtime setting, with a new grounded turn
checked in each mode.

The first backup command wrote to container temporary storage and could not be
copied afterward. It changed no durable data. The procedure was corrected to
write atomically through an ignored host-mounted evidence directory before the
successful backup and clean restore.

## Results

- Clean live HTTPS journey: **24/24 passed**.
- Full-service restart: **6/6 passed**.
- Checksum backup and clean restore: **6/6 passed**.
- T0 rollback mode: **3/3 passed**.
- Restored T1 mode: **3/3 passed**.
- Live API p95 during the clean journey: **7.017 ms** across 25 requests.
- Ingestion queue-to-complete: **543.938 ms**.
- Repository gate: **1,221 Python tests and 47 frontend tests passed**, with
  frontend lint/build, active execution freeze, and **696/696 audited files**.
- Provider calls, tokens, and cost: **zero by release configuration**.

## Decision

**Keep** the exact revision as the qualified local R1 for the Sunday boundary.
T1 is the local default and T0 is the immediate rollback. Issues covering the
local learning-gap and A0 outreach workflows may close as completed.

The result does not close durable-host deployment, real professor fidelity,
external usability, learning outcomes, true visual reasoning, or the sealed
10,000-case actual-product evaluation.

## Generated evidence

The ignored operational artifacts are retained locally:

- clean journey: `reports/generated/local-r1-final-live-journey.json`;
- verified backup: `reports/generated/local-r1-final-runtime-backup.zip`,
  SHA-256 `7a4d2de66cc6f587a08404c8283ced1cfe48f812163de7bb85c1af39c597807e`;
- professor walkthrough: `output/playwright/local-r1-final-professor-walkthrough.webm`,
  SHA-256 `255b6d50f804afcbe305141b5e4cca751d11784315aeff15ab66f1fe9cdd53a3`;
- student walkthrough: `output/playwright/local-r1-final-student-walkthrough.webm`,
  SHA-256 `dfc9f420fd683dcdf22842c3dcf93172f9316023d924cb11546470bb882c8e97`.
