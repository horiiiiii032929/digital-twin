# Graduate CS presentation script with term explanations

32 main slides, Questions and 16 backup slides. Main narration remains approximately 5162 words plus the 4:06 video. Reading aids are optional and should not be read twice.

## 1. An Instructor-Configurable Course Digital Twin

This project aimed to connect an instructor's course materials and teaching settings to continuing student support. I will first show what the prototype delivers and what remains unvalidated. I will then explain the system designs I tried, the failures that changed my decisions, and the work needed to address the remaining gaps.

Sources: research/06_reports/final/chapters/01-objective.tex

## 2. The twin continues course support between questions

This project builds a course-specific teaching assistant configured by a professor. The student can ask questions and submit attempts. The system also keeps observations and goals between chats, so support can begin without another question. The professor remains responsible for the published materials and controls whether proactive support is enabled. In this project, digital twin describes that configured course assistant. It does not mean a validated replica of the professor’s judgement. The engineering question is how to connect configuration, evidence and accumulated observations, and which component choices are justified by comparisons.

The video compresses thirty virtual days into four minutes. First watch publication and student access. Then watch what happens after a student stops typing: the software processes due work and a message arrives without a new question. A reply and a non-response lead to different recorded histories. Pause and consent controls are also exercised. This is actual product UI with synthetic accounts, an accelerated clock and deterministic services. It demonstrates the operating loop; historical model-backed studies later examine other configurations. It is not a real classroom trial.

During the video, please watch the first follow-up after the student stops typing, and then what happens when the professor pauses support or a student withdraws consent. [Pause before playback.]

Sources: research/06_reports/final/chapters/01-objective.tex, research/06_reports/final/chapters/02-course-workflow.tex, reports/presentation/recording/live-virtual-demo.md

## 3. The contribution is an evaluated system and its design lessons

There are two kinds of contribution here. The deliverable is an inspectable course-support prototype that retains state and schedules permitted work between questions. The research contribution is the evidence from explicit design comparisons, including unsuccessful candidates. The comparisons show why particular evidence contracts, fallback compositions and objective boundaries mattered in this implementation. I am not claiming to invent Bayesian Knowledge Tracing or retrieval. I am also not claiming that every complex design is inferior. The general lesson is a hypothesis informed by these bounded results: before adding another decision stage, check what evidence crosses the existing interfaces and what happens when a stage rejects it. The rest of the presentation follows those interfaces, then returns to the integrated system.

Sources: research/06_reports/final/chapters/01-objective.tex, research/06_reports/final/chapters/04-comparisons.tex, research/05_evaluation/goal-completion-scope-development-001-results.md

## 4. Delivery against the project brief

The brief asked for a course Twin that uses instructor materials and teaching preferences, supports students over time, and preserves instructor oversight. This table separates implemented behaviour from demonstrated quality.

The prototype provides course configuration, reviewed publication and student access. Local checks exercised approval, reload, withdrawal and operational recovery. That supports a bounded claim about these workflows.

The factual response path preserves source references, but its fresh grounded-answer score remains below acceptance. Teaching preferences enter the response pathway, but fidelity to the actual instructor has not been validated.

Continuing support is implemented through stored observations, goals and autonomous jobs. An integrated trial exercised delivery and restart controls. A later correction removed unsupported goal completions in a targeted regression. Neither result demonstrates learning benefit for students.

The deliverable is therefore a working research prototype with inspectable decisions and specific local evidence. It has not satisfied all five acceptance requirements. I will use those remaining gaps to explain why the design comparisons matter.

This is also the scope of the recording. It will show operation, while the tables and saved examples explain which quality claims the evidence supports.

Sources: research/06_reports/final/chapters/01-objective.tex, research/06_reports/final/chapters/02-course-workflow.tex, research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md, research/05_evaluation/goal-completion-scope-development-001-results.md

## 5. After the student stops typing, scheduled support continues

I will first show the software. There are two professors, two courses and four synthetic students. Watch what happens after a student stops typing. The system observes the saved state and processes due work as the virtual clock advances. Also watch the professor pause and the student consent change. The recording uses existing deterministic services in an isolated environment. It is a demonstration of operation, not the historical model-backed evaluation.

[Play the embedded video. No speech for 4 minutes 6 seconds.]

The important point is that support can originate from the system. The remaining slides examine whether the designs behind that behavior are useful, correct and supported by valid evidence.

Sources: reports/presentation/recording/live-virtual-demo.md

## 6. Publication binds approved content to a course release

The professor provides materials and settings, reviews the draft, and runs the preflight checks. Blockers return the work to revision. Publication creates the reviewed release that an authorised student can use. The lanes distinguish instructor decisions from application work and student access. A release is the published version to which later tutoring and goals are tied. This is why source review and publication are part of the software’s behaviour, rather than administrative background.

Diagram scope and key: UML Activity — Course publication and student access Scope: one course release · Activity partitions identify responsibility Notation: rounded action; diamond = merge/decision; [guard] = branch condition; filled circle = initial; bullseye = activity final.

Sources: research/06_reports/final/chapters/02-course-workflow.tex

## 7. Instructor settings and observed behavior

The instructor settings reach different parts of the software. Source permissions define what evidence the tutor may use. Approved objectives define what its goals may cover. Action permissions and consent restrict whether the system can deliver a proposed action. These are executable controls. A response model cannot authorize itself to ignore them.

Teaching preferences have a different role. Tone, explanation depth and the help sequence enter the generation pathway. Their presence in an input does not prove that the output follows the instructor’s practice. We need to inspect what the student actually receives.

This saved Socratic profile requested a diagnostic question, a student attempt and then one hint. The student asked how slot seal worked in the synthetic course protocol. The tutor asked for the student’s current explanation and the step they were unsure about. That shows part of the intended help sequence. However, it does not diagnose the particular conceptual difficulty. The response is still generic.

A separate explanatory example uses a different topic and context. It is not a controlled profile comparison. For a stronger test, I would hold the question, evidence and learner state fixed, vary only the approved profile, and independently review the resulting instruction. That remains proposed work. The owner can inspect the settings and enforcement points now, but instructor fidelity still needs evidence.

