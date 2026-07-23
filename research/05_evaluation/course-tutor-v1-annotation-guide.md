# Course-tutor-v1 annotation guide

Date: 2026-07-23

Status: schema candidate v1.1 for professor-anchor review; private draft cases
may be authored locally, but no case is approved for tutoring or evaluation

## Purpose

`course-tutor-v1` is the course-specific gold benchmark for the deployable
tutor. It evaluates whether one frozen system can use approved evidence, follow
the professor's policy, respond appropriately to the student's declared state,
and fail safely.

The selected candidate course corpus is all 13 official IT5002 lecture PDFs in
[`it5002_lectures_v1.manifest.json`](it5002_lectures_v1.manifest.json). The
anchor and later splits cover five topic strata: foundations, MIPS ISA,
datapath/control, memory hierarchy, and operating systems/processes/IPC.

The machine-readable contract is
[`course_tutor_v1.schema.json`](course_tutor_v1.schema.json). The committed
[`course_tutor_v1_synthetic_example.json`](course_tutor_v1_synthetic_example.json)
demonstrates the shape without containing real course, professor, or student
data.

Schema v1.1 adds a manifest-controlled topic stratum and allows a private local
draft to retain `pending` tutoring permission. Pending evidence may be authored
and reviewed locally, but it cannot enter a tutor run or count as approved gold
evidence.

## Unit of analysis

One **case** is one frozen student question plus any necessary prior dialogue,
declared student state, expected tutoring behavior, atomic claims, evidence
links, policy rules, rubric applicability, and annotation history.

A case is not a retrieved context and is not a model response. One case may be
run through C0-C4 and may produce several returned-context records. Keeping
these units separate prevents a retriever's current behavior from becoming the
gold label.

## Record groups

| Group | What it fixes before a run | Why it is separate |
| --- | --- | --- |
| Dataset identity | Version, split, language, course, corpus, policy, rubric, permission, full-context eligibility, and sealing state | Makes every result traceable to one frozen input |
| Student input | Question, minimal dialogue, and declared or scenario-supported learning state | Prevents the evaluator from inventing student intent after seeing the response |
| Ground truth | Corpus answerability, expected action, allowed support, atomic claims, evidence links, and policy rules | Separates content correctness from tutoring behavior |
| Rubric applicability | Required pedagogy dimensions, hard-gate focus, and policy-pair eligibility | Fixes metric denominators before output generation |
| Stressors | Retrieval, safety, and operational challenge tags | Supports failure slices without using the tag as the answerability label |
| Annotation | Authors, reviewers, disagreement, revision, and professor decision | Preserves how the gold label was produced |

## Required conceptual separations

### Corpus answerability is not returned-context sufficiency

- `corpus_answerability` asks whether approved evidence exists anywhere in the
  frozen corpus.
- Returned-context sufficiency asks whether the evidence actually supplied to
  the generator is `complete`, `partial`, or `none`.
- The first is a case label. The second is a human judgment in the run output.
- Neither is inferred from query category, retrieval score, or vocabulary
  overlap.

### A gold case is not a reference answer

Do not prescribe one ideal paragraph. Record:

- atomic required and optional claims;
- the evidence supporting each claim;
- the expected primary action and acceptable alternatives;
- forbidden actions and maximum support level; and
- a rationale describing what valid behavior must accomplish.

This permits different correct wording while making unsupported additions,
missing claims, over-help, and policy violations measurable.

### Student state must be evidenced, not guessed

Use only a state declared in the question, supported by the dialogue, or
explicitly created as part of a synthetic scenario. Do not infer emotion,
disability, demographic attributes, motivation, or ability from writing style.
`basis` records where the state came from.

## Case-construction workflow

1. Confirm the source is approved for this course, use, and provider boundary.
2. Select exactly one primary scenario type and any secondary stressors.
3. Record case family, authoring method, any parent case, transformation, and a
   reason for the difficulty label.
4. Write an authentic but synthetic or explicitly approved student question.
5. Add only dialogue needed to establish the student's attempt or intent.
6. Set corpus answerability without looking at a candidate's retrieved output.
7. Decompose the valid content into the smallest independently judgeable
   required claims.
8. Link every required claim to approved, active source-version passages.
9. Define the primary action, acceptable alternatives, forbidden actions,
   allowed support level, citations, and required tutoring moves.
10. Predeclare applicable pedagogy dimensions and hard-gate focus.
11. Complete independent review, preserve disagreements, and obtain professor
    approval for every anchor case before scaling the dataset.

## Semantic validation rules

