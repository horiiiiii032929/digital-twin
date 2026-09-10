# Read-aloud script for the audited presentation

Read the paragraphs. Headings and the single video cue are navigation aids. Main talk: slides 1–31. Questions: 32. Optional backup responses: 33–49.

## 1. An Instructor-Configurable Course Digital Twin

Thank you for joining me. Today, I'll present the course Digital Twin prototype and the design decisions behind it.

The starting point was to connect a professor's course materials and teaching preferences to a system that can support students over time. That includes answering questions, but also following up when a student hasn't asked another question.

I'll begin with what the software currently does and show a recording of it in use. Then I'll explain the designs I tried, where they failed, and how those findings changed the implementation. I'll finish with the remaining gaps and the next comparison I would run.

## 2. A course assistant configured by the professor

Let me start with the interaction this software supports.

The professor provides the course materials and teaching settings, reviews them, and publishes the course assistant. The student then uses that published course to ask questions or submit attempts.

The application answers using the course material. The separate lanes show who is responsible for each step. The professor controls the approved course, the application produces the response, and the student decides what to ask or attempt.

This is the ordinary question-and-answer part of the system. The same course context also carries forward into continuing support. The application can retain observations and goals after the conversation ends.

The next page shows a concrete example of what that allows. It's the same student before and after a scheduled follow-up.

## 3. A follow-up arrives without another question

These are two cropped frames from the actual recording, both for student B1 on virtual day three.

On the left, the student has stopped typing and the inbox has no check-ins. On the right, a follow-up has arrived from the system.

The student didn't send another question between those events. The recording environment advances virtual time, and the application processes the work that becomes due. The resulting message appears in the student's inbox.

That's the autonomous behavior I want to make visible: the system can start the next contact using its saved state and scheduled work.

This example establishes that a message was delivered. It doesn't show that the software diagnosed a particular misunderstanding or that the advice improved learning. We'll examine those quality questions through the later studies.

Now I'll show the wider workflow, including setup and the controls around support.

## 4. Demo: setup, student interaction and follow-up

I'll now show the software running with two professors, two courses, and four synthetic students.

The recording begins with setup and access, then advances through thirty virtual days. The main thing to watch is what happens after a student stops typing. The software processes scheduled work and sends support without receiving a new question.

You'll also see how a professor can pause support and how a student's consent affects delivery.

This recording uses an isolated environment, an accelerated clock, and deterministic services. It shows the actual application, while the student activity is simulated. It is separate from the historical evaluation that used external models.

[VIDEO CUE — play the video; remain silent for 4 minutes 6 seconds]

That shows the operating loop. The system can initiate support and retain the result. Now I'll show the components behind that workflow, then examine the decisions that were tested.

## 5. The components behind answers and follow-ups

This diagram connects the workflow you just saw to the parts of the software that were compared.

At the top are the tutoring and scheduled-support services. They check permission and save the result. The components below perform more specific jobs.

The evidence selector finds the course facts needed for an answer. The input adapter prepares the learner information that the planner receives. The action planner chooses the next support action. The wording generator writes the text the student sees.

These are separate boundaries. A change to how the system finds evidence doesn't automatically fix how it chooses a follow-up or writes that follow-up.

The studies therefore compare particular components while retaining the relevant shared controls. They don't form a single ranking of every possible complete system.

Before the technical comparisons, I'll show how a teaching preference appears in a saved response. That gives us a concrete way to distinguish a setting reaching the software from the resulting instruction being useful.

## 6. The tutor asks for an attempt, but stays generic

Different instructor settings have different roles.

Source permissions determine which evidence the tutor can use. Approved objectives limit what its goals can cover. Action permissions and student consent restrict what support it can deliver. The application enforces those controls.

Teaching preferences work differently. Tone, explanation depth, and the sequence of help enter the generation process. To find out whether those preferences work, we need to examine the response a student receives.

In this saved example, the Socratic profile asks for a diagnostic question, a student attempt, and then one hint. The student asks about a concept called slot seal in the synthetic course protocol. The tutor asks for the student's current explanation and the part they are unsure about.

That follows part of the requested sequence. But the question is still generic. It doesn't identify the student's particular conceptual difficulty.

A stronger test would hold the student question, course evidence, and learner state fixed, then vary only the approved teaching profile. An independent review could then assess the differences. That comparison remains to be done.

