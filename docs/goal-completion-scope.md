# Objective-scoped goal completion

The V2 goal manager completes an active goal only from evidence for that goal's
approved objective. The previous manager selected the strongest concept in the
whole learner state; the student service also completed every active goal whenever
any concept met its evidence threshold. Two cache-coherence answers could therefore
complete an unassessed virtual-memory goal.

## Completion contract

The immutable release domain maps an exact, unambiguous objective statement to a
set of concept IDs. Let this set be C(g). For a committed V2 attribution snapshot,
let correct(c), incorrect(c), and confidence(c) be its evidence counts and
attribution confidence. The operational rule is:

```text
complete(g) = unique same-release objective mapping exists
              AND the learner state has the same course and release
              AND for every c in C(g):
                    evidence for c exists
                    AND correct(c) >= 2
                    AND incorrect(c) = 0
                    AND confidence(c) >= 0.5
```

The service supplies the authenticated student's turn state. An uncommitted or
rejected state is not eligible. Missing/ambiguous mappings remain incomplete.
For objectives with several concepts, all must qualify; unrelated concepts have
no influence. The legacy mastery-state route keeps its existing thresholds but
also requires all mapped concepts. Progress is the minimum of the existing
per-concept progress heuristics, with missing concepts contributing zero.

This rule is an evidence threshold, not a calibrated mastery estimate. The existing
cumulative-state contradiction rule is retained: an incorrect assessment continues
to block completion in that state. Free-text success conditions are descriptions;
the manager does not parse arbitrary professor-written criteria into executable rules.

## Turn and persistence flow

```text
grounded student turn -> eligible belief revision -> release objective mapping
                     -> evaluate each active goal independently
                     -> collect only supported completion IDs
                     -> retain follow-up for another incomplete objective
                     -> save turn, belief, completion and cancellation atomically
```

The goal lookup retains goals completing in the current turn so that the same turn
does not recreate them. Before creating a later goal, the service also checks
whether its objective already has sufficient evidence. The repository transaction
still verifies ownership/release/status, completes the supplied IDs and cancels
only their pending opportunities and wake-ups. HTTP schemas and database schemas
are unchanged. Historical completed statuses are not retroactively rewritten.

The implementation is in [autonomy_control.py](../src/digital_twin/student/autonomy_control.py)
and [service.py](../src/digital_twin/student/service.py). The
[regression tests](../tests/digital_twin/test_goal_completion_scope.py) include an
actual two-goal service conversation and database reopening. The
[audit tests](../tests/test_goal_completion_scope_evaluation.py) ensure that rejected
observations, future state and separate conversations cannot manufacture success.

## Decision and limitations

Exact domain mapping was chosen over lexical matching or LLM interpretation:
completion must use the same approved concepts throughout the release, without a
model gaining authority to mark goals complete. The cost is conservative behaviour
when a policy objective lacks an unambiguous domain mapping. The correction changes
goal lifecycle only; it does not calibrate learner mastery, improve response wording,
or validate human learning outcomes.

The [prospective experiment](../research/04_experiments/2026-09-06-goal-completion-scope-plan.md)
and [retrospective audit](../research/05_evaluation/goal-completion-scope-review-audit-001-results.md)
retain the control, failure evidence and measurement corrections. The 30-day paired
comparison uses actual services with synthetic students/time and deterministic
generation. The original 025 and provider-backed experiments remain unchanged.
