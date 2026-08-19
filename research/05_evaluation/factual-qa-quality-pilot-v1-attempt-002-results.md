# Evaluation result: factual-qa-quality-pilot-v1-attempt-002

## Run identity

- Component: source-linked factual-QA dataset-generation and review method
- Status: **machine gates passed; six-case human audit required**
- Date and owner: 2026-08-19, researcher with Codex implementation support
- Code revision: `beb1b3cda6745fc8533b3d647166bdc5cc99d243`
- Working tree: clean
- Method: `source-constrained-factual-qa-v2`
- Instrument:
  `research/05_evaluation/instruments/factual_qa_quality_pilot_v1_attempt_002.json`
- Instrument SHA-256:
  `e85cbe35fb9f8d0d398d9d4e1b75a13463c8ebba256ec20652ab947774526514`
- Generated artifact:
  `reports/generated/factual-qa-quality-pilot-v1-attempt-002.json`
- Generated artifact SHA-256:
  `559dd7da52693605d260792912a975b9d0ee0a12450cc2b8224f9f36302d6a64`
- Preserved audit packet:
  `judgments/factual_qa_quality_pilot_v1_attempt_002_human_audit_001.json`

The complete raw artifact is ignored because it contains bulky provider output.
The sanitized audit packet and this result retain the evidence needed for the
next decision.

## Decision question

Does the corrected source-constrained generation and fail-closed review method
produce a trustworthy 24-case pilot that is ready for a six-case stratified
human audit?

This run qualifies a dataset-building method. It does not rank models or
measure the product's question-answering performance.

## Data and configuration

- Corpus: `factual-qa-pilot-corpus-v1`, SHA-256
  `dd69703503b6ed0883e19e03330f9a4d98fa9c14056a71d7bdfdee0ed4aecd31`
- Sources: 21 source units across four synthetic courses: 15 text and six
  visual-source units
- Cases: 24 fixed blueprints across direct, paraphrase, multi-evidence,
  multimodal, no-evidence, ambiguous, cross-course-confusion, and adversarial
  slices
- Author: DeepSeek V4 Pro, non-thinking, temperature 0; fingerprint
  `a307abda487cd1b463329ccb945ce396`
- Primary review: DeepSeek V4 Flash, non-thinking, temperature 0; fingerprint
  `a26a7955944dc5c60445bff77fac9c8e`
- Independent sensitivity review: local `qwen3:4b`, digest `359d7dd4bcda`
- Gemma calls: zero
- Private course or student data: none read or emitted
- Execution: sequential, zero retries, at most 24 calls per role, USD 1 stop

Qwen remained diagnostic only because prior repository evidence did not
qualify it to clear citation correctness. Acceptance required deterministic
source checks plus the normalized fail-closed DeepSeek primary review.

## Results

All machine gates passed.

| Measure | Observed | Frozen gate |
| --- | ---: | ---: |
| Source integrity | 21/21 (100%) | 100% |
| Author completion | 24/24 (100%) | 100% |
| Deterministic provenance | 24/24 (100%) | 100% |
| Boundary action | 7/7 (100%) | 100% |
| Primary-review completion | 24/24 (100%) | 100% |
| Retained cases | 24/24 (100%) | at least 80% |
| Quarantined cases | 0/24 (0%) | at most 20% |
| Retained multimodal cases | 6/6 (100%) | at least 80% |
| Exact / near duplicate questions | 0 / 0 | at most 5% each |
| Cross-course citation leakage | 0 | 0 |
| Primary/Qwen verdict agreement | 24/24 (100%) | diagnostic alert below 80% |
| Review-contract mismatches | 0 primary / 0 Qwen | diagnostic |
| External cost | USD 0.01211694 | at most USD 1.00 |

Every slice retained all of its cases. All 24 author, 24 primary-review, and 24
independent-review calls were counted once. Raw JSON was preserved for all 48
returned reviews. The seven abstain, clarify, or refuse cases had non-empty
user-visible responses and correctly used no factual claim IDs or citations.

## Operational evidence

| Role | Calls | Input / output tokens | p50 / p95 latency | Cost |
| --- | ---: | ---: | ---: | ---: |
| V4 Pro author | 24 | 15,732 / 2,422 | 1.70 / 2.76 s | USD 0.00895056 |
| V4 Flash primary review | 24 | 16,493 / 3,062 | 1.64 / 2.00 s | USD 0.00316638 |
| Local Qwen sensitivity review | 24 | 15,182 / 4,135 | 8.92 / 12.31 s | USD 0 |

The combined p95 was 11.83 seconds because the local diagnostic review was
slower. That local review is not required to accept a generated case and can
be scheduled asynchronously in a future scale workflow.

## Cross-check and limitations

A post-run inspection confirmed stable identities, complete call records,
exact citation substrings, complete required-source coverage, empty citations
for boundary cases, and no hidden review-contract normalization.

Important limitations remain:

1. The author and reviewers received the frozen blueprint and curated source
   truth. The run validates method conformance, not open-domain factual QA or
   the deployed tutor.
2. The six multimodal cases use source truth extracted from synthetic visual
   assets. They validate visual-source lineage in the dataset method, not a
   production vision or OCR provider.
3. Twenty-four synthetic cases cannot estimate quality at 10,000-case scale.
   Model agreement is a screening signal, never ground truth.
4. The required six-case audit is still blank. No Keep or scale decision is
   available until that audit passes.
5. Even a perfect six-case audit is a bounded process check, not a precise
   retained-label error estimate. A scaled run needs its own prospective
   sampling and uncertainty plan.

## Decision

- Outcome: **Go Deeper**
- Qualified method for human audit: `source-constrained-factual-qa-v2`
- Human audit: required for the six preserved cases
- Scale authorization: false
- Product or factual-QA benchmark claim: none

If any audited case fails question clarity, answer/action correctness, complete
source support, citation lineage, or course/privacy boundaries, classify the
failure and create a new prospective method attempt. If all six pass, freeze a
separate scale-stage plan before generating a larger dummy-document dataset.
