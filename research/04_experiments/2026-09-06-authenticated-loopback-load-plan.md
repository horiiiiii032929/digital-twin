# Authenticated loopback load development plan

Instrument: `authenticated-loopback-load-development-001`.

Decision: does the explicitly selected development candidate meet the unchanged
15-second end-to-end request-p95 gate with real authenticated network requests at
five versus25 burst clients? This remedies the missing sockets/authenticated-load
boundary in the earlier in-process G6 comparison; it is not public deployment.

Use a fresh, single-process Uvicorn server bound only to a newly allocated loopback
port. Staging requires secure cookies, so issue a task-local self-signed certificate
trusted only by the evaluation client. Do not install certificates or alter the
user's services, ports or Docker. Bootstrap synthetic accounts and a mixed
PDF/transcript/anonymized-forum course through the same application services;
policy onboarding is disclosed fixture setup, while profile/domain/source approval
and publication use actual APIs and queued ingestion. Actual credentials, session
cookies and Origin checks remain enabled; synthetic identity headers must fail.

The fixed workload is two answerable source questions per student, on independent
fresh conversations. Three repetitions of each burst size5 and25 produce180 planned
POSTs. Fix order to5,25,25,5,5,25 before execution. Clients in each group start their
first turn together and issue the second only after their own first completes.
This is a finite closed-loop burst comparison, not an open arrival-rate or
sustained saturation model. Do not add favorable repeats or tune the question set.

Use the final explicit v2/v3 development configuration after the pending bounded
contract comparison, record that choice before dispatch, and retain profile/control
boundaries. Provider concurrency is explicitly five; maximum300 actual calls,
USD10 global reservation cap,1500 output tokens,30-second provider timeout,
120-second request timeout and600-second load deadline. Expected call count270 is
an estimate, not a reason to relax caps. Preserve every incomplete/failing request.

Hard gates per repetition: p95 of all observed request latencies at most15seconds;
all planned requests complete with expected conversation/course/release lineage;
zero HTTP errors; no no-evidence or safe-failure action on the fixed answerable
packet; expected durable messages; actual provider identity matches configuration;
all source hashes unchanged. Questions are counted separately as non-answer
behavior, not silently scored as correct. Passing operational gates cannot establish
semantic accuracy, professor fidelity or learning benefit.

Record entire synthetic responses, per-request attribution, burst/order, all-call
and provider latency, actual model overlap, budget-plus-ledger admission wait,
server process RSS samples, saved messages, tokens/cost/reservations and co-resident
process names. Admission wait is measured non-invasively around the unchanged
budget call and transport admission; it includes serialization/ledger overhead and
is not pure semaphore time. Record cold/warm order and no confidence interval from
three dependent repetitions. Keep the15-second gate even if the run fails it.

One injected-provider network contract run precedes live dispatch. Its timings are
not combined with live metrics. Failures remain registered. A measured fail leads
to Refine, not deletion, threshold relaxation or a claim of infinite scale.


Before live dispatch, select explicit v3 via
`bounded_generation_contract_enabled=True`, with the existing question-specific
and approved-profile flags and1500-token output cap. The completed v2/v3 comparison
supports schema-contract consistency only; pedagogical Refine and default v2 remain.
The first network contract exposed Uvicorn's final SIGTERM re-raise: requests and
persistence passed but the enclosing provider-summary cleanup did not run. Preserve
that attempt as incomplete evidence, and require clean child exit plus the complete
provider summary in the corrected runner. The fixed packet's contract exercised one
provider call per turn (four calls for four POSTs), so180 live calls are plausible;
the prospective300-call hard cap is unchanged.
