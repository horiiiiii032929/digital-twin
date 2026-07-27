# Modern retrieval for a course-grounded tutor

Date reviewed: 2026-07-23

## Decision

The current BM25 implementation remains the inspectable control, but it is not
the intended final retriever. The next course-specific comparison will test a
bounded, reproducible approximation of modern source-grounded research
assistants:

1. structure-aware chunks with deterministic course, lecture, section, and
   locator context;
2. BM25 plus an instruction-aware dense retriever;
3. reciprocal-rank fusion over matched candidate pools;
4. a learned query-passage reranker;
5. parent-section expansion under a fixed evidence budget; and
6. a separate returned-context sufficiency decision that may answer, retrieve
   once more, or abstain.

The primary modern open candidate is `Qwen/Qwen3-Embedding-0.6B` paired with
`Qwen/Qwen3-Reranker-0.6B`. `BAAI/bge-m3` is retained as a bounded alternative
only if the Qwen runtime fails the local feasibility preflight or the
development evidence justifies one additional comparison.

NotebookLM is retained as a dated black-box product reference. It is not an
eligible internal retriever because its chunking, candidate ranking,
reranking, context assembly, thresholds, and model revision are not exposed.

## What NotebookLM establishes

Google documents that NotebookLM:

- answers from uploaded or selected sources;
- supports PDFs, Google Slides and Docs, websites, images, audio, and other
  source types;
- exposes inline citations that navigate to a quoted source location;
- allows source inclusion and exclusion; and
- retrieves relevant information before composing an answer when many sources
  are present.

These capabilities define useful product behavior: explicit source control,
inspectable citations, and source-location navigation. They do not disclose a
reproducible retrieval algorithm or an exposed ranked candidate list.

NotebookLM therefore may be evaluated only on observable end-to-end outcomes:
required-claim support, citation correctness and completeness, appropriate
abstention, latency, and representative failures. Its result must record the
date, account tier, source set, source-selection state, query order, and chat
history treatment. It must not be included in Recall@K, nDCG, or internal
component-selection statistics.

Primary product documentation:

- [Learn about NotebookLM](https://support.google.com/notebooklm/answer/16164461)
- [Use chat in NotebookLM](https://support.google.com/notebooklm/answer/16179559)
- [Add or discover sources](https://support.google.com/notebooklm/answer/16215270)

## Candidate evidence

### Qwen3 embedding and reranking

The Qwen3 Embedding report provides paired embedding and reranking models at
0.6B, 4B, and 8B parameters. The models support task instructions, long input,
and more than 100 languages. The authors report strong MTEB retrieval and
reranking results, but those public results are prior evidence only.

The 0.6B pair is the first candidate because it is open, inspectable, and
plausibly feasible on the project machine. Feasibility, latency, memory, and
quality still require local measurement.

- [Qwen3 Embedding technical report](https://arxiv.org/abs/2506.05176)
- [Qwen3 Embedding reference implementation](https://github.com/QwenLM/Qwen3-Embedding)

### BGE-M3

BGE-M3 supports dense, sparse, and multi-vector retrieval in one model and
accepts inputs up to 8,192 tokens. It is relevant when a unified hybrid or
longer-document representation is useful. It is not automatically added to the
final comparison: the experiment first tests whether the Qwen3 pair is
feasible and whether a further model comparison can answer a remaining
decision.

- [BGE-M3 technical report](https://arxiv.org/abs/2402.03216)

### Contextual chunks

Anthropic's Contextual Retrieval work prepends chunk-specific context before
BM25 indexing and embedding, then combines hybrid retrieval with reranking.
Its reported retrieval-failure reductions are vendor evidence and cannot be
transferred directly to IT5002.

The project will first test deterministic context derived from approved
metadata rather than LLM-generated summaries. This isolates the retrieval
effect, avoids adding unsupported statements to indexed evidence, and costs
nothing at ingestion time. An LLM-generated context condition requires a new
prospective plan if deterministic context fails.

- [Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)

### Sufficient context

Google Research separates two failure sources: the generator may fail despite
sufficient evidence, or retrieval may supply insufficient evidence and the
generator may answer anyway. Their selective-generation results motivate an
explicit sufficiency and abstention boundary.

This distinction matches the project's evidence-sufficiency-v1 failure: the
best tested heuristic still produced false answers and false abstentions.
Retrieval relevance and returned-context sufficiency must remain separate
labels and result sections.

- [Sufficient Context: A New Lens on Retrieval Augmented Generation Systems](https://research.google/pubs/sufficient-context-a-new-lens-on-retrieval-augmented-generation-systems/)

### Query decomposition

Question decomposition can improve multi-hop evidence collection by retrieving
for bounded subquestions and reranking their combined candidates. It also adds
latency and query-drift risk.

The project will test one frozen decomposition prompt only on cases labeled
`multi_evidence`. It will not become the default path unless it improves
complete-evidence success without violating the latency, false-answer, and
query-drift guardrails.

- [Question Decomposition for Retrieval-Augmented Generation](https://aclanthology.org/2025.acl-srw.32/)

### Visual document retrieval

ColPali and Qwen3-VL retrieval represent document-page images and can use
layout, tables, diagrams, and other visual evidence lost by text extraction.
They are relevant only if the dataset contains a separately adjudicated visual-
evidence slice and text retrieval fails on it.

The 13 course PDFs have selectable text, so a multimodal model is not part of
the required v3 comparison. Adding it without a visual denominator would add
complexity without answering a measured question.

- [ColPali](https://arxiv.org/abs/2407.01449)
- [Qwen3-VL Embedding and Reranker](https://arxiv.org/abs/2601.04720)

### Hierarchical and graph retrieval

RAPTOR and GraphRAG address global summarization, cross-document themes, or
multi-hop relations through generated hierarchy or graph structure. They add
indexing cost, generated intermediate artifacts, and provenance questions.
The current corpus and failures do not yet justify that complexity.

These methods remain future candidates only if the frozen comparison shows
that bounded decomposition plus reranking cannot retrieve cross-lecture
evidence.

- [RAPTOR](https://arxiv.org/abs/2401.18059)
- [Microsoft GraphRAG](https://www.microsoft.com/en-us/research/project/graphrag/)

## Bounded comparison

The internal ablation ladder is:

| ID | Condition | Decision role |
| --- | --- | --- |
| R0 | Fixed-window chunks plus BM25 | Representation control |
| R1 | Heading-aware chunks plus BM25 | Current rollback control |
| R2 | Heading-aware chunks plus Qwen3 dense retrieval | Dense contribution |
| R3 | Heading-aware BM25 plus Qwen3 dense RRF | Hybrid contribution |
| R4 | Deterministically contextualized R3 | Context contribution |
| R5 | R4 candidate pool plus Qwen3 reranker | Confirmatory modern candidate |
| R6 | R5 plus one decomposition-and-retrieval round on `multi_evidence` cases | Conditional multi-evidence candidate |
| O1 | Gold essential evidence | Non-deployable upper bound |
| B1 | NotebookLM | Exploratory black-box product reference |

R5 versus R1 is the primary component-selection comparison. R0, R2, R3, and R4
diagnose where any gain originates. R6 has a separate multi-evidence
denominator. O1 estimates the generator ceiling. B1 is never pooled with
internal retrieval metrics.

## Claim boundary

The experiment may support:

> On the frozen IT5002 corpus and benchmark, the selected contextual hybrid
> retrieval configuration improved complete-evidence retrieval or safe
> grounded task success over the BM25 control under the recorded context,
> latency, memory, and permission constraints.

It may not support:

- universal or state-of-the-art retrieval;
- equivalence or superiority to NotebookLM's hidden retriever;
- improved student learning or usability;
- safety outside the tested corpus and query distribution; or
- production readiness from an offline retrieval result.
