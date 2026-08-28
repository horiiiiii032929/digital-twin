# Open 10,000 factual-QA development checkpoint 004

Result ID:
`academic-factual-qa-open-10000-development-checkpoint-004-wording-refine`

Decision: **Refine / stop before product execution**

Checkpoint 004 started from clean authorization revision `76796f0`. The
question-wording stage completed all 50 planned calls: 25 exact
`gpt-5.4-mini-2026-03-17` generation calls and 25 exact
`gpt-5.4-2026-03-05` reviews. All calls used the direct OpenAI Responses API,
`store: false`, zero retries, and the expected model identity.

The stage accepted 452 of 500 model-written questions (90.4%), below the
preregistered 95% gate. The independent configuration-level reviewer rate was
also 90.4%, which met its separate 90% minimum. Canonical fallback remained
available for all 48 rejected variants. There were zero normalized duplicates,
zero canonical-answer leaks, zero malformed responses, and zero identity drift.

## Failure diagnosis

Of the 48 fallbacks:

- 47 were explicit reviewer rejections;
- 46 of those were labelled meaning shifts, including seven also labelled
  awkward;
- one preserved meaning but was rejected because it still requested a
  submission-ready graded answer;
- one additional review returned `accept: true` together with
  `faithfulness: meaning-shift`; the deterministic invariant rejected that
  inconsistent vote and used the canonical fallback.

Fallbacks were distributed across 14 cross-course, 10
definition/explanation, eight paraphrased, five multi-evidence, five ambiguity,
four academic-integrity, one direct-factual, and one structured-equation case.
Operational inspection found that several rejections arose when a model tried
to repair awkward canonical fragments—for example, `concerns` versus `is
about`—and the reviewer treated that repair as a meaning shift. This diagnosis
does not override the frozen gate or convert the result into a pass.

## Accounting and boundaries

- Provider calls: 50/50 completed.
- Input tokens: 61,974.
- Output tokens: 41,705.
- Reported cost: USD 0.555499.
- Aggregate provider latency: 345.361 seconds.
- Generator latency: p50 3.599 seconds; p95 5.682 seconds.
- Reviewer latency: p50 7.361 seconds; p95 8.711 seconds.
- Retries, recovered failures, private-data calls, and final-set calls: zero.

The run stopped before runtime-package materialization, candidate T0 execution,
the paired control, deterministic product scoring, and post-score advisory
audit. Hidden development gold was not opened for scoring, and the untouched
10,000-case final set remained closed. This result therefore evaluates the
wording stage only; it is not evidence that the T0 product passed or failed.

The ignored ledger is
`reports/generated/academic-factual-qa-open-10000-wording-development-004.sqlite3`
with SHA-256
`437dadae508205fdba4e1277040a5748ec29dcf90c76da8f916199a135b26263`.
The ignored wording result has SHA-256
`864664af671bdb0881cb0ea60f72f7821d1b9488a112307dcc41191df323c436`;
the terminal checkpoint state has SHA-256
`9d8e35bc39cfd4c400d4563d15c98245bfc71ceceaf8e5761cf83bf9f00ebf48`.

All checkpoint-004 authority is revoked. The recommended method-level
successor is to preserve this immutable 452-model/48-canonical mixed wording
package, treat canonical fallback as an explicit dataset composition rather
than a product-quality failure, and run no new wording calls. That successor
must be frozen prospectively and receive separate authority before any T0
product call. The current `Refine` result remains unchanged.
