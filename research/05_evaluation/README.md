# Evaluation artifacts

Use this folder for versioned datasets, rubrics, machine-readable component
records, release profiles, and readable result summaries.

```text
05_evaluation/
├── templates/   component plans and decision records
├── records/     validated machine-readable candidate comparisons
├── profiles/    complete system component selections
├── result-registry.md index of every named evaluation result
├── *.json       component-specific public evaluation datasets
└── *-results.md readable measurements, failures, and decisions
```

Follow [the evaluation architecture](../../docs/evaluation-architecture.md)
when proposing or replacing an implementation. Validate the current
experimental profile with `npm run verify:profile`.

`generation_v1.json` is the public preflight set for policy action, citation,
no-evidence, and provider-suppression behavior. It does not measure live answer
quality and cannot select a model or prompt by itself. Its clean deterministic
control run is summarized in `generation-v1-preflight-results.md`.

The retrieval v2 artifacts demonstrate an inconclusive comparison: a `refine`
decision may intentionally select no implementation when every candidate fails
a required gate or metric. In that case, preserve the previous profile entry,
record the failed evidence, and use a new frozen held-out set for the next
candidate iteration.

Evidence-sufficiency v1 demonstrates the same rule at a separate runtime
boundary. Ranking score, lexical overlap, and embedding similarity did not act
as calibrated answerability probabilities. The failed calibration and held-out
results remain registered, and no gate was added to the selected profile.

## Recording every result

Every named run that informs a configuration or product decision must have a
stable row in [the result registry](result-registry.md) and a readable summary
based on [the evaluation-result template](templates/evaluation-result.md).
Record successful, failed, inconclusive, and invalid runs. Never replace an old
summary with new measurements; create a new result ID and link predecessor and
successor runs.

Generated per-case JSON stays under ignored `reports/generated/`. A committed
summary must still include the reproduction command, exact revision, dataset
split and size, configuration, aggregate and slice results, raw counts for
safety rates, uncertainty when meaningful, failures, operational cost,
limitations, and decision. A component comparison also receives a validated
machine-readable record under `records/`.

Validate registry coverage and record schemas with:

```bash
npm run verify:evaluation-results
```
