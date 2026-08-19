# Evaluation result: local-qwen-reviewer-sensitivity-v1-development-001

## Run identity

- Component: local factual-QA diagnostic reviewer
- Status: completed; one prospective hard gate failed
- Date and owner: 2026-08-19, researcher-run synthetic-public evaluation
- Code revision: `9365bae724c835eea9b2c4c7ed1622386658a866`
- Working tree: clean at execution start
- Reproduction command: `uv run python -m scripts.run_local_reviewer_sensitivity --execute --output reports/generated/local-qwen-reviewer-sensitivity-v1-development-001.json`
- Runtime: Ollama `0.32.14`; `qwen3.5:9b-q4_K_M`; 9.7B Q4_K_M;
  exact manifest digest
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
- Generated artifact: ignored JSON at the command path, 46,757 bytes, SHA-256
  `fd9044e6e8e8c9f405eec51529f5d206284767fe50d7435325d6ab22dfee4567`
- Predecessor: none; this is the first current-Qwen reviewer-role run

## Decision context

The prospective question was whether this exact local artifact could become a
diagnostic first-pass reviewer across text, safe boundaries, course isolation,
and actual visual evidence. Passing could not select a final judge, clear the
six-case human audit, validate Professor Digital Twin fidelity, or authorize
10,000-case scaling.

The prediction, dataset, prompt, seed, labels, and thresholds were committed
before model execution in the
[plan](../04_experiments/2026-08-19-local-qwen-reviewer-sensitivity-v1-plan.md)
and [instrument](instruments/local_qwen_reviewer_sensitivity_v1_development_001.json).
Deterministic labels were the reference; direct DeepSeek remained the retained
operational control and was not called.

## Data and sample size

- Dataset: `local-reviewer-sensitivity-probes-v1`, SHA-256
  `c72abce9f4d392aeab0ec31ef90d26b9759a95ff90b9c4ee0138ec799770a352`
- Corpus: `factual-qa-pilot-corpus-v1`, hash-bound in the dataset
- Permission: synthetic-public only; zero private or held-out inputs
- Grain: one reviewer decision per probe
- Sample: 11 paired clean/defect cases, 22 calls total
- Coverage: three approved-text pairs, one no-evidence pair, one disallowed
  cross-course pair, and six visual pairs
- Visual inputs: actual rendered diagram, chart, table, equation, screenshot,
  and scanned-page fixtures; their textual source-truth summaries were withheld
- Uncertainty: this is a small method-development probe, not a population
  performance estimate. Wilson 95% intervals are shown to make that limitation
  visible.

## Exact configuration

- Temperature: `0`
- Seed: `8703`
- Thinking: disabled
- Maximum output tokens: `500`
- Timeout: 180 seconds per call
- Concurrency: one
- Retries: zero
- Prompt: `local-factual-qa-reviewer-sensitivity-v1`
- Response: closed JSON schema with fail-closed verdict normalization
- External provider allowance: zero calls and USD 0

## Aggregate results

| Metric | Value | Raw count | Wilson 95% interval | Gate | Pass |
| --- | ---: | ---: | --- | ---: | --- |
| Structured completion | 100.0% | 22/22 | — | 100% | Yes |
| Critical-defect recall | 100.0% | 11/11 | 74.1–100% | 100% | Yes |
| Clean-control acceptance | 90.9% | 10/11 | 62.3–98.4% | at least 90% | Yes |
| Visual-defect recall | 100.0% | 6/6 | 61.0–100% | 100% | Yes |
| Visual clean acceptance | 83.3% | 5/6 | 43.6–97.0% | at least 5/6 | Yes |
| Primary failure classification | 72.7% | 8/11 | 43.4–90.3% | at least 80% | **No** |
| Review-contract mismatch | 9.1% | 2/22 | — | diagnostic | — |

All identity, source-integrity, privacy, external-call, and cost gates passed.
The classification gate failed, so the overall prospective decision is
`Refine`.

## Slice results

