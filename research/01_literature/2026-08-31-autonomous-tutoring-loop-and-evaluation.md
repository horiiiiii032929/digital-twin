# Autonomous tutoring loop and evaluation research

Date: 2026-08-31

Status: implementation-facing literature and architecture synthesis

Related decisions:

- [`autonomous-tutoring-graph-001`](../../docs/autonomous-tutoring-graph.md)
- [`autonomous-tutoring-loop-002`](../../docs/autonomous-tutoring-loop-v2.md)
- [`proactive-outreach-001`](../../docs/proactive-outreach.md)

## Research question

How should the Course Digital Twin use an LLM inside an autonomous tutoring
loop, and how should that loop be evaluated so that factual grounding,
pedagogical behavior, state adaptation, proactive initiative, safety, and
operational reliability remain distinguishable claims?

## Executive conclusion

The project should use a **bounded mixed-initiative control system**, not a
free-running LLM. The trusted application runtime owns identity, permissions,
course and release scope, professor policy, source lineage, persistence,
delivery, budgets, and stopping conditions. The LLM performs semantic
perception, pedagogical planning, and grounded language generation through
typed contracts. Every proposed action and state mutation is mediated by
deterministic code.

The existing LangGraph implementation remains the correct orchestration base,
but its current regex-only interpretation and rule-only intent selection are
not yet the intended LLM-assisted autonomous loop. The successor should add a
structured semantic planner while keeping the deterministic router and
validators authoritative.

Autonomy must be evaluated across trajectories and side effects, not inferred
from answer quality. The previous 10,000-case Program 011 result is valid
factual product evidence, but it does not establish pedagogical adaptation,
memory quality, proactive usefulness, professor fidelity, or learning benefit.

## Evidence reviewed

