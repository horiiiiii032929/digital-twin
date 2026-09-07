# Advisory semantic reviewer v2: calibration success, transfer failure

Decision: **Drop as a decision-bearing semantic scorer for these broad profiles**.
Retain raw outputs as diagnostic evidence only. Neither calibration success nor
its aggregate labels qualify tutor accuracy, pedagogy or a model ranking.

## Prospective design and execution

The [v2 execution plan](../04_experiments/2026-09-06-completion-semantic-review-v2-plan.md)
used32 new controls on four fictional source contexts, two shuffled repetitions,
then all88 frozen live005 responses only after the gate passed. Positive controls
include paraphrase, abstention and appropriate elicitation; negative controls
include unsupported additions, wrong versions and premature solutions. Current-turn
requirements are explicit. Gold/arm/old scores never entered reviewer payloads.

All64 calibration judgments satisfied their predeclared mandatory labels.
The runner then made88 product-review calls:87 valid judgments and one rejected
for quoting text with added curly quotation marks. Total152 calls, USD0.668908
reported cost, USD5.719504 conservatively reserved. No budget stop or retries.
The model was Terra/low/1500; store=false; only synthetic data left the machine.
Exact model, usage, latency and input/source/profile hashes are retained.

## Why these counts are not quality scores

An independent assistant inspected12 diagnostic outputs with their actual
question, prior turns, sources and saved approved profile. Two incumbent Socratic
answers revealed the core rule before any attempt but were accepted after adding
a generic invitation to try. A comparable ledger failure was correctly rejected.
Broad profiles also received inconsistent judgments about whether an explanation
must include a same-turn check question. Exact citation mappings were checked;
there is no namespace mismatch explaining these findings.

The raw counts are retained for audit: incumbent19 acceptable/22 defective/2
uncertain/1 missing; candidate21 acceptable/21 defective/2 uncertain. **Do not
interpret19/44 or21/44 as semantic accuracy or infer candidate superiority.**
A simple explicit-turn calibration did not establish reliability on ambiguous
multi-turn profile instructions. The twelve-case review is diagnostic and cannot
estimate an overall judge error rate either.

The [validity sidecar](completion-semantic-review-development-001-live-002-validity-review.json)
records all12 findings. The [machine record](records/completion-semantic-review-development-001-live-002.json)
retains the original summary separately from this post-run validity decision.
Raw outputs, frozen inputs, source snapshot and measurements remain at
`reports/generated/completion-semantic-review-development-001-live-002/`.

## Consequence

Do not use this judge to qualify the new v3 tutoring candidate or to manufacture
confidence through more calls. Preserve transparent contract checks and
per-case assistant findings; independent human semantic/profile review remains
necessary for stronger claims. This result repairs false assurance from the
evaluation process; it does not itself improve or validate teaching quality.
