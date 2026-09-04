# Local R1 governed V2.1 release qualification 006 plan

## Decision question

Does the exact candidate-v3 local R1 composition remain operationally correct
after the multi-concept learner-assessment scope correction recorded by
`governed-full-autonomy-v2-1-multi-concept-confirmation-025`?

This is an operational requalification, not a new grounding-quality or
professor-fidelity claim. The selected composition is unchanged except for the
assessment-scope correction:

- `governed-autonomous-tutoring-graph-v2.1`;
- `guarded-policy-value-planner-v2` with exact GPT-5.6 Luna planning;
- deterministic grounded generation;
- `dominance-scoped-ambiguity-safe-v3` evidence gating;
- profile `student-tutor-r1-local-candidate` version
  `v2.1-floor-004-h-e1`;
- T0 grounded-assistant rollback.

## Fixed checks

1. Build immutable API/web images from a clean revision and record digests.
2. Validate the exact non-secret environment and fail-closed startup binding.
3. Complete the existing 25-check administrator, professor, and student HTTPS
   journey using synthetic identities and open demonstration material.
4. Restart the services and complete all six persistence checks.
5. Produce and verify a runtime backup, restore it into a clean Compose
   project, and complete all six restore checks.
6. Switch the original stack to T0 and complete all three rollback checks.
7. Restore governed V2.1 and complete all three mode-restoration checks.
8. Run desktop and 390-pixel browser smoke checks, inspect console errors, and
   verify keyboard-reachable primary controls and critical accessibility.
9. Record revision, profile and binding hashes, image digests, artifact hashes,
   provider usage, failures, and limitations.

## Decision rule

- `Keep`: all 43 machine-verifiable operational checks pass, browser smoke has
  no critical defect, exact selectors and hashes match, and no secret, private
  source, real student, or unrestricted model output is committed.
- `Refine`: the valid composition fails a workflow, persistence, safety,
  grounding, browser-critical, or rollback check.
- `Invalid`: an environment or harness defect prevents interpretation. Correct
  only that demonstrated operational defect and preserve the failed attempt.

The known 10,000+1,000 package remains immutable and is not read, rerun, or
rescored. The true-visual and professor-fidelity successors remain separate
evaluation boundaries.
