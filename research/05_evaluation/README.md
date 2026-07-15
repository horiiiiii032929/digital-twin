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

`generation_v1.json` is the public preflight set for policy action, citation,
no-evidence, and provider-suppression behavior. It does not measure live answer
quality and cannot select a model or prompt by itself. Its clean deterministic
control run is summarized in `generation-v1-preflight-results.md`.
