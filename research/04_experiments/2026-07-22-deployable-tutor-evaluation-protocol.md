# Deployable tutor evaluation protocol

Date: 2026-07-22

Status: selected protocol for professor review and freeze under issue #11

## Decision

Use a three-layer dataset portfolio and a paired evaluation. Do not use the
current synthetic web-security corpus as the sole final-project dataset, and do
not substitute a public RAG or mathematics-tutoring leaderboard for evaluation
on the intended course.

The final method comparison holds the generator and decoding configuration
fixed and separates four causal questions:

1. Can the generator answer safely when the required evidence is supplied?
2. Does the professor policy measurably change tutoring behavior?
3. How much quality is lost when oracle evidence is replaced by retrieval?
4. Is retrieval better than supplying all approved documents when the full
   corpus fits the context window?

This is a pilot evaluation. It can support claims about the named course,
corpus, model, prompt, participants, and deployment revision. It cannot support
universal SOTA, institution-wide readiness, or improved learning outcomes.

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

### Layer B: course-specific gold benchmark

Create `course-tutor-v1` from 4-8 explicitly approved course documents. Keep
private originals and derived passages outside Git. Commit only schemas,
synthetic examples, hashes, permission metadata, and sanitized aggregate
evidence.

Use three non-overlapping partitions:

| Partition | Cases | Purpose | Access rule |
| --- | ---: | --- | --- |
| Professor anchor | 12 | Validate expected actions, required claims, evidence links, and rubric interpretation | May be inspected before evaluation; never used as the final estimate |
| Development/calibration | 48 | Develop prompts, thresholds, context verifier, and scorer behavior | Candidates may be tuned only here |
| Sealed diagnostic test | 72 | Final paired component and system comparison | Open once for the named run after protocol and configuration freeze |

The 72-case held-out set is a feasibility-sized pilot diagnostic, not a
population survey. Report uncertainty and avoid interpreting small differences
or nine-case slice estimates as stable general effects.

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

Primary paired contrasts are C1-C2 for policy effect, C2-C3 for retrieval loss,
C0-C3 for complete-system value, and C3-C4 for RAG versus full context. Do not
change the generator while making these comparisons.

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
- Two independent reviewers label at least the complete anchor and 25% of final
  responses. Report agreement by dimension using weighted Cohen's kappa or
  Krippendorff's alpha as appropriate.
- Preserve disagreements and adjudication; do not silently replace labels.
- Use deterministic rules for IDs, permissions, exact actions, tokens, latency,
  and cost.
- RAGAS, RAGChecker, ARES, or an LLM judge may provide development diagnostics.
  No automated judge selects a model or prompt until its agreement and failure
  modes are measured against the in-domain human labels.
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
