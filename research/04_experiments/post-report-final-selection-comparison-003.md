# Final selection comparison 003: composed model identity correction

Series002 is retained as an integration failure. The audit generator attempted
to infer revision identity from its direct client, but the application passes a
budget wrapper; the role metadata was not present at that boundary. As a result,
Luna audit responses were rejected against the historical Sol default. Individual
role and generator tests passed but the new full-composition test caught the
failure. This is not evidence that Luna's semantic judgments failed.

Fix before rerunning: carry the audit model as an explicit factory runtime flag,
validate it only when final auditing is enabled, and expose the exact model in
runtime configuration. No wrapper introspection or silent substitution. Preserve
Sol default behavior. Add composed-runtime regression for both Sol and Luna.

After all four mixed-source restore tests pass, run the same complete twelve
paired packets once as series003, same seed, caps and models. The seven originally
new cases are now exposed development; do not call them held-out transfer evidence.
No changes to sources, questions, expected meanings, prompts or adoption threshold.
No selective answer retries. Same calibrated Mini instrument003 with all64 controls
and96 product ratings; strict gates and case-cluster bootstrap as specified in
comparison002. Keep current configuration if improvement is not supported.

Any further failure is recorded; this pass does not promise a quality improvement.
All calls stay under the cumulative US$30 budget, no Sol calls. Do not edit source
or plans frozen in a running evaluation. Source archives record exact code epochs.
