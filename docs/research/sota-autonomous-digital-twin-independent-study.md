# Independent study: a governed, fully autonomous Professor Digital Twin

Date: 2026-09-02

Study ID: `sota-autonomous-digital-twin-independent-study-001`

Status: independent, blinded research and design proposal; not a decision
record, not a release selection, and not an authorization for any provider,
paid, private-data, human-study, or release activity

Branch: `claude/sota-autonomous-digital-twin-study` (isolated worktree; no
change to `main`, evaluation instruments, historical results, generated
ledgers, hidden gold, or sealed datasets)

Companion documents:

- [Flow-independent evaluation design](sota-autonomous-digital-twin-evaluation-design.md)
- [Architecture decision and experiment plan](sota-autonomous-digital-twin-decision.md)

## 1. Purpose, isolation, and method

This study answers one question: what is the strongest practical architecture
for a Professor Digital Twin that continuously observes learner events,
maintains an evidence-based learner model, chooses learning goals, plans
pedagogical actions, contacts students proactively when justified, observes
outcomes, and replans safely, without per-action professor approval, while
staying inside professor-approved sources, course objectives, teaching policy,
consent, privacy, academic-integrity rules, release versions, frequency limits,
and a kill switch.

Blinding and isolation rules that were followed:

- The audit in section 2 read code and design documents only. No file under
  `reports/generated/`, `research/05_evaluation/records/`, or the result
  registry was opened, and no metric from any prior run is used as guidance.
  Where existing design documents quote earlier run outcomes, those numbers
  were deliberately not used to rank components.
- No model or provider API was called. Source verification used plain HTTP
  fetches of public pages. Every external source in section 3 was fetched on
  2026-09-02 and is cited with its canonical URL; sources that could not be
  fetched are listed as unverified rather than cited.
- Nothing outside the three documents under `docs/research/` was modified.

Method: (a) a code-level audit of the three tutoring modes and their shared
persistence, outreach, and grounding layers; (b) a primary-source literature
and official-documentation review across agent architecture, durable
execution, learner modelling, tutoring evaluation, proactive intervention,
safety, and model pricing; (c) four competing engine designs; (d) one
recommended successor defined to the level of interfaces, limits, and
migration; (e) an evaluation framework and decision matrix in the companion
documents. Repository line references refer to revision `8786375`.

## 2. Audit of the existing architecture

### 2.1 What exists

Three runtime modes share one service, one repository, and one SQLite schema
(`src/digital_twin/student/service.py:193-206` selects the mode per course from
`course_tutoring_runtime_profiles`, falling back to a process-wide setting).

| Mode | Entry | Shape | Model calls per turn |
| --- | --- | --- | --- |
| T0 grounded assistant | `StudentTutoringService.submit_message` (`service.py:260`) | Linear pipeline: authz, release binding, per-release retrieval, evidence gate, regex policy enforcer, one schema-validated generation, server-resolved citations, optional claim validation, atomic persist | 1 (plus a local query embedding) |
| T1-v1 reactive graph | `BoundedTutoringGraph` (`tutoring_graph.py:507-536`) | Nine LangGraph nodes: interpret, retrieve, select intent, generate, validate, repair, validate repair, fallback, finalize | 1 to 2 |
| T1-v2.1 governed autonomous graph | `GovernedReactiveTutoringGraphV2` (`tutoring_graph.py:900-937`) plus the proactive `GovernedAutonomousTutoringGraph` (`autonomy_runtime.py:434-472`) | Eleven reactive nodes with deterministic perception, belief update, constraint merge, evidence verification, pedagogy planning, generation, validation, one repair, and a commit boundary; a separate nine-node proactive graph driven by a leased worker | 0 to 3 reactive (optional semantic proposal, generation, repair); 0 to 3 proactive |

Around these sit: two learner models persisted side by side (v1
`LearnerState`, `tutoring_graph.py:131-167`; v2 `LearnerBeliefStateV2`,
`autonomy_models.py:290-310`); a goal, opportunity, plan, action, outcome, and
wake-up ledger (`autonomy_models.py:523-675`, tables in `migrations.py:482-616`);
an A0 outreach stack with preferences, triggers, messages, citations, and a
write-only delivery outbox (`migrations.py:370-442`); LangGraph SQLite
checkpoints plus request-hashed model-call ledgers
(`tutoring_graph.py:1396-1505`); and a fail-closed grounding chain shared by all
modes.

### 2.2 Event lifecycle as implemented

Reactive: the client request id is the idempotency key
(`service.py:276-296`); the v2 graph derives a deterministic event id and uses
it as the LangGraph thread id, so a crashed turn resumes from its checkpoint and
never repeats a completed provider call (`tutoring_graph.py:799-817`). Every
provider stage reserves a ledger row under `BEGIN IMMEDIATE`, replays a
completed row, and treats a `started` or `failed` row as an uncertain outcome
that is never retried (`tutoring_graph.py:1396-1505`). The graph node named
`atomic_commit_boundary` does not commit; the real transaction is
`repository.save_turn` after the graph returns (`repository.py:1213-1479`),
with optimistic revision checks on both learner models.

Proactive: opportunities are produced by three producers (turn follow-ups with
fixed +24 h and +48 h windows, an observer sweep that infers six event kinds
from persisted state, and wake-ups), each with a unique idempotency key
(`autonomy_service.py:458-650, 852-894`). A polling worker claims due
opportunities with leases (`repository.py:2385-2446`), runs the proactive graph,
delivers through the A0 trigger path, and commits plan, action, outcome, and
wake-up in one transaction (`repository.py:2448-2624`).

Two lifecycle defects were found in code:

1. Delivery precedes commit. `_deliver` runs before
   `commit_autonomous_job` (`autonomy_service.py:1007-1008`). The unique
   trigger key prevents a second message, but a crash between the two calls
   leaves a delivered message with a leased opportunity; on lease expiry the job
   re-runs, the trigger path reports `duplicate`, and the outcome is recorded as
   suppressed rather than delivered, so the attempt count is wrong for a message
   the student actually received.
2. Replanning is a constant. Every temporary block and every still-active goal
   schedules the next wake-up at exactly +24 h (`autonomy_runtime.py:862`);
   the plan's `replan_condition` is prose that nothing evaluates.

### 2.3 Learner belief state as implemented

The v2 estimator is deterministic and count based: attribution confidence is
`min(0.95, n / (n + 2))`, uncertainty is its complement
(`learner_belief.py:85-94`); concept attribution is bag-of-words overlap against
concept labels (`tutoring_graph.py:1547-1566`); attempt correctness is token
overlap with thresholds 0.45 and 0.20 (`tutoring_graph.py:1569-1605`).
Hypotheses carry expiry dates but the estimator regenerates the list from the
current observation on every revision (`learner_belief.py:100-104, 141-169`), so
nothing is ever confirmed, retracted, or decayed. Belief is keyed by
conversation, not by learner and course (`migrations.py:652-661`), so a second
conversation starts empty and the observer reads only the first conversation
(`autonomy_service.py:514-537`). Prerequisite links exist in the domain model
(`autonomy_models.py:136`) but are never used. There is no calibration path,
no forgetting curve, and no knowledge-tracing estimator.

### 2.4 Goals, plans, actions, outcomes as implemented

Goals are built by objective-to-evidence term overlap with fixed strings for
subgoal and success condition, priority 3 to 5, attempt limit 3, expiry +7 d
(`autonomy_control.py:185-252`). The only model-writable planning surface is
`AutonomousPlannerOutputV1` (`autonomy_models.py:665-675`), narrowed to an
event-scoped envelope with a deterministic fallback when the model leaves it
(`autonomy_eligibility.py:22-82`, `autonomy_runtime.py:227-235`). Outcomes are
observed through three hooks (dismissal, reply linkage with a heuristic
progress value, and a 24 h "practice incomplete" rule), and no code reads
outcomes to adapt help level, timing, or action choice. Two of the nine action
kinds are never eligible for any event.

### 2.5 Proactive outreach as implemented

