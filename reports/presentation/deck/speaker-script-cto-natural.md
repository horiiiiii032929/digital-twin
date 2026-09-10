# Course Digital Twin — read-aloud script

For digital-twin-presentation-cto-refined.pptx. Read the paragraphs. Headings and the bracketed video cue are not spoken. No narration is required during the video.

4,898 spoken words across 31 slides, plus the 4:06 video. Estimated total: 31.3–32.9 minutes at 180–170 words per minute, or 34.7 minutes at 160 words per minute. These estimates exclude extra pauses, slide changes and questions; no timed rehearsal has been performed.

## 1. Developing a Course Digital Twin

Thank you for joining me. Today, I’ll walk you through the Course Digital Twin software I developed, explain the main design decisions, and discuss what I would improve next.

The software lets a professor publish course materials and teaching settings. Students can then ask questions about the published materials. The system also keeps track of learning goals and can follow up with students later, as long as their permissions allow it.

I’ll focus on three questions. What does the software currently do? Which design choices worked best in the tests so far? And what needs to improve before students can rely on it for support over time?

There is now a working prototype, and I’ve compared several approaches to its main components. The next challenge is to make the software both reliable and useful for teaching. I’ll cover what worked and what failed, because both shaped the development decisions.

## 2. Presentation roadmap

I’ve organized the talk into six parts.

First, I’ll introduce the product and show the application running. Then I’ll explain how the software is organized, what it stores, and how it starts a follow-up.

The next two chapters cover the main design decisions. The first is how it answers course questions. The second is how it decides when to offer support and what it assumes about the learner.

After that, I’ll explain how goals, permissions, and retries are handled over time. Finally, I’ll bring the results together and explain what I would work on next.

One point to keep in mind is that the comparisons use different datasets and conditions. Each comparison supports a particular decision. We cannot simply combine the best number from every study and claim that the whole system has been validated.

## 3. Who uses the course assistant?

This diagram shows the people and systems involved.

On the left, the professor publishes materials and configures teaching policy. These materials and settings define what the assistant should use for that course.

On the right, the student asks questions, tries tasks, and receives support. The assistant in the middle uses the course information it is allowed to access. It can answer immediately or provide a follow-up later.

At the bottom is the external model provider. The software can ask it to generate a proposal or a response. The application still decides what is permitted and what can be saved.

By autonomous support, I mean that the system can start a follow-up without waiting for another question. For example, a follow-up saved after an earlier conversation may become due later.

I use the name Course Digital Twin for this configurable course assistant. We still need to evaluate how well it reflects the professor’s teaching.

## 4. Demo: course setup and 30 days of support

Before explaining the architecture, I’ll show the actual application.

The recording uses two professors, two courses, and four synthetic students. The recording advances a virtual clock, so thirty days of activity fit into a few minutes.

Please watch three things: course publication, the separate student histories, and the follow-ups that appear without a new student request.

This is the actual application. For the recording, it uses fixed, repeatable responses, so the same setup produces the same demonstration. Some preparation happened off-camera.

[PLAY VIDEO — 4 minutes 6 seconds. Let the subtitles explain the recording.]

That gives you a picture of how the application works. Next, I’ll explain the design behind it and the tests I used to assess the quality of its answers and decisions.

## 5. What has been built—and what remains open

The prototype now supports course publication, student dialogue, saved goals, and later check-ins. The next question is how well these features support learning.

For answers, specifying exactly which facts an answer needs to include worked better in the development tests. Performance on new questions is still a problem.

For support decisions, keeping a permitted baseline action worked better than losing that option when a new proposal failed. We still need to show that the resulting support is useful and responds to the individual student.

For goal completion, the software now uses evidence relevant to the goal’s own concepts. This fixed a bug that could mark the wrong goal as complete. We still need to check whether the completion rule makes sense educationally.

Throughout the talk, “current best” means the best-supported choice among the alternatives I tested, under those test conditions.

## 6. Requirements and acceptance conditions

