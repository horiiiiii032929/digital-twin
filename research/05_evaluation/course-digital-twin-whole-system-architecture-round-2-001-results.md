# Whole-system architecture round 2 results

## Outcome

**Completed Refine.** The one authorized network-free execution compared the
Round 1 lexical control with two typed-target architectures over the frozen
497-case second development fold. The typed-target method was materially
better than the control, but no architecture passed every prospective gate.

| Architecture | Grounded factual success | Answerable action | Boundary action | All evidence@3 | Recall@5 | Severe releases |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Lexical/any-hit control | 63.73% | 100.00% | 100.00% | 95.97% | 97.73% | 0 |
| Typed target evidence | 89.42% | 98.99% | 100.00% | 98.74% | 98.99% | 0 |
| Typed target plus section ranking | 89.42% | 98.99% | 100.00% | 98.74% | 98.99% | 0 |

Within the same fold, typed targets improved grounded factual success by 25.69
percentage points. Its source-family bootstrap 95% interval was
85.23%–93.43%. The section-ranked variant produced identical quality and more
than doubled p95 latency (2.79 ms versus 1.36 ms), so it provides no evidence
of a useful architectural improvement.

## Causal finding

The target/cardinality contract fixed the dominant Round 1 failure. It raised
multi-evidence success from 0% for the Round 2 lexical control to 90.20%, while
preserving 100% boundary action accuracy and zero severe releases.

The remaining 42 answerable failures are localized and inspectable:

- four answerable paraphrase cases safely abstained because the public target
  reduced to an unresolved token such as `if`;
- 28 cases lacked complete canonical citation lineage, including repeated
  lexical anchors that selected a neighboring region from the same source;
- 14 further cases cited the canonical region but their extracted claim did
  not represent the exact canonical answer span;
- failures were concentrated in paraphrased (15), direct-factual (9),
  definition/explanation (9), multi-evidence (5), and structured-code (4)
  cases.

This is no longer a general retrieval or safety failure. Round 3 should retain
typed target/cardinality and replace single-region extraction with a
source-range-aware candidate-set and claim assembly contract. It should also
detect information-theoretically ambiguous target anchors and clarify instead
of guessing. This is a coherent method-level successor, not prompt tuning or
threshold relaxation.

## Execution integrity

- Every candidate response was persisted before hidden gold was opened.
- Public, response, and gold rows were reconciled by case ID.
- Provider calls, tokens, and paid cost were zero.
- Operational failures, duplicate outputs, and severe unsupported releases
  were zero.
- The exact code revision was `15c9d88` and the worktree was clean.
- Raw per-case responses remain in the ignored generated-results directory;
  this summary and the machine record are the durable sanitized evidence.

## Decision

Retain `typed-target-evidence-v1` only as the Round 3 baseline. Do not select it
for release because grounded success, claim precision/recall, citation
precision/recall, and source-version validity remain below the frozen gates.

## Limitations

- This is a development fold, not the one-time fresh final confirmation.
- Deterministic extractive responses isolate architecture and grounding; they
  do not measure hosted-model answer quality.
- Some residual failures expose underspecified public questions as well as
  runtime selection defects; the third fold must preserve this distinction.
- No professor fidelity, real usability, or real student-learning claim is
  supported.
