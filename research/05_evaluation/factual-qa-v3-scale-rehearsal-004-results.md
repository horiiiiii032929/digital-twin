# Factual-QA v3 scale rehearsal 004 results

## Technical summary

The 120-case synthetic-public rehearsal completed, but it failed the frozen
reviewer-sensitivity gate and therefore has a **Refine** decision. The source,
ingestion, retrieval, authoring, boundary-action, latency, cost, and accounting
gates passed. Mistral Small 4 detected all ten invalid claim/source bindings but
detected none of the ten missing or truncated citations, producing 50%
sensitivity against a 90% gate.

The completed 12-case manual audit accepted six stratified controls and
confirmed all six deterministic quarantines. Both Mistral and DeepSeek V4 Pro
had accepted those six provenance defects. LLM review remains advisory and may
not override exact source, claim, and citation checks.

## Run identity

- Result ID: `factual-qa-v3-scale-rehearsal-004`
- Execution revision: `6a754103221cafd79c2f1d16e5a9c117add0f757`, clean worktree
- Date: 2026-08-20
- Instrument SHA-256: `7a446f812427c7620a9e163f0455370a9a9b8a0b94fee54060fde7b7402b78df`
- Ignored raw output: `reports/generated/factual-qa-v3-scale-rehearsal-004.json`, SHA-256 `c2e147dee995187f29f17681e105c290da249cdf3a7f94b99da92174baed60d4`
- Sanitized summary: [factual-qa-v3-scale-rehearsal-004-summary.json](judgments/factual-qa-v3-scale-rehearsal-004-summary.json)
- Human audit: [factual-qa-v3-scale-rehearsal-004-human-audit-001.json](judgments/factual-qa-v3-scale-rehearsal-004-human-audit-001.json)
- Data boundary: synthetic-public; provider collection/retention allowed for this run; zero private-data calls
- Rerun prohibited under 004; any correction requires a successor instrument

## Results

| Metric | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Product PDF ingestion | 100% | 100% | Pass |
| Author completion | 120/120 | 100% | Pass |
| Deterministic provenance | 114/120 (95%) | at least 95% | Pass; six quarantined |
| Boundary actions | 24/24 | 100% | Pass |
| All-evidence@3 | 96/96 | at least 90% | Pass |
| Evidence recall@5 | 100% | at least 95% | Pass |
| Controlled multimodal all-evidence@3 | 18/18 | at least 90% | Pass |
| Independent review completion | 120/120 | 100% | Pass |
| Mutation sensitivity | 10/20 (50%) | at least 90% | **Fail** |
| Paired clean specificity | 20/20 (100%) | at least 90% | Pass |
| Reviewer p95 latency | 2.45 seconds | at most 8 seconds | Pass |
| Review stage | 38.22 seconds | at most 240 seconds | Pass |
| End to end | 82.30 seconds | at most 900 seconds | Pass |
| External cost | USD 0.046029 | at most USD 3 | Pass |
| Provider calls | 268 | at most 286 | Pass |

The run used 200,228 input tokens and 32,278 output tokens. Exact model roles
were DeepSeek V4 Flash for 120 author calls, Mistral Small 4 for 120 case reviews
and 20 mutation reviews, and DeepSeek V4 Pro for six disputes, plus two provider
health calls.

## Failure analysis and human audit

Mistral rejected 5/5 invalid-claim and 5/5 invalid-source mutations, but accepted
5/5 missing-citation and 5/5 truncated-citation mutations. The review prompt
mentions citation mismatch but does not state the frozen exact target-claim
coverage rule precisely enough. Several rationales also asserted claim-ID
linkage that was not present in the citation objects.

The six deterministic quarantines were `fqa-r005`, `fqa-r006`, `fqa-r021`,
`fqa-r022`, `fqa-r031`, and `fqa-r072`. Five had incomplete or non-exact target
claim citations. `fqa-r006` added a second supported claim outside the exact
blueprint scope. Manual source review rejected all six under the frozen dataset
contract and accepted the six clean controls. This confirms the deterministic
quarantine rather than the model dispute decisions.

## Decision and next gate

**Refine the reviewer method; do not scale.** Preserve the deterministic
acceptance gate, add explicit exact-quote, target-claim, and no-extra-claim
review rules, and test a successor on new paired citation mutations before any
real-source or larger factual-QA execution. Rehearsal 004 cannot authorize
10,000 cases.
