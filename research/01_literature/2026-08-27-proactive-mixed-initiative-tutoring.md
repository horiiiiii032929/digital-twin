# Proactive mixed-initiative tutoring research

Date: 2026-08-27

Status: implementation-facing literature and prior-art synthesis

Related decision: [`proactive-outreach-001`](../../docs/proactive-outreach.md)

## Research question

How should a Professor Digital Twin decide whether, when, and how to initiate a
student interaction, and how can the project evaluate whether that initiative
helps learning without becoming intrusive, unsafe, or academically misleading?

## Executive conclusion

The appropriate product model is **mixed-initiative, just-in-time adaptive
tutoring**. The system may initiate a bounded intervention, but only within a
published professor policy and a student-controlled interruption budget.

This is not evidence for a free-running LLM agent. The literature instead
supports separating:

1. a decision point at which support might be useful;
2. trusted variables that describe the learning opportunity and availability;
3. deterministic eligibility and suppression rules;
4. a small set of professor-approved intervention options;
5. grounded composition and delivery; and
6. proximal and delayed learning outcomes.

The current professor-scheduled implementation is autonomy level A0. The first
defensible autonomous expansion is A1: deterministic event-driven triggers such
as notifying a student when a previous no-evidence condition has been resolved,
or scheduling retrieval practice from professor-tagged concepts. A model-inferred
misconception or disengagement trigger should remain A2 and must not be selected
before shadow-mode precision and interruption-risk evidence exists.

## What the evidence does and does not establish

| Evidence | What it supports | Limitation for this project |
| --- | --- | --- |
| Controlled intelligent-tutoring studies of proactive hints | Timely, predicted help can improve help appropriateness, training efficiency, and post-test performance in a structured problem-solving tutor | Results come from bounded logic/problem environments, not asynchronous general course chat |
| Contextual ASSISTments hint experiments | Hint benefit depends on prior knowledge, task difficulty, deadline context, and how students use help | On-demand hints are not the same as unsolicited notifications |
| Just-in-time adaptive intervention and micro-randomized-trial methodology | A rigorous vocabulary for decision points, availability, tailoring variables, intervention options, proximal outcomes, and causal optimization of timing | The strongest literature is from health interventions; transferring the experimental method to education is a project inference, not evidence of educational effectiveness |
| Mixed-initiative and interruption research | Automation should account for uncertainty, user attention, expected benefit, interruption cost, and easy return of control | Much of the work predates LLM tutoring and does not settle course-specific trigger policy |
| Singapore agentic-AI and education-data guidance | Bound autonomy, retain meaningful human accountability, disclose agent use, limit data and purpose, and make consent withdrawable | Governance guidance does not demonstrate tutoring quality |

The key academic consequence is that delivery success, opens, clicks, or model
agreement cannot establish learning benefit. Those are operational or engagement
measures. Learning claims require a defined learning objective, a proximal
response measure, delayed retention or transfer where feasible, and an evaluation
design that separates selection effects from intervention effects.

## Design vocabulary adapted from just-in-time interventions

The just-in-time adaptive intervention literature defines six useful components.
For this project they map as follows.

| Component | Course Digital Twin definition |
| --- | --- |
| Decision point | A moment at which the system evaluates whether to send nothing, create a quiet inbox item, or notify the student |
| Tailoring variables | Course, current release, concept, prior attempts, prior hint use, elapsed time, student preference, recent outreach, and evidence availability |
| Availability | Consent, active membership, acceptable local time, frequency budget, no unresolved assessment/privacy restriction, and a reachable private channel |
| Intervention options | No action, retrieval question, self-explanation prompt, progressive hint, source-recovery notice, or professor-authored course notice |
| Decision rule | Versioned deterministic rule initially; a learned policy can rank eligible options only after prospective evidence |
| Outcomes | Immediate productive response and help appropriateness; later retention, transfer, self-regulation, and course outcome hypotheses kept separate |

`No action` is a first-class intervention option. At every decision point, the
agent must be able to conclude that silence is best. The absence of a message is
not an operational failure.

## Assistance dilemma

Proactive tutoring must resolve two different errors:

- **help avoidance**: a student needs support but does not request or receive it;
- **help abuse or over-assistance**: support arrives when it is unnecessary,
  reveals too much, or replaces productive effort.

The controlled HelpNeed studies provide evidence that proactive hints can help
in a structured logic tutor when a predictor identifies unproductive steps. A
later study reported that incorporating prior hint usage improved the predictor,
reduced unproductive training, and improved post-test performance. These studies
support measuring the appropriateness of help, not maximizing message volume.

