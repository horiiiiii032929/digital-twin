# Autonomous tutor best-practice audit

Date: 2026-08-31

Status: prospective architecture review; no provider, paid, private-data, human-study,
or release authorization

Related decision:
[`autonomous-tutoring-loop-002`](../../docs/autonomous-tutoring-loop-v2.md)

## Audit question

Does the proposed bounded LangGraph tutor represent established best practice for
an autonomous Professor Digital Twin, and which parts should be retained, amended,
or rejected before implementation?

## Verdict

**Needs revision before implementation.** There is no single established
best-practice architecture for an autonomous LLM professor. The current design is
strong as a safety-conscious agent workflow, but its first version expresses
temporal loops more clearly than it expresses the established conceptual modules of
an intelligent tutoring system.

The defensible design is a hybrid:

- retain the bounded LangGraph execution graph, deterministic policy authority,
  evidence gating, durable state, idempotent side effects, and T0 rollback;
- make the domain model, learner-belief model, pedagogical policy, interaction
  model, and governance/execution model explicit and separately testable;
- use the LLM to interpret language, map utterances to possible observations,
  propose a pedagogical move, and realize grounded wording;
- never let an LLM declaration become mastery, policy, source truth, or an
  externally visible action without a separate authoritative update;
- treat Bayesian knowledge tracing, model tracing, constraint-based tutoring, and
  POMDP-style policy selection as domain-dependent candidates rather than one
  universal solution;
- require real professor and student evidence before making fidelity or learning-
  outcome claims.

This rating follows the repository's evidence standard: the design is not "best"
because it has not yet beaten its baselines on project-specific evidence, and the
field itself does not establish one universally superior LLM-agent architecture.

## Method

The audit compared the prospective design against:

1. classic intelligent tutoring system architecture and inner/outer-loop behavior;
2. model tracing, constraint-based modeling, and knowledge tracing;
3. partially observable learner-state and pedagogical-policy formulations;
4. recent multi-turn LLM tutoring systems and tutor-evaluation benchmarks;
5. randomized and field evidence about guarded versus unguarded AI tutoring;
6. current agent-orchestration, persistence, safety, and trace-evaluation guidance.

Primary papers, official documentation, or publisher records were preferred.
Vendor guidance is used only for software/runtime claims, not educational-efficacy
claims.

## Established structure versus the proposed design

| Established idea | Evidence | V2 status | V2.1 decision |
| --- | --- | --- | --- |
| Domain, learner, pedagogical, and interface models are distinct ITS responsibilities | Classic ITS literature and recent ITS work retain this separation | Present implicitly across retrieval, learner state, planning, and UI | Make five explicit model planes by adding governance/execution as a separate authority |
| Inner-loop support and outer-loop task selection operate at different time scales | VanLehn's two-loop account | L1 and L2 are broadly aligned | Keep them, but distinguish a clock from the model that owns each decision |
| Learner knowledge is latent and inferred from observations | BKT and POMDP work | Evidence ledger is safe, but no calibrated belief-state contract exists | Add an explicit learner-belief state and estimator; preserve uncertainty and provenance |
| Pedagogical actions should follow an instructional policy, not generic helpfulness | Cognitive Tutors, StratL, ScaffoldLM, and guarded-tutor studies | `PedagogicalPlanV2` is directionally correct | Add a versioned pedagogical-policy contract and policy-specific transition guards |
| Step-level model tracing is powerful when a task has an explicit solution process | Cognitive Tutor evidence | Not represented as a domain-specific mode | Add it only for code/math/problem tasks with observable steps |
| Constraint-based feedback is useful when a submitted solution exposes rich constraints | Constraint-based modeling literature | Atomic claim validation provides a partial analogue | Keep claim constraints for open text; add task-specific constraints where the domain supports them |
| LLMs tend to reveal answers and drift in long dialogue | StratL, ScaffoldLM, MathTutorBench | Help ladder and one-repair graph address part of this | Retain bounded transition graph; test answer revealing and long-horizon drift explicitly |
| Agent frameworks are implementation choices, not pedagogical theories | OpenAI, LangGraph, and agent-engineering guidance | LangGraph is treated appropriately as control infrastructure | Keep LangGraph; do not claim it makes the tutor pedagogically valid |
| High-impact autonomy needs least privilege and human control | OWASP and current agent safety guidance | Deterministic ownership and approved-profile boundaries are strong | Keep A0/A1 bounded; leave inferred high-impact outreach in shadow until separately supported |
| Learning claims require learner outcomes, not only response quality | ITS meta-analyses and recent RCTs | Human study is listed only as the last evaluation layer | Keep that boundary explicit: synthetic trajectories cannot establish learning |

