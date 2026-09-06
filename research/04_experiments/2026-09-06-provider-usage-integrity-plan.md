# Missing provider usage must remain unknown

Prospective repair, program `provider-usage-integrity-development-001`.
The current OpenAI response parser substitutes zero when the `usage` object or
an input/output token field is missing. The surrounding budget correctly stops
unknown-cost calls, but cannot do so when the transport converts missing data
into an apparently known zero. This threatens budget and operational-measurement
integrity even though the observed successful provider runs returned usage.

Prediction/control: the current parser accepts missing usage or individual
missing counts as zero. Candidate: reject absence, preserve explicit nonnegative
integer zero, keep all existing wrong-type/negative checks. Do not infer unknown
usage from prose or retry provider calls.

Evaluation uses synthetic response envelopes only: absent usage, absent input,
absent output, explicit zeros, normal counts and malformed counts. Exercise the
actual HTTP response parser and budget wrapper, including unknown-cost failure
retaining reservation/stopping later admissions. No external provider calls,
credentials or real course/student data are used. Capture pre-fix source hash
and parser observations, post-fix source hash, test results and limitations.

Gate: every absent count fails usage validation; valid zero/normal usage stays
accepted; surrounding budget does not treat malformed unknown usage as free.
Record a Keep repair decision only if focused provider/budget regressions pass.
No performance/teaching claim or selected model change follows. Existing real
run costs are not retroactively marked invalid without evidence of missing
usage in their raw output.