Gating is triplicated: producer scope checks, the graph's eighteen boolean
`authorize` checks (`autonomy_runtime.py:529-585`), and the A0 delivery path's
own consent, snooze, quiet-hour, frequency, release, and chunk checks
(`proactive.py:552-692`). Two frequency ceilings (policy and student
preference) are evaluated at different points. Quiet hours are implemented
twice with different code. The kill switch is a per-course policy field
(`autonomy_models.py:323`); there is no global or process-level kill switch and
no policy-independent rate limiter. Delivery is in-app only; the Discord outbox
is written but never drained.

### 2.6 Grounding controls as implemented

Scope, release binding, permission lineage, no-evidence, and citation validity
are enforced in code rather than by prompt: eligibility filtering at chunk and
retrieval level (`grounding/retrieval.py:448-471`), a fail-closed evidence gate
(`service.py:1053-1068`), server-owned citation ids and `extra="forbid"`
output models (`generation/prompt.py:30-33`, `generation/models.py`), and
citation materialisation that rejects any citation not matching exactly one hit
(`service.py:1393-1443`). Two weaknesses: atomic-claim extractiveness is
prompt-only in default T0 wiring because the factory constructs the claim
validator only for the autonomy mode (`services/api/app/factory.py:223-231`),
and the deterministic fallback generator's "atomic claim" is the entire first
chunk, which makes exact-quote validation trivially pass
(`service.py:1195-1223`).

### 2.7 Professor profile and policy as implemented

`TutorPolicy` exists and six of its fourteen fields reach the prompt as JSON
(`generation/prompt.py:44-79`). The `ProfessorProfile` named in
`docs/architecture.md` does not exist as a class; the nearest object,
`TeachingProfileV1`, is hash-bound to the release but never read by generation
or planning. No runtime code checks tone, approach, or help-ladder adherence.

### 2.8 Model roles and interfaces as implemented

The provider seam is `LlmClient.chat(messages, task) -> LlmResponse`
(`src/digital_twin/llm.py:113-115`) with a typed error taxonomy. Engine swaps
without code changes work only inside the OpenAI candidate allowlist; the
factory hard-wires both planners to one model with a per-process budget wrapper
(`factory.py:236-256`). Prompt versions are string labels without content
hashes. Deterministic planners bypass the model-call ledger and checkpoint
requirement, so restart behaviour differs between deterministic and live
configurations (`tutoring_graph.py:1196`, `autonomy_runtime.py:623, 655`).

### 2.9 Assessment

**Genuinely strong, and should be retained.**

- Authority separation is real: models fill two schema-closed proposal
  contracts, every id they emit is checked against a closed set, and no model
  output can mutate identity, membership, release, policy, consent, or delivery.
- Exactly-once mechanics are layered and mutually reinforcing: request-hashed
  call ledgers, deterministic thread ids, optimistic revisions, unique
  idempotency keys at every producer, lease claims with expiry, and
  binding-hash commits.
- Lineage pinning (release, profile hash, policy version, graph version, model
  ids) on every durable record, with cascade cancellation on publish, withdraw,
  consent change, kill switch, pause, and policy change.
- The fail-closed grounding chain and the action lattice
  (`operational > refuse > clarify > abstain > answer`).
- An injectable clock and a fully network-free deterministic configuration.
- Two flow-independent evaluation contracts already exist
  (`evaluation/factual_qa_contract.py:173`, `evaluation/autonomy_contract.py:272`).

**Accidental complexity.**

- Two learner models persisted side by side, with v2 still mutating v1 fields
  and goal and outcome logic branching on both.
- Three intent and action vocabularies with lossy maps between them, plus a
  fourth vocabulary in the design documents.
- Two proactive stacks; a governed action must be laundered through an A0
  trigger to be delivered.
- Triplicated eligibility checks, duplicated quiet-hour and source-range
  helpers with different checksum fallbacks.
- Pseudo-nodes injected into trace paths, a commit node that does not commit,
  a hard-coded proactive node path, and gate decisions transported through
  audit-event dictionaries.
- One 3,430-line repository module and one 1,543-line service module that
  contain every mode.

**What structurally prevents state of the art.**

- No learner model in the accepted sense: no knowledge tracing, no calibration,
  no decay, no prerequisite propagation, per-conversation rather than
  per-learner belief, and hypotheses that are overwritten rather than updated.
- No outcome-driven policy: fixed decision tables, constant wake-up interval,
  constant windows; outcomes are recorded but never consulted.
- No forward model: nothing predicts the effect of an action on the learner,
  so goal selection, opportunity ranking, and replanning cannot be value based.
- No fast-path and planner separation in the proactive graph; in the reactive
  graph the fast path is a boolean that skips one call.
- Per-node token, latency, and cost limits promised by the design do not exist
  in the graphs; the student message is passed verbatim to the planner.
- Lexical grounding only (token-overlap gate, exact-quote claim validation).
- The delivery-before-commit ordering and the absence of a global kill switch.

These findings are structural. They are not judgments about the quality of
the evaluation results, which this study did not read.

## 3. Research synthesis from primary sources

Every source below was fetched on 2026-09-02. Peer-reviewed venues and arXiv
originals are preferred; official vendor or framework documentation is marked
as such; nothing marketing-only is used as evidence. Where a publisher blocked
the page, the metadata and abstract were verified through OpenAlex, Semantic
Scholar, Europe PMC, or the author's preprint, and the entry says so. Sources
that could not be verified are listed at the end of the section, not cited.

### 3.1 Autonomous and long-horizon agent architectures

| Source | What it establishes for this design |
| --- | --- |
| Yao et al., ReAct, ICLR 2023, <https://arxiv.org/abs/2210.03629> | Interleaving reasoning with actions and observations beats act-only and reason-only baselines (+34 and +10 absolute points on ALFWorld and WebShop). The loop shape of one decision, one action, one observation is the right unit. |
| Shinn et al., Reflexion, NeurIPS 2023, <https://arxiv.org/abs/2303.11366> | A verbal record of failures across attempts improves later attempts without weight updates. In this design the equivalent is the outcome ledger read by the next episode plan, not free-text memory. |
| Park et al., Generative Agents, UIST 2023, <https://arxiv.org/abs/2304.03442> | Memory stream with recency, importance, and relevance retrieval, periodic reflection, and replanning on observation. Ablations show each component contributes. A source of the observe-reflect-replan structure, not of any pedagogical claim. |
| Wang et al., Voyager, 2023, <https://arxiv.org/abs/2305.16291> | A growing library of verified skills plus an automatic curriculum yields long-horizon competence. The analogue here is a professor-approved, versioned move vocabulary and policy envelope, not a self-extending skill set. |
| Yao et al., Tree of Thoughts, NeurIPS 2023, <https://arxiv.org/abs/2305.10601>; Zhou et al., LATS, ICML 2024, <https://arxiv.org/abs/2310.04406> | Search over candidate plans with self-evaluation buys large gains on puzzle-like tasks at several times the token cost. Justifies bounded lookahead at the episode level only, where it is amortised. |
| Yang et al., SWE-agent, NeurIPS 2024, <https://arxiv.org/abs/2405.15793>; Wang et al., OpenHands, ICLR 2025, <https://arxiv.org/abs/2407.16741> | The interface between agent and environment matters as much as the model, and a single event stream of actions and observations is a workable substrate for a general agent. Supports the event-sourced lifecycle in section 5.1. |
| Chen, Wang, Qu, The Horizon Gap (survey of 1,547 papers), 2026, <https://arxiv.org/abs/2608.06663> | Outcome-only signals grow uninformative as horizons lengthen; the field responds with denser step-level signals. Supports per-step expected observations and stop predicates in episode plans. |
| Khanal, Tao, Zhou, Beyond pass@1, 2026, <https://arxiv.org/abs/2603.29231> | Reliability decays with horizon and is domain-dependent (10 models, 23,392 episodes; frontier models showed a 19% "meltdown" rate). Supports hard per-episode and per-learner limits rather than trust in the model. |
| Zhang et al., AFlow, ICLR 2025, <https://arxiv.org/abs/2410.10762> | Static workflows that encode domain procedure can beat dynamic agents; small models beat GPT-4o on some tasks at 4.55% of its inference cost. Justifies candidate A as a serious baseline. |
| Anthropic, Building effective agents (official vendor guidance, not peer reviewed), <https://www.anthropic.com/research/building-effective-agents> | Recommends starting with single optimized calls and adding agentic complexity only when simpler solutions demonstrably underperform. |

