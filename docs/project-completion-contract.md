# Project completion contract

Working scope established 2026-09-06 to replace open-ended patching. This is a
prospective engineering and research target, not an advisor-approved grading
rubric or a claim that the current system passes. It organizes the existing
[completion plan](../research/04_experiments/2026-09-05-project-completion-plan.md).

## Project-level goal

Enable an instructor to extend their instructional presence beyond their own
available time: students receive course-grounded, pedagogically aligned support,
and the instructor receives actionable evidence of learning difficulties. Build
this as a coherent, governed Digital Twin system and demonstrate, through
reproducible controlled evaluation, what instructor knowledge, teaching-profile
alignment and bounded autonomous support contribute relative to simpler tutors.

The approved project has three pillars: identity/knowledge ingestion,
pedagogical alignment, and a student interface with an instructor dashboard.
These define the project. The implementation fixes, sample counts and operational
targets below are subordinate acceptance work, not separate project goals.

The computer-science contribution is the evaluated architecture and mechanisms
that connect grounded knowledge, pedagogical decisions, persistent learner state,
autonomous action and instructor feedback. A complete report explains why these
boundaries were chosen and what comparisons support them, including negative
results. It does not require inventing a new foundation model or claiming a
positive educational effect without a suitable study.

## Outcome

Deliver and evaluate an instructor-configured course Digital Twin that uses
approved course materials, provides grounded and style-aligned student support,
maintains learner state, initiates bounded consent-aware follow-up, and returns
traceable learning-gap insights to the instructor. One accepted, versioned
composition must support the complete journey through the actual web interface.

After instructor setup and student consent, ordinary tutoring and eligible
follow-up run without an operator initiating each turn. Course publication,
changes to teaching policy, and material revisions remain instructor-approved.
Autonomy includes completion, abstention, escalation, withdrawal and stopping;
it does not require unrestricted actions or indefinite model loops.

## Mandatory scope and acceptance

| Area | Required behavior | Acceptance evidence |
| --- | --- | --- |
| Knowledge ingestion | PDF slides/materials, text transcripts, and anonymized forum exchanges enter the same preview, approval, versioning and withdrawal workflow | Actual uploads through product UI; provenance, malformed/empty inputs, update and withdrawal tests; one multi-document course plus a second course for isolation tests |
| Grounded tutoring | Understand natural questions; answer requested details from evidence; identify ambiguity and missing support | At least 95% fully correct, relevant and supported answers on fresh answerable confirmation questions; at least 98% correct safe handling on boundary questions; exact citation lineage for every delivered citation; severe fabricated/prohibited answers are hard failures |
| Teaching alignment | Approved explanation order, hint depth and misconception handling influence delivered content across turns | At least 95% applicable explicit-profile rubric adherence on fresh cases, assessed on actual content; comparison with profile-off control; Socratic cases must withhold the solution until the permitted help stage |
| Autonomous support | Persist learner state, decide whether intervention is useful, deliver within consent/time/frequency limits, and stop or escalate | Actual selected model paths in fresh 30-virtual-day paired histories; restart, withdrawal, opt-out and provider-failure perturbations; zero observed wrong-recipient, unauthorized, duplicate-delivery or unbounded-loop events |
| Instructor feedback | Show traceable source/topic difficulty, observation window and denominator; support instructor review of improvement drafts | Actual student dialogues produce the displayed aggregate; privacy suppression and cross-course isolation pass; percentages reconcile with underlying eligible counts; concept labels require an evaluated mapping |
| Integrated operation | Accepted components work together from upload to instructor review and recovery | Same revision/configuration for UI journey, API checks, restart/restore and load trial; proposed initial load scope: 25 concurrent active students, full tutoring-response p95 <=15 seconds and unexpected request failure rate <=1%; report sample size, duration, hardware and all failures |

Targets apply to the declared evaluation scope. Zero observed violations does
not prove universal safety. Any change to thresholds or scope must be recorded
before the relevant confirmation, with its rationale; do not lower a gate after
seeing a failed result. An unmet gate produces an explicit Refine result and an
honest report, not an indefinitely extended or retrospectively redefined run.

## Quantity and evaluation design

Existing unit-test counts and historical benchmark volume are not a substitute
for evidence about the accepted composition. Use the following initial design
for planning; finalize and version sampling, labels and failure gates before
opening the confirmation set:

- One coherent multi-document course for the complete product journey, including
  all three input types. A second distinct course tests access and evidence
  isolation; it does not establish cross-discipline generalization.
- Development: separate public cases spanning paraphrases, missing details,
  multi-source questions, misconceptions and adversarial inputs. Use these to
  compare general implementations; do not tune on confirmation questions.
- Fresh confirmation: 400 answerable questions, 200 boundary questions, and
  200 profile opportunities balanced across Socratic and explanatory settings.
  Include at least 50 short multi-turn dialogues in the profile portion; score
  applicable turns and cluster uncertainty by dialogue. Do not pool these three
  denominators or count repetitions as independent cases.
- Longitudinal engineering confirmation: six personas x two teaching profiles x
  two reactive/autonomous conditions = 24 histories over 30 virtual days, with
  matched inputs/seeds between conditions and a recorded restart. These are
  synthetic histories, not 24 real students or evidence of educational benefit.
