# Seven-persona roleplay demo

This pack adds seven fictional student accounts to the existing deployed demo.
Each can access Data Systems and Browser Security. Each starts with one actual,
current-time interaction in Data Systems; log in and continue the conversation.
The professor and student accounts from the original seed remain available.

The source code defines two six-persona research sets. This demo combines
`typical-engaged` from the newer set with the six historical personas. It is a
new seven-persona demo composition, not a claim that a historical experiment or
presentation evaluated these exact seven together.

| Persona | Login | Try next |
| --- | --- | --- |
| Engaged baseline | typical-engaged.persona@example.test | Explain why members can share a team reference |
| Fast learner | fast-learner.persona@example.test | Predict the join results for Ari, Bo and Cam |
| Slow learner | slow-learner.persona@example.test | Ask for one small step using just Ari |
| High forgetting | high-forgetting.persona@example.test | Recall the two key roles without looking |
| Misconception-prone | misconception-prone.persona@example.test | Reconsider whether every foreign key must be unique |
| Answer-seeking | answer-seeking.persona@example.test | Turn a graded-submission request into an allowed hint |
| Low receptivity | low-receptivity.persona@example.test | Ask for concise help, then stop when ready |

Passwords and fuller role cards are in the private local
`output/aws-pilot-seed/seven-persona-accounts.md`. The private resume state is
`output/aws-pilot-seed/persona-state.json`. Both remain ignored and mode 0600.
Use separate browser profiles or log out when switching roles.

## What is and is not seeded

The versioned [manifest](../tests/fixtures/seed_data/seven-personas-v1/manifest.json)
contains labels, synthetic openings and suggested follow-ups. All seven use the
same approved course release and audited tutor. Identity labels are for human
roleplay, not hidden system instructions that force the tutor to behave a
certain way. The app sees the actual submitted words and its ordinary history.

No hidden simulator learning rates, mastery probabilities, fabricated scores,
backdated conversations or notification consent are inserted. A forgetting
scenario is a fictional student's self-report, not a measured forgetting rate.
No personas run autonomous conversations while you are away. Outreach stays off.
The one-hour testing window and weekday office-hours schedules are unchanged.

## Apply, resume and verify

```bash
uv run python -m scripts.seed_pilot_personas
uv run python -m scripts.seed_pilot_personas --apply
uv run pytest tests/infra/test_pilot_seed.py -q
```

The first command prints a local plan. Apply requires the existing private
pilot mapping and an online server. It uses admin/professor/student APIs, creates
seven new credentials and fourteen memberships, and submits one starter per
persona. It checks that the original seeded published releases are still active.
A completed repeat verifies existing records without resetting passwords or
adding new starter turns. Local locking prevents concurrent imports of this pack.

Credentials are saved before invitation. Student turn request IDs are stable so
an interrupted response can recover a committed turn. Course changes or manifest
hash changes fail rather than silently retargeting the seed. A remote account,
conversation or turn that succeeds before its checkpoint is saved may require
inspection; this is not a distributed transaction. Do not delete the resume
mapping or use force/reset operations during ordinary retries.

The local staging integration checks sixteen total identities including the
original administrator, unchanged original credentials, seven persona histories,
fourteen persisted messages, course retention, repeat safety and cross-persona
privacy. Local wording is deterministic; live wording uses the deployed audited
route. Retain actual live responses, including withholding, as operational demo
evidence rather than claiming seven distinct learner models or teaching benefit.
