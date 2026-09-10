# AWS seven-persona demo seed 001

Decision: **Keep for synthetic manual demonstration**, with no research or release promotion. Seven additional student accounts are live on the existing Singapore pilot. The selection combines the typical-engaged baseline with the six original simulator labels; it is not a historical seven-persona experiment.

## Configuration and evidence

- Run: `aws-seven-personas-001`, 2026-09-09; revision `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty workspace. Exact final seed/test/manifest hashes are in the [sanitized machine-readable evidence](../../reports/aws-pilot/seven-personas-001.json).
- [Prospective plan](../04_experiments/2026-09-09-seven-persona-seed-plan.md), [versioned synthetic pack](../../tests/fixtures/seed_data/seven-personas-v1/manifest.json), [manual guide](../../docs/seven-persona-demo.md).
- Existing `audited-presentation-v1` route, candidate `v19-luna-luna-medium`: Luna low generation and medium final audit. The deterministic control remains available; no runtime configuration was changed by this seed.
- Only fictional openings and the existing approved synthetic Data Systems corpus were used. Each account has Data Systems and Web Security memberships. No real student data, fabricated assessment scores, backdated forgetting history, notification consent, or simulator parameters were inserted.
- One real starter interaction per persona provides operational coverage of the seven requested roles. This sample cannot estimate teaching effectiveness, persistence of personality, or population-level effects; no statistical quality claim is made.

## Gates and observations

All seven logins, fourteen course memberships, seven persisted conversations and fourteen messages passed. The first persona was denied access to the other six conversations. The final repeat preserved all seven password hashes, conversation IDs, message counts and starter responses, with no additional generated turns. Local integration checks passed: `uv run pytest tests/infra/test_pilot_seed.py -q` (2 tests), including local prepare/publish, persona seed/repeat, identity preservation, privacy and manifest drift protection.

The engaged baseline received a focused question. The fast learner moved to predicting a join result; the beginner and returning learner received explanations and checks. The misconception case corrected the uniqueness claim. The answer-seeking case returned `redirect-graded-work` and offered a hint instead of a completed submission. The low-receptivity opening received an explanation and a quick check; its label does not secretly modify the tutor policy. These are inspected responses, not independently scored learning outcomes. Existing proactive outreach remains disabled.

Starter latency ranged from 10.286 to 54.063 seconds (median 11.788). Slow-learner and misconception cases took 44.234 and 54.063 seconds, which remains a manual-demo limitation. Returned generation/audit traces total 36,464 input and 13,729 output tokens, approximately $0.023768. Planner overhead is not aggregated and AWS charges are excluded; these are trace estimates, not billing totals. Memory was not measured because this changes seed content, not the runtime architecture.

## Retained failure and recovery

The initial seed completed successfully. The first repeat verified all seven accounts and saved starters, then its redundant extra login for the privacy check received HTTP 429 (`rate_limit_exceeded`). This is an operational verification failure. The final script reuses an already authenticated student client; a subsequent complete repeat passed with the rate limiter unchanged. Local logs remain at `/tmp/digital-twin-persona-live.log`, `/tmp/digital-twin-persona-repeat.log` and `/tmp/digital-twin-persona-repeat-final.log`; durable sanitized evidence records the failure. The final repeat also verified the exact original published release IDs.

A pre-seed backup succeeded through SSM command `c574e972-2a1a-4f7a-abb2-5c1c22365197`, schema 19 and eight data files, saved on the host at `/opt/digital-twin/backups/pre-seven-personas-20260909.zip`. No restart or deployment occurred. The user's existing stop schedule at 21:35:12 Singapore on September 9 was still enabled after verification.

Credentials and resume checkpoints are ignored local files under `output/aws-pilot-seed/`; the credential sheet is mode 0600. Reproduce with `uv run python -m scripts.seed_pilot_personas` for a read-only plan, or `--apply` for the authorized existing pilot. The latter requires the original private seed checkpoint and AWS `digital-twin` profile. Avoid frequent repeated login verification during manual testing because the normal rate limit applies.
