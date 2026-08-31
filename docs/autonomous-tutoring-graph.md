# Autonomous tutoring graph

Date: 2026-08-21

Decision ID: `autonomous-tutoring-graph-001`

Status: accepted by the project owner on 2026-08-21 and retained as the T1-v1
historical design. The prospective architecture is now
[`autonomous-tutoring-loop-002`](autonomous-tutoring-loop-v2.md). No new
runtime, provider, dataset, or release authorization follows from either design.

Implementation owner: [GitHub issue #107](https://github.com/horiiiiii032929/digital-twin/issues/107)

## Decision question

How should the Course Digital Twin interact with students autonomously while
remaining grounded in approved course evidence, following the professor's
teaching policy, adapting across multiple turns, and stopping safely when it
cannot continue?

## Proposed decision

Implement the student-facing Digital Twin as a **closed-loop, stateful
pedagogical agent**. Use one code-controlled LangGraph state graph with bounded
LLM-assisted nodes. Do not implement the tutor as a free-form chatbot, an
unbounded ReAct loop, or a swarm of agents that negotiate the response.

The professor configures, previews, approves, publishes, updates, withdraws,
and rolls back the Digital Twin. Once a version is published, normal student
interaction is autonomous. The professor does not approve each response.

The completed 10,000-row factual-QA programme validates deterministic dataset
and provider-pipeline behavior, not product knowledge coverage: the author was
given gold metadata and the final answer/citations came from truth packages. A
separate leakage-free evaluation must test retrieval, answerability, factual
claims, and citation behavior. Neither track evaluates the autonomous tutoring
loop or establishes that students learn.

## Why a graph rather than one agent prompt

The application needs different owners for different decisions:

- deterministic code owns identity, course access, source permission, loop
  limits, policy ceilings, persistence, and release binding;
- retrieval owns the evidence available for the turn;
- the pedagogical controller owns the set of valid tutoring moves;
- models may classify student state, propose a tutoring intent, and produce
  natural language within those boundaries;
- validators decide whether the response may be shown or must fall back;
- the versioned professor policy controls course-specific behavior.

This follows current agent engineering guidance to mix deterministic routing
with bounded model behavior when speed, cost, and reliability matter. It also
matches recent tutoring work in which student-state tracing and an explicit
transition graph steer the next tutoring intent rather than relying on a
general instruction to "act as a tutor."

## Runtime architecture

```text
Student message
      |
      v
Authenticate and bind course, release, conversation, and policy versions
      |
      v
Interpret the turn and trace the current learner state
      |
      +---- unsafe / disallowed graded-work request ----> policy response
      |
      +---- navigation / social turn -------------------> bounded chat response
      |
      `---- learning turn
                |
                v
      Retrieve approved text and multimodal evidence
                |
                v
      Evidence sufficient for the requested action?
          | no                         | yes
          v                            v
      clarify or abstain       select tutoring intent
                                      |
                 +--------------------+--------------------+
                 |                    |                    |
              diagnose             scaffold             explain
              question               hint             or summarize
                 |                    |                    |
                 +--------------------+--------------------+
                                      |
                                      v
                         generate grounded response
                                      |
                                      v
                 verify evidence, citation, policy, help level,
                         privacy, and response contract
                           | pass                 | fail
                           v                      v
                      persist state       one bounded repair
                           |                      |
                           |              safe fallback on failure
                           +-----------+----------+
                                       v
                              stream to student
                                       |
                                      END
```

Each student message starts one bounded graph invocation. Persisted state makes
the sequence of invocations a continuing tutoring relationship. The graph does
not keep calling itself while waiting for the next student message.

## Three loops

### Turn loop

The turn loop produces one safe response. The default bound is one state
interpretation, one grounded generation, and at most one repair. A failed repair
returns a deterministic clarification, refusal, or no-evidence response.

Every graph path must have:

- an explicit terminal node;
- a maximum graph-step count;
- per-node time and token limits;
- idempotent persistence and request identifiers;
- a defined provider-failure fallback; and
- no automatic retry that could duplicate a response or charge.

### Learning loop

Across student turns, the tutor observes the student's work, updates a bounded
learner-state estimate, selects the next pedagogical move, and checks whether
the learning objective has been reached. It may decrease or increase
scaffolding, change representation, ask for self-explanation, provide practice,
or revisit a misconception.

This decision originally limited autonomous proactivity to an active tutoring
session. On 2026-08-27, the project owner promoted asynchronous, opt-in outreach
to a core product direction. Its separate trigger, consent, delivery, and
evaluation boundary is recorded in
[`proactive-outreach-001`](proactive-outreach.md). The turn graph still cannot
schedule or deliver messages by itself.

### Course-improvement loop

Across conversations, the system aggregates privacy-preserving topic,
misconception, no-evidence, and failure signals. It proposes course-material,
policy, explanation, or practice improvements. Consequential changes remain
drafts until the professor accepts them and publishes a new version.

## State contract

The graph state should contain explicit, typed fields rather than relying on the
raw transcript as memory:

- authenticated account, role, course, release, policy, and conversation IDs;
- current learning objective and topic/concept IDs;
- estimated mastery by concept, with confidence and evidence for the update;
- observed and hypothesized misconceptions, kept distinct;
- latest student request, attempt, confidence, confusion, and engagement
  signals;
- previous and proposed tutoring intents;
- current help/scaffolding level and academic-integrity ceiling;
- retrieved source IDs, versions, regions, claims, and approved crops;
- draft response, citations, validation results, and failure reason;
- suggested next activity and whether the current objective is complete;
- turn, model, token, latency, cost, and trace metadata.

Models may propose learner-state changes through a strict schema. Deterministic
rules validate and apply them. Model output cannot modify identity, source
permission, professor policy, release versions, or authoritative source
lineage.

## Tutoring-intent graph

The initial intent vocabulary should be small and professor-configurable:

- `clarify_request`
- `diagnose_understanding`
- `ask_next_step`
- `prompt_self_explanation`
- `give_hint`
- `give_analogy_or_example`
- `correct_misconception`
- `explain_concept`
- `check_understanding`
- `give_retrieval_practice`
- `summarize_progress`
- `refuse_and_redirect`
- `abstain_no_evidence`
- `close_or_transition_objective`

Transition conditions should combine trusted policy and evidence state with a
structured interpretation of the student's latest turn. For example, a student
who made a reasoning error may receive a diagnostic question or hint, while a
student who demonstrated mastery may receive a transfer question or move to the
next objective. The model writes the response for the selected intent; it does
not invent an unrestricted intent.

## Engineering selection

- Retain LangGraph as the stateful orchestration runtime. The repository
  already uses its graph, state, conditional-edge, persistence, and interrupt
  model.
- Add a production Postgres checkpointer and store rather than introducing a
  second orchestration framework.
- Retain Pydantic models for graph state, tool inputs, tool outputs, and
  provider responses.
- Retain the provider-neutral model interface, while the R1 candidate uses the
  direct OpenAI Responses API with exact allowlisted model identities,
  `store: false`, bounded budgets, and no router fallback.
- Keep retrieval, evidence sufficiency, learner-state interpretation,
  pedagogical intent selection, generation, and validation as separately
  testable contracts.
- Use region-aware local document processing as the default ingestion path;
  evaluate Docling as a candidate parser for layout, reading order, tables,
  formulas, code, OCR, and images without replacing the existing fallback by
  assumption.
- Use one economical primary tutor model and bounded specialist fallbacks. A
  newer or larger model is not selected without project evidence that it
  improves the graph's tutoring outcome.

## Current repository mapping

The existing student workflow remains the **T0 control and rollback**. It
already provides release-bound conversations,
course isolation, selected retrieval with fallback, professor-policy loading,
citation validation, idempotent turns, persistence, and safe generation
failure. Its accepted path still uses a deterministic grounded generator.

LangGraph now runs the bounded student T1 graph behind an explicit mode. Its
live generator can produce only source-bound atomic claims; deterministic code
owns the pedagogical teaching move, policy, citations, and learner-state
mutation. T0 remains selected until confirmation passes.

Reusable foundations:

- professor onboarding, policy, preview, revision, and approval contracts;
- course/release/source authorization and atomic publication boundaries;
- M2 hybrid text retrieval with BM25 fallback;
- region-aware multimodal chunks and crop citation lineage;
- durable local conversation and audit repositories;
- provider-neutral model, embedding, and reranking interfaces; and
- student/professor conversation-first web workspaces.

Still missing before release selection is execution evidence: the selected
product model, the frozen 50-trajectory T0/T1 confirmation, and the public
workflow/recovery qualification. Professor-profile, learning-gap, and A0
outreach APIs/UI are implemented; the real professor-approved T2 fidelity
reference remains outside the demo claim.

## Course-improvement loop checkpoint

The autonomous product has two deliberately separated loops:

1. The online T1 tutoring graph interprets one authenticated turn, retrieves
   eligible evidence, selects one bounded intent, generates and validates a
   response, performs at most one repair, and commits the response plus learner
   state atomically.
2. The asynchronous course-improvement loop receives only privacy-minimized
   post-commit signals. It stores keyed learner/turn pseudonyms, suppresses
   groups below a minimum of five distinct learners, aggregates counts within
   one course and release, and creates non-executable professor-review drafts.

The first #132 checkpoint implements the second loop's domain and persistence
core. It contains no provider call and cannot read raw student content or
change learner state, policy, sources, prompts, releases, or the selected T0/T1
profile. Live emission, professor authorization, UI, deletion/key rotation,
and utility/privacy evaluation remain prospective checkpoints.

## Completed network-free development checkpoint

Issue #107 now implements the first T1 contract behind
`APP_STUDENT_TUTORING_MODE=bounded-tutoring-graph` for local demo/test use. T0
remains the default and staging validation rejects T1. The implementation adds:

- privacy-minimized typed learner state with revisioned atomic persistence;
- deterministic turn signals and a bounded tutoring-intent selector;
- one compiled LangGraph invocation per student message with 12 steps maximum;
- at most one response repair followed by a deterministic safe fallback;
- exact citation and source-lineage validation before persistence;
- fail-closed learner-state race handling and restart-surviving state; and
- a ten-trajectory, provider-free development contract at
  `research/05_evaluation/instruments/autonomous_tutoring_graph_contract_v1.json`.

The ten-trajectory deterministic local T0/T1 comparison completed at clean
revision `51eb43a` as `completed-go-deeper`. Every expected action and T1 intent
matched; citations, forced fallback, atomic persistence, and restart consistency
were 100%; and no safety violation, provider call, token, or cost occurred. The
per-turn evidence and durable decision are recorded in
[`autonomous-tutoring-graph-development-001`](../research/05_evaluation/autonomous-tutoring-graph-development-001-results.md).
The one-time network-free execution authorization is revoked.

T0 remains selected for staging and rollback. The development pass advances T1
only to one separately frozen confirmation; it does not select T1 for release,
prove model-based learner-state interpretation, establish professor fidelity,
authorize provider use, or establish student learning.

## Evaluation question

Does the graph-controlled tutor adapt its teaching behavior across a
conversation more reliably than a free-form grounded tutor, without reducing
factual support, citation quality, safety, response reliability, or acceptable
latency and cost?

## Evaluation conditions

Use the same questions, course evidence, generator model, decoding settings,
and source permissions for each applicable condition:

- **T0 — grounded answer assistant:** retrieves approved evidence and answers,
  but has no learner-state or pedagogical transition graph;
- **T1 — graph-controlled generic tutor:** adds learner-state tracing,
  bounded help levels, and the tutoring-intent graph;
- **T2 — professor-configured Digital Twin:** uses the same graph and evidence
  as T1 plus a professor-approved policy, examples, boundaries, and preferred
  tutoring moves.

T0 versus T1 answers whether the autonomous pedagogical graph adds value. T1
versus T2 answers professor-specific fidelity and stays pending until the
professor-profile method and reference examples are approved.

## Evaluation layers

| Layer | Decision supported | Evidence and evaluator |
| --- | --- | --- |
| Turn contract | Can one turn safely reach a terminal response? | Deterministic graph, access, schema, citation, policy, loop, and persistence tests |
| Factual grounding | Is the answer supported by approved course evidence? | Source-linked factual cases, citation validators, answer/abstain cases, and bounded human audit |
| Pedagogical transition | Did the tutor choose an appropriate next teaching move? | Labelled learner states and allowed transition sets; independent model review is advisory |
| Multi-turn trajectory | Does the tutor diagnose, scaffold, adapt, and recover across a session? | Scripted and model-assisted student trajectories with hidden state cards and trajectory-level scoring |
| Professor fidelity | Does the tutor follow the approved professor policy rather than a generic style? | Fixed T1/T2 comparisons and 8–12 professor- or expert-reviewed calibration conversations |
| Product workflow | Can real roles complete setup, publication, tutoring, review, withdrawal, and rollback? | Credentialed staging acceptance, usability tasks, operations traces, and recovery tests |
| Learning outcome | Does use improve learning or retention? | Separately approved human pilot with consent and pre/post or delayed assessment; never inferred from simulator scores |

## Metrics and gates

### Hard product gates

The candidate cannot pass with any critical occurrence of:

- unauthorized course, source, release, or student access;
- unsupported factual claim presented as course fact;
- invalid, invented, or cross-course citation;
- prohibited graded-work completion or critical policy violation;
- boundary case acquiring unsupported evidence;
- professor policy or source permission being changed by model output;
- unbounded graph execution, duplicate student turn, or corrupted resume;
- private or identifying data entering an unauthorized provider or log.

Expected provider failure, insufficient evidence, and malformed model output
pass only when the graph reaches the specified safe fallback and preserves the
student's input and state.

### Turn and trajectory measures

- learner-state classification accuracy and calibration;
- tutoring-intent transition validity;
- over-help and premature-answer rate;
- misconception identification and correction rate;
- appropriate adaptation after correct, incorrect, confused, irrelevant, and
  adversarial student turns;
- evidence support and citation completeness by modality;
- objective completion and transfer-question success;
- unnecessary turns, repeated questions, and conversational dead ends;
- state consistency across restart and release changes;
- p50/p95 time to first token and completed turn;
- provider calls, input/output tokens, cost per turn, and fallback rate.

Simulator measures support method debugging; they do not establish student
learning, satisfaction, or professor fidelity by themselves.

## Finite progression and stopping rule

1. **Graph-contract verification:** network-free state, transition, branch,
   loop-limit, fallback, and persistence tests.
2. **Development trajectories:** a compact stratified set covering direct
   questions, misconceptions, partial work, repeated confusion, requests for
   solutions, no evidence, multimodal evidence, and course-boundary attacks.
   Use it to calibrate labels and thresholds, not to claim product quality.
3. **One frozen confirmation:** run one untouched multi-turn confirmation after
   the method and thresholds are frozen. Do not start another sequence of
   prompt-only reruns.
4. **Professor calibration:** review 8–12 representative T1/T2 conversations
   before claiming Digital Twin fidelity.
5. **Hosted workflow evaluation:** test one immutable release through real
   administrator, professor, and student journeys.
6. **Invite-only human pilot:** evaluate usability first. Evaluate learning
   outcomes only under a separately approved study design.

A failed confirmation produces a method-level decision: change state tracing,
the transition policy, help ladder, evidence gate, or model role. It does not
automatically create another numbered dataset, prompt revision, or model
leaderboard.

## Relationship to supervisor guidance

On 2026-08-21 the professor replied “sounds good” after the deterministic
source-linked Q&A with multi-model wording/review and the separate C0-C3
Professor Digital Twin evaluation were proposed. The project therefore keeps
deterministic source lineage as the working factual-QA authority without
claiming approval of every evaluation parameter.

Professor guidance is still required before treating an explicit or inferred
professor profile as the fidelity reference. That unresolved choice does not
block the separately authorized factual-QA confirmation or implementation of
the generic T0/T1 tutoring graph contracts.

## Research basis

- LangGraph Graph API: <https://docs.langchain.com/oss/python/langgraph/graph-api>
- LangGraph workflow and agent patterns:
  <https://docs.langchain.com/oss/python/langgraph/workflows-agents>
- Puech et al., pedagogical intent transition graph:
  <https://aclanthology.org/2025.findings-acl.1348/>
- Qiu et al., planning-guided tutoring with assessment-driven memory:
  <https://aclanthology.org/2026.acl-long.325/>
- Shi et al., multi-horizon tutoring evaluation:
  <https://aclanthology.org/2026.acl-long.518/>
- Pisan, non-LLM help-level supervisor architecture:
  <https://arxiv.org/abs/2608.12292>
- IBM Docling document-processing project:
  <https://github.com/docling-project/docling>
