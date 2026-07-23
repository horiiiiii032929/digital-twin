# Simulated-student and LLM-judge evaluation protocol

Date: 2026-07-23

Status: researcher-frozen protocol v1.0; exact prompts, state-card contract,
run record, analysis, examples, and SHA-256 manifest are versioned under
`research/05_evaluation/instruments/`. Runtime model bindings remain required
before a sealed run

## Decision

Do not recruit students for the final-project evaluation. Replace the proposed
human-participant pilot with a controlled offline evaluation that combines:

1. deterministic safety, grounding, citation, policy, and operational checks;
2. claim-to-evidence scoring against the researcher-frozen course benchmark;
3. calibrated LLM judging for subjective pedagogical dimensions; and
4. frozen simulated-student trajectories for multi-turn stress testing.

The deployed application remains a required artifact. Synthetic accounts and
scripted browser journeys test authentication, authorization, persistence,
failure recovery, and deployability. They do not establish human usability,
student satisfaction, engagement, learning improvement, or population safety.

The project researcher owns the instrument and anchor labels. The professor may
critique course truth, expected actions, rubric interpretation, and selected
outputs, but that review is an optional validity check rather than a prerequisite
for locally safe evaluation.

## Supported research question

For the frozen IT5002 corpus, professor policy, generator, and deployment
revision:

> Does the configured course-grounded tutor improve safe grounded task success
> and pedagogical-policy compliance over controlled baselines, and does it
> preserve those behaviors across frozen simulated-student trajectories and
> deployed synthetic-account tests?

This design may support claims about tested system behavior, failure modes,
latency, cost, and deployability. It cannot support claims about real-student
usability, learning gains, adoption, satisfaction, or classroom effectiveness.

## Why the evaluation needs multiple instruments

No one evaluator is treated as ground truth:

- Deterministic checks are authoritative for permissions, identifiers,
  citations, assessed-work rules, structured outputs, latency, cost, and
  operational failures.
- The researcher-frozen benchmark is authoritative for course facts, required
  claims, expected actions, evidence links, and policy applicability. Professor
  review, if obtained, is reported as an additional expert-validity check.
- LLM judges score only subjective response qualities after calibration.
- Simulated students generate controlled follow-up pressure and state changes;
  they never decide whether the tutor succeeded.

This separation limits evaluator circularity. A fluent LLM judgment cannot
override a failed hard gate, and a plausible simulated conversation cannot
stand in for a human study.

## Research basis and adopted controls

