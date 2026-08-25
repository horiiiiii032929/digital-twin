# Academic factual-QA end-to-end evaluation plan

Date: 2026-08-25

Status: prospective design; no dataset generation or execution authorized

Owner issue: [#127](https://github.com/horiiiiii032929/digital-twin/issues/127)

## Decision question

Can the frozen Course Digital Twin retrieve eligible source evidence, produce a
factually correct answer with complete citations, and abstain, clarify, or
refuse safely when required?

The previous 10,000-case run answered a different question: whether a
deterministic synthetic truth-package and provider workflow could operate at
scale. This plan evaluates the actual product path.

## Predictions and controls

- The current T0 grounded assistant is the product baseline and rollback.
- The candidate is the same T0 path plus the provisional atomic-claim release
  boundary. No T1 or professor-style change is mixed into this comparison.
- Deterministic lineage and exact-quote containment remain inspectable controls.
- The candidate should reduce unsupported releases without making supported
  answers unusably conservative.

## Data design

Build a 10,000-question source-linked pool from an eligible, versioned corpus
with materially varied documents, facts, modalities, courses, and question
families. Synthetic or dummy sources are acceptable only when they resemble
documents rather than marker templates and are kept separate from real-source
claims.

For each source unit:

1. Two independent LLM roles may propose questions, answers, atomic claims, and
   source spans without seeing each other's output.
2. Deterministic checks verify that every cited quote occurs in the declared
   source version and that boundary cases have no answer lineage.
3. Agreement is used to prioritize review, never as ground truth.
4. Conflicts, near-duplicates, ambiguous questions, and unsupported claims are
   quarantined.
5. Accepted canonical labels are frozen independently from the product run.

The pool must include direct, paraphrased, compositional, cross-source,
cross-course-confusion, no-evidence, ambiguous, stale-version, integrity, and
multimodal cases. Question-family and source-level identifiers are retained so
uncertainty can be clustered correctly.

## Gold and review layers

- **Full 10,000 pool:** automated source-span, lineage, duplicate, leakage,
  action, and schema checks plus execution metrics.
- **Independent gold subset:** approximately 600 cases, stratified as 300
  answerable and 300 boundary/negative cases across courses, modalities, source
  and question families. Labels require independent validation before system
  scoring.
- **Human audit:** 60–100 stratified cases plus every sampled disagreement,
  unsupported release, malformed output, and high-severity citation failure.
  The reviewer does not see the candidate decision before assigning the
  reference label where blinding is practical.

The final sample sizes must be justified from the precision needed for the
primary error rates and the number of independent source/question clusters.
Rows created from one template or fact family do not count as independent
replicates.

## Leakage-free execution

Freeze one code revision, corpus/index version, release profile, prompts,
models, decoding configuration, and environment. For every test case, the
system receives only:

- the student question;
- authenticated course and release context; and
- access to the indexed eligible corpus through its normal retrieval path.

The product must not receive the canonical answer, expected action, target
claims, evidence quotes, source IDs, or citations. Those fields are available
only to the evaluation harness after the response is persisted.

## Primary outcomes

- action accuracy for answer, abstain, clarify, and refuse;
- claim-level factual precision, recall, and F1;
- citation precision, recall, source/version correctness, and complete-evidence
  rate;
- unsupported-release rate and supported-answer retention;
- retrieval evidence recall before generation;
- exact and near-duplicate rates, malformed-output rate, and failure classes;
- latency, token use, cost, peak memory, and safe-fallback frequency.

Report numerators and denominators, overall and stratified results, and 95%
confidence intervals clustered by source and question family where applicable.
Do not convert an operational stress-test total into an academic sample-size
claim.

## Prospective decision rules

Before opening the evaluation split, freeze numeric gates for unsupported
release, claim correctness, citation completeness, boundary actions, supported
retention, retrieval, malformed output, latency, and cost. Gates must be
justified from product risk and expected confidence—not chosen after observing
the candidate.

- **Keep:** every hard safety and quality gate passes on the independent gold
  subset, no severe human-audit defect remains, and the candidate improves the
  product decision relative to T0.
- **Refine:** a correctable data, harness, or integration problem prevents a
  trustworthy decision.
- **Go Deeper:** evidence is directionally useful but uncertainty or coverage
  remains insufficient.
- **Drop:** the method causes material quality or operational regression.

No result automatically promotes T1, establishes professor fidelity, proves
learning outcomes, or authorizes deployment or a human pilot.

## Execution stages

1. Approve corpus eligibility and the annotation protocol.
2. Build and audit a 100–200-case method pilot without touching the final gold
   subset.
3. Freeze the system and run a 1,000-case confirmation with the first
   independently validated gold tranche.
4. Continue to 10,000 only if the method and data gates pass; retain atomic
   checkpoints and complete cost/latency accounting.
5. Register every outcome and preserve raw outputs outside Git with hashes.

This staged design is for catching invalid methodology and runtime defects. It
must not become repeated prompt tuning on consumed evaluation cases.
