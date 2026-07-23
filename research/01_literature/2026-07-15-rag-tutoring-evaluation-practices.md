# Evaluating grounded AI tutoring systems

Date reviewed: 2026-07-15

## Research question

How should this project evaluate a course-grounded AI tutor so that component
choices are replaceable, failures are diagnosable, and claims about teaching or
learning do not exceed the available evidence?

## Conclusion

There is no single trustworthy "RAG score" or public benchmark that can select
the complete system. The defensible pattern is a layered evaluation stack:

1. evaluate retrieval and context construction;
2. evaluate whether the evidence is sufficient to answer;
3. evaluate generated claims and citations against that evidence;
4. evaluate tutoring behavior with an explicit pedagogical rubric;
5. evaluate the integrated, multi-turn system under operational and safety
   constraints; and
6. evaluate student learning outcomes separately when a consented study is
   possible.

This structure matches the repository's component contracts and evaluation
profiles. An aggregate score may summarize eligible candidates, but it must not
hide which component failed or allow a quality gain to compensate for a privacy,
permission, integrity, provenance, or unsafe-answer failure.

## What established evaluations measure

### Retrieval and context construction

[BEIR](https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/65b9eea6e1cc6bb9f0cd2a47751a186f-Abstract-round2.html)
shows that retrieval performance varies across heterogeneous domains and tasks.
[CRAG](https://papers.nips.cc/paper_files/paper/2024/hash/1435d2d0fca85a84d83ddcb754f58c29-Abstract-Datasets_and_Benchmarks_Track.html)
also evaluates results across question types and difficulty rather than relying
only on one overall result.

The repository should therefore measure Recall@K, MRR, and nDCG at the context
sizes it actually uses, then report slices for exact-term, paraphrase,
multi-evidence, distractor-heavy, ambiguous, no-evidence, superseded-source, and
permission-restricted cases. Latency and resource use remain part of the
comparison. BM25 is the inspectable control; dense and hybrid methods are
candidates, not presumed upgrades.

The metrics have different roles. Recall@K measures how much required evidence
was found, MRR only measures the rank of the first useful item, and nDCG rewards
placing more important evidence earlier. MRR is therefore diagnostic rather
than primary for multi-evidence questions. Add complete-evidence success@K and
gold-claim context coverage so an apparently good ranking cannot hide a missing
load-bearing passage. The central
[RAG benchmarking guide](../../docs/rag-and-llm-benchmarking.md#metric-contract-for-this-repository)
records the formulas, cutoffs, limitations, and result-presentation contract.
Its current-implementation boundary also records that retrieval v2 uses binary
relevance judgments and that complete-evidence, graded relevance, and
claim-coverage fields belong to the successor benchmark. Completed results must
not be relabeled as if those judgments had already been collected.

### Evidence sufficiency

[ARES](https://aclanthology.org/2024.naacl-long.20/) evaluates context relevance,
answer faithfulness, and answer relevance using automated judges corrected with
a human-labeled set. The reusable principle is to validate an automated judge
against human decisions and quantify uncertainty rather than treating the judge
as ground truth.

The evidence verifier should report answerability precision and recall, false
answers, false abstentions, balanced accuracy, and calibration. It should retain
raw numerators and denominators for safety-relevant rates. Observing zero false
answers does not prove a zero population failure rate: by the rule of three,
zero failures in 60 no-evidence cases gives an approximate 95% upper bound of
5%. Roughly 300 zero-failure no-evidence cases would be needed for an upper bound
near 1%.

### Claims, grounding, and citations

[RAGChecker](https://arxiv.org/abs/2408.08067) uses fine-grained diagnostics to
separate retriever and generator failures, while
[RAGTruth](https://aclanthology.org/2024.acl-long.585/) provides human-annotated
unsupported content for retrieval-augmented generation.
[ALCE](https://arxiv.org/abs/2305.14627) makes an especially important
distinction:

- citation correctness asks whether a citation actually supports its claim;
- citation completeness asks whether all externally verifiable claims have
  adequate support.

A valid document or chunk identifier therefore does not establish groundedness.
Generation evaluation should divide an answer into atomic claims and label each
claim as supported, partially supported, unsupported, contradicted, or not
requiring evidence. Referential citation validity remains a deterministic gate,
while support and completeness require evidence-aware judgment.

This choice is also consistent with the
[TREC 2024 RAG evaluation design](https://trec.nist.gov/data/rag2024.html),
which separates retrieval judgments, attributed generation, and the complete
pipeline. The final report should preserve component results and end-to-end
results rather than presenting one combined score.

### Tutoring behavior

[MRBench](https://aclanthology.org/2025.naacl-long.57/) treats tutor evaluation as
multidimensional, and
[MathTutorBench](https://arxiv.org/abs/2502.18940) separates subject expertise,
student understanding, and pedagogical capability. Solving a problem correctly
does not by itself demonstrate effective tutoring.

After factual support passes as a qualification gate, the project should score
misconception diagnosis, use of student reasoning, appropriate scaffolding,
adaptation, clarity, uncertainty, and avoidance of unnecessary direct answers.
These dimensions should remain visible instead of being hidden in one average.
No universal prompt style, including a Socratic style, should be selected before
it is tested against the relevant course scenarios and professor policy.

### Automated evaluators

[G-Eval](https://aclanthology.org/2023.emnlp-main.153/) demonstrates that
rubric-guided LLM evaluation can correlate with human judgments. The
[MT-Bench judge study](https://proceedings.neurips.cc/paper_files/paper/2023/file/91f18a1287b398d378ef22505bf41832-Paper-Datasets_and_Benchmarks.pdf)
also documents limitations such as position, verbosity, and self-enhancement
biases.

Before an LLM judge contributes decision evidence, candidate identities should
be hidden, response order should be randomized and reversed on a stability
subset, and a blindly human-reviewed anchor set should be adjudicated. Agreement
and judge errors must be reported by slice. Deterministic checks should continue
to enforce permissions, versions, citation identifiers, secrets, and structured
output.

### End-to-end behavior and learning outcomes

An offline vertical-slice evaluation can support claims about groundedness,
policy compliance, pedagogical plausibility, latency, and cost. It cannot show
that students learn more. A preregistered randomized study found that unrestricted
generative-AI assistance could improve assisted practice performance while
harming later unassisted performance
([Bastani et al., PNAS](https://doi.org/10.1073/pnas.2422633122)). Field research
such as [Tutor CoPilot](https://nssa.stanford.edu/sites/default/files/Tutor_CoPilot.pdf)
therefore measures outcomes with real tutors and learners rather than inferring
learning from answer quality.

Claims about learning should wait for an approved study measuring unassisted
post-help performance, transfer, delayed retention, and differences by prior
knowledge. Multi-turn evaluation should also test student-state tracking and
cumulative adaptation; [LongTutor](https://aclanthology.org/2026.acl-long.1371/)
is a useful design reference for that later stage.

## Application to the current roadmap

### Issue #24: DeepSeek generator and prompt qualification

- Keep the deterministic generator as the control.
- Treat DeepSeek API as the fixed primary product constraint, not as an
  evidence-backed claim that it is the best model.
- Qualify DeepSeek against the deterministic structural control and retain
  Gemma 3 4B as the zero-cost local fallback rather than running a broad model
  leaderboard.
- Compare at least two predeclared prompt conditions using identical sufficient
  gold evidence and policies, then freeze the qualified configuration before
  varying RAG context strategies.
- Add atomic-claim labels and keep citation correctness, citation completeness,
  factual support, and pedagogical dimensions separate.
- Freeze the rubric, thresholds, review procedure, and analysis before inspecting
  held-out outputs.
- Treat the planned 100 held-out cases as candidate-selection and regression
  evidence, not evidence that the tutor improves learning.
- Permit only synthetic data for external calls and stop before the cumulative
  #24 DeepSeek API spend can exceed USD 10.

### Issue #43: open-set evidence verifier

- Use answerable and no-evidence cases with difficult near-domain distractors.
- Report false-answer and false-abstention behavior separately, including
  confidence intervals and calibration.
- Use the first dataset size as a selection floor and state the failure-rate bound
  it can support; expand the no-evidence set before making a production safety
  claim.

### Issue #25: grounded tutoring vertical slice

- Run only after generator/prompt and evidence-sufficiency decisions are valid.
- Combine component gates with end-to-end scenario and operational measurements.
- Preserve component-level failure attribution instead of reporting only total
  task success.
- Reserve learning-effectiveness claims for a later consented outcome study.

## Recommended evaluation toolkit

Use RAGAS-style reference-free signals for fast development feedback,
RAGChecker-style claim diagnostics for durable failure analysis, ARES-style
human calibration when scaling automated judgments, ALCE-style citation
correctness and completeness, and MRBench/MathTutorBench-inspired pedagogical
dimensions. These are design references rather than a substitute for the
versioned course-specific dataset and professor policy.

NotebookLM should be included later as an external black-box product reference
using the same synthetic source pack and questions. Its source-restricted chat,
direct quotation citations, and locator navigation are valuable grounding and
UX references, but its model, retrieval, prompt, and version cannot be frozen or
inspected. It therefore cannot replace the full-document and BM25 scientific
controls or select an internal component. ChatGPT file-based and deep-research
behavior may provide a second external product reference, subject to the same
reproducibility limitation.

## Immediate work order

The next milestone is not another model run. First pre-register the #24
evaluation: freeze the exact DeepSeek identifier and parameters, prompt
versions, sufficient gold-evidence contexts, case slices, claim labels,
pedagogical rubric, thresholds, human-review protocol, statistical reporting,
operational measurements, and the synthetic-only USD 10 cap. Only then prepare
the development/calibration set, validate the scoring instruments, and seal the
held-out set. After DeepSeek and the prompt qualify, hold them constant while
comparing full-document, BM25, dense, hybrid, and justified reranked context
strategies.
