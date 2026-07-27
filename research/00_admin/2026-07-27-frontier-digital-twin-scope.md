# Frontier Digital Twin scope

Date: 2026-07-27

Status: authoritative project and delivery baseline

Supersedes: `2026-07-22-deployable-pilot-rescope.md`

## Product thesis

Build and evaluate a professor-configurable pedagogical Digital Twin that
combines teaching behaviour, approved course evidence, tutoring policy, student
interaction state, and evaluation-before-publication. It is not a generic
multi-course RAG chatbot.

The final product must let multiple professors independently create and operate
course Digital Twins. Students interact only with Digital Twins to which they
are invited. The evaluated implementation runs locally and is packaged so it
can be hosted later; public hosting is not required for the final submission.

## Research contribution

The primary contribution is:

> A configurable multi-professor Digital Twin platform, with evidence-complete
> retrieval across heterogeneous courses as the central technical study.

The project studies whether an evidence-complete retrieval pipeline and an
explicit professor policy can produce safer, more faithful course tutoring than
simple retrieval and generic-assistant controls. The system must also show that
the selected methods survive complete professor and student workflows.

IT5002 is a pilot corpus and development anchor, not the product or research
boundary. The final research portfolio uses approximately four heterogeneous
courses drawn from explicitly permitted material.

No method is called state of the art because it appears in a paper, benchmark,
or vendor claim. A method earns selection only through project-specific
evidence against a shared baseline.

## Non-negotiable priorities

When time or evidence forces a trade-off, preserve these in order:

1. professor fidelity;
2. pedagogical tutoring and misconception handling;
3. evaluation-before-publication;
4. evidence-complete multi-course grounding;
5. reliable professor and student workflows.

Authentication, privacy, isolation, recovery, and portability are release
baselines. They support the contribution but are not the primary research
claim.

## Required product journeys

### Administrator

- Create, revoke, and reset invite-only professor and student accounts.
- Associate users with permitted courses without public signup.
- Inspect health, failed jobs, model/provider configuration, cost, and capacity
  evidence without exposing unnecessary course content.

### Professor

- Create and manage multiple courses.
- Upload approved text, Markdown, and selectable-text PDF material.
- Review source permission, sensitivity, version, inclusion, and exclusion.
- Configure the Digital Twin's teaching approach, tutoring moves, examples,
  tone, boundaries, and academic-integrity policy through the existing
  chat-led workflow.
- Preview representative student interactions and inspect citations, grounding,
  policy adherence, and known failures before publication.
- Publish, withdraw, update, and roll back a course Digital Twin.
- Review aggregate quality and failure evidence.

### Student

- Sign in with an invited account and access only assigned courses.
- Ask single- and multi-turn questions.
- Receive evidence-grounded, professor-aligned tutoring, misconception support,
  or a clear clarification, refusal, or no-evidence response.
- Inspect citations and source locators.
- Preserve conversation state without crossing course or user boundaries.

## Research programme

### R1: cross-course evidence retrieval

Compare a fixed four-condition ladder under shared chunks, queries, filters, and
metrics:

- M0: heading-aware BM25;
- M1: dense retrieval;
- M2: BM25+dense hybrid;
- M3: hybrid plus reranking.

Provider or model qualification is development-only. One fixed embedding and
reranking configuration is used in the final comparison. The existing Jina
adapter remains an unselected spike until a bounded provider-qualification
experiment compares it with the local Qwen3 path on quality, latency, cost,
privacy, reproducibility, and operational fit.

The final sealed set targets about 100 researcher-verified cross-course cases:
60 answerable and 40 no-evidence, cross-course confusion, or adversarial cases.
At least 20% receive independent second review. Primary evidence includes
complete-evidence success@3, atomic-claim coverage@3, no-evidence accuracy, and
course-isolation violations. Recall@k, nDCG, MRR, latency, cost, and failure
type are diagnostics. Hardware latency is an operational measurement, not a
retrieval-quality criterion.

### R2: professor fidelity and pedagogy

Hold the generator and evidence constant while comparing:

1. generic assistant without professor policy;
2. grounded assistant with generic tutoring policy;
3. grounded Digital Twin with professor policy.

Measure policy adherence, pedagogical-move appropriateness, misconception
handling, academic-integrity behaviour, citation support, and abstention.
Deterministic checks precede calibrated LLM judging. Judge agreement and
failure slices are reported.

### R3: end-to-end product validity

