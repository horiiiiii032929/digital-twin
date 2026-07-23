# RAG and LLM application benchmarking

The dated literature synthesis in
[Evaluating grounded AI tutoring systems](../research/01_literature/2026-07-15-rag-tutoring-evaluation-practices.md)
records the supporting sources, statistical cautions, and current implications
for generator, evidence-verifier, and vertical-slice evaluation.

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

### Comparison matrix for reporting

Use this table when explaining the evaluation to a supervisor or in the final
report. Read it from left to right: each layer answers a different decision
question, unsafe candidates fail before quality averages are compared, and the
next layer is evaluated without hiding failures from the previous layer.

| Layer | Decision question | Qualification gate | Primary comparison | Diagnostic evidence | Current repository boundary |
| --- | --- | --- | --- | --- | --- |
| Parsing and chunking | Did the source become complete, ordered, traceable evidence units? | approved source, checksum and provenance preserved, unsupported input rejected | extraction completeness, required-structure retention, boundary loss | reading-order errors, duplicate text, chunk size, latency and memory | PyMuPDF and heading-paragraph chunking are the baseline; OCR, layout-aware parsing, and chunk settings still need representative-course evaluation |
| Retrieval | Did the context window contain all evidence needed for the question? | no prohibited or superseded source returned | gold-evidence Recall@3, complete-evidence success@3, graded nDCG@3 | Recall@5, Precision@3/5, MRR, category slices, latency and index burden | BM25 v1 is the rollback baseline; retrieval v2 selected no replacement and currently has binary relevance labels |
| Evidence sufficiency | Should the system answer using this retrieved context? | false-answer count meets the profile threshold | answerability precision and recall, no-evidence accuracy | balanced accuracy, false abstentions, calibration, selective accuracy versus coverage | evidence-sufficiency v1 selected no gate; current scores are heuristic rather than calibrated probabilities |
| Generation and citations | Did the answer express the required claims and support them with approved evidence? | zero high-severity unsupported claims; valid active-version citation references; correct policy action | claim support rate, required-claim recall, citation correctness and completeness | contradiction types, pedagogy rubric, malformed output, repeat stability | deterministic control passed preflight; Gemma was exploratory only; DeepSeek and prompt qualification is active in issue #24 |
| End-to-end tutor | Did the complete system answer or abstain correctly, safely, and helpfully? | all privacy, permission, integrity, provenance, and abstention gates pass | unconditional grounded task success | conditional generation quality, failure attribution, multi-turn consistency | issue #25 remains blocked until generator/prompt and open-set evidence verifier qualify |
| Operations | Is the eligible configuration practical and reproducible? | budget, secret isolation, provider failure, and data-boundary requirements pass | successful-case rate and p95 latency | tokens, per-case and cumulative cost, memory, footprint, timeouts and index maintenance | DeepSeek evaluation is synthetic-only with a cumulative USD 10 issue #24 cap |
| Evaluator validity | Can the comparison and its judgments be trusted? | prospective rubric and held-out split remain uncontaminated | human agreement on a blinded anchor set | order bias, repeated-judge stability, uncertainty intervals and slice sample sizes | automated judging cannot select a candidate until validated against human labels |

Selection is lexicographic, not one weighted score. A candidate first passes
permission, privacy, provenance, integrity, and required abstention gates. It
then passes minimum quality and operational thresholds. Only eligible
candidates are compared on relative quality and complexity.

## Metric contract for this repository