### 3.2 Planning, acting, observing, replanning

| Source | What it establishes |
| --- | --- |
| Liu et al., LLM+P, 2023, <https://arxiv.org/abs/2304.11477>; Kambhampati et al., LLM-Modulo, ICML 2024, <https://arxiv.org/abs/2402.01817> | Autoregressive models do not reliably plan or self-verify; gains appear when an external sound verifier or solver closes the loop. This is the strongest argument for deterministic validation of every proposal and against a model critic as the authority. |
| Wang et al., Plan-and-Solve, ACL 2023, <https://arxiv.org/abs/2305.04091> | Explicit plan-then-execute prompting reduces missing-step errors. Supports a typed plan object rather than an implicit one. |
| Prasad et al., ADaPT, NAACL 2024 Findings, <https://arxiv.org/abs/2311.05772>; Sun et al., AdaPlanner, NeurIPS 2023, <https://arxiv.org/abs/2305.16653>; Song et al., LLM-Planner, ICCV 2023, <https://arxiv.org/abs/2212.04088> | Decomposition and replanning help when conditional on executor failure or feedback (up to +28 points), not when always on. The replan predicates in section 5.4 are this principle. |
| Hao et al., RAP, EMNLP 2023, <https://arxiv.org/abs/2305.14992>; Gu et al., WebDreamer, 2024, <https://arxiv.org/abs/2411.06559> | Using a world model to simulate outcomes of candidate actions before acting improves sequential decisions and avoids irreversible mistakes at four to five times the efficiency of tree search. The forward model in candidate C is the analytic, calibratable version of this idea. |
| Li et al., Task-Decoupled Planning, 2026, <https://arxiv.org/abs/2601.07577> | Reasoning on each sub-task's local context instead of the whole history cuts tokens by up to 82% and localises error correction. Supports the compact state card over raw history. |
| Li et al., Embodied Agent Interface, NeurIPS 2024 D&B, <https://arxiv.org/abs/2410.07166> | A fine-grained error taxonomy for goal interpretation, decomposition, sequencing, and transition modelling. The specific replanning gains attributed to its appendix by search snippets could not be confirmed from the fetched page and are not used. |

### 3.3 Durable execution and event-driven agents (official documentation)

| Source | What it establishes |
| --- | --- |
| LangGraph persistence, <https://docs.langchain.com/oss/python/langgraph/persistence>; checkpointers, <https://docs.langchain.com/oss/python/langgraph/checkpointers>; interrupts, <https://docs.langchain.com/oss/python/langgraph/interrupts>; Functional API, <https://docs.langchain.com/oss/python/langgraph/functional-api> | Thread-scoped checkpoints per super-step with three durability modes (`exit`, `async`, `sync`); pending writes avoid re-running completed nodes in a failed super-step; on resume an interrupted node re-runs from its start, so code before an interrupt must be idempotent; non-deterministic operations belong inside tasks. |
| Temporal workflow definition, <https://docs.temporal.io/workflow-definition>; workflows, <https://docs.temporal.io/workflows>; activities, <https://docs.temporal.io/activities>; retry policies, <https://docs.temporal.io/encyclopedia/retry-policies> | Workflow code must be deterministic under replay of the event history; activities encapsulate side effects, are at-least-once, and must be idempotent; recorded activity results are reused on replay. |
| Inngest steps, <https://www.inngest.com/docs/features/inngest-functions/steps-workflows>; Restate durable execution, <https://docs.restate.dev/concepts/durable_execution> | Steps are memoised checkpoints; a journal of side-effect results lets a handler replay with completed steps skipped. |
| Cloudflare Agents SDK, <https://developers.cloudflare.com/agents/api-reference/agents-api/> | A durable per-entity object with embedded SQLite, synchronised state, and scheduling is one deployable shape for a per-learner agent; noted as an option, not adopted. |
| Richardson, Transactional outbox, <https://microservices.io/patterns/data/transactional-outbox.html> | Write the message to an outbox in the same transaction as the business update; a relay publishes at-least-once; consumers must be idempotent. This is the delivery model in section 5.1 and the fix for the ordering defect in section 2.2. |

All five agree on one model: journal every side effect's result, replay
deterministically, treat side effects as at-least-once, and achieve
exactly-once at the application layer with keys and deduplication. The
repository already does this for provider calls; the successor applies it to
every side effect.

### 3.4 Single-agent versus multi-agent

| Source | What it establishes |
| --- | --- |
| Cemri et al., Why do multi-agent LLM systems fail?, 2025, <https://arxiv.org/abs/2503.13657> | Fourteen failure modes from 1,600+ traces across seven frameworks; most are specification, coordination, and verification failures rather than model-capability failures. |
| Kim et al., Towards a science of scaling agent systems, 2025 to 2026, <https://arxiv.org/abs/2512.08296> | Controlled comparison of single-agent against four multi-agent topologies over 260 configurations: from +80.8% on decomposable financial reasoning to −70.0% on sequential planning; the coordination benefit shrinks as the single-agent baseline rises. |
| Bogavelli et al., AgentArch, 2025, <https://arxiv.org/abs/2509.10769> | Best configurations reached only 35.3% on complex enterprise tasks; the best architecture is model-specific. |
| Li et al., Single-agent vs multi-agent strategies for student reflection assessment, PAKDD 2025, <https://arxiv.org/abs/2504.05716> | On an education task (5,278 reflections), a single few-shot agent agreed most with human graders, beating multi-agent variants. |
| Li, When single-agent with skills replace multi-agent systems, 2026, <https://arxiv.org/abs/2601.04748> | A single agent with a skill library reproduces multi-agent benefits at lower cost until skill confusability grows. |
| Hong et al., MetaGPT, ICLR 2024, <https://arxiv.org/abs/2308.00352>; Wu et al., AutoGen, 2023, <https://arxiv.org/abs/2308.08155>; Li et al., CAMEL, NeurIPS 2023, <https://arxiv.org/abs/2303.17760>; Qian et al., ChatDev, ACL 2024, <https://arxiv.org/abs/2307.07924> | The canonical multi-agent frameworks; their gains are reported on decomposable software tasks with structured hand-offs, which is not the shape of a tutoring decision. |
| Anthropic, multi-agent research system (official vendor engineering post), <https://www.anthropic.com/engineering/built-multi-agent-research-system> | Vendor-internal 90.2% gain on a parallel research task, with roughly fifteen times the tokens of chat. Not generalisable and not used as evidence for tutoring. |

Conclusion for this design: a tutoring decision is sequential and tool heavy,
which is the regime where the controlled evidence shows multi-agent designs
hurting. Candidate D is therefore defined as a single testable verifier step,
not as the recommendation.

### 3.5 Agent memory and uncertainty

| Source | What it establishes |
| --- | --- |
| Packer et al., MemGPT, 2023, <https://arxiv.org/abs/2310.08560>; Xu et al., A-MEM, NeurIPS 2025, <https://arxiv.org/abs/2502.12110>; Chhikara et al., Mem0, 2025, <https://arxiv.org/abs/2504.19413> | Structured, evolving memory with paging or linking beats full-context recall on conversational benchmarks with large token savings. Their evidence is about recall, not about long-horizon task execution, so this design uses a typed evidence ledger and state card rather than free-text agent memory. |
| Tian et al., Just ask for calibration, EMNLP 2023, <https://arxiv.org/abs/2305.14975>; Kadavath et al., Language models (mostly) know what they know, 2022, <https://arxiv.org/abs/2207.05221> | Verbalised confidence from RLHF models is better calibrated than token probabilities (about 50% relative ECE reduction) but far from perfect. Model confidence is therefore advisory and never a learner-state estimate. |
| Farquhar et al., Semantic entropy, Nature 630, 2024, <https://www.nature.com/articles/s41586-024-07421-0> | Entropy over meaning clusters detects confabulation (AUROC 0.79 vs 0.69). A candidate advisory signal for the generator; not a substitute for the deterministic claim validator. |
| Wen et al., Abstention survey, TACL 2024, <https://arxiv.org/abs/2407.18418> | Frames abstention along query, knowledge, and values axes with metrics. The action lattice's `abstain` and `clarify` are the operational form. |

