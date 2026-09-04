# Experiments

Use this folder for research plans and logs. Store runnable configs under the
root `experiments/configs/` folder and generated run outputs under
`experiments/runs/`.

Use [templates/experiment-plan.md](templates/experiment-plan.md) before a
measured experiment and [templates/learning-log.md](templates/learning-log.md)
after completing each major technical component.

The prospective visual study-material comparison is defined in
[`2026-07-31-multimodal-retrieval-v1-plan.md`](2026-07-31-multimodal-retrieval-v1-plan.md).
It is independent of the sealed text benchmark and does not authorize a model
run by itself.

The method-level successor to the completed visual-description `Refine`
result is
[`2026-09-04-colpali-visual-retrieval-successor-plan.md`](2026-09-04-colpali-visual-retrieval-successor-plan.md).
It compares the visible-text BM25 control with direct multi-vector visual
late-interaction retrieval on a fresh 30-asset/60-case package. Its current
build-only state does not authorize provider execution or select a visual
release component.

The active factual-evaluation plan is
[`2026-08-30-api-first-retrieval-successor-v1-plan.md`](2026-08-30-api-first-retrieval-successor-v1-plan.md).
It replaces local retrieval-model execution with a finite direct-API method
comparison while preserving deterministic source truth and scoring.

Other research plans include:

- [`2026-08-03-professor-fidelity-v1-plan.md`](2026-08-03-professor-fidelity-v1-plan.md)
  for the frozen R2 policy/evidence comparison; and
- [`2026-08-03-student-workflow-slice-plan.md`](2026-08-03-student-workflow-slice-plan.md)
  for the bounded R3 student-facing acceptance path.

## Naming

Use date-prefixed experiment names:

```text
YYYY-MM-DD-short-description.md
```
