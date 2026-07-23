# State-of-the-art references for grounded tutor evaluation

Date reviewed: 2026-07-22

## Decision question

Which recent research results should inform the Digital Twin tutor's retrieval,
grounding, citation, pedagogical, and reporting evaluations, and which reported
state-of-the-art methods are credible candidates for local comparison?

## Conclusion

No paper establishes a universally state-of-the-art system for an
instructor-aligned, course-grounded tutor. Published state-of-the-art claims are
conditional on a named benchmark, corpus, model, prompt, evaluator, and budget.
They provide candidate methods and evaluation patterns, not evidence that a
component should be selected for `student-tutor-v0`.

The strongest transferable result is methodological: evaluate the pipeline at
separate boundaries. The project must distinguish:

1. whether an answer exists in the approved corpus;
2. whether the context actually returned to the model is sufficient;
3. whether every generated claim is supported by that context;
4. whether citations are correct and complete;
5. whether the response follows the professor's pedagogical policy; and
6. whether the integrated tutor improves an appropriate student outcome.

This separation is required before the project can defend a comparison between
a generic assistant, a grounded assistant, and the professor-configured Digital
Twin tutor.

## Research most relevant to the current evaluation defect

### Context sufficiency is not corpus answerability

[Sufficient Context: A New Lens on Retrieval Augmented Generation Systems](https://openreview.net/forum?id=Jjr2Odj8DJ)
(Joren et al., ICLR 2025) explicitly separates whether retrieved context contains
enough information from whether the generator uses that information correctly.
It reports that strong proprietary models often answer incorrectly instead of
abstaining when context is insufficient, while smaller models may hallucinate or
abstain even when context is sufficient.

This directly applies to the repository's current evidence-sufficiency
evaluation. A case must not be labeled `expected_answerable=true` merely because
the answer exists somewhere in the corpus. The label presented to an evidence
gate must describe the actual returned context, with at least:

- `complete`: all required claims are supported by the returned context;
- `partial`: some useful evidence is present but at least one required claim is
  unsupported; and
- `none`: the returned context does not support the requested answer.

Corpus answerability remains a separate retrieval label. A retrieval miss on a
corpus-answerable question is a retrieval failure; abstaining on the resulting
insufficient context can still be the correct gate behavior.

[Unanswerability Evaluation for Retrieval Augmented Generation](https://aclanthology.org/2025.acl-long.415/)
(Peng et al., ACL 2025) introduces UAEval4RAG and a six-category taxonomy of
knowledge-base-specific unanswerable requests. Its experiments find that no
single configuration consistently optimizes both answerable and unanswerable
behavior across knowledge bases. For issue #43, this supports using several
unanswerable types and reporting the answer-versus-abstain tradeoff rather than
searching for one universal similarity cutoff.

### Retrieval and generation failures need separate diagnostics

[RAGChecker](https://proceedings.neurips.cc/paper_files/paper/2024/hash/27245589131d17368cccdfa990cbf16e-Abstract-Datasets_and_Benchmarks_Track.html)
(Ru et al., NeurIPS 2024) evaluates retrieval and generation with fine-grained
diagnostic metrics and reports stronger human correlation than earlier metric
sets. It supports keeping retrieval coverage, context precision, claim recall,
faithfulness, and end-to-end task success visible rather than collapsing them
into one score.

[RAGAS](https://aclanthology.org/2024.eacl-demo.16/) (Es et al., EACL 2024)
provides reference-free development metrics for retrieval focus, faithfulness,
and answer quality. These signals are useful for rapid iteration, but they do not
replace frozen gold evidence, claim labels, or professor review in a
decision-bearing run.

[ARES](https://aclanthology.org/2024.naacl-long.20/) (Saad-Falcon et al., NAACL
2024) combines automated evaluation with a smaller human-labeled set and
statistical correction. The transferable principle is to validate any automated
judge against blinded human labels from this project before using it to select a
prompt, verifier, or model.

[RAGEval](https://aclanthology.org/2025.acl-long.418/) (Zhu et al., ACL 2025)
generates scenario-specific evaluation material and extracts factual key points
for completeness, hallucination, and irrelevance scoring. Its key-point design
is applicable to a professor-reviewed course dataset, but automatically
generated cases still need expert review before they become held-out evidence.

### Citation identity is weaker than citation faithfulness

[ALCE](https://aclanthology.org/2023.emnlp-main.398/) (Gao et al., EMNLP 2023)
separates citation correctness from citation completeness. A citation can point
to a real retrieved source while failing to support the associated statement,
and a response can correctly cite one claim while leaving other verifiable
claims unsupported.

[RAGTruth](https://aclanthology.org/2024.acl-long.585/) (Niu et al., ACL 2024)
contains human annotations of unsupported and contradictory content at case and
word level. It demonstrates why answer-level citation-ID validity cannot act as
a factual-support score.

[LongCite](https://aclanthology.org/2025.findings-acl.264/) (Zhang et al.,
Findings of ACL 2025) reports state-of-the-art citation quality on
LongBench-Cite using sentence-level citations and citation-focused training.
That result makes sentence-level attribution a plausible future candidate, but
it does not select LongCite for this project or prove performance on course
tutoring.

The local generation dataset should therefore add required atomic claims and
claim-to-evidence links. Deterministic citation identity should remain a hard
integrity gate, while human-validated claim support and citation completeness
measure grounding quality.

## Reported state-of-the-art methods and their local meaning

| Paper or system | Published result | Scope of the claim | Local implication |
| --- | --- | --- | --- |
| [BGE M3-Embedding](https://arxiv.org/abs/2402.03216) | Reports state-of-the-art multilingual and cross-lingual retrieval results while supporting dense, sparse, and multi-vector retrieval | Public multilingual retrieval benchmarks; technical report | Candidate for a later multilingual or hybrid comparison, not a replacement for BM25 without course-corpus evidence |
| [RankRAG](https://proceedings.neurips.cc/paper_files/paper/2024/hash/db93ccb6cf392f352570dd5af0a223d3-Abstract-Conference.html) | Outperforms strong RAG baselines on nine general knowledge-intensive benchmarks and is competitive on biomedical benchmarks | Instruction-tuned ranking and generation with Llama 3; NeurIPS 2024 | A `Go Deeper` reference if simple reranking and set selection fail; too complex to adopt before the baseline question is valid |
| [SetR](https://aclanthology.org/2025.acl-long.861/) | Outperforms proprietary LLM rerankers and open baselines on multi-hop RAG benchmarks | Set-wise passage selection for multi-evidence QA; ACL 2025 | Directly motivates complete-evidence and claim-coverage metrics; candidate only if multi-evidence failures remain important |
| [LongCite](https://aclanthology.org/2025.findings-acl.264/) | Reports state-of-the-art citation quality on LongBench-Cite | Long-context QA with sentence-level citations; Findings of ACL 2025 | Motivates fine-grained citation output and evaluation, not model selection |
| [LearnLM](https://arxiv.org/abs/2412.16429) | Reports expert-rater preference over GPT-4o, Claude 3.5, and its Gemini 1.5 Pro base across learning scenarios | Pedagogical instruction following; technical report | Supports a professor-policy condition and expert pairwise review; does not establish learning gains or qualify DeepSeek |
| [MRBench](https://aclanthology.org/2025.naacl-long.57/) | Provides 192 conversations, 1,596 annotated responses, and eight pedagogical dimensions across AI and human tutors | Mathematics tutoring; NAACL 2025 | Strong source for rubric dimensions, but course-specific professor anchors are still required |
| [MathTutorBench](https://aclanthology.org/2025.emnlp-main.11/) | Finds that subject-solving expertise does not automatically produce good tutoring and that longer dialogue is harder | Mathematics tutoring; EMNLP 2025 | Requires separate subject-correctness, student-understanding, pedagogy, and multi-turn measures |
| [MMTutorBench](https://aclanthology.org/2026.acl-long.1068/) | Evaluates 12 multimodal models on 770 problems with problem-specific six-dimension rubrics and finds a remaining human-tutor gap | Multimodal mathematics tutoring; ACL 2026 | Supports problem-specific rubrics and later figure/slide evaluation; not applicable to the current text-only selection |
| [DeepSeek-V3](https://arxiv.org/abs/2412.19437) | Reports performance competitive with leading closed models and stronger than other open models on its benchmark suite | General model technical report | Supports DeepSeek as a plausible constrained provider, not as an evidence-selected RAG tutor |

These are benchmark-specific results. They must not be rewritten in the final
report as “the project uses the state of the art.” A defensible statement is:

> The project evaluates simple baselines against candidates motivated by recent
> peer-reviewed RAG and tutoring research under a course-specific dataset,
> professor policy, privacy boundary, and operational budget.

## Baselines required by recent evidence

[Retrieval Augmented Generation or Long-Context LLMs?](https://aclanthology.org/2024.emnlp-industry.66/)
(Li et al., EMNLP Industry 2024) reports that sufficiently resourced long-context
models outperform RAG on average in its evaluated datasets, while RAG remains
substantially cheaper. The Digital Twin experiment should therefore compare RAG
with a full-approved-document or long-context control when the course corpus
fits the model context window. RAG should not be assumed superior by design.

[CRAG](https://proceedings.neurips.cc/paper_files/paper/2024/hash/1435d2d0fca85a84d83ddcb754f58c29-Abstract-Datasets_and_Benchmarks_Track.html)
(Yang et al., NeurIPS 2024) finds large remaining reliability gaps even for
advanced RAG solutions across diverse and dynamic questions. Public benchmark
performance is therefore prior evidence for candidate selection, not a local
release gate.

The course experiment should hold the exact DeepSeek model and parameters fixed
and compare at least:

1. generic DeepSeek without course context or professor policy;
2. DeepSeek with approved evidence but a generic tutoring policy;
3. DeepSeek with the same evidence and professor-approved policy; and
4. a full-approved-document context condition when the corpus fits safely.

An oracle-evidence condition should be used separately to qualify generation
and prompting without retrieval confounding. Retrieved-evidence conditions then
measure the complete system.

## Pedagogical and learning-outcome evidence

MRBench and MathTutorBench both show why answer correctness is not a tutoring
metric. The local rubric should adapt their dimensions to the professor's
policy, including misconception identification, use of student reasoning,
guidance quality, actionability, scaffolding, clarity, and avoidance of giving
away assessed work.

LearnLM's expert pairwise evaluation supports comparing policy conditions with
blinded response order. It does not justify copying one universal pedagogical
style: the Digital Twin claim concerns adherence to a named professor-approved
profile.

Offline response ratings cannot demonstrate improved learning. That claim
requires student participants, consent, and outcomes such as unassisted transfer
or delayed retention. Until such a study exists, the report must use terms such
as `pedagogical quality`, `professor alignment`, and `grounded task success`, not
`learning improvement`.

## Reproducible reporting

[ReproEvalCard](https://aclanthology.org/2026.acl-short.22/) (Pattnayak and
Bhatia, ACL 2026) identifies prompts, judge configurations, retrieval snapshots,
randomness controls, and intermediate traces as necessary artifacts for
reproducing multi-stage LLM evaluations. This aligns with the repository's
result registry and profiles. Each decision-bearing run should additionally
preserve:

- the exact generation and evaluation prompts;
- the judge model, parameters, order randomization, and repeated judgments;
- retrieved hit IDs, scores, versions, and context presented to the generator;
- claim and citation judgments plus adjudication state;
- seeds or an explicit explanation when a provider does not expose them; and
- separate retrieval, gate, provider-call, and end-to-end latency measurements.

## Required changes before issues #24, #43, and #25 continue

1. Replace the binary evidence-gate target derived from query category with a
   human-reviewed label over the actual returned context: complete, partial, or
   none.
2. Keep corpus answerability, retrieval completeness, context sufficiency, and
   final-answer correctness as separate fields and metrics.
3. Add required atomic claims and claim-to-evidence mappings to generation
   cases before the held-out outputs are inspected.
4. Pilot the rubric on professor-reviewed course scenarios and measure reviewer
   agreement before scaling an LLM judge.
5. Compare generic, grounded, and professor-configured conditions using the
   same DeepSeek model and questions; add the long-context control where
   feasible.
6. Report citation identity, claim support, citation correctness, and citation
   completeness separately.
7. Preserve a representative-use set for quality estimates and a deliberately
   oversampled safety set for hard-gate stress testing; do not interpret the
   stress-set class balance as real usage frequency.
8. Retain BM25 and deterministic behavior as controls. Add BGE-M3, cross-encoder
   verification, SetR-style selection, RankRAG, or citation-specialized models
   only as bounded candidates justified by observed local failures.

## Decision for this project

`Refine` the evaluation design before another decision-bearing provider run.
The literature supports the repository's modular architecture and its refusal
to hide component failures, but it also confirms that the current corpus-level
answerability label cannot validate context sufficiency and that citation-ID
integrity cannot validate factual support.

No component profile changes follow from this review. The next evidence target
is a professor-reviewed pilot that validates the research question, conditions,
context labels, atomic claims, and rubric before the DeepSeek held-out run.