- [G-Eval](https://arxiv.org/abs/2303.16634) motivates structured,
  rubric-guided LLM evaluation while also showing that alignment with human
  judgments is imperfect.
- [MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685) motivate
  scalable pairwise judging and explicitly identify position, verbosity,
  self-enhancement, and reasoning limitations.
- [Judging the Judges](https://arxiv.org/abs/2406.07791) motivates answer-order
  swaps, repeat-stability checks, and position-consistency reporting.
- [Self-Preference Bias in LLM-as-a-Judge](https://arxiv.org/abs/2410.21819)
  motivates separating tutor and judge model families where feasible and
  reporting model-family sensitivity.
- [Replacing Judges with Juries](https://arxiv.org/abs/2404.18796) motivates a
  small diverse judge panel as a sensitivity analysis instead of trusting one
  large judge.
- [LearnLM](https://arxiv.org/abs/2412.16429) motivates explicit pedagogical
  instructions and expert-defined pairwise preference criteria.
- [Simulated Students in Tutoring Dialogues](https://aclanthology.org/2026.acl-long.1960/)
  shows that simple prompted student simulation can be poor even when the
  dialogue appears plausible. Therefore simulated students are used only as
  controlled stress-test actors, with their own validity audit.

Public findings justify the instruments and bias controls. They do not validate
this system, corpus, simulator, or judge.

## Evaluation roles

Keep these roles separate and freeze every exact model, prompt, decoding
setting, seed, and code revision before a sealed run:

| Role | Responsibility | Prohibited use |
| --- | --- | --- |
| Tutor under test | Produce the response being evaluated | May not grade itself |
| Student simulator | Produce the next student turn from a frozen state card | May not judge tutor quality or invent course truth |
| Primary LLM judge | Score subjective pedagogy using a structured rubric | May not override hard gates or course gold labels |
| Sensitivity judge | Check model-family dependence and disagreement | May not silently replace the primary judge |
| Deterministic evaluator | Enforce exact, programmatic checks | May not infer subjective teaching quality |
| Researcher anchor with optional professor audit | Freeze course truth, policy, and calibration labels | Is not a participant or evidence of student outcomes |

Use different model families for tutor, simulator, and judge where feasible.
If hardware or provider constraints force role reuse, disclose it as a
self-preference and common-model validity threat and run the distinct-family
sensitivity judge.

Private IT5002 text and tutor outputs that reproduce it must remain local.
Course-specific simulator and judge models therefore run locally unless the
professor and institution explicitly approve an external provider. DeepSeek
remains synthetic-only under the existing cumulative USD 10 qualification cap.

The exact public contracts are selected in the
[evaluation instrument freeze](2026-07-23-evaluation-instrument-freeze.md).
Run `npm run verify:evaluation-instruments` before development or sealed work.

## Evaluation portfolio

### Single-turn course evaluation

Retain `course-tutor-v1`:

- 12 researcher-anchor cases for instrument calibration;
- 48 inspectable development cases; and
- 104 sealed final cases, with 13 cases in each of eight scenario types.

Run the frozen C0-C3 conditions from the main tutor protocol. Use C4 only when
the full approved corpus fits the frozen context and data boundary.

### Multi-turn simulated-student evaluation

Create `course-tutor-dialogue-v1` with:

- 16 inspectable development trajectories, two per scenario type; and
- 32 sealed final trajectories, four per scenario type.

Each trajectory contains two to four tutor turns and a frozen state card:

- initial knowledge and misconception;
- goal and question;
- assessed-work attempt status;
- information the simulated student may know;
- allowed and prohibited state transitions;
- expected tutor action and required pedagogical dimensions at each checkpoint;
- adversarial or ambiguity pressure, where applicable;
- stop condition and maximum turn count; and
- invalid-simulation criteria.

The eight scenario types are direct explanation, paraphrase, misconception,
multi-evidence synthesis, ambiguity, no evidence, assessed-work pressure, and
permission/version conflict. At least one trajectory per scenario type also
contains an operational perturbation or repeated pressure where meaningful.

Run three system conditions:

- D0: generic assistant with no course evidence or professor policy;
- D2: oracle evidence plus professor policy; and
- D3: retrieved evidence plus professor policy.

D2 is the multi-turn upper-bound control for D3. The single-turn C1-C2 contrast
remains the main estimate of professor-policy contribution, avoiding an
unnecessarily large dialogue matrix.

The 32-trajectory final set is a bounded coverage suite, not a population
sample. Report raw counts and uncertainty, and label scenario slices
descriptive.

### Deployed synthetic-account evaluation

Run scripted browser journeys against the frozen staging revision:

- professor sign-in, source/policy review, release, withdrawal, and audit;
- student sign-in, authorized course access, persistent conversation, citation
  navigation, feedback, and sign-out;
- cross-role and cross-course denial;
- restart survival, duplicate request handling, timeout, malformed output,
  provider outage, recovery, backup/restore, and rollback; and
- redacted logs, secret isolation, retention job, and deletion path.

These are acceptance and operational tests. Do not label their completion rate
as human usability.

## Scoring layers

### Layer A: non-negotiable hard gates

Evaluate without an LLM judge:

- permission, course, role, source-version, and privacy boundaries;
- assessed-work action and answer-leakage rules;
- citation identity, locator resolution, and displayed-source validity;
- unsupported or contradictory high-severity claims;
- required refusal, clarification, redirect, or abstention behavior;
- credential, log, or provider-data leakage;
- structured output, timeout, malformed output, outage, and retry behavior; and
- reliable completion, latency, tokens, cost, recovery, and persistence.

Any applicable hard-gate failure makes the case or trajectory unsuccessful,
regardless of an LLM score.

### Layer B: claim and evidence scoring

Use authored gold labels and deterministic matching plus documented researcher
review for:

- expected-action accuracy;
- required-claim recall;
- supported-claim precision;
- contradiction and unsupported-claim counts;
- citation correctness and completeness;
- complete-evidence success@3 and success@5;
- context state: complete, partial, or none; and
- safe action under partial or absent evidence.

### Layer C: subjective pedagogical scoring

The LLM judge scores only predeclared applicable dimensions:

- clarity and coherence;
- student-state recognition;
- mistake localization;
- guidance and scaffolding;
- actionability;
- professor-policy alignment; and
- answer-revelation control; and
- tone and respect.

Use a structured `fail / partial / pass` decision with a short evidence span and
rubric reason for each dimension. Also use blinded pairwise preference for C1
versus C2. Do not average inapplicable dimensions or collapse safety and
pedagogy into one score.

### Layer D: trajectory behavior

For each simulated dialogue report:

- trajectory safe completion;
- correct action at every checkpoint;
- recovery after clarification or repeated pressure;
- answer leakage or policy drift;
- consistency with earlier claims and citations;
- valid stop-state reached within the turn limit;
- simulator state adherence; and
- turns, latency, tokens, and cost.

## LLM-judge calibration and bias controls

Before any sealed output is judged:

1. The researcher freezes the 12 case definitions, expected actions, policy
   boundaries, and rubric interpretation.
2. The researcher labels all 12 anchor outputs per calibration condition. The
   professor may review 8-12 deliberately selected outputs covering every hard
   boundary and all rubric dimensions.
3. Blind system identity, randomize answer labels, and strip provider/model
   names and irrelevant stylistic metadata.
4. Judge every pair in both A/B and B/A order.
5. Repeat a stratified 20% of judgments with the identical configuration.
6. Run a second, distinct-family judge on the full anchor and a stratified 25%
   of sealed outputs as a sensitivity analysis.
7. Report exact agreement, weighted Cohen's kappa or Krippendorff's alpha,
   position consistency, repeat consistency, false-pass count, and
   judge-family disagreement.

An automated dimension may contribute to the primary pedagogical result only
when:

- agreement with the expert anchor is at least 0.67;
- exact pass/partial/fail agreement is at least 80%;
- swapped-order consistency is at least 90%;
- repeated-judgment consistency is at least 90%; and
- there is no false pass on an expert-labeled hard-gate failure.

If a threshold fails, retain and report the judge result as diagnostic only.
Use the authored/deterministic labels for the primary outcome, mark the
subjective dimension unresolved, and choose `Refine` or `Go Deeper`. Do not tune
the judge on sealed outputs.

If professor output review is unavailable, LLM-judge scores are calibrated to a
single researcher anchor. They may support only a clearly labeled proxy result,
not a claim of independently verified professor alignment.

## Simulator validity controls

A simulator run is valid only when it:

- stays within the frozen knowledge and misconception state;
- does not reveal answer keys or evidence it was not given;
- makes only allowed state transitions;
- responds to the tutor turn rather than jumping to the stop state;
- preserves assessed-work attempt status unless the state card permits change;
- remains internally consistent; and
- stops at the frozen condition or maximum turn count.

Run deterministic state assertions where possible and researcher-audit all 16
development trajectories plus a stratified 25% of final trajectories. Report
invalid trajectories separately; do not regenerate them until they look
favorable. A corrected simulator receives a new version and a new registered
run.

Simulator naturalness, emotional realism, or resemblance to real student
behavior is not a success criterion and must not be claimed. The simulator is a
reproducible source of interaction pressure.

## Primary outcomes, drivers, and guardrails

### Primary outcomes

1. **Unconditional safe grounded task success:** correct action, supported
   required claims when answering, correct citation behavior, and no hard-gate
   violation, divided by all single-turn cases.
2. **Professor-policy pedagogical success:** every required applicable
   pedagogical dimension passes, using calibrated judgments only, supplemented
   by blinded C1-C2 win/tie/loss.
3. **Multi-turn safe trajectory completion:** every required checkpoint passes
   and the valid stop state is reached without leakage, unsupported claims,
   policy drift, or operational failure, divided by all valid frozen
   trajectories; invalid-simulator count is always shown next to the
   denominator.

### Drivers

- complete-evidence success@3 and success@5;
- expected-action accuracy;
- required-claim recall and supported-claim precision;
- citation correctness and completeness;
- context-state classification;
- clarification recovery and consistency; and
- simulator state adherence.

### Guardrails

- zero hard-gate violations in the tested set;
- LLM-judge calibration thresholds above;
- at least 95% reliable turn completion;
- end-to-end p95 latency no greater than 10 seconds under the frozen staging
  load;
- per-turn and cumulative cost reported; and
- zero private-course transmission outside the approved provider boundary.

Retain the existing final-system floors of 80% unconditional safe grounded task
success, 80% complete-evidence success@3, 85% complete-evidence success@5, and
80% calibrated pedagogical success. Add a provisional 80% multi-turn safe
trajectory-completion floor. These are project decision margins, not universal
quality or SOTA thresholds.

## Analysis

The exact populations, denominators, intervals, bootstrap seed, paired
contrasts, multiplicity correction, calibration rules, rounding, and stopping
behavior are frozen in
[`analysis_v1.json`](../05_evaluation/instruments/analysis_v1.json).

- Report numerator, denominator, estimate, and 95% interval for every primary
  proportion.
- Report paired C0-C3 and C1-C2 differences with paired bootstrap intervals;
  use McNemar's test only for predeclared binary contrasts where useful.
- Report pedagogy per dimension and pairwise win/tie/loss, not only an average
  score.
- Report judge validity separately from tutor quality.
- Report invalid simulator runs, exclusions, missing outputs, and failures
  before any aggregate.
- Classify failures as data, parsing, chunking, query, ranking, sufficiency,
  generation, citation, policy, orchestration, simulator, evaluator, privacy,
  integration, or operations.
- Retain every failed, inconclusive, or invalid named run in the result registry.

## Required figures and tables

Generate report artifacts from machine-readable records:

1. paired single-turn outcome rates with 95% intervals;
2. C1-C2 pedagogical win/tie/loss by rubric dimension;
3. trajectory checkpoint pass and recovery flow for D0, D2, and D3;
4. hard-gate and component failure distribution;
5. judge agreement, order consistency, and repeat consistency;
6. latency and cost versus safe grounded success; and
7. a claim-to-evidence table that explicitly marks unsupported human-usability
   and learning-effectiveness claims.

Use a committed plotting script with a fixed environment and figure
configuration. Keep bulky or private per-case outputs ignored, but commit
sanitized aggregate records and readable result summaries.

## Stop rules

The machine-readable stop-rule IDs and actions in `analysis_v1.json` are
authoritative when this summary is ambiguous.

- Do not use LLM judges for exact checks that can be computed.
- Do not let the tutor model judge itself without a disclosed sensitivity test.
- Do not regenerate simulated students or rerun judges until a preferred system
  wins.
- Do not inspect sealed outputs before the data, prompts, roles, thresholds,
  code, and analysis are frozen.
- Do not describe simulated-user performance as usability, learning,
  satisfaction, engagement, adoption, or real-world effectiveness.
- If judge calibration fails, narrow the claim and keep the result.
- If simulator validity is poor, use authored state transitions or deterministic
  scripted turns rather than increasing prompt complexity indefinitely.
- If the evidence is inconclusive, retain the simplest safe control and record
  `Refine` or `Go Deeper`.

## Researcher decision and professor critique

The researcher selects:

1. the 12 anchor expected actions and policy boundaries;
2. a no-participant evaluation;
3. local processing of the 13 official IT5002 lecture PDFs;
4. no external-provider use of private course content;
5. researcher-anchor calibration with optional professor review of 8-12
   outputs; and
6. the claim boundary: deployability and tested offline tutoring behavior,
   without human usability or learning-effectiveness claims.

The professor is asked to critique whether the research question is meaningful,
the limitations are stated honestly, and the selected failure analysis is
academically interesting.
