# Academic factual-QA end-to-end pilot 002 — attempt 001

Result ID: `academic-factual-qa-end-to-end-pilot-002-attempt-001-invalid`

Decision: **Invalid execution**

The 160-case network-free development comparison completed and its internal
checks passed, but it ran from a dirty worktree before the runner enforced a
clean-revision preflight. It is retained as procedural evidence and is not used
to support a method claim.

The attempt used 480 paired condition rows, made zero provider calls, read no
private or held-out data, and cost USD 0. Its raw ignored artifact has SHA-256
`60f88079663f33749275f1d6a465d5c1663bafbbae9d7412f58dca1a916cd92f`.

Correction: bind the runner to the Git revision and dirty state, require a clean
worktree for CLI execution, freeze the build in Git, and rerun to a new exclusive
output path. The measurements from this attempt must not be substituted for the
corrected run.
