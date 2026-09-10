# Evaluation result: aws-office-hours-001

## Run identity and decision

**Keep** weekday office-hours scheduling for the deployed initial-state pilot.
Date: 2026-09-09. Owner: Codex, user-requested deployment. Code revision:
`9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty working tree. Source hashes,
saved AWS schedules and observed timestamps are in the sanitized
[evidence](../../reports/aws-pilot/office-hours-001.json).

The [prospective plan](../04_experiments/2026-09-09-aws-office-hours-plan.md)
compares the continuously running EC2 control with direct EventBridge Scheduler
EC2 API targets. The candidate avoids a custom Lambda or running scheduler.
Reproduce using the [manual procedure](../../tests/manual-aws-office-hours-2026-09-09.md)
and [CDK guide](../../infra/cdk/README.md). No model or learning-quality profile
is changed; the local R1 composition remains the application fallback.

## Configuration and data

AWS account 030334071887, profile `digital-twin`, region `ap-southeast-1`.
Two enabled schedules start the existing instance at 09:00 and stop it at 18:00,
Monday–Friday in Asia/Singapore. No flexible window; two retries maximum with
five-minute event expiration. Each execution role permits its single EC2 action
on only this instance and trusts this account's schedule group. Failed delivery
goes to an encrypted SQS queue and a CloudWatch alarm without notifications.

Dataset: the initial administrator and synthetic authentication rejection cases;
no course corpus, learner data, provider inference, prompt change or random seed.
One stop/start cycle tests the operational integration; it cannot estimate
long-term failure probabilities or an availability SLA. Existing EBS storage,
credentials, private host, CloudFront URL and release selectors are preserved.

## Results and hard gates

| Gate | Result |
| --- | --- |
| CDK assertions | 7/7 passed, including schedule/IAM contract |
| Deployment | UPDATE_COMPLETE; 102 seconds |
| Existing resource changes | No host or volume replacement; final CDK diff reports zero differing stacks |
| Saved schedules | Two enabled weekday schedules, expected timezone and exact instance targets |
| Actual scheduled stop | Scheduled 11:24:20 UTC; stopping observed 11:25:11; stopped 11:25:27 |
| Actual scheduled start | Scheduled 11:26:43 UTC; running observed 11:27:03 |
| Post-start public authentication | 9/9 passed on first trial using existing administrator credentials |
| Temporary schedule cleanup | Both removed; only the two recurring schedules remain |

The temporary one-time schedules used the deployed recurring targets and roles
in the same schedule group. Times are observations with approximately 15-second
polling, not exact API execution timestamps. Minute-level delivery precision
explains the interval after the scheduled second. No failed integration trial
occurred in this run. Prior deployment failures remain in their separate records.

HTTPS readiness, anonymous rejection, synthetic-header rejection, cross-origin
login rejection, administrator login, cookie flags, authenticated session,
logout and revoked-session rejection all passed. This demonstrates persistence
of the initial administrator across an actual EC2 stop/start. It does not test
populated-course recovery. Provider calls and tokens: zero. Memory and actual AWS
billing were not measured in this scheduling run.

## Final operating state and limitations

After the test, the host was stopped for the evening; the next regular start is
2026-09-10 at 09:00 Singapore time. The site returns an origin error while off.
Startup takes time after the 09:00 trigger; there is no public-holiday calendar.
These are timed transitions, so a manual after-hours start requires a manual stop
or the next weekday stop event. Requests still running at 18:00 may be interrupted.

Stopping reduces EC2 compute usage, but provisioned NAT, EBS, backups and other
retained resources still incur charges. No dollar saving or total-cost claim was
measured. Failure notification delivery, recurring cron reliability across
multiple days, high availability and load capacity remain untested.
