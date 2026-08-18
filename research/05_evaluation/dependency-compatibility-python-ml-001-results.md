# Evaluation result: dependency-compatibility-python-ml-001

## Run identity

- Component: selected M2 retrieval ML dependency stack
- Status: completed; candidate gate failed
- Date and owner: 2026-08-18, researcher with Codex execution support
- Control code revision: `c5154e5d0fe211a7d0d400f37523c85e2c1af4fe`, clean
- Candidate code revision: `6b225802002d1ff5f0a7ddfc2776815ad5f58046`, clean
- Reproduction: the three commands in
  `research/04_experiments/2026-08-18-dependency-security-upgrade-plan.md`
- Runtime: Python 3.12.13 on macOS arm64 with local MPS execution
- Generated artifacts: ignored under
  `reports/generated/dependency-compatibility-{baseline,candidate,comparison}.json`
- Artifact SHA-256: baseline
  `4690a1742fa55ea37de3ea7761432d9b67b51895e410cc8385669ee193a3788d`,
  candidate
  `3af19f587929044eb5e1d3bb6cbcce21dc2f0197c15a519f870a43038539bced`,
  comparison
  `5e5f58e890d0a03c273eaecf7faeaa1147cfb7e13a0e6dcfcedc30dddfc480b8`

## Decision context

The decision was whether Torch 2.13.0, Transformers 5.15.0, and Sentence
Transformers 5.7.0 could replace the selected stack without altering selected
M2 retrieval behavior. The prediction was exact compatibility. The control
used Torch 2.9.1, Transformers 4.57.6, and Sentence Transformers 5.2.0.
FastEmbed 0.8.0, OpenCLIP 3.3.0, the frozen Qwen3 embedding revision, M2
configuration, dataset, machine, and Python version were held constant.

The prospectively declared decision rule required every gate to pass. In
particular, all 40 per-case top-three chunk lists had to remain identical; an
aggregate metric tie was not enough.

## Data and configuration

- Dataset: all 40 sealed cross-course retrieval development cases, SHA-256
  `e3749c3ee831dcf4c06f3b33cb94f21fe758eaec36e627d034715d4ca0cdd863`
- Corpus/profile: `cross-course-portfolio-v2` through `student-tutor-v1`
- Method: selected M2 BM25 plus Qwen3 dense reciprocal-rank fusion
- Embedding: `Qwen/Qwen3-Embedding-0.6B` revision
  `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`
- Trials: one index build followed by three query trials per stack
- Boundaries: zero held-out file reads, zero external provider calls, and no
  professor-fidelity data access
- Sample rationale: every available development case was used because exact
  compatibility, not population inference, was the decision question

## Results

| Metric | Control | Candidate | Gate | Result |
| --- | ---: | ---: | --- | --- |
| Complete evidence success@3 | 0.771429 | 0.771429 | No regression | Pass |
| Evidence recall@3 | 0.743590 | 0.743590 | No regression | Pass |
| nDCG@10 | 0.829053 | 0.829053 | No regression | Pass |
| MRR | 0.778571 | 0.778571 | No regression | Pass |
| Exact top-three lists | 40/40 control | 38/40 identical | 40/40 identical | **Fail** |
| Course-isolation violations | 0 | 0 | 0 | Pass |
| Median trial p95 latency | 95.990 ms | 70.641 ms | Candidate/control <= 1.20 | Pass |
| Held-out reads / external calls | 0 / 0 | 0 / 0 | 0 / 0 | Pass |

The candidate changed only the third-ranked chunk for
`ccr1-cs5421-02` and `ccr1-it5002-04`. Because the aggregate metrics rounded
to the same exact values, a metric-only check would have missed this behavioral
drift. The failure category is model/runtime ranking compatibility, not data,
policy, course isolation, or evaluator failure.

## Validity review

Both runs were made from clean commits on the same machine with the same
dataset hash, binding, model revision, and trial procedure. The analyzer
verified all 40 case IDs. No held-out or private professor-fidelity split was
read. The comparison is valid for the exact tested group; it does not isolate
which of the three upgraded packages caused the two rank changes.

## Decision

- Outcome: **Drop** the tested ML dependency group.
- Selected implementation: retain Torch 2.9.1, Transformers 4.57.6, and
  Sentence Transformers 5.2.0 for the optional local retrieval benchmark.
- Profile change: none; selected M2 remains unchanged.
- Retained upgrades: independently passing API, test, frontend, and build
  dependency upgrades remain in the candidate branch.
- Security handling: nine findings in the restored optional ML environment are
  explicit temporary compatibility exceptions, reviewed by 2026-09-15. CI
  fails on any unreviewed advisory or exact-policy drift.

## Limitations and follow-up

This run does not identify the individual package responsible and does not
justify a public deployment of the restored vulnerable optional environment.
The next dependency experiment should test the smallest patched Torch and
Transformers changes independently against the same frozen compatibility gate.
Until then, use only approved model artifacts and data in the local evaluation
runtime and do not expose it as a service.

## Learning note

Dependency upgrades can preserve aggregate retrieval scores while changing
individual rankings. Exact per-case comparison caught a compatibility change
that four aggregate metrics did not, so the rollback is evidence-based rather
than a preference for older packages.
