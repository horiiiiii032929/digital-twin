# Evaluation artifacts

Use this folder for versioned datasets, rubrics, machine-readable component
records, release profiles, and readable result summaries.

The cross-course retrieval benchmark was privately sealed with 40 development
and 60 held-out cases. The one-time held-out comparison is complete and selected
M2 hybrid RRF for the experimental profile, with BM25 retained as rollback.
Its construction and freeze state are preserved in
[`cross-course-retrieval-v1-draft-status.md`](cross-course-retrieval-v1-draft-status.md),
and its decision-bearing result is recorded in
[`cross-course-retrieval-v1-heldout-results.md`](cross-course-retrieval-v1-heldout-results.md).

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

The visual study-material groundwork is defined by a strict
[`multimodal retrieval schema`](multimodal_retrieval_v1.schema.json), a
[`public synthetic fixture`](multimodal_retrieval_v1_synthetic.json), and six
hash-bound visual assets under `tests/fixtures/multimodal/`. Validate them with
`npm run verify:multimodal-retrieval-instruments`. The fixture exercises
contracts only: it contains no private course data, runs no model, and provides
no candidate-quality evidence.

The private authoring checkpoint is summarized without source content in
[`multimodal-retrieval-v1-draft-status.md`](multimodal-retrieval-v1-draft-status.md).
Create the ignored source inventory, PDF sample, and provisional 40-case draft
with:

```bash
npm run inventory:multimodal-sources
npm run sample:multimodal-pdf-pages
npm run draft:multimodal-private-benchmark
```

The generated researcher checklist must be completed before split sealing or a
V0-V3 run. Draw.io and other formats without a reliable local renderer remain
in the review queue instead of being silently treated as supported.

The exact no-participant evaluator contracts are frozen under
[`instruments/`](instruments/). Validate judge, simulator, run-record, analysis,
synthetic-example, and SHA-256 consistency with:

```bash
npm run verify:evaluation-instruments
```

This is structural readiness, not evidence that a judge is calibrated or a
simulated trajectory is valid.

The professor-fidelity comparison is frozen in
[`professor_fidelity_v1.json`](instruments/professor_fidelity_v1.json), with
its research plan in
[`2026-08-03-professor-fidelity-v1-plan.md`](../04_experiments/2026-08-03-professor-fidelity-v1-plan.md).
The first development source run completed 192/192 provider attempts but is
invalid for selection. Its registered correction documents dataset-review,
gold-label leakage, candidate-identity, condition-binding, citation, and judge
defects. Do not cite its C0-C3 effects as professor-fidelity evidence.

The repaired workflow builds exact selected-chunk v1.2 review drafts, creates
no seal or held-out ledger until a non-Codex human approves every case, freezes
a shared policy/integration prompt by hash, and records exact passage identity
in future runs. The ignored v1.2 draft currently contains 48 development and
104 held-out authoring cases and is awaiting human review; held-out execution
remains unopened.

The prerequisite generator comparison is frozen in
[`generator_qualification_v1.json`](instruments/generator_qualification_v1.json).
Its 48-case public synthetic development split and 104-case hash-sealed
held-out split are bound by
[`generator_qualification_v1_freeze.json`](generator_qualification_v1_freeze.json).
Run `npm run verify:generator-qualification` for a network-free readiness check.
Development execution requires an environment-owned `DEEPSEEK_API_KEY`; no
credential is stored or printed, and held-out content remains inaccessible to
routine validation.

The current durable student and publication workflow acceptance result is
summarized in
[`student-workflow-slice-v2-publication-results.md`](student-workflow-slice-v2-publication-results.md).
Reproduce its 19 network-free synthetic checks with:

```bash
npm run verify:student-workflow
```

This keeps only a bounded local persistence, authorization, and publication
foundation. It does not qualify credentialed authentication, complete
professor/source administration, usability, or capacity.

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

Analyze the private development-only local Qwen3 provider qualification without
copying queries, passage text, or per-case rankings into durable outputs:

```bash
npm run analyze:retrieval-provider-local
```

This validates the complete 40-case method matrix and the held-out-access,
course-isolation, provider-failure, and cost gates before emitting a sanitized
summary, CSV, and chart under ignored `reports/generated/`. The historical
hosted comparison was retired before execution; the registered local
deployability results preserve that amendment and its operational decision.

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

The first professor-facing retrieval result uses a smaller disjoint screening
set defined by the
[`IT5002 retrieval rapid checkpoint`](../04_experiments/2026-07-23-it5002-retrieval-rapid-checkpoint.md):
26 development cases and a sealed 59-case R0-R6 ablation with R5 versus R1 as
the primary contrast. That checkpoint cannot select `Keep`; its cases cannot
enter the expanded retrieval-v3 held-out split.

After a one-time held-out runner completes, independently recompute its metrics:

```bash
uv run python -m scripts.analyze_it5002_rapid_result \
  --latency-contaminated
```

The contamination flag retains observed held-out timing while using the clean
development p95 for the predeclared deployability gate. Omit it only when the
held-out runtime was not affected by an independently documented operational
contaminant. The command writes no private course text to the committed result
package. Do not run it for an incomplete result: register the run as invalid
instead.

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

The current professor-fidelity repair commands are:

```bash
npm run build:course-tutor-splits
npm run prepare:course-tutor-authoring-review
npm run seal:course-tutor-splits -- --review <ignored-human-review.json>
npm run analyze:professor-fidelity-development
```

The builder is review-only and refuses to overwrite its output. The review
preparer creates ignored private development and held-out packets plus a
hash-bound checklist template. The sealer requires a complete non-Codex human
review for all 152 authoring cases, writes an immutable v2 seal, and creates a
new unopened held-out ledger. The analysis command audits the preserved v1
result without provider calls or held-out content access.

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

The DeepSeek qualification sequence is recorded separately in
`generator-qualification-v1-development-attempt-001-results.md`,
`generator-qualification-v1-development-attempt-002-results.md`, and
`generator-qualification-v1-development-stability-001-results.md`. P0 and P1
failed citation correctness. P2 passed the 48-case development floors and the
12-case, three-repeat stability check, then passed 104/104 one-time held-out
attempts and the frozen 20/20 second-review sample. The exact binding and P2 are
selected in the experimental profile. The second review was a separate Codex
pass delegated by the researcher, not independent human judgment.

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
