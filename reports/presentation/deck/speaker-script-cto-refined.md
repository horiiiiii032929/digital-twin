# Course Digital Twin — read-aloud script

For digital-twin-presentation-cto-refined.pptx. Read the paragraphs. Headings and the bracketed video cue are not spoken. No narration is required during the video.

4,786 spoken words across 31 slides, plus the 4:06 video. Estimated total: 30.7–32.3 minutes at 180–170 words per minute, or 34.0 minutes at 160 words per minute. These estimates exclude extra pauses, slide changes and questions; no timed rehearsal has been performed.

## 1. Developing a Course Digital Twin

Thank you for your time. Today, I’ll present the Course Digital Twin software that I developed, the design choices behind it, and the improvements it needs next.

The software lets a professor publish course materials and teaching settings. Students can then ask questions using those published materials. The system can also save learning goals and provide later support, when that support is permitted.

I’ll focus on three questions. What does the software currently do? Which choices have the strongest evidence so far? And what should we improve to make it useful for continuing learning support?

The project has a working prototype and several component comparisons. The remaining challenge is to connect reliable operation with useful teaching. I’ll explain both the progress and the failures, because those failures helped determine the next development decisions.

## 2. Presentation roadmap

The presentation follows six chapters.

First, I’ll introduce the product and show the application running. Then I’ll explain its structure, its stored data, and how background support starts.

The next two chapters cover the main design decisions. One concerns how the system answers course questions. The other concerns how it chooses later support and represents the learner’s state.

After that, I’ll explain how goals, permissions, and retries are handled over time. Finally, I’ll bring the results together and propose the next development work.

One point to keep in mind is that the comparisons use different datasets and conditions. Each comparison supports a particular decision. We cannot simply combine the best number from every study and claim that the whole system has been validated.

## 3. Who uses the course assistant?

This diagram shows the people and systems involved.

On the left, the professor publishes materials and configures teaching policy. That published information defines the course context the assistant should use.

On the right, the student asks questions, attempts tasks, and receives support. The assistant sits between these activities. It answers using the permitted course context and can continue supporting the student later.

The external generation provider is shown below. The software can request generated candidates from that provider, while the application still controls permissions and what is saved.

The autonomous part is the ability to begin permitted support without another student question. For example, saved work may become due after an earlier interaction.

I use the name Course Digital Twin for this configurable course assistant. Whether it faithfully reproduces a professor’s teaching is still something we need to evaluate. The name itself does not establish that result.

## 4. Demo: course setup and 30 days of support

Before explaining the architecture, I’ll show the actual application.

The recording uses two professors, two courses, and four synthetic students. Time moves forward virtually, so we can see activity across thirty days within a few minutes.

Please watch three things: course publication, the separate student histories, and the follow-ups that appear without a new student request.

The application is real, but responses in this recording are deterministic. This makes the demonstration repeatable. Some preparation happened off-camera.

[PLAY VIDEO — 4 minutes 6 seconds. Let the subtitles explain the recording.]

That was the operational workflow. The demonstration shows that these actions can happen through the application. I’ll now explain the design and the separate evaluations that examine whether its decisions and answers are good enough.

## 5. What has been built—and what remains open

The prototype now supports course publication, student dialogue, saved goals, and later check-ins. However, a working feature and an accepted teaching capability are different stages of development.

For answers, the evidence supports making the required facts explicit. That helped on development cases, but performance on fresh questions remains a problem.

For support decisions, the evidence supports keeping an allowed baseline action when a proposed replacement is unsuitable. We still need stronger evidence that the resulting support is useful and personalized.

For goal completion, the software now uses evidence relevant to the goal’s own concepts. This corrected a state-management failure. The educational meaning of the completion rule still needs validation.

When I say a choice is the current best, I mean the best supported choice within the alternatives and conditions tested. That is the scope of the claims I’ll make throughout the presentation.

## 6. Requirements and acceptance conditions

These three requirements connect the software design to the evaluations.