Sources: research/06_reports/final/chapters/02-course-workflow.tex, research/06_reports/final/chapters/profile-examples.tex

## 8. Experiments change components inside shared runtime controls

This component view locates the experimental boundaries. The tutoring and autonomy services share authority checks and persistent state. Factual studies change evidence selection and the required-answer contract. Planner studies change the action-selection strategy. Wording studies change generation or revision. The planner-input adapter is a separate integration boundary: the current default supplies a delivery and event proxy. Study E evaluates learner estimators and timing outside the tutoring service, so it must not be read as evidence that BKT already operates inside this application. These studies do not form a single controlled ranking of complete systems. [Pause and point to the adapter before moving on.]

Sources: research/06_reports/final/chapters/03-runtime-design.tex, src/digital_twin/student/planning_architectures.py, src/digital_twin/student/learner_estimators.py, src/digital_twin/generation/generator.py

## 9. What the simulation executes and supplies

There are three different kinds of evidence in this presentation, and I do not want to combine their claims. The video shows a new deterministic software demonstration. Its student inputs and thirty-day clock are controlled, while existing product services create goals, select actions and save deliveries.

The historical operational dialogue study shown in this component diagram also supplies synthetic student behavior and virtual elapsed time. However, it invokes the configured external model through actual tutoring and autonomy services. It checks saved turns, delivery, consent and restart behavior. The student driver decides attendance and constructs replies according to its configured probabilities. Those replies are not observations from real students.

The learner and timing study is separate. It contains a hidden simulated learner state for scoring predictions and intervention outcomes. It does not execute the text retrieval and generation pipeline. The candidates see permitted observations, while the evaluator can use hidden simulator state. That distinction is why a lower estimation error there does not demonstrate better instructional text in the product.

In a classroom, actual students would supply attendance, attempts and reactions. Here those inputs are simulated so that runs are finite and reproducible. The measured software actions are real executions, but the human behavior and educational outcome assumptions are supplied by the experimental design. I therefore attach each result to its own study rather than calling every thirty-day result the same experiment.

Diagram scope and key: UML Component: operational dialogue simulation Study G only. Synthetic student text and elapsed time enter actual product services. Student attendance and replies are simulated. This operating trial does not measure hidden mastery. Study E uses a separate learner/timing simulator.

Sources: research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md, research/05_evaluation/successor-learner-timing-simulation-001-results.md, reports/presentation/recording/live-virtual-demo.md

## 10. The complex factual paths shared an acceptance stage

These are the three factual paths that were tried. The lexical control retrieves by matching words, accepts an evidence hit, and extracts a source response. The hierarchy and plan-observe paths add organisation or explicit retrieval steps. Both eventually require coverage of the whole question. That shared check is the important failure location: it treated question-framing words as required evidence. The next chart shows the resulting loss of answers on cases that were answerable. The comparison identifies a contract defect; it does not establish that hierarchical retrieval or planning is inherently inferior.

Diagram scope and key: UML Activity: factual paths tried Historical Round 1. All paths receive the same question and course evidence. Coverage was an action-selection defect: question scaffolding became required evidence. This does not reject event sourcing generally.

Sources: research/05_evaluation/course-digital-twin-whole-system-architecture-round-1-001-results.md

## 11. Both complex factual paths lost answer coverage

The chart reports the same development cases for three factual designs. Grounded means the answer contains the required supported claims. Answerable action means that the system answers when sufficient evidence is present. The lexical control answered every answerable case, although grounded accuracy was only about fifty-three percent. Both more complex paths fell to about twenty-five percent grounded accuracy, and answered only about thirty-six percent of answerable cases. They shared a whole-question coverage check that incorrectly required evidence for question-framing words. This is the concrete reason for the regression. Boundary handling remained perfect in this development comparison, so conservative abstention alone did not make the overall design useful. The next comparison changed the required-fact contract instead of adding another decision stage.

Sources: research/05_evaluation/course-digital-twin-whole-system-architecture-round-1-001-results.md

## 12. A retrieved passage can still produce an incomplete answer

This is an illustrative example of the contract, not a quoted evaluation case. Suppose the question asks for all three stages and the retrieved sentence contains draft, review and publish. An answer containing only draft and review is supported in what it says but incomplete. Retrieval succeeded; the full answer did not. An explicit target describes both the required type of answer and its cardinality. This is why the next comparison tests the required-fact contract, and why high retrieval coverage later does not imply high grounded-answer accuracy.

Sources: research/05_evaluation/course-digital-twin-whole-system-architecture-round-2-001-results.md

## 13. Explicit required facts helped. Extra ranking added no gain.

The successor design changed what the answer path received. Instead of asking whether evidence covered the wording of the whole question, it identified the target and the number of facts required. It then selected claims for those requirements.

On the same second development fold, the lexical control produced two hundred and fifty-three fully grounded answers from three hundred and ninety-seven answerable cases. The typed target and fact-count design produced three hundred and fifty-five. Adding section ranking produced exactly the same count.

The added ranking stage also increased measured ninety-fifth-percentile latency from one point three six to two point seven nine milliseconds. These are local deterministic retrieval measurements. The result supplied no quality reason to keep that extra complexity.

The typed design still had errors involving paraphrased targets, neighbouring source regions and missing answer spans. It remained a development baseline with Refine status because no arm passed every quality gate.

The defensible design change here is the typed contract on its own comparison fold. The sequence does not justify combining results from different folds into a single improvement curve.

The later source-range variants remain diagnostic evidence because their comparison violated its candidate-count limit. I preserve that correction with their results in the backup. Their status does not change the valid typed-target comparison just shown.

Reading aid: p95 latency = the time within which 95% of measured requests finish. Lower means faster responses for most requests.
Original source/scope footer: Study A: one development fold, 397 answerable cases within 497 total cases.

Sources: research/05_evaluation/course-digital-twin-whole-system-architecture-round-2-001-results.md

## 14. Fresh factual answers still missed the acceptance gates

Two further observations explain why the retained factual path still falls short. First, an earlier ambiguity gate compared distinct answers across every candidate above a coverage threshold. In a full course, a weakly related region could compete with the strongest relevant answer. The earlier confirmation used one approved chunk per release, so it could not exercise that competition.

