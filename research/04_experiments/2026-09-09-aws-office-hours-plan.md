# AWS office-hours scheduling plan

Question: can the existing pilot stop outside office hours and resume with the
same storage, authentication and URL, without adding a running scheduler host?

Control: the current continuously running EC2 pilot. Candidate: two EventBridge
Scheduler universal targets invoking StartInstances and StopInstances for that
single instance, weekdays at 09:00 and 18:00 in Asia/Singapore. An optional hours
question was asked; use this stated default absent a user adjustment. AWS direct
API targets avoid a custom Lambda implementation for these supported operations.

Pre-run gates: exactly two enabled, timezone-aware schedules; no flexible delay;
only the selected host may be started/stopped; no forced shutdown or termination;
bounded retries cannot execute yesterday's transition; failures go to an encrypted
dead-letter queue; existing volumes and release selectors remain unchanged.
Synthetic CDK assertions cover the schedule and IAM contract. Inspect the CDK
diff before updating AWS and inspect the actual saved schedules afterward.

Operational verification: outside office hours, test a temporary one-time
Scheduler stop followed by a temporary one-time Scheduler start using the same
targets and execution roles. Verify host state and HTTPS/authentication after
start. Remove those temporary schedules and stop the host again to leave it in
the requested off-hours state. If Scheduler integration fails, retain the failed
result and correct the configuration before calling scheduling operational.

No course data or provider inference is involved. Preserve EBS and credentials.
One transition in each direction checks the integration, not long-term schedule
reliability or load capacity. Record event timing, failures and state results;
the existing URL, database and password must survive. Account for continued NAT,
storage and backup charges separately from EC2 compute savings. An ordinary
EC2 stop is graceful; running requests can still be interrupted at closing time.
