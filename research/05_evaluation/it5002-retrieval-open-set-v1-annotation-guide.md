# IT5002 retrieval open-set v1 annotation guide

Date: 2026-07-23

Status: schema and synthetic example frozen; private development and held-out
records are pending

## Purpose

`it5002-retrieval-open-set-v1` measures whether a retriever or returned-context
threshold mistakes topically similar material for sufficient course evidence.
Every case is expected to abstain. It supplements, but never replaces, the
answerable and policy cases in `course-tutor-v1`.

The development split contains 24 cases. The held-out split contains 52 cases.
These counts were selected to materially strengthen the small no-evidence slice
in the final course benchmark while keeping researcher adjudication feasible.
Even zero held-out failures would support only a bounded failure-rate statement,
not proof of zero deployment risk.

## Categories

| Category | Construction rule | Primary failure |
| --- | --- | --- |
| `near_domain_absent` | Ask about a nearby computing concept not taught in the approved corpus | Dense semantic overreach |
| `vocabulary_collision` | Reuse important course words in a different domain | Sparse lexical overreach |
| `plausible_non_course` | Ask a realistic student question whose answer is absent | Product overconfidence |
| `unsupported_precision` | Ask for a value, exception, deadline, or rule more specific than the evidence | Partial-evidence overclaim |
| `prohibited_trap` | Provide a tempting exact match that permission filtering must exclude | Permission leakage |
| `superseded_trap` | Provide a tempting exact match from an inactive version | Version leakage |

Each split should cover every category. No category should supply more than one
third of a split.

## Unit and gold label

One case contains:

- one frozen query;
- a case-family identifier used for split-leakage checks;
- one primary category;
- course-topic affinities that explain why retrieval may be tempted;
- zero or more tempting passages, stored by identity and hash;
- a rationale explaining why no eligible evidence is sufficient; and
- annotation and review history.

`expected_action` is always `abstain`. An approved passage may be listed as
`approved_but_insufficient`; approved does not mean that it answers this
question. Prohibited and superseded passages are always negative evidence.

## Authoring workflow

1. Start from the frozen corpus and write a plausible query without inspecting
   candidate retrieval output.
2. Search the entire eligible active corpus manually.
3. Confirm that no passage or combination of passages supports the requested
   answer at the requested precision.
4. Record any tempting approved-but-insufficient, prohibited, or superseded
   passage by stable identity, locator, and SHA-256.
5. Explain the insufficiency in one inspectable rationale.
6. Assign a case family before the split. Families and paraphrases cannot cross
   development and held-out files.
7. Obtain independent review of answerability, category, and tempting evidence.
8. Resolve disagreements before sealing.

LLMs may propose candidate queries, but a researcher must verify every absence
claim against the corpus. `llm_candidate_researcher_verified` records that
lineage. An LLM assertion that the answer is absent is never sufficient.

## Leakage and quality rules

- Normalized questions and case families are unique across splits.
- Light paraphrases remain in the same family and split.
- Held-out query text, rationales, and tempting evidence are not inspected
  during candidate or threshold selection.
- Every passage identity and hash resolves against the frozen source revision.
- Private query and passage text remains under ignored local storage.
- Direct identifiers, student records, grades, forum posts, and assessment
  answers are prohibited.
- A held-out access event is recorded before the one allowed evaluation.

## Analysis boundary

Report:

- no-evidence accuracy with raw numerator, denominator, and Wilson 95% interval;
- answerability precision when combined with answerable course cases;
- false-answer count by category;
- the highest-scoring false positives;
- threshold-versus-coverage behavior;
- permission and version violations separately; and
- retrieval, threshold, and annotation failure causes separately.

Do not combine no-evidence cases with MRR, Recall@K, or nDCG denominators.