They do not justify transferring a HelpNeed classifier directly into this
project. Our tutor observes less structured natural-language evidence, and an
incorrect inference can disclose a sensitive learner-state judgment or create
unwanted pressure. The first learner-state candidate therefore needs a shadow
mode in which it proposes triggers without sending them.

## Autonomy ladder

| Level | Trigger authority | Example | Current decision |
| --- | --- | --- | --- |
| A0: scheduled delivery | Professor or student explicitly creates the trigger | Professor schedules a source-linked retrieval check | Implemented locally |
| A1: deterministic event | Versioned code creates a trigger from an objective event | New release resolves an earlier no-evidence answer | Recommended next candidate |
| A2: bounded inference | A model proposes a trigger from learner-state evidence; deterministic code validates or suppresses it | Repeated misconception followed by a progressive hint | Shadow mode only |
| A3: learned policy | A calibrated policy chooses among eligible interventions based on measured outcomes | Contextual intervention ranking | Deferred until real prospective evidence |
| A4: open-ended autonomy | A model invents goals, recipients, timing, and actions | Free-running professor impersonator | Prohibited |

A1 is meaningfully autonomous from the student's perspective while remaining
inspectable. A2 and A3 are research candidates, not prerequisites for a useful
product demonstration.

## Recommended trigger portfolio

### Tier 1: low-inference triggers

- student-requested reminder;
- professor-scheduled retrieval practice;
- professor-authored course-wide notice;
- evidence-recovery notice after a previous source-grounded abstention; and
- a spaced-review decision point created from a professor-tagged concept and a
  student opt-in schedule.

### Tier 2: bounded learner-state triggers

- repeated incorrect or contradictory claim on the same concept;
- repeated request for increasingly explicit help;
- an abandoned tutor-initiated retrieval attempt; and
- a student-declared low-confidence or confusion signal.

Tier 2 requires a minimum evidence count, a confidence value, an explanation of
why the trigger was proposed, and a shadow-mode audit. A single long pause,
message sentiment, low activity level, grade, demographic characteristic, or
absence from the application is insufficient by itself.

### Excluded initial triggers

- inferred laziness, motivation, emotion, mental health, or likelihood of failure;
- grade-risk or disciplinary escalation;
- surveillance derived from unrelated device, calendar, location, or Discord
  activity;
- messages based on hidden or unapproved course content; and
- autonomous outreach about graded work that would exceed the published
  academic-integrity policy.

## Intervention design

The first message should preserve student agency and productive struggle. Prefer
an invitation or retrieval prompt over a complete explanation:

1. state that the message comes from the AI course tutor configured by the
   professor, not from the professor personally;
2. give a short, specific reason such as “You asked to revisit cache coherence”
   or “new approved material now covers your earlier question”;
3. ask one bounded question or offer one next action;
4. link to the original in-app evidence and conversation context; and
5. expose `Not now`, `Snooze`, `Less often`, and `Turn off` without requiring a
   reply.

Progressive assistance should follow a ladder: retrieval attempt, metacognitive
prompt, conceptual cue, partial structure, then explanation if the policy allows
it. A notification should not contain a bottom-out answer by default.

## Interruption and attention model

Classic mixed-initiative work identifies poor timing, uncertainty about user
goals, and failure to consider action cost as core agent problems. Interruption
research also finds that task relevance and task breakpoints affect disruption.

The initial system should not infer attention from invasive sensors. It can use
low-risk availability variables:

- student-configured timezone and quiet hours;
- explicit snooze and channel state;
- a per-course weekly budget;
- time since the latest tutor or student message;
- whether the student is currently in an active tutor turn;
- recent dismissals, ignored prompts, or frequency reductions; and
- deadline or review windows explicitly published by the professor.

Repeated dismissal is evidence about interruption cost, not evidence that the
student is disengaged. It should reduce future outreach rather than trigger more.

## Outcome model

Every trigger type needs a declared proximal outcome before execution.

| Trigger | Proximal outcome | Delayed outcome hypothesis |
| --- | --- | --- |
| Retrieval practice | Student attempts the question without opening a complete answer first | Correct recall or transfer after a frozen delay |
| Misconception follow-up | Student revises or explains the target claim with source support | Reduced recurrence on a later case |
| Evidence recovery | Student receives a valid grounded answer or successfully follows the cited source | Restored task completion and trust |
| Spaced review | Student completes a short recall check in the intended window | Better delayed retention than no prompt |
| Course notice | Student acknowledges or completes the stated course action | Operational completion only; no learning claim by default |

