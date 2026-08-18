# Dependency and security upgrade plan

Status: frozen before candidate installation

## Decision

Decide whether the current Python and frontend dependency set can move to the
latest compatible releases while retaining Python 3.12, Node 24, selected M2
retrieval behavior, API behavior, and frontend behavior.

The control is the lockfiles at repository revision `355b2e2`. The candidate
updates direct dependencies broadly, including major Torch, Transformers,
pytest, pytest-asyncio, and TypeScript versions. No provider, model revision,
prompt, dataset, or selected component configuration changes.

## Prediction and rollback

Prediction: patched dependency versions remove known audit findings without
changing the exact selected M2 top-three rankings or project tests. If the
Torch/Transformers group fails its compatibility gates, retain its old pins and
merge only the independently passing upgrades. The complete pre-upgrade
lockfiles remain the rollback through Git history.

## Evaluation data and execution

- Python and npm audits cover the resolved development and optional retrieval
  environments.
- The ML check uses all 40 sealed cross-course retrieval development cases and
  the selected M2 BM25 plus Qwen3 dense RRF configuration.
- The local Qwen3 embedding model revision remains
  `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`.
- Three query trials are run after one index build. Only case IDs, ranked chunk
  IDs, aggregate metrics, timings, and version metadata are written to ignored
  output.
- The already-completed cross-course held-out split is not read. The
  professor-fidelity held-out split remains unopened.
- No external provider or billable model call is permitted.

## Gates

1. Python dependency audit reports zero known vulnerabilities.
2. npm audit reports zero known vulnerabilities without forced overrides.
3. All repository checks pass on Python 3.12 and Node 24.
4. Every candidate M2 top-three list is identical to the control for all 40
   development cases and all three trials.
5. Complete-evidence@3, evidence recall@3, nDCG@10, and MRR do not regress.
6. Course-isolation violations, provider failures, external calls, and
   held-out reads remain zero.
7. Candidate median trial p95 query latency is at most 20% above control on the
   same machine. Latency remains an operational compatibility gate, not new
   retrieval-selection evidence.

## Commands and durable evidence

```bash
uv run --extra retrieval-benchmark python -m scripts.evaluate_ml_dependency_compatibility \
  --label baseline --output reports/generated/dependency-compatibility-baseline.json

uv run --extra retrieval-benchmark python -m scripts.evaluate_ml_dependency_compatibility \
  --label candidate --output reports/generated/dependency-compatibility-candidate.json

uv run python -m scripts.compare_ml_dependency_compatibility \
  --baseline reports/generated/dependency-compatibility-baseline.json \
  --candidate reports/generated/dependency-compatibility-candidate.json \
  --output reports/generated/dependency-compatibility-comparison.json
```

The final decision will be registered whether it is Keep, partial Keep, or
Drop. Raw development output remains ignored; the durable summary will contain
only aggregate results, exact revisions and versions, gates, limitations, and
the rollback decision.
