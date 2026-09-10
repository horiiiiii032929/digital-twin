# Office-hours integration verification

Use AWS profile `digital-twin` and region `ap-southeast-1` for every command.
Read the instance, schedule group, and schedule names from
`infra/cdk/cdk-outputs.json`. This procedure interrupts availability; run it
outside office hours with no active course work.

1. Run `npm --prefix infra/cdk run check` and inspect the CDK diff before deploy.
2. Run `aws scheduler get-schedule` for each deployed schedule, supplying its
   `--name` and `--group-name`. Check enabled weekday 09:00/18:00 schedules with
   `ScheduleExpressionTimezone=Asia/Singapore` and the intended instance input.
3. Create a uniquely named temporary schedule in the same group, copying the
   complete Stop schedule `Target` object. Use a future UTC `at(...)` expression
   at least 75 seconds ahead, timezone UTC, flexible window OFF, state ENABLED,
   and `ActionAfterCompletion=DELETE`. Use `aws scheduler create-schedule
   --cli-input-json` with those fields. Never copy credentials into its input.
4. Poll `aws ec2 describe-instances` until stopped (allow ten minutes). Scheduler
   has minute-level precision. Remove the temporary schedule if auto-deletion
   has not completed before proceeding. Record timestamps and failures.
5. Repeat with the Start target and a new future time. Confirm running, then
   allow the OS, persistent mount and containers to recover. Run
   `uv run python scripts/verify_aws_pilot.py` and retain all trial outcomes.
6. Confirm only the two recurring schedules remain. Reconcile the instance with
   current office hours: outside the window, call normal `aws ec2 stop-instances`
   and wait until stopped. Never terminate the instance or use forced stop.

The one-time tests exercise the same execution roles and EC2 targets as the
recurring schedules. They do not establish future cron delivery reliability,
load capacity, holiday behavior, or a service availability guarantee.