I used these three requirements to connect the design to the tests.

The first is correct answers. An answer should include the requested facts, and those facts should be supported by the published course. I check this through answer and citation comparisons.

The second is appropriate support. The system should choose actions using the student’s goal and relevant evidence about that student. The tests of action selection and contact timing help us examine that.

The third is controlled operation. The system needs to follow the current permissions and keep its saved records consistent. That includes using evidence for the right goal, handling permission changes, and recovering safely when work is retried.

The labels R one, R two, and R three are just a convenient way to track these requirements. I’ll return to the same three labels near the end.

These requirements give us a way to judge whether the product is ready. Producing a message is only part of that. The answer or follow-up also needs to be appropriate for the student, the course, and the permissions in place.

## 7. Current local software structure

Here’s how the current local application is organized.

The web application provides the professor and student interfaces. It talks to the A P I service, which handles course setup, processing materials, tutoring, and checking whether results can be saved.

The autonomy worker handles background tasks. It checks saved activity and processes follow-ups when they become due.

Both services use information that the application has saved. The database stores dialogue, goals, and jobs. File storage holds the source materials. The model provider generates output when the selected workflow needs it.

The connection to focus on is the shared database. Information saved during a student interaction is available to the worker later. The student does not need to keep the browser open for that background work to continue.

This diagram describes the current local configuration. I haven’t established that this database or deployment setup scales better than the alternatives. That would need a separate comparison before using it more widely.

## 8. Data relationships behind continuing support

This diagram shows the main database relationships behind continuing support. I’ll focus on the connections that matter for learning goals.

An account identifies the student. A published release identifies a particular version of the course materials and settings. Both conversations and learning goals refer to the student and the release.

On the right, learner observations and concept assessments are attached to conversations. The system can use these records when it makes later decisions.

The application decides which concept assessments belong to a learning goal. There is no direct foreign key connecting these two records.

That means the application must select the correct evidence when evaluating a goal. It isn’t enough to find evidence from the same student. The evidence must also belong to the right course release and cover the concepts in that goal.

Later, I’ll show a failure where this selection was too broad. The database could store the records correctly while the application still used them to complete the wrong goal.

## 9. Two entry points into the same saved system

This sequence diagram shows how work starts in two situations. You can read it from top to bottom.

At the top, the student sends a question or an answer to a task. The service handles it, checks that the current permissions still allow it, and saves the response.

In the lower half, some time has passed. The worker finds a follow-up that is due and asks the service to process it. This can happen without another message from the student.

Being due doesn’t automatically mean that a follow-up should be sent. The goal, available evidence, consent, and schedule must still permit the action. The outcome can be a saved support message or a decision to take no action.

In both cases, the system checks permission again before saving the result. That matters because permissions can change while the work is running.

That’s how the system follows up on its own: it returns to saved work later, checks the current conditions, and decides whether to act.

## 10. Current factual-answer path

Now let’s look at how the system answers a course question.

The current factual-answer path begins by loading the published course and the sources that the student is allowed to use.

It then ranks evidence using B M twenty-five, a keyword-based retrieval method. In simple terms, this stage helps identify source passages that match the question’s words.

The blue step is where the answer is put together. The system checks the evidence and selects the facts the answer needs. This part follows fixed rules in the current version.

If the evidence is unclear or insufficient, the system should ask for clarification or say it cannot answer. A successful answer is saved with references to its sources.

A key design question is what the system considers sufficient evidence. Finding a passage is only one part of the task. The answer still needs to include all the facts requested by the question. Here’s a simple example of why that matters.

## 11. Finding the source does not complete the answer

Suppose the student asks, “List all three stages.” The retrieved source says, “The stages are draft, review and publish.”

Now look at the answer on the left. It says, “Draft and review.” Both items are supported by the source, but the answer leaves out publish.

The answer on the right includes all three stages. It satisfies both requirements: the items are supported, and the requested set is complete.

