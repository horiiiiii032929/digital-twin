# Interpretation and claim-scope review

Reviewed on 6 September 2026. This is a review artifact, not a revision of the
submission PDFs. Page references below refer to the Desktop submission: main
pages 1–35; detailed appendix pages S-1–S-326.

## Scope and method

- Read the standalone abstract, all active main-report chapters and included
  summary appendices in context, including equations, tables and captions.
- Read the text labels in all 11 active vector diagrams.
- Screened all 474 detailed result entries for language about learning,
  effectiveness, validation and certainty. Examined the 172 flagged sentence
  occurrences in context, including duplicate matches. This is not a claim
  that all 326 archive pages or their underlying raw logs received a fresh
  sentence-by-sentence factual re-audit. Historical configuration/provenance
  fields remain archival evidence, not current-system claims.
- Cross-checked the central interpretations against the goal-completion paired
  result, live-model operational result, learner/timing result and instructional
  confirmation result. No experiments were rerun.
- The review asks what each sentence permits a first-time reader to infer:
  measured quantity, comparator, configuration, population, causal scope and
  historical versus current status.

The central distinction is between (a) an implemented learning-support feature,
(b) a measured software or simulator result, and (c) an effect on actual students.
The absence of a student study establishes neither benefit nor absence of benefit.
Conversely, this distinction must not erase genuine output-quality failures.

## Findings requiring correction

### 1. Abstract: missing comparator for the learning statement

Location: `chapters/abstract.tex`, lines 13–15.

Original: “without improving simulated learning.”

Risk: the reader can interpret this as the whole tutoring system producing no
learning. The experiment compares the old and corrected goal-completion logic,
not tutoring against no tutoring. Its reported final simulator means are
0.3632 and 0.3608 in the autonomous conditions.

Suggested replacement:

> The correction eliminated the observed unsupported completions, but did not
> increase mean final simulator mastery relative to the previous implementation.

State that this is a separate deterministic regression, rather than implying
that the preceding live-model trial used the corrected configuration.

Evidence: `research/05_evaluation/goal-completion-scope-development-001-results.md`,
primary correctness and secondary outcomes. Preserve the negative mean
difference; do not describe an equivalence test or statistically established harm.

### 2. Abstract: identify why real-student benefit is unknown

Location: `chapters/abstract.tex`, lines 16–18.

Original: “Fidelity to the actual instructor's teaching style and benefits to
student learning have not been established.”

This is factually defensible, not an assertion that students failed to learn.
However, after consecutive unsuccessful results it can sound like an unsuccessful
human trial. Make the evaluation population explicit:

> The evaluations used synthetic students and teaching profiles; fidelity to the
> actual instructor and effects on real-student learning remain untested.

Do not replace this with a claim of likely or demonstrated educational benefit.

### 3. Main page 21: live-model study does not score learning change

Location: `chapters/05-integration.tex`, lines 53–57.

Original: “Student reactions, learning, forgetting and the passage of 30 days
were simulated.”

This blurs the operational dialogue study with the hidden-mastery simulations.
The source describes seeded attendance/receptivity/misconception configurations,
synthetic text and virtual time, and explicitly says no mastery delta was scored.
The sentence can make a reader expect a missing learning-effect result.

Suggested replacement:

> Student utterances, attendance and receptivity were synthetic, and time was
> advanced virtually. This operational trial did not score changes in mastery.

Evidence: `research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md`,
Design and provenance. Its 484 turns and 654 calls are execution counts, not
learning or accuracy denominators.

### 4. Main page 22: teaching improvement is wider than the measured outcome

Location: `chapters/05-integration.tex`, lines 124–130.

Original: “with no demonstrated teaching improvement.”

The phrase is cautious but still omits the comparator and the outcome definition.
The source reports a descriptive simulator mean, not human teaching effectiveness.

Suggested replacement:

> Retain the correction for objective-scoped state correctness. In these matched
> autonomous histories, final simulator mastery was 0.0024 lower on average than
> under the previous implementation; the comparison did not measure student
> learning effects.