In a later one-hundred-case diagnostic, the target region ranked first in eighty-four cases. Sixty-nine of those still returned clarification. This motivated comparing dominant interpretations rather than treating every weak match equally.

Second, the fresh five-configuration comparison still found a large gap after retrieval. The retained BM25 and dominance-gate composition retrieved complete evidence in ninety-eight percent of eight hundred answerable cases, but produced fully grounded answers in sixty-three point two five percent. The hybrid with the same gate scored sixty-two percent.

The final-answer rubric requires all necessary facts and exact claim-to-citation coverage. Missing a required fact fails the case even when the retrieved set contains it. Normalized text and source ranges make that scorer inspectable, but limit its semantic flexibility.

BM25 remained the simpler local fallback; both configurations failed acceptance. Its separate boundary score was one hundred and ninety-two of two hundred. The diagnostic explains a gate failure, while the fresh study bounds the retained composition's quality. Together they show why retrieval upgrades alone did not resolve the answer contract.

The denominator is eight hundred for the answerable metrics and two hundred for boundary actions. The BM25 grounded score is five hundred and six out of eight hundred, with a source-family bootstrap interval from fifty-eight point seven five to sixty-seven point six three percent. Some mechanically generated questions are malformed. For example, the recorded analysis describes a question asking for the source point about two, whose expected answer is a raw table row. That limits the benchmark’s realism. We preserve the case and do not tune on these held-out results. The small difference between BM25 and hybrid is not a claim of general superiority.

Reading aid: BM25 (Best Matching 25): keyword ranking. Hybrid combines keyword and semantic retrieval. Qwen3 is a model name.
CI = confidence interval. Evidence @3 means the required evidence is among the top three retrieved results.
Original source/scope footer: Grounded = complete required claims supported by evidence. Mechanically generated questions and rigid target matching affect this benchmark.

Sources: research/05_evaluation/final-cross-method-factual-confirmation-001-results.md, research/05_evaluation/final-cross-method-factual-confirmation-001-results.md, research/05_evaluation/records/final-cross-method-factual-confirmation-001-analysis-correction-001.json

## 15. Better visual retrieval did not improve grounded answers

Visual retrieval deserves a place in the main findings because richer source representation did not automatically improve the answer. In the historical comparison, relevant visual retrieval rose from eighteen to twenty-eight cases out of thirty, but grounded answers stayed at twenty. In a separate fresh image-capable comparison, the candidate produced sixteen grounded answers versus twenty-six for its control, and was dropped. These are separate studies. Their common lesson is that locating a relevant visual and turning it into a complete supported answer are different requirements.

Sources: research/06_reports/final/chapters/04-comparisons.tex

## 16. A rejecting verifier could remove a usable action

The planner comparison changed the decision stages inside a common execution boundary. Every method still faced the same permissions, evidence checks and delivery rules. A used a deterministic event rule. B asked a model to propose a permitted action without lookahead. C added deterministic analytic lookahead to rank actions. C plus V added a model verifier after the C selection.

The question was whether these extra decision stages improved the resulting action enough to justify replacing the simple control. In the third development fold, the deterministic control had the best registered hidden utility. B’s direct proposal did not justify automatic priority over that control. C had stronger agreement with a preferred-action label, but lower utility than A. Those metrics asked different questions.

The additional verifier exposed a more concrete failure. It could reject a usable move, and the reject branch returned no action. It did not search for another useful move or return the baseline. This is a failure of the reject-only composition, not an argument that all verification is harmful.

The later audit also corrected the interpretation of acceptable-move scores. Preferred-label agreement had been confused with permitted transition validity. Five planner failures came from a non-authoritative reason-string length constraint. These details matter because they explain which boundary failed. They do not support saying that the entire safety mechanism collapsed. The successor therefore preserved the baseline when a proposed replacement did not earn acceptance.

Reading aid: A / B / C are local planner labels defined in the table. V = the added verifier. Lookahead estimates action consequences.
Original source/scope footer: Fold 003 labels were later reinterpreted. Preferred-label agreement was not action validity.

Sources: research/05_evaluation/successor-architecture-development-fold-003-single-case-001-results.md, research/05_evaluation/successor-architecture-fold-003-causal-audit-001-results.md, research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md

## 17. Guarded replacement falls back to the deterministic action

The H design changes what happens when a proposal is weak. It first computes the deterministic baseline. If there is no authorized evidence, the result is no action. When evidence is available, a model proposal can replace the baseline only if it is valid, permitted, agrees with the analytic best action and exceeds the minimum value margin of zero point zero four. Otherwise, the method keeps A.

Diagram scope and key: UML Activity: guarded replacement H preserves deterministic A unless an authorized proposal passes the replacement guards.

Reading aid: A = deterministic rule baseline. H = guarded replacement: keep A unless a permitted proposal passes the replacement conditions.
Original source/scope footer: H replaces A only for a valid, permitted proposal matching the analytic best action, with value gain ≥ 0.04.

Sources: research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md, research/05_evaluation/successor-architecture-confirmation-005-001-results.md

## 18. Guarded replacement produced a small synthetic utility gain

The means are close, so the paired effect is more informative than the means alone. Guarded replacement improves registered evaluation utility by zero point zero zero four eight zero five. The ninety-five-percent paired interval runs from about zero point zero zero three one to zero point zero zero six eight. It excludes zero for these synthetic contexts, but the gain is small. Both methods obeyed the tested action rules. Preferred-action agreement moved from seventy-four to seventy-three percent and its paired interval includes zero. Evaluation utility is the synthetic instrument’s value for the selected action, not the runtime heuristic used to rank proposals. The run recorded eight hundred and one provider calls, four failed calls and about thirty-four US cents in reported cost. Those are historical totals rather than a controlled latency or current-price claim. The result justified progression to the next engine comparison. It did not establish student learning or isolate the language model’s contribution against direct analytic selection. That ablation remains necessary.

Reading aid: CI = confidence interval, showing statistical uncertainty. A = rule baseline; H = guarded replacement. USD = US dollars.
Original source/scope footer: Runtime heuristic and evaluation utility are different quantities. Formulas and instrument scope are in backup.