This gives us a more precise way to check the answer. For this question, we need a list of stages, we need three items, and we need draft, review, and publish. Making those requirements explicit lets the system check whether the answer actually contains what the student asked for.

## 12. Why the more complex answer paths failed

I also tested more complex ways of producing an answer. These diagrams show where two earlier approaches ran into trouble.

The simple control retrieves a keyword match and extracts a response. The middle approach uses hierarchical retrieval. The approach on the right breaks the task into parts, retrieves evidence, and combines the results.

The orange steps show the shared problem in the two more complex paths. Both tried to check the wording of the whole question too broadly. As a result, they could reject a question even when the evidence contained the facts needed to answer it.

Adding retrieval and planning steps didn’t fix that problem. Both approaches still used the same overly broad check to decide whether the evidence was sufficient.

That led to the change I just described: specify the facts the answer needs, and check for those facts directly.

This finding is specific to these tested paths. It does not show that hierarchical retrieval or more structured architectures are generally ineffective.

## 13. Explicit answer facts improved the same 397 cases

The next comparison tested that change on the same three hundred and ninety-seven answerable cases.

With the original rule, the system produced two hundred and fifty-three grounded answers. With explicit required facts and item counts, that increased to three hundred and fifty-five.

The third bar shows an additional section-ranking stage. It also produced three hundred and fifty-five grounded answers.

The extra stage did increase the measured latency. The ninety-fifth percentile rose from about one point four to about two point eight milliseconds. That measure describes the time within which ninety-five percent of the measured requests finished.

Based on this comparison, I kept the explicit fact requirement. The extra ranking stage took more time without producing more correct answers.

Of course, the next question is whether that improvement holds up on new questions.

## 14. Fresh answers still missed the acceptance thresholds

When I tested new questions, there was still a substantial gap to the acceptance criteria.

This comparison used eight hundred answerable questions and two hundred cases requiring refusal or clarification. The blue bars show the two methods. The gray bars show the required thresholds.

On the left, the keyword-based control produced complete, supported answers in sixty-three point two five percent of the answerable cases. Hybrid retrieval reached sixty-two percent. Both were well below the ninety-five percent requirement.

On the right, the control correctly refused or clarified in ninety-six percent of boundary cases. The hybrid path reached ninety-five percent. Both missed the ninety-eight percent threshold.

The hybrid method adds semantic retrieval, but the two paths share the answer check. Adding that retrieval method didn’t bring the results up to the required standard.

For now, these results support keeping the simpler method and improving answer quality. It helped on the development cases, but the results on new questions are still below the standard the product needs to meet.

## 15. Better retrieval or wording did not ensure correct answers

I also looked at visual retrieval and wording revision in two separate studies. Both show why we need to check the final answer, even when an earlier step improves.

On the left, visual retrieval found more relevant evidence. The result improved from eighteen to twenty-eight out of thirty. However, grounded answers stayed at twenty out of thirty in both conditions. Better evidence retrieval did not produce more complete, supported answers.

On the right, a wording revision changed the meaning of the source. The source says that exactly two seals are required. The revision says that two seals guarantee acceptance. A requirement has become a guarantee, which the source does not support.

The tested revisions fixed many flawed drafts and preserved the drafts that were already adequate. Even so, a critical error remained.

These were separate studies, so I am not combining their numbers. They support the same development lesson: evaluate the final answer after every stage. Retrieval quality and fluent wording are useful, but neither one establishes answer correctness by itself.

## 16. Current support planner: retain an allowed fallback

Now I’ll turn to autonomous support: how the software decides what to do after the original interaction.

The planner selects an action. A separate generator writes the selected message. So choosing the action and writing the message are separate steps.

Starting on the left, the planner checks whether it is allowed to use the evidence. If not, it takes no action.

If it can use the evidence, the planner starts with a permitted baseline action, called A. It keeps that option available while evaluating a proposed replacement.

The proposal only replaces the baseline when the replacement conditions pass. These include permission and validity checks, analytic support, and a predicted gain of at least zero point zero four.

