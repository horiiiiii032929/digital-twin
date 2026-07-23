# Evaluation artifacts

Use this folder for versioned datasets, rubrics, machine-readable component
records, release profiles, and readable result summaries.

```text
05_evaluation/
├── instruments/ frozen prompts, schemas, analysis, examples, and hashes
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

The exact no-participant evaluator contracts are frozen under
[`instruments/`](instruments/). Validate judge, simulator, run-record, analysis,
synthetic-example, and SHA-256 consistency with:

```bash
npm run verify:evaluation-instruments
```

This is structural readiness, not evidence that a judge is calibrated or a
simulated trajectory is valid.

The course-specific retrieval-v3 candidate and analysis contract is separately
frozen in
[`instruments/retrieval_v3_freeze.json`](instruments/retrieval_v3_freeze.json).
Validate its candidate identities, primary metrics, held-out lock, NotebookLM
black-box boundary, and public open-set example with:

```bash
npm run verify:retrieval-v3-instruments
```

This validation does not download a model, complete a private dataset, inspect
held-out cases, or produce a retrieval result.

The existing committed datasets are regression and development assets, not the
sole final-project benchmark. The selected successor design is documented in
the [deployable tutor evaluation protocol](../04_experiments/2026-07-22-deployable-tutor-evaluation-protocol.md): retain the synthetic suite, add a
researcher-frozen course-specific gold benchmark, and keep deployed
synthetic-account evidence separate from offline component selection. The
2026-07-23 amendment removes participant recruitment and uses calibrated LLM
judging, frozen simulated-student trajectories, and scripted synthetic-account
acceptance. Professor review, when available, is recorded as an optional
expert-validity check rather than an experiment-start gate.

The `course-tutor-v1` design is defined by:

- [`course_tutor_v1.schema.json`](course_tutor_v1.schema.json), the strict gold-
  case JSON Schema;
- [`course_tutor_v1_synthetic_example.json`](course_tutor_v1_synthetic_example.json),
  a public one-case example that contains no real course or student data;
- [`course_tutor_v1_condition.schema.json`](course_tutor_v1_condition.schema.json)
  and its
  [`synthetic example`](course_tutor_v1_condition_synthetic_example.json),
  which freeze candidate/presented evidence, exclusions, faults, and justified
  condition-specific behavior without changing corpus answerability;
- [`course-tutor-v1-annotation-guide.md`](course-tutor-v1-annotation-guide.md),
  the semantic rules, split discipline, privacy boundary, and annotation
  workflow; and
- [`course-tutor-v1-professor-anchor.md`](course-tutor-v1-professor-anchor.md),
  the construction state and review questions for the 12-case researcher
  anchor.

The companion no-evidence instrument is defined by:

- [`it5002_retrieval_open_set_v1.schema.json`](it5002_retrieval_open_set_v1.schema.json);
- its
  [`synthetic example`](it5002_retrieval_open_set_v1_synthetic_example.json);
  and
- the
  [`annotation guide`](it5002-retrieval-open-set-v1-annotation-guide.md).

It adds 24 development and 52 held-out hard-negative cases without placing
no-evidence questions in ranking-metric denominators.

The selected full-course candidate corpus is inventoried in
[`it5002_lectures_v1.manifest.json`](it5002_lectures_v1.manifest.json), with the
scope rationale and source hierarchy in the
[`IT5002 corpus decision`](../00_admin/2026-07-23-it5002-full-course-corpus-decision.md).

Private course text, derived passages, or any accidentally encountered real
student content must not be committed. The anchor is an
instrument-calibration set, not a system performance result.

Private anchor cases, companion conditions, and extracted evidence passages
live under ignored `data/processed/course_tutor_v1/` and
`data/interim/course_tutor_v1/`. The committed professor-anchor document
records construction and instrument state without exposing course wording or
gold claims.

Validate the local 12-case researcher draft without running a model:

```bash
uv run python scripts/validate_course_tutor_dataset.py --expected-cases 12
```

This checks both JSON Schemas plus IDs, claim-evidence links, corpus and topic
identity, passage hashes, candidate/presented evidence partitions, permission
filters, condition-specific claim sets, and fault contracts.

`generation_v1.json` is the public preflight set for policy action, citation,
no-evidence, and provider-suppression behavior. It does not measure live answer
quality and cannot select a model or prompt by itself. Its clean deterministic
control run is summarized in `generation-v1-preflight-results.md`.

The first local live use of that set is recorded in
`generation-v1-gemma3-4b-results.md`. It proves the Ollama/LiteLLM transport and
structural controls, but its post-run grounding review is diagnostic rather
than selection evidence. Three of 18 model answers added unsupported content or
used mismatched evidence, so the durable decision is `Refine` with no selected
generator or prompt.

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