Sources: research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md, research/05_evaluation/successor-architecture-confirmation-005-001-results.md, research/05_evaluation/records/successor-architecture-confirmation-005-001.json, research/06_reports/final/chapters/planner-math.tex

## 19. Estimation and timing are separate experimental choices

Before reading the results, it helps to distinguish the estimator from the timing policy. The count baseline is a smoothed proportion of correct assessed attempts and does not forget. Bayesian Knowledge Tracing, or BKT, maintains a belief that a concept is known and updates it using correct or incorrect answers. Its model permits guessing, mistakes despite knowledge, learning, and forgetting over time. Performance Factors Analysis, or PFA, uses a logistic function of successes and failures with time decay. None of these methods reads the student’s text. They consume an assessed correctness record. Constant timing sends whenever the scheduled check is eligible. Conditional timing also requires a stalled or low-and-uncertain state. Value timing estimates the gain from intervening and requires it to exceed a margin. The experiment crosses the estimators and timing policies so their effects can be compared separately.

Sources: research/05_evaluation/successor-learner-timing-simulation-001-results.md, src/digital_twin/student/learner_estimators.py, src/digital_twin/student/intervention_policies.py

## 20. The learner study tests two different prediction targets

The held-out evaluation contains two hundred and forty learners per condition, formed from six personas, two simulator families, and twenty seeds. Parameters were selected on separate development seeds. Mean squared error compares each daily concept estimate with the simulator’s hidden mastery. The Brier score instead compares the estimate just before an assessed attempt with the observed correct or incorrect outcome. These are different evaluation targets. Messages and waste measure intervention behaviour. Waste means sending when hidden mastery is already at least zero point eight five, or when the learner is unreceptive. All methods face the same consent, quiet-hour and frequency restrictions. Paired bootstrap resampling gives uncertainty intervals across these simulated learners. The held-out split reduces seed overfitting, but does not remove dependence on the simulator’s assumptions.

One simulator family is BKT-like and the other logistic-like. Both are assumptions chosen by the researcher. A held-out seed changes the random trajectory, not the family of learner behaviour. The count baseline has no fitted parameters or forgetting. The alternatives have fitted parameters and time-dependent behaviour, which limits the fairness of the baseline comparison.

Reading aid: Seed = a reproducible random sequence. Bootstrap resamples learners to estimate uncertainty. Brier is a score name, not an acronym.
Original source/scope footer: 6 personas × 2 families × 20 test seeds. Same consent / timing constraints. 1,000 paired learner bootstrap resamples.

Sources: research/05_evaluation/successor-learner-timing-simulation-001-results.md, src/digital_twin/student/learner_estimators.py, src/digital_twin/student/intervention_policies.py

## 21. BKT improved state estimates. Answer prediction was inconclusive.

Here timing is held constant for count and BKT on the same learners. Hidden-state error falls from zero point zero eight four to zero point zero three five. The paired interval excludes zero. The estimate made before the next answer tells a different story: both rounded Brier means are zero point two five nine, and the paired interval includes zero. A closer fit to the simulated hidden state therefore does not establish better prediction of observed answers. The source also reports lower hidden-state error in both simulator families, which reduces but does not remove concern that BKT benefits from simulator alignment. We need a decayed-count control and a third family before strengthening the claim. BKT remains an experimental candidate outside the default planner-input adapter. [Pause on the two different evaluation targets.]

Reading aid: BKT = Bayesian Knowledge Tracing. MSE = mean squared error. CI = confidence interval. ↓ means lower is better.
Here MSE compares hidden-state estimates; Brier scores predictions of the next correct / incorrect answer.
Original source/scope footer: BKT remains outside the default runtime. Next controls: count with decay and a third simulator family. Limitations are expanded in backup.

Sources: research/05_evaluation/successor-learner-timing-simulation-001-results.md

## 22. Conditional timing halved contact, with a mastery tradeoff

With the count estimator fixed, conditional timing cuts the mean number of messages from fourteen to seven. However, the mean final hidden mastery falls from zero point three one four to zero point three zero two. The paired interval excludes zero in this simulator. Value timing retains more contact and has lower waste. That result warns against treating fewer messages as an unqualified success. The complete crossed experiment and the BKT-plus-value result remain in backup. These policies have not established a real-course educational benefit. The scope is still the simulator. Lower message volume is not automatically a better teaching outcome. The next test should challenge the assumptions as well as reproduce the paired comparison.

Reading aid: Constant / conditional / value are contact policies. Mastery here is hidden simulator state; it is not a real-student assessment.
Original source/scope footer: Waste: 50.6% / 38.8% / 34.1%. Waste means contact at mastery ≥ 0.85 or while unreceptive. Simulator outcomes only.

Sources: research/05_evaluation/successor-learner-timing-simulation-001-results.md

## 23. The default planner still receives a delivery proxy

The application still exposes a gap between the experimental learner design and the retained runtime. Goal completion uses committed concept assessments. The default planning adapter instead constructs its state from deliveries and event identifiers.

Its field named mastery probability rises from one half to two thirds after one delivered goal action, even without a new student answer. Its uncertainty counts supporting identifiers, and elapsed observation time is absent. That input is a planning proxy, not the BKT estimate from the previous experiment.

The assessment store also has an evidence-confidence field. Two assessed attempts produce the same confidence whether both were correct or incorrect, so the completion rule checks outcome counts as well.

This separation matters because planner comparisons supplied state cards directly. Their gains do not validate the adapter that prepares those cards in the product. The estimator experiment was outside the tutoring service, and its promising result did not automatically become an integrated capability.

A plausible hypothesis is that this weak connection contributes to poorly targeted support. The current evidence does not isolate it as the cause of every generic message. The next design needs an explicit comparison between the current proxy and committed target-concept evidence, with other components held fixed.

Diagram scope and key: UML Activity: the default planner input Current adapter constructs a delivery proxy. Assessment and completion follow a separate path.

