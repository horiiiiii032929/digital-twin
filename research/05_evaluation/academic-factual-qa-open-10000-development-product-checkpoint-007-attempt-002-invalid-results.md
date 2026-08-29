# Product checkpoint 007 — corrective attempt

Result ID: `academic-factual-qa-open-10000-development-product-checkpoint-007-attempt-002-invalid`

Decision: **Invalid reference / stop checkpoint 007**

The sole corrective execution completed all 500 candidate responses, all 100
paired control responses, deterministic scoring, 44 routine advisory calls, and
10 bounded critical reviews. It made 594 total provider calls, used zero product
retries, reported USD 1.13834545, and retained exact model identities. The
sealed 10,000-case split remained unopened and unauthorized.

Deterministic scoring produced a diagnostic `Refine`: candidate fully grounded
factual success was 4.5%, answerable action accuracy was 28.5%, boundary action
accuracy was 84%, canonical all-evidence@3 was 39.25%, Evidence Recall@5 was
44%, and three severe unsupported releases were recorded. Boundary safety on
the paired 100 cases was 100% for the candidate and 95% for the any-hit control,
but the paired supported-answer retention lower 95% bound was -6.25 percentage
points and failed the -3-point gate.

These rates are diagnostic, not a valid academic product estimate. The routine
GPT-5.4 nano audit reviewed 428 cases and flagged ten possible reference-truth
defects. The bounded GPT-5.4 review narrowed these to two. Direct source audit
confirmed both:

- `academic-open-dev2-0011-q4` asks which statements “connect spanning tree
  with the root tree.” The pinned STP passage does contain the two intended
  spans, but the question is malformed and does not define that relationship.
- `academic-open-dev2-0016-q2` asks only for “the point about wait state.” The
  pinned TCP source contains both `CLOSE_WAIT` and `TIME_WAIT`; the question
  does not identify which claim should be paraphrased, while the gold requires
  `CLOSE_WAIT`.

Both exact evidence spans exist and their hashes are valid, but the questions
do not uniquely support the required `answer` action. The preregistered
zero-reference-defect gate therefore invalidates this confirmation package.
The deterministic diagnostic result was not changed by model review.

Checkpoint 007 authority is revoked. The finite policy permits no further
harness correction or method successor against these 500 cases. Scaling to the
sealed 10,000 cases, T1 promotion, professor fidelity, and deployment remain
closed. The next decision must replace or independently validate the reference
question layer before another academic product evaluation.

## Durable generated evidence

- Candidate responses: 500, SHA-256 `512251a00dff66a676a801b48e51768afb2ca8ef325a4301be6c9e50b3a77727`
- Control responses: 100, SHA-256 `476e3ba4a35b351f4a7f4e8dae088fcc5c69abea1497dae7dfb800aff8a6d8a2`
- Candidate score: SHA-256 `1941ef0224a41c770dc50fd5c6f2f432a427b20998fba6e7422174dc896a8d20`
- Paired score: SHA-256 `540df6ae19619e55dddc9c86618561eb9c3bb045f5d3884e4415a876eae488e2`
- Advisory result: SHA-256 `24631bf96de7c51a89f5125aed04af2a1f876a56ee2d40cb8b42143a8bdb2e6e`
- Critical review result: SHA-256 `64abf8fdd2d717a4f8df03fcfc0e562b8786f734e7faa8c5f63190af0e3e06d9`
- Terminal state: SHA-256 `98190a891d13f7509e15eba4ae49b9ccefe8395874495ce29b227a91524148b8`

Raw responses and provider ledgers remain ignored. This result publishes only
aggregate metrics, hashes, and the two decision-relevant public-source cases.
