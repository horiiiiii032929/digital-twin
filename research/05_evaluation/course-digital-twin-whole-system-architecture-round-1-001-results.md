# Whole-system architecture round 1 results

## Outcome

**Completed Refine.** The one authorized network-free execution compared three
complete architecture manifests over 495 development cases. No architecture
passed the frozen quality gates.

| Architecture | Grounded factual success | Answerable action | Boundary action | All evidence@3 | Recall@5 | Severe releases |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Lexical/any-hit control | 52.66% | 100.00% | 100.00% | 89.87% | 96.20% | 0 |
| Evidence-first hierarchical | 24.81% | 36.46% | 100.00% | 88.86% | 96.20% | 0 |
| Plan-observe/event-sourced | 24.81% | 36.20% | 100.00% | 88.35% | 95.95% | 0 |

The lexical control is retained as the Round 2 baseline because it was the
best of the three, not because it is release-ready. Its source-family bootstrap
95% interval for grounded factual success was 48.48%–57.74%.

## Causal finding

The two more complex candidates did not fail because of unsafe boundary
behavior: all three conditions achieved 100% boundary action accuracy and zero
severe unsupported releases. They failed because whole-question concept
coverage treated question scaffolding as required evidence and therefore
abstained on many answerable cases. The lexical control answered all
answerable cases but still selected incomplete or incorrect source regions,
especially for multi-evidence and structured cases.

The next architecture must therefore change the public-question-to-evidence
contract coherently:

- derive explicit evidence targets and cardinality from the public question;
- rank and validate each target independently;
- require every target before answering;
- emit one atomic claim and exact source-range citation per selected region;
- retain the deterministic boundary router and fail-closed delivery policy.

This is a method-level successor, not threshold relaxation or prompt tuning.

## Execution integrity

- Every candidate response was persisted before hidden gold was opened.
- Public, response, and gold rows were reconciled by case ID.
- Provider calls, tokens, and paid cost were zero.
- Operational failures, duplicates, and severe unsupported releases were zero.
- Raw per-case responses remain in the ignored generated-results directory;
  this summary and the machine record are the durable sanitized evidence.

## Limitations

- This is a development fold and cannot serve as the one-time final
  confirmation.
- Deterministic extractive responses isolate architecture and grounding; they
  do not measure hosted-model answer quality.
- No professor fidelity, real usability, or real student-learning claim is
  supported.
