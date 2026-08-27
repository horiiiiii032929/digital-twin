# Post-generation atomic-claim validation

Status: product boundary integrated; clean synthetic development comparison
complete; production selection and product binding unauthorized.

## Decision

Replace query-to-passage answerability classification with a post-generation
release boundary. The tutor may draft factual claims, but it cannot decide
whether those claims are supported or alter source lineage. The server releases
an answer only when every atomic factual claim is supported by its declared,
eligible retrieved evidence.

This is a method-level response to
`evidence-sufficiency-v2-candidate-comparison-001`. That comparison showed that
question/passage similarity was the wrong abstraction: the safe deterministic
control retained only 8.8% of answers, while both learned candidates retained
15.0% and still made seven false-answer decisions.

## Product boundary

```text
student question
      |
course-scoped retrieval
      |
bounded tutor generation
      |
atomic claims + short citation IDs
      |
server resolves active retrieved source lineage
      |
claim/evidence support validation
      |
all claims pass? ---- no ---> safe fallback, audit, no citations released
      |
     yes
      |
server assembles and persists the answer and citations atomically
```

The selected tutor policy and T1 pedagogical intent remain outside the semantic
support model. Identity, course, release version, source permissions, citation
mapping, claim count, and final release remain deterministic.

## Alternatives

| Method | Role | Reason |
| --- | --- | --- |
| Normalized exact-quote containment | High-precision control | Inspectable and safe, but expected to reject valid paraphrases |
| NLI with evidence as premise and claim as hypothesis | Prospective candidate | Matches the entailment task and can support paraphrases |
| Query-to-evidence relevance or pairwise evidence NLI | Dropped | Failed comparison 001 and does not directly test generated claims |
| LLM judge as final authority | Rejected | Agreement is advisory and cannot replace deterministic lineage or release policy |

The prospective NLI candidate reuses the already pinned Apache-2.0
`cross-encoder/nli-deberta-v3-base` revision. This is a method evaluation, not a
new model search or leaderboard.

## Prospective confirmation

Instrument: `evidence-sufficiency-v3-atomic-claim-confirmation-001`.

The new 120-case synthetic-public confirmation contains 40 supported drafts and
80 reject cases across exact, paraphrased, multi-claim, contradiction,
unsupported-addition, wrong-lineage, stale-source, cross-course,
partial-support, missing-citation, and malformed-contract slices. It does not
reuse the consumed v2 decision split.

Frozen hard gates:

- zero unsupported releases;
- at least 90% supported-draft and multi-claim retention;
- 100% mutation, invalid-lineage, and malformed-contract rejection;
- local verifier p95 at or below 500 ms and added memory below 2 GiB.

Thresholds are fixed before opening the confirmation data. A failure cannot
start threshold tuning on the consumed split or another model search. It
requires one explicit method-level decision. A pass selects only the validation
method; it does not automatically bind the product, promote T1, deploy, or
authorize a human pilot.

## Integration after a passing result

1. Add a versioned generator response contract that exposes atomic factual
   claims and short citation IDs instead of unrestricted factual prose.
2. Resolve citation IDs to eligible retrieved hit IDs on the server.
3. Validate every claim and fail the entire factual response closed when any
   claim, lineage reference, or verifier output fails.
4. Assemble the user-visible response from validated claims plus the
   code-selected pedagogical move.
5. Bind the method to one immutable product profile, then run the untouched
   T0/T1 confirmation and publication workflow on that same revision.

The confirmation passed its frozen synthetic contract gates, but retrospective
analysis found that 120 rows came from ten fact groups crossed with twelve
templates, were not independent, had no independent expert annotation, and did
not exercise real product retrieval or generation. The current decision is
therefore `Go Deeper`, not production `Keep`.

No current product profile or release claim changes until a leakage-free
end-to-end T0 evaluation runs on independently validated source-linked examples.
The system under test must receive only the question and indexed corpus; gold
answers, actions, claims, source spans, and citations remain evaluator-only.

Issue #127 enforces that input boundary. Successor
`academic-factual-qa-end-to-end-pilot-002` integrates optional post-generation
claim validation into the T0 service and permits the evidence gate to select a
bounded retrieved subset. The clean paired development run passed all 160
synthetic-public cases; the any-hit control released 34/80 boundary cases while
the two-boundary arm released none and retained all 80 supported answers.

That result is `Go Deeper`, not method selection. The source aliases and
questions were authored in the same unblinded synthetic design, the labels were
not independently validated, and the clean paired drafts did not contain
naturally occurring generation defects. A fresh independently validated
confirmation must challenge both question/evidence coverage and atomic claim
support before a component profile can bind either candidate.
