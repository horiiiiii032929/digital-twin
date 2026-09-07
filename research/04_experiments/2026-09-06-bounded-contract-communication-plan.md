# Bounded contract communication v3

Instrument: `bounded-contract-progression-development-001`.

## Confirmed defect and comparison

The preserved output-cap run found one local count-limit failure at500 tokens
and seven at1500. The provider-visible strict schema intentionally drops
maxItems, while the v2 prompt did not disclose the locally enforced four-aspect
and two-spans-per-aspect limits. This is request/validator misalignment.

Retain v2 as control. Candidate v3 explicitly supplies shared parser limits and
instructs the model to group related requested details only when every detail
can remain supported. If the question cannot be represented without omission,
request clarification rather than silently dropping requirements. Missing
course evidence remains insufficient, not a representation excuse. Retain all
local count bounds, exact spans, citation authority, boundary checks and
nonempty-answerability requirements. Do not raise limits or truncate proposals.

## Finite development evaluation

Compare v2 and v3 at the same1500 output-token cap. Use three order/repetition
seeds (7401,7402,7403), six situations, two fixed student turns each, and both
versions:36 trajectories/72 student turns. Three situations derive from the
consumed cap-development failure classes (multipart, topic reset, no-attempt);
three new situations request five related details, nine separately structured
details without grouping, and a mix of supported/absent numeric specifics.
All current turns use actual production tutoring services and actual provider
calls. Student stimuli/source/profile match across versions; later actual tutor
history may diverge. Restart before the second turn to retain continuity coverage.
Seeds identify repetition/order only, not provider randomness. This is fresh
named development evidence, not new held-out confirmation.

Measure count-limit/truncation/other model failures, delivered guarded failures,
all requested content retained versus omitted (independent review), clarification
for unrepresentable requests, missing-evidence boundaries, source lineage,
profile continuation, exact model/configuration hashes, tokens/cost/latency and
per-situation/repetition results. Initial-message bodies intentionally differ by
the v3 contract addition; no claim of identical provider prompts across versions.

Maximum240 total calls/$4.80 conservative reservations (.02/call), four isolated
histories concurrently,1500 output tokens,30-second timeout, no retries. The
selected release and500-token default remain unchanged. Concurrent advisory
provider traffic is recorded; latency remains descriptive. Preserve unfavorable
results and do not infer semantic correctness from schema validity.
