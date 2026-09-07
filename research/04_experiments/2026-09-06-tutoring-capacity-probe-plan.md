# Tutoring capacity measurement

Decision: can the integrated candidate serve concurrent active students within
its declared latency/error target? Previous course-list timing does not answer
this question. Prediction: model latency and state-write contention dominate
full response latency; measuring only a read endpoint understates these costs.

The reusable probe sends actual message POST requests through independently
authenticated student clients. Each student's turns are sequential; students
run concurrently. Record every request outcome, end-to-end duration, observed
client concurrency, HTTP errors, schema failures and citation course/release
mismatches. Credentials and response text are not written by the probe.

Contract tests inject an HTTP transport and do not establish capacity. A live
qualification must supply clients on the same accepted deployment and record
revision, effective profile, hardware, duration, warm-up and model call ledger.
The first proposed qualification is 25 students x 4 measured turns, following
separate warm-up. Report the latency distribution and uncertainty limitations:
100 requests and four turns per student are a short burst, not sustained 24/7
operation or an independently powered failure-rate estimate. Do not count a
refusal or abstention as quality success merely because HTTP returned200.

Incumbent/candidate comparisons use identical predeclared student messages,
student count and turn count. Do not send private dialogue or change a running
user session; use isolated synthetic accounts. Provider and deployment execution
remain owned by the named qualified runner, not this reusable helper.