Keep the preceding 56 additional messages and wasted-message fractions. Do not
attribute all individual-history changes to a uniform benefit or harm: 11 rose,
nine fell and 16 were unchanged.

### 5. Main page 29: shortened table repeats the same ambiguity

Location: `chapters/appendices.tex`, goal-completion row.

Original: “simulated learning did not improve.”

Suggested replacement:

> Unsupported completions fell from 12 to zero; mean final simulator mastery
> changed by −0.0024 relative to the old completion logic.

This row must agree with finding 1 and finding 4. It is not a separate negative
learning study.

### 6. Detailed page S-126: interpretation is stronger than its source

Location: `design-appendix.tex`, line 5626; run
`goal-completion-scope-development-001`.

Original: “Correctness improved without teaching improvement”.

The source says “No learning-quality improvement is established” and bounds the
measurements to descriptive simulator effects. The appendix removes that
qualification and reads like an established general null result.

Suggested replacement:

> The correction removed the observed unsupported completions. Relative to the
> old logic, the autonomous condition delivered 56 more messages and had a mean
> final simulator-mastery difference of −0.0024; real-student learning was not
> evaluated.

Keep the original run, counts, status, links and historical correction relationships.
This finding concerns the report's editorial interpretation, not rewriting history.

### 7. Main page 19: “useful outputs” misidentifies the evaluation unit

Location: `chapters/04-comparisons.tex`, lines 295–297.

Original: “A typed instruction candidate produced 44/48 useful outputs”.

The record reports 44/48 useful **targets**, with 15/16 primary contexts;
the complete comparison has 96 histories and 168 turns. These are not 48
independent student judgments or simply 48 output messages. The rubric was
applied through assistant review.

Suggested replacement:

> Assistant review classified 44 of 48 evaluated targets as useful under the
> instructional rubric, compared with 16 of 48 for the control. The candidate
> nevertheless retained one critical attribution error.

Evidence: `research/05_evaluation/paired-pedagogy-development-001-confirmation-v10-live-001-results.md`.
Retain the failed critical gate. Adding the control here restores the actual
comparison without implying independently validated student benefit.

### 8. Main page 22: completion counts are not matched retained goal identities

Location: `chapters/05-integration.tex`, lines 117–121.

Original: “retained supported completions. Its lower total is the removal of
false completion, not a fall in measured learning success.”

The count changes from 26 to 15, while unsupported completions change from 12
to zero and supported completions from 14 to 15. Later histories can diverge.
“Retained” can be read as preserving exactly the same 14 completed goals;
the sentence also invokes a learning-success measurement that was not made.

Suggested replacement:

> Target-supported completions numbered 14 in the original arm and 15 in the
> corrected arm; unsupported completions numbered 12 and zero. Total completed
> goals therefore measure software status decisions, not student learning success.

## Clarifications that would improve first-time reading

### 9. Abstract: 89.42% and 63.25% are not a before/after deterioration

The text already says “separate evaluation on fresh cases”, so the numbers are
not factually contradictory. The abstract should explicitly call the first a
development comparison and the second a different fresh-case fallback evaluation.
Both are strict fully-grounded-answer proportions, not test scores obtained by
students. The main text's scoring equations are adequate and should remain.

Suggested phrase for the second result:

> On a different fresh-case evaluation, the retained BM25 fallback met the full
> grounding criteria in 63.25% of answerable cases, below its acceptance threshold.

Do not describe the remaining 36.75% as hallucinations: a failure can include
missing a required fact, an abstention or another failed scoring condition.

### 10. Main page 15: zero grounded answers does not mean no relevant evidence

The paragraph already explains the incompatible composition: an unrestricted
evidence set reaches an interface requiring one or two selected claims.
Its 98% retrieval coverage and zero strict grounded successes concern that
control, not all system responses. Keep the mechanism adjacent to the zero;
“zero cases satisfying the complete grounding rubric in this control” is clearer.

### 11. Main pages 21 and 34: generic questions versus no student benefit

All 16 reviewed check-ins wrapped an entire source card in generic guidance.
That is a real observed output limitation. The report should state it directly
and then separately state that no student usefulness study was conducted.
It should neither claim those messages cannot help any student nor remove the
failure because a student might still learn from quoted material.

