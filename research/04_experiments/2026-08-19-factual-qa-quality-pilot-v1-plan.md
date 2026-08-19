# Source-linked factual-QA quality pilot v1

Date: 2026-08-19

Issue: #87

Status: frozen pending execution

## Decision question

Does the source-constrained generation and cross-review method produce a
trustworthy 24-case factual-QA pilot that is ready for a six-case stratified
human audit?

This is a dataset-quality and method-improvement exercise, not a leaderboard or
retrieval benchmark. The models have fixed roles. If the quality gates fail,
the decision is **Refine** and the generation/review method changes before a
successor pilot. A low-quality result must never be hidden or compensated for
by selecting whichever model has the highest score.

## Prediction

Exact source units, constrained claim identifiers, exact supporting quotes, and
one primary cross-review plus an independent sensitivity review should retain
at least 80% of the 24 cases while producing no
unsupported answer, wrong boundary action, cross-course leakage, or broken
source lineage. The main risk is disagreement from the small local Qwen3
reviewer. Prior project evidence makes that reviewer ineligible for citation
clearance, so disagreements are surfaced and prioritized for human audit rather
than silently accepted or automatically rejected.

## Source corpus

- Corpus: `factual-qa-pilot-corpus-v1`.
- Boundary: committed synthetic-public material only; no private course or
  student data, solutions, submissions, or answer keys.
- Four synthetic text handouts cover browser security, data systems, machine
  learning, and human-centred AI.
- Six existing synthetic visual fixtures cover a diagram, chart, table,
  equation, screenshot, and scanned notice.
- Every text unit binds an exact file hash and verbatim source passage. Every
  visual unit binds an asset hash, region locator, and researcher-authored
  source-truth statement already represented in the synthetic multimodal set.

## Pilot composition

The 24 prospectively fixed blueprints contain:

| Slice | Cases |
| --- | ---: |
| Direct text | 4 |
| Paraphrase text | 4 |
| Multi-evidence text | 3 |
| Multimodal | 6 |
| No evidence | 3 |
| Ambiguous | 2 |
| Cross-course confusion | 1 |
| Adversarial integrity | 1 |

This size is intended to expose method defects cheaply. It is not used to claim
population-level dataset accuracy.

## Fixed method

1. Validate every source file, permission, hash, locator, blueprint, course
   boundary, and claim identifier before a model call.
2. DeepSeek V4 Pro authors one case per blueprint in JSON. It receives only the
   approved synthetic source units needed for that blueprint and must return
   claim IDs plus exact supporting quotes.
3. Deterministic checks reject schema drift, incorrect action, invalid claim
   IDs, incomplete multi-source coverage, non-verbatim quotes, source/course
   mismatch, or citations on non-answer cases.
4. DeepSeek V4 Flash performs a separate support and action review.
5. Local `qwen3:4b` performs an independent-family sensitivity review. Gemma is
   excluded. Qwen is diagnostic only because its earlier citation-clearance
   probes were invalid; its verdict cannot accept or reject a case.
6. A case is retained only when deterministic checks pass and DeepSeek V4 Flash
   accepts. Primary-review rejection is quarantined. Qwen disagreements are
   recorded and receive priority in the human-audit sample.
7. If machine gates pass, generate a six-case stratified human-audit packet.
   Scaling remains blocked until that bounded audit passes.

The official DeepSeek API listed `deepseek-v4-pro` and
`deepseek-v4-flash` as the available current model IDs when the instrument was
frozen. Runtime model names and fingerprints are recorded and must remain
stable within the run.

## Frozen gates

### Hard gates

- source integrity, author completion, and deterministic provenance: 100%;
- correct action on every no-evidence, ambiguous, cross-course, and adversarial
  case: 100%;
- cross-course leakage: zero;
- private-data provider calls: zero;
- stable, non-empty DeepSeek fingerprints and exact local Qwen digest;
- cumulative external cost at most USD 1.00.

### Quality gates

- retained cases: at least 80%;
- quarantined cases: at most 20%;
- primary cross-review completion: 100%;
- retained multimodal cases: at least 80%;
- normalized exact-duplicate and high-overlap near-duplicate question rates:
  each at most 5%.

DeepSeek/Qwen verdict agreement is reported with an 80% diagnostic alert, not a
dataset-quality gate, until Qwen is calibrated against human labels.

Machine gates only qualify the method for the six-case audit. They do not by
themselves authorize scaling toward 10,000 cases.

## Failure-driven revision loop

Failures are classified as source, blueprint, schema, provenance, author,
cross-reviewer, independent-reviewer, disagreement, duplication, policy,
privacy, or operations. If a gate fails:

1. register the unfavorable attempt;
2. diagnose the failed cases without changing its frozen thresholds;
3. modify the source constraints, prompt, review contract, or deterministic
   checks that own the failure;
4. freeze a new attempt ID and rerun the same bounded pilot;
5. compare failure removal and newly introduced failures, not model rankings.

## Reproduction commands

```bash
uv run python -m scripts.run_factual_qa_quality_pilot
uv run python -m scripts.run_factual_qa_quality_pilot --execute \
  --allow-external-provider \
  --output reports/generated/factual-qa-quality-pilot-v1-attempt-001.json
```

The execution command writes a non-overwriting per-case artifact under
`reports/generated/`. A named attempt is registered whether it passes, fails,
or is invalid.

## Decision

Pending. The allowed outcomes are:

- **Refine** if any frozen machine gate fails;
- **Go Deeper** only when machine gates pass, meaning proceed to the six-case
  human audit;
- **Keep** only after the human audit passes, meaning the method may scale;
- **Drop** if bounded revisions do not produce a defensible method.