The first is correct answers. An answer should include the requested facts, and those facts should be supported by the published course. I check this through answer and citation comparisons.

The second is appropriate support. The system should choose actions using the student’s goal and relevant evidence about that student. The action-selection and timing comparisons examine parts of this requirement.

The third is controlled operation. The system should respect current authority and preserve consistent saved state. This includes checking the scope of evidence, handling permission changes, and recovering from a retry.

The labels R one, R two, and R three are just a convenient way to track these requirements. I’ll return to the same three labels near the end.

Together, they give us a way to discuss acceptance. The software must do more than produce a message successfully. It must produce an appropriate result under the current course and student conditions.

## 7. Current local software structure

Here is the current local software structure.

The web application provides the professor and student interfaces. It talks to the API service, which handles course setup, material ingestion, tutoring, and authorized saves.

The autonomy worker runs background work. It observes saved activity and processes support that has become due. This is how the application continues beyond a single browser request.

Both paths connect to durable state. The database stores dialogue, goals, and jobs. File storage holds the source materials. The generation provider supplies generated output where the configured path calls for it.

The important connection is the shared saved state. A student interaction can leave information that the worker uses later. Background support therefore depends on what was actually saved, rather than on an open browser session.

This diagram describes the current local configuration. It does not mean that this database or deployment arrangement has won a scaling comparison. Those operational choices would need their own evaluation before broader deployment.

## 8. Data relationships behind continuing support

This diagram shows a subset of the actual database relationships. I’ll focus on what those relationships mean for continuing support.

An account identifies the student. A published release fixes the course materials and settings for a particular version. Both conversations and learning goals refer to the student and the release.

On the right, learner observations and concept assessments are attached to conversations. These records provide information that later decisions can inspect.

The blue boxes highlight the important distinction. A learning goal and a concept assessment are related through application logic, but there is no direct foreign key between these two boxes.

That means the application must select the correct evidence when evaluating a goal. Matching the student alone is insufficient. It must also match the published release and the concepts that the goal targets.

Later, I’ll show a failure where this selection was too broad. The database could store the records correctly while the application still used them to complete the wrong goal.

## 9. Two entry points into the same saved system

This sequence diagram shows the two ways work can enter the same system. Time moves downward.

In the upper part, the student submits a question or an attempt. The service processes the interaction, checks authority again, and saves the response.

In the lower part, some time has passed. The worker reads work that is due and asks the service to process eligible support. This second path does not require another student message.

However, due work does not automatically mean that a message should be sent. The goal, available evidence, consent, and schedule must still permit the action. The outcome can be a saved support message or a decision to take no action.

Both paths check authority before saving their effects. This matters because the conditions can change between the beginning and the end of the work.

So the autonomous behavior comes from saved state and later processing, with the same need for valid decisions and controlled saves.

## 10. Current factual-answer path

I’ll now move to the answer design.

The current factual-answer path begins by loading the published course and the sources that the student is allowed to use.

It then ranks evidence using B M twenty-five, a keyword-based retrieval method. In simple terms, this stage helps identify source passages that match the question’s words.

The highlighted step is where the answer is assembled. The system checks the available evidence and selects the required, supported facts. In this retained path, the assembly is deterministic.

If the evidence is ambiguous or insufficient, the response should clarify the question or abstain. If the answer succeeds, it is saved with source citations.

A key design question is what the system considers sufficient evidence. Finding a passage is only one part of the task. The answer still needs to include all the facts requested by the question. The next example makes that distinction concrete.

## 11. Finding the source does not complete the answer

Suppose the student asks, “List all three stages.” The retrieved source says, “The stages are draft, review and publish.”

The retrieval step has succeeded. The complete source is available.

Now look at the answer on the left. It says, “Draft and review.” Both items are supported by the source, but the answer leaves out publish. It contains two correct items when the question requires three.

The answer on the right includes all three stages. It satisfies both requirements: the items are supported, and the requested set is complete.

In this evaluation, that is what a grounded answer must do. It must be complete as well as supported.