If the proposal fails those checks, the planner falls back to A.

The idea is to keep a usable option available. An unsuitable proposal shouldn’t make the system lose an action it was already allowed to take. The earlier designs help explain why I chose this approach.

## 17. Why reject-only verification was not retained

These earlier designs used the same permission constraints but chose actions in different ways.

The first design, fixed rules A, provides a predictable baseline. It has limited flexibility, but it also gives us a clear control for comparison.

The second adds a model proposal and lookahead. It adds steps for proposing actions and estimating their value. In the earlier comparison, those stages did not beat A on the evaluation score.

The third adds a reject-only verifier. This can identify a proposal that should not be used, but rejection by itself does not provide a better action. It can remove a usable choice without replacing it.

The highlighted design, guarded replacement H, keeps A unless another proposal qualifies.

The question is whether a proposal is good enough to replace the baseline. To test that, I looked at whether the chosen actions followed the rules and how much value they produced in the evaluation.

## 18. Guarded replacement slightly improved simulated utility

I then compared rules A and guarded H on the same one thousand contexts.

The mean utility was about zero point seven nine five for A and zero point eight zero zero for H. The paired gain was approximately zero point zero zero four eight. The ninety-five percent confidence interval for that gain was above zero.

That is a small positive gain. To interpret it, we need to be clear about utility. Here, a separate evaluator scores the chosen action using simulated learner outcomes. This score is different from the planner’s prediction, and it doesn’t measure learning by real students.

Both methods obeyed all tested action rules. The extra steps required calls to the model provider, and some of those calls failed. The cost and failures are recorded at the bottom of the slide.

There’s also a comparison I still need to make. What happens if we use the analytic scoring method to choose the best action directly, without first asking a model for a proposal?

The result is encouraging enough to keep testing guarded replacement. It still leaves open whether the model proposal is needed and whether the small gain would help students in practice.

## 19. The planner input can rise without a new answer

There’s another issue with the planner: the information we give it before it makes a decision.

The current input adapter calculates a probability from the number of messages delivered. The formula is the delivery count plus one, divided by the delivery count plus two, with an upper cap.

Before any delivery, the value is zero point five. After one delivery, it rises to about zero point six seven.

Notice the line below the two values. There are no new assessed answers in either case. The number went up because the system sent a message. The student hasn’t demonstrated any new understanding.

That makes the number a weak indicator of what the student knows. The planner may change its decision in response to its own activity, even when there is no new evidence from the student.

This is why I looked at alternatives based on assessed answers. Just to keep the two mechanisms clear, goal completion already uses assessed evidence. The problem here is the input to the planner.

## 20. Learner models: what they estimate and how we test it

Here are the three methods I compared using assessed answers. They were tested separately and haven’t yet been connected to the current planner input.

The first is a simple count baseline. It estimates knowledge from the assessed answer history.

B K T stands for Bayesian Knowledge Tracing. It updates the probability that a student knows a concept after each correct or incorrect attempt.

P F A stands for Performance Factors Analysis. It uses the history of successes and failures to predict the probability of the next correct answer.

The two measures below test different things. Mean squared error compares an estimate with the simulator’s hidden knowledge. The Brier score compares a predicted answer probability with the observed answer outcome. Lower is better for both.

A better estimate of hidden knowledge doesn’t necessarily give us a better prediction of the next answer. That’s why I report both measures. The method we choose should depend on what we need it to predict.

## 21. The best estimator depends on the prediction task

This study used two hundred and forty synthetic learners per condition, across two simulator families, over thirty days. I kept the contact schedule the same while comparing the estimators.

On the left, B K T has the lowest mean squared error: zero point zero three five, compared with zero point zero eight four for Count. The reported paired confidence interval supports an improvement in estimating hidden knowledge.

On the right, Count and B K T both round to a Brier score of zero point two five nine. P F A reaches zero point two four nine, with a paired confidence interval supporting an improvement against Count.

So there isn’t one winner for every purpose. B K T is promising for estimating knowledge, while P F A is promising for predicting the next answer.

