# AWS pilot infrastructure

Deployed 2026-09-09: [open the app](https://d3cccbyk2qjxd6.cloudfront.net).
See the [deployment evidence](../../research/05_evaluation/aws-pilot-deployment-003-results.md)
for successful public authentication, redeployment, reboot and initial-state
backup/restore checks, along with the retained failed attempts and limitations.

This CDK app targets **Singapore (`ap-southeast-1`)** using **`--profile digital-twin`**
(account `030334071887`). It deploys a single-host pilot with an AWS-generated
`https://….cloudfront.net` URL. No domain purchase, Route 53 zone, or custom
certificate is required.

The research [latest decision](../../research/05_evaluation/profiles/post-report-final-decision-v1.json)
keeps the [final R1 profile](../../research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json).
The user-selected AWS demo now uses the presentation's **audited tutor** through
`APP_PILOT_TUTOR_ROUTE=audited-presentation-v1`: V19 Luna-low teaching generation
with Luna-medium final audit, bounded repair and withholding. This explicit
[demo override](../../research/05_evaluation/profiles/aws-presentation-demo-v1.json)
is not a research promotion. See the
[live route verification](../../research/05_evaluation/aws-presentation-route-001-results.md). Retrieval, authentication, the base v2.1 graph and
source permissions remain in place. Other post-report learning flags and
proactive outreach remain off.

For rollback, set `APP_PILOT_TUTOR_ROUTE=deterministic-r1` in `runtime/runtime.env`,
run the CDK checks/deploy, then `npm --prefix infra/cdk run activate`. The explicit
factory selects the deterministic base composition when that route is selected.
`APP_GENERATOR_MODE=deterministic` remains the required base setting for the
experimental factory; verify the actual composition using the authenticated
course `runtime-status` API, not that environment field alone.

## Design and tradeoffs

CloudFront connects through a VPC origin to Caddy on one private EC2 c7i-flex.large.
Caddy serves the compiled frontend and proxies `/api/*` to FastAPI. The ingestion
worker and API share an encrypted 80-GiB gp3 EBS volume with SQLite WAL and source
objects. This x86 type is eligible under the target account’s current plan; the original
t3.medium selection was rejected by AWS. The host has no public IP or SSH ingress. A single NAT gateway provides
outbound access to registries, Systems Manager, Secrets Manager, and the model
provider. HTTP is used only within the VPC origin path; viewer access requires
HTTPS. The origin security group permits port 80 from the AWS CloudFront origin-facing
managed prefix list (`pl-31a34658` in Singapore), not arbitrary VPC addresses.
The list uses 55 security-group quota entries; this stack has one ingress rule.

All CloudFront caching is disabled to protect authenticated responses; cookies,
query parameters, and authorization are forwarded. Error responses are not
cached. CloudWatch receives container logs with 30-day retention. Request access
logging is disabled to avoid collecting learner URLs. An EC2 status alarm is
created; notification delivery is not configured.

This retains the existing single-host baseline. Fargate/RDS/S3 is a future
alternative after repository adapters and a migration are evaluated. EFS is not
used for the current local SQLite WAL database. There is no autoscaling or
multi-AZ availability claim. One NAT gateway increases the fixed monthly cost;
instance, EBS, backups, NAT processing, CloudFront, logging, secrets, and model
usage are separate charges. No unverified monthly price is quoted.

Data volume, secrets, backup vault and logs are retained on stack deletion.
Daily EBS backups expire after 14 days. Snapshots are crash-consistent; a tested
application backup/restore is still required. A host or AZ replacement requires
an explicit maintenance/restore procedure; never enable parallel hosts writing
to the same database. CloudFront's configured origin read timeout is 60 seconds;
slow provider calls need validation on the real host.

## Install and verify

From the repository root:

```bash
npm --prefix infra/cdk ci
npm --prefix infra/cdk run check
npm --prefix infra/cdk run synth
```

`check` runs offline assertions and synthesis. `synth`, `diff`, and `deploy` use
the named profile. The application fixes the region to Singapore and rejects
a different account. The image build context is allowlisted; `.env`, datasets,
recordings, reports, and local runtime files are excluded. The staged manifest
records the git revision, dirty state and every included source hash. Dirty
application changes are included deliberately; review them before release.

The deployment plan is in the
[infrastructure evaluation plan](../../research/04_experiments/2026-09-09-aws-pilot-infrastructure-plan.md).

## Provision and activate

Docker must be running; CDK builds Linux amd64 images and publishes them to ECR.
Bootstrap the target account once, then inspect and deploy:

```bash
cd infra/cdk
npx cdk bootstrap aws://030334071887/ap-southeast-1 --profile digital-twin
npm run diff
npm run deploy
```

Provisioning creates the host, data volume, HTTPS distribution, runtime secret,
and an SSM deployment document. It does not invent an API key or administrator.
Outputs are in the ignored `cdk-outputs.json`. To reuse a retained secret, set
`runtimeSecretArn` in the ignored `cdk.context.json` (or pass `-c runtimeSecretArn=ARN`).
Keep this setting for subsequent deployments; never clear it during an update
without reviewing the resulting secret replacement. In Secrets Manager in Singapore,
edit the secret named by `RuntimeSecretArnOutput`: set its `OPENAI_API_KEY` field
and preserve `APP_LEARNING_GAP_HMAC_SECRET`. Do not put either value into CDK
context, source files, command history, or task messages.

For automatic first-administrator creation, also set `ADMIN_EMAIL` and
`BOOTSTRAP_ADMIN_PASSWORD` in the same secret. The password must satisfy the
application's password policy. Activation preserves an existing administrator
and never uses this field to reset their password. The operator can retrieve
the initial password from Secrets Manager; credentials are not printed by the
deployment. Remove the bootstrap password field after securing administrator
access, or rotate it through the application's password-change flow.

After EC2 initialization completes and the key is populated, run `npm run activate`
from `infra/cdk`. It submits the deployment document using the saved stack outputs.
The equivalent AWS commands are (substitute stack outputs):

```bash
aws ssm send-command --profile digital-twin --region ap-southeast-1 \
  --instance-ids INSTANCE_ID --document-name DEPLOY_DOCUMENT \
  --document-version '$LATEST' --query Command.CommandId --output text
aws ssm get-command-invocation --profile digital-twin --region ap-southeast-1 \
  --command-id COMMAND_ID --instance-id INSTANCE_ID
```

The document pulls immutable asset tags, validates the secret and exact release
binding before stopping services, and launches the API, ingestion worker and
web. It refuses to run without the mounted data volume. All deployments are
serialized with a host lock. A readiness failure stops deployment and requires
operator diagnosis/rollback; this is not a blue/green rollout. The generated URL
is not usable until activation succeeds.

## Administrator and acceptance

Connect with `aws ssm start-session --profile digital-twin --region ap-southeast-1
--target INSTANCE_ID` (Session Manager plugin required), or use the AWS console's
Session Manager. On the host, use an interactive shell so the password is not
recorded in SSM command parameters:

```bash
sudo -i
read -rsp 'New administrator password: ' BOOTSTRAP_ADMIN_PASSWORD
export BOOTSTRAP_ADMIN_PASSWORD
docker exec -e BOOTSTRAP_ADMIN_PASSWORD digital-twin-api \
  python -m scripts.bootstrap_admin --email YOUR_EMAIL --display-name Administrator
unset BOOTSTRAP_ADMIN_PASSWORD
```

Run `uv run python scripts/verify_aws_pilot.py` from the repository root for
HTTPS, login/logout, cookie and rejection checks. Also verify professor/student isolation,
synthetic ingestion, source withdrawal, host reboot persistence, and a backup
restore before inviting users. Existing staging recovery commands are documented
in [deployment and recovery](../../docs/deployment.md). Do not upload existing
private course or learner datasets as part of deployment.

## Recovery and operations

### Office hours

EventBridge Scheduler starts the EC2 host at **09:00** and stops it at **18:00**,
Monday–Friday, in **Asia/Singapore**. Startup can take a few minutes. There is no
public-holiday calendar. The stable CloudFront URL returns an origin error while
the host is off; the schedules do not terminate the instance or erase its disks.
Docker and the data mount recover automatically on start.

Two direct EC2 API targets use separate execution roles restricted to this
instance and this schedule group. There is no scheduler Lambda or continuously
running scheduling process. Flexible windows are disabled, retries expire after
five minutes, and delivery failures go to an encrypted SQS dead-letter queue
with a CloudWatch alarm (no email subscription is configured).

The `OfficeHours` construct in `lib/office-hours.mjs` accepts `startHour`,
`stopHour`, and `weekdays`; change the constructor arguments in `lib/stack.mjs`,
run `npm run check` and `npm run diff`, then deploy. `ScheduleGroupOutput`,
`StartScheduleOutput` and `StopScheduleOutput` identify the AWS resources.

For temporary after-hours access, use the EC2 console or:

```bash
aws ec2 start-instances --instance-ids INSTANCE_ID --profile digital-twin --region ap-southeast-1
aws ec2 stop-instances --instance-ids INSTANCE_ID --profile digital-twin --region ap-southeast-1
```

These are timed transitions, not continuous enforcement: a manual after-hours
start remains on until someone stops it or the next weekday stop event occurs.
New schedules do not retroactively apply a stop time that has already passed.
During this setup, the current state is reconciled to the office-hours window.

Stopping reduces EC2 compute usage; it does not remove ongoing EBS, NAT gateway,
backup or other retained-resource charges. See AWS documentation for
[stopped-instance billing](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/how-ec2-instance-stop-start-works.html)
and [NAT gateway pricing](https://aws.amazon.com/vpc/pricing/).

Live scheduled stop/start and authentication verification are recorded in
[aws-office-hours-001](../../research/05_evaluation/aws-office-hours-001-results.md).

### Backup and restore

Inspect `/var/log/cloud-init-output.log`, `docker ps`, and the stack's
`RuntimeLogGroupOutput`. Docker requires the data mount before starting after
reboot. Retained EBS is separate from the replaceable OS disk.

Before updating an active pilot, pause writes and use the existing
`python -m scripts.backup_runtime --output ...` command inside the API image,
with a separate mounted backup destination outside `APP_DATA_ROOT`. Copy the
verified backup to approved encrypted storage and rehearse restore on an
isolated host. Daily EBS snapshots alone do not prove application recovery.

Keep the previous CDK output, image tags, runtime bundle, and data backup. To
roll back code, deploy the previous reviewed CDK/source revision and activate
its SSM document. CDK asset tags are content-addressed; do not overwrite them.
An incompatible schema needs a coordinated data restore while all writers are
stopped. Do not simply attach a replacement disk over a running application.

Destroy only after exporting required data. Retained resources continue to incur
charges and require deliberate cleanup; stack deletion is not data erasure.

AWS references: [CloudFront VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)
and [CDK EC2 VPC origin](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_cloudfront_origins.VpcOrigin.html).

### Latest deployment and pause

[10 September deployment/state summary](../../reports/aws-pilot/deployed-state-2026-09-10.md): validated local app fixes deployed; EC2 stopped; both start and stop Scheduler entries disabled via AWS CLI pending professor review. This manual schedule drift must be preserved on later CDK updates. The pilot AMI is pinned to its existing `ami-0872fceefd41a6357` to prevent an app release from replacing the host; OS upgrades require explicit maintenance.
