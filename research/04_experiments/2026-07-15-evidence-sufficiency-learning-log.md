# Evidence-sufficiency learning log

## What I expected

I expected the any-hit control to fail vocabulary-sharing negatives and the
semantic agreement candidate to be the most promising. I also expected lexical
coverage and absolute BM25 score to have a visible precision/recall tradeoff.

## What happened

All three expectations were directionally correct, but the failure was much
stronger than the earlier six-case no-evidence slice suggested. Any-hit accepted
all 18 held-out negatives. Semantic agreement was best, yet still accepted five
negatives and refused eight of 32 answerable questions. Raw score and lexical
coverage rejected fewer unrelated questions while also losing valid ambiguous,
paraphrase, or permission-policy questions.

No candidate passed calibration, so none could be selected even if its held-out
numbers had looked favorable. I preserved that rule rather than tuning against
the test set.

## How the algorithms differ

- Any-hit asks only whether BM25 matched at least one token.
- Minimum raw score asks whether BM25's unnormalized sum of term weights is high
  enough. That score changes with query length and rarity; it is not a
  probability.
- Lexical coverage asks how much of the informative query vocabulary appears in
  the top evidence. A different-domain query can deliberately reuse many terms,
  while a good paraphrase can reuse few.
- Semantic agreement asks a second embedding retriever whether the query is
  close to some corpus passage. Embeddings improve conceptual matching but also
  map neighboring meanings close together, which creates open-set confusion.

## The metric trap

Conditional Recall@3 rose for every learned gate because each gate removed some
hard answerable cases from the denominator. That is selection bias, not a better
ranker. Unconditional Recall@3 and nDCG correctly counted abstained answerable
cases as failures. Evidence-gate evaluation must always show both views.

## What I would defend in a review

The result is not “embeddings are bad.” It is that one BGE-small threshold is
not a calibrated answerability classifier for this corpus. Ranking relevance,
semantic similarity, and sufficient evidence are distinct variables. A safe
system needs a labeled open-set decision boundary and must measure both false
answers and false abstentions.

## Next experiment

Compare a cross-encoder relevance verifier and a small calibrated answerability
classifier using BM25, dense, overlap, score-margin, and query/corpus features.
Use independent label review, more near-domain negatives, and a prospectively
appropriate latency budget. Keep the current candidates as controls and use a
new calibration and held-out version; never retune this run.