## 7. Three kinds of evidence, with different claims

This table separates three kinds of evidence used in the presentation. Each answers a different question.

The video you just saw is a new software demonstration. It uses synthetic student inputs and a virtual clock. The product services create goals, choose actions, and save messages.

The historical operational study also uses synthetic students and virtual time. However, it calls the configured external model through the tutoring and autonomy services. Its student driver controls attendance and constructs replies according to the simulation settings. Those replies are generated behavior, rather than observations from a classroom.

The learner-model study has a different purpose. It maintains a hidden learner state that the evaluator can use to score estimates and intervention outcomes. It doesn't run the text retrieval and generation pipeline.

This distinction matters when we interpret a result. A better estimate of hidden knowledge in the learner simulation doesn't establish that the application produces better explanations. Likewise, successful delivery in the video doesn't establish that the delivered advice improves learning.

I'll keep those boundaries explicit as we move through the findings.

## 8. Finding the source does not guarantee a complete answer

This small example illustrates the distinction. It isn't a quoted test case.

Suppose a question asks for three stages. The retrieved passage contains all three: draft, review, and publish.

An answer that says only draft and review is supported by the passage. But it still fails the question because it leaves out publish.

That gives us two separate checks. Did retrieval find the necessary evidence? And did the final answer include every required fact?

The revised design represents the target explicitly, including the type of answer and the number of facts needed. The response path can then check whether it has supplied all three stages.

This is also why a high retrieval score later in the presentation can coexist with a much lower answer score. Finding the right passage is only one step toward producing a complete answer.

## 9. Two answer paths shared the same faulty evidence check

The first comparison examined three ways to answer factual questions from course material.

The simple control used lexical retrieval, which matches words in the question to words in the source. It then extracted a response from accepted evidence.

The hierarchy design added structure to the evidence search. The plan-and-observe design added explicit retrieval steps. Both eventually passed through a check that required coverage of the whole question.

That shared check turned out to be the problem. It treated some words used to frame the question as facts that the evidence needed to contain. As a result, it could reject a passage even when the passage contained the answer.

The diagram shows why this failure affected both of the more complex paths. They added different mechanisms earlier in the process, but both relied on the same faulty acceptance rule.

The next chart shows how much that rule reduced answer coverage.

## 10. The shared check rejected many answerable questions

All three designs received the same development cases.

There are two useful measures here. A grounded answer contains the required claims and supports them with evidence. Answerable action measures whether the system actually answers when sufficient evidence is available.

The lexical control answered every answerable case, although only about fifty-three percent of its answers were fully grounded. Both complex paths fell to about twenty-five percent grounded accuracy. They answered only about thirty-six percent of the answerable cases.

The shared coverage check explains the regression. It rejected useful evidence because the evidence didn't match words that belonged to the question's framing.

Boundary handling remained perfect in this development comparison. So the designs could avoid answering outside their boundary while still failing to answer many questions they should have answered.

The response was to change the answer requirement itself. Before adding more retrieval steps, the system needed a clearer definition of which facts the answer must contain.

## 11. Stating the required facts improved answers

On this development fold, the lexical control produced two hundred and fifty-three fully grounded answers out of three hundred and ninety-seven answerable cases.

The design with an explicit target and fact count increased that to three hundred and fifty-five. Adding a section-ranking stage produced exactly the same count.

The extra ranking also increased local retrieval latency. The ninety-fifth percentile rose from about one point four to two point eight milliseconds. That percentile tells us how long ninety-five percent of the measured requests took to finish.

The absolute times are small, but the decision is still clear within this comparison. The added stage increased processing time without improving answer quality.

The explicit target was useful, but it didn't solve every case. Errors remained around paraphrased targets, neighboring source regions, and missing answer spans. No candidate passed every quality requirement.

These are results from one development fold. We shouldn't connect numbers from different datasets into a single improvement curve. The next slide moves to a separate test on fresh sources.

## 12. Evidence was usually found; complete answers still failed

The fresh test included eight hundred answerable cases and two hundred boundary cases.

The retained keyword-ranking method is called BM25. The other configuration combines keyword and semantic retrieval. Both use the same dominance gate to choose between competing interpretations of the evidence.