## 22. Contact timing changes messages and simulated knowledge

I also used the simulation to compare when the system contacts the student.

This time, I kept the count estimator the same and changed the contact rule. Constant timing sends support at every eligible check. Conditional timing waits for signs that support may be needed. Value-based timing requires enough predicted benefit before sending a message.

On the left, conditional timing reduces the mean number of messages from fourteen to seven. That looks good if we only count the messages.

But the right-hand chart shows the tradeoff. Mean hidden mastery at day thirty falls from zero point three one four to zero point three zero two. In this simulation, fewer messages also came with lower knowledge.

Value-based timing produced a different balance. Of the feasible combinations tested, B K T with value-based timing had the highest average mastery at day thirty.

So I would look at both useful support and missed opportunities. Fewer messages may be better for the student, but we need to check whether that also means missing support they could have benefited from.

## 23. A goal outlives a single background job

Next, I’ll look at how the software keeps its records correct over time.

An active goal can lead to background jobs, such as attempts to send support. Those jobs have limits on how much work they do. Sending a message increases the attempt count. Reaching an attempt limit does not mean that the learning goal has been achieved.

The state diagram shows three ways to leave the active state. A goal can be marked complete when the evidence passes for all its target concepts. It can expire when its expiry condition is met. It can also be cancelled, for example when its scope is no longer valid.

For each target concept, completion requires at least two correct attempts, no incorrect attempts, and sufficient confidence under the software’s rule.

These are the software’s current thresholds. They haven’t been validated as measures of mastery. What I’m checking here is whether the system applies them to the right concepts. A correct answer on an unrelated topic should never complete this goal, even if it comes from the same student.

## 24. Target-specific evidence removed false completions

Here’s an example of that problem in the earlier version.

Correct answers about cache coherence could also complete a virtual-memory goal that had not been assessed. The student and course release matched, but the concepts did not.

The chart compares the old rule and the corrected rule on seventy-two matched synthetic histories per version. Blue shows supported completions. Orange shows unsupported completions.

The old rule produced fourteen supported completions and twelve unsupported ones. After the target-scope correction, there were fifteen supported completions and no unsupported completions in this comparison.

That supports keeping the correction. The system now uses evidence about the right concepts when it decides whether a goal is complete.

However, it does not establish an educational gain. In the part of the evaluation that tested autonomous behavior, the correction led to fifty-six more messages. Simulated mastery was slightly lower.

So there are two things to test: whether goals are recorded correctly and whether students receive useful support. Fixing false completions matters for reliability. The extra follow-ups that result from that fix still need to prove their value.

## 25. Authority can change while an answer is generated

Permissions can also change while the system is working on an answer.

In this sequence, the tutoring service first reads the current release and state. It begins generating a response based on that information.

Before the response is saved, the professor withdraws the release. The system is no longer allowed to use that release to save the answer.

At step three, just before saving, the service checks the current authority again. It detects the change, rejects the outdated work, and saves no answer.

Generation runs outside the write transaction. The system doesn’t hold a write transaction open while it waits for generation. Because of that gap, it needs to check the conditions again before saving.

The same issue can arise if the saved learner state changes. The system checks its revision so it doesn’t apply an update based on outdated information.

The rule is simple: checking permission at the beginning isn’t enough. The system must still have permission, and a valid view of the relevant state, when it saves the result.

## 26. A retry reuses the message already saved

This example shows what happens if the worker stops at an awkward moment: the message has been saved, but the job hasn’t been marked complete.

At step one, the worker processes a delivery with key K. At step two, the delivery service saves the message for that key.

The worker then stops. After restarting, it retries the same key, because the job was not recorded as complete.

The service looks up the message associated with K and returns the saved message. It does not need to create a second in-app message for the same delivery.

Using the same key lets the service recognize that this delivery has already happened. That is how this retry avoids creating a duplicate message in the application.

This guarantee applies to the local workflow shown here. If we later send messages through an external service, we would need to check how that service handles retries too.