This example suggests a more precise interface between the question and the answer check. We can state the expected fact type, the required count, and the required items. Then the check can ask whether those facts are available and included, instead of relying on a broad match to the whole question.

## 12. Why the more complex answer paths failed

This slide shows why two more complex historical answer paths did not work well in the tested setting.

Each column is a separate activity. The simple control retrieves a keyword match and extracts a response. The hierarchy path adds hierarchical retrieval. The plan-and-observe path decomposes the work, retrieves evidence, and combines it.

The orange steps show the shared problem in the two more complex paths. Both checked coverage of the whole question too broadly. This could cause them to reject a case even when the evidence contained the facts needed for the answer.

So additional retrieval and planning stages did not remove the underlying problem. They still depended on an unsuitable sufficiency check.

The development response was to make the answer requirement more explicit. We wanted the check to focus on the facts the answer needed to contain.

This finding is specific to these tested paths. It does not show that hierarchical retrieval or more structured architectures are generally ineffective.

## 13. Explicit answer facts improved the same 397 cases

The next comparison tested that change on the same three hundred and ninety-seven answerable cases.

With the original rule, the system produced two hundred and fifty-three grounded answers. With explicit required facts and item counts, that increased to three hundred and fifty-five. That is one hundred and two additional complete, supported answers on the matched cases.

The third bar shows an additional section-ranking stage. It also produced three hundred and fifty-five grounded answers. There was no further quality gain in this comparison.

The extra stage did increase the measured latency. The ninety-fifth percentile rose from about one point four to about two point eight milliseconds. That measure describes the time within which ninety-five percent of the measured requests finished.

The decision was therefore to retain the explicit fact requirement. The extra ranking stage did not justify itself on these results.

The next question is whether that development improvement carries over to fresh cases.

## 14. Fresh answers still missed the acceptance thresholds

On fresh cases, the remaining gap was much larger.

This comparison used eight hundred answerable questions and two hundred cases requiring refusal or clarification. The blue bars show the two methods. The gray bars show the required thresholds.

On the left, the keyword-based control produced complete, supported answers in sixty-three point two five percent of the answerable cases. Hybrid retrieval reached sixty-two percent. Both were well below the ninety-five percent requirement.

On the right, the control correctly refused or clarified in ninety-six percent of boundary cases. The hybrid path reached ninety-five percent. Both missed the ninety-eight percent threshold.

The hybrid method adds semantic retrieval, but the two paths share the answer check. It did not resolve the acceptance gap here.

These results support keeping the simpler control while refining answer quality. They also limit the earlier conclusion. An improvement on development cases is useful evidence, but it does not establish that the product is ready to teach from new questions.

## 15. Better retrieval or wording did not ensure correct answers

Two other studies examined changes around the answer path. They help explain why intermediate improvements can be misleading.

On the left, visual retrieval found more relevant evidence. The result improved from eighteen to twenty-eight out of thirty. However, grounded answers stayed at twenty out of thirty in both conditions. Better evidence retrieval did not produce more complete, supported answers.

On the right, a wording revision changed the meaning of the source. The source says that exactly two seals are required. The revision says that two seals guarantee acceptance. A requirement has become a guarantee, which the source does not support.

The wording candidates repaired many defective drafts and preserved the adequate drafts in their evaluation, but a critical error remained.

These were separate studies, so I am not combining their numbers. They support the same development lesson: evaluate the final answer after every stage. Retrieval quality and fluent wording are useful, but neither one establishes answer correctness by itself.

## 16. Current support planner: retain an allowed fallback

The next chapter concerns autonomous support: how the software decides what to do later.

The planner selects an action. A separate generator writes the selected message. This separates the decision about support from the wording of that support.

Reading from the left, the planner first checks whether the evidence is allowed. If it is not, the result is no action.

If it is allowed, the planner keeps a permitted baseline action, called A. It then evaluates a proposed replacement and its predicted value.

The proposal only replaces the baseline when the replacement conditions pass. These include permission and validity checks, analytic support, and a predicted gain of at least zero point zero four.

If those conditions fail, the planner uses the baseline that it already retained.