Opens, clicks, reply rate, and time-to-open are diagnostics. They are not primary
learning outcomes. Dismissal, snooze, channel disablement, and negative feedback
are interruption-cost signals and must be reported even when learning metrics
look favorable.

## Evaluation programme

### P0: deterministic safety simulation

Freeze synthetic trigger opportunities spanning eligibility and every
suppression rule. Require zero consent, course, release, evidence, privacy,
academic-integrity, duplicate, expiry, and withdrawal violations. This validates
the mechanism, not usefulness.

### P1: shadow-mode trigger study

Run A1 and prospective A2 rules over synthetic and approved development
trajectories without sending messages. Audit every proposed trigger and a seeded
sample of suppressions. Measure trigger precision, missed-help cases, calibration,
slice behavior, and policy explanations. The professor can review whether the
trigger types match the intended teaching policy without seeing private student
content.

### P2: opt-in usability pilot

With institutional/supervisor approval and explicit participant consent, test
the in-app channel with a small number of participants. Measure comprehension of
the AI identity and controls, opt-out success, interruption burden, usefulness,
and recovery. Do not make a learning-effect claim from this stage.

### P3: prospective intervention experiment

If sample size and approval permit, adapt a micro-randomized design: at eligible
decision points, randomize between `no message` and one frozen intervention
option. This can estimate proximal effects while accounting for changing context
within a student. The analysis must cluster repeated observations by student and
source/concept; message events are not independent samples.

If a micro-randomized study is infeasible, use a simpler randomized or
counterbalanced study and state its weaker causal scope. Never compare students
who happened to receive help with those who did not without accounting for the
fact that struggling students are more likely to be selected for help.

### P4: delayed learning confirmation

Only after safety, usability, and proximal benefit pass should the project test
retention or transfer on a delayed assessment. Keep learning, engagement,
usability, and operational reliability as separate claims.

## Metrics and gates

### Mechanism hard gates

- 100% correct consent, membership, course, release, evidence, quiet-hour,
  snooze, expiry, withdrawal, and destination enforcement;
- zero duplicate or cross-course deliveries;
- 100% source-version-valid citations for grounded outreach;
- zero hidden grades, student records, or inferred learner state in shared or
  externally visible notifications; and
- immediate, durable opt-out with no later delivery from an already queued item.

### Trigger quality

- eligible-trigger precision and recall on frozen labels;
- help appropriateness and help-avoidance rate;
- calibration by confidence band for inferred candidates;
- unsupported or insufficiently explained trigger rate; and
- slice results by trigger type, course, concept, prior-help behavior, time
  window, and channel.

### Student cost and benefit

- productive-response rate and proximal objective success;
- dismissal, snooze, frequency reduction, opt-out, and ignored-message rates;
- time trend in response and dismissal to detect notification fatigue;
- self-reported usefulness, pressure, trust, and perceived control; and
- delayed retention or transfer only in the separately powered confirmation.

No single aggregate score should trade away a consent, privacy, grounding, or
severe-interruption violation.

## Architecture conclusion

Use two cooperating runtimes rather than one perpetual agent loop:

```text
approved events / schedules / learner-state proposals
                         |
                         v
                trigger candidate ledger
                         |
                         v
     deterministic eligibility + availability + policy
               | suppress                 | eligible
               v                          v
          audit reason             select intervention
                                              |
                                              v
                              retrieve approved evidence
                                              |
                                              v
                        bounded composition and validation graph
                                              |
                                              v
                            transactional outbox + in-app source
                                              |
                                              v
                               channel delivery + outcome events
```

LangGraph remains appropriate for the bounded composition/validation subgraph
because it supports explicit deterministic and model-assisted steps,
checkpointing, and human interrupts. It should not become the global clock or
recipient authority. The durable database, scheduler, trigger ledger, and outbox
own asynchronous timing and exactly-once effects.

The existing SQLite worker is enough for local and single-instance staging. A
new workflow platform is not currently justified. If multi-instance scheduling,
long-lived retries, or many external connectors become operational requirements,
compare a Postgres-backed worker with a durable workflow runtime such as Temporal
using failure recovery, operational complexity, observability, and portability.

Canvas Live Events are useful prospective event inputs but are documented as
analytics/data-collection events rather than an immediate consistency channel.
Use them to propose a trigger or update an event ledger; recheck current state
through the Canvas API before a consequential delivery.