JSON Schema validates shape and controlled values. The following cross-field
rules must also pass before a split is approved:

| Rule | Failure meaning |
| --- | --- |
| Dataset and case IDs are unique; every case split matches the file split and every topic ID appears in the corpus manifest | Provenance, split, or topic corruption |
| Every case-family ID occurs in one split only; parent and transformation history resolve | Paraphrase or transformed-case leakage |
| Every difficulty label has a task-specific rationale | Uninterpretable slice label |
| Every `answer` or content-bearing `scaffold` case has at least one required claim | Success cannot be judged |
| Every required factual claim maps to at least one `essential`, `approved`, active-version evidence unit | Gold answer is not grounded |
| Every claim-to-evidence reference resolves in both directions | Broken annotation graph |
| `prohibited`, `superseded`, and `unapproved` evidence never supports a required claim | Unsafe gold label |
| `not_answerable` cases contain no essential factual evidence and do not require an unsupported answer | False-answer target is invalid |
| Assessed-work cases declare assessment context, allowed support level, and at least one forbidden behavior | Integrity behavior is ambiguous |
| Privacy/authorization stress cases name the prohibited behavior without embedding real personal data | Safety test creates its own privacy risk |
| Hard-gate and pedagogy applicability are set before model output | Denominator can be changed after seeing results |
| Anchor cases reach `professor_approved`; held-out cases are sealed and not professor-previewed individually | Instrument or split leakage |
| Normalized questions, dialogue, and claim sets do not duplicate or paraphrase a record in another split | Development-to-test leakage |
| Direct identifiers, raw consent records, grades, private forum text, and unapproved transcripts are absent | Data-boundary violation |

## Evidence-link rules

Evidence units store identity and integrity metadata, not committed private
source text:

- stable source artifact ID and active version;
- stable passage ID and human-readable locator;
- SHA-256 of the exact approved passage;
- role: essential, helpful, distractor, prohibited, or superseded;
- permission state; and
- claim IDs supported by the passage.

Private source text and derived passages remain in approved ignored or external
storage. The result summary may commit sanitized aggregate evidence, hashes,
and synthetic examples only.

## Split and leakage rules

| Split | Size | Permitted use |
| --- | ---: | --- |
| Professor anchor | 12 | Rubric calibration, policy clarification, and schema correction; never a performance estimate |
| Development | 48 | Course-specific integration, prompt, threshold, and reviewer calibration |
| Held-out | 104 | One final frozen C0-C3 comparison after component and analysis freeze |

Do not create split variants by lightly paraphrasing the same base question.
Cases sharing a source may appear across splits only when their learning task,
required claims, and student situation are materially different. Record a
sealed-set access event. If held-out content leaks, mark the dataset/run
invalid, preserve the record, and create a versioned successor.

Record C4 full-context eligibility at dataset level only after measuring the
approved corpus with the frozen generator tokenizer and context limit. A
pending or ineligible C4 does not block the required C0-C3 evaluation.

## Annotation and adjudication

1. The primary annotator drafts the case and self-checks every evidence link.
2. A second reviewer independently labels expected action, claims, evidence,
   rubric applicability, and safety focus.
3. Differences receive stable disagreement IDs; do not overwrite the original
   labels silently.
4. The professor approves or revises the 12 anchors, especially course facts,
   misconceptions, assessed-work limits, and teaching moves.
5. After calibration, two reviewers independently label the frozen share of
   final responses. Human judgment remains authoritative for any dimension
   whose automated agreement is below the protocol threshold.

## Run-output boundary

Evaluation outputs are stored separately under ignored `reports/generated/`.
For every case and condition they must record:

- run, case, condition, dataset, corpus, policy, model, prompt, and code
  revision identifiers;
- exact retrieved passage IDs, ranks, scores, and context supplied;
- human returned-context label: complete, partial, or none;
- raw answer, atomic answer claims, citations, and policy action;
- per-dimension judgments, hard-gate results, reviewer identity, and
  adjudication;
- latency, tokens, cost, retries, errors, and failure category; and
- dirty state and invalidation reason when applicable.

The run-output schema and executable semantic validator are later evaluation-
tooling work. Creating them does not authorize provider calls or held-out
inspection.

## Definition of ready for professor review

- the JSON Schema and synthetic example validate;
- all 12 anchor slots have an explicit purpose and expected decision;
- every anchor uses synthetic placeholders until course permission exists;
- professor questions focus on content, policy, evidence, and allowed tutoring
  behavior rather than implementation; and
- no source ingestion, RAG implementation, provider call, or held-out record is
  created as part of this design step.