## V2.1 reference architecture

The conceptual models and the execution clocks are orthogonal. A loop says *when*
the system acts; a model says *which knowledge and authority* the action uses.

```text
MODEL PLANES

  Domain model
    sources / concepts / tasks / worked steps / constraints / misconceptions
            |
            v
  Learner-belief model <---- observations and assessed opportunities
            |
            v
  Pedagogical-policy model ---- professor-approved strategy and help ladder
            |
            v
  Interaction model ----------- dialogue, UI, citations, activities
            |
            v
  Governance/execution model --- identity, policy, consent, commits, delivery

CLOCKS

  per turn     per objective/session     proactive event     course/release
      L1                L2                    L3                   L4
```

### Domain model

The domain model must contain more than retrieved text. It should version:

- concepts and learning objectives;
- canonical sources and source-range lineage;
- task types and expected observable steps where available;
- valid solution constraints and common misconceptions where approved;
- prerequisite relations and permissible next activities;
- release, permission, and academic-integrity metadata.

Open-ended factual questions use source-range retrieval and atomic-claim constraints.
Structured code or mathematical work may additionally use model tracing or
constraint-based checks. One universal free-form RAG path is not sufficient for all
task types.

### Learner-belief model

The learner model must separate four objects:

1. `LearnerObservation`: what the learner actually wrote, selected, attempted, or
   completed, with turn/task provenance;
2. `ConceptAttribution`: a bounded mapping from an observation to one or more
   approved knowledge components, with uncertainty;
3. `LearnerBeliefState`: calibrated estimates and uncertainty supported by multiple
   observations;
4. `LearnerHypothesis`: temporary natural-language interpretations such as a
   possible misconception, with expiry and confirmation rules.

The LLM may propose concept attribution and hypotheses. It must not directly write
mastery probabilities. A deterministic or calibrated estimator owns the belief
update.

For the first release, use the existing provenance-rich evidence ledger and avoid a
false precision claim. Once the product has sufficient real assessed opportunities,
compare a simple count/rule baseline with BKT or PFA. DKT or another high-capacity
sequence model is not justified without substantially more representative student
traces and calibration evidence.

### Pedagogical-policy model

Add a versioned policy containing:

- instructional objective and strategy family;
- allowed tutoring intents and help levels;
- transition guards and required observations;
- answer-revealing and integrity ceilings;
- expected learner action;
- completion, hand-back, clarification, and stop conditions;
- professor approval, provenance, and release binding.

The LLM selects only among actions allowed by the active policy. It does not invent a
new teaching strategy in production. Productive Failure, Socratic guidance, worked
examples, direct explanation, retrieval practice, and fading are alternatives that
must be selected by course/task context and evaluated; none is universally best.

### Interaction and governance models

The interaction model realizes the selected action as dialogue, a question, a hint,
an activity, or a cited explanation. The governance/execution model remains the sole
authority for identity, release, permission, integrity, consent, budgets, state
commits, scheduling, delivery, interruption, and rollback.

This preserves the strongest part of V2: the model plans inside a bounded action
space while code owns consequential state and side effects.

## Why a full POMDP or reinforcement-learning tutor is not the default

Tutoring is naturally partially observable: learner knowledge is latent, actions
change both learning and future observations, and the best intervention depends on
uncertain state. A POMDP therefore provides a useful *interface discipline*:

- observation;
- belief-state update;
- pedagogical action;
- transition/outcome;
- objective or reward;
- stopping rule.

It does not follow that this project should immediately learn a POMDP or RL policy.
The project lacks enough representative learner trajectories and validated rewards;
offline optimization would be vulnerable to simulator bias, confounding, and reward
shortcuts. V2.1 adopts the separation while initially using professor-approved rules.
A learned policy becomes a future candidate only after an auditable logged-policy
baseline and consented real interaction evidence exist.

## Framework decision

Retaining LangGraph is reasonable, but only as an implementation decision.
LangGraph supplies explicit nodes, checkpoints, interruption, and replay. Its
documentation requires durable checkpointers and idempotent side effects around
resume boundaries. The direct Responses API remains suitable because the application
must own custom branching and broader policy controls; the OpenAI Agents SDK would
provide more built-in lifecycle and tracing but would not solve learner modeling or
pedagogical-policy validity.

Do not add a multi-agent hierarchy by default. Current agent-engineering guidance
recommends the simplest composable workflow that passes evaluation. Separate typed
roles inside one graph are easier to audit than independent agents with overlapping
authority.

## Evaluation correction

The existing factual, boundary, persistence, and trace gates remain necessary but are
not sufficient. V2.1 needs five distinct claims:

| Claim | Required evidence | What does not prove it |
| --- | --- | --- |
| Grounding and safety | Source-linked single-turn and trajectory tests with deterministic truth | A fluent response or LLM-judge agreement |
| Learner-state validity | Observation/attribution accuracy plus belief calibration such as Brier score, ECE, and selective risk/coverage | An LLM's confidence or synthetic persona consistency |
| Pedagogical-policy adherence | Transition-graph conformance, answer-revealing rate, help appropriateness, and long-horizon drift | Factual QA accuracy |
| Professor fidelity | Professor-approved profile and calibrated paired C0-C3 judgments | Style inferred from files without approval |
| Learning effectiveness | Consented learner study with pre/post or delayed transfer measures and an appropriate control | 10,000 synthetic questions or simulated learners |

Model-trace grades and LLM reviewers are useful diagnostics, but human-labelled
pedagogical calibration is still required. MRBench and MathTutorBench also show that
subject accuracy and tutoring quality are different dimensions and that longer
dialogue is harder.

Repeated-run stability, final state, and policy compliance should be reported in
addition to per-turn success. The unit of analysis must match the claim: source
cluster for grounding, learner/trajectory for tutoring, and participant for learning
outcomes.

## Accepted, amended, and rejected parts

### Keep

- bounded LangGraph plus direct provider interfaces;
- deterministic action lattice and evidence authority;
- one repair followed by safe fallback;
- durable checkpoints, atomic commits, outbox, and rollback;
- separate turn, learner, proactive, and governance clocks;
- professor-approved policy and consented low-risk outreach;
- trace-first and layered evaluation.

### Amend before code implementation

- make the five ITS model planes explicit;
- add learner observation, attribution, belief, and hypothesis contracts;
- separate state estimation from pedagogical planning;
- add a versioned pedagogical-policy contract;
- route structured tasks to model-tracing or constraint-based adapters where
  appropriate;
- add calibration, answer-revealing, and long-horizon policy metrics.

### Reject for the current release

- unrestricted ReAct-style autonomy;
- LLM-owned mastery or permanent learner-profile mutations;
- one universal pedagogy for every task;
- full learned POMDP/RL policy without real trajectories and validated rewards;
- default multi-agent orchestration;
- automated high-impact outreach;
- claims of professor fidelity or learning improvement from synthetic evaluation.

## Sources

- VanLehn, [The Behavior of Tutoring Systems](https://www.public.asu.edu/~kvanlehn/Stringent/PDF/06IJAIED.pdf), 2006.
- Anderson et al., [Cognitive Tutors: Lessons Learned](https://kilthub.cmu.edu/articles/journal_contribution/Cognitive_Tutors_Lessons_Learned/6469901), 1995.
- Corbett and Anderson, [Knowledge Tracing: Modeling the Acquisition of Procedural Knowledge](https://doi.org/10.1007/BF01099821), 1995.
- Ohlsson, [Constraint-Based Modeling: From Cognitive Theory to Computer Tutoring—and Back Again](https://doi.org/10.1007/s40593-015-0075-7), 2016.
- Piech et al., [Deep Knowledge Tracing](https://proceedings.neurips.cc/paper_files/paper/2015/file/bac9162b47c56fc8a4d2a519803d51b3-Paper.pdf), 2015.
- Ma et al., [Intelligent Tutoring Systems and Learning Outcomes: A Meta-Analysis](https://doi.org/10.1037/a0037123), 2014.
- Puech et al., [Towards the Pedagogical Steering of Large Language Models for Tutoring](https://aclanthology.org/2025.findings-acl.1348/), 2025.
- Wang et al., [Planning-Guided Tutoring with Assessment-Driven Memory](https://aclanthology.org/2026.acl-long.325/), 2026.
- Maurya et al., [Unifying AI Tutor Evaluation](https://aclanthology.org/2025.naacl-long.57/), 2025.
- Macina et al., [MathTutorBench](https://aclanthology.org/2025.emnlp-main.11/), 2025.
- Bastani et al., [Generative AI without guardrails can harm learning](https://doi.org/10.1073/pnas.2422633122), 2025.
- Kestin et al., [AI tutoring outperforms in-class active learning](https://www.nature.com/articles/s41598-025-97652-6), 2025.
- Oreopoulos et al., [Making AI Tutoring Productive](https://www.nber.org/papers/w35621), 2026.
- OpenAI, [Responses API and Agents SDK comparison](https://developers.openai.com/api/docs/guides/agents#compare-the-responses-api-and-agents-sdk) and [trace grading](https://developers.openai.com/api/docs/guides/trace-grading).
- LangChain, [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) and [interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts).
- Anthropic, [Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents), 2024.
- OWASP, [LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/).
