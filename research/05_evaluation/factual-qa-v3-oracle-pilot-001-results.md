# Factual-QA v3 oracle pilot 001 results

## Technical summary

The bounded 40-case synthetic-public pilot passed every prospectively frozen
machine gate, but it does **not** authorize scaling to 10,000 cases. Thirty-nine
cases passed deterministic source and citation checks; one multimodal table case
was correctly quarantined because its citation omitted the final words of the
source sentence. The selected hybrid retriever recovered all required evidence
within the first three results for 32/32 answerable cases. The corrected
eight-case human audit is complete: all seven retained controls were accepted,
and the quarantined citation defect was confirmed as a rejection.

The most important validity result is that both LLM reviewers accepted the
non-exact citation that the deterministic checker rejected. Model agreement is
therefore useful for routing, but cannot replace exact source, claim, and
citation checks.

## Run identity

- Result ID: `factual-qa-v3-oracle-pilot-001`
- Execution revision: `7ef0ef3e3867d52ee3c8821d45b20a91e7bc9289`, clean worktree
- Date: 2026-08-20
- Instrument: `factual-qa-v3-oracle-pilot-001`, SHA-256 `1cbb0949cde9efca0fa2134b35321e3e3232b39fa947432b7ad740b0f4b1dff0`
- Base corpus: `factual-qa-pilot-corpus-v1`, SHA-256 `dd69703503b6ed0883e19e03330f9a4d98fa9c14056a71d7bdfdee0ed4aecd31`
- Ignored raw output: `reports/generated/factual-qa-v3-oracle-pilot-001.json`, SHA-256 `b1c4431dceab8c830459b2a48976b4bd1db645a7a4ab0a7585c76ac09726eda5`
- Durable sanitized summary: [`factual-qa-v3-oracle-pilot-001-summary.json`](judgments/factual-qa-v3-oracle-pilot-001-summary.json)
- Corrected review packet: [`factual-qa-v3-oracle-pilot-001-audit.md`](factual-qa-v3-oracle-pilot-001-audit.md)
- Data boundary: synthetic-public only; zero private or student data calls
- Reproduction: `uv run python scripts/run_factual_qa_v3_oracle_pilot.py --execute --allow-deepseek`; rerun requires a successor run ID because the output is exclusive

## Results

| Metric | Result | Frozen gate | Outcome |
| --- | ---: | ---: | --- |
| Product PDF ingestion | 4/4 (100%) | 100% | Pass |
| Author completion | 40/40 (100%) | 100% | Pass |
| Deterministic provenance | 39/40 (97.5%) | at least 95% | Pass; one quarantined |
| Boundary-action accuracy | 8/8 (100%) | 100% | Pass |
| All required evidence in top 3 | 32/32 (100%) | at least 80% | Pass |
| Mean evidence recall at 5 | 100% | at least 95% | Pass |
| Controlled multimodal all-evidence@3 | 6/6 (100%) | at least 80% | Pass |
| Deterministic/Qwen agreement | 38/40 (95%) | diagnostic | Two disputes |
| Cross-course leakage | 0 | 0 maximum | Pass |
| External cost | USD 0.005825 | at most USD 1 | Pass |
| Wall time | 624.7 seconds | recorded, no hard gate | Local review dominated |

For sample-size context, the 95% Wilson interval is 87.1–99.6% for
deterministic provenance, 89.3–100% for all-evidence@3, and 61.0–100% for the
six-case controlled multimodal slice. The perfect retrieval point estimates
should not be interpreted as production certainty.

## Method and model roles

The runner rendered four realistic selectable-text PDFs from 21 approved
synthetic source units, passed them through `LocalCourseSourceIngestionService`
and `RegionAwareChunker`, and indexed 115 chunks with the selected hybrid BM25
plus `Qwen/Qwen3-Embedding-0.6B` retriever. Gold evidence was not injected into
retrieval.

DeepSeek V4 Flash authored 40 source-linked cases at a stable provider revision.
The exact local `qwen3.5:9b-q4_K_M` artifact independently reviewed all 40.
DeepSeek V4 Pro reviewed the two deterministic/Qwen disputes. Exact source
facts, claim IDs, source IDs, and verbatim citation checks—not any model vote—
determined retention.

The six visual cases included the original synthetic visual fixtures plus
approved accessibility descriptions. This validates the controlled
description-to-retrieval path; it does not qualify OCR, layout reconstruction,
or raw image-only semantic understanding.

## Failure analysis

`fqa-p14` answered the table question correctly but quoted “The project and
quizzes together account for 65 percent.” The approved source sentence ended
with “of the assessment.” The deterministic exact-quote gate rejected and
quarantined the case. Qwen 3.5 and DeepSeek V4 Pro both accepted it, showing a
concrete correlated LLM-review miss.

`fqa-v31` passed every deterministic check. Qwen rejected it because it inferred
a non-existent requirement that the answer itself be paraphrased; DeepSeek V4
Pro accepted it. This is a local-review false rejection and confirms Qwen should
remain advisory.

The post-run audit-sampling analysis also found that same-slice priority could
select a clean multimodal case before the quarantined one. The sampler was
corrected prospectively to prioritize deterministic failures first, then model
disagreements, before stratified clean controls. This correction does not alter
the run metrics or retained/quarantined cases.

## Operational implication

DeepSeek V4 Flash averaged 1.47 seconds per authored case. Local Qwen review
averaged 12.47 seconds and consumed most of the 10.4-minute run. At that serial
rate, 10,000 local reviews alone would take about 34.6 hours. Since speed and
quality are now prioritized over minimum spend, the scale design should test a
current hosted independent reviewer or bounded parallel review while preserving
the deterministic acceptance gate. This is an architecture change to evaluate,
not a reason to reinterpret this run.

## Human audit outcome

The project researcher completed the corrected eight-case packet on 2026-08-20.
Seven retained cases were accepted. `fqa-p14` was rejected overall because its
citation was incomplete, while its answer correctness and retrieval correctness
were explicitly preserved as passes. The audit therefore confirms both the
retained-set quality in this small sample and the precision of the quarantine;
it is not an 8/8 validity claim.

## Decision and next gate

**Go deeper to a prospectively frozen 100–200 case rehearsal; do not scale to
10,000 yet.** Every machine gate passed, the seven retained audit controls were
accepted, and the human reviewer confirmed the one quarantined citation defect.

Replace or parallelize the slow local reviewer in that new prospective
instrument, while retaining deterministic source and citation acceptance gates.
Scaling toward 10,000 remains a later decision and must not be combined with
Professor Digital Twin fidelity evaluation.
