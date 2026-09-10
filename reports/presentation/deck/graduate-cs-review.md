# Graduate computer science presentation review

Reviewed: 7 September 2026. Target: `deck/digital-twin-presentation-improved.pptx`, SHA-256 `f8acc1bbdf67a66fdfdca331c88df7512d2e445bf44fa7a7149690198a75ea63`. Slide references use this 42-slide version: 32 main slides, Questions, nine backup slides.

## Overall judgement

The deck is suitable for a graduate CS project discussion and has a credible empirical software-engineering core. It is stronger on implemented systems, failure analysis and bounded claims than on research positioning and experimental interpretation. I would not yet call it a finished research defence. The professor can understand what was built and what failed, but still has to reconstruct the precise contribution, why the evaluation instruments are trustworthy, and which successful component results transfer to the integrated system.

This is a judgement against graduate-level CS expectations, not a predicted university grade. A professional software-engineering audience needs fewer general definitions and more evidence about interfaces, controls, alternatives, measurement and limitations.

## Priority findings

### High: the central research contribution is implicit (slides 2, 3, 32)

The opening asks a broad question about correct, controlled and useful support. The conclusion lists a prototype and findings, but does not distinguish an implementation deliverable from a research contribution. The deck risks sounding like a sequence of development incidents.

Use the existing opening/conclusion space to state an explicit empirical thesis. For example: “The evaluated prototype exposes failures at evidence selection, action fallback and objective scope. We compare repairs at those boundaries while retaining shared execution controls.” Then identify the actual contributions: an inspectable persistent-support prototype, bounded component comparisons including unsuccessful candidates, and an exact-objective completion correction with regression evidence. Treat this wording as a synthesis of this project, not a universal causal theorem or a novel learning algorithm.

Likely question: “What knowledge did this work produce beyond implementing this application?” The answer should identify the measured design lessons and their limits. BKT, UML and retrieval algorithms themselves are not the claimed novelty. A short comparison with the capabilities of a reactive course assistant would help position the work; it does not require a general AI or software-engineering lecture.

### High: the planner result lacks enough measurement detail (slides 17–18, 40)

Slide 18 says utility improved from 0.7954 to 0.8002 but gives neither the paired uncertainty nor enough explanation of the scoring instrument. A professor can reasonably ask whether the gain is noise, useful in practice, or favoured by the same analytic model used to choose the action.

The committed Study C record supports a paired difference of +0.004805 with a 95% interval of [0.003065, 0.006760] over 1,000 pairs. Put the difference and interval beside the means. Explain the utility components and weight provenance in backup, including the relationship between the analytic selector and evaluation oracle. The observed gain is about 0.6% of the control mean; the interval excluding zero does not establish practical educational value.

The study recorded 801 provider calls, four failed calls and USD 0.335790 reported cost. These are historical run totals, not a current price estimate or a controlled latency comparison. They provide an engineering cost context for the small gain. The already-visible missing analytic-only ablation is essential and should remain explicit.

Source: [Study C machine-readable record](../../../research/05_evaluation/records/successor-architecture-confirmation-005-001.json).

### High: simulator assumptions and baseline fairness deserve visible treatment (slides 19–22, 39)

Separating hidden-state MSE from next-answer Brier score is a strong improvement. However, “held-out seeds” can sound more independent than this study is. Development and test learners come from the same author-defined simulator families. One family is BKT-like. The count baseline has neither parameter fitting nor forgetting, whereas the alternatives have fitted parameters and time-dependent behaviour.

State these as construct-validity and comparison limitations in the main learner discussion. The source reports the hidden-state advantage in both families, which narrows but does not remove simulator alignment concerns. The appropriate next comparisons are a decayed-count baseline and a third, differently structured simulator family. This does not invalidate the existing bounded result; it limits the inference to the tested baseline and simulator assumptions.

Likely question: “Did BKT win because your simulated learners behave like BKT?” A good answer acknowledges the model-family relationship, the second family, the missing stronger baseline, and the inconclusive next-answer result.

Source: [Study E, limitations and decision](../../../research/05_evaluation/successor-learner-timing-simulation-001-results.md).

### High: factual evaluation needs denominator and instrument clarity (slides 12–15)

Slide 14 says metrics use their eligible case sets but leaves the audience to infer those sets. Show 800 answerable cases and 200 boundary cases. The BM25 grounded result is 506/800; boundary accuracy is 192/200. Its recorded grounded-success interval is 58.75%–67.63%, bootstrapped by source family. Avoid implying that the small BM25/hybrid difference establishes general superiority without a paired comparison supporting that claim.

A compact caveat should explain that mechanically generated questions and rigid target-to-claim selection affect this benchmark. The source gives a malformed question about “the source point about 2”; this matters to the interpretation of the score. The labelled illustrative example on slide 12 explains completeness, but it is not evidence that all measured failures had that simple cause.

