# Output cap and dialogue progression development

Instrument: `output-cap-progression-development-001`.

## Decision and prediction

The prior 24-history operating run contained11 incomplete provider responses
at the configured500 output-token cap, including reasoning-token exhaustion.
Compare500 (unchanged default/control) with1500 output tokens at the same Luna
model and low reasoning effort. Prediction:1500 reduces incomplete responses
and their delivered failure states, at potentially higher latency/cost. A larger
cap need not improve teaching behavior or override profile/source boundaries.
No default or selected profile changes before evidence review.

## Dataset and comparison

Eight newly authored synthetic dialogue situations, four student turns each:
correct attempt, incorrect attempt, explicit no-attempt, explanatory multipart
specifics, topic switch, never-direct-answer profile, missing course specifics,
and private-data/boundary context. Four fictional protocol cards form a fresh
source fixture. Run all eight situations under both caps for each of three
predeclared order/repetition seeds (7301,7302,7303):48 trajectories and192 current
student turns, all through actual production tutoring services. Each trajectory
restarts before its last turn. Fixture setup is explicit and does not prove
material ingestion or deployed authentication.

Student stimuli, profiles and sources are matched across caps. Actual tutor
outputs are retained and feed later turns, so later prompts can diverge between
arms. Initial requests provide a paired cap comparison where their serialized
message bodies match; compare request digests excluding only the output-cap
setting. Seeds randomize scheduling order and identify repeat runs; they are
not provider random seeds and do not create independent source families.
This is development on synthetic material, not held-out quality confirmation.

## Metrics and failures

Report all model task attempts, valid/completed/incomplete/error outcomes,
requested/returned identity, output/input tokens, cost, provider latency,
wall time, user-visible answer/question/boundary/failure fractions, restart
identity, source/citation lineage violations, paired first-request equality,
and per-situation/per-repeat slices. Report repeated generic elicitation and
profile progression as review questions, not automatically scored learning.
Preserve every output and failure. Distinguish output-limit failure from schema,
focus/span validation, retrieval, policy, and operational causes.

No factual accuracy or professor-fidelity pass is inferred from exact spans,
model-schema validity or action counts. Semantic review and uncertainty must
respect source/trajectory clustering;192 correlated turns are not192 independent
students. Retain the earlier failed500-token evidence and both new arms.

## Finite execution

Maximum500 external calls and$10 total conservative reservations, four isolated
trajectories concurrent,30-second per-call timeout, no provider retries. Each
arm has its own truthful serializer/output cap and per-call .02 reservation;
the total nominal reservation ceiling is$10. Two250-call arm caps jointly prevent
aggregate overflow beyond500 calls. Output directories are exclusive. Record exact code/profile
hashes and their unchanged state at completion. Stop dispatch on ledger-budget
failure or fatal infrastructure failure, not merely an unfavorable quality
result. Source and provider defaults remain unchanged.

The parent task may execute an advisory provider review concurrently. Record
that co-resident workload; timing results are descriptive, not an isolated
causal performance comparison.