For BM25, the top three retrieved results contained all the required evidence in ninety-eight percent of answerable cases. However, only about sixty-three percent of final answers were fully grounded. The hybrid scored sixty-two percent.

That is the main gap on this slide. The evidence was usually available, but the final response often failed to include all the required claims with the required citation support.

BM25 handled one hundred and ninety-two of the two hundred boundary cases correctly, or ninety-six percent. Both configurations fell short of the stated acceptance gates.

There are also limits to the test. The questions were mechanically generated, and some were malformed. The scorer uses explicit targets and source ranges, which makes it inspectable but less flexible about meaning. The confidence interval shown here describes sampling uncertainty, not all of those limitations.

BM25 remained the simpler local fallback. The small difference from the hybrid doesn't establish general superiority. The larger finding is that better retrieval alone hadn't resolved the final-answer problem.

## 13. Visual retrieval improved, but final answers did not

The visual comparisons showed a similar problem.

In one historical study, the number of cases with relevant visual retrieval rose from eighteen to twenty-eight out of thirty. Yet the number of grounded answers stayed at twenty.

In a separate fresh comparison, the image-capable candidate produced sixteen grounded answers, while its control produced twenty-six. That candidate was dropped.

These are separate studies, so the bars shouldn't be read as successive steps in one experiment. What they share is a gap between finding useful material and using it correctly in the answer.

An image can contain relevant evidence, but the response still needs to interpret it and include the required supported claims. The richer input didn't automatically improve that final step.

So far, I've focused on answering questions. I'll now turn to the planner, which decides what support action the system should take.

## 14. A verifier could reject an action without replacing it

The planner candidates are labeled A, B, and C in the project records.

A is the deterministic rule baseline. B asks a model to propose an action. C adds analytic lookahead, which estimates the consequences of candidate actions. The final variant adds a model verifier after C chooses an action.

All of them still face the same permissions and delivery rules.

The comparison didn't show a simple progression where each extra stage improved the result. On the development fold, A had the best registered utility. C agreed more often with the preferred-action label, but its utility was lower. Those measures capture different properties.

The verifier exposed a specific composition problem. It could reject a usable action, and the rejection branch then returned no action. It neither selected another useful move nor restored the baseline.

A later audit also corrected how some scores had been described. Agreement with a preferred label had been confused with action validity. That limits the earlier interpretation.

The useful design lesson was to preserve an allowed baseline when a replacement fails. That's the change in the next diagram.

## 15. A rejected proposal now keeps the baseline action

This design is labeled H. It starts by computing the deterministic baseline action.

If there is no authorized evidence, the system takes no action. If evidence is available, a model can propose a replacement.

The proposal has to pass several conditions. It must be valid and permitted. It must match the best action identified by the analytic comparison. Its estimated value gain must also reach the configured margin, which is zero point zero four.

If any of those conditions fails, H keeps the baseline.

The change is in what happens after a weak or rejected proposal. The previous verifier could leave the system with no useful move. This composition retains a known alternative whenever replacement isn't justified.

That makes the fallback behavior explicit and testable. It still leaves an empirical question: does this guarded replacement improve the selected actions enough to justify its additional model calls?

## 16. Guarded replacement gave a small simulated score gain

The confirmation found a small gain in registered evaluation utility.

The average paired improvement was about zero point zero zero four eight. The ninety-five percent confidence interval stayed above zero for these synthetic contexts. So the direction was consistent enough to support that narrow finding, although the size of the gain was small.

Both methods obeyed the tested action rules. Agreement with the preferred-action label moved from seventy-four to seventy-three percent, with an interval that included zero.

Utility here is a value assigned by the synthetic evaluation. It is separate from the heuristic used to rank proposals at runtime, and it doesn't measure student learning.

The run recorded eight hundred and one provider calls, including four failed calls. The reported total cost was about thirty-four US cents. Those are historical run totals.

This result supported moving to the next comparison. One important control is still missing: directly selecting the analytic best action without the model proposal. We need that comparison to isolate what the model contributes.

## 17. Estimate the learner’s knowledge, then decide when to send

The learner experiment separates estimating knowledge from deciding when to send support.

On the left are the knowledge estimators. The count baseline uses a smoothed proportion of correct attempts. It doesn't forget older evidence.

