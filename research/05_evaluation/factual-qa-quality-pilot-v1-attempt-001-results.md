# Evaluation result: factual-qa-quality-pilot-v1-attempt-001

## Run identity

- Component: source-linked factual-QA dataset-generation and review method
- Status: **invalid for method qualification; diagnostic Refine evidence retained**
- Date and owner: 2026-08-19, researcher with Codex implementation support
- Code revision: `2aa117e3b4ca6cdd281a52223f9c32f676870894`
- Working tree: clean
- Instrument:
  `research/05_evaluation/instruments/factual_qa_quality_pilot_v1_attempt_001.json`
- Instrument SHA-256:
  `04cfc8baa3f1f48797a82963de204f026984bb553a809eaed3cda7fbeff1440e`
- Generated artifact:
  `reports/generated/factual-qa-quality-pilot-v1-attempt-001.json`
- Generated artifact SHA-256:
  `c8197eb088992e2b60e7ce3e1c10f7e94804808cefdcddf9c3f0175147dd142f`
- Reproduction: prohibited under the non-overwrite attempt policy; use the
  prospective attempt-002 successor.

The provider and local-model work completed before the command failed while
rendering the final output-path summary. The complete 96 KB result artifact was
written first and is preserved. The path-reporting defect did not alter its
contents, but the run is invalid for qualification because separate call-count
and reviewer-contract defects affected review completion and aggregate gates.

## Decision context

The question was whether source-constrained authoring, deterministic lineage
checks, a DeepSeek V4 Flash primary cross-review, and diagnostic local Qwen3
could produce a 24-case pilot ready for a six-case human audit. This is a method
quality question, not a model-ranking benchmark.

The frozen prediction was at least 80% retention with 100% source integrity,
author completion, deterministic provenance, boundary actions, and primary
review completion. Scaling was never authorized by machine results alone.

## Data and exact configuration

- Corpus: `factual-qa-pilot-corpus-v1`, SHA-256
  `dd69703503b6ed0883e19e03330f9a4d98fa9c14056a71d7bdfdee0ed4aecd31`
- Grain: one generated case per fixed blueprint
- Cases: 24 across four synthetic courses and eight slices
- Sources: 15 text units and six multimodal units
- Author: `deepseek-v4-pro`, non-thinking, temperature 0
- Primary cross-reviewer: `deepseek-v4-flash`, thinking enabled
- Independent sensitivity reviewer: local `qwen3:4b`, digest `359d7dd4bcda`
- Gemma calls: zero
- Private or student data: none read or emitted

The author returned one stable provider fingerprint,
`a307abda487cd1b463329ccb945ce396`. The 18 recorded primary-review calls used
one non-empty fingerprint,
`a26a7955944dc5c60445bff77fac9c8e`. Local Qwen records used the frozen digest.

## Aggregate diagnostic results

| Metric | Observed | Frozen gate | Interpretation |
| --- | ---: | ---: | --- |
| Source integrity | 21/21 (100%) | 100% | Passed |
| Author completion | 24/24 (100%) | 100% | Passed |
| Deterministic provenance | 17/24 (70.8%) | 100% | Failed |
| Boundary action field | 7/7 (100%) | 100% | Passed, but every boundary answer string was blank |
| Valid primary reviews | 18/24 (75.0%) | 100% | Failed |
| Recorded retained cases | 12/24 (50.0%) | at least 80% | Failed |
| Recorded quarantine | 12/24 (50.0%) | at most 20% | Failed |
| Multimodal retention | 6/6 (100%) | at least 80% | Passed diagnostically |
| Exact / near duplicate questions | 0 / 0 | at most 5% each | Passed |
| Cross-course citation leakage | 0 | 0 | Passed |
| DeepSeek/Qwen verdict agreement | 12/17 (70.6%) | diagnostic alert below 80% | Alert; Qwen remained non-decisive |
| External cost | USD 0.01211153 | at most USD 1.00 | Passed |

The aggregate `model_identity_stable` result was false because six primary call
records were absent and one independent review was skipped by the call-counter
defect, not because a recorded non-empty fingerprint changed.

## Slice diagnostics

| Slice | Recorded retained / total |
| --- | ---: |
| Direct text | 3/4 |
| Paraphrase text | 1/4 |
| Multi-evidence text | 2/3 |
| Multimodal | 6/6 |
| No evidence | 0/3 |
| Ambiguous | 0/2 |
| Cross-course confusion | 0/1 |
| Adversarial integrity | 0/1 |

These rates are diagnostic only because the run-level review accounting is
invalid.

## Failures and causes

1. **Author prompt / boundary contract:** all seven non-answer blueprints used
   the correct `abstain`, `clarify`, or `refuse` action and empty claims and
   citations, but DeepSeek V4 Pro returned an empty answer string. The prompt
   did not explicitly require a concise user-visible safe response.
2. **Primary reviewer transport:** thinking-mode V4 Flash produced three empty
   or malformed responses. Three additional reviews were skipped after the
   runner double-counted calls whose JSON returned but failed semantic contract
   validation.
3. **Review validation and evidence preservation:** a contradictory verdict and
   dimension set was raised as an exception instead of being normalized to a
   fail-closed rejection, and the raw invalid review was not retained for
   diagnosis.
4. **Independent review accounting:** one Qwen validation failure was counted
   twice, causing the final independent review to be skipped. Qwen produced 23
   valid reviews: 17 accept and six reject. Its known citation-clearance
   limitation remains; these labels are diagnostic only.
5. **CLI reporting:** the relative output argument was not resolved before
   `Path.relative_to`, causing exit code 1 after the artifact was written.

## Operational results

- DeepSeek input/output tokens: 25,543 / 11,113
- Combined call latency p50/p95: 4.55 / 10.02 seconds
- Author p95: 2.73 seconds
- Recorded primary-review p95: 5.71 seconds
- Local Qwen p95: 12.23 seconds
- External cost: USD 0.01211153
- Retries: zero

## Validity review

- Source/corpus integrity and provider data boundary: valid
- Author outputs and recorded per-case artifacts: valid diagnostic evidence
- Aggregate review completion and model-identity gate: invalid due runner
  accounting and fail-fast contract handling
- Human-audit packet: not created
- Scale authorization: false
- Attempt-001 rerun: prohibited

## Decision

- Outcome: **Refine** diagnostically; **invalid** for method qualification
- Selected method: none
- Scale or human audit: not authorized
- Retained fallback: deterministic source/corpus validation and the 24 frozen
  case blueprints

Attempt 002 must require a non-empty boundary response, use V4 Flash
non-thinking JSON review, count each attempted call exactly once, preserve
fail-closed contradictory reviews, resolve output paths before reporting, and
keep Qwen diagnostic only.

## Limitations and learning notes

This small synthetic pilot does not estimate 10,000-case quality or validate
real course PDFs. Its value is that it exposed method defects cheaply. Correct
actions with blank user-visible answers are not valid QA labels, and a review
pipeline must preserve invalid judgments rather than converting schema or
transport failures into missing evidence. The failed result therefore changes
the method instead of selecting a better-scoring model.
