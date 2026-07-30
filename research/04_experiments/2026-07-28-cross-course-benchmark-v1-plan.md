# Cross-course retrieval benchmark v1 plan

Date: 2026-07-28

Status: completed; private draft 6 was researcher verified, second reviewed,
and sealed on 2026-07-30

## Decision question

Can a balanced, traceable 100-case benchmark be constructed from the selected
four-course corpus to compare M0 BM25, M1 dense, M2 hybrid, and M3
hybrid-plus-reranking under shared evidence and metrics?

## Dataset grain and allocation

One row is one student-style retrieval query with an expected action and zero
or more page-local gold evidence chunks.

| Slice | Total | Development | Held-out draft |
| --- | ---: | ---: | ---: |
| IT5002 answerable | 15 | 8 | 7 |
| CS5421 answerable | 15 | 8 | 7 |
| IT5100B answerable | 15 | 8 | 7 |
| IT5100E answerable | 15 | 8 | 7 |
| No-evidence | 15 | 3 | 12 |
| Cross-course confusion | 15 | 3 | 12 |
| Adversarial / integrity boundary | 10 | 2 | 8 |
| **Total** | **100** | **40** | **60** |

The held-out label is provisional during authoring. It becomes sealed only
after all cases pass researcher verification, at least 20 cases receive an
independent second review, file hashes are frozen, and sealed-access controls
are recorded. Retrieval candidates must not run against held-out cases before
that point.

## Authoring method

### Answerable and cross-course-confusion drafts

- Corpus: `cross-course-portfolio-v2`
- Chunker: selected
  `page-bounded-heading-paragraph-chunker@v1`, 1,200/160 characters
- Drafting model: local `gemma3:4b`, Ollama digest
  `a2af6cc3eb7f`, temperature 0, fixed per-case seed
- Prompt: `cross_course_benchmark_author_v1.prompt.md`
- Evidence contract: the model must return an exact supporting quote copied
  from the supplied candidate chunk
- Automated checks: exact quote containment, quote and chunk hashes, source
  manifest hash, page and chunk identity, unique query, slice allocation, and
  action/evidence consistency

The local model proposes wording only. It cannot approve a query, claim,
answerability label, visual sufficiency judgment, or gold evidence.

### Boundary drafts

- No-evidence drafts use course-adjacent and out-of-scope questions with no gold
  evidence. Researcher review must check the complete corpus rather than
  treating low lexical overlap as proof of absence.
- Adversarial drafts cover solution requests, hidden instructions, credentials,
  student data, cross-course access, citation fabrication, and forced answers.
- Cross-course-confusion drafts provide a target evidence chunk and a
  vocabulary-sharing distractor from another course.

## Review workflow

Every case starts as `machine_draft`.

1. Automated structural and evidence validation.
2. Researcher verifies all 100 query/action labels.
3. For every positive case, researcher verifies that the gold chunk completely
   supports the required claim without depending on handwriting or
   diagram-only spatial meaning.
4. For every no-evidence case, researcher searches the whole corpus and records
   why the question is unsupported.
5. At least 20 cases receive independent second review with disagreements
   adjudicated and recorded.
6. Rejected cases are replaced under a new dataset draft version.
7. Only then freeze development and sealed files plus SHA-256 hashes.

## Primary metrics and hard gates

Primary retrieval metrics:

- complete-evidence success@3;
- atomic-claim coverage@3;
- no-evidence accuracy; and
- course-isolation violations.

Diagnostics:

- Recall@1/3/5;
- nDCG@3;
- MRR;
- latency;
- cost; and
- data, parsing, layout, chunking, query, ranking, provider, and operational
  failure classifications.

Hard gates:

- 100/100 researcher-verified labels before freeze;
- at least 20/100 independently second-reviewed;
- 100% manifest/hash/page/chunk/quote integrity;
- zero prohibited, solution, answer-key, submission, student-data, credential,
  or secret evidence;
- zero diagram-only or handwriting-only text gold;
- exact development/held-out allocation;
- zero retrieval access to the sealed file before the one-time run; and
- zero cross-course or permission violations for any selectable method.

## Validity risks

- A local LLM can create plausible but unsupported questions.
- A single page can contain multiple concepts or visual-only relationships.
- Negative questions are harder to validate than positive questions.
- Shared templates can make cross-course confusion artificial.
- Model-generated wording can favor dense retrieval.

Mitigations are exact-quote checks, balanced lexical/paraphrase wording,
researcher verification, independent second review, explicit visual sufficiency,
whole-corpus negative searches, and reporting results by slice and course.

## Stop rule

Do not freeze or run M0-M3 if any case remains machine-only, evidence integrity
fails, the second-review quota is unmet, or the held-out access ledger is
missing.