The purpose of this design is to preserve a usable option. A failed proposal should not cause the system to lose an allowed baseline action. The next slide shows why that became important.

## 17. Why reject-only verification was not retained

The earlier alternatives changed how actions were selected while keeping shared permission constraints.

The first design, fixed rules A, provides a predictable baseline. It has limited flexibility, but it also gives us a clear control for comparison.

The second adds a model proposal and lookahead. It introduces more stages to propose and score possible actions. In the earlier comparison, those stages did not beat A on the evaluation score.

The third adds a reject-only verifier. This can identify a proposal that should not be used, but rejection by itself does not provide a better action. It can remove a usable choice without replacing it.

The highlighted design, guarded replacement H, keeps A unless another proposal qualifies. It therefore retains an allowed fallback when the proposal fails.

This changes the question from whether a proposal can be rejected to whether a replacement is justified. To evaluate that change, we need to examine both rule compliance and the value of the selected action.

## 18. Guarded replacement slightly improved simulated utility

The confirmation comparison used the same one thousand contexts for rules A and guarded H.

The mean utility was about zero point seven nine five for A and zero point eight zero zero for H. The paired gain was approximately zero point zero zero four eight. The ninety-five percent confidence interval for that gain was above zero.

The gain is positive, but small. It also depends on what utility means here. An authored evaluator scores the chosen action using simulated learner outcomes. This is separate from the planner’s own predicted score, and it is not a measurement of real-student learning.

Both methods obeyed all tested action rules. The extra process also required provider calls and had some failures, as recorded below.

One important comparison is still missing: choosing the analytically best action without asking a model to propose it first.

So this result supports further comparison of guarded replacement. It does not settle whether the model proposal is necessary, or whether students would benefit from the measured utility gain.

## 19. The planner input can rise without a new answer

There is also a problem before the planner makes its decision: the input it receives.

The current adapter uses the number of delivered messages to set a probability. The formula is the delivery count plus one, divided by the delivery count plus two, with an upper cap.

Before any delivery, the value is zero point five. After one delivery, it rises to about zero point six seven.

The important line is below the two values: there are no new assessed answers in either state. The value has increased because the system delivered a message, even though the student has not demonstrated new understanding.

This creates a weak connection between the input and the learner’s actual state. A later planner decision can react to a number that changed because of the system’s own activity.

That motivates the next comparison: using assessed answers to estimate learner state. Goal completion already uses assessed evidence separately; this slide concerns the planner’s current input adapter.

## 20. Learner models: what they estimate and how we test it

The learner-model comparison examines three methods that use assessed answers. These are experimental alternatives, and they are not integrated into the current delivery-count input.

The first is a simple count baseline. It uses the assessed history to produce a knowledge estimate.

B K T stands for Bayesian Knowledge Tracing. It updates a probability that the learner knows a concept after correct or incorrect attempts.

P F A stands for Performance Factors Analysis. It uses the history of successes and failures to predict the probability of the next correct answer.

Below the methods are the two evaluation tasks. Mean squared error compares an estimate with the simulator’s hidden knowledge. The Brier score compares a predicted answer probability with the observed answer outcome. Lower is better for both.

These are different prediction targets. A model can represent the simulator’s hidden knowledge more accurately without improving its prediction of the next answer. We therefore need to inspect both results before deciding which method is useful.

## 21. The best estimator depends on the prediction task

This study used two hundred and forty synthetic learners per condition, across two simulator families, over thirty days. Contact timing was held constant so that we could compare the estimators.

On the left, B K T has the lowest mean squared error: zero point zero three five, compared with zero point zero eight four for Count. The reported paired confidence interval supports an improvement in estimating hidden knowledge.

On the right, Count and B K T both round to a Brier score of zero point two five nine. P F A reaches zero point two four nine, with a paired confidence interval supporting an improvement against Count.

So the result depends on the target. B K T better estimates hidden knowledge here. P F A improves prediction of the next answer against the count baseline.

