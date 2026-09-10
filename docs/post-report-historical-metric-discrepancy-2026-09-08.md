# Historical factual score discrepancy

Read-only audit on 2026-09-08, inventory F03. The historical record
`research/05_evaluation/records/academic-factual-qa-open-10000-winner-regression-001.json`
reports 1,669 answers among 10,000 cases, 8,000 answerable cases and a fully
grounded factual success value of 0.2538.

The current scoring definition in
`src/digital_twin/evaluation/factual_qa_scoring.py` requires an answerable,
action-correct response for fully grounded success, and averages this measure
over answerable cases. Under that definition even treating every one of the
1,669 answers as fully grounded gives an upper bound of 1,669 / 8,000 =
0.208625. Thus 0.2538 cannot be reconciled with the reported action counts under
the current definition.

This identifies a discrepancy, not its historical cause. The original generated
response ledger was not found in this workspace during this audit; the original
run revision and scorer must be recovered and checked before correction.
**0.208625 is an upper bound, not a corrected score.** No hidden gold was read,
no sealed evaluation was rerun, and no historical value or submitted report was
modified. Exclude the disputed percentage from new presentation claims until
resolved. The original No Release decision is retained; this audit does not
requalify the method.