### 3.6 Learner modelling, tutoring effectiveness, and pedagogical evaluation

Learner modelling.

| Source | What it establishes |
| --- | --- |
| Corbett and Anderson, Knowledge tracing, UMUAI 1995, <https://doi.org/10.1007/BF01099821> (metadata via OpenAlex; page not machine-readable) | Two-state hidden Markov model per skill with four parameters; the default estimator in section 5.3. |
| Piech et al., Deep Knowledge Tracing, NeurIPS 2015, <https://arxiv.org/abs/1506.05908>; Pandey and Karypis, SAKT, EDM 2019, <https://arxiv.org/abs/1907.06837>; Ghosh et al., AKT, KDD 2020, <https://arxiv.org/abs/2007.12324>; Abdelrahman et al., KT survey, 2022, <https://arxiv.org/abs/2201.06953> | Deep and attention-based tracing gains 4 to 6 AUC points on large logs. |
| Gervet et al., When is deep learning the best approach to knowledge tracing?, JEDM 2020, <https://eric.ed.gov/?id=EJ1273917> | Nine datasets: logistic models win with moderate data or long histories, DKT wins only on large datasets; evaluates calibration as the downstream requirement. |
| Bhattacharjee and Wayllace, Cold start in KT, 2025, <https://arxiv.org/abs/2505.21517> | All deep tracing models perform poorly on new students' first interactions. |
| Pelánek, Elo in adaptive systems, Computers & Education 2016, <https://doi.org/10.1016/j.compedu.2016.03.017>; Pelánek, BKT, logistic models, and beyond, UMUAI 2017, <https://doi.org/10.1007/s11257-017-9193-2> (abstracts via author preprints) | Elo and PFA are robust, cheap, and calibratable with small data; model choice should follow purpose and evaluation, which is why section 5.3 selects by Brier and calibration rather than by architecture. |
| Bull and Kay, SMILI open learner models, IJAIED 2016, <https://doi.org/10.1007/s40593-015-0090-8> (metadata via OpenAlex) | Framework for what a learner model shows to whom with what control; basis for the learner-visible explanation in section 5.11. |

Tutoring effectiveness and learning-science mechanisms.

| Source | What it establishes |
| --- | --- |
| VanLehn, Relative effectiveness of human tutoring, ITS, and other tutoring, Educational Psychologist 2011, <https://doi.org/10.1080/00461520.2011.611369> (abstract via OpenAlex) | Step-based tutoring d ≈ 0.76, substep d ≈ 0.79, human tutoring d ≈ 0.79; the 2.0 figure is refuted. |
| Kulik and Fletcher, ITS meta-analysis, RER 2016, <https://doi.org/10.3102/0034654315581420> (abstract via OpenAlex) | Median effect 0.66 SD across 50 evaluations; smaller on standardised tests. |
| Koedinger, Corbett, Perfetti, KLI framework, Cognitive Science 2012, <https://doi.org/10.1111/j.1551-6709.2012.01245.x> (abstract via Semantic Scholar) | Maps knowledge-component types to learning processes and instructional principles; the basis for choosing a move by concept type. |
| Aleven et al., Example-tracing tutors, IJAIED 2016, <https://doi.org/10.1007/s40593-015-0088-2> (abstract via OpenAlex) | Authoring by demonstration is four to eight times more cost-effective than classic ITS development; supports professor-authored policy envelopes over learned policies. |
| Kulik, Kulik, Bangert-Drowns, Mastery learning meta-analysis, RER 1990, <https://doi.org/10.3102/00346543060002265>; Cepeda et al., Distributed practice, Psychological Bulletin 2006, <https://doi.org/10.1037/0033-2909.132.3.354>; Roediger and Karpicke, Test-enhanced learning, Psychological Science 2006, <https://doi.org/10.1111/j.1467-9280.2006.01693.x> (abstracts via OpenAlex) | Mastery criteria, spacing with intervals that grow with the retention interval, and retrieval practice each have strong meta-analytic support and are implementable as deterministic scheduling policy. |
| Kestin et al., AI tutoring outperforms in-class active learning, Scientific Reports 2025, <https://doi.org/10.1038/s41598-025-97652-6> (full text via Europe PMC) | Crossover RCT, 194 analysed; effect 0.63 SD or larger; the tutor was tightly scripted to the class pedagogy. Evidence for scripted, policy-bound tutoring, not for open-ended tutoring. |
| Bastani et al., Generative AI without guardrails can harm learning, PNAS 2025, <https://doi.org/10.1073/pnas.2422633122> (abstract via OpenAlex; a correction exists) | Unrestricted access cut unassisted exam performance by 17% versus no AI; a guardrailed tutor removed the harm. The answer ceiling is a learning requirement, not only an integrity one. |
| Wang et al., Tutor CoPilot, 2024 to 2025, <https://arxiv.org/abs/2410.03017> | RCT with 900 tutors and 1,800 students: +4 points mastery, +9 for students of lower-rated tutors; tutors asked more guiding questions and gave fewer direct answers. |

Pedagogical planning and tutoring-dialogue evaluation.

| Source | What it establishes |
| --- | --- |
| Macina et al., MathDial, EMNLP 2023 Findings, <https://arxiv.org/abs/2305.14536> | Models reveal solutions too early by default; evaluates the trade-off between student success and telling. |
| Wang et al., Bridging the novice-expert gap, NAACL 2024, <https://arxiv.org/abs/2310.10648> | Conditioning generation on an explicit expert decision (error type, strategy, intention) raised preference by 76%; random decisions cut quality by 97%. Direct support for plan-then-generate with a typed move. |
| Tack and Piech, AI teacher test, EDM 2022, <https://arxiv.org/abs/2205.07540> | Human raters found models below teachers on helpfulness. |
| LearnLM team, Google, Improving Gemini for learning (official vendor technical report), <https://arxiv.org/abs/2412.16429>; Google, LearnLM page, <https://ai.google.dev/gemini-api/docs/learnlm> | Pedagogical instruction following via system-prompted attributes with expert-rater preference gains; LearnLM is now folded into Gemini and is not a separate model. |
| Maurya et al., MRBench, NAACL 2025, <https://arxiv.org/abs/2412.09416>; Macina et al., MathTutorBench, EMNLP 2025, <https://arxiv.org/abs/2502.18940>; Srinivasa et al., TutorBench, 2025, <https://arxiv.org/abs/2510.02663>; Xu et al., EduBench, 2025, <https://arxiv.org/abs/2505.16160> | Rubric dimensions for single turns and short dialogues; problem-solving skill does not transfer to teaching; quality degrades in longer dialogues; no frontier model above 56% on TutorBench. None measures learning. |
| Liu et al., SocraticLM, NeurIPS 2024, <https://proceedings.neurips.cc/paper_files/paper/2024/hash/9bae399d1f34b8650351c1bd3692aeae-Abstract-Conference.html> | Simulated student profiles used to build Socratic training dialogues; a precedent for held-out simulated learners in evaluation. |

### 3.7 Proactive intervention and learning analytics

| Source | What it establishes |
| --- | --- |
| Arnold and Pistilli, Course Signals, LAK 2012, <https://doi.org/10.1145/2330601.2330666>; Jayaprakash et al., Early alert, JLA 2014, <https://doi.org/10.18608/jla.2014.11.3> | Early-warning systems delivered by instructors; effects on withdrawal rather than grades; later disputes about retention claims. |
| Oreopoulos and Petronijevic, NBER 26059 (2019) and Economic Journal 2023, <https://www.nber.org/papers/w26059>, <https://doi.org/10.1093/ej/uead064> | 20,000 to 25,000 students over five years: low-touch coaching and texts moved study time slightly and moved no grade or credit outcome. |
| Bird et al., Nudging at scale, JEBO 2021, <https://doi.org/10.1016/j.jebo.2020.12.022> | Over 800,000 students, two RCTs: no effect overall or in any subgroup; framing, timing, and advising variants made no difference. |
| Kizilcec et al., Scaling up behavioral science interventions, PNAS 2020, <https://doi.org/10.1073/pnas.1921417117> (abstract via Semantic Scholar) | 250,000 learners in 247 courses: prompts raised early engagement but not completion; effects fell by an order of magnitude at scale; minimal evidence that ML targeting helps. |
| Damgaard and Nielsen, Nudging in education, EER 2018, <https://doi.org/10.1016/j.econedurev.2018.03.008> (abstract via Semantic Scholar) | Nudges help those facing the targeted barrier and can backfire by crowding out motivation or adding pressure. |
| Lu et al., Proactive Agent, 2024, <https://arxiv.org/abs/2410.12361> | Frames proactivity as predicting whether unsolicited help will be accepted, with a reward model trained on human judgments. |