Discord remains a delivery adapter, not a learner-state source. Even for a
student-linked private destination, the safer initial design is a generic
notification and deep link to the authenticated in-app message. Full learner
state, misconception labels, grades, evidence excerpts, and tutoring history
should remain in the application. This is stricter than the current disabled
request builder and must be implemented before Discord can be enabled.

## Governance consequences

Singapore's 2026 Model AI Governance Framework for Agentic AI recommends
bounding agent powers, defining meaningful human checkpoints, applying lifecycle
technical controls, and enabling end-user responsibility through transparency
and education. For this project:

- the professor approves the available trigger classes and policy, not every
  low-risk delivery;
- the student controls channel consent and interruption budget;
- code, not a model, controls identity, recipient, timing eligibility, source
  permission, and external side effects;
- the interface identifies the sender as an AI course tutor configured by the
  professor; and
- policy changes, external-channel activation, and higher-autonomy promotion are
  meaningful approval checkpoints.

Singapore's education-sector PDPA guidance reinforces purpose notification and
consent before collecting, using, or disclosing personal data. Consent withdrawal,
data minimization, limited retention, correction, and overseas-transfer review
must be part of the real-user protocol. Product consent and research consent are
separate: opting into tutor reminders does not automatically consent to a study.

## Project decisions from this review

1. Keep the current deterministic authority and in-app-first architecture.
2. Define the feature as mixed-initiative just-in-time tutoring, not professor
   impersonation or open-ended agent autonomy.
3. Implement and evaluate A1 evidence-recovery as the first truly autonomous
   trigger candidate.
4. Run any misconception/struggle detector in shadow mode before delivery.
5. Add a trigger-level proximal-outcome contract and treat `no action` as a valid
   decision.
6. Keep external notifications generic and route students back to authenticated
   in-app content.
7. Evaluate mechanism safety, trigger validity, interruption cost, usability,
   and learning effects in separate stages.
8. Do not introduce Temporal, a multi-agent swarm, reinforcement learning, or a
   learned trigger classifier until the simpler architecture has evidence of a
   limitation that they would address.

## Primary and authoritative sources

- Maniktala, M., Cody, C., Isvik, A., Lytle, N., Chi, M., & Barnes, T. (2020).
  *Extending the Hint Factory for the Assistance Dilemma: A Novel, Data-driven
  HelpNeed Predictor for Proactive Problem-solving Help*. Journal of Educational
  Data Mining, 12(4). https://jedm.educationaldatamining.org/index.php/JEDM/article/view/450
- Maniktala, M., Chi, M., & Barnes, T. (2022). *Enhancing a student productivity
  model for adaptive problem-solving assistance*. International Journal of
  Artificial Intelligence in Education.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC9362072/
- Inventado, P. S., et al. (2018). *Contextual factors affecting hint utility*.
  International Journal of STEM Education.
  https://link.springer.com/article/10.1186/s40594-018-0107-6
- Klasnja, P., et al. (2015). *Micro-Randomized Trials: An Experimental Design
  for Developing Just-in-Time Adaptive Interventions*.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4732571/
- Horvitz, E. (1999). *Principles of Mixed-Initiative User Interfaces*.
  https://doi.org/10.1145/302979.303030
- Iqbal, S. T., & Horvitz, E. (2007). *Disruption and Recovery of Computing
  Tasks: Field Study, Analysis, and Directions*.
  https://www.microsoft.com/en-us/research/wp-content/uploads/2016/11/CHI_2007_Iqbal_Horvitz-1.pdf
- IMDA (2026). *Model AI Governance Framework for Agentic AI*.
  https://www.imda.gov.sg/-/media/imda/files/about/emerging-tech-and-research/artificial-intelligence/mgf-for-agentic-ai.pdf
- Personal Data Protection Commission Singapore (2024). *Advisory Guidelines
  for the Education Sector*.
  https://www.pdpc.gov.sg/-/media/files/pdpc/pdf-files/advisory-guidelines/advisory-guidelines-for-education-sector_25-apr-2024.pdf
- LangChain. *LangGraph overview, persistence, and interrupts*.
  https://docs.langchain.com/oss/python/langgraph/overview
- Instructure. *Canvas Live Events introduction*.
  https://developerdocs.instructure.com/services/canvas/data-services/live-events/overview/file.data_service_introduction
- Discord. *Webhook resource*.
  https://docs.discord.com/developers/resources/webhook

## Evidence boundary

The literature review supports the architecture and prospective evaluation
design. It does not select a proactive trigger component, prove that this
Digital Twin improves learning, authorize processing student data, or authorize
external delivery. Those require project-specific prospective evidence and the
corresponding approvals.
