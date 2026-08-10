# Professor-fidelity v1 development result

## Answer first

Decision: **Refine; do not open held-out and do not claim professor fidelity.**

The controlled C0-C3 development comparison completed all 192 requested tutor
turns across 48 private synthetic IT5002 cases. C3, the selected retriever plus
professor policy, improved the conservative safe-grounded score by 47.9
percentage points over C0, but reached only 60.4% against the prospective 80%
floor. Complete evidence@3 was 77.1%, also below its 80% floor. Automated
pedagogy remains unresolved because the local judge is not eligible under the
frozen calibration gates. The 104-case one-time held-out ledger remains
unopened.

This is the appropriate professor checkpoint: the architecture and provider
boundary work operationally, professor policy changes behavior in the expected
direction, but retrieval depth, claim measurement, and independent judgment
must be repaired before confirmatory testing.

## Run identity

- Result ID: `professor-fidelity-v1-development-001`
- Status: completed development run; prospective selection gates failed
- Date and owner: 2026-08-10; researcher with Codex-assisted execution and QA
- Code revision: `3d968ae43c46a12921cd3c8237c64b5747a209e7`
- Working tree at execution: clean
- Dataset: `course-tutor-v1.1.0-development`, 48 cases, SHA-256
  `9985e5ce87c50c77fa8904c8ed83e4fc5e2bf6f5d2bf61043044189ab765fc3e`
- Corpus: `it5002-lectures-v1`, 13 source-holder-authorized lecture PDFs
- Reproduction command: `npm run benchmark:professor-fidelity-development`
- Raw local artifact: ignored
  `experiments/runs/professor_fidelity_v1/development/result.json`
- Sanitized machine record:
  [`records/professor-fidelity-v1-development-001.json`](records/professor-fidelity-v1-development-001.json)

## Decision context

The question was whether grounding and the structured professor policy improve
a fixed live generator enough to justify the complete course-tutor candidate.
The prospective conditions were:

- C0: generic assistant, no evidence or professor policy;
- C1: oracle evidence plus generic tutoring policy;
- C2: oracle evidence plus professor policy;
- C3: selected M2 retrieval plus professor policy.

The provider and prompt were held fixed at DeepSeek V4 Flash non-thinking and
strict-evidence prompt v3. C1 and C2 isolate policy because they receive the same
oracle evidence. C2 and C3 isolate retrieval because they receive the same
professor policy.

## Aggregate evidence

| Condition | Safe grounded success | Action accuracy | Citation validity | Complete evidence@3 | p95 latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| C0 | 6/48 (12.5%) | 35/48 (72.9%) | 18/48 (37.5%) | 18/48 (37.5%) | 2.90 s |
| C1 | 23/48 (47.9%) | 40/48 (83.3%) | 48/48 (100%) | 48/48 (100%) | 1.42 s |
| C2 | 31/48 (64.6%) | 48/48 (100%) | 48/48 (100%) | 48/48 (100%) | 1.62 s |
| C3 | 29/48 (60.4%) | 47/48 (97.9%) | 48/48 (100%) | 37/48 (77.1%) | 1.76 s |

The conservative paired effects were:

- C1 − C0: +35.4 points (95% paired-bootstrap interval +20.8 to
  +52.1; Holm-adjusted exact McNemar p=0.000664).
- C2 − C1: +16.7 points (+6.2 to +27.1; adjusted p=0.015625).
- C3 − C2: −4.2 points (−12.5 to +4.2; adjusted p=0.625).
- C3 − C0: +47.9 points (+33.3 to +62.5; adjusted p<0.000001).

These effects are useful directional development evidence, not confirmatory
held-out estimates. In particular, the C2−C1 result shows that the professor
policy improved deterministic action/grounding behavior with evidence held
constant. It does not establish professor-like pedagogy.

## Slice and failure review

C3 passed every ambiguity and no-evidence case (6/6 each) and five of six
assessed-work cases. It passed 3/6 direct, 3/6 paraphrase, 4/6 misconception,
2/6 permission/version, and 0/6 multi-evidence cases under the current
conservative score.

The 19 C3 failures have overlapping causes:

- Ranking/context: 11/48 C3 cases lacked complete essential evidence in the
  first three results; multi-evidence retrieval succeeded in only 1/6 cases.
- Evaluation/generation ambiguity: exact-phrase matching flagged 18 C3 answer
  cases as missing a required claim. Anchor review demonstrated that this
  checker produces paraphrase false negatives, so these cannot all be treated
  as generation failures.
- Policy: one assessed-work case returned the wrong action and failed the
  assessed-work boundary.
- Operations: zero malformed tutor outputs, provider-revision drifts,
  timeouts, or incomplete turns occurred.

## Judge calibration

Gemma 3 4B primary, swapped-order Gemma, and Qwen3 4B sensitivity judging ran
locally over the complete 12-case anchor. Repeat exact agreement was 100% and
swapped-order exact agreement was 96.6%, but swapped-order linear-weighted
kappa was 0.630, below 0.67. Gemma/Qwen exact agreement was 93.2% while
weighted kappa was only 0.119, reflecting severe prevalence sensitivity and
limited discriminative agreement. The primary judge also produced pedagogy
passes on deterministic hard-gate failures.

Most importantly, the earlier Codex QA pass saw condition identities and
cannot serve as the frozen blinded researcher reference. Automated pedagogy is
therefore ineligible and is not reported as a quality score. The failed bundled
Gemma attempts and the initial Qwen-thinking configuration failure remain in
the local calibration record rather than being omitted.

## Operational and provider boundary

- Provider: `deepseek-v4-flash`
- Exact fingerprint: `fp_a18b46594c_prod0820_fp8_kvcache_20260402`
- Tutor cost: USD 0.00997349
- Tokens: 83,145 input; 13,114 output
- Overall latency: 1.161 s p50; 1.865 s p95
- Local retrieval embedding: 58,506 estimated tokens, zero external cost,
  zero failures
- Reliable completion: 192/192 (100%)

The source holder authorized this exact issue #24 provider use. DeepSeek's
[context-cache documentation](https://api-docs.deepseek.com/guides/kv_cache)
states that disk caching is enabled by default and normally expires within
hours to days. Its public [Open Platform terms](https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html)
do not provide this project a specific no-training guarantee. No student or
participant data was sent, but this remains a material research limitation.

## Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| C3 safe grounded success ≥80% | Fail | 29/48 (60.4%) |
| C3 complete evidence@3 ≥80% | Fail | 37/48 (77.1%) |
| Zero C3 hard-gate failures | Fail | 19 conservative failures |
| Pedagogy resolved and ≥80% | Fail | Judge ineligible; metric unresolved |
| C3−C0 gain ≥10 points | Pass | +47.9 points |
| C3 no more than 10 points below C2 | Pass | −4.2 points |
| Reliable completion ≥95% | Pass | 192/192 |
| p95 latency ≤10 seconds | Pass | 1.865 seconds overall |
| Held-out isolation | Pass | Ledger remains `unopened` |

## Decision and next experiment

Outcome: **Refine**. Do not change the experimental component profile and do
not open the one-time held-out split.

Retain the deterministic generator and BM25 retrieval rollback. Before a new
development attempt:

1. replace exact claim-phrase recall with an authored, reproducible semantic
   support method and test it against positive paraphrases and hard negatives;
2. improve multi-evidence retrieval above the 80% complete-evidence@3 floor;
3. repair the assessed-work action failure and add its regression case;
4. obtain a genuinely blinded researcher/professor anchor review, then rerun
   calibration and require every per-dimension gate to pass;
5. freeze the corrected scoring and candidate before considering the unopened
   104-case held-out split.

Issue #24 was already marked closed in GitHub before this development result,
although its latest acceptance comment expected held-out completion. This
record does not reinterpret that state as a successful Keep decision. It
provides the missing C0-C3 evidence and a defensible Refine checkpoint for
professor review.

## Claim boundary

This result supports a narrow claim: on synthetic course-specific development
cases, grounding and professor policy materially improved deterministic safe
behavior over a generic assistant, and the live architecture was reliable and
inexpensive. It does not establish professor fidelity, learning effectiveness,
student usability, real-course readiness, independent human validity, or
deployment approval.