The consequence for this design is that a proactive message is an
intervention with a prior of roughly zero effect. Section 5.7 therefore
requires an expected-effect margin over `no action`, forbids counting opens and
clicks as effect, and the evaluation design treats proactive quality as a
pre-registered outcome.

### 3.8 Safety, consent, privacy, and academic integrity

| Source | What it establishes |
| --- | --- |
| Regulation (EU) 2024/1689, Annex III point 3, <https://eur-lex.europa.eu/eli/reg/2024/1689/oj> | Systems that evaluate learning outcomes, including to steer the learning process, are high-risk uses in education. An autonomous twin that grades and steers plausibly falls under point 3(b). |
| US Department of Education, FERPA, <https://studentprivacy.ed.gov/ferpa> | Disclosure of education records to a contractor without consent is allowed only under direct institutional control with redisclosure limits. |
| US Department of Education OET, Designing for education with AI, 2024, <https://files.eric.ed.gov/fulltext/ED661949.pdf> | Requires evidence of rationale and impact, safety, transparency, and humans in the loop. |
| UNESCO, Guidance for generative AI in education and research, 2023, <https://www.unesco.org/en/articles/guidance-generative-ai-education-and-research> | Data-privacy protection, age limits for independent use, human-agency-centred design, and ethical validation before classroom use. |
| Zhao, Knežević, Käser, Answer leakage robustness of LLM tutors, 2026 preprint, <https://arxiv.org/abs/2604.18660> | Fine-tuned adversarial students extract withheld solutions; simple defences reduce leakage. The answer ceiling must be tested adversarially, which the evaluation design does. |

### 3.9 Model allocation from official pricing (accessed 2026-09-02)

Sources: Anthropic pricing and models, <https://platform.claude.com/docs/en/about-claude/pricing>, <https://platform.claude.com/docs/en/about-claude/models/overview>, prompt caching, <https://platform.claude.com/docs/en/build-with-claude/prompt-caching>, batch, <https://platform.claude.com/docs/en/build-with-claude/batch-processing>; OpenAI pricing and models, <https://developers.openai.com/api/docs/pricing>, <https://developers.openai.com/api/docs/models>, caching, <https://developers.openai.com/api/docs/guides/prompt-caching>; Google pricing, <https://ai.google.dev/gemini-api/docs/pricing>, caching, <https://ai.google.dev/gemini-api/docs/caching>; DeepSeek pricing, <https://api-docs.deepseek.com/quick_start/pricing>, caching, <https://api-docs.deepseek.com/guides/kv_cache>; open-weight cards at <https://huggingface.co/Qwen>, <https://huggingface.co/deepseek-ai>, <https://mistral.ai/news/mistral-small-4/>, <https://openai.com/open-models/>.

Prices in USD per million tokens, input / output / cached input, as published
on the access date. Vendor benchmark claims on these pages are not used.

| Tier | Representative models | Price | Role in section 5.2 |
| --- | --- | --- | --- |
| Frontier | Claude Fable 5.1 (10 / 50 / 0.25); Claude Opus 5 (5 / 25 / 0.50); GPT-5.6 Sol (4 / 20 / 0.40); Gemini 3.1 Pro Preview (2 / 12 / 0.20) | | Episode planner only, batchable, amortised over steps; candidate for the offline judge panel |
| Mid | Claude Sonnet 5 (2 / 10 / 0.20); GPT-5.6 Terra (2 / 12 / 0.20); DeepSeek V4-Pro (1.32 / 3.96 / 0.044) | | Turn planner; optional verifier test |
| Small | Claude Haiku 4.5 (1 / 5 / 0.10); GPT-5.6 Luna (0.20 / 1.20 / 0.02); Gemini 3.7 Flash (0.75 / 3.75 / 0.075 promotional until 2026-12-31); DeepSeek V4-Flash (0.44 / 1.32 / 0.014) | | Perceiver, generator, wording |
| Open weight, self-hosted | Qwen3.8-27B (Apache 2.0); Mistral Small 4 (Apache 2.0); gpt-oss-120b/20b (Apache 2.0); DeepSeek V4 weights (MIT) | hardware cost only | Deterministic-adjacent fallback tier and privacy-sensitive deployments; must pass the same paired evaluation |

Ratios that drive the allocation: output is five to six times input on every
vendor; frontier output is roughly forty times small-model output across
vendors and ten times within Anthropic; cache reads are one tenth of input
(one fortieth on Fable 5.1); batch is a flat 50% on all four vendors and
stacks with caching; DeepSeek halves prices off-peak and Gemini 3.7 Flash
doubles on 2027-01-01, so budgets use non-promotional rates. Minimum cacheable
prefix lengths (512 tokens on Anthropic 5.x, 1,024 on GPT-5.6, 4,096 on Gemini
3.x) set the floor for the stable prompt prefix in section 5.2.

The repository's current allowlist is OpenAI-only (`model_policy.py`); the
registry in section 5.10 removes that restriction so that any tier above can be
evaluated under identical conditions.

### 3.10 Sources that could not be verified and are not used

- Kafka delivery-semantics documentation (the docs site served a redirect page).
- Replanning success-rate figures attributed to Embodied Agent Interface
  Appendix H by search snippets.
- The Nature Machine Intelligence version of Kim et al.; the arXiv original is
  cited.
- OpenAI's GPT-5.6 launch post (HTTP 403); pricing and limits come from the
  developer documentation instead.
- UNESCO's PDF (HTTP 403); the official landing page is cited.

## 4. Competing engine architectures

All four candidates share the retained substrate from section 2.9: the
fail-closed grounding chain, the action lattice, release and profile binding,
consent and frequency enforcement in code, request-hashed provider ledgers,
idempotent commits, cascade cancellation, and the injectable clock. They differ
in who decides, how far ahead they look, and how many model calls they spend.

The candidates are ordered by decision complexity, and each later candidate is
defined as the previous one plus one mechanism. This is deliberate: it makes
every comparison a one-factor ablation rather than a comparison of two
unrelated systems.

### 4.1 Candidate A: deterministic workflow baseline

Definition. No model participates in any decision. A model is called at most
once per delivered message, for wording only, inside the existing grounded
generator. Perception is regex and lexical attribution; the learner model is an
evidence ledger with counts; goals are the professor's published objectives in
order; proactive actions come from a fixed trigger table (scheduled review,
evidence recovery after a source change, student-requested follow-up); timing
is fixed by policy; the fast path is the whole system.

Why it belongs in the set. It is the cleaned-up version of what the repository
already runs network-free. Evidence from workflow-versus-agent studies
(section 3, AFlow; Anthropic's official guidance; the enterprise agent
benchmark) is that predefined code paths often match dynamic agents on
well-specified tasks at a fraction of the cost. If a more complex candidate
cannot beat A on pedagogy and proactive quality under identical grounding, the
complexity is not earned.

Structural ceiling. A cannot handle novel misconceptions, cannot choose between
pedagogical moves on the basis of learner state beyond counts, and its
proactive timing is policy constant. It is a floor, not a destination.

### 4.2 Candidate B: governed single-agent planner

Definition. A plus one typed planner call per decision point. The planner is a
single model call that receives a compact learner state card, the eligible
action envelope, the professor policy summary, and the evidence summary, and
returns one proposal: a pedagogical move, a help level, an evidence
requirement, and a proposed observation to look for next. Deterministic code
validates the proposal against the envelope, executes it through the fast
path, and records the outcome. The learner model gains a calibrated estimator
interface (a Bayesian Knowledge Tracing or Performance Factors Analysis
baseline, selected by calibration against assessed opportunities) keyed by
learner and course rather than by conversation. Goals get explicit success
criteria and budgets. Replanning becomes conditional: a follow-up is scheduled
only when a stop or replan predicate written in a small closed vocabulary is
true, not on a constant interval.