These last two examples show why background support needs clear rules about saving results. We need to handle both changing permissions and work that runs again after a failure.

## 27. The integrated trial exposed weak continuing support

I also tested the application over longer histories, making actual calls to an external model.

This trial was separate from the demo. It used twenty-four synthetic histories over thirty virtual days. The totals were four hundred and eighty-four tutor turns, six hundred and fifty-four model calls, sixteen proactive messages, and ten synthetic replies.

During days ten to nineteen, consent was off, and there were no proactive messages. The application respected that window.

After that window, follow-ups didn’t resume. The check-ins that had been saved were also generic. So the trial showed a delivery mechanism, but it didn’t demonstrate sustained, useful support tailored to the student.

Running the components together revealed problems that weren’t obvious from their individual test scores.

That leaves a clear development question: how can we make the follow-ups more useful and consistent while preserving the permission and recovery checks?

## 28. Acceptance status against the original requirements

We can now return to the three original requirements.

For R one, correct answers, specifying the required facts improved the development results. But answers to new questions still fell below the acceptance thresholds. Answer quality remains a priority.

For R two, appropriate support, we have evidence from guarded planning and learner simulations. But the current planner input is still a proxy, and the integrated trial showed generic or discontinued support.

For R three, controlled operation, we have the scope correction, authority checks, and retry behavior. We need to test these choices further as part of the full application.

I’ve based these conclusions on the valid, corrected results. I excluded an architecture comparison because it didn’t follow the evaluation protocol.

We have working workflows and components whose behavior we can inspect. We still need to show how well the system reflects the professor’s teaching and helps real students learn. Those are the gaps I would use to guide the next stage of development.

## 29. Current best choices—and their scope

Given those results, these are the choices I would keep or investigate next.

For factual answers, I would keep the explicit fact requirements and the simpler retrieval method. They have the strongest support here, although answer quality still needs to improve on new questions.

For the planner, I would keep guarded replacement with baseline A. It produced a small gain in simulated utility. I would also run the missing comparison to check whether the model’s proposals add value.

For learner state, B K T and P F A are promising for different prediction targets. These methods are not integrated into the current planner input.

For operation over time, I would keep the goal-specific evidence checks and the checks before saving. They address the state and recovery problems shown earlier.

Some of these choices are already part of the software; others are promising candidates. When we combine accepted changes, we need to test the whole application again. Good results for individual components don’t automatically carry over to their combination.

## 30. Next change: replace the planner’s proxy input

The next change I would test is replacing the planner’s delivery count with evidence from assessed answers.

The control is the current input, which rises with messages delivered. The new version would use saved assessments that cover the concepts in the student’s goal.

To understand the effect of that change, I would hold the planner, allowed actions, retrieval, and wording fixed.

The first comparison would use identical snapshots. Those snapshots should include relevant evidence, missing evidence, unrelated concepts, and conflicting evidence.

The second stage would compare complete histories. I would measure useful and missed support, inappropriate contact, authority violations, latency, and cost.

Before running the tests, I would decide what results are good enough to accept the change. I would also check the assessments themselves. A better input method won’t help if the evidence behind it is wrong or unrelated to the goal.

## 31. Continuing development: evidence determines the next step

To finish, here are the four areas I would focus on next.

First, improve answer completeness. Then test it on new, independent questions, checking both the facts and the citations.

Second, improve the learner-state input. Compare the old and new versions on the same cases to see whether decisions improve while still following the rules.

Third, bring the accepted changes together and test complete histories again, including permission changes and failures. Answer quality and learner-state work can develop separately, but we need to test how they work together.

Finally, prepare for an approved course evaluation, with the appropriate consent. That would let us examine how well the system reflects the professor’s teaching and how useful students find it.

The project now has a working foundation and several improvements supported by the tests. The next step is to make those improvements work together as reliable, useful support over time.

Thank you. I’d be interested to hear which of these remaining gaps you think we should focus on first.