BKT stands for Bayesian Knowledge Tracing. It maintains a probability that the learner knows a concept and updates that probability after an answer. It allows for a correct guess, a mistake despite knowing, learning, and forgetting.

PFA stands for Performance Factors Analysis. It predicts success from earlier correct and incorrect attempts. In this implementation, older evidence receives less weight.

These estimators consume assessed correctness records. They don't read the student's text themselves.

On the right are the timing policies. Constant timing sends at each eligible check. Conditional timing waits for a stalled state or knowledge that is low and uncertain. Value-based timing sends only when the estimated benefit passes a threshold.

The experiment crosses these choices. That lets us ask whether a result comes from the estimate, the timing policy, or their combination.

## 18. Knowledge estimates and next-answer predictions are different

Each condition contains two hundred and forty simulated learners. They come from six personas, two simulator families, and twenty test seeds. A seed makes a random sequence reproducible. The parameters were selected using separate development seeds.

The first measure is mean squared error, or MSE. It compares the estimated concept knowledge with the simulator's hidden knowledge state.

The second is the Brier score. It checks the probability prediction made before an answer against whether that answer was correct or incorrect. Lower is better for both measures, but they test different targets.

The small calculations on the slide illustrate the difference. If a knowledge estimate is zero point seven and the hidden state is zero point eight, the squared error is zero point zero one. If the probability of a correct answer is zero point seven and the next answer is correct, the squared error is zero point zero nine. These are illustrative numbers, not results from the experiment.

The study also counts messages and wasted contact. Here, contact is classified as waste when hidden mastery is already high or the learner is unreceptive. All methods share the same consent and timing restrictions.

The uncertainty intervals resample learners. However, a new seed only changes a trajectory within the chosen simulator families. It doesn't test a new theory of learner behavior.

The count baseline also has no fitted parameters or forgetting, while the alternatives do. That makes a stronger simple control necessary before drawing broader conclusions.

## 19. BKT improved estimates of hidden simulator knowledge

Here the timing policy is held constant, so both methods send the same average number of messages.

On the left, BKT reduces hidden-state error from zero point zero eight four to zero point zero three five. The paired interval excludes zero.

On the right, the rounded Brier scores are both zero point two five nine. The interval for their difference includes zero.

So BKT estimated the hidden simulator state more closely, but this comparison didn't establish better prediction of the next observed answer. The two charts answer different questions, and we need both to interpret the result.

The hidden-state improvement appeared in both tested simulator families. That helps, but both families still reflect assumptions chosen for this study. One is itself similar to BKT.

Before strengthening the claim, I would add a count baseline that discounts old evidence and a third simulator family. BKT remains an experimental candidate outside the default application adapter.

Next, I'll hold the estimator fixed and look at timing.

## 20. Halving messages also reduced simulated knowledge

With the count estimator fixed, conditional timing reduces average messages from fourteen to seven.

That looks attractive if we focus only on the amount of contact. But average final hidden mastery also falls, from zero point three one four to zero point three zero two. The paired interval excludes zero within this simulator.

Value-based timing sends about ten messages. It retains more contact than the conditional policy and has a lower fraction of wasted messages. Its mean final hidden mastery is about zero point three one seven.

The tradeoff matters. Sending less can remove unnecessary interruptions, but it can also remove useful practice opportunities.

These values describe the simulator's hidden state. They haven't established a real-course learning effect. The fuller comparison is available in backup, including combinations with BKT and PFA.

The next slide returns to the application. It shows why these learner-model results don't automatically translate into better planner inputs in the product.

## 21. Sending a message raises the planner’s “mastery” input

The current input adapter uses deliveries and event identifiers to prepare the planner's state.

One field is named mastery probability. After a single delivered goal action, it rises from one half to two thirds, even if the student hasn't submitted a new answer. That makes it an indirect proxy based on activity.

Goal completion uses a separate path through committed concept assessments. So the product has assessment records, but the default planner doesn't yet receive the learner estimate tested in the simulation.

This matters for interpreting the planner comparison. That experiment supplied state cards directly. It therefore evaluated decisions made from those cards, without validating the adapter that constructs them in the application.

The gap may contribute to poorly targeted support. I can't claim it explains every generic message, because that cause hasn't been isolated.