Why it belongs in the set. It is the current v2.1 design with its accidental
complexity removed and its promised mechanisms (calibration, decay, conditional
replanning, per-learner belief) actually built. The agent literature supports
this shape: interleaved reason-act-observe loops beat act-only baselines, and
decomposition or replanning helps when it is conditional on feedback rather
than always on (ReAct, ADaPT, AdaPlanner, LLM-Planner in section 3).

Structural ceiling. B still selects actions greedily. It cannot compare two
candidate interventions by expected learning effect, cannot decide that the
best action today is no action because a better one becomes available
tomorrow, and cannot rank opportunities across learners under a course-wide
budget.

### 4.3 Candidate C: hierarchical, model-based planner

Definition. B plus a forward model and three planning horizons.

- Turn level (seconds): the fast path from A and the typed planner from B.
- Episode level (hours to days): a per-learner, per-goal plan of at most a
  small fixed number of steps, each step being one intervention with an
  expected observation and a stop or replan predicate. Steps are proposed by a
  model and validated by code. The episode plan is regenerated only when a
  replan predicate fires (surprise: an observation that the forward model gave
  low probability) or on goal completion, expiry, or a governance change.
- Course level (days to weeks): deterministic goal selection and opportunity
  ranking across a learner's objectives and across learners, using expected
  learning gain per unit cost from the forward model, under the frequency and
  cost budgets, with `no action` as the default.

The forward model is an explicit, replaceable interface that predicts the
distribution of the next observation given the learner belief and a candidate
action. Its first implementation is not learned: it is the same knowledge
tracing estimator run forward under the standard assumptions of the estimator
(a correct assessed response raises the mastery posterior by a known amount;
an unassessed message contributes evidence but not mastery). A learned or
model-simulated forward model becomes selectable only if it is better
calibrated than the analytic one on held-out trajectories.

Why it belongs in the set. Model-based planning with a world model (RAP,
WebDreamer, and the LLM-Modulo argument in section 3) is where the agent
literature reports the largest gains on sequential decision tasks, and it is
the only shape that can justify proactive contact by expected effect rather
than by trigger match. Established intelligent tutoring systems separate an
outer loop (task selection) from an inner loop (within-task steps), which is
exactly the course and turn split here. The learning-science evidence on
spacing and retrieval practice (section 3) gives the forward model a
principled prior for the timing of review interventions without a learned
policy.

Structural risk. The forward model can be wrong in a way that is hard to see:
a badly calibrated estimator will make confident bad recommendations. This is
why C is defined so that turning the lookahead depth to zero recovers B
exactly, and why the evaluation design measures calibration separately from
pedagogy.

### 4.4 Candidate D: multi-agent design

Definition. C plus separate model roles that talk to each other at decision
time: a planner agent, an independent critic or verifier agent that can reject
or amend the planner's proposal, and a simulated-student agent used to
role-play the effect of a candidate message before it is sent.

Why it is included, and why it is not recommended. The one clear, testable
advantage a second model role can offer is independent verification, and the
planning literature is explicit that verification must be external and sound,
not another sample from the same model (LLM-Modulo in section 3). The
controlled comparisons of single-agent against multi-agent topologies (Kim et
al., Cemri et al., the enterprise benchmark, and the student-reflection
grading study in section 3) find that multi-agent systems help on decomposable
parallel tasks and hurt on sequential planning and tool-heavy tasks, and that
most multi-agent failures are specification and coordination failures. A
tutoring decision is sequential and tool heavy. The simulated-student role is
also already provided at evaluation time by the framework in the companion
document, where it can be held out and checked, rather than at decision time
where it would be an unverified oracle.

D is therefore defined only as a test: a verifier call that must reduce the
rate of pedagogical and policy defects on a fixed proposal set by more than
its added cost and latency, measured under the evaluation design. If it does,
the verifier becomes one more deterministic-validation-plus-one-model-call step
inside C, not a conversation between agents.

### 4.5 Summary of the four candidates

| Property | A deterministic | B single planner | C hierarchical model-based | D multi-agent |
| --- | --- | --- | --- | --- |
| Model calls per student turn | 0 to 1 | 1 to 2 | 1 to 2 | 2 to 4 |
| Model calls per proactive decision | 0 to 1 | 1 to 2 | 1 to 2 (episode plan amortised) | 3 to 5 |
| Learner model | evidence counts | calibrated estimator, decay, per-learner | B plus forward prediction | same as C |
| Goal selection | objective order | rule-scored | expected gain per cost under budget | same as C |
| Replanning | fixed interval | conditional predicate | surprise-triggered with lookahead | same as C plus critic |
| Proactive justification | trigger match | trigger plus eligible action | expected effect versus no action | same as C |
| Failure modes that are new | none | planner leaves envelope; over-help | mis-calibrated forward model | coordination and specification failures; cost |
| Recovers the previous candidate by | n/a | disabling the planner call | lookahead depth 0 | removing the extra roles |

## 5. Recommended successor: candidate C, staged through B

The recommendation is candidate C, the hierarchical model-based planner,
built so that B is C with lookahead depth zero and A is B with the planner
disabled. The three configurations are one code base with two switches, which
is what makes the comparison in the decision document fair and cheap.

The sections below define the successor at the level of interfaces and limits.
Names are proposals; the evaluation design in the companion document does not
depend on any of them.

### 5.1 Event lifecycle

Every change to a learner's world is an immutable event in an append-only,
per-learner-per-course stream. Event kinds are closed:

```text
student.message        student.practice_outcome     student.consent_changed
student.inbox_action   student.membership_changed   course.release_published
course.release_withdrawn  course.policy_changed     course.source_changed
twin.action_delivered  twin.action_suppressed       twin.outcome_observed
clock.tick             ops.kill_switch              ops.provider_failure
```

Lifecycle of one event:

1. Ingest. The event is appended with a deterministic id (hash of stream,
   producer, and producer-side key). Appending is the only side effect of
   ingestion. A duplicate id is a no-op.
2. Project. Deterministic projections fold the event into the learner belief
   snapshot, the goal ledger, and the opportunity ledger (section 5.3, 5.4,
   5.6). Projections are pure functions of prior snapshot plus event and are
   replayable from the stream.
3. Decide. If the event is a student message, the turn decision runs
   synchronously (section 5.2). Otherwise a job is enqueued keyed by
   `(stream, event_id, decision_kind)`; a worker claims it with a lease.
4. Act. The decision produces zero or one action record and zero or more
   scheduled wake-ups. Actions that are externally visible are written to an
   outbox row in the same transaction as the action and the belief revision.
5. Deliver. A separate relay drains the outbox at-least-once; the delivery
   channel is idempotent on the action id. Delivery success is itself an
   event (`twin.action_delivered`), which is how the loop closes.
6. Observe. Student replies, inbox actions, practice outcomes, and timeouts
   become events; the projection updates belief and goal progress; the
   surprise test (section 5.4) decides whether to replan.

The ordering in step 4 and 5 fixes the delivery-before-commit defect found in
the audit: nothing is delivered that has not been committed, and nothing
committed is delivered twice, because the relay is idempotent on the action id.

There is no perpetual model process. Every model call is inside a leased job
or a synchronous turn, and every job terminates in a bounded number of steps.

### 5.2 Planner and fast-path allocation

A deterministic router assigns every decision to one of three tiers before any
model is called. The router uses only observed facts: request form, policy
prefilter result, evidence-gate result, goal state, and the learner state
card. Model confidence never changes the tier.

| Tier | When | Model role | Budget |
| --- | --- | --- | --- |
| Fast path | Factual question with unique, sufficient, authorized evidence; or any turn that the policy prefilter resolves to refuse, clarify, or abstain | Wording only (small model), or none | 1 call, capped output |
| Turn planner | Tutoring turn: an attempt, a misconception signal, a confusion signal, or an active episode step awaiting this observation | One typed proposal (mid-tier model) then wording (small model) | 2 calls |
| Episode planner | Goal start, replan predicate fired, or governance change affecting an active goal | One typed episode plan (frontier or mid-tier model, batchable when not user-facing) | 1 call per episode, amortised over its steps |

