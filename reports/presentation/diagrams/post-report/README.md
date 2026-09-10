# Post-report implementation diagrams

These assets describe explicit experimental components added after submission;
they do not retroactively change the submitted report or select a release profile.

- [Goal recovery state machine](goal-recovery-states.drawio), PNG export (local artifact: `goal-recovery-states.png`): UML state machine based on `RecoveryAwareGoalManager.interpret()` in `src/digital_twin/student/post_report_learning.py`. Completion requires two distinct assessed correct turns per approved target concept within seven days after that concept's latest wrong/partial response, confidence at least0.5, evidence and source-turn keys, matching learner/course/release and an unexpired goal. Duplicate turns cannot manufacture progress. Expiry/cancellation retain the existing goal lifecycle. Diagram uses conventional states, guarded transitions and a note, and remains editable in draw.io.

The figure explains the implementation; tests and synthetic simulations provide
separate evidence. Two correct assessed turns are a configured completion rule,
not proof of real mastery. Final presentation must label this as post-submission
experimental functionality until the component/profile decision is recorded.
