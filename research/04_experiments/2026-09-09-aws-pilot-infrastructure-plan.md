# AWS pilot infrastructure plan

Decision question: can the selected single-host R1 runtime move to AWS without
changing model, storage, authentication, or experimental component selection?

Prediction: one EC2 t3.medium with encrypted gp3 EBS can preserve the local
Docker/SQLite architecture. CloudFront VPC origin supplies an AWS HTTPS hostname
without a custom domain. Singapore (`ap-southeast-1`) and the `digital-twin` AWS
profile are explicitly requested by the user.

Control: qualified local R1 composition in `deploy/local-r1.qualified.env.example`.
Candidate: CDK infrastructure in `infra/cdk`, retaining those exact selectors.
Alternatives: ECS/Fargate with PostgreSQL/S3 requires a new persistence boundary
and evaluation; Lambda changes worker lifecycle and request duration; a public
EC2 origin needs additional origin authentication. These are design comparisons,
not measured performance comparisons. No component replacement is proposed.

Evaluation set: synthetic infrastructure assertions in
`tests/infra/aws_stack.test.mjs`, the existing staging configuration validator,
and the exact allowlisted container build. No course corpus or learner data is
uploaded. Baseline release, binding record, code revision, dirty state, and
source hashes are recorded in the generated deployment context manifest.

Predeclared gates: private host; no SSH; IMDSv2; encrypted retained local-block
storage; secret values absent from CloudFormation; credential authentication;
uncached cookies/authorization/API responses; no experimental promotion;
container builds and release settings validation pass. CI and synth are local
checks, not public-host qualification.

Operational rehearsal before pilot acceptance: authenticate synthetic roles;
reject cross-role access; upload a synthetic source; verify restart persistence;
perform backup and isolated restore; redeploy the previous image; check origin
bypass denial and HTTPS readiness. Record elapsed deploy/restore time, host
memory/CPU/disk, HTTP latency/errors, snapshot age, provider tokens/cost, and AWS
cost separately. At least one case per boundary and recovery path is required;
this sample establishes mechanics only and provides no statistical availability
or learning-effect claim. No provider calls are needed for infrastructure CI.

Failure classification: integration (build/configuration), policy (auth or
experimental drift), privacy (asset/caching exposure), operational (IAM, network,
storage, timeout, reboot or restore). Keep the local control until the cloud
rehearsal passes. Record any named decision-bearing rehearsal, including failed
or inconclusive runs, in the result registry using its result template.
