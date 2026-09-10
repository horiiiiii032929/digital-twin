# Evaluation result: aws-presentation-route-001

## Run identity and decision

Date: 2026-09-09. Owner: Codex, user-requested presentation-route deployment.
Revision: `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty workspace.
[Plan](../04_experiments/2026-09-09-aws-presentation-route-plan.md),
[explicit demo profile](profiles/aws-presentation-demo-v1.json),
[sanitized evidence and source hashes](../../reports/aws-pilot/presentation-route-001.json).

**Keep this user-selected audited teaching route for the AWS demo.** This is an
explicit deployment override, not promotion of the experimental candidate or a
change to the retained research default. V19 remains semantically unqualified;
the previous final-selection decision remains intact.

## Configuration and comparison

The presentation's audited tutor uses `v19-luna-luna-medium`: Luna-low generation
and Luna-medium final audit/eligible repair through the existing V2 audit path.
The new staging-only pilot factory delegates to the existing experimental
factory without changing its generator, audit, repair, evidence or privacy
algorithms. Caddy still serves the frontend. Other post-report learning and
outreach settings remain disabled. The base R1 profile, BM25/text-OCR retrieval,
course permissions, authentication, storage, URL and EventBridge schedules remain.

Control: the deterministic seeded pilot in [aws-demo-seed-001](aws-demo-seed-001-results.md).
Candidate rationale comes from the bounded
[IT5004 presentation run](it5004-presentation-teaching-002-results.md), whose
actual private lecture content was not uploaded to AWS. The two courses here
use only authored synthetic notes and existing fictional accounts.

This operational run contains two exposed histories, two turns each. The first
prompts match previously tried seed prompts; follow-ups are authored correct
synthetic attempts. It is not a randomized/paired quality experiment, a held-out
benchmark, a model-selection run, or an estimate of student learning benefit.
There is no claimed latency or quality improvement over control.

## Results

| Gate | Observed result |
| --- | --- |
| Local route/experimental factory/runtime identity tests | 16 passed |
| CDK assertions | 7 passed |
| Staging route guard | Unknown/ambiguous routes and demo-auth mode rejected; deterministic rollback supported |
| CloudFormation and SSM activation | Successful; existing administrator preserved |
| Observed runtime identity | Both courses report V19 audited implementation, Luna-low generation and Luna-medium revision role |
| Existing account/access checks | 24/24 passed |
| Administrator HTTPS/auth checks | 9/9 passed |
| Synthetic two-turn histories | Both completed and persisted four messages each |
| Response outcomes | Two focused questions; two generated explanations with one citation each; no withholding in this small run |
| Final CDK diff | Zero differing stacks |

Data Systems first asks the student to distinguish the identifying member key
from the team reference. After the supplied attempt, it explains Ari–Cedar and
Bo–Cedar and asks about Cam. Browser Security first asks about request intent
versus session identity. After the attempt, it explains permitted-Origin checks
and asks why the cookie alone is insufficient. These are author-inspected
source-consistent examples, not independent semantic certification.

The successful V19 traces declare `final-response-quality-audit-v2-required`,
use `gpt-5.6-luna`, and have nonzero model usage. The audited implementation calls
the final audit before returning a proposal; combined observed composition,
code path and returned traces verify use of the configured audited route. This
run does not separately retain every raw provider request or count audit calls
individually, so no independent per-call ledger claim is made.

Public elapsed times: 22.227, 13.002, 19.607 and 14.593 seconds, all below the
configured 60-second origin timeout in these samples. Returned generation/audit
usage totals 15,711 input tokens and 5,499 output tokens, with approximately
US$0.009741 in trace-reported cost. Separate planner overhead is not included.
This is a sample cost, not an account bill or ongoing cost forecast.

## Recovery, failures and limits

A verified populated backup was taken before activation and retained privately
on the host. No credentials were reset and no seed records were replaced. The
new container uses the explicit pilot factory; switching
`APP_PILOT_TUTOR_ROUTE` to `deterministic-r1`, deploying and activating restores
the control route without changing accounts or course data.

There were no failed final live trials in this run. Activation briefly observed
connection refusal before startup readiness, then recovered within its normal
readiness loop. The seed's earlier false abstention, outline-only answers,
importer failures and missing-domain failures remain in their own result.

The audit is fallible. This run did not provoke withholding or bounded repair,
retest every adversarial/missing-evidence case, validate autonomous background
wording, or qualify instructor fidelity, human usability, capacity or recovery
after host loss. Older built-in onboarding previews remain template fixtures;
the live student route is what was changed and verified here.

The host is returned to its stopped off-hours state. Its next scheduled start
is 2026-09-10 09:00 Asia/Singapore. All credentials and the CloudFront URL remain
unchanged. Documentation includes the route switch and rollback procedure.

Changed documentation links and `git diff --check` pass. The full repository
Markdown check remains blocked by two unrelated Desktop artifact links in
`docs/final-report-vs-latest-slides-2026-09-09.md`; that document is unchanged.