Reading aid: Proxy = an indirect substitute. This adapter counts delivered actions rather than demonstrated knowledge. BKT is not integrated here.
Original source/scope footer: Current adapter behavior. Experimental BKT results do not establish product integration.

Sources: research/06_reports/final/chapters/03-runtime-design.tex, reports/presentation/design-comparisons.md

## 24. Structured wording retained critical semantic errors

Both wording candidates preserved all fifty-six adequate drafts and repaired forty-seven of fifty-six defective drafts. Each still left one critical error, failing the zero-critical-error gate. The example is a necessary-versus-sufficient condition error. The source requires exactly two seals; an added example guarantees acceptance when two seals are present. The source does not support that guarantee. Structural compliance and fluent wording do not establish semantic correctness. The decision was not to promote either revision candidate. These were bounded, AI-assisted draft assessments, not evidence of student learning. The visual-retrieval comparison earlier showed a related boundary: improving an intermediate representation does not necessarily improve the final supported answer.

Sources: research/05_evaluation/independent-factual-revision-controls-001-fresh-v16-live-001-results.md, research/06_reports/final/chapters/04-comparisons.tex

## 25. Completion used evidence from the wrong objective

The goal defect is the clearest example of a correct stored observation leading to an incorrect later decision. Two goals were active: cache coherence and virtual memory. I will call them Topic A and Topic B. After two correct attempts on Topic A, the system completed both goals. Topic B had no assessment evidence. Reopening SQLite preserved both completed statuses.

The old service shortcut and the goal interpreter used evidence too broadly. Strong evidence for a concept anywhere in the learner record could complete a goal about another concept. The assessments themselves could be correct, and the storage could survive a restart, while the goal decision remained wrong.

The correction binds each active goal to its exact objective and checks committed evidence for every target concept in the same scope. Missing or ambiguous mappings remain incomplete. Under the retained rule, each target needs at least two correct assessments, no incorrect assessments, and sufficient evidence confidence.

This fixes the scope error, but the rule still has limitations. An earlier incorrect count continues to block completion in that state. The implementation also does not interpret an instructor's free-text success condition as an arbitrary executable rule. A completed goal therefore records satisfaction of a fixed software condition.

This failure explains why earlier restart and assessment checks were insufficient. They tested whether records persisted and whether attempts received the correct assessment. The missing check linked the completed goal to its own target concepts. The revised regressions cover unrelated, missing, ambiguous and uncommitted evidence, as well as continued work on another goal.

Diagram scope and key: UML Activity: goal-completion evidence scope Historical guard and corrected guard. These are separate activities, not one sequential execution. The corrected completion check uses two correct assessments per target, no incorrect assessment, and confidence at least 0.5. It is not mastery validation.

Sources: research/05_evaluation/goal-completion-scope-development-001-results.md, research/06_reports/final/chapters/03-runtime-design.tex

## 26. Exact-objective evidence removed unsupported completions

The lifecycle comparison isolated a much smaller design change. Each arm ran seventy-two histories using the same driver, concepts, seeds, profiles and dependencies. Only two runtime source files differed. Planning and wording were deterministic, and no external model calls were made.

The old implementation completed twenty-six goals. Fourteen had support from the target concepts, and twelve did not. The corrected implementation completed fifteen, all supported. It passed the run's nineteen gates.

Both arms preserved restart consistency and passed the reported attribution and assessment checks. Those equal results explain why persistence and assessment tests had missed the separate completion defect. An audit had to connect each completed goal to its committed target evidence.

The correction also changed subsequent support. Across thirty-six autonomous histories per arm, it produced fifty-six more messages. Mean final simulated mastery changed by minus zero point zero zero two four, and the wasted-message fraction increased slightly. Those are descriptive simulator outcomes, not demonstrated effects on students.

Shared starting seeds do not require identical later conversations: different interventions can change simulated replies. The evidence supports keeping the objective-scope correction because an unassessed goal must not complete from another topic's evidence. It does not support a learning-improvement claim.

This result shows both the value and the remaining weakness of the revised design. The state decision became correct under the tested rule, while the quality of the additional support remained unresolved.

The independent audit checks the same explicit completion contract using committed evidence snapshots. It is an independent check of contract compliance, not independent educational validation. The assessment itself could still be wrong. Two correct records, no incorrect records and confidence at least one half do not prove mastery. An earlier incorrect record also matters under this prototype rule. Zero observed unsupported completions applies to these dependent synthetic histories, not all future users.

Sources: research/05_evaluation/goal-completion-scope-development-001-results.md, research/05_evaluation/goal-completion-scope-development-001-results.md

## 27. Authority is checked when saving a turn

Some retained boundaries were requirements-driven choices rather than winning experimental architectures. A published release fixes approved source versions and configuration. Current authority can still change while the system prepares a response.

The application performs generation outside the transaction, then checks authority again at commit. If the release has been withdrawn or permission has been revoked, the earlier successful check cannot authorize the later effect. The saved turn must still belong to the allowed course and release.

An accepted turn saves the response, its citations and the learner update together. A revision check prevents a result based on stale learner state from silently overwriting a newer state. The important point on the sequence diagram is the boundary between preparing a candidate response and committing an authorized turn.

These checks address concrete consistency and permission requirements. They do not prove that SQLite or the chosen process topology outperforms a distributed alternative. I have not performed that deployment comparison. The evidence supports the specific local contract that a prepared answer must pass the current checks before its effects become committed state. The next slide addresses a separate problem: how to recognize an effect that was already saved before a worker stopped.

Diagram scope and key: UML Sequence — Tutoring and authority at commit Scope: a fresh request reaching generation; policy/evidence boundary responses are omitted Notation: synchronous calls / dashed replies; alt operands have exclusive guards. Matching duplicate requests return the saved turn.

The invariant is that a generated proposal cannot commit under stale or revoked authority. Generation runs outside the write transaction, followed by current authority and expected-revision checks. This is a local functional contract; it is not a scaling result.

Sources: research/06_reports/final/chapters/03-runtime-design.tex

## 28. A retry recognizes the saved in-app delivery

For proactive support, the message save and job-result save are separate steps. Imagine that the worker saves the message successfully and then stops before recording the completed job result. When its lease expires, another worker can claim the work. A lease alone does not tell that worker whether the student-facing effect already exists.