The current metric family is appropriate, but the metrics have different jobs.
Traditional information-retrieval measures diagnose ranking; they do not prove
that a context is sufficient or that an answer is grounded. The
[TREC 2024 RAG track](https://trec.nist.gov/data/rag2024.html) similarly
separates retrieval, augmented generation with supplied retrieval results, and
the complete RAG task. Repository results must preserve those separations.

Metric roles are explicit:

- **hard gate:** a violation disqualifies a candidate regardless of averages;
- **primary:** directly answers the predeclared decision question;
- **diagnostic:** explains behavior but cannot select a candidate alone; and
- **operational:** tests whether an eligible candidate fits the named budget.

The cutoff `K` must match a real context boundary. For the current retrieval
experiments, report `K=3` as the primary evidence window and `K=5` as a
diagnostic candidate window. If runtime context assembly changes those limits,
pre-register and report the new cutoffs rather than keeping a convenient old
number.

### Retrieval and ranking metrics

| Measure | Meaning | Repository role | Important limitation |
| --- | --- | --- | --- |
| Gold-evidence Recall@K | fraction of required gold passages present in the first K results | primary coverage measure at K=3; diagnostic at K=5 | treats all judged passages equally and says nothing about order |
| Complete-evidence success@K | fraction of questions for which every essential evidence item appears in the first K results | primary multi-evidence measure | requires explicit essential-evidence sets |
| nDCG@K | relevance gain discounted by rank and normalized by the ideal ordering | primary ranking measure when relevance is graded | depends on trustworthy relevance grades; with only binary labels it is less informative |
| Precision@K / context precision | proportion of the first K chunks that support at least one required claim | diagnostic for noise and token waste | a redundant chunk may look relevant without adding new information |
| Reciprocal rank / MRR | reciprocal rank of the first relevant result, averaged across answerable questions | diagnostic for first-useful-evidence behavior | ignores missing second or third evidence items |
| Permission/version violations | prohibited or superseded chunks returned | hard gate and raw count | must never be averaged away |

For answerable question `q` with gold evidence set `G_q` and first `K`
retrieved chunks `R_q@K`:

```text
Recall@K(q) = |G_q intersect R_q@K| / |G_q|

Complete-evidence@K(q) = 1 if every essential item is in R_q@K, otherwise 0

RR(q) = 1 / rank of the first relevant result
MRR = mean RR across answerable questions
```

No-evidence questions have no gold passage, so their retrieval recall is
undefined. Exclude them from Recall/MRR denominators and evaluate their false
acceptance separately. Mixing them into MRR as zeros would make the score depend
on class balance rather than ranking quality.

nDCG is retained because it rewards putting highly useful evidence earlier. It
originates from graded-relevance retrieval evaluation
([Järvelin and Kekäläinen, 2002](https://doi.org/10.1145/582415.582418)):

```text
DCG@K = sum from rank i=1..K of (2^relevance_i - 1) / log2(i + 1)
nDCG@K = DCG@K / ideal-DCG@K
```

Use fixed relevance grades with annotation anchors, for example `0=irrelevant`,
`1=helpful`, `2=essential`. If judgments remain binary, publish that limitation
and do not imply that nDCG distinguishes essential from merely helpful evidence.

Chunk-level relevance is not enough for long or multi-part questions. Add:

```text
Gold-claim context coverage =
  required answer claims supported by retrieved context
  / all required answer claims
```

This follows the motivation of RAGChecker's claim recall and context precision,
[CRUX](https://aclanthology.org/2025.findings-emnlp.1151/), and
[sub-question coverage evaluation](https://aclanthology.org/2025.naacl-long.301/):
a ranked list can contain topically relevant passages while still omitting a
load-bearing fact or question facet.

### Evidence-sufficiency and abstention metrics

Treat `answerable` as the positive class. Report the full confusion matrix and
raw counts before derived metrics:

| Measure | Formula or question | Role |
| --- | --- | --- |
| Answerable recall | `TP / (TP + FN)` | primary; how often supported questions are allowed through |
| No-evidence accuracy | `TN / (TN + FP)` | primary safety measure; how often unsupported questions are stopped |
| Answerability precision | `TP / (TP + FP)` | primary; how trustworthy an `answerable` decision is |
| Balanced accuracy | mean of answerable recall and no-evidence accuracy | diagnostic aggregate robust to class imbalance |
| False-answer count | no-evidence cases incorrectly allowed through (`FP`) | hard gate for the current profile |
| False-abstention count | answerable cases incorrectly stopped (`FN`) | primary usefulness diagnostic |
| Brier score and calibration error | whether predicted sufficiency confidence matches observed frequency | required when the verifier emits probabilities |
| Selective accuracy versus coverage | correctness among answered cases versus fraction of cases answered | diagnostic for the abstention tradeoff |

[Sufficient Context](https://research.google/pubs/sufficient-context-a-new-lens-on-retrieval-augmented-generation-systems/)
shows why this boundary is separate: a model can fail despite sufficient
context, or confidently answer when context is insufficient. Threshold-free
AUROC or AUPRC may be reported while developing a classifier, but they cannot
replace metrics at the actual deployed threshold.

Every safety proportion must include its numerator, denominator, and uncertainty.
Zero observed failures is not proof of zero risk. Use the approximate rule of
three for an interpretable 95% upper bound when there are zero failures, and use
bootstrap or an appropriate binomial interval for ordinary proportions.

### Generation, attribution, and answer metrics

Split generated responses into atomic externally verifiable claims. Report:

- **claim support rate:** supported factual claims divided by factual claims;
- **required-claim recall:** required gold answer claims expressed correctly in
  the answer divided by all required claims;
- **contradiction and unsupported-claim counts:** separated by severity;
- **citation referential validity:** every citation identifier maps to supplied,
  approved, active-version evidence;
- **citation correctness:** cited evidence entails the associated atomic claim;
- **citation completeness:** factual claims with adequate citations divided by
  factual claims requiring citations;
- **answer relevance and pedagogical dimensions:** scored with the frozen human
  rubric; and
- **policy action and safe abstention:** exact action accuracy plus raw failures.

This implements the attribution principle in
[AIS](https://aclanthology.org/2023.cl-4.2/) and the citation evaluation in
[ALCE](https://aclanthology.org/2023.emnlp-main.398/). A valid citation ID is
only a structural check; it does not prove entailment. RAGChecker-style
claim-level diagnostics are preferred to one response-level faithfulness number
because they expose the exact unsupported statement.

Exact match and token F1 may be used for narrowly specified fact questions with
stable reference answers. They are not primary for free-form tutoring because
correct explanations can use different wording, and verbose instruction-following
answers make traditional QA matching unreliable
([Adlakha et al., 2024](https://aclanthology.org/2024.tacl-1.38/)).

### End-to-end and operational metrics

Report at least two end-to-end views:

1. **unconditional grounded task success:** correct supported answer when
   answerable, correct abstention when not, valid citations, and correct policy
   action across all cases; and
2. **conditional generation quality:** answer quality only on cases where the
   supplied context was independently judged sufficient.

The first measures the product. The second separates generator failure from
retrieval/context failure. Also report slice results, complete-system hard-gate
pass rate, failure category, p50/p95 latency, timeouts, input/output/context
tokens, cumulative and per-case cost, memory, disk/model footprint, and index
build/update burden.

### Required result presentation

Every comparison used in the report must contain:

- the exact control and candidates under paired inputs and matched token budgets;
- aggregate metrics plus direct, paraphrase, multi-evidence, distractor,
  ambiguity, no-evidence, permission, version-conflict, table/figure, and
  integrity slices where applicable;
- raw numerators and denominators, per-case records, uncertainty intervals, and
  the predeclared minimum useful effect;
- both favorable and unfavorable representative cases;
- a failure attribution to data, parsing, chunking, query, ranking, sufficiency,
  generation, citation, policy, integration, or operations; and
- the resulting Keep, Refine, Go Deeper, or Drop decision.

Do not select a candidate from a higher average alone. A useful claim for the
final report must say which dataset, cutoff, profile, model, prompt, and budget
the improvement applies to.

### Current implementation boundary

The metric contract above defines the next benchmark and final-report standard;
it does not retroactively add information to completed runs. The existing
retrieval v2 dataset declares binary relevant-passage references. Its evaluator
already reports Recall@1/3/5, Precision@1/3/5, binary nDCG@3, MRR over answerable
cases only, no-evidence accuracy, permission/version violations, category
slices, latency, and per-case hits. This separation of answerable and
no-evidence denominators is retained.

Retrieval v2 does not yet emit a named aggregate for complete-evidence
success@3, does not distinguish `helpful` from `essential` evidence, and does
not label required answer claims. The successor benchmark must add those labels
and metrics before graded nDCG or gold-claim context coverage is reported. Old
binary nDCG results must continue to be identified as binary.

The evidence-sufficiency v1 evaluator reports answerable recall, no-evidence
accuracy, balanced accuracy, false-answer and false-abstention counts, and
conditional versus unconditional retrieval quality. Its gate score is an
inspectable heuristic score, not a validated probability. The next evaluation
must add answerability precision and the full confusion matrix. Brier score,
expected calibration error, and selective-risk curves become valid only after a
candidate produces a probability-like confidence that is calibrated on the
calibration split and evaluated once on held-out data.

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