Run scripted and simulated professor/student journeys across multiple courses.
Measure successful setup, evaluation-before-publication, publish/withdraw,
grounded tutoring, state persistence, isolation, provider failure, rollback,
and recovery. Exercise a planning envelope of approximately 10 professors,
20 courses, 500 documents, and 100 concurrent student sessions. This is a
bounded capacity result, not an adoption or service-level claim.

## Data and provider boundary

Approved course material may be processed by an external embedding, reranking,
or generation API only after its provider, model, terms, retention, region,
estimated cost, and fallback are recorded. Exclude solution files, answer keys,
student submissions, student data, credentials, and secrets. Assessment
instructions and policies may be included.

The cumulative prospective API/model budget is USD 30. Every experiment sets a
smaller cap before execution. Private or bulky run output remains untracked;
sanitized aggregate and failure evidence is durable.

## Evaluation boundary and claims

No real-user recruitment is required. Evaluation uses deterministic tests,
researcher-verified course anchors, calibrated LLM judges, frozen
simulated-student trajectories, scripted synthetic accounts, and load tests.
Optional professor review is expert critique.

The final project may claim bounded component quality, professor-policy
fidelity, simulated pedagogical behaviour, workflow completion, isolation,
reliability, latency, cost, and portability. It must not claim human usability,
adoption, satisfaction, engagement, or improved learning outcomes.

Every named run, including failed, invalid, inconclusive, and no-selection
results, remains registered. The invalid one-time IT5002 rapid run is historical
evidence and is never rerun.

## Compressed delivery plan

| Date | Decision-bearing outcome |
| --- | --- |
| 2026-07-27 | Lock this product thesis, research questions, claims, and exclusions |
| 2026-07-28 | Align GitHub roadmap, milestones, issue dependencies, and project status |
| 2026-07-29 | Consolidate repository architecture and archive superseded planning |
| 2026-07-30 | Freeze course portfolio, system boundaries, source permissions, and provider candidates |
| 2026-07-31 | Complete ingestion/chunking QA across the course portfolio |
| 2026-08-01 to 2026-08-02 | Draft, verify, second-review, and freeze the cross-course benchmark |
| 2026-08-03 | Qualify and freeze one embedding/reranking provider configuration |
| 2026-08-04 | Implement and verify M0-M3 behind the shared retrieval interface |
| 2026-08-05 | Run development comparison and failure analysis |
| 2026-08-06 | Freeze configurations, thresholds, analysis, and sealed-run controls |
| 2026-08-07 | Execute the sealed cross-course retrieval run once |
| 2026-08-08 | Analyze, register, plot, and select or reject the retrieval profile |
| 2026-08-09 | Integrate the selected profile or documented rollback |
| 2026-08-10 to 2026-08-12 | Complete professor and student core journeys |
| 2026-08-13 | Run professor-fidelity, pedagogy, and end-to-end evaluation |
| 2026-08-14 | Test isolation, failures, publication rollback, and recovery |
| 2026-08-15 | Run capacity tests and package the local deployment |
| 2026-08-16 | Absolute technical and evidence freeze |
| 2026-08-17 to 2026-08-31 | Analysis, figures, report foundation, demo stabilization, and presentation appointment preparation |
| 2026-09-01 to 2026-09-03 | Complete report and presentation draft |
| 2026-09-04 | Target professor presentation and critique |
| 2026-09-05 to 2026-09-09 | Revise report, figures, slides, and demo from critique |
| 2026-09-10 to 2026-09-12 | Contingency and submission packaging only |
| 2026-09-13 | Final submission |

Daily work should normally end in one reviewable change or one
decision-bearing result. Experiments are not manufactured to satisfy a cadence:
they are run only when a component or architecture decision requires evidence.

## Professor reporting contract

Report every Monday, Wednesday, and Friday when there is new evidence. Each
update is a short conversational message with:

- one decision or result;
- exact sample size and two to four decision numbers;
- one compact table or at most two charts;
- one important limitation or failure; and
- the next decision and date.

Do not send a formal report unless requested. Do not send routine implementation
activity as if it were a research result.

## Stop rules

- Do not add a method because it is fashionable or available.
- Do not inspect or rerun sealed data after a failure.
- Do not silently change a selected profile.
- Do not sacrifice professor fidelity, pedagogy, or pre-publication evaluation
  to add lower-priority administration features.
- After 2026-08-16, make only fixes required to preserve frozen claims, the
  demonstration, or reproducibility.
