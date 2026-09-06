# Question-specific answers and profile-aware rendering development

Candidate: `question-specific-profile-grounded-v1`. Baseline: selected deterministic evidence-set V2 with dominance V3. This is an opt-in development candidate; no selected profile is changed.

Decision question: can an asynchronous model distinguish requested details absent from otherwise related retrieved evidence, select evidence addressing all requested aspects, and avoid showing the answer during a Socratic elicitation stage?

Prediction: requiring an explicit per-aspect support assessment will reduce answers to unsupported specifics relative to copying complete retrieved chunks. A code-owned elicitation renderer will withhold evidence text during diagnosis, next-step and self-explanation stages. These predictions are not conclusions until independently scored live trials.

Design: one bounded provider task after deterministic policy and retrieval eligibility. Inputs contain question, approved evidence, trusted teaching preferences, selected pedagogical intent and help level. The structured proposal declares question requirements, support and exact evidence spans, answerability, and teaching move. Application code owns policy, citations, release/state authority and final rendering. No model call is hidden in a synchronous evidence gate. Provider failure, malformed output, absent support or invalid spans cannot fall back to releasing the whole retrieved passage.

Comparison: same fresh four-course development cases and sources for incumbent and candidate; include answerable single/multiple aspects, absent numeric/mechanistic specifics, unrelated/no evidence, ambiguous reference, graded-work, Socratic initial and post-attempt stages, profile changes, malformed/provider failure and stale evidence. Gold required facts and withheld spans remain outside candidate input. Preserve every failure and exact configuration in per-case output. Existing 16-question and 24-profile development observations are not sealed confirmation data; do not retune or rerun consumed sealed factual sets.

Metrics defined before execution: question-specific requirement coverage, unsupported-specific abstention, missing-answer rate, inappropriate abstention, Socratic answer leakage, profile-stage adherence, structural citation validity, independent semantic review, latency, calls, tokens and cost. Hard gates: zero unauthorized/uncited fabricated releases and zero literal evidence leakage during enforced elicitation; compare quality against incumbent. Insufficient evidence or no improvement means Refine, not acceptance. Exact source spans establish provenance only; they do not prove relevance, semantic entailment, requirement completeness or learning benefit.

Initial validation: deterministic fake-provider tests for missing support, exact-span validation, bounded task shape, profile forwarding, withholding, failure and default-preserving factory binding. Subsequent finite provider-backed comparison is orchestrated separately and results must be registered. No live model calls are part of implementation testing.

Admission configuration: candidate explicitly replaces dominance's pre-generation sufficiency decision with `authorized-top5-async-answerability-admission-v1`, admitting up to five already-authorized ranked hits to the asynchronous assessor. This is eligibility for assessment, not proof of answerability. The incumbent remains unchanged. BM25 ranking, course/version/permission filtering and zero-score document exclusion remain unchanged; true retrieval misses are outside this replacement's capability. Report admission and generator changes together, never as generator-only evidence.

Progression contract: forced initial elicitation applies only when the selected intent is diagnostic/next-step/self-explanation, no assessed attempt is available, and help level is zero. After an application-observed assessed attempt, the model may select explanation under the approved profile and recorded history. This does not force explanation after every attempt; it prevents an unconditional elicitation override from trapping all later turns. Test the same question/profile before and after attempt context. The fixed topical reflection question is an initial bounded renderer; its educational helpfulness remains unscored until independent review.

Development refinement after G7 live development 002: valid explain-first proposals were overridden by an initial elicitation intent. The deterministic perception intent is advisory, not instructor authority. When trusted approved teaching-profile context is supplied, the bounded model teaching move controls ask versus explain; initial elicitation fallback applies only without profile context. This changes no authority, evidence or source checks. Profile adherence remains a measured model outcome, not a code guarantee. Add matched Socratic-ask, explanatory-first-explain, no-profile fallback and assessed-attempt progression regressions before a fresh rerun. The observed cases remain development data.

Conditional contract refinement after live development 004: empty focus is valid when it is unused (explanation, abstention or clarification); an actual elicitation still requires a nonblank exact substring of the current question. Non-answer boundaries may have no declared aspects. An answerable proposal must contain at least one aspect, preserving the existing support/span checks and preventing vacuous empty-list answers. This removes irrelevant global minimum constraints rather than relaxing factual lineage. Provider-envelope validation and actual-rendering tests must cover the conditional contract before a fresh run.


### Neutral insufficient-evidence follow-up after operational pilot 001

Decision: remove the generic request to provide a course source, since a
privacy-sensitive question should not invite disclosure of the missing data.
Prediction: the same insufficient boundary and empty claims/citations remain,
while every insufficient response neutrally refers the student to the instructor.
Comparison: previous source-soliciting wording versus the neutral wording on a
fresh synthetic private-interaction question. This uniform wording change adds
no question keyword classifier or semantic privacy guarantee.

### Dialogue progression v2 after operational pilot 001

Decision question: can the candidate continue a declarative attempt in the
previous tutoring context and advance through an approved hint ladder without
repeating the same diagnostic question indefinitely? Baseline: frozen v1 pilot
001 (ten questions, two clarifications, no useful progression). Candidate:
`question-specific-profile-grounded-v2`, with authoritative recent actions,
current-turn assessment rather than global recent-concept assessment, explicit
continuation semantics, and a separately evidenced single-hint move. Defaults
still select the deterministic incumbent.

Prediction: after an elicitation, a relevant attempt is interpreted using the
prior student question; if the approved ladder allows hints, one partial hint
can be given; further requests advance to explanation only where the approved
profile allows it. A new concept resets the model's interpreted help episode.
An instructor who never permits direct answers must retain that restriction.
History and quoted source spans do not grant authority or establish semantic
correctness. Stage interpretation is a model proposal, measured rather than
claimed as a deterministic guarantee.

Finite development cases, before provider execution: initial question, correct
attempt, incorrect attempt, post-hint request, changed concept, explanatory
profile, never-direct-answer profile, absent requested detail, and private-data
request. Compare transcript actions and delivered content, repeated diagnostic
questions, evidence/citation validity, explicit source/model failures, and cost.
The new hint field must reference one exact approved span; a hint is not
permitted to silently become all selected answer spans. Full-solution leakage
still needs content review, since a short exact quote can disclose a solution.
The old pilot remains preserved; these cases are development, never sealed
quality confirmation or evidence of learning effects.