The analysis correction leaves the grounded score and Refine decision unchanged. It does narrow source-version validity and notes missing raw artifacts for some other historical runs. If discussing “zero severe releases”, clarify that this means releasing an answer when the expected action was not answer; it does not mean zero unsupported claims.

Sources: [Study B](../../../research/05_evaluation/final-cross-method-factual-confirmation-001-results.md), [reporting correction](../../../research/05_evaluation/records/final-cross-method-factual-confirmation-001-analysis-correction-001.json).

### Medium: completion correctness and pedagogical validity need a sharper boundary (slides 8, 25–26)

The 12-to-0 unsupported completion result is a strong software-engineering finding. The independent audit checks committed evidence against an explicit completion contract. However, two correct assessments, no incorrect assessment and confidence at least 0.5 define the contract; they do not validate mastery or the correctness of the upstream assessment process.

State that the correction establishes objective-scope compliance in the tested histories. Avoid turning zero observed violations into a population guarantee. The source explicitly says the finite dependent history grid does not justify a population error-rate interval. Be ready to explain the consequence of an earlier incorrect assessment and why the threshold is appropriate for this prototype. Also distinguish an independent implementation of a contract audit from independent educational validation.

Source: [Study H](../../../research/05_evaluation/goal-completion-scope-development-001-results.md).

### Medium: the architecture diagram should identify the compared interfaces (slides 7, 17, 23, 27–28)

The native C4/UML views convey concrete boundaries and make good use of the audience's SE background. The container view alone does not show where the evidence selector, planner, wording generator and learner adapter sit. Yet those are the main experimental units. Label these interface locations in the existing architecture view or provide a focused standard component view in backup.

Authority rechecks and retry recovery are concrete engineering strengths. Explain each as an invariant under a stated failure scenario, with pointers to the relevant tests. Do not imply that these functional checks establish a deployment, throughput or distributed exactly-once benchmark. The deck already limits these claims appropriately.

### Medium: the talk is feasible but visually and cognitively demanding (slides 4–9, 19–23, 27–28)

The estimated 32.1–33.7 minutes includes speech at 170–180 words per minute and the video, but excludes transitions, pauses and time to read diagrams. Fast speech does not give the audience more processing time. Dense sequence and container diagrams need deliberate pointing and a short pause after the main inference.

The new charts are substantially clearer than the former result tables. The remaining architecture and sequence labels are smaller than the principal slide text. Share the slide at full size; avoid presenting it in a small meeting window. If rehearsal exceeds 35 minutes, condense the early lifecycle explanation or move one recovery sequence to backup. Preserve the experiment method, failed-design reasoning and result limitations.

The video should receive one spoken viewing instruction: notice the first message after the student stops typing, then the effect of pause/consent controls. It demonstrates execution under accelerated synthetic conditions. It cannot by itself establish longitudinal teaching quality.

### Medium: the supporting Q&A file had stale slide references

The packaged `defence-notes.md` described an older 24-slide structure. This could cause confusion during an online defence. A new `defence-notes-graduate.md` maps the questions to the current deck and adds contribution, simulator-bias and utility questions. The original file and the reviewed slides are preserved. Use the new support file for rehearsal.

## Assessment by aspect

| Aspect | Assessment | What would raise it to defence readiness |
| --- | --- | --- |
| CS / SE technical depth | Substantial implementation and boundary analysis | Locate experimental interfaces and state tested invariants |
| Research contribution | Plausible but implicit | State the empirical thesis and distinguish delivery from knowledge contribution |
| Experimental method | Strong comparison discipline, uneven explanation | Make denominators, control fairness and uncertainty visible |
| Validity and claim strength | Good restraint about real learning | Surface simulator assumptions, scorer limits and assessment validity |
| Failure analysis | A major strength | Keep mechanisms and bounded lessons, avoid generalising one composition's failure |
| Narrative | Coherent but many experiments compete for attention | Link each study back to the central research question |
| Visual design | Restrained, clearer charts, informative captions | Improve a few dense diagram labels and cue what to inspect |
| Oral delivery | Script and video provide useful support | Rehearse with pauses and a full-size screen-share layout |
| Reproducibility / traceability | Extensive notes and result records | Use current Q&A numbering; keep run configuration and artifact limitations accessible |

## Recommended next revision

Prioritise five changes within existing slides: clarify the contribution, add planner effect/uncertainty, expose simulator and baseline limitations, show factual denominators/scorer scope, and distinguish completion-contract correctness from mastery validation. Keep the failed designs and evaluation corrections in the main talk. Put full formulas, configurations, test references and secondary comparisons in backup.

The review does not require a new experiment or a claim that the project has proven educational effectiveness. It requires the presentation to make the existing evidence and its limits easier to examine.

## Review scope

Reviewed slide content and renderings, English speaker notes, the existing Q&A material, source evaluation summaries, and the relevant committed machine-readable records. No new evaluation or hidden-gold access occurred. Earlier visual and structural checks passed, but they do not establish academic validity. Native Microsoft PowerPoint video playback remains untested. No university-specific rubric was supplied.