This gives us candidates for further work, rather than one universal winner. We should select the estimator according to the decision it needs to support, then test it after integration into the application.

## 22. Contact timing changes messages and simulated knowledge

The same simulation also lets us examine when the system contacts the learner.

Here, the count estimator is held fixed. Constant timing sends support at every eligible check. Conditional timing waits for a need signal. Value-based timing requires predicted benefit above a margin.

On the left, conditional timing reduces the mean number of messages from fourteen to seven. That looks attractive if we only measure contact volume.

But the right-hand chart shows the tradeoff. Mean hidden mastery at day thirty falls from zero point three one four to zero point three zero two. In this simulation, fewer messages also came with lower knowledge.

Value-based timing produced a different balance. Across the tested feasible pairs, B K T with value-based timing had the highest mean day-thirty mastery, but it remains an unintegrated candidate.

The decision should therefore consider useful and missed support together. Reducing contact is valuable only if we understand what learning opportunities may also have been removed.

## 23. A goal outlives a single background job

The next chapter looks at correctness over time. This begins with the difference between a learning goal and a background job.

An active goal can produce bounded jobs, such as attempts to deliver support. Sending a message increases the attempt count. Reaching an attempt limit does not mean that the learning goal has been achieved.

The state diagram shows three ways to leave the active state. A goal can complete when all target evidence passes. It can expire when its expiry condition is reached. Or it can be cancelled when cancellation or scope conditions require it.

The current completion rule checks each target concept. It requires at least two correct attempts, no incorrect attempts, and sufficient confidence under the software’s rule.

Those thresholds are implementation rules, not validated measures of mastery. The key correctness property here is narrower: completion must use evidence for the goal’s own targets. An unrelated success should not complete the goal, even when it belongs to the same student.

## 24. Target-specific evidence removed false completions

This was a concrete failure in the earlier completion logic.

Correct answers about cache coherence could also complete a virtual-memory goal that had not been assessed. The student and course release matched, but the concepts did not.

The chart compares the old rule and the corrected rule on seventy-two matched synthetic histories per version. Blue shows supported completions. Orange shows unsupported completions.

The old rule produced fourteen supported completions and twelve unsupported ones. After the target-scope correction, there were fifteen supported completions and no unsupported completions in this comparison.

That supports retaining the correction. It fixes which evidence can justify a saved state change.

However, it does not establish an educational gain. In the autonomous slice, the correction led to fifty-six additional messages, while the simulated mastery change was slightly negative.

The conclusion is that valid goal state and useful teaching both need evaluation. Correcting false completion is necessary for reliable software, but sending more follow-ups after that correction is not automatically better for the learner.

## 25. Authority can change while an answer is generated

Authority can also change while work is in progress.

In this sequence, the tutoring service first reads the current release and state. It begins generating a response based on that information.

Before the response is saved, the professor withdraws the release. The conditions that allowed the work at the beginning are no longer current.

At step three, the service checks authority again at commit. The final result is to reject the stale work and save no answer.

Generation runs outside the write transaction. That avoids treating a long-running generation call as one continuous database write, but it also makes the final recheck essential.

The same general concern applies to saved learner-state revisions. The system checks those revisions to avoid applying an update based on an old state.

The contract is that permission at the start is insufficient. The authority and state relevant to the effect must still be valid when that effect is committed.

## 26. A retry reuses the message already saved

This sequence shows a different failure window: a worker stops after the message has been saved, but before the job is marked complete.

At step one, the worker processes a delivery with key K. At step two, the delivery service saves the message for that key.

The worker then stops. After restarting, it retries the same key, because the job was not recorded as complete.

The service looks up the message associated with K and returns the saved message. It does not need to create a second in-app message for the same delivery.

The stable key connects the retry to the effect that already happened. This is the specific local recovery contract shown here.

It does not guarantee exactly-once effects in every external system. If delivery later involves another service, that boundary needs its own handling and evaluation.

Together with the authority recheck, this illustrates why continuing support needs explicit rules for what may be saved and what happens when work is repeated.