Course-level goal selection and opportunity ranking (section 5.4, 5.6) are
deterministic and use no model call at all; they consume the forward model,
which is analytic in the first implementation.

The allocation follows directly from the pricing in section 3.7: output
tokens cost five to six times input tokens on every provider, frontier output
costs roughly forty times small-model output across vendors, and cached input
costs one tenth (one fortieth on the newest Anthropic model) of uncached
input. The stable prefix (policy summary, action envelope schema, course
domain summary) is therefore placed first in every prompt and cached; the
variable suffix (state card, evidence summary, message) is kept small by
construction.

### 5.3 Learner observation and belief-state update

Observation. Every learner-originated event yields zero or more immutable
`Observation` records with provenance (event id, span or task id), a kind
(`assessed_response`, `unassessed_statement`, `help_request`,
`explicit_self_report`, `inbox_action`, `inactivity`), and a candidate concept
attribution. Attribution is proposed by the perceiver (lexical first; a small
model may propose alternatives) and accepted only if every concept id is in
the release's domain model. Assessed responses carry a score from a
deterministic scorer or a professor-approved rubric; a model may grade only
where the professor has approved model grading for that task type.

Belief. `LearnerBelief` is keyed by pseudonymous learner key, course, and
release, never by conversation. Per concept it holds: a mastery estimate with
an uncertainty interval, the estimator version, the evidence counts by kind,
the time of last assessed evidence, and a decay-adjusted estimate for the
current time. It also holds a hypothesis ledger where each hypothesis
(misconception, gap, low confidence, disengagement) has a creation event,
supporting and contradicting observation ids, a status
(`tentative`, `supported`, `retracted`, `expired`), and an expiry.

Update rule. The update is a pure function
`estimator.update(belief, observation) -> belief'` behind the
`LearnerEstimator` interface. The first implementation is a two-state
Bayesian Knowledge Tracing model per concept with professor-visible priors and
a fixed forgetting schedule derived from the spacing literature; Performance
Factors Analysis is the second implementation; both are compared by Brier
score and calibration error against held-out assessed opportunities before
either is selected. Hypotheses are updated by explicit rules: a supporting
observation increments support, a contradicting assessed response retracts,
and time expires. A model may propose a hypothesis; it may never write a
mastery estimate, a status, or a protected attribute.

Prohibited inferences are enforced at the schema: no field exists for
motivation, ability, disability, mental state, or risk category, and the
perceiver's output schema rejects free-text learner descriptors.

State card. The planner never sees the belief object. It sees a compact,
schema-fixed `LearnerStateCard`: the current goal, the target concept's
mastery band and uncertainty band, the active hypotheses by kind, the last
three tutoring moves and their outcomes, the current help level, and the
remaining budget. The card is deterministic, has a fixed token ceiling, and is
the unit that the evaluation design inspects.

### 5.4 Goal selection and termination

A `Goal` is `(objective_id, concept_ids, success_criterion, budget, expiry,
policy_version, release_id)`. Success criteria are closed forms over belief:
mastery estimate above a threshold with uncertainty below a threshold and at
least `n` assessed observations, or a professor-approved task completed.
Budget is a count of interventions and a cost ceiling.

Selection is deterministic and runs on the course-level projection. For each
learner, candidate goals are the published objectives whose prerequisites are
met (prerequisite links from the domain model, now used), minus goals that are
complete, expired, or cancelled. Each candidate is scored by expected mastery
gain per unit cost from the forward model, with a tie-break on professor
objective order. At most a small fixed number of goals are active per learner
(the current three is reasonable). A goal terminates on success, on budget
exhaustion, on expiry, on a governance change that invalidates its release or
policy, on consent withdrawal, or when the learner explicitly declines it.
Termination is an event and cascades to opportunities and wake-ups exactly as
the current implementation does.

Replanning. An episode plan is regenerated only when one of the closed replan
predicates is true:

- `surprise`: the observed outcome of the last step had probability below a
  threshold under the forward model;
- `stalled`: two consecutive steps produced no assessed observation;
- `budget_low`: remaining budget cannot cover the remaining plan;
- `governance`: policy, release, or consent changed;
- `student_request`: the learner asked for a different goal or pace.

