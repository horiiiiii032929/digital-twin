# Natural course quality development baseline 001

## Decision

**Refine query-to-evidence adequacy.** All 16 development cases completed through
the final-profile production factory. Eleven of twelve answerable cases passed
the independent exact-span and citation check; three of four boundary cases
passed their action contract. No external model or injected client was called.
This is a deterministic development diagnostic, not live-model qualification.

## Configuration and data

Revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty working tree. The runner
selected BM25, the dominance-scoped v3 gate, the deterministic evidence-set
generator, and reactive T1-v2 through the production factory. An injected fake
semantic client prevented any external call but was never reached.

The fresh [packet](datasets/natural-course-quality-development-v1.json) contains
four authored source cards and three natural question forms per concept
(paraphrase, partial explanation, misconception), plus out-of-course,
missing-evidence, graded-work and private-data boundaries. Sources were installed
as a synthetic approved release, bypassing ingestion and browser workflows.
Source spans and labels are AI-authored and await researcher review; they are
not independently human-validated. No consumed confirmation gold was used.

## Measurement and failures

The independent scorer checks exact requested span coverage and source,
document, version, checksum, course, release and locator. This detects extractive
coverage and lineage; it does not grade arbitrary paraphrases, unsupported extra
text, or full semantic correctness. No population inference is warranted from
these 16 development cases.

| Measure | Result |
| --- | --- |
| Completed cases | 16/16 |
| Exact-span and citation diagnostic | 11/12 |
| Boundary action contract | 3/4 |
| Actual model/network and fake-client calls | 0 / 0 / 0 |
| Reported duration | 1.054 seconds |
| Model cost | USD 0 |

Two failures remain unchanged:

- `ncq-1-1`: a natural archived-file-change question returned no-evidence.
  Its persisted audit shows three retrieved hits but zero selected evidence.
  The source and question share only `bytes` under the gate's exact tokenizer;
  `archived`/`archival` and `changed`/`altered` do not match. The two-token minimum
  rejects the relevant source.
- `ncq-no-evidence`: a request for the checksum algorithm and output length
  received the general checksum source excerpt. The source specifies neither
  requested detail. Three topic terms admitted the source, and the final claim
  validator confirmed the excerpt's support, not its adequacy for the question.
  No algorithm was fabricated; the failure is answering without the requested
  specificity rather than hallucinating an algorithm.

The next candidate should separate semantic answerability from topical lexical
overlap, retain deterministic source-span/citation validation, and compare on
additional development cases before a fresh confirmation. Do not patch these
two question strings or change their labels to erase failures.

## Reproduction and evidence limitations

```sh
uv run python -m scripts.natural_course_quality_development --validate
uv run python -m scripts.natural_course_quality_development --output-dir <fresh-output-directory>
uv run pytest tests/test_natural_course_quality_development.py -q
```

Four focused tests passed. Per-case text, citations and latency are preserved in
`reports/generated/natural-course-quality-development-v1-contract-baseline-001/`.
The [machine record](records/natural-course-quality-development-v1-contract-baseline-001.json)
retains dataset and output hashes. Harness/profile/diff hashes were not captured
at execution; the dirty revision alone cannot reconstruct the exact source
state. Memory and an aggregate token ledger were not captured. No later hash is
presented as an execution snapshot.
