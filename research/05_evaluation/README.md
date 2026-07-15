# Evaluation artifacts

Use this folder for versioned datasets, rubrics, machine-readable component
records, release profiles, and readable result summaries.

```text
05_evaluation/
├── templates/   component plans and decision records
├── records/     validated machine-readable candidate comparisons
├── profiles/    complete system component selections
├── *.json       component-specific public evaluation datasets
└── *-results.md readable measurements, failures, and decisions
```

Follow [the evaluation architecture](../../docs/evaluation-architecture.md)
when proposing or replacing an implementation. Validate the current
experimental profile with `npm run verify:profile`.

The retrieval v2 artifacts demonstrate an inconclusive comparison: a `refine`
decision may intentionally select no implementation when every candidate fails
a required gate or metric. In that case, preserve the previous profile entry,
record the failed evidence, and use a new frozen held-out set for the next
candidate iteration.
