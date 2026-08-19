# Deployment freeze artifact boundary

## Decision

`deployable-product-foundation-freeze-v6` supersedes V5 only as the current-tree
artifact boundary. It does not introduce a new deployment implementation,
result, image, or quality claim.

V5 globally required every one of its 67 bound files to match the current
working tree. That included the append-only evaluation result registry and
status/decision documentation. Recording a new, unrelated evaluation therefore
made `npm run verify:deployable-freeze` fail even though all deployment code,
configuration, model policy, images, and recovery evidence remained unchanged.

V6 retains the same evidence revision, run ID, selected candidate, model policy,
local gate counts, image digests, rollback, and three pending external gates. It
adds an explicit per-binding classification:

- 45 deployment implementation, configuration, policy, command, and regression
  artifacts must match both the evidence revision and current tree;
- 22 plans, results, records, registries, literature, and status documents must
  match the evidence revision but may evolve in the current tree.

This preserves immutable evidence while allowing the research log to remain
append-only. Moving an implementation artifact into the evidence-only class,
changing a current-match artifact, changing model/provider identity, or
promoting an external gate requires a new freeze ID.

## Verification

```bash
uv run pytest tests/test_deployable_foundation_freeze.py -q
uv run python -m scripts.validate_deployable_foundation_freeze
```
