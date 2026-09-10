# Evaluation result: aws-pilot-deployment-001

## Run identity

- Component: AWS deployment boundary; first infrastructure provisioning attempt.
- Status: failed; CloudFormation rolled back on backup selection creation.
- Date and owner: 2026-09-09; Codex, user-requested deployment.
- Code revision: `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`; dirty working tree.
- Reproduction: `npm --prefix infra/cdk run deploy -- --require-approval never`.
- Dependencies: Node 24.15.0, CDK library 2.268.0, CDK CLI 2.1140.0;
  Docker 28.5.1; Linux amd64 image targets.
- Generated artifacts: ignored `infra/cdk/.build-context/release-manifest.json`,
  `infra/cdk/cdk.out/`; local `/tmp/digital-twin-aws-deploy.log`.
- Successor: corrected backup binding and a new provisioning attempt are required.

## Decision context

The [predeclared plan](../04_experiments/2026-09-09-aws-pilot-infrastructure-plan.md)
asks whether the unchanged qualified local R1 composition can be hosted on AWS.
The control is local single-host Docker with persistent SQLite; the candidate is
the same topology on EC2/EBS with a CloudFront VPC origin. This is operational
qualification, not a comparison of model quality or cloud performance.

## Data and sample size

One initial CloudFormation provisioning attempt; no course corpus, user data,
or model prompt. Local tests use synthetic configuration and no network access
for the API smoke check. No calibration or held-out data is involved. A single
provisioning attempt can reveal integration defects but cannot estimate an SLA.

## Exact configuration

Singapore `ap-southeast-1`, named AWS profile `digital-twin`, EC2 t3.medium,
private subnet, one NAT gateway, retained encrypted 80-GiB gp3 data volume,
CloudFront-generated hostname, no custom domain, Secrets Manager runtime
configuration, 30-day container logs, intended 14-day daily EBS backup retention.
The initial backup selection incorrectly referenced a nonexistent JavaScript
`volumeArn` property, so its synthesized resource list was absent.
Qualified runtime selectors remain in `infra/cdk/runtime/runtime.env`; no
experimental component was promoted. No live provider request was made.

## Aggregate and slice results

| Candidate | Check | Result | Threshold |
| --- | --- | --- | --- |
| AWS candidate | API and web Linux amd64 images | Both built | Both build |
| AWS candidate | Offline API readiness | HTTP 200; all five checks true | HTTP 200 |
| AWS candidate | Initial infrastructure assertions | Six passed after assertion corrections | All pass |
| AWS candidate | Real backup resource creation | Failed: resource list empty | Successful creation |
| AWS candidate | Public host, role isolation, restore, rollback rehearsal | Not reached | All required before pilot acceptance |

## Hard gates

Provisioning failed. No successful cloud backup, public-host readiness,
application persistence or restore is claimed. Local image/configuration checks
do not override the failed deployment gate.

## Operational results

AWS created the CDK bootstrap and published both images, then began stack
creation. Backup returned HTTP 400: “Either 'ListOfTags' or 'Resources' section
must be non-empty.” No EC2 host was created in this attempt and no runtime was
activated. Model tokens/calls/cost: zero. AWS provisioning charges are not yet
measured. Application latency, host memory and restore time are not available.

## Failures and validity review

Failure category: integration, infrastructure configuration. JavaScript accepted
an undefined property; a resource-count-only backup assertion missed the absent
volume binding. The AWS failure is valid evidence and is retained. The fix
constructs the volume ARN explicitly, specifies a daily schedule, and asserts
the nonempty resource list and retention in the synthesized template.

## Decision

**Refine** the infrastructure candidate and retry after cleaning up empty
resources from this failed attempt. Keep the local release as the control;
no release profile change or public-host qualification follows from this run.

## Limitations and learning notes

Successful synthesis only shows that a template can be generated. Assertions
must inspect the actual persistence and backup bindings, and live provisioning
must validate AWS service contracts. A subsequent successful deployment still
needs synthetic auth, persistence, restore, and rollback acceptance before users
are invited.