The next useful comparison would replace the proxy with committed evidence for the goal's own target concepts, while keeping the other components fixed. Before describing that proposal, I'll show two more failures involving how evidence affects a final output or state decision.

## 22. The revision turned a requirement into a guarantee

The wording comparison tested whether revision could preserve adequate drafts and repair defective ones.

Both candidates preserved all fifty-six adequate drafts. Both repaired forty-seven of fifty-six defective drafts. However, each left one critical error, so neither passed the requirement of zero critical errors.

The example on this slide concerns a necessary condition. The source says that exactly two seals are required. The added example goes further and guarantees acceptance when two seals are present.

That guarantee doesn't follow from the source. Other conditions may still be required.

The output can therefore look fluent and well structured while changing the meaning of the rule. The decision was to keep both revision candidates from promotion.

These were bounded assessments of drafts, with AI assistance in the evaluation. They don't establish student learning. The specific finding is that structural compliance left a critical semantic failure unresolved.

The next defect concerns a similar evidence boundary, but in goal completion rather than wording.

## 23. Evidence for Topic A incorrectly completed Topic B

This was one of the clearest implementation failures.

Two goals were active, one for cache coherence and one for virtual memory. I'll call them Topic A and Topic B. After two correct attempts on Topic A, the old system completed both goals. Topic B had no assessment evidence.

The stored assessments could be correct. The completed statuses could survive a restart. Yet the decision about Topic B was still wrong.

The table shows the consequence for each goal. The old logic used strong concept evidence too broadly. It didn't require that evidence to belong to the particular objective being completed.

The correction checks each goal against committed evidence for every one of its target concepts. Missing or ambiguous mappings keep the goal incomplete. The retained rule requires at least two correct assessments per target, no incorrect assessments, and sufficient evidence confidence.

That fixes the scope problem, but the rule itself remains limited. An earlier incorrect assessment can still block completion. A completed status records satisfaction of this software condition, rather than validated mastery.

The regression therefore needed to connect the goal, its target concepts, and its evidence. Persistence checks alone couldn't catch this failure.

## 24. The correction removed all 12 unsupported completions

The comparison ran seventy-two histories in each arm. It kept the driver, concepts, seeds, and dependencies the same. Planning and wording were deterministic, and there were no external model calls.

The old implementation completed twenty-six goals. Fourteen had support from their target concepts, and twelve did not. The corrected implementation completed fifteen, all supported under the tested rule.

Both arms passed the reported restart and assessment checks. That helps explain why the separate completion defect had survived those earlier tests.

The correction also kept more goals active. Across the autonomous histories, it produced fifty-six additional messages. Mean final simulated mastery changed slightly downward, and waste increased slightly.

The reason to retain the correction is that a goal without relevant evidence should remain incomplete. The result doesn't support a learning-improvement claim.

There is another limit here. The independent audit checks compliance with the same authored completion rule. It doesn't validate the educational meaning of that rule or the correctness of every assessment. Zero unsupported completions refers to these tested histories.

The state decision improved. The usefulness of the extra support still needs evaluation.

## 25. Permission can change while an answer is being written

I'll now explain two boundaries that protect the stored state during normal operation and recovery.

First, permission can change while a response is being generated. A professor might withdraw a release, or a student's access might change after the initial check.

The application generates the candidate response outside the write transaction. Before saving it, the application checks current authority again. It also checks the expected state revision, so a result based on old learner state can't silently replace a newer state.

When the turn is accepted, the response, citations, and learner update are saved together.

Read the sequence from top to bottom. The final exchange is the boundary between preparing a response and committing its effects. Passing an earlier check doesn't authorize a later save after permission has changed.

These are local consistency and permission requirements. They don't establish that this deployment topology is better than a distributed alternative. The evidence supports the specific behavior under test.

The second boundary concerns a worker that stops after saving a message.

## 26. A retry must find the message that was already saved

Imagine that the worker saves a proactive message and then stops before recording that the job has finished.

After the worker's lease expires, another worker can claim the job. But the lease doesn't tell it whether the message already exists.

Recovery therefore uses a stable delivery key. When the worker retries with the same key, it finds the saved message and finishes the job bookkeeping without sending a second in-app message.

The crash window is after the message save and before the job-result save. The lower part of the diagram shows the retry after restart. The repeated key is what connects recovery to the effect that already happened.

