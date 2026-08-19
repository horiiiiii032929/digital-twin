# Local Qwen reviewer sensitivity v2 plan

## Decision

Determine whether a corrected hybrid review method can use the exact local
`qwen3.5:9b-q4_K_M` artifact as a diagnostic first-pass factual-QA reviewer.
This is a prospective successor to
`local-qwen-reviewer-sensitivity-v1-development-001`, which detected every
planted defect but failed its free-form failure-classification gate.

## Method change

Attempt 002 keeps the same development probes and model but changes the method:

- exact citation-source membership and required-source coverage are checked in
  deterministic code instead of delegated to the model;
- Qwen judges only semantic action, content, evidence completeness, and course
  boundary dimensions;
- verdict and one non-overlapping triage label are derived fail-closed from the
  semantic dimensions, source mode, expected action, and deterministic citation
  result;
- visual attachments are explicitly bound to an approved source ID and image
  index in the prompt;
- the RSS sampler recognizes the current Ollama `llama-server` process name;
- shorter diagnostic output reduces unnecessary local latency.

These repairs address observed evaluator and instrumentation failures. They do
not change any candidate answer, source, expected verdict, or quality label.

## Data boundary and interpretation

- Dataset: unchanged `local-reviewer-sensitivity-probes-v1`, 11 paired
  development cases and 22 total calls
- Inputs: synthetic-public only, including six actual visual modalities
- Model: exact local digest
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
- External and private-data calls: zero
- Gemma and Claude: prohibited
- OpenRouter: not called

Because the method was refined against attempt 001 failures, attempt 002 is
method-debugging evidence rather than an independent generalization estimate.
A pass permits diagnostic first-pass use only.

## Prospective gates

| Metric | Gate |
| --- | ---: |
| Source and asset integrity | 100% |
| Exact model identity and vision capability | required |
| Structured completion | 100% |
| Critical-defect recall | 100% |
| Clean-control acceptance | 100% |
| Visual-defect recall | 100% |
| Visual clean acceptance | 6/6 |
| Derived primary failure accuracy | 100% |
| External calls, private calls, and cost | 0 |

Latency, tokens, and corrected process RSS are reported as diagnostics.

## Failure handling

Any failed gate produces `Refine`; do not tune again inside this run. Preserve
the result and decide whether the local reviewer should remain diagnostic-only
or be dropped. A pass does not clear human review, select an API judge, or
authorize scaling.

## Reproduction

```bash
uv run python -m scripts.run_local_reviewer_sensitivity
uv run python -m scripts.run_local_reviewer_sensitivity \
  --execute \
  --output reports/generated/local-qwen-reviewer-sensitivity-v2-development-002.json
```
