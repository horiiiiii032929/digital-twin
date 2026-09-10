# Evaluation result: walkthrough-codefix-004

## Decision and run identity

**Keep locally** the decision-preserving UI repairs. No deployment, algorithm replacement or evaluation-profile promotion. Date: 10 September 2026. Revision `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty. The [machine record](records/walkthrough-codefix-004.json) retains source hashes, frozen-file fingerprints and all 18 audit comparisons. [Prospective plan](../04_experiments/2026-09-10-walkthrough-codefix-plan.md).

Question: can primary chat remain usable when optional metadata stalls or fails, without changing tutor requests or decisions? Control is the pre-edit dirty hook retained under `output/browser-qa/walkthrough-codefix-004/`; the preceding investigation reproduced both failures. Candidate completes primary operations independently, scopes asynchronous reads and exposes read-only retry controls. No competing algorithm is proposed.

## Changes and hard gates

H-001: completed sends now clear sent drafts/pending IDs and unlock the composer before optional evidence refresh. Synchronous submit protection prevents same-render duplicate clicks; failed sends retain IDs for manual retry. H-002: validated saved conversations display before evidence/citation reads. Auxiliary failures never enter the primary conversation fallback or create a new conversation. Successful citations merge by message ID without replacing authoritative turn citations or user selection. Request sequencing and workspace invalidation discard stale reads, including unmounted accounts (the app keys student workspaces by account ID).

Separate frontend metadata states distinguish loading, unavailable and empty evidence; retained observations are identified during refresh/failure. Legacy previews truthfully describe fixed CSRF and generic synthetic content without changing their acceptance gates. No backend API or persistence changes.

All 328 fingerprinted backend, release-profile and dataset files remained byte-identical. The 18 existing audit controls retain identical prior behavior. Evaluation splits, metrics, scoring, thresholds, algorithms, prompts, validators and approval rules were not edited. New QA records are appended, not substitutes for historical results.

## Data, configuration and reproducibility

Nine new deterministic hook cases extend the existing synthetic fixtures in `apps/web/src/hooks/use-student-workspace.test.ts`: completed send with stalled evidence/duplicate click; stalled history metadata; partial metadata failures and retries; failed-send request ID; successive-turn evidence race; cross-course race; delayed citations versus new turn; retry/unmount race; same-course conversation race. These targeted branch tests use no stochastic seed or train/test split and do not estimate reliability rates. No real learner data or provider output was collected.

```sh
npm --workspace apps/web test -- --run
npm --workspace apps/web run lint
npm --workspace apps/web run build
uv run pytest -q tests/api tests/services tests/test_audited_instruction_generation.py tests/test_final_response_audit.py tests/test_contract_repair_generation.py
uv run python -m scripts.verify_slide_codefix --control infra/cdk/cdk.out/asset.47bdf176a935ba44e6d33c0417079155fd5e41be75259c79942573db8793aa92/src/digital_twin/generation/final_response_audit.py --output output/browser-qa/walkthrough-codefix-004/audit-comparison.json --run-id walkthrough-codefix-004 --dataset decision-preserving-codefix-v1
npm run check
```

The browser used ordinary UI/API code, a private synthetic SQLite fixture and deterministic defaults at `http://localhost:5174`. Local-only fault middleware delayed evidence by 45 seconds and returned 503 for evidence/citation reads. The localhost proxy substitutes a synthetic allowed HTTPS Origin to emulate TLS termination; this is not a production TLS/security verification. No production config was changed. The fixture and Vite configuration remain ignored under the output directory and app cache. To repeat, use a fresh fixture data directory: its published releases are immutable, so rerunning seed creation against existing state is rejected. Start the retained local app with `PYTHONPATH=. uv run python output/browser-qa/walkthrough-codefix-004/local_app.py` and its cached Vite config. Ingestion was processed once using the existing `scripts.run_ingestion_worker --once` with that fixture's explicit data/database paths; no autonomous outreach worker ran.

## Verification results

| Check | Result |
| --- | --- |
| Frontend suite | 98 passed in 18 files; 727 ms total, 223 ms test execution |
| API/services/accounting | 410 passed in 22.22 seconds; existing dependency and backup-fixture warnings |
| Lint | Pass, no warnings after cleanup-reference adjustment |
| Production build | Pass; existing >500 kB chunk warning retained |
| Audit control comparison | 18/18 behavior-identical |
| Infrastructure checks | 7 passed |
| Repository-wide check | Blocked at two pre-existing absolute Desktop presentation links; later stages not claimed as executed by this command |
| Frozen source/config fingerprints | 328 checked, zero changes |

The component suites and comparisons overlap; do not sum them as unique coverage. Real model calls, tokens, model cost and AWS calls: zero. Memory and production latency were not measured. Statistical uncertainty is not meaningful for these targeted deterministic assertions.

## Browser walkthrough

| Check | Evidence/result |
| --- | --- |
| Identity/nonblank/overlay | Correct student and professor titles/routes; meaningful screens; no framework overlay |
| Completed-send recovery | Second turn accepted while evidence from completed turn was delayed 45 seconds |
| Saved-history recovery | Three-turn history remained visible despite injected evidence/source 503s; editable composer and enabled Send with a draft |
| Read-only retries | Both error banners disappeared after recovery without additional tutoring requests |
| Course navigation | Selected Synthetic systems course survived setup → delivery roundtrip |
| Source ingestion | Professor uploaded synthetic notes; one-shot ingestion completed with 1 chunk; publication remained blocked |
| Preview wording | New synthetic-example explanation visible; approval not bypassed |
| Check-ins | Existing consent on, pause, resume, off controls worked; worker stayed disabled |
| Account isolation | Student B saw only Synthetic policy course and no student A history; student A's three-turn history restored on return |
| Responsive/console | Desktop 1280×720 and mobile 390×844 recovery controls visible; sampled error/warning logs empty |

Screenshots: `output/browser-qa/walkthrough-codefix-004/recovery-desktop.png` and `recovery-mobile.png`. Browser evidence was captured through CUA, including its supported browser locators and screenshots. No external Playwright fallback was used. The synthetic provider path returned three safe no-evidence replies, so positive citation-detail rendering and live model quality are not certified by this browser run. Citation association and recovery are covered by hook tests. The initial 45-second request models delay; rejection tests and browser 503s model unavailable reads, not a full network disconnection.

## Failures, limitations and follow-up

Retained local setup failures: staging rejected an HTTP Origin; a Vite config outside the app could not resolve workspace plugins; reseeding the first fixture directory rejected immutable release changes. Corrected only the isolated test setup, using a fresh directory and local proxy config. An account-menu role locator failed because the browser exposed the control as generic; CUA accessibility navigation succeeded. These are not newly fixed application defects. Earlier lint warnings about cleanup refs were resolved; initial and final logs retained.

B-001, B-006, B-007, B-008 and B-009 remain decision/quality limitations. B-003's misleading explanation is clarified, but course-specific preview generation/publication design remains unresolved. Earlier B-002/B-004/B-005 repairs remain intact; local metadata fixes remain undeployed. No historical report or failed evaluation was overwritten. The [coverage supplement](../../tests/manual/walkthrough-codefix-004-coverage.md) records what this run adds without claiming all 106 cases passed. AWS remains paused; no guarantee of zero bugs or diagnosis of the historical AWS hang is made.