Permission checks still apply. Reusing an identity doesn't create permission to deliver new content.

This guarantee covers the tested local persistence path. It doesn't promise exactly-once effects across every external provider. If an external outcome is uncertain, recovery needs to account for that uncertainty before repeating an effect.

With those mechanisms in place, the next question was how the historical integrated configuration behaved over a simulated month.

## 27. The system ran, but its follow-ups remained generic

The historical trial ran twenty-four synthetic histories across thirty virtual days. It used actual external model calls through the application services.

It processed four hundred and eighty-four tutor turns, delivered sixteen check-ins, and exercised twenty-four service restarts. Consent was disabled during virtual days ten through nineteen. No proactive messages arrived during that interval.

The run also recorded failures. Eleven of the six hundred and fifty-four model calls reached the output limit. Thirteen tutor turns ended in a safe graph failure.

The main quality limitation was that every check-in remained generic. All sixteen appeared before day ten, and proactive delivery didn't resume later in the run. The system could initiate and preserve support, but this trial didn't demonstrate sustained, well-targeted intervention.

A later diagnostic reviewed selected responses and failures. Because that sample was deliberately selected, it can't estimate overall response quality.

This result applies to the historical configuration tested. It doesn't establish real classroom benefit or qualify every component change made afterward. It is also separate from the newer demonstration video.

## 28. Some earlier quality claims had to be withdrawn

Some evaluation results needed correction, and those corrections affect what I can claim.

A ten-thousand-case analysis exposed the reference answer during authoring. I therefore exclude it as independent evidence of product quality.

Another result contains an unresolved contradiction in its aggregate numbers. Its unsupported grounded percentage is also excluded.

The third factual round exceeded the registered candidate limit. Its cases can still help explain failures, but its selection claim is invalid.

The planner audit separated preferred-label agreement from action validity and utility. Those distinctions changed the interpretation of the earlier scores.

The original records and corrections remain available together. Keeping them makes it possible to see why a claim was narrowed or withdrawn.

Other, separately scoped comparisons still support the findings I've presented, including the explicit factual target and the completion correction. The next step needs to build on that surviving evidence and use a clear, fixed comparison.

## 29. What is delivered, and what remains unresolved?

Now that we've seen the comparisons, this table returns to the project brief.

Course setup, reviewed publication, and student access are implemented. The local workflow checks provide evidence about those operations.

The answer path produces source-based responses with citations. However, the fresh factual comparison didn't meet its answer-quality thresholds. The existence of a citation is therefore not enough to call this requirement complete.

Teaching preferences enter the generation process, and the saved example showed part of the requested sequence. We still need a controlled evaluation of fidelity to the professor's teaching practice.

The application can keep goals and send scheduled messages. The integrated trial also showed that useful, sustained intervention remains unresolved.

Review, pause, and consent controls are available, but the selected components need to be evaluated together before a broader product claim.

This is the current position: a working prototype, specific local and synthetic evidence, and remaining quality requirements. The next slide proposes one focused comparison to address the planner's input gap.

## 30. Next test: plan from student answers instead of delivery counts

The immediate proposal is to change the adapter that prepares the planner's input.

The control would keep the current delivery and event proxy. The candidate would use committed assessment evidence for the goal's target concepts. Initially, the planner, permitted actions, retrieval, and wording would stay fixed.

The hypothesis is that separating correct, incorrect, and missing evidence will make support decisions respond more directly to the student's observed difficulty.

I would start with identical saved snapshots. Cases would include unrelated concepts, conflicting records, ambiguous assessments, and missing observations. The dataset, scoring rules, and thresholds would be fixed before the run.

After that, I would compare complete histories, where different actions can produce different later replies. The measurements would include useful and inappropriate interventions, missed support, authority constraints, and operational cost.

The assessment evidence also needs an independent quality check. Better use of an incorrect assessment can still produce a wrong decision.

This experiment addresses a specific integration gap. Factual and instructional quality remain acceptance priorities, and a later approved course pilot would be needed to evaluate actual student usefulness.

## 31. A working prototype and specific lessons from failed designs

To close, the project delivers an inspectable system for continuing course support. It connects published course settings to conversations, stored observations, goals, and scheduled work.

The comparisons explain several decisions in that system. Explicit required facts improved development answers. A verifier that only rejected could discard a usable action. Checking the exact objective removed unsupported goal completions in the tested histories.

