# Independent reference-question validation 003

## Outcome

`completed-refine`. The execution was operationally valid, but the one-question-
per-target method did not produce enough complete clusters for product evaluation.

## Result

- 80/80 direct OpenAI calls completed with zero failures or retries.
- 448/800 individual questions passed every blind recovery and deterministic check.
- Only 8/160 clusters had all five questions pass; 100 were required.
- The eight eligible clusters yielded 40/500 selected cases.
- Seven normalized duplicate question groups were detected.
- Reported cost was USD 1.4173615; total provider latency was 550.178 seconds.

Failure reasons are overlapping: 234 answer-span mismatches, 89 unnatural
questions, 86 action mismatches, 38 ambiguous questions, 24 gold-hint leaks,
and 22 duplicate-question findings. Boundary wording was especially weak:
30/160 boundary questions passed, compared with 418/640 answerable questions.

## Interpretation

This is a valid method failure, not an OpenAI transport or harness failure. Exact
response IDs, model identities, token/cost accounting, and the complete call
sequence remained stable. The result shows that one generated question per target
is too brittle when complete five-question clusters are required.

The finite successor changes the method once: generate three distinct candidates
for each answerable target, independently recover the answer from the source, and
select the first valid unique wording. Versioned deterministic templates own the
boundary probes so a wording model cannot mutate policy truth. No final question,
product response, private source, or sealed 10,000-case gold was opened here.

## Limitations

- Both model roles are different OpenAI configurations, not independent provider
  families or external human annotation.
- Exact answer-span recovery is deliberately strict and may reject semantically
  equivalent answers; it is used here to protect source-linked ground truth.
- The ignored provider ledger remains local. Only aggregate metrics and hashes are
  committed.
