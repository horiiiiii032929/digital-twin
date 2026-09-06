# In-process tutoring concurrency development plan

Instrument: `final-profile-asgi-tutoring-concurrency-development-001`.

Decision: can the current candidate handle 25 simultaneous synthetic student
conversations, four sequential turns each, without request, model identity or
citation-scope failures? Baseline is the existing network-free ASGI contract;
candidate is the final-profile factory with approved explanatory profile context
and question-specific generation enabled. No replacement is selected by this run.

The test uses one actual factory-built tutoring service and SQLite runtime,
mounted through the existing student router. Identity is a synthetic account
header injected at the route dependency; real service authority checks remain.
It excludes production authentication middleware, sockets, Docker, TLS, distributed
workers and real students. Thus this is not deployed capacity qualification.

Data: fixed fresh synthetic protocol facts and four messages, repeated across
25 independent students to measure operational contention, not population quality.
Network-free contract smoke starts with two students and two turns; live execution
requires explicit instrument authorization, finite 500-call/USD5 default caps,
exclusive output and unchanged runtime source hashes from start to finish.

Hard gates: 100/100 planned POSTs complete the nonempty-response/conversation and
citation-scope contract; zero failed provider calls or model identity mismatch;
all25 students exercise the provider; source hashes unchanged. Record p50/p95,
request failures, tasks/calls/usage/cost, maximum concurrent client requests,
actual delivered responses, citations and retained conversation lengths. No fixed
latency acceptance target is invented before deployment requirements exist.

Model/provider failures and missing evidence are retained; boundary/fallback
responses are not treated as semantically correct answers. Quality remains
unscored and requires independent review. If the source changes or coverage is
missing, mark invalid/incomplete; if contract gates fail, refine. Passing permits
only Go Deeper to the deployed/load/quality gates, never release qualification.

## Pre-live contention finding and correction

The initial two-student contract exposed a real operational failure: synchronous
SQLite turn writes waited for an asynchronous checkpoint writer on the same event
loop, preventing that writer from completing its commit. Two of four requests
failed with database-lock errors. This was an integration defect, not evidence of
provider quality or deployed capacity.

The corrected turn commit uses immediate SQLite busy failure followed by bounded
asynchronous retries of only the short atomic persistence transaction. Every
attempt rolls back before yielding, restores the connection's busy timeout, and
rechecks durable authority. Model generation is not retried. Deadline exhaustion
maps to the retryable `turn_storage_busy` HTTP503 outcome.

Regression coverage uses a genuine AsyncSqliteSaver held at commit: normal release,
authorization revocation, deadline exhaustion and two duplicate requests waiting
for the same checkpoint. The duplicate contenders must converge on one persisted
turn without regeneration during storage retry. Both 2-by-2 and 25-by-4 actual
shared-runtime ASGI contracts pass with an injected provider; that provider's
malformed outputs deliberately exercise fallback and establish no answer quality.

## Prospective bounded provider concurrency comparison

After live baseline `final-profile-asgi-tutoring-concurrency-development-20260906-001`
showed provider peak concurrency one and request p95 148.576 seconds, compare an
explicit maximum of five concurrent provider requests against that retained serial
control. Keep serial as the default. Prediction: five admitted calls reduce queued
request latency while preserving all 100 request, identity, lineage and persistence
contracts. Reuse the fixed synthetic operational workload; this is not held-out
quality evaluation. Do not tune answers or suppress unfavorable attempts.

Only clients exposing a conservative request-cost ceiling can overlap. The known
OpenAI transport bounds serialized UTF-8 input at 20,000 bytes, reserves one token
per byte plus 4,096 framing tokens and its configured maximum output tokens using
configured catalog prices. Admission atomically counts completed charged cost,
uncertain retained reservations, all in-flight reservations, and the new ceiling.
Call-count and concurrency caps also apply. Unknown-cost clients remain serial;
unknown usage or cancellation retains the admitted reservation and blocks future
admissions. A reported cost above its ceiling invalidates the bound and closes
further admissions. Existing admitted work remains accounted for.

Tests must prove overlap at the cap, finite call/dollar admission under contention,
oversized-input rejection, known-cost reconciliation, cancellation before and after
admission, missing usage, a broken ceiling, and serial fallback. Live candidate
25-by-4 uses maximum 500 calls/USD5, exclusive outputs and unchanged source hashes.
Record provider and client peak concurrency, all response actions and failures,
latency, usage/cost and co-resident work. A successful load contract remains separate
from teaching quality, real deployment and release-profile selection.