Suggested wording:

> The 16 check-ins repeated source-card content with generic guidance rather
> than concept-specific follow-up. Their effect on students was not measured.

The 77 diagnostic cases were deliberately selected; the existing warning against
using them as a representative quality estimate is correct.

### 12. Main page 22: “not an accepted deployment” is unnecessarily ambiguous

Location: final sentence of `chapters/05-integration.tex`.

Original: “not an accepted deployment meeting all five requirements.”

This can sound like the software does not execute, or that all five requirements
failed. The preceding paragraph distinguishes bounded verification from unmet
quality requirements correctly.

Suggested replacement:

> The prototype implements the course and tutoring workflows, but has not met
> all five acceptance requirements: factual-quality gates remain unmet, and
> instructor fidelity and real-student learning effects remain unvalidated.

This does not turn the prototype into an accepted production release.

### 13. Main pages 26 and S-1: registered entries versus executed experiments

“474 registered trials” includes build-only checks, corrections and stopped
attempts, not 474 full evaluations with learners or model calls. The detailed
introduction correctly says “474 registered result rows”. Use the same unit in
the main summary: “474 registered result entries, including build checks,
completed evaluations, stopped attempts and corrections”. Never sum their case
counts into an independent student sample.

### 14. Conclusion: make the tested comparison explicit

Original: “correcting goal completion need not improve simulated learning.”

It is a defensible statement of non-equivalence, but again leaves the reader to
remember which configuration and comparator it means. Prefer:

> The objective-scoped correction improved completion correctness but did not
> increase the simulator's mean final mastery relative to the old logic.

The conclusion can separately mention that BKT/value improved simulated mastery
relative to count/constant while remaining an unintegrated experimental candidate.
Do not claim the whole application already realizes that gain.

### 15. Simulator results need their own comparison identities

The three results below are compatible and must not be pooled:

| Result | Comparator | Supported interpretation |
| --- | --- | --- |
| +0.014 final simulated mastery | BKT/value versus count/constant | A timing/estimator candidate improved that simulator outcome; not integrated product or human evidence. |
| +0.0324 historical paired difference | Autonomous versus reactive in the old multi-concept run | Historical simulator result; the later goal defect prevents treating it as evidence for the corrected lifecycle. |
| −0.0024 final simulated mastery | Corrected versus old goal logic, autonomous conditions | A descriptive secondary outcome of a correctness regression; not tutoring versus no tutoring. |

The first result is already clearly qualified in the main body. Adding it to
the abstract is an optional balance decision, not a factual requirement. Do not
select positive results merely to counter the negative impression.

### 16. Diagram terminology is mostly bounded correctly

The goal-state diagram labels COMPLETED as “Evidence threshold met”; the learner
diagram separates the planning proxy from assessed mastery; the simulation
diagram separates observations and hidden truth. These are useful distinctions
and should remain. “Learning objective” in general prose should not imply that
the software's two-correct-attempt threshold validates educational mastery.

The autonomy diagram's end node terminates one job, not all continuing tutoring.
Its caption and later-event lane already say so. There is no reason to redraw
this flow for the present interpretation issue.

## Expressions to retain

- “have not been established” is not itself false or an assertion of no effect;
  the main improvement is stating what population and outcome were not evaluated.
- The failed factual acceptance gates and critical attribution errors are real
  findings. Do not recast them as mere missing evaluations.
- “working research prototype” is consistent with executed service, worker and
  persistence evidence, provided the configuration and acceptance limits remain.
- No measured real-student learning effect is established. This is an evidence
  boundary, not a negative learning result.
- The 30 virtual days do not establish 30 days of uptime; the explicit distinction
  is correct.

## Recommended revision order

1. Correct findings 1–8 consistently across the abstract, body and appendix.
2. Clarify the metric and population boundaries in findings 9–15, avoiding
   repetitive disclaimers. Keep existing adequate diagram labels.
3. Rebuild both PDFs; verify all changed sentences in their page context and
   recheck navigation, indices and source-package reproducibility.

The current review has not changed or replaced either Desktop submission PDF.
