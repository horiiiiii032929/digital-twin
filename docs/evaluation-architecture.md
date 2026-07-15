# Evaluation architecture

## Purpose

The Digital Twin is an experimental product: parsers, chunkers, retrieval
methods, models, prompts, policies, agent behavior, and analytics will change as
evidence improves. Runtime code therefore depends on component-specific
contracts, while a shared evaluation system records how implementations are
compared and which version is selected for a system profile.

"Best" means the best eligible implementation for a named profile, dataset,
policy, and operational budget. It does not mean universally best or state of
the art.

## Two stable layers

```text
Runtime layer
  component-specific contract
    |- control implementation
    |- candidate implementation A
    `- candidate implementation B

Evidence layer
  same inputs and conditions
    -> hard gates
    -> required quality thresholds
    -> latency, memory, tokens, and cost
    -> failure analysis
    -> decision record
    -> versioned system profile selection
```

Runtime contracts stay specific. A retriever returns ranked chunks, a generator
returns an answer, and a proactive trigger returns a trigger decision. The
project must not replace these useful types with a generic
`execute(any) -> any` abstraction.

Component-specific factories resolve selected profile entries outside business
or orchestration logic. Retrieval provides the first reference factory: changing
its validated profile entry from BM25 to term overlap changes the constructed
retriever without changing the caller. Generator, policy, conversation, and
analytics factories should be added only when those components become active.

The evidence layer is shared. It uses the validated models in
`src/digital_twin/evaluation/` for candidate identity, metrics, hard gates,
failures, decisions, and the complete system profile.

## Component lifecycle

Every decision-bearing component follows the same lifecycle:

1. Define the decision question and prediction before implementation.
2. Freeze the component contract and representative evaluation inputs.
3. Implement or retain the simplest inspectable control.
4. Add one bounded candidate without changing the control's inputs.
5. Run both under the same dataset, permissions, policy, configuration, and
   resource conditions.
6. Reject any candidate that fails a hard gate or required metric.
7. Compare remaining candidates on quality, operational cost, and complexity.
8. Record Keep, Refine, Go Deeper, or Drop with limitations and failures.
9. Update the experimental release profile to select the accepted version.
10. Keep the control and regression data so the decision can be challenged or
    rolled back later.

An implementation is not selected merely because it exists. A pending profile
entry may name candidates, but it has no selected implementation or decision.

## Selection order

Selection is lexicographic rather than one weighted score:

1. **Hard gates:** source permission, privacy, integrity, citation validity,
   provenance, and required failure behavior. A failed gate disqualifies the
   candidate.
2. **Required quality thresholds:** component-specific minimum acceptable
   behavior. A candidate below a required threshold cannot be selected.
3. **Operational constraints:** maximum latency, memory, tokens, cost, and
   reliability requirements.
4. **Relative quality:** compare eligible candidates on the metrics that answer
   the decision question.
5. **Complexity and reversibility:** when gains are negligible, prefer the
   simpler component with lower operational burden and easier rollback.

This prevents a fluent model or high aggregate score from compensating for a
privacy violation, invented citation, or academic-integrity failure.

## Evaluation record

A standard component evaluation record contains:

- component and run identity;
- dataset, corpus, and exact Git revision;
- exactly one control and one or more candidates;
- versioned implementation references and configuration;
- metrics with direction, threshold, value, and validated pass state;
- explicit hard-gate results and evidence;
- failure counts by component-specific category;
- selected implementation, rationale, limitations, and decision outcome.

The model refuses a record when a selected candidate failed any hard gate or
required metric. The retrieval comparison at
[`retrieval-v1.json`](../research/05_evaluation/records/retrieval-v1.json) is the
first standard record.

## System release profile

The profile at
[`student-tutor-v0.json`](../research/05_evaluation/profiles/student-tutor-v0.json)
is the versioned source of truth for component selection. Every component in
the inventory must appear exactly once as:

- `selected`: an implementation is active and supported by evidence;
- `pending`: candidates or requirements are known but no decision exists;
- `disabled`: evidence records an explicit decision not to include the
  component.

Only an `experimental` profile may contain pending components. A
`release-candidate` or `released` profile must resolve every entry. Selected
entries record their version, configuration, hard gates, evidence, control when
applicable, and standard evaluation record when a replacement comparison has
been run.

Run profile validation with:

```bash
npm run verify:profile
```

Validation checks inventory completeness, status invariants, evidence paths,
evaluation-record alignment, selected implementation identity, and hard-gate
or metric failures.

## Swapping and rollback

To propose a replacement:

1. add the candidate behind the existing component-specific contract;
2. add its identifier to the profile entry without selecting it;
3. create a component plan from the shared template;
4. run the control and candidate through the same evaluation;
5. commit the standard evaluation record and readable decision summary;
6. change only the profile entry after the candidate passes;
7. let the component-specific factory resolve the new selection;
8. retain the previous implementation as the control or fallback;
9. rerun component and end-to-end regression checks.

Rollback changes the profile selection to the retained implementation and
revalidates the profile. Source versions, datasets, prompts, model names, and
configuration must remain traceable so a rollback reproduces known behavior.

## Public and private evaluation

Committed synthetic data provides repeatable CI regression tests and must cover
normal, boundary, adversarial, privacy, and no-evidence cases. Explicitly
approved course materials may provide a second private evaluation stage, but:

- originals and derived private content remain Git-ignored;
- source approval and version checks apply before processing;
- per-case private content is not committed;
- sanitized aggregate metrics and failure categories may be recorded only when
  they do not reveal protected material;
- private performance cannot silently replace the public regression suite.

## Required repository artifacts

```text
src/digital_twin/<domain>/                 component contracts and implementations
src/digital_twin/evaluation/               shared evidence/profile models
research/04_experiments/                   predictions and learning logs
research/05_evaluation/templates/          reusable plans and decision records
research/05_evaluation/records/            machine-readable evaluation records
research/05_evaluation/profiles/           selected experimental/release profiles
scripts/evaluate_<component>.py             reproducible evaluation commands
tests/                                     contract, gate, regression, and failure tests
docs/                                      algorithms, interfaces, limitations, and decisions
```

## Applying the architecture to issue #24

Live generation and tutor-policy enforcement must not be implemented as one
inseparable model call. Issue #24 should preserve separate generator, prompt,
policy-enforcement, and citation-validation boundaries.

The first generation evaluation should compare a deterministic generator
control with one live provider candidate using the same questions, retrieved
evidence, tutor policy, and prompt version. Hard gates are grounded-evidence
use, valid citations, graded-work behavior, no-evidence behavior, secret
isolation, and explicit provider failures. Quality metrics should cover
grounding, pedagogy, policy compliance, and citation validity; operational
metrics should cover latency, tokens, and approximate cost.
