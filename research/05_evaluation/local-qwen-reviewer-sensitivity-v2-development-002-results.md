# Evaluation result: local-qwen-reviewer-sensitivity-v2-development-002

## Run identity

- Component: hybrid deterministic/local factual-QA diagnostic reviewer
- Status: completed; one prospective hard gate failed
- Date and owner: 2026-08-19, researcher-run synthetic-public evaluation
- Code revision: `dd132c69265f750882d2365d6bdeb3742765d78c`
- Working tree: clean at execution start
- Reproduction command: `uv run python -m scripts.run_local_reviewer_sensitivity --execute --output reports/generated/local-qwen-reviewer-sensitivity-v2-development-002.json`
- Runtime: Ollama `0.32.14`; exact `qwen3.5:9b-q4_K_M`; manifest
  digest
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
- Generated artifact: ignored JSON at the command path, 45,534 bytes, SHA-256
  `1c7c6b44659c7b003e2572d0d078ec0ac13ac92ec2c7516817f41fc5225c502c`
- Predecessor:
  [`local-qwen-reviewer-sensitivity-v1-development-001`](local-qwen-reviewer-sensitivity-v1-development-001-results.md)

## Decision context

Attempt 001 detected every planted defect but missed its free-form failure-label
gate and falsely rejected one clean image after inventing a citation-authorization
problem. Attempt 002 prospectively moved exact citation lineage to deterministic
code, derived non-overlapping triage labels, explicitly bound image attachments,
and repaired RSS sampling. The same model and development probes were retained
to test whether the method defects were corrected.

This reused set is method-debugging evidence, not an independent generalization
estimate. A pass could authorize diagnostic first-pass use only; it could not
clear human review, validate Professor Digital Twin fidelity, or authorize
10,000-case scaling.

## Data and exact configuration

- Dataset: unchanged `local-reviewer-sensitivity-probes-v1`, 11 paired
  clean/defect cases and 22 calls
- Coverage: five text/boundary/cross-course pairs and six actual visual pairs
- Permission: synthetic-public only; no private or held-out data
- Method: `hybrid-deterministic-lineage-derived-triage-v2`
- Prompt: `local-factual-qa-reviewer-hybrid-v2`
- Temperature / seed: `0` / `8704`
- Thinking: disabled
- Maximum output: 300 tokens
- Concurrency / retries: one / zero
- External-provider allowance: zero calls and USD 0

## Aggregate results

| Metric | Value | Raw count | Wilson 95% interval | Gate | Pass |
| --- | ---: | ---: | --- | ---: | --- |
| Structured completion | 100.0% | 22/22 | — | 100% | Yes |
| Critical-defect recall | 100.0% | 11/11 | 74.1–100% | 100% | Yes |
| Clean-control acceptance | 90.9% | 10/11 | 62.3–98.4% | 100% | **No** |
| Visual-defect recall | 100.0% | 6/6 | 61.0–100% | 100% | Yes |
| Visual clean acceptance | 100.0% | 6/6 | 61.0–100% | 6/6 | Yes |
| Derived failure classification | 100.0% | 11/11 | 74.1–100% | 100% | Yes |
| Output-contract mismatch | 0.0% | 0/22 | — | diagnostic | — |

Identity, source, visual capability, privacy, external-call, and cost gates also
passed. Clean-control acceptance failed, so the overall decision remains
`Refine`.

## Change from attempt 001

| Measure | Attempt 001 | Attempt 002 | Interpretation |
| --- | ---: | ---: | --- |
| Defect recall | 11/11 | 11/11 | High recall was retained. |
| Visual clean acceptance | 5/6 | 6/6 | Explicit image/source binding fixed the visual false alarm. |
| Failure-label accuracy | 8/11 | 11/11 | Deterministic, non-overlapping triage fixed the label contract. |
| All clean acceptance | 10/11 | 10/11 | One false rejection moved to the cross-course boundary slice. |
| Contract mismatches | 2 | 0 | Removing free-form verdict and label fields fixed structural inconsistency. |
| Total latency | 373.276 s | 271.565 s | The shorter contract reduced total time by 27.2%. |

## Failure analysis

`boundary-cross-course--clean` was the only incorrect verdict. The candidate
correctly abstained from answering a browser-security question using a
data-systems distractor. Qwen reported:

- action correct: true;
- response content correct: true;
- course boundary respected: true; and
- evidence complete: false.

Its observation and rationale correctly explained that the only supplied source
was disallowed and that abstention was appropriate. The remaining false reject
therefore comes from semantic-dimension interpretation: the model treated
absence of usable evidence as incomplete evidence even for a correct abstention.
This is not a source, citation, or visual-understanding failure.

The result demonstrates why a fluent rationale cannot repair an inconsistent
machine field after execution. The prospective gate remains failed.

## Operational results

- Total measured inference latency: 271.565 seconds
- p50 / p95 latency: 11.985 / 15.698 seconds per probe
- Input / output tokens: 11,527 / 3,497
- Peak sampled local model-process RSS: 6,045.69 MiB
- Model artifact size: 6,594,474,711 bytes
- Approximate cost: USD 0
- External / private-data calls: 0 / 0

The first memory sample was zero before model load; the remaining samples used
the current `llama-server` process name and are interpretable.

## Validity review

- Prospective method, labels, and gates preserved: yes
- Exact model identity and clean code revision: yes
- Actual visual inputs used: yes
- Raw generated result preserved under ignored output: yes
- Run invalidated: no
- Important caveat: the probes were reused after attempt 001 and cannot measure
  independent generalization

## Decision

- Outcome: **Refine**
- Local Qwen status: not selected as an autonomous acceptance gate
- Permitted interpretation: promising zero-cost, high-recall advisory flagger
  for public/synthetic development work
- Profile change: none
- Retained production/evaluation path: direct DeepSeek remains unchanged
- OpenRouter: not called; an exact independent API reviewer remains a
  prospective next method

Further tuning on these same 11 pairs risks overfitting a development fixture.
Stop local-only prompt iteration here. The practical next step is either to
accept a documented false-positive budget for an advisory-only role or to
qualify an independent paid reviewer on a new probe set. High-stakes citation,
fidelity, scale, and human-audit decisions must not rely on this Qwen result
alone.

## Learning notes

Deterministic citation checks and derived triage labels materially improved the
evaluation pipeline, but a small local model still interpreted one boundary
dimension inconsistently with its own explanation. The defensible engineering
choice is to use deterministic logic wherever the rule is exact, reserve local
LLM judgment for low-cost sensitivity, and use a stronger independent reviewer
or human calibration for consequential acceptance decisions.
