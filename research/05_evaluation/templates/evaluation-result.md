# Evaluation result: <result ID>

## Run identity

- Component:
- Status: completed / failed / inconclusive / invalid
- Date and owner:
- Code revision:
- Working tree clean or dirty:
- Reproduction command:
- Runtime and important dependency/model versions:
- Generated artifact path:
- Predecessor or superseding result:

## Decision context

- Decision question:
- Prediction recorded before the run:
- Control:
- Candidates:
- Metrics and thresholds chosen before the run:
- Hard gates:

## Data and sample size

- Dataset and version:
- Calibration, development, and held-out split:
- Corpus and version:
- Permission and sensitivity status:
- Total cases and cases per slice:
- Sample-size or uncertainty rationale:
- Exclusions:

## Exact configuration

Record every parameter needed to reproduce each candidate, including model or
provider version, prompt or policy version, seed, context size, and number of
repeated trials.

## Aggregate results

| Candidate | Metric | Value | Raw count | Uncertainty | Threshold | Pass |
| --- | --- | ---: | ---: | --- | ---: | --- |
| | | | | | | |

## Slice results

| Candidate | Slice | Cases | Primary metric | Important observation |
| --- | --- | ---: | ---: | --- |
| | | | | |

## Hard gates

| Candidate | Gate | Result | Raw count | Evidence |
| --- | --- | --- | ---: | --- |
| | | | | |

## Operational results

Record mean and tail latency, memory, model or index size, tokens, cost,
timeouts, cold start, and dependency burden when relevant.

## Failures and surprises

List representative case IDs, expected versus observed behavior, diagnosed
failure category, and whether the problem belongs to data, parsing, chunking,
query, ranking, model, policy, integration, evaluator, or operations.

## Validity review

- Calibration/test separation preserved:
- Metric or judge reliability:
- Data or judgment defects:
- Run invalidated: yes / no
- If invalid, reason and corrected successor:

## Decision

- Outcome: Keep / Refine / Go Deeper / Drop
- Selected implementation, if any:
- Profile change:
- Retained fallback:
- Rationale:

## Limitations and follow-up

- What this result does not establish:
- Required next dataset or experiment:
- Open risk or user/professor decision:

## Learning notes

Explain the algorithmic or evaluation lesson in language the student can use
to reproduce and defend the decision.
