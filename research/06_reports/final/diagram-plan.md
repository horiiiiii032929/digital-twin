# Final report diagram plan

Status: system-design core polished twice and rendered-QA checked; class, AWS, and results figures pending  
Report target: 10--15 pages  
Rule: every figure must answer one report question and distinguish observed,
implemented, and proposed material

The system-flow subset must also follow the IT5004 modeling grammar documented
in [the enterprise-systems alignment review](it5004-system-design-alignment.md):
separate system scope, activity flow, runtime interaction, logical layering,
and deployment instead of combining them in one architecture picture.

## Figure strategy

The report should use approximately five to seven figures in the main body.
Additional architecture variants can move to an appendix or presentation.
Figures should replace difficult prose, not repeat it.

Three visual families are needed:

1. **System understanding:** what the Course Digital Twin contains, who owns
   each decision, and how a student turn is processed.
2. **Research understanding:** how the evaluation programme evolved from
   component success through integrated failures to the narrow local release
   selection.
3. **Deployment understanding:** what was actually qualified locally and what
   an AWS deployment could become after new architecture decisions and tests.

## Proposed figure catalogue

| ID | Figure question | Proposed form | Report location | Evidence state | Draft state |
| --- | --- | --- | --- | --- | --- |
| F1 | Who may do what inside the Course Digital Twin boundary? | UML system use-case diagram organized by primary actor | Requirements/system design | Implemented functional scope | Improved Draw.io review draft |
| F2 | Which decisions remain deterministic, and where may a model propose an action? | UML swimlane activity diagram with guarded alternatives and terminating authorization exception | System design | Implemented selected local profile | Improved Draw.io review draft |
| F3 | How does a professor move from sources and policy to an immutable release? | Use-case description plus UML sequence diagram | System design | Implemented workflow and release controls | Improved Draw.io review draft |
| F4 | Why do both No Release and Keep results appear in the project? | Evidence-evolution timeline | Results | Registered evaluation chronology | Drafted |
| F5 | How did retrieval success, grounded-answer success, boundary safety, and exact citation quality differ? | Small-multiple quantitative chart | Results | Machine-readable records | Planned; values must be normalized carefully |
| F6 | What exactly is selected, pending, and retained as rollback in the current profile? | Component-profile decision map | Results/discussion | Current experimental profile | Planned |
| F7 | How do source bytes become a displayed citation with version and region lineage? | Evidence/data lineage | Methodology | Implemented provenance contracts | Planned |
| F8 | Where does the multimodal path differ from the text path, and why is it unselected? | Text-versus-region lineage | Limitations | Implemented foundation; no selected profile | Planned |
| F9 | What is the smallest AWS deployment that preserves the qualified single-host architecture? | Deployment diagram mapped to the logical tiers | Deployment/future work | Proposed, not implemented | Prototype exists; tier mapping required |
| F10 | What managed AWS architecture would support horizontal growth and stronger recovery boundaries? | Managed deployment diagram mapped to the logical tiers | Appendix/future work | Proposed, not implemented | Prototype exists; tier mapping required |
| F11 | Which conditions answer, clarify, abstain, refuse, or terminate the use case? | Policy decision table plus step-linked exception table | Discussion/security | Implemented and evaluated cases | Review draft created |
| F12 | Which design classes carry the release, tutoring, policy, retrieval, and persistence responsibilities? | Compact UML design class diagram with operations, multiplicities, and role names | System design appendix | Implemented design | Missing; next Draw.io unit |

## Recommended main-report selection

For the 10--15 page version, the recommended core set is the multi-tier logical
architecture, F2, F3, F4, F5, and F6. F9 is a seventh, conditional main-text
figure when deployment is central. The system use-case scope, F7, F8, F10,
F11, and F12 should normally move to an appendix unless their associated
discussion becomes central.

The two AWS figures should not both consume full pages in the report. A compact
comparison may use F9 in the main text and F10 in an appendix, or combine them
as two panels after the individual drafts are approved.

## Draft figure sources