The stable delivery identity is the additional mechanism. Recovery uses the same key and recognizes the message that was already saved. It can finish the job bookkeeping without sending another in-app message. A matching request identifier provides a related reuse contract for ordinary tutoring turns.

The authority check still matters during recovery. A stable key does not create permission to send new content, and a lease does not replace the saved-effect check. These mechanisms solve different parts of the failure.

This is a local persistence guarantee for the tested path. It is not a promise of exactly-once effects across every external provider. If a provider outcome is uncertain, the system must not blindly repeat an irreversible effect. The retained tests exercise these boundaries, but they are not a benchmark of alternative production topologies. Keeping that distinction makes the architecture claim precise and reviewable.

Diagram scope and key: UML Sequence — Retry after an in-app delivery is saved Scope: one stable delivery identity; local persistence recovery, not external exactly-once delivery Notation: calls and replies on lifelines; UML note marks the crash window; stable key identifies the saved message on retry.

The invariant is that retrying the same saved delivery key returns the existing in-app message. A crash after the message save but before the job commit is the concrete failure window. External provider effects remain outside this local guarantee. [Point to the crash window and then the repeated key.]

Sources: research/06_reports/final/chapters/03-runtime-design.tex

## 29. The integrated trial ran, but every check-in stayed generic

The live-model trial checked whether a historical integrated configuration could execute these paths together. It ran twenty-four synthetic histories over thirty virtual days and used actual external model calls.

The run processed four hundred and eighty-four tutor turns, delivered sixteen check-ins and exercised twenty-four service restarts. Consent was disabled on virtual days ten through nineteen, and no proactive messages arrived during that interval.

There were six hundred and fifty-four model calls, of which eleven reached the output limit. Thirteen tutor turns ended in a safe graph failure. The trial therefore includes actual operational failures and controlled stopping behaviour.

The generic check-ins discussed earlier show the limit of the integration. The worker could initiate support and preserve its effects while the content still failed to target the learner's difficulty. A post-run AI diagnostic inspected seventy-seven deliberately selected responses and failures; that selection cannot estimate overall response quality.

This run supports bounded execution and control claims for its historical configuration. It does not establish thirty days of real uptime, learning benefit, or qualification of every later component change. That is why the final design must preserve a separate evidence status for the components it combines.

Sources: research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md

## 30. Evaluation corrections limit the surviving claims

Some historical scores cannot support the claims originally attached to them. A ten-thousand-case analysis exposed the reference answer during authoring, so it is not independent product-quality evidence. Another result has an unresolved aggregate contradiction and its unsupported grounded percentage is excluded. Round three exceeded the preregistered candidate limit, invalidating the selection claim while retaining useful diagnostics. The planner audit also separated preferred-label agreement from valid actions and utility. These corrections remain in the evidence record. They do not erase every result: the separately scoped typed-target, fresh factual, planner and lifecycle comparisons still support their stated conclusions. The point is to distinguish valid selection evidence from material that only explains a failure.

Sources: research/05_evaluation/factual-qa-v3-scale-completion-10000-001-analysis-correction-001-results.md, research/05_evaluation/academic-factual-qa-open-10000-winner-regression-001-results.md, research/05_evaluation/course-digital-twin-whole-system-architecture-round-3-001-analysis-correction-001-results.md, research/05_evaluation/successor-architecture-fold-003-causal-audit-001-results.md

## 31. The next comparison should change the planner’s input evidence

The next experiment would change one specific boundary: the adapter that prepares the planner input. The control would keep the delivery and event proxy. The candidate would use committed assessment evidence for the target concepts of the goal. The planner, permitted actions, retrieval and wording would initially stay fixed.

My hypothesis is that distinguishing correct, incorrect and missing evidence will make the decision respond more directly to the student’s observed difficulty. That is a proposal, not an established result. It does not require assuming that a larger model will solve the problem.

I would first compare decisions on identical saved snapshots. The cases should include unrelated concepts, conflicting evidence, ambiguous assessment and missing observations. The dataset, scoring rules and acceptance thresholds must be fixed before the run. Then I would compare complete histories, where different actions can legitimately produce different later replies.

The measurements should cover inappropriate interventions, useful interventions, missed support, the existing authority and lifecycle constraints, and operational cost. We also need an independent check that the assessment evidence itself is meaningful. An improved adapter cannot compensate for an incorrect assessment.

This comparison can proceed on fixed, reviewed inputs while factual and instructional quality remain acceptance priorities. Before making a broader product claim, the selected components need to be frozen and evaluated together. A later approved course pilot would be needed to examine actual usefulness and student experience. That dependence is why I do not present this single adapter change as the completion of the whole project.

Sources: research/06_reports/final/chapters/03-runtime-design.tex, research/05_evaluation/goal-completion-scope-development-001-results.md

## 32. Deliverable, findings and acceptance gaps

The deliverable is the inspectable persistent-support system. The knowledge contribution is the bounded comparison evidence: explicit required facts improved answering in development; reject-only verification could discard a usable move; exact-objective evidence removed unsupported completions in the tested histories. These are different experimental scopes, not one universal claim about architecture. The planner’s small synthetic gain and the learner-estimator results identify promising next comparisons. They do not establish professor fidelity or real learning. The immediate integration experiment changes the planner-input adapter while holding the other components fixed, alongside continued work on factual and assessment quality.

Sources: research/06_reports/final/chapters/01-objective.tex, research/06_reports/final/chapters/04-comparisons.tex, research/05_evaluation/goal-completion-scope-development-001-results.md

## 33. Questions

Use the backup diagrams and the defence notes for detailed questions.

Sources: 

## 34. BKT example: updating one concept after an answer

This calculation uses the evaluated BKT configuration. Start with a thirty-percent belief that one concept is known. The model permits a correct guess when it is unknown, and a slip when it is known. After a correct answer, Bayes’ rule gives about sixty-six percent. Allowing learning from the attempt raises the belief to about seventy-six percent. One day of the configured forgetting reduces it to about seventy-two percent. These values are model estimates under assumptions, not observed percentages of learning. The evaluation must therefore test how well the estimates agree with hidden simulator state and subsequent assessed outcomes.