- Baselines: selected incumbent for each replaced component; grounded profile-off
  control for style; reactive-only control for autonomous support. Hold unrelated
  components fixed and include component-removal comparisons where they answer a
  specific contribution question. Adopt complexity only with useful evidence.
- Report counts, source/question-type slices and uncertainty. The proposed sizes
  support engineering diagnostics; they are not a power analysis for real learning
  effects. Real-professor fidelity requires instructor review of held-out responses;
  learning-effect claims require a separate appropriate real-student study.

Before sealing, independently review source-answer mappings and scoring rules,
including at least 20% of quality labels under the existing plan. Report who
reviewed them and what remains AI-authored. A model judge alone is not a human
or instructor review. If that review is unavailable, explicitly narrow the
claim to synthetic-profile alignment.

## Work order and change control

1. Fix and compare the two central mechanisms: question-specific answerability
   and profile-aware pedagogical planning/rendering. Retain explicit interfaces
   and deterministic authority/citation validation. General failure classes drive
   changes, not patches for individual observed question strings.
2. Complete product ingestion and instructor feedback workflows; integrate the
   accepted tutoring candidate. Each work item must name one acceptance row above.
3. Freeze the candidate and fresh evaluation package. Run quality, longitudinal,
   UI and operational confirmation on the same composition; register all outcomes.
4. Reconcile the English LaTeX report with implementation and evidence. Explain
   architectural alternatives, controlled comparisons, failures and limits.

A new feature enters mandatory scope only if it closes a listed acceptance gap.
Additional messaging channels, raw audio transcription, broad cloud deployment,
fine-tuning and additional retrieval providers are optional extensions with
separate decisions. Existing visual retrieval evidence is retained; new multimodal
work needs an identified course-use-case failure and a controlled comparison.

The software/evaluation milestone can complete without asserting real-professor
identity replication, real educational gains, infinite scale or universal safety.
Those stronger claims require their own evidence and are not silently inherited
from a working demo.

## Goal-to-gap audit, 2026-09-06

The earlier three priorities were broad phases, not an exhaustive work list.
Use these stable work packages for completion tracking. Findings are bounded to
inspected code and recorded evidence; this is not proof that no other bugs exist.

| ID / priority | Verified gap | Required completion output |
| --- | --- | --- |
| G1 / first | Lexical evidence matching misses paraphrases and admits excerpts that omit requested details; supported quotations can still fail to answer the question | General question-specific answerability and response mechanism, compared with incumbent; fresh content-quality and boundary confirmation |
| G2 / first | Approved profile context is an opt-in, unpromoted candidate; live adherence stayed 3/6; Socratic responses expose complete explanations. Approval preview shows expected behavior descriptions, not generated tutor outputs | Profile-aware multi-turn teaching with bounded help progression, actual response preview tied to configuration, profile-off comparison, retained authority checks |
| G3 / next, parallel | Product ingestion jobs implement PDF; text transcripts/forum exchanges are not connected to the same workflow | Approved multi-document course through real PDF and text/forum ingestion, update, provenance and withdrawal; demonstrate separation of course evidence from instructor teaching examples |
| G4 / next, parallel | Source labels are now readable, but source confusion is not an evaluated concept diagnosis or a cohort percentage; observed timestamp fields exist, yet the intended reporting window/denominator needs qualification; proposal review exists in API but not dashboard | Traceable learning-gap view with explicit reporting population/window and reviewed label meaning; usable professor draft-review flow |
| G5 / after G1-G2, design now | Seven-day live wiring passed, but exact accepted composition lacks 30-day model-backed confirmation and demonstrated intervention usefulness; historical simulated prediction/utility remain limited | Reactive/autonomous comparison, held-out synthetic histories, meaningful intervention/stop criteria, restart/failure/consent checks; no real-learning claim |
| G6 / after integration, design now | New changes lack same-revision browser/container/recovery/load qualification; course-list timing is not tutoring latency | Complete UI journey and exact composition manifest; concurrent real tutoring requests, provider failure/recovery, restart/restore, isolation and withdrawal checks |
| G7 / parallel research preparation | Synthetic profile responsiveness does not establish similarity to this instructor; new final-composition controlled comparisons and independent quality-label review remain incomplete | Approved instructor examples and instructor review where available; preregistered controls, reviewed fresh datasets, per-case evidence, uncertainty and failure analysis; otherwise narrow claims explicitly |
| G8 / outline now, finalize last | Report Related Work and Methodology sections remain placeholders; latest failed/successful development results and accepted composition need reconciliation | Concise English LaTeX report linking research questions, architecture alternatives, controlled results and limitations; verified references, relevant diagrams and compiled PDF |

No automatic extraction of a professor's personality is assumed necessary.
Manual instructor-approved settings and examples can satisfy configuration scope
if their effect is demonstrated. Actual-instructor fidelity needs actual-instructor
evidence; synthetic comparisons support only a narrower claim.

G1 and G2 are the central quality bottlenecks. G3, G4 and preparation for G7 can
progress independently. G5 and G6 qualify the integrated accepted candidate, and
G8 reports that evidence. Do not wait until the end to design experiments or write
the report structure. Optional deployment channels, model training and additional
multimodal providers remain outside mandatory scope unless an acceptance gap
justifies them. The earlier numerical targets are project proposals, not university
requirements or a statistical guarantee of sufficiency.
