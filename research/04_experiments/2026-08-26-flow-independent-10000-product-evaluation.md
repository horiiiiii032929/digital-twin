# Flow-independent 10,000-question product evaluation

Date: 2026-08-26

Owner issue: [#127](https://github.com/horiiiiii032929/digital-twin/issues/127)
Instrument: `academic-factual-qa-open-10000-v1`

## Decision question

Can the selected T0 Digital Twin retrieve, answer, cite, and abstain over a
large open-source workload when it receives only the course identifier and
question, and can the same benchmark compare a later T1/T2 graph or deployed
HTTP flow without rebuilding its reference data?

This supersedes reviewer calibration as the immediate #127 blocker. The prior
10,000-row result remains engineering evidence because those rows did not test
independent product retrieval and answer generation.

## Stable boundary

The public case package contains only case, cluster, source-family, course,
question, split, slice, and author-family identifiers. Hidden gold contains the
expected action, exact source spans, atomic claims, boundary reason, and
canonical source coordinates. A versioned adapter maps T0, T1/T2, HTTP, and the
any-hit control into the same observable action, answer, claim, citation,
retrieval, operational, latency, token, and cost schema.

Runtime chunk IDs, prompts, UI routes, graph nodes, and internal traces are not
gold. A changed product flow receives a new system-under-test manifest; it does
not require a new benchmark. After results influence development, later runs
are labelled known-benchmark comparisons, and a new sealed tranche is required
for a fresh confirmatory claim.

## Dataset and authorship

The prospective dataset contains 100 development and 2,000 final source
clusters. Each contributes four answerable questions and one boundary question,
for 500 development and 10,000 untouched final cases. Deterministic code derives
canonical answers, claims, actions, and exact source ranges before any provider
call. DeepSeek V4 Flash and Gemini 3.7 Flash alternate question wording; the
other family independently answers and classifies each question without seeing
the author's answer. Neither model can modify gold. Acceptance requires
verifier agreement with deterministic truth, valid source hashes, licences,
source coordinates, unique wording, and no private data.

The source scan identified a preregistration correction before data creation:

- the requested 1,075 development-plus-final networking clusters exceed the
  theoretical five-per-section maximum of 495;
- the requested 425 data-structures clusters exceed its theoretical maximum of
  400;
- no dataset has been written and no acceptance threshold has been lowered;
- the first feasible recommendation was corrected before provider execution
  because it counted tiny markup/import fragments and mid-token cuts;
- AFQC-035 requires token-aligned windows of at least 100 characters and four
  tokens, producing 396 operating-systems, 450 networking, 350 data-structures,
  and 904 Python clusters including 25 development clusters per course.

The recommendation yields exactly 2,100 non-overlapping source windows and has
enough source-matched windows for 735 code, 256 equation, and 53 table clusters
across development and final splits. AFQC-035 freezes this allocation while
retaining the source-diversity cap. AFQC-036 separately authorized only the
construction and development checkpoint. Attempt 001 then failed closed on the
first DeepSeek canary because its runtime fingerprint differed from the frozen
binding; AFQC-037 revokes that authority. The final split remains sealed.

## Product comparison

The candidate is selected hybrid BM25 plus Qwen3 retrieval, structured evidence
coverage, the two-boundary policy, atomic-claim generation/validation, the
strict grounded prompt, and DeepSeek V4 Flash. The any-hit control uses the same
corpus, retriever, generator, decoding, and policy. Development executes 500
candidate cases and 100 paired controls. Final execution uses all 10,000
candidate cases and a frozen 1,000-case/200-cluster control subset.

Response execution and scoring are separate processes. The response process
cannot load the hidden-gold path. It persists every response in an exclusive,
resume-bound SQLite ledger before the scoring process may open gold.

## Metrics and decisions

Primary outcomes are fully grounded factual success, boundary safety, and
overall grounded task success. Diagnostics include action accuracy, atomic-claim
precision/recall, citation precision/recall/completeness/version validity,
canonical source-range evidence coverage at 3 and recall at 5, course/source/
question/author/flow slices, provider completion, malformed responses, latency,
tokens, cost, persistence, and duplicates.

Uncertainty uses 10,000 seeded hierarchical bootstrap replicates over original
source families. Case-level micro-rates are descriptive and are not interpreted
as 10,000 independent observations. The complete hard gates are frozen in the
instrument. A valid failure is published as `completed-refine`; leakage,
identity, accounting, or harness failure is `invalid-execution`; all gates are
required for `completed-keep`.

## Stop points

1. Freeze and separately authorize a prospective provider-identity correction,
   then execute dataset construction plus the 500-case development run against
   the unchanged AFQC-035 allocation.
2. Review the development result and projected cost. Only a complete pass can
   request separate authorization for the sealed 10,000-case run.
3. Do not tune and rerun against the same final set after a valid quality
   failure.

True visual evidence, Professor Digital Twin fidelity, autonomous pedagogical
quality, deployment, and student usability remain separate evaluations.