Reading aid: BKT = Bayesian Knowledge Tracing. Guess: correct despite not knowing. Slip: incorrect despite knowing. This is a worked calculation.
Original source/scope footer: Worked calculation, not a recorded learner trajectory. Guess = 0.20; slip = 0.10; learning = 0.30; daily forgetting = 0.05.

Sources: src/digital_twin/student/learner_estimators.py, research/05_evaluation/successor-learner-timing-simulation-001-results.md

## 35. System context

Backup. Explain only the part relevant to the question. Preserve the scope stated in the figure.

Diagram scope and key: C4 System Context — Course Digital Twin Scope: course teaching system · Configured external inference is optional Key: labelled boxes = people/systems; grey = external system; solid open arrow = directed relationship.

Sources: research/06_reports/final/chapters/03-runtime-design.tex

## 36. Domain model and persistence

Backup. Explain only the part relevant to the question. Preserve the scope stated in the figure.

Diagram scope and key: UML Class — Course, conversation and autonomous work Scope: conceptual domain model · Selected identifiers only; implementation methods are omitted Notation: class name / attribute compartments; solid association; endpoint multiplicities. Each opportunity may reference no goal.

Sources: research/06_reports/final/chapters/03-runtime-design.tex

## 37. Publication and approval sequence

Backup. Explain only the part relevant to the question. Preserve the scope stated in the figure.

Diagram scope and key: UML Sequence — Preflight and publication Scope: successful publication of an owned draft; blockers return to revision Notation: dashed lifeline; filled arrow = synchronous call; dashed open arrow = reply; opt frame = guarded interaction.

Sources: research/06_reports/final/chapters/02-course-workflow.tex

## 38. Reject-only verification path

Backup. Explain only the part relevant to the question. Preserve the scope stated in the figure.

Diagram scope and key: UML Activity: reject-only verification Historical C+V path. A rejected selection does not obtain a replacement action.

Sources: research/05_evaluation/successor-architecture-development-fold-003-single-case-001-results.md, research/05_evaluation/successor-architecture-fold-003-causal-audit-001-results.md

## 39. Full estimator and timing comparison

The learner and timing experiment compared two design decisions together. One decision estimated the learner's state using a count baseline, BKT or PFA. The other chose intervention timing using constant, conditional or value-based rules. The simulator evaluated nine combinations and two bounds, with two hundred and forty simulated learners per condition.

The simple count and constant-timing baseline delivered an average of fourteen messages. Conditional timing cut that to seven, but final simulated mastery fell from zero point three one four to zero point three zero two. Sending fewer messages removed some useful practice along with unwanted interventions.

BKT with value-based timing delivered about twelve messages. Its wasted-message fraction fell from roughly fifty-one to thirty percent, while mean final simulated mastery increased to zero point three two eight. The paired intervals supported those differences within the simulator.

That did not justify immediately installing BKT in the product. Its improvement in hidden-state estimation did not establish better next-answer prediction: the Brier-score comparison under constant timing was inconclusive. The product integration with committed observations, a decayed-count control and a third simulator family also remained unfinished.

The design decision was Go Deeper. BKT with value-based timing remained a hypothesis and PFA a comparator. These results show why estimator and timing choices need to be evaluated together. They do not establish real learning effects, and the simulation did not execute text retrieval or generation.

The initial simulation attempt also needed correction because one simulator made forgetting overwhelm learning. The corrected attempt and the invalid result remain separate. This matters for design selection because an estimator or timing rule can look favourable under an unrealistic learner process. A third simulator family and an additional simple control are therefore substantive comparisons, not just more repetitions.

Reading aid: BKT = Bayesian Knowledge Tracing. PFA = Performance Factors Analysis. MSE = mean squared error (lower is better).
Oracle uses hidden simulator information as a comparison bound. Mastery is the simulator’s day-30 state.
Original source/scope footer: Backup. 240 simulated learners per condition. All mastery values are hidden simulator states.

Sources: research/05_evaluation/successor-learner-timing-simulation-001-results.md

## 40. Planner confirmation and model allocation

The model-allocation comparison kept the guarded architecture fixed and crossed two planner choices with two wording choices. It used three hundred contexts and four allocations, giving twelve hundred context and configuration pairs.

The alternatives produced very small pooled effects. The recorded confidence intervals for the planner utility effect and wording validity effect both included zero. Neither satisfied the selection rule requiring the whole interval to be positive. Luna for planning and Luna for wording remained the simplest and least expensive eligible allocation under that recorded comparison.

One detail changes the reliability interpretation. The Terra-planner and Luna-wording allocation completed two hundred and thirty-eight of two hundred and forty generator calls. Two failures used the deterministic fallback. The final wording could therefore remain valid even though some provider calls failed. That allocation missed the provider-completion gate.

The choice follows the recorded objective, completion requirement and cost comparison. It does not establish that Luna is generally the best model, and it is not a recommendation based on current model prices or availability.

This also limits what model substitution alone can solve. Changing the planner model would still leave the product's delivery-count proxy unless the adapter also changed. The model comparison and the input-quality problem concern different boundaries, so one result cannot stand in for the other.

Sources: research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md, research/05_evaluation/successor-architecture-confirmation-005-001-results.md, research/05_evaluation/successor-architecture-engine-comparison-006-001-results.md

## 41. Evidence index: studies and decisions

Source paths:
A: research/05_evaluation/course-digital-twin-whole-system-architecture-round-2-001-results.md
B: research/05_evaluation/final-cross-method-factual-confirmation-001-results.md
C: research/05_evaluation/successor-architecture-confirmation-005-001-results.md
D: research/05_evaluation/successor-architecture-engine-comparison-006-001-results.md
E: research/05_evaluation/successor-learner-timing-simulation-001-results.md
F: research/05_evaluation/independent-factual-revision-controls-001-fresh-v16-live-001-results.md
G: research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md
H: research/05_evaluation/goal-completion-scope-development-001-results.md

