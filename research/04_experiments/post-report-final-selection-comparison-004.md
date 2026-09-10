# Final selection comparison004: evaluation adapter parity

Series003 is retained as incomplete: the application factory accepted the explicit
audit-model flag and mixed-source restore passed, but the separate longitudinal
evaluation factory did not yet accept/forward that keyword. Candidate histories
therefore failed before provider construction, while V4 histories ran. This is an
evaluation-adapter integration defect, not a quality result; missing candidate
outputs must not be silently dropped or rated as delivered refusals.

Carry the same named flag through the longitudinal adapter. Add preflight validation
that every selected runtime keyword is accepted before any provider calls. Add an
actual injected paired-run test for the cheap candidate and require both histories
to finish with answers and an executed audit through the budget wrappers. Do not
start the next live pass until this exact runner test and composed restore pass.

One full repeat of twelve unchanged packets as series004, same models/seed/caps and
judging protocol as002/003. Both arms rerun in the same code epoch. Sources now
exposed development. No prompt, source, expected meaning or quality threshold
change; no selective output retry. Preserve003 failure and cost. Stop the outer
series at any incomplete history rather than continuing subsequent packets. No
Sol calls; cumulative US$30 ceiling still applies. This corrects execution parity
without treating any previous incomplete experiment as a semantic win.
