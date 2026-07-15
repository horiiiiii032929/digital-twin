# Retrieval evidence-sufficiency v1 experiment

## Decision question

Can an explicit gate stop weak vocabulary-sharing out-of-domain retrieval from
reaching generation without refusing too many answerable course questions or
hiding ranking failures?

## Prediction

- The current any-hit control will preserve answerable recall but fail
  no-evidence behavior on vocabulary-sharing negatives.
- An absolute BM25 raw-score gate will remain brittle because several
  out-of-domain queries contain rare corpus terms.
- Lexical coverage should improve abstention but will trade off against
  paraphrased and ambiguous answerable questions.
- Independent BGE-small semantic agreement should have the best balance, but
  may still confuse nearby technical domains or reject multi-evidence queries.

## Candidates

1. `any-hit-evidence-gate`, the explicit current-behavior control.
2. `minimum-raw-score-evidence-gate`, with its BM25 cutoff selected on
   calibration only.
3. `lexical-coverage-evidence-gate`, with query coverage and minimum matching
   terms selected on calibration only.
4. `secondary-retriever-agreement-gate`, using local
   `BAAI/bge-small-en-v1.5` and optionally requiring source agreement with BM25.

BM25 v1 (`k1=1.2`, `b=0.75`) remains the ranker for every condition so this
experiment isolates the evidence-sufficiency decision. The semantic candidate
does not replace returned BM25 evidence; it independently decides whether that
evidence may proceed.

## Data and separation

- Corpus: unchanged 40-chunk `synthetic-web-security-v2` corpus.
- Calibration: 30 new cases, including 12 vocabulary-sharing no-evidence
  questions. It is used only to select each candidate's configuration.
- Held-out: 50 new frozen cases: 32 answerable and 18 no-evidence questions
  across exact, paraphrase, multi-evidence, distractor, ambiguous,
  permission/version, and vocabulary-sharing out-of-domain slices.
- Retrieval v2 held-out outcomes motivated this experiment but are not reused
  for threshold fitting.
- All committed content is synthetic; no private course or student data is used.

## Metrics and hard gates

Primary answerability metrics are answerable recall, no-evidence accuracy,
balanced accuracy, false-answer count, and false-abstention count. Unconditional
Recall@3 and nDCG@3 remain visible so abstention cannot hide ranking losses;
conditional versions are diagnostic only.

A selectable candidate must:

- pass calibration with zero false answers, answerable recall at least 0.90,
  and zero permission/version violations;
- produce zero held-out false answers and no-evidence accuracy 1.00;
- retain held-out answerable recall at least 0.90 and balanced accuracy at
  least 0.95;
- preserve at least 95% of the any-hit control's unconditional Recall@3 and
  nDCG@3; and
- add no more than 1 ms mean gate latency, excluding primary BM25 retrieval.

Calibration failure remains a held-out hard-gate failure even if the frozen
candidate happens to perform well on the test set. No threshold or case is
changed after the first held-out run.

## Reproduction

```bash
npm run calibrate:evidence-sufficiency
npm run benchmark:evidence-sufficiency
```

The full per-case artifact is written to ignored
`reports/generated/evidence-sufficiency-v1.json`. Every candidate, including a
failed or inconclusive one, remains visible in the durable result summary and
machine record.