Sources: research/05_evaluation/course-digital-twin-whole-system-architecture-round-2-001-results.md, research/05_evaluation/final-cross-method-factual-confirmation-001-results.md, research/05_evaluation/successor-architecture-confirmation-005-001-results.md, research/05_evaluation/successor-architecture-engine-comparison-006-001-results.md, research/05_evaluation/successor-learner-timing-simulation-001-results.md, research/05_evaluation/independent-factual-revision-controls-001-fresh-v16-live-001-results.md, research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md, research/05_evaluation/goal-completion-scope-development-001-results.md

## 42. Evidence index: corrections and demonstration

Read the linked correction alongside the original result. The new screen recording is not evidence that the historical external-model composition was requalified. No real-student learning claim is made.

Sources: research/05_evaluation/course-digital-twin-whole-system-architecture-round-1-001-results.md, research/05_evaluation/successor-architecture-development-fold-003-single-case-001-results.md, research/05_evaluation/successor-architecture-fold-003-causal-audit-001-results.md, research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md, research/05_evaluation/course-digital-twin-whole-system-architecture-round-3-001-analysis-correction-001-results.md, research/05_evaluation/factual-qa-v3-scale-completion-10000-001-analysis-correction-001-results.md, research/05_evaluation/academic-factual-qa-open-10000-winner-regression-001-results.md, reports/presentation/recording/live-virtual-demo.md

## 43. Persistent goals connect observations to scheduled work

A goal is a persistent support objective. It stays active while there is work to do. It can complete only when the exact target concepts satisfy the evidence rule, expire when its time ends, or be cancelled when its scope is invalidated. Hitting an attempt limit blocks further work but does not create a separate exhausted state. These are software lifecycle states. The completed label is not a validated claim of student mastery. This diagram explains what the observer and worker are maintaining between individual chats.

Diagram scope and key: UML State Machine — Autonomous goal lifecycle Scope: governed goal record · Completion guard shown for the evidence-count learner state Notation: filled circle = initial pseudostate; rounded rectangle = state; trigger [guard] / effect. Terminal records remain persisted.

Sources: research/06_reports/final/chapters/03-runtime-design.tex, research/05_evaluation/goal-completion-scope-development-001-results.md

## 44. Runtime prediction and evaluation utility are different quantities

The executable runtime heuristic uses authored constants. It rewards estimated immediate gain, observation and future value, adds a misconception bonus and subtracts evidence risk and interruption. These weights were not fitted to measured educational outcomes. The confirmation runner instead looks up a registered synthetic value for the selected action and averages it over contexts. The instrument uses state information and a seeded hidden outcome. It is separate from the runtime heuristic, but that separation does not make it a real-student outcome measure. The missing direct-analytic ablation is still required to isolate why the guarded composition helps.

Sources: research/06_reports/final/chapters/planner-math.tex, src/digital_twin/student/planning_architectures.py, scripts/run_successor_architecture_confirmation_005.py

## 45. The learner result needs stronger controls before integration

The full comparison should not imply BKT wins every target. PFA improves next-answer Brier under constant timing, while BKT does not establish that improvement. The hidden-state ranking favours BKT in both tested families, but it remains conditional on the simulator and control choice. The next design should separately test calibration, targeting and the integration of committed assessments. Neither BKT nor PFA was selected for product release.

Sources: research/05_evaluation/successor-learner-timing-simulation-001-results.md

## 46. Completion correctness leaves mastery validity unresolved

The test compares the selected objective with committed concept-level evidence. This catches an implementation error that earlier persistence and assessment checks missed. However, the contract is authored, and checking it independently does not validate the educational meaning of its threshold. The experiment separately verified timestamp and service-boundary behaviour with regression tests. The current rule’s treatment of earlier mistakes is a limitation to discuss rather than silently call mastery.

Sources: research/05_evaluation/goal-completion-scope-development-001-results.md, tests/digital_twin/test_goal_completion_scope.py, tests/test_goal_completion_scope_evaluation.py

## 47. Deployment context: logical containers

The alternatives did not all change the same part of the system. This diagram separates the comparison boundaries so that the later results have a clear meaning.

The common product contains a published course release, a student conversation path, persistent learner observations, and a worker that can initiate permitted support. Course authority, evidence checks and persistence remain responsibilities of the application. Model proposals do not replace those controls.

One program compared complete architecture manifests, with a lexical control, an evidence-first hierarchy, and a plan-observe design. Its executed comparison used deterministic factual responses to expose evidence-path behaviour. It did not test every proposed capability of those architectures over a student's learning history.

A different program compared autonomous planners. It started with an event rule, added a model proposal, then added analytic lookahead and a verifier. Those candidates shared the product boundary and learner-state plane.

Other comparisons changed learner estimation and intervention timing, or the way approved source material became an instructional response. I will show what each design was intended to fix, which mechanism it added, and what the corresponding experiment found.

This distinction also limits the Twin claim. The product represents instructor settings and course material, but fidelity to the actual instructor remains untested. The contribution here is the implemented integration and the design decisions supported by these bounded comparisons.

Diagram scope and key: C4 Container — Course Digital Twin Scope: logical applications and data stores · External inference is configuration-dependent Key: dashed system boundary; blue = internal container; grey = external system; cylinder/folder = data store; arrows = labelled relationships.

Sources: research/06_reports/final/chapters/03-runtime-design.tex

## 48. Reference: learner models and evaluation terms

Use this page as a reference when a term needs clarification. The definitions describe the usage in this project.

Sources: research/05_evaluation/successor-learner-timing-simulation-001-results.md, src/digital_twin/student/learner_estimators.py, src/digital_twin/student/intervention_policies.py

## 49. Reference: retrieval and local system labels

Use this page as a reference when a term needs clarification. The definitions describe the usage in this project.

Sources: research/05_evaluation/final-cross-method-factual-confirmation-001-results.md, research/05_evaluation/final-cross-method-factual-confirmation-001-results.md, research/05_evaluation/records/final-cross-method-factual-confirmation-001-analysis-correction-001.json, research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md, research/05_evaluation/successor-architecture-confirmation-005-001-results.md, research/05_evaluation/records/successor-architecture-confirmation-005-001.json, research/06_reports/final/chapters/planner-math.tex