| Source | Relevant evidence | Consequence for this project |
| --- | --- | --- |
| [OpenAI Agents SDK guidance](https://developers.openai.com/api/docs/guides/agents) | Responses API is appropriate when the application owns custom loops and branching; Agents SDK is appropriate when the SDK should own the recurring tool loop, sessions, guardrails, and approvals | Retain the code-owned LangGraph and direct Responses API boundary; do not add a second orchestration runtime without comparative evidence |
| [OpenAI trace grading](https://developers.openai.com/api/docs/guides/trace-grading) | End-to-end decision and tool traces support failure localization and reproducible workflow evaluation | Treat the structured agent trace as a versioned evaluation artifact, not an incidental debug log |
| [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | Checkpoints support conversation continuity, failure recovery, inspection, and time-travel debugging; stores support cross-thread application memory | Separate thread-scoped execution state from durable learner/profile memory and use persistent rather than in-memory checkpointing in release environments |
| [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | A graph can pause with durable state and resume after review; side effects before an interrupt must be idempotent | Use interrupts for genuinely consequential policy/profile decisions, not ordinary student turns; keep delivery in a transactional outbox |
| [Anthropic, Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) | Workflows offer predictable code paths; open agents are useful for uncertain tasks but add latency, cost, and compounding-error risk; evaluator-optimizer loops need clear criteria and stopping conditions | Use a graph workflow for tutoring, one bounded repair, and no unbounded ReAct or evaluator loop |
| [ReAct](https://arxiv.org/abs/2210.03629) | Interleaving reasoning, action, and environmental observations can improve open-ended task solving | Preserve the observe-decide-act idea, but expose only typed decisions and bounded tools; do not persist private chain-of-thought or permit arbitrary tools |
| [Pedagogical Steering](https://aclanthology.org/2025.findings-acl.1348/) | General assistants often reveal answers too quickly; predefined multi-turn transition graphs can steer an LLM toward a tutoring strategy | Keep an explicit tutoring-intent graph and help ladder rather than asking one prompt to “act like a professor” |
| [ScaffoldLM](https://aclanthology.org/2026.acl-long.325/) | Stepwise pedagogical plans, assessment-driven memory, and inferred learner state can improve coherent multi-turn scaffolding | Add plan progress and evidence-backed state deltas, while distinguishing observations from model hypotheses |
| [LearnLM](https://arxiv.org/abs/2412.16429) | Pedagogical behavior can be framed as instruction following controlled by explicit desired teaching attributes | Bind generation to a versioned professor-approved profile; evaluate profile adherence separately from factual quality |
| [MRBench taxonomy](https://aclanthology.org/2025.naacl-long.57/) | Tutor quality includes mistake identification/location, answer revealing, guidance, actionability, coherence, tone, and human-likeness; LLM critics were unreliable on difficult pedagogical dimensions | Adopt the dimensions as an adapted rubric, but do not make an uncalibrated LLM judge authoritative |
| [tau-bench](https://openreview.net/pdf?id=roNSXZpUDN) | Multi-turn agents must be evaluated against policy and final environment state; repeated-trial consistency can be much lower than single-run success | Score final repository state and policy effects, and report repeated-run consistency rather than one successful walkthrough |
| [OWASP Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) | Excessive functionality, permissions, and autonomy create damaging side effects; downstream authorization must not rely on the model | Give the model narrow read/propose tools only; enforce complete mediation in repository and delivery services |
| [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1) | Generative-AI risk management spans design, development, use, measurement, and monitoring | Keep prospective gates, unfavorable results, incident evidence, rollback, and post-release monitoring as one lifecycle |

## Framework decision

| Alternative | Decision | Reason |
| --- | --- | --- |
| Current LangGraph plus direct Responses API | **Keep and strengthen** | The graph already exposes explicit nodes, state, repair, fallback, and deterministic ownership. It supports the product's custom policy and evaluation boundaries. |
| OpenAI Agents SDK as a replacement runtime | Defer | It offers sessions, tracing, guardrails, and resumable approvals, but adopting it now would duplicate or replace an already evaluated graph and make historical T0/T1 comparisons less direct. Reconsider only if a concrete missing capability is demonstrated. |
| Free-form ReAct tutor | Reject for the student runtime | Open-ended tool selection and iteration are unnecessary for the bounded course task and increase error, cost, privacy, and termination risk. |
| Multi-agent tutor swarm | Reject | Interpretation, pedagogy, grounding, and delivery have overlapping context. Separate agents would add coordination and evaluation burden without current project evidence of benefit. |
| Generator/evaluator loop | Use only as one bounded repair | Deterministic validators have clear criteria; repeated LLM critique is not authoritative and previously caused operational evaluation loops in this repository. |
| Scheduler plus perpetual LLM process | Reject | Timing, recipients, consent, and retries belong to the durable event ledger, worker, and outbox. The LLM is invoked only for an eligible bounded decision. |

## Four cooperating loops

The product should not be represented as one perpetual loop. It contains four
loops with different clocks, authority, and evaluation units.

### L1: bounded turn-execution loop

Duration: one student request, normally seconds.

Purpose: understand the turn, retrieve evidence, select one pedagogical move,
generate a response, verify it, and commit exactly once.

The loop terminates with `answer`, `clarify`, `abstain`, `refuse`, or
`operational-failure`. It permits at most one repair and no arbitrary tool use.

### L2: learner-control loop

Duration: multiple turns and sessions.

Purpose: compare observed student work with the current learning objective,
update bounded learner-state hypotheses, and choose the next help level.

Observed facts and inferred hypotheses are separate. Every inference has
evidence, confidence, provenance, and expiry. The model proposes a delta; code
validates and atomically applies it.

### L3: proactive mixed-initiative loop

Duration: asynchronous minutes to days.

Purpose: respond to professor schedules or eligible learning events without a
new student message.

The durable event system owns time and recipient selection. Deterministic code
owns consent, quiet hours, frequency, deduplication, release validity, evidence,
and delivery. The LLM may rank an already eligible intervention and compose its
wording. `No action` is a valid and expected outcome.

### L4: course-governance and improvement loop

Duration: releases and teaching cycles.

Purpose: aggregate privacy-preserving learning-gap signals, propose course or
policy changes, and bind only professor-approved profile/release versions.

No model-generated proposal changes a live course automatically. Professor
approval creates a new immutable policy/profile/release binding.

## Why one global loop would be incorrect

A single always-running agent would conflate:

- language interpretation with authorization;
- learner-state inference with observed fact;
- response generation with course publication;
- intervention usefulness with permission to interrupt;
- a model retry with durable business-process recovery; and
- pedagogical quality with factual correctness.

Keeping the loops separate makes every claim measurable and prevents an error
in one clock from acquiring authority in another.

## Evaluation synthesis

### Separate claims

The evaluation must report at least these claims independently:

1. factual grounding and citations;
2. action and academic-integrity routing;
3. pedagogical move selection;
4. learner-state accuracy and calibration;
5. trajectory coherence and adaptation;
6. proactive eligibility and interruption cost;
7. professor-profile fidelity;
8. persistence, recovery, privacy, latency, and cost; and
9. learning or usability outcomes, only after an approved human study.

A single aggregate score cannot compensate for a safety, permission, privacy,
or severe-grounding violation.

### Evaluation hierarchy

| Level | Unit | Authority and purpose |
| --- | --- | --- |
| E0 contracts | Schemas, invariants, migrations, idempotency keys | Deterministic tests prove that prohibited states and side effects cannot be committed |
| E1 nodes | Perception, router, retrieval, evidence gate, planner, generator, validator | Isolate whether a failure came from interpretation, evidence, pedagogy, language, or integration |
| E2 turns | Source-linked direct, ambiguous, no-evidence, integrity, permission, and adversarial turns | Measure grounded action and response quality without trajectory confounding |
| E3 trajectories | Source-disjoint multi-turn student simulations | Measure transition validity, help progression, misconception correction, consistency, restart, and goal shifts |
| E4 proactive events | Frozen opportunities, suppressions, and delivery failures | Measure eligibility, `no action`, consent, timing, duplicate prevention, and interruption risk |
| E5 profile conditions | C0-C3 on fixed cases and evidence | Separate generic capability, grounding, professor policy, and retrieval effects |
| E6 whole-product operations | HTTPS journeys, provider failure, restart, backup/restore, rollback | Establish that the evaluated behavior survives the actual product boundary |
| E7 human evidence | Professor calibration and consented student study | Establish fidelity, usability, and eventually learning outcomes; non-human evidence cannot replace it |

### Trace contract

Each evaluated turn should persist an `AgentTraceV2` containing:

- run, conversation, turn, course, release, profile, policy, and code revisions;
- sanitized input classification and policy flags;
- structured observations and hypotheses with confidence and provenance;
- retrieval query IDs, source ranges, and evidence-gate decision;
- candidate intents and the selected intent with deterministic reason codes;
- model/provider identity, prompt/schema hashes, tokens, latency, and cost;
- generated atomic claims and citation mappings;
- validation failures, repair count, and terminal action;
- proposed and accepted learner-state deltas;
- persistence revision, outbox effect IDs, and restart lineage.

Do not store hidden chain-of-thought. Store typed decision factors and compact
rationale codes required for audit and replay.

### Repeated-run reliability

Single-run success is insufficient for an autonomous system. On a frozen
trajectory subset, run at least three seeded repetitions per system condition
and report:

- per-run success;
- `pass^3` for hard policy and final-state correctness;
- transition and action disagreement across repetitions;
- variance in citations, help level, and terminal state; and
- latency and cost distributions.

Every hard safety case must pass every repetition. Pedagogical variation may be
acceptable only when all variants remain within the approved intent and help
policy.

### Population, grain, and uncertainty

Each study must preregister its population, eligibility and exclusion rules,
unit of analysis, comparison conditions, primary estimand, and stopping rule.
The apparent number of turns is not the independent sample size:

- factual turns are clustered by source region and source family;
- dialogue turns are clustered by trajectory and simulated learner;
- proactive decisions are clustered by learner, concept, and opportunity;
- C0-C3 responses are paired by case; and
- eventual human outcomes are clustered by participant and course.

Report numerators and denominators for every rate, paired differences where
conditions share cases, and hierarchical or cluster bootstrap intervals where
appropriate. Do not average subgroup percentages without their underlying
weights. Freeze primary metrics and gates before execution; label every new
slice or supporting-evidence reinterpretation as post hoc. If many soft
pedagogical dimensions are tested, report the complete family and control or
clearly disclose multiplicity rather than selecting only favorable dimensions.

### Evaluation-data quality

Before a dataset can support a decision, validate:

- unique case, source, trajectory, turn, event, and condition identifiers;
- exact source/release/profile/policy hashes and referential integrity;
- complete coverage of required slices and explicit exclusions;
- no overlap between development and sealed source regions or trajectories;
- no gold fields, target spans, hidden policies, or future state in product
  inputs;
- no duplicated or near-duplicated questions that inflate the effective sample;
- consistent action, intent, help-level, and failure taxonomies;
- durable response completeness before scoring opens hidden labels; and
- agreement between persisted trace state and final repository/outbox state.

Simulated learners are controlled test instruments, not samples of real
students. Use multiple frozen personas and goal-change patterns to test
robustness, but do not infer usability, engagement, or learning effects from
their behavior. Once a benchmark has influenced design, subsequent results on
it are known-benchmark regressions; a fresh sealed tranche is required for a
new confirmatory claim.

### LLM judges

LLM review may support failure discovery, taxonomy labelling, and priority
sampling. It cannot override deterministic source truth, repository state, or
policy checks. Pedagogical judges must be calibrated against professor or human
labels for the exact rubric before their scores support a fidelity conclusion.
The MRBench result that critic models correlated poorly with human annotations
on difficult pedagogical dimensions makes this a required limitation, not an
optional refinement.

## Implementation consequence

The immediate implementation order should be:

1. finish issue #153's deterministic action and evidence boundary on fresh
   development evidence;
2. replace regex-only semantic interpretation with a typed LLM perception and
   pedagogical-plan proposal, while retaining regex and policy rules as hard
   prefilters and safe fallback;
3. add explicit observation-versus-hypothesis learner-state deltas with expiry;
4. persist `AgentTraceV2` and make all commits idempotent and revision-bound;
5. evaluate T0 versus the new T1 on identical evidence, model, release, and
   decoding across fresh multi-turn trajectories and repeated runs;
6. evaluate A1/A2 outreach in shadow mode before any inferred trigger can send;
7. bind an explicit professor-approved profile and run C0-C3; and
8. conduct human fidelity/usability/learning studies only under their separate
   approvals.

This order is finite but is not schedule-driven. A valid failure changes the
responsible method boundary; it does not trigger another evaluator search or
prompt-only rerun against known evidence.