## 27. The integrated trial exposed weak continuing support

The integrated trial then tested the application over longer histories with actual external model calls. This study is separate from the deterministic demonstration shown earlier.

It used twenty-four synthetic histories over thirty virtual days. The totals were four hundred and eighty-four tutor turns, six hundred and fifty-four model calls, sixteen proactive messages, and ten synthetic replies.

The lower part of the slide shows two different operational conclusions.

During days ten to nineteen, consent was off, and there were no proactive messages. The application respected that window.

After the window, proactive delivery did not resume. The saved check-ins were also generic. So the trial did not demonstrate useful, sustained, personalized teaching.

The run included restarts and model-related failures, which are recorded in the footnote. It gives evidence about an integrated path operating under those conditions, while also exposing weaknesses that component scores alone did not show.

The remaining development question is how to improve continuing support without weakening the controls that already matter.

## 28. Acceptance status against the original requirements

We can now return to the three original requirements.

For R one, correct answers, making required facts explicit improved the development cases. However, fresh-question quality still missed the acceptance thresholds. That remains a clear product gap.

For R two, appropriate support, we have evidence from guarded planning and learner simulations. But the current planner input is still a proxy, and the integrated trial showed generic or discontinued support. These results have not yet established useful personalization.

For R three, controlled operation, we have the scope correction, authority checks, and retry behavior. The full retained configuration still needs further integrated evaluation.

This status review is based on valid, corrected evidence. A protocol-invalid architecture comparison was excluded from selection.

The overall conclusion is that the project has inspectable components and working workflows, but instructor fidelity and real-student learning remain unestablished. The next development work should target these acceptance gaps rather than simply add more stages to the system.

## 29. Current best choices—and their scope

This slide summarizes the current best choices and the limits of each one.

For factual answers, retain explicit required facts and the simple retrieval control. The improvement is supported, even though fresh-answer acceptance still fails.

For the support planner, retain the guarded replacement approach with baseline A. Its evidence is a small synthetic utility gain, with a further comparison still needed to test whether model proposals add value.

For learner state, B K T and P F A are promising for different prediction targets. The highlighted cell is important: these methods are not integrated into the current planner input.

For persistent operation, retain target-specific completion and guarded saves. The available evidence supports bounded state and recovery behavior.

These choices are at different stages of validation. We should keep that visible when planning integration. Combining individually promising components changes the full configuration, and that combined configuration needs its own evaluation before we can claim a qualified best system.

## 30. Next change: replace the planner’s proxy input

My proposed next change is to replace the planner’s delivery-count input with relevant assessed evidence.

The control is the current input, which rises with messages delivered. The candidate would use committed assessments for the target concepts of the goal.

To understand the effect of that change, I would hold the planner, allowed actions, retrieval, and wording fixed. Otherwise, it would be difficult to tell which change caused the result.

The first comparison would use identical snapshots. Those snapshots should include relevant evidence, missing evidence, unrelated concepts, and conflicting evidence. This would test whether the input is interpreted correctly before running long histories.

The second stage would compare complete histories. I would measure useful and missed support, inappropriate contact, authority violations, latency, and cost.

Decision thresholds should be set before execution. We also need to evaluate the quality of the assessments feeding the candidate. A more sophisticated planner input is only useful if the underlying evidence is relevant and trustworthy.

## 31. Continuing development: evidence determines the next step

I’ll finish with the development path that follows from these results.

First, improve answer completeness and test it on fresh independent cases, including factual support and citation correctness.

Second, repair the learner-state input and use matched comparisons to check whether support decisions improve without violating the constraints.

Third, integrate accepted changes and repeat complete histories, including permission changes and failure recovery. Answer and learner-state work can proceed separately, but their combined behavior must be evaluated together.

Finally, move toward an approved course evaluation, with appropriate consent, to examine professor fidelity and student usefulness.

The project has produced a working foundation and several specific design improvements. The next objective is to turn those improvements into reliable, useful continuing support.

Thank you. I’d welcome your feedback on which acceptance gap should determine the next development priority.
