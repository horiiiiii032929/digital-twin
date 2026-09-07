# Goal completion scope correction

Status: prospective contract, written before the runtime correction and paired run.

## Decision and prediction

Can goal completion use only committed evidence for the goal's approved objective,
without suppressing legitimate completion or follow-up for other active goals?
The current control picks the strongest concept and also has a service shortcut
that completes every active goal. The prediction is that explicit objective
binding removes false completions while retaining correctly supported completions.

## Alternatives and contract

- Control: unchanged current working-tree goal manager v1 and service.
- Candidate: manager v2, exact objective-statement mapping in the immutable release
  domain, every associated concept required, same per-concept evidence thresholds.
- Rejected design: fuzzy objective matching for completion; ambiguous or missing
  mappings must remain incomplete. No model interprets free-text success conditions.

For V2 evidence, each required concept needs at least two correct assessments, no
incorrect assessment in the current cumulative state, and attribution confidence
at least 0.5. This is an operational evidence rule, not demonstrated mastery.
Missing target evidence, missing/ambiguous mappings, mismatched course/release, and
uncommitted state cannot complete a goal. Legacy mastery state retains its existing
thresholds but applies them to every required target concept. Progress uses the
least-supported required concept; it is a heuristic, not a probability.
Completion and follow-up for another objective may coexist in the same turn.

## Dataset and comparison

Run ID: `goal-completion-scope-development-001`, with separate `baseline` and
`candidate` arms. Reuse the six synthetic concept cards and fixed schedule of 025,
with seeds 9101, 9102, 9103. These are new stochastic histories, **not** new concepts
or an independent held-out study. Each arm has 72 histories: six personas, two
simulator families, three seeds, reactive/autonomous conditions; 30 virtual days
and a day-15 process restart. Same driver, simulator, prompts, conditions and seeds
in both arms; only the two runtime files may differ. Archive source and dependency
identity before each arm; do not overwrite an existing output directory.

Use the real product adapter and SQLite state; deny network connections. There are
zero external LLM calls, tokens and provider cost. Students, time and learning
effects are simulated. Sample size covers all existing persona/family combinations
with three repeats; it is a regression study, not a powered learning-effect study.

## Metrics and gates

Primary: completed goals lacking eligible target evidence, histories affected,
unresolvable objectives. Independently inspect committed attribution snapshots at
completion time, by conversation, never sum rejected observations or pool evidence
across conversations. Require zero unsupported/unresolvable completions in the
candidate, plus positive supported completions and passing target-specific tests.
The final-database audit cannot distinguish two commits with exactly equal virtual
timestamps; regression tests therefore verify the exact per-turn state boundary.

Retain 025's attribution/assessment >=0.95, recognised attempts =1, zero quiet-hour,
frequency and cooldown violations, zero provider calls, and consistent restarts.
Compare paired per-history outreach and hidden learner outcomes descriptively;
these are secondary simulator-specific effects, not human learning evidence.
Report wall time and process peak memory; no latency optimisation claim.

Regression cases: unrelated correct evidence, incorrect target, valid target,
multi-concept partial/all readiness, low confidence, no state, ambiguous mapping,
course/release mismatch, legacy state, rejected state, two active goals, concurrent
completion/follow-up, and persistence after reopening the database. Run the relevant
existing autonomy, belief, service and persistence tests before broader checks.

## Evidence and disposition

Keep historical 025 and the provider-backed dialogue run unchanged. Add an explicit
correction link explaining that historical goal lifecycle was not validated by
their assessment gates. Retain the prior audit's initial harness and observation-
only measurement errors as superseded diagnostics, not product failures.
Record both paired arms, any failed gates, source hashes, per-goal evidence and
limitations in the result registry. Select the correction in a new experimental
component profile only after the gates pass; do not requalify the frozen release.
The planner's attempt-count proxy and teaching-response quality are outside this
bounded correction.
