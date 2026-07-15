# RAG and LLM application benchmarking

## What a public benchmark can and cannot decide

Public benchmarks help identify serious candidate methods, common failure
modes, and useful metrics. They cannot select this tutor's retriever, model,
prompt, or architecture because they do not reproduce our course sources,
permission rules, academic-integrity policy, user questions, or budget.

The repository therefore uses two evidence levels:

1. Public benchmark research narrows the alternatives worth implementing.
2. Versioned repository benchmarks decide whether an alternative is eligible
   and useful for a named system profile.

This distinction matters. [BEIR](https://arxiv.org/abs/2104.08663) found BM25
to be a robust zero-shot baseline while reranking and late-interaction methods
often achieved stronger average retrieval at higher computational cost.
[MTEB](https://arxiv.org/abs/2210.07316) and
[MMTEB](https://arxiv.org/abs/2502.13595) show that embedding performance
varies across tasks, domains, and languages. [BRIGHT](https://arxiv.org/abs/2407.12883)
further demonstrates that strong general retrieval models can struggle on
reasoning-intensive queries. A leaderboard position is useful prior evidence,
not a local acceptance test.

## Benchmark stack for this repository

| Layer | Decision | Primary measures | Important gates and diagnostics |
| --- | --- | --- | --- |
| Retrieval | Which chunks enter the context? | gold-evidence Recall@3, nDCG@3 | permission/version leakage, no-evidence accuracy, Precision@k, MRR, slice failures, latency and index burden |
| Context assembly | Is the supplied context sufficient and economical? | gold-claim coverage, context precision | token budget, duplicated evidence, conflicting versions, missing provenance |
| Generation | Does the model use evidence correctly? | grounded task success, claim correctness | faithfulness, citation validity, abstention, policy compliance, malformed output |
| End-to-end tutor | Does the complete interaction help safely? | rubric-scored pedagogical task success | academic integrity, privacy, consistency, recovery, latency and cost |
| Operations | Can the configuration run reliably? | success rate, p95 latency, cost per case | timeout rate, dependency size, cold start, memory, provider or model availability |
| Evaluator | Can we trust the score? | agreement with human labels | position/order bias, repeat stability, rubric coverage, uncertainty |

Selection is lexicographic, not one weighted score. A candidate first passes
permission, privacy, provenance, integrity, and required abstention gates. It
then passes minimum quality and operational thresholds. Only eligible
candidates are compared on relative quality and complexity.

## Retrieval benchmark design

The retrieval set must be difficult enough that adding more returned chunks
does not make the score trivial. It should include:

- exact terminology and identifiers, where sparse retrieval should be strong;
- conceptual paraphrases, where dense retrieval may add value;
- questions requiring two or more independently judged passages;
- topically similar distractors and ambiguous short queries;
- absent answers, including queries that share generic terms with the corpus;
- prohibited and superseded sources containing tempting exact matches;
- tables, figures, multilingual content, and long documents when those
  capabilities enter the product.

Gold judgments identify stable source-and-passage relationships rather than a
generated answer string. Report Recall, Precision, and nDCG at the actual
context sizes under consideration, plus MRR for first-useful-evidence behavior.
Always publish category slices and representative failures; an aggregate can
hide a system that handles exact queries but fails paraphrases or multi-evidence
questions.

The v2 repository benchmark uses BM25 as the control, a local
`BAAI/bge-small-en-v1.5` dense candidate, and reciprocal-rank fusion. The model
is accessed through [FastEmbed's passage and query encoders](https://qdrant.github.io/fastembed/qdrant/Retrieval_with_FastEmbed/),
and model files remain in an ignored local cache. RRF combines ranks rather
than incomparable lexical and cosine scores; this follows the original
[Reciprocal Rank Fusion](https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/)
motivation. It is not assumed to win.

The broader candidate ladder is deliberately staged:

1. BM25 control.
2. Small local dense retriever.
3. BM25 plus dense RRF.
4. Reranker only if top-k noise remains the limiting failure.
5. Late interaction, multilingual, or multimodal retrieval only when the
   product requirement and measured failures justify their cost.

[ColBERTv2](https://arxiv.org/abs/2112.01488) is relevant to the fourth or
fifth stage, while [BGE-M3](https://arxiv.org/abs/2402.03216) is a useful future
candidate when multilingual, long-document, sparse, dense, and multi-vector
coverage matter. Neither is selected merely from public results. Recent
[TREC RAG results](https://trec.nist.gov/pubs/trec33/appendices/trec2024-rag-retrieval.html)
also support testing multi-stage sparse/dense fusion and reranking rather than
assuming a single universal ranker.

## RAG and generation evaluation

Retrieval metrics alone do not establish a good RAG system. Run the generator
with frozen questions, frozen retrieved contexts, and frozen policy versions,
then separate these questions:

- Did retrieval contain every needed claim?
- Did the generator use relevant context and ignore distractors?
- Is each answer claim supported by the supplied context?
- Does each displayed citation map to the supporting chunk and active source?
- Does the system abstain when evidence is absent or contradictory?
- Does it comply with the professor's tutoring and graded-work policy?

[RAGAS](https://aclanthology.org/2024.eacl-demo.16/) introduced reference-free
signals for RAG pipelines. [ARES](https://arxiv.org/abs/2311.09476) evaluates
context relevance, answer faithfulness, and answer relevance with lightweight
judges plus a small human set. [RAGChecker](https://arxiv.org/abs/2408.08067)
adds fine-grained retrieval and generation diagnostics, while
[RAGBench](https://arxiv.org/abs/2407.11005) provides domain-diverse examples
and the TRACe evaluation dimensions. These frameworks inform our metric names
and failure taxonomy; their automatic scores still require validation on our
tutor rubric.

For application-level coverage, use scenario families rather than one QA
average: conceptual explanation, misconception correction, synthesis across
sources, tables or figures, graded-work redirection, ambiguous questions,
missing evidence, conflicting versions, and provider failures. This follows
the multi-scenario, multi-metric spirit of
[HELM](https://arxiv.org/abs/2211.09110). Newer RAG generator benchmarks such
as [LIT-RAGBench](https://arxiv.org/abs/2603.06198) and
[T2-RAGBench](https://arxiv.org/abs/2506.12071) are useful designs for
integration, reasoning, tables, and abstention, but do not replace our
course-specific cases.

## Human and model judges

An LLM judge is an instrument, not ground truth. Before using one as a scalable
driver metric:

1. Create a small, blindly reviewed human anchor set with explicit rubric
   labels and adjudicated disagreements.
2. Compare judge scores with human labels by slice, not only overall.
3. Randomize answer order, repeat a subset with order reversed, and measure
   decision stability.
4. Hide model/provider identity and avoid revealing which answer is the
   baseline.
5. Measure agreement and retain examples where judges disagree.
6. Keep deterministic gates for citations, permissions, versions, secrets, and
   structured-output validity.

These controls address documented LLM-judge
[position bias](https://aclanthology.org/2025.ijcnlp-long.18/) and
[superficial-quality bias](https://aclanthology.org/2024.ccl-1.101/). An
uncalibrated judge must never be the sole reason to replace a component.

## Repository workflow

For every retriever, model, prompt, or architecture proposal:

1. State the decision question and prediction.
2. Freeze a calibration set and a separate held-out set.
3. Run the control and candidates under identical conditions.
4. Reject gate failures before comparing quality.
5. Inspect aggregate, slice, and per-case evidence.
6. Record Keep, Refine, Go Deeper, or Drop.
7. Update the component profile only when the evidence supports a selection.
8. Retain the previous implementation and dataset for regression and rollback.

This is the repository-wide standard for claiming that an algorithm, model, or
architecture is better here.
