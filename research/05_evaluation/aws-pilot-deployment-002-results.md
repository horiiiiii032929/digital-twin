# Evaluation result: aws-pilot-deployment-002

## Run identity

- Component: AWS deployment boundary, second provisioning attempt.
- Status: failed; valid account-policy rejection followed by rollback.
- Date and owner: 2026-09-09, Codex, user-requested deployment.
- Revision: `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty working tree.
- Reproduction: `npm --prefix infra/cdk run deploy -- --require-approval never`.
- Versions: CDK library 2.268.0, CLI 2.1140.0; Linux amd64 images.
- Generated artifact: local `/tmp/digital-twin-aws-deploy-002.log` and ignored
  `infra/cdk/cdk.out/`.
- Predecessor: [deployment 001](aws-pilot-deployment-001-results.md).

## Decision context, data and exact configuration

The [original plan](../04_experiments/2026-09-09-aws-pilot-infrastructure-plan.md)
and unchanged local R1 control apply. This was one provisioning attempt in
Singapore using profile `digital-twin`, with no course corpus, learner data,
calibration split, model call or prompt. A single attempt measures integration
feasibility, not availability or learning effects.

The candidate retained t3.medium, 80-GiB encrypted gp3 EBS, private networking,
one NAT gateway and CloudFront VPC origin. It corrected the prior backup failure
by explicitly binding the volume ARN and setting daily backups at 18:00 UTC
with 14-day retention. No algorithm or model replacement was proposed.

## Results and hard gates

| Gate / slice | Result |
| --- | --- |
| Corrected backup selection | Created successfully |
| Infrastructure assertions | Six passed |
| Existing authentication regression suite | 42 passed |
| Host creation | Failed: t3.medium not eligible under this account's Free Tier plan |
| Runtime activation, public auth, persistence, restore | Not reached |

AWS returned HTTP 400 on EC2 creation: “The specified instance type is not
eligible for Free Tier.” No host was launched. AWS's read-only eligibility API
listed c7i-flex.large as eligible, with two vCPUs, 4,096 MiB memory and x86_64;
the offerings API confirmed all three Singapore availability zones.

## Operational results and validity review

Category: operational/account entitlement. This is not an application failure
or invalid experiment. Model calls, tokens and inference cost were zero.
AWS infrastructure charges, host performance and recovery time were not measured.
The unused volume, empty vault and empty log group were deleted after rollback.
The populated runtime secret was preserved and selected through the ignored
`runtimeSecretArn` CDK context; credential values were never emitted.

## Decision and limitations

**Refine**: use the account-eligible c7i-flex.large while preserving the planned
CPU/memory envelope and image architecture. Keep the local release profile;
there is no quality promotion or cloud-pilot acceptance. The successor must
provision the host and verify HTTPS/authentication, then separately rehearse
application data backup and recovery. Eligibility does not mean all resources
are free, and no account billing-plan upgrade was performed.

## Learning notes

Account entitlements are an operational architecture constraint. Query eligible
instance types and regional offerings rather than assuming a common instance
family can be launched in every account.