This replaces the constant +24 h wake-up. Wake-up times are chosen by the
episode step (a review step uses the spacing schedule; a follow-up to a
delivered message uses the policy's response window), bounded by policy
minimums and maximums.

### 5.5 Retrieval and grounding

The T0 grounding chain is retained without change to its guarantees, and
extended in three ways that the audit found missing:

- the planner supplies a retrieval request (query variants, concept filter,
  evidence requirement) that deterministic code bounds (maximum variants,
  maximum hits, release-scoped only) before execution;
- the atomic-claim validator is always constructed for every mode, not only
  for the autonomy mode, and the deterministic fallback generator emits a
  bounded quote rather than a whole chunk;
- the reranker that exists but is not wired is selectable through the
  profile, subject to the same paired evaluation as any other component.

Semantic verification of claims (an entailment model rather than exact quote)
is a candidate component, not part of the recommendation, because the
evaluation design must first show that it does not admit claims the exact
validator rejects. Grounding remains lexical-exact until then.

### 5.6 Pedagogical policy

The professor's approved policy is compiled, at publish time, into a
`PolicyEnvelope`: allowed moves by situation, the help ladder and its maximum
step per turn, the answer-revealing ceiling by task type, integrity rules,
tone constraints as checkable properties (length bounds, forbidden phrasings,
required elements such as a question back to the student), proactive classes
allowed, and the frequency, quiet-hour, and budget limits. The envelope is
immutable, hash-bound to the release, and is the only pedagogical authority
the planner sees.

The move vocabulary is one closed enum shared by turn planner, episode
planner, proactive ranking, and evaluation:

```text
ask_diagnostic  give_hint  worked_example  scaffold_step  request_attempt
corrective_feedback  confirm_and_advance  spaced_review  recommend_source
summarize_progress  hand_back_to_professor  no_action
```

The turn planner chooses one move within the envelope; deterministic code
enforces the help ladder (a move cannot skip more than one rung upward without
an attempt in between) and the answer ceiling (a `worked_example` for a
graded-task type is not eligible). Adherence to tone constraints is checked
after generation by deterministic property checks, with one repair, then
fallback. The rules that today live in prompts (word limits, required
question back) become checked properties.

### 5.7 Proactive opportunity selection

An opportunity is `(learner, goal, step, candidate_move, window,
evidence_requirement, expected_effect, cost)` produced by the course-level
projection from events and episode plans, never from raw conversation text.

Selection runs in three deterministic stages:

1. Eligibility, evaluated once in one place: consent for the channel, active
   membership, current release, policy enabled, kill switches off, quiet hours,
   the learner's own frequency ceiling and the policy's ceiling, same-concept
   cooldown, evidence available and authorized. Any failure is `no action` with
   a reason code, and a temporary failure schedules exactly one bounded retry.
2. Value. Among eligible opportunities for a learner, the expected effect from
   the forward model (change in mastery posterior for the goal concept,
   discounted by uncertainty) is compared against the cost (message budget,
   tokens, and an interruption penalty from the policy). Only opportunities
   whose value exceeds the `no action` baseline by a policy margin survive.
   Nudging studies with null effects (section 3.4) are the reason the margin
   exists and the reason opens and clicks are not counted as effect.
3. Budget. A per-learner token bucket (messages per seven days) and a
   per-course daily cost bucket are decremented at commit time, inside the
   same transaction as the action, so two workers cannot both spend the last
   token.

Composition is then a fast-path generation over approved evidence, with the
same validation as a reactive turn, written to the outbox. A2 (model-proposed
learner-state triggers) is not needed as a separate autonomy level in this
design: the model proposes episode steps; the projection turns steps into
opportunities; code decides whether they are worth acting on.

### 5.8 Validation and execution boundaries

The v2.1 invariants are retained verbatim: a model output is a proposal until
deterministic code validates it; only the authenticated course, published
release, approved profile, and authorized source set may affect a decision;
`answer` requires unique, complete, current, authorized evidence; every
accepted claim maps to a canonical source range; refuse, clarify, and abstain
contain no academic answer; integrity ceilings are enforced before and after
generation; observed facts and inferred hypotheses are never conflated; a
model cannot mutate identity, membership, release, policy, profile, lineage,
consent, or delivery state; one repair per turn; state and side effects commit
atomically; `no action` is a valid outcome.

Three boundaries are added:

- the planner output schema is closed and every id it emits (concept, move,
  evidence key, step) must exist in a closed set already in the transaction;
- the forward model is read-only during a decision and its version is recorded
  in every action it influenced;
- delivery relays are the only code allowed to talk to a channel, they read
  only outbox rows, and they carry no credentials for the tutoring database.

### 5.9 Persistence, restart, idempotency, and rollback

Persistence is event-sourced: the event stream is the source of truth;
belief, goal, and opportunity ledgers are projections with a stored snapshot
and the event offset it reflects. A restart replays events after the snapshot
offset. Because projections are pure, replay is deterministic.

Durable execution for jobs uses the same pattern the official LangGraph,
Temporal, Inngest, and Restate documentation agree on (section 3.3): every
side effect's result is journaled under a request hash; a resumed job replays
journaled results and never re-executes a completed model call or delivery;
an uncertain call (started, no result) stops the job safely and is never
retried automatically. This is exactly the repository's existing model-call
ledger, generalised to every side effect and applied identically to
deterministic and live configurations, which removes the audit's finding that
restart behaviour differs between them.

Idempotency keys:

- event: `(stream, producer, producer_key)`;
- job: `(stream, event_id, decision_kind)`;
- model call: `(job_id, stage, request_hash)`;
- action: `(goal_id, step_id, opportunity_id)`;
- delivery: `action_id` plus channel.

Rollback has three forms, all already partly present: release rollback (one
setting, cascades to goals, opportunities, and outbox rows bound to the
withdrawn release); policy rollback (a new policy version cancels episodes
planned under the old envelope and lets projections re-derive goals); and
belief rollback (a compensating event that marks a range of observations as
invalid, after which the projection is rebuilt from the stream, which is only
possible because belief is a projection rather than a mutable row).

### 5.10 Model roles and replaceable interfaces

Every model-facing role is a Python protocol with a task id, an input schema,
an output schema, and a version, registered in a profile that maps
`task_id -> (client, model, prompt_hash, schema_hash, budget)`. The registry,
not the factory, decides which client serves which task, so a swap is a profile
change. Prompts are content-hashed; a prompt whose hash changed is a new
version by construction.

| Role | Interface | Input | Output | Default engine tier | Deterministic alternative |
| --- | --- | --- | --- | --- | --- |
| Perceiver | `Perceiver.perceive(message, domain_summary) -> PerceptionProposal` | message, allowed concept ids | request form, concept candidates, attempt span, misconception candidates, confidence | small | regex plus lexical attribution (exists) |
| Turn planner | `TurnPlanner.propose(state_card, envelope, evidence_summary) -> MoveProposal` | fixed-size card and envelope | one move, help level, evidence requirement, expected observation | mid | decision table (exists) |
| Episode planner | `EpisodePlanner.plan(state_card, goal, envelope, forward_summary) -> EpisodePlan` | card, goal, envelope, forward-model summary | up to `k` steps with predicates | frontier or mid, batchable | fixed spacing template |
| Generator | `Generator.generate(move, evidence, envelope, card) -> GroundedResponse` | approved evidence only | text, atomic claims, citation ids | small | template generator (exists) |
| Verifier (optional, candidate D test) | `Verifier.review(proposal, envelope) -> Verdict` | proposal | accept or enumerated defects | mid | none |
| Estimator | `LearnerEstimator.update(belief, observation) -> belief` | belief, observation | belief | none (analytic) | counts (exists) |
| Forward model | `ForwardModel.predict(belief, move) -> OutcomeDistribution` | belief, move | distribution over next observation kinds and score | none (analytic) | uniform (recovers B) |
| Retriever, gate, claim validator | existing protocols in `grounding/protocols.py` | unchanged | unchanged | local | unchanged |
| Judge (evaluation only) | defined in the companion document | | | | |

The protocol names above are proposals; the evaluation design never
references them.

### 5.11 Privacy and authority boundaries

- Data minimisation: the planner sees a state card, never raw history; the
  episode planner sees the card and the goal; no model sees another learner's
  data; course-level ranking uses pseudonymous keys and aggregate budgets only.
- Prohibited inference is a schema property, not a prompt instruction.
- Learner-facing explanations of any proactive message state the trigger class
  and the source in plain language, and every message carries a one-action
  opt-out that becomes a `student.consent_changed` event.
- Professor authority: policy envelope, sources, objectives, release, and
  proactive classes are approved artifacts; the twin cannot change them; the
  course-improvement loop produces proposals only.
- Kill switches at three levels, each a deterministic check before any action
  and any delivery: global (process configuration and a database flag), course
  (policy field, exists), learner (consent and snooze, exists). A tripped
  switch cancels pending jobs and outbox rows and is itself an event.
- Retention and export follow the existing lifecycle service; the event stream
  makes deletion a stream truncation plus projection rebuild.

### 5.12 Finite loop and cost limits

Every limit is an explicit input to the decision and a terminal field in its
trace.

| Scope | Limit |
| --- | --- |
| Student turn | at most 1 perception call, 1 planner call, 1 generation, 1 repair; wall-clock ceiling; output token ceiling per call |
| Proactive decision | at most 1 planner call (only when an episode needs replanning), 1 generation, 1 repair; no retry of uncertain calls |
| Episode | at most `k` steps (proposed default 5), at most 2 regenerations, one expiry |
| Learner per course | at most 3 active goals; messages per 7 days from the tighter of policy and preference; daily token and cost ceiling |
| Course per day | token and cost ceiling; when exhausted, all proactive decisions resolve to `no action` with reason `budget`, and reactive turns fall to the fast path |
| Job | lease with expiry; at most 1 automatic re-run after a crash; the second failure parks the job for operator review |
| Process | global kill switch; provider circuit breaker after consecutive failures, which degrades to deterministic configuration rather than stopping service |

Loop finiteness is provable from the structure: a turn is a directed acyclic
sequence with one back-edge (repair) bounded to one; a proactive job is the
same; an episode has a fixed step count and a fixed regeneration count; goals
have budgets and expiries; and no event handler enqueues more than one job for
itself.

## 6. Why this is preferable to the current design

Relative to T1-v2.1 as implemented, the successor:

- replaces count-based, per-conversation belief with a calibrated, per-learner,
  decaying estimator whose calibration is measured, and makes hypotheses
  accumulate rather than reset;
- replaces constant timing and fixed decision tables with conditional
  replanning and value-based proactive selection that can choose `no action`
  on evidence rather than on trigger absence;
- collapses two learner models, three action vocabularies, two proactive
  stacks, and three eligibility layers into one event stream, one move enum,
  one opportunity ledger, and one eligibility function;
- fixes the delivery-before-commit ordering and adds a global kill switch;
- makes engine swaps a profile change and prompt versions content-addressed;
- keeps every invariant, every exactly-once mechanism, the grounding chain,
  and the two evaluation contracts that the audit found genuinely strong.

Relative to candidate B alone, the successor adds only the forward model and
the episode horizon, both behind interfaces with analytic defaults, and both
removable by a switch. Whether that addition is worth its cost is the
experiment defined in the decision document; the recommendation stands only if
C beats B there.

## 7. Limitations of this study

- The audit is of code at one revision, read without executing anything.
  Line references will drift.
- The literature review is a verified sample, not a systematic review. Every
  entry was fetched and its claim checked against the page, but selection was
  by relevance judgment.
- Pricing and model availability change monthly; the allocation in 5.2 is
  derived from ratios that have been stable across vendors for two years, not
  from any single price.
- No claim in this study has been tested against the repository's data. The
  recommendation is a hypothesis with a prospective experiment attached, not a
  result.
