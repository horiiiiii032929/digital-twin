# Evaluation result: aws-pilot-deployment-003

## Run identity

- Component: AWS pilot deployment and initial-state recovery boundary.
- Status: completed; final provisioning, activation and public checks passed.
- Date and owner: 2026-09-09; Codex, user-requested deployment.
- Revision: `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty working tree.
- Runtime: CDK library 2.268.0, CLI 2.1140.0, Linux amd64 containers.
- Reproduction: the [CDK guide](../../infra/cdk/README.md) and
  [manual verification procedure](../../tests/manual-aws-pilot-2026-09-09.md).
- Durable sanitized evidence, image digests and configuration hashes:
  [deployment-003.json](../../reports/aws-pilot/deployment-003.json).
- Predecessors: failed [001](aws-pilot-deployment-001-results.md) and
  [002](aws-pilot-deployment-002-results.md), retained without overwriting.

## Decision context

The [plan](../04_experiments/2026-09-09-aws-pilot-infrastructure-plan.md) retains
the qualified local single-host R1 control. This candidate hosts that release
on AWS, without replacing the database, model selection, or authentication.
The user selected Singapore, profile `digital-twin`, and no custom domain.

## Data, sample size and exact configuration

One initial administrator; no course sources or learner records. Four public
smoke trials are individually retained: two aborted at readiness with HTTP 504,
then two complete nine-case passes. The last pass followed redeployment and an
actual host reboot. No held-out quality dataset, prompt, random seed, provider
inference or human learning evaluation is involved. These cases test operational
boundaries; they cannot estimate an availability SLA.

The final configuration uses EC2 c7i-flex.large (2 vCPU, 4 GiB), a private
Singapore subnet, one NAT gateway, an encrypted retained 80-GiB gp3 volume,
CloudFront VPC origin and an AWS-generated HTTPS hostname. Origin ingress uses
the Singapore CloudFront managed prefix list `pl-31a34658`; no public instance
address, SSH, custom domain or Route 53 record is provisioned. Secrets Manager
supplies credentials. CloudWatch retains container logs for 30 days; daily EBS
backups are scheduled at 18:00 UTC with 14-day retention.

`infra/cdk/runtime/runtime.env` binds the final R1 profile, deterministic
generation, Luna policy-value planning and v2.1 graph. Experimental post-report
flags and proactive outreach remain off. The existing local project API key was
transferred directly to the runtime secret; a new administrator password was
generated there. Neither credential was emitted into logs or source files.

## Aggregate, slice and hard-gate results

| Check | Result | Scope |
| --- | --- | --- |
| CDK infrastructure assertions | 6/6 passed | Private host, storage, origin, secret/backup bindings, release selectors, asset exclusions |
| Existing authentication tests | 42 passed | Local application regression suite |
| Administrator bootstrap tests | 3 passed | No reset of existing administrator; no password in process arguments; probe failure refuses provisioning |
| Linux amd64 image builds | 2/2 built | API and web |
| Initial public trial | 504, aborted | Proxy configuration file unreadable |
| Proxy-fixed public trial | 504, aborted | Origin ingress still incorrectly used VPC CIDR |
| Origin-fixed public trial | 9/9 passed | HTTPS, login/session/logout, secure cookies and rejection cases |
| Post-redeploy/reboot public trial | 9/9 passed | Same credentials remained usable; logout still revoked access |
| Application backup/isolated restore | Passed | Schema 19; one identity matched; SQLite integrity check passed; zero source files |
| Host reboot | Passed | EBS remounted, Docker active, three containers running |
| Frontend delivery | Passed | Public HTML and referenced JavaScript returned 200 |
| Final CDK infrastructure diff | No differences reported | Standard CDK diff ignores a non-ASCII normalization difference |

## Operational results

Initial successful stack provisioning took 981.59 seconds, dominated by AWS
network/origin provisioning. Runtime-only updates followed without replacing the
host or data volume. The isolated initial-state backup/restore took 0.015
seconds. A single memory sample was 243.4 MiB API, 86.88 MiB worker and 11.19 MiB
web; these are not peak or workload measurements. The verified reboot time was
11:11:42 UTC. No recovery-time percentile is claimed.

Provider calls/tokens/inference cost: zero. AWS resource charges have not yet
been measured; Free Tier eligibility does not imply that all resources are free.

## Failures, corrections and validity

The first runtime activation succeeded locally but public readiness returned
504. Python archive extraction under `umask 077` left the Caddyfile at 0600,
unreadable by the unprivileged web container. The deployment now explicitly sets
0644 on this non-secret configuration only. Secrets remain private.

The second public trial still returned 504 because the VPC CIDR rule did not
admit CloudFront's origin-facing traffic. The AWS-managed origin prefix list
fixed this; the infrastructure regression now checks that specific binding.
Both failed trials are retained in the evidence JSON. They were valid failures,
not discarded measurements. The corrected deployment was reactivated to verify
the fixes are reproducible and the existing administrator is not reset.

## Decision

**Keep** this deployed initial-state pilot infrastructure. The app is available
at [its AWS HTTPS URL](https://d3cccbyk2qjxd6.cloudfront.net). No model/learning
quality profile is promoted. The local R1 composition remains the control and
fallback; the original single-host availability limitations remain.

## Limitations and follow-up

This result does not establish populated-course restoration, AWS snapshot
restoration, cross-AZ recovery, load capacity, notification delivery, or a
production SLA. Professor/student permissions passed the local regression suite;
the public smoke uses the initial administrator only. Use approved synthetic
courses for the next multi-role cloud acceptance run before importing sensitive
data or making broader availability claims.

## Learning notes

Successful CloudFormation provisioning and local container health are necessary
but insufficient. Verify the complete public route, real cookie authentication,
file permissions under the actual deployment umask, and restart persistence.
Keep every failed attempt so the operational decision remains reproducible.
