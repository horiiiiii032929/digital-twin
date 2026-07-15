# Component evaluation inventory

This inventory is the readable view of the machine-validated
[`student-tutor-v0`](../research/05_evaluation/profiles/student-tutor-v0.json)
experimental profile. The profile is authoritative when this table and the JSON
disagree.

| Component | Runtime boundary | Current state | Selected or control | Next comparison | Primary evidence or gates |
| --- | --- | --- | --- | --- | --- |
| Source adapter | Provides an approved source artifact | Selected | Local files v1 | Optional Canvas adapter | Approval, sensitivity, version integrity |
| Parser | Produces normalized document segments and figures | Selected | PyMuPDF document parser v1 | Layout-aware parser; OCR only if justified | Extraction, reading order, provenance |
| Chunker | Produces stable retrieval units | Selected / Refine | Heading-paragraph chunker v1 | Fixed-token and semantic chunking | Retrieval quality, duplication, boundary loss |
| Retriever | Returns ranked approved chunks | Selected / Refine | BM25 v1 provisional rollback baseline; term overlap control | Evidence-sufficiency gate, then targeted lexical, dense, or hybrid refinement | Recall@K, MRR/nDCG, no-evidence, permission filtering, latency |
| Reranker | Reorders retrieved candidates | Pending | No selected implementation | No reranker vs cross-encoder or LLM | Ranking gain, latency, cost, evidence preservation |
| Figure description | Produces reviewable semantic figure text | Pending | Caption/context is metadata, not selected description | Caption/context vs vision model | Factuality, figure lineage, review and display permission |
| Generator | Produces a grounded answer | Pending | Deterministic control planned | One live provider candidate in #24 | Grounding, failure handling, latency, tokens, cost |
| Prompt | Packages question, evidence, and policy | Pending | No version selected | Direct vs guided grounded prompt | Pedagogy, consistency, prompt traceability |
| Tutor policy | Stores professor-approved behavior | Selected | Structured professor policy v1 | Versioned policy refinements | Professor approval, privacy, integrity boundaries |
| Policy enforcement | Applies policy to a tutoring turn | Pending | No implementation selected | Deterministic rules vs model-assisted check | Refusal precision, safe redirection, no-evidence behavior |
| Citation validation | Confirms answer citations map to hits | Pending | Deterministic validator planned | Validator variants only if needed | Hit relationship, locator, active version |
| Conversation orchestration | Maintains student-turn state | Pending | No implementation selected | Deterministic state vs graph orchestration | Traceability, recovery, data minimization |
| Proactive trigger | Decides whether to initiate support | Pending | No implementation selected | Rules vs classifier | Trigger precision/recall, suppression, student control |
| Learning-gap analytics | Aggregates confusion signals | Pending | No implementation selected | Rules vs clustering or model summary | Accuracy, privacy thresholds, uncertainty, actionability |

## Current profile meaning

Five components are selected because the repository already has design or
evaluation evidence: local source input, PyMuPDF parsing, heading/paragraph
chunking, BM25 retrieval, and the structured professor policy. Nine remain
pending. Pending does not mean unimportant; it prevents the roadmap from
pretending a technical decision exists before its evaluation.

The chunker is selected with a `Refine` decision because the algorithm works
and preserves provenance, but size and overlap still need comparison on a
larger approved corpus. Retrieval v2 evaluated BM25, local BGE-small dense
retrieval, and reciprocal-rank fusion on a harder held-out set. None satisfied
all gates, so no candidate replaced BM25 v1 and the next comparison must target
the observed evidence-sufficiency and ranking failures. Both retrieval runs and
the ingestion result are indexed by the durable evaluation-result registry.

## Roadmap integration

- #24 resolves generator, prompt, policy enforcement, and citation validation.
- A bounded evidence-sufficiency task must pass before #25 makes end-to-end
  grounding claims.
- #25 validates the first complete end-to-end experimental profile.
- #8 resolves conversation orchestration.
- #9 resolves proactive triggering.
- #10 resolves learning-gap analytics.
- #11 and #12 expand shared datasets, rubrics, comparisons, and refinements.

Each issue may refine the inventory, but it must not silently select an
implementation. A profile change requires evidence and a decision record.
