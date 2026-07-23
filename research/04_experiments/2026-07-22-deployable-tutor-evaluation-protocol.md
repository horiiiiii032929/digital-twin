# Deployable tutor evaluation protocol

Date: 2026-07-22

Status: internally selected protocol candidate v1.1; professor and
data-governance approval remain required under issue #11 before
implementation, provider calls, or held-out inspection

## Decision

Use a three-layer dataset portfolio and a paired evaluation. Do not use the
current synthetic web-security corpus as the sole final-project dataset, and do
not substitute a public RAG or mathematics-tutoring leaderboard for evaluation
on the intended course.

The final method comparison holds the generator and decoding configuration
fixed and separates four controlled contribution questions:

1. Can the generator answer safely when the required evidence is supplied?
2. Does the professor policy measurably change tutoring behavior?
3. How much quality is lost when oracle evidence is replaced by retrieval?
4. Is retrieval better than supplying all approved documents when the full
   corpus fits the context window?

These paired conditions identify differences under the frozen evaluation setup;
they do not by themselves establish general causal effects. This is a pilot
evaluation. It can support claims about the named course, corpus, model,
prompt, participants, and deployment revision. It cannot support universal
SOTA, institution-wide readiness, or improved learning outcomes.

## Why the existing datasets are insufficient for the final claim

The existing datasets are useful, internally consistent regression assets:

| Asset | Current size | Strength | Final-project limitation |
| --- | ---: | --- | --- |
| `synthetic-web-security-v2` corpus | 40 chunks, 17 documents, 16 source identities | Includes a prohibited source, a superseded source, distractors, locators, and no missing chunk IDs/text | Synthetic and small; it does not represent the approved pilot course or real tutoring dialogue |
| Retrieval v2 held-out set | 40 cases | No duplicate IDs or queries; exact, paraphrase, multi-evidence, distractor, ambiguity, permission/version, and no-evidence slices | Binary relevance does not label required claims or distinguish essential from merely helpful evidence |
| Evidence-sufficiency v1 held-out set | 50 cases | Separate calibration and test files; strong negative coverage | Labels corpus relevance rather than the sufficiency of the actual context returned to the generator |
| Generation v1 | 25 cases | Balanced policy, citation, misconception, ambiguity, and no-evidence preflight | No atomic required claims, claim-to-evidence links, generated-context labels, student state, or multi-turn tutoring evaluation |

Therefore:

- retain all existing datasets for deterministic regression and historical
  comparisons;
- do not quote their aggregate scores as evidence of course-pilot quality;
- create a successor course dataset before the DeepSeek held-out comparison;
  and
- preserve every existing unfavorable result in the result registry.

## Research basis

The protocol adopts established evaluation patterns rather than inventing one
aggregate score:

- [RAGChecker](https://proceedings.neurips.cc/paper_files/paper/2024/hash/27245589131d17368cccdfa990cbf16e-Abstract-Datasets_and_Benchmarks_Track.html)
  motivates claim-level retrieval and generation diagnostics.
- [ARES](https://aclanthology.org/2024.naacl-long.20/) motivates validating an
  automated evaluator against a human-labeled in-domain set before scaling it.
- [ALCE](https://aclanthology.org/2023.emnlp-main.398/) separates citation
  correctness from citation completeness.
- [RAGTruth](https://aclanthology.org/2024.acl-long.585/) demonstrates that RAG
  output still requires fine-grained unsupported and contradictory-claim
  annotation.
- [TREC 2024 RAG](https://trec.nist.gov/data/rag2024.html) publishes separate
  passage relevance, nugget, and citation/support judgments.
- [RGB](https://arxiv.org/abs/2309.01431) motivates noise, negative-rejection,
  information-integration, and counterfactual robustness slices.
- [MRBench](https://aclanthology.org/2025.naacl-long.57/) provides an
  eight-dimension pedagogical taxonomy over 192 conversations and 1,596 tutor
  responses.
- [MathTutorBench](https://aclanthology.org/2025.emnlp-main.11/) separates
  subject expertise, student understanding, pedagogy, and longer-dialogue
  behavior.

Public benchmarks validate constructs and instruments, not the local product.
RAGTruth and ALCE are not course-tutoring datasets; RGB and CRAG are not the
approved course corpus; MRBench and MathTutorBench are mathematics-centered.
Their transferable contribution is the evaluation design and rubric, while the
primary product evidence must remain course-specific.

## Dataset portfolio

### Layer A: public, committed regression suite

Keep the existing synthetic corpus and cases as the permanently reproducible CI
and regression suite. Use it to detect broken parsing, provenance, retrieval,
permission, citation-identity, policy-action, abstention, and provider-failure
behavior.

This layer answers: "Did the implementation regress?" It does not answer:
"Does the deployed tutor work for the selected course?"

### Layer B: frozen offline qualification datasets

Do not reuse one held-out set both to choose components and to make the final
system claim. Use the same schema and rubric vocabulary across three separately
versioned datasets:

| Dataset | Inspectable partition | Sealed partition | Purpose |
| --- | ---: | ---: | --- |
| `generator-qualification-v1` | 48 development cases | 104 held-out cases | Synthetic-only oracle-context qualification for issue #24; no private course data is sent to DeepSeek |
| `context-sufficiency-v2` | 60 context records: 20 base questions x complete/partial/none | 150 context records: 50 base questions x complete/partial/none | Qualify the returned-context verifier in issue #43 without using corpus answerability as a proxy |
| `course-tutor-v1` | 12 professor-anchor plus 48 development cases | 104 sealed final cases | Course-specific final system comparison in issue #25 after component freeze |

The generator and course datasets use the eight scenario types below. Forty-
eight development cases provide six cases per type, and 104 held-out cases
provide 13 cases per type. This even allocation is a coverage decision, not a
claim that each slice has population-level precision. At 104 cases, the
worst-case Wilson 95% interval for one aggregate proportion has a half-width of
about 9.4 percentage points; a 13-case slice has a worst-case half-width of
about 23.9 points and is descriptive only.

The context-sufficiency held-out set has 50 records in each returned-context
state. With zero false answers among 50 `none` records, the approximate one-
sided 95% upper bound is still 5.8%; therefore this set qualifies a bounded
pilot component and does not establish production safety. Prefer actual frozen
retriever outputs. Deliberately constructed complete, partial, or none stress
contexts must be tagged and reported separately from naturally occurring
outputs.

Create `course-tutor-v1` against all 13 official IT5002 lecture PDFs in
[`it5002_lectures_v1.manifest.json`](../05_evaluation/it5002_lectures_v1.manifest.json).
Personal notes may inform question wording and misconceptions but are not
authoritative evidence. Tutorials, assignments, exams, answers, secrets, and
student records remain excluded. Keep private originals and derived passages
outside Git. Commit only schemas, synthetic examples, hashes, permission
metadata, and sanitized aggregate evidence. The 12-case professor anchor
deliberately covers every scenario type and all five course-topic strata while
repeating four high-risk boundaries. It validates expected actions, required
claims, evidence links, and rubric interpretation; it is not a performance
estimate. The 48 development cases may be used for course-specific integration
decisions. Open the 104-case final set once, only after the protocol, component
profile, prompts, thresholds, and analysis code are frozen.

The versioned case contract is
[`course_tutor_v1.schema.json`](../05_evaluation/course_tutor_v1.schema.json),
with semantic rules in the
[`annotation guide`](../05_evaluation/course-tutor-v1-annotation-guide.md) and
the planned 12-case coverage in the
[`professor-anchor blueprint`](../05_evaluation/course-tutor-v1-professor-anchor.md).

No held-out record from component qualification may be used to tune the final
system. No `course-tutor-v1` final record may be inspected during component
selection. If leakage occurs, register the run as invalid and create a new
sealed version rather than silently replacing cases.

Stratify all partitions across these eight scenario types:

1. direct course fact or concept;
2. paraphrase or vocabulary shift;
3. misconception or flawed student reasoning;
4. multi-evidence synthesis;
5. ambiguity requiring clarification;
6. no-evidence or out-of-course request;
7. assessed-work or professor-policy boundary; and
8. conflicting, superseded, prohibited, or permission-sensitive evidence.

Each case must contain:

- stable case ID, dataset version, split, scenario type, and difficulty;
- student question, relevant dialogue history, and declared student state;
- corpus-answerability label;
- expected action: answer, scaffold, clarify, redirect, or abstain;
- atomic required claims and optional claims;
- gold evidence links at source, version, locator, and passage level;
- evidence role: essential, helpful, distractor, prohibited, or superseded;
- professor-policy rule and assessed-work status;
- privacy/safety tags;
- reference rationale rather than one mandatory answer wording; and
- annotator, adjudication state, and revision history.

The output record adds the exact retrieved chunks and scores, context presented
to the model, human context-sufficiency label (`complete`, `partial`, or
`none`), answer, atomic answer claims, citations, policy action, tokens,
latency, cost, errors, and failure category.

### Layer C: deployed-pilot evidence

Use the supervised pilot only for usability, reliability, operational, and
ecological-validity evidence. Keep method selection on the frozen offline data.
Record participant role, task, completion, time, assistance, failed turns,
clarifications, citation use, feedback, incidents, withdrawal, and data
retention status without committing identifying content.

With 5-15 invited users, report raw counts and participant-level distributions.
Do not present averages from this pilot as evidence of learning improvement or
as population-level usability estimates.

## Frozen comparison conditions

Use identical questions, generator version, decoding, token budget, and output
schema in every applicable condition:

| ID | Context | Policy | Question answered |
| --- | --- | --- | --- |
| C0 | None | Generic assistant | What does the unconstrained model do? |
| C1 | Professor-approved oracle evidence | Generic tutoring policy | Can the model use sufficient evidence safely? |
| C2 | Same oracle evidence as C1 | Professor-approved policy | What behavior is attributable to professor policy? |
| C3 | Retrieved evidence | Professor-approved policy | What is the complete deployed RAG result? |
| C4 | All approved documents, when they fit | Professor-approved policy | Is retrieval justified over a full-context control? |

The four required end-to-end conditions are C0-C3. C4 is a conditional control,
not an entry gate: run it only when every approved document fits the frozen
context and provider data boundary. Primary paired contrasts are C1-C2 for
policy contribution, C2-C3 for retrieval loss, C0-C3 for complete-system
value, and C3-C4 for RAG versus full context. Do not change the generator while
making these comparisons.

## Predictions and minimum useful effects

Freeze these predictions before any held-out output. They are project decision
margins for a bounded pilot, not universal benchmark thresholds or proof of
statistical significance:

| ID | Predeclared prediction | Minimum useful or tolerable effect |
| --- | --- | --- |
| H1 | The complete tutor (C3) improves unconditional safe grounded task success over the generic assistant (C0) | At least +10 percentage points |
| H2 | Professor policy (C2) improves pedagogical success over generic tutoring policy with identical oracle evidence (C1) | At least +10 points in required-dimension success, and blinded wins exceed losses by at least 10 points among all applicable pairs |
| H3 | Retrieved evidence (C3) remains close enough to oracle evidence (C2) for a pilot | No more than 10 points lower in unconditional safe grounded task success |
| H4 | When C4 is eligible, retrieval reduces context burden without material quality loss | No more than 5 points lower safe grounded success and at least 20% fewer input-context tokens than C4 |

The 104-case design may not distinguish a 10-point paired effect from zero when
few cases differ or uncertainty is wide. Report the paired interval and make an
explicit `Refine` or `Go Deeper` decision rather than converting an imprecise
result into a positive claim.

## Metrics and decision framework

Selection is lexicographic: hard gates, required quality, operational limits,
relative quality, then complexity and reversibility. Never combine safety and
quality into one weighted score.

### Primary outcomes

1. **Unconditional safe grounded task success**: cases with the correct action,
   all required answer claims supported when answering, correct citation
   behavior, and no policy violation, divided by all cases.
2. **Complete-evidence success@k**: answerable cases for which the top-k context
   contains every essential gold-evidence unit required by the case.
3. **Professor-policy pedagogical success**: applicable cases meeting every
   predeclared required pedagogy dimension without revealing prohibited work,
   supplemented by blinded C1-versus-C2 win/tie/loss judgments.

Freeze denominators with the dataset: safe grounded task success uses all
cases; complete-evidence success uses corpus-answerable cases with at least one
essential gold-evidence unit; pedagogical success uses only cases whose
required dimensions were marked applicable before output generation. A false
answer is an answer when the frozen returned context requires clarify,
redirect, or abstain. A false abstention is failure to answer or scaffold when
the frozen complete context and policy permit it. Always report the excluded
count and reason next to each conditional metric.

### Component and system decision floors

These floors are evaluated only after every applicable hard gate passes:

| Decision | Predeclared quality floor |
| --- | --- |
| Generator/prompt qualification (#24) | At least 80% unconditional safe grounded task success, at least 90% required-claim recall on answer cases, and at least 95% citation correctness and completeness |
| Returned-context verifier (#43) | At least 0.80 three-class macro F1, zero false answers on `none` cases, at least 90% correct answer eligibility on `complete` cases, and at least 90% correct safe action on `partial` plus `none` cases |
| Final course system (#25) | At least 80% unconditional safe grounded task success, at least 80% complete-evidence success@3, at least 85% complete-evidence success@5, at least 80% professor-policy pedagogical success on applicable cases, and H1-H3 within their decision margins |

The verifier's zero observed false-answer gate is intentionally strict for the
tested set but does not imply a zero deployment error rate. Reliable turn
completion must be at least 95%, with end-to-end p95 latency no greater than 10
seconds under the frozen staging load. Issue #24 also retains its cumulative
USD 10 provider-call cap. Report per-turn cost even when the cap passes.

### Diagnostic metrics

- Recall@3/5, precision@3/5, graded nDCG@3, and MRR for first useful evidence;
- gold-claim context coverage and context utilization;
- complete/partial/none context confusion matrix, answerability precision,
  answerability recall, false-answer count, and false-abstention count;
- atomic claim support, contradiction, and unsupported-claim counts;
- citation referential validity, correctness, completeness, and source-version
  validity;
- expected-action accuracy and separate pedagogy-dimension distributions;
- p50/p95 latency, timeout/error rate, input/output/context tokens, per-turn and
  cumulative cost, recovery time, memory/model footprint, and index build time;
- usability task completion, completion time, errors, researcher intervention,
  failed-turn rate, citation comprehension, and role-specific feedback; and
- failures classified as data, parsing, chunking, query, ranking, sufficiency,
  generation, citation, policy, integration, evaluator, privacy, or operations.

### Hard gates

- zero use or disclosure of prohibited, superseded, cross-course, or unapproved
  private evidence;
- zero authorization, privacy, secret, retention, or deletion violations;
- zero prohibited assessed-work completion;
- every displayed citation resolves to an approved active source and locator;
- zero unsupported high-severity factual claims;
- correct visible behavior for no evidence, timeout, malformed provider output,
  and provider outage; and
- no run exceeds the approved external-provider data boundary or cost cap.

A zero count in a small pilot is not proof of population safety. Always report
the denominator and interval or upper bound, and limit the claim to the tested
cases.

## Human judgment and automated evaluation

- Randomize condition order and hide condition identity from reviewers.
- The professor reviews the 12-case anchor and adjudicates ambiguous policy or
  course-content judgments.
- Two independent reviewers label the complete anchor and a stratified 25% of
  final C0-C3 responses, covering every condition and scenario type. Double-
  review every observed hard-gate failure. Report agreement by dimension using
  weighted Cohen's kappa or Krippendorff's alpha as appropriate.
- Preserve disagreements and adjudication; do not silently replace labels.
- Use deterministic rules for IDs, permissions, exact actions, tokens, latency,
  and cost.
- RAGAS, RAGChecker, ARES, or an LLM judge may provide development diagnostics.
  No automated judge selects a model or prompt until its agreement and failure
  modes are measured against the in-domain human labels. Automate a dimension
  only when agreement is at least 0.67 and it produces no false pass on a
  human-labeled hard-gate failure; otherwise retain human judgment for that
  dimension.
- If reviewer agreement is inadequate, refine the rubric and repeat rubric
  calibration without opening the sealed test outputs.

## Statistical reporting

- Report numerator, denominator, estimate, and 95% interval for every primary
  proportion.
- Because conditions share cases, report paired differences with paired
  bootstrap confidence intervals; use McNemar's test for predeclared binary
  contrasts when inferential testing is useful.
- Report pedagogical judgments as per-dimension distributions and blinded
  win/tie/loss, not only an average 1-5 score.
- Correct the small family of confirmatory comparisons with Holm's procedure.
- Report effect sizes and uncertainty even when a p-value is shown.
- Report every slice, but label small-slice findings descriptive rather than
  confirmatory.
- A corrected rerun receives a new result ID; an unfavorable or invalid run
  remains registered.

## Evidence and report outputs

Every named run produces:

1. a frozen plan under `research/04_experiments/`;
2. versioned dataset/rubric metadata under `research/05_evaluation/`;
3. per-case machine-readable output under ignored `reports/generated/`;
4. a readable result summary and component record;
5. a row in `research/05_evaluation/result-registry.md`;
6. any profile decision under `research/05_evaluation/profiles/`;
7. a learning log and decision record; and
8. figures generated from the machine-readable record by a committed script.

The final report should use four main figure families: paired outcome
comparisons with intervals, retrieval-to-generation failure flow, failure-type
distribution, and latency/cost versus grounded success. The deployed-pilot
section adds role-specific task completion and failed-turn plots.

## Stop rules

- Do not inspect sealed outputs before datasets, claims, rubric, conditions,
  metrics, gates, and configuration are frozen.
- Do not keep rerunning until a candidate wins.
- Do not use the public benchmark result as a substitute for course evidence.
- Do not use the synthetic regression distribution as an estimate of real
  student-query frequency.
- Drop optional models, rerankers, or analytics before reducing evidence,
  privacy, or reproducibility requirements.
- If evidence is inconclusive, retain the simplest safe control and report
  `Refine`; no selection is a valid research result.
