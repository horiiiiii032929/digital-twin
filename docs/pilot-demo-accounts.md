# Deployed synthetic demo

The [seven-persona roleplay pack](seven-persona-demo.md) adds seven independent
student accounts alongside the original eight demo identities below.

The Singapore pilot now contains two professors, six student identities, three
courses, two published releases and two approved source-bound concept models.
The original administrator is preserved. Four approved Markdown documents were
ingested; a fifth governance document is registered as pending review. Ten course
memberships include one intentionally inactive membership. Finn is deliberately
revoked for the login-denied scenario.

| Login | Role | Use |
| --- | --- | --- |
| maya.professor@example.test | Professor | Data Systems; draft Release Governance onboarding |
| daniel.professor@example.test | Professor | Browser Security |
| alex.student@example.test | Student | Data Systems walkthrough |
| bea.student@example.test | Student | Graded-work request walkthrough |
| chris.student@example.test | Student | Switch between both published courses |
| dina.student@example.test | Student | Browser Security walkthrough |
| eli.student@example.test | Student | Login works; course membership inactive |
| finn.student@example.test | Student, revoked | Login is intentionally denied |

Generated passwords are in the private local `output/aws-pilot-seed/demo-accounts.md`
and resume state in `output/aws-pilot-seed/state.json`. Both are ignored by Git;
the directory is 0700 and these files are 0600. They contain real credentials.
The runtime Secrets Manager secret continues to hold the existing administrator
credential. No invitations or emails were sent.

Use [the deployed app](https://d3cccbyk2qjxd6.cloudfront.net) during weekday
09:00–18:00 Singapore time. Outside those hours it is stopped. See the
[CDK operations guide](../infra/cdk/README.md) for temporary manual access.
Use separate browser profiles or log out when switching roles.

## Walkthrough and limitations

As Alex, ask “Why can two members have the same team_id?” As Dina, ask “Why is
cookie authentication alone not a complete CSRF defense?” Both returned cited
notes in the live verification. Existing conversations from verification are
real synthetic service interactions, not human student activity or fabricated
learning results.

The deployed demo now uses the presentation’s audited V19 Luna tutor, verified
in [two live two-turn histories](../research/05_evaluation/aws-presentation-route-001-results.md). The
[explicit demo override](../research/05_evaluation/profiles/aws-presentation-demo-v1.json)
keeps the deterministic R1 composition available for rollback. The observations
below describe the initial deterministic seed verification, before that change.
Those earlier responses often quoted a whole source chunk. A short “What does HttpOnly do?” request conservatively
abstained despite relevant source material; a broad security request retrieved
the outline instead of a substantive explanation. These unfavorable outcomes
are retained in the [acceptance result](../research/05_evaluation/aws-demo-seed-001-results.md).
Neither seeding nor selecting the presentation route qualifies a new model or claims teaching quality. Built-in policy
previews still use historical CSRF templates; their acceptance is a synthetic
workflow demonstration, not course-specific factual evaluation.

## Reproduce and resume

Review the [seed design](seed-data-design.md), manifest and domain specifications.
Back up and verify the target before applying. The tool is intentionally bound
to this deployed pilot URL and AWS profile `digital-twin`, Singapore region.

```bash
uv run python -m scripts.seed_aws_pilot
uv run python -m scripts.seed_aws_pilot --apply
# Inspect output/aws-pilot-seed/*-review.json before accepting demo workflow previews.
uv run python -m scripts.seed_aws_pilot --apply --approve-demo-reviews
uv run python -m scripts.verify_pilot_seed
# Optional: creates new synthetic conversations and invokes the configured tutor.
uv run python -m scripts.verify_pilot_seed --tutor
uv run pytest tests/infra/test_pilot_seed.py -q
```

The first command only validates and prints a plan. Apply provisions identities,
courses, source jobs, onboarding sessions and teaching profiles through normal
APIs. The review flag records explicit demo review decisions, runs publication
preflight, publishes, and binds source-backed concepts through the professor API.
Since the API has no inactive-membership write endpoint, finalization uses SSM
and the domain repository only for Eli's inactive membership. It refuses to
replace an existing active membership. The revoked account uses the admin API.

Resume state preserves generated credentials and returned account IDs. Repeating
completed work does not reset passwords or duplicate releases. Changed manifest
or domain hashes and conflicting records stop the importer. Concurrent local
runs use a file lock. This is not a distributed transaction: if a remote create
succeeds and checkpoint writing fails, inspect the remote object before adopting
it; some interrupted onboarding/profile creates can leave orphan drafts. Retain
the private mapping when moving between machines. Do not run after-hours without
arranging temporary access; the seeder never modifies the schedule.

Pre-seed and populated backups are on the host under
`/opt/digital-twin/backups/`, mode 0600. Both were restored into disposable paths
and checked; the populated restore preserved all nine identity hashes. Existing
scheduled EBS backups remain enabled. These local archives share the host's
failure domain and are not a replacement for off-host backups.