| Slice | Probes | Correct verdicts | Important observation |
| --- | ---: | ---: | --- |
| Text, boundary, and cross-course | 10 | 10/10 | Every planted defect was rejected and every clean control accepted. |
| Six visual modalities | 12 | 11/12 | Every visual defect was rejected; the clean diagram was falsely rejected. |
| All defects | 11 | 11/11 | Screening sensitivity passed, but three primary labels were wrong or internally inconsistent. |
| All clean controls | 11 | 10/11 | One visual citation-authorization interpretation produced a false alarm. |

## Operational results

- Total measured inference latency: 373.276 seconds
- p50 / p95 per-call latency: 14.234 / 25.314 seconds
- Input / output tokens: 14,369 / 4,404
- Model artifact size reported by Ollama: 6,594,474,711 bytes
- Approximate cost: USD 0
- External provider calls: 0
- Private-data calls: 0

The automated RSS sampler recorded zero because Ollama `0.32.14` launches the
model as `llama-server`, while the committed sampler matched the older
`ollama runner` process name. That operational field is invalid and must not be
interpreted as zero memory use. A separate read-only observation during the run
showed Ollama's loaded size as 5.5 GB and one `llama-server` RSS sample of
5,960.77 MiB; this is not a measured peak or a hard gate.

## Failures and surprises

1. `text-multi-evidence--defect` was correctly rejected, and the rationale
   explicitly diagnosed the missing RTO answer and citation, but
   `primary_failure` was `none`. Fail-closed normalization preserved the reject.
   This is a model/output-contract inconsistency.
2. `visual-assessment-table--defect` was correctly rejected and the rationale
   calculated 45% + 20% = 65%, but `primary_failure` was again `none`. This is a
   second model/output-contract inconsistency.
3. `visual-softmax-equation--defect` was correctly rejected as
   `wrong_factual_answer` rather than the expected
   `visual_evidence_mismatch`. Both labels describe the same planted error, so
   this exposes overlap in the evaluator taxonomy as well as a classification
   miss.
4. `visual-diagram-flow--clean` was falsely rejected. The model read the image
   correctly but claimed the visual source ID was not authorized even though
   it was present and marked `approved-target-course`. This is a prompt/model
   evidence-binding failure, not an asset or ground-truth defect.
5. The RSS process-name mismatch is an operational instrumentation defect. It
   does not change the quality metrics because memory was not a hard gate.

## Validity review

- Prospective labels and thresholds were preserved: yes
- Code revision and clean state recorded: yes
- Exact model and digest stable: yes
- Actual visual inputs used: yes
- Calibration/test separation: development probes only; no held-out or private
  evaluation was opened
- Data quality: source hashes, unique pair IDs, source IDs, blueprint IDs,
  actions, and expected labels validated before execution
- Run invalidated: no; the quality result is valid, while the RSS field is
  explicitly invalid and excluded from interpretation

## Decision

- Outcome: **Refine**
- Selected implementation: none
- Profile change: none; local Qwen remains prospective and diagnostic-only
- Retained fallback: direct DeepSeek remains unchanged
- OpenRouter: not called and not selected

The model detected every planted defect, including all six visual defects, at
zero marginal API cost. That is promising for screening. However, one false
rejection and three classification misses violate the frozen method gate. The
next attempt should clarify visual source authorization, make reject/failure
consistency structural, remove overlapping labels, and repair memory sampling
before any role promotion.

## Limitations and follow-up

- Eleven pairs are enough for high-signal method debugging, not a broad quality
  or robustness claim.
- No repeated seeds, adversarial image perturbations, private course sources,
  long contexts, or Professor Digital Twin outputs were tested.
- A successful corrected local attempt would still permit only first-pass
  diagnostics. Independent API review or human calibration remains necessary
  for high-stakes fidelity and citation decisions.
- The six-case factual-QA human audit and 10,000-case scaling remain separate
  and unauthorized by this result.

## Learning notes

The local model's core accept/reject sensitivity was stronger than its
explanatory taxonomy. For this use case, the method should first demand a
consistent binary evidence judgment and derive non-overlapping triage labels
from explicit failed dimensions. A reviewer that catches defects but emits
contradictory metadata can reduce human reading, but it cannot yet be trusted as
an autonomous dataset gate.