- [F1 UML system use cases](../../../reports/figures/drawio/course-digital-twin-use-cases.drawio)
- [F1 multi-tier logical architecture](../../../reports/figures/drawio/course-digital-twin-logical-architecture.drawio)
- [F2 governed tutoring activity](../../../reports/figures/drawio/governed-tutoring-activity.drawio)
- [F3 professor-publication sequence](../../../reports/figures/drawio/professor-publication-sequence.drawio)
- [F3/F11 use-case and decision-table components](components/system-design-tables.tex)
- [F1 system context](../../../reports/figures/source/course-digital-twin-system-context.dot)
- [F2 governed tutoring authority flow](../../../reports/figures/source/governed-tutoring-authority-flow.dot)
- [F4 evaluation evolution](../../../reports/figures/source/evaluation-evolution-and-release-decision.dot)
- [F9 low-divergence AWS proposal](../../../reports/figures/source/aws-r1-low-divergence-proposal.dot)
- [F10 managed AWS target](../../../reports/figures/source/aws-managed-target-proposal.dot)

Each source is rendered to SVG for review and PDF for later LaTeX inclusion.
Figure numbering and full captions remain in LaTeX rather than being baked into
the artwork, so the report can reorder or omit figures without regenerating the
visuals. Proposed AWS status remains visible inside F9 and F10 themselves.

## AWS architecture reasoning

### F9: low-divergence pilot

The first AWS experiment should preserve the topology that already passed local
qualification: Caddy and the Docker Compose web/API/worker services on one
host, SQLite and the content-addressed store on one encrypted persistent
volume, and an off-host backup. An EC2 instance with encrypted EBS is the
closest mapping. AWS documents that EBS encryption covers the volume, data
moving between the instance and volume, snapshots, and volumes created from
those snapshots ([EBS encryption](https://docs.aws.amazon.com/ebs/latest/userguide/how-ebs-encryption-works.html)).
Snapshots can be created directly or automated through Data Lifecycle Manager
or AWS Backup ([EBS snapshots](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-create-snapshot.html)).

This proposal minimizes application change, making it suitable for a first
external-host rehearsal. It does not provide horizontal API scaling, managed
database failover, or queue isolation. A passing local run cannot be reused as
AWS evidence; the exact host, images, profile, DNS/TLS path, backup, restore,
restart, and rollback must be qualified again.

### F10: managed target

A later managed target can place web/API and worker containers on ECS Fargate
behind an Application Load Balancer. AWS supports ALB routing for ECS/Fargate
services, including path-based routing
([ECS service load balancing](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-load-balancing.html)).
AWS WAF can protect an Application Load Balancer or CloudFront distribution
([AWS WAF](https://docs.aws.amazon.com/waf/)).

The current durable adapters would then need evaluated replacements:

- SQLite to Amazon RDS for PostgreSQL. RDS automated backups retain snapshots
  and support point-in-time recovery within the configured retention period
  ([RDS automated backups](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html)).
- The filesystem source store to versioned, encrypted S3. S3 Versioning retains
  prior object versions after overwrite or ordinary deletion
  ([S3 Versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/versioning-workflows.html)).
- The leased database job table to SQS plus a dead-letter queue. SQS remains an
  at-least-once system, so existing idempotency and durable result checks remain
  necessary; failed messages can be isolated in a DLQ
  ([SQS visibility and failure handling](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)).
- Local logs and counters to CloudWatch, and runtime secrets to Secrets Manager
  with KMS-backed encryption and narrowly scoped IAM roles.

This managed design is not a drop-in hosting change. It changes transaction,
consistency, retry, failure-recovery, cost, and trust boundaries. It requires a
prospective architecture comparison and migration evaluation before selection.

## AWS decisions still needed

- AWS Region and data-residency requirements.
- Expected pilot users, courses, document volume, concurrency, and monthly
  availability target.
- Whether the first goal is merely an externally reachable research pilot or a
  horizontally scalable managed service.
- Whether the existing application-owned invite/session system remains, or an
  institutional identity provider must be integrated later.
- Backup retention, recovery-point objective, recovery-time objective, and
  cross-account or cross-Region requirements.
- Whether external model providers may receive approved course material from
  the selected Region.

These decisions are prerequisites for a defensible AWS cost comparison. No
monthly AWS price or capacity claim should be placed in the report until the
Region, topology, workload, and retention assumptions are fixed.