The planner and learner-model results also identify promising comparisons, but their gains remain bounded by synthetic evaluation and incomplete integration.

The main gaps are factual acceptance, fidelity to the professor's teaching, and evidence of real student benefit. The next focused experiment is to improve the planner's input evidence while keeping the other components fixed.

Those are the outcomes of the project so far: a working prototype, specific design findings, and a clearer account of what still needs to be tested.

Thank you. I'd be happy to discuss the implementation or any of the comparisons in more detail.

## 32. Questions

Which part would you like to discuss first?

## 33. Publication workflow: review before student access

This backup expands the publication process.

The professor provides materials and settings, reviews the draft, and requests preflight checks. A blocker sends the work back for revision. Once the checks pass, the application publishes the reviewed release and an authorized student can access it.

The release identifies the approved course version used by later tutoring and goals. This is why the approval process and the relationship between records matter when permissions or course materials change.

## 34. BKT worked example: from one answer to an updated belief

This is a worked calculation using the evaluated BKT configuration.

We start with a thirty percent probability that the learner knows a concept. The model allows a learner to guess correctly when they don't know it, or make a mistake when they do.

After a correct answer, the updated probability is about sixty-six percent. Allowing for learning during the attempt raises it to about seventy-six percent. One day of the configured forgetting then reduces it to about seventy-two percent.

These are estimates produced by the model's assumptions. They aren't observed percentages of learning. That's why the evaluation compares them with both hidden simulator state and later answer outcomes.

## 35. System context: professor, student and model provider

At this level, the diagram shows the system's relationship with its users and external services.

The professor supplies and approves the course configuration. Students use the published course for questions and continuing support. The application is responsible for applying the relevant controls to those interactions.

External inference is configuration-dependent. Using an external model changes how a proposal or response is generated, while the application's authority checks still determine whether its effects can be saved.

## 36. Stored relationships keep turns and goals in their course scope

This is the conceptual model behind the stored records.

The course and release give an interaction its approved context. Conversations and turns retain what happened with a student. Observations and goals carry relevant state forward, while autonomous work records connect that state to later processing.

Those relationships matter because a record can be valid on its own and still be used in the wrong context. The completion defect was an example: the assessment existed, but the decision needed to check which goal and target concept it supported.

## 37. Publication records the approved release and retires old work

This sequence expands the publication workflow.

The professor works with an owned draft and runs the preflight checks. Any blocker sends the work back for revision. Successful publication records the approved release that later student activity refers to.

The key distinction is between preparing a draft and approving a version for use. Tutoring needs to refer to that published context, while current authority checks still handle later withdrawal or access changes.

## 38. Historical verifier: rejection ended with no action

The failure is on the rejection branch.

The planner has selected an action, and the verifier can reject it. In this historical composition, rejection ends with no action. The system doesn't search for another move or return the deterministic baseline.

That explains why adding a verifier could reduce usefulness. The later guarded design changed the fallback behavior. It retained the baseline unless a proposed replacement passed the conditions.

## 39. All learner-model and timing combinations

This table shows all nine combinations of estimator and timing policy, plus two comparison bounds.

The count and constant-timing baseline sends fourteen messages on average. Conditional timing cuts that to seven, with lower final hidden mastery.

BKT with value-based timing sends about twelve messages. Compared with the count and constant baseline, its wasted-message fraction falls from roughly fifty-one to thirty percent, and final hidden mastery rises to about zero point three three.

Those differences support further investigation within the simulator. They don't settle which estimator should enter the product. BKT's next-answer prediction was inconclusive in the fixed-timing comparison, and the integration remained unfinished.

The initial simulation also required a correction because one learner process let forgetting overwhelm learning. The invalid attempt remains recorded separately. Stronger simulator controls are therefore part of the next study, rather than simply repeating more seeds.

## 40. Model allocation: small effects and a completion constraint

This comparison kept the guarded architecture fixed and varied the model allocation for planning and wording.

It used three hundred contexts and four allocations. The recorded intervals for the pooled planner and wording effects both included zero, so neither met the rule requiring the whole interval to be positive.

The Luna allocation for both roles remained the simplest and least expensive eligible option in that comparison.

