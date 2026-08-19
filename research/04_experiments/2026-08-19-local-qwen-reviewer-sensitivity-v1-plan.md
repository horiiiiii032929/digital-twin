# Local Qwen reviewer sensitivity v1 plan

## Decision

Determine whether the exact local `qwen3.5:9b-q4_K_M` artifact is reliable
enough to serve as a **diagnostic first-pass reviewer** for factual-QA dataset
quality. This run does not select a final judge, replace the retained DeepSeek
workflow, clear the six-case human audit, or compare general model capability.

## Prediction

The 9.7B multimodal model should reliably accept correct synthetic controls and
reject deliberately corrupted answers across text, boundary, cross-course, and
visual evidence. It may still be unsuitable for final citation or Professor
Digital Twin fidelity decisions.

## Baseline and candidate

- Deterministic labels in a frozen paired-probe dataset are the reference.
- Candidate: local Ollama `qwen3.5:9b-q4_K_M` at manifest digest
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.
- Retained operational control: direct DeepSeek remains unchanged and is not
  called in this run.
- Prospective independent reviewer: OpenRouter
  `mistralai/mistral-small-2603`; deferred unless a later frozen instrument and
  explicit credential configuration authorize it.
- Gemma and Claude are prohibited by the current repository policy.

## Dataset and intended use

The synthetic-public probe set contains paired clean and deliberately corrupted
cases. It draws only from the versioned factual-QA pilot corpus and six checked-in
SVG fixtures. Every probe is one reviewer decision; paired probes share the same
question and evidence but differ in candidate quality.

Coverage includes:

- direct and multi-evidence text;
- no-evidence, ambiguity, and cross-course boundaries;
- diagram, chart, table, equation, screenshot, and scanned-page images;
- wrong factual answers, incomplete evidence, unsupported answers, wrong safe
  actions, cross-course leakage, and visual-evidence mismatches.

For visual probes, the reviewer receives the actual rendered image and locator,
not the corpus's textual source-truth summary. This prevents the visual result
from being a disguised text-only check.

## Metrics and prospective gates

| Metric | Gate | Reason |
| --- | ---: | --- |
| Source and asset integrity | 100% | No result is meaningful against changed evidence. |
| Model identity and vision capability | Exact match | Prevent silent model or runtime drift. |
| Structured completion rate | 100% | A screening role must fail closed and be machine-consumable. |
| Critical-defect recall | 100% | No deliberately wrong or unsafe case may be accepted. |
| Clean-control acceptance | at least 90% | Excessive false alarms make screening impractical. |
| Visual-defect recall | 100% | Multimodal defects are part of the intended role. |
| Visual clean-control acceptance | at least 5/6 | One uncertainty is tolerable in this small development probe. |
| Primary failure classification accuracy | at least 80% | The output should be useful for triage, not only rejection. |
| Private-data calls | 0 | Only synthetic-public evidence is authorized. |
| External-provider calls and cost | 0 and USD 0 | This run is local-only. |

Latency, token counts, peak process memory, and representative failures are
reported but are not hard quality gates in this development run.

## Failure handling

- If any hard gate fails, keep Qwen diagnostic-only or drop it from the role;
  classify the cause and change the method before another attempt.
- Do not change thresholds, prompts, probes, or expected labels after execution.
- Do not turn a failed run into a model ranking exercise.
- Do not use results to clear human-only uncertainty or authorize 10k scaling.

## Reproduction

Preflight without model execution:

```bash
uv run python -m scripts.run_local_reviewer_sensitivity
```

One bounded local execution:

```bash
uv run python -m scripts.run_local_reviewer_sensitivity \
  --execute \
  --output reports/generated/local-qwen-reviewer-sensitivity-v1-development-001.json
```

The durable result must record the clean code revision, dirty state, hashes,
runtime identity, aggregate and slice metrics, operational measurements,
failures, limitations, and Keep / Refine / Go Deeper / Drop decision.