One allocation had two generator failures and used the deterministic fallback. Its final wording could remain valid even though the provider-completion requirement failed. That distinction is why we record completion and output quality separately.

This was a historical selection under the recorded configuration and costs. It doesn't establish a generally best model. It also doesn't resolve the separate problem with the planner's input proxy.

## 41. Evidence index: what each study supports

This page maps the study labels to their saved results and decisions.

Each label refers to a specific comparison with its own dataset, configuration, and scope. We can use the index to locate the evidence behind a particular chart without treating the studies as one combined experiment.

## 42. Evidence index: invalid claims and the separate demo

This page links the corrections and the newer demonstration to their records.

The correction should be read alongside the original result, because it explains which interpretation changed. The demonstration has a separate status. It shows the software operating in its recording environment, but it doesn't requalify the historical external-model configuration.

## 43. Goal lifecycle: active, completed, expired or cancelled

A goal records a support objective that persists between chats.

It remains active while work is still possible. It can complete when its exact target concepts satisfy the evidence rule, expire when its time ends, or be cancelled when its scope is invalidated.

Reaching an attempt limit blocks further work, but the prototype doesn't create a separate exhausted state.

These states tell the software how to manage continuing support. In particular, completed means that the configured evidence condition was met. The label hasn't been validated as a measure of student mastery.

## 44. The planner’s score and the evaluator’s score are separate

The runtime heuristic helps rank actions before the system chooses one. It combines estimated gain, observation value, future value, and penalties using authored constants.

The evaluation utility is calculated separately. The confirmation uses a registered synthetic value for the selected action, based on state information and a seeded hidden outcome.

That separation prevents us from simply calling the runtime score its own evaluation. However, the evaluation still depends on a synthetic instrument. It doesn't measure real educational outcomes.

A direct analytic-selection control is also missing. We need it to establish whether the model proposal adds value beyond the analytic ranking itself.

## 45. Stronger controls are needed before choosing a learner model

BKT doesn't win every prediction target.

Under constant timing, PFA improves the next-answer Brier score, while the BKT comparison is inconclusive. BKT performs better on hidden-state estimation in the tested families.

That is why I would keep both as candidates and strengthen the controls. A count model with decay would test whether part of the gain comes simply from discounting old evidence. A third simulator family would challenge dependence on the current learner assumptions.

We also need to test the connection to committed assessments in the application. Neither model was selected for product release on the basis of this simulation alone.

## 46. Evidence confidence counts attempts, not correct answers

The three rows show why evidence confidence cannot be read as the probability that the student is correct.

With two assessed attempts, the confidence value is one half in every row. It is the same whether the attempts were both correct, both incorrect, or one of each.

The completion rule therefore checks correct and incorrect counts separately, as well as checking the exact target concept. Only the first row passes that correctness condition for the target.

This is an illustration of the software's rule. The audit can check that the rule is enforced, but it doesn't establish that two correct assessments prove mastery. Assessment accuracy, the threshold, and the treatment of earlier mistakes still need validation.

## 47. Logical deployment: web app, services, workers and stores

This diagram shows the logical applications and stores within the system boundary.

The user-facing application connects to the services that handle course configuration, tutoring, and autonomous work. Persistent records allow those services to continue from earlier interactions. External inference is used where the selected configuration requires it.

The diagram describes responsibility and communication. It doesn't establish a performance advantage for the chosen deployment topology. A comparison of scaling, operational complexity, or alternative databases would need its own workload and measurements.

## 48. Glossary: learner models and evaluation

The table gives the full names and the meaning of each measure in this project.

BKT and PFA are learner models. MSE measures error against a target, which is hidden simulator mastery in this study. The Brier score checks a predicted probability against a correct or incorrect outcome.

A confidence interval describes statistical uncertainty under the method's assumptions. It doesn't cover every possible problem with the dataset or simulator.

## 49. Glossary: retrieval, planner labels and scores

This page explains the retrieval terms and the labels used in the planner comparisons.

BM25 is the keyword-ranking method. Evidence at three checks the top three retrieved results. The ninety-fifth percentile describes the time within which ninety-five percent of measured requests finish.

A, B, C, V, and H are local labels for the candidate designs. They aren't standard names that the audience is expected to know. The model names identify the tested configurations, with the exact allocation details on the earlier backup slide.
