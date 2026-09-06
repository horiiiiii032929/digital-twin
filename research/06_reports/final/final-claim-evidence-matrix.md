# Final claim–evidence matrix

Status: evidence input for report discussion; not report prose

| Prospective claim | Evidence | Final status | Permitted wording boundary |
| --- | --- | --- | --- |
| A governed autonomous tutor was implemented | 670-case confirmation 024, 72-case confirmation 025, exact HTTPS qualification | Supported under synthetic conditions; qualification 011 passed 43/43 | May claim bounded event-driven autonomy, finite loops, persisted goals, proactive in-app action, restart, and rollback under synthetic conditions |
| The system is safe against unsupported autonomous actions | Confirmation 024 reported zero unauthorized actions, scope errors, invalid citation lineage, duplicates, or unbounded loops | Supported for the evaluated synthetic conditions | Do not generalize to all real-world courses or adversaries |
| The selected factual method is high quality | Fresh 1,000-case best arm reached 63.25% fully grounded success and 96.0% boundary accuracy | Not supported | Describe a safety-oriented local fallback and a valid `Refine` result |
| The system has representative visual understanding | Jina v5 reached 16/30 versus text/OCR 26/30; control also had one wrong-region citation | Not supported | State that text/OCR fallback is retained and visual reasoning remains future work |
| The system matches the real professor | C0–C3 proxy 003 produced 45/48 non-empty responses and stopped before review; earlier proxies were invalid or Refine | Not supported | May claim a professor-profile workflow exists, not fidelity |
| The system improves real student learning | Synthetic learner state showed +0.0324 final hidden-mastery proxy, but AUROC was 0.466 and 32.9% of interventions were wasted | Not supported | Report synthetic diagnostic behavior only; no real learning claim |
| The system is usable by representative students | Automated browser and workflow checks only | Not supported | May claim functional local workflows and basic responsive/accessibility smoke |
| The exact local product is operable | HTTPS journey, restart, clean restore, rollback, and browser smoke | Keep: qualification 011 passed 43/43 | May claim the exact qualified local research release; not durable hosted production |

## Terminal interpretations

### Professor-profile proxy

The terminal decision is `Refine`. Missing/empty outputs are treated as a
quality-contract failure rather than a transport excuse, and no profile uplift
is calculated. A synthetic profile may be used to demonstrate workflow, but it
is not a fidelity reference.

### Simulated learner state

The terminal decision is split: Keep the corrected multi-concept bookkeeping
and autonomous safety controls; Go Deeper on prediction and intervention
utility. The learner simulator is useful for regression testing, but cannot
substitute for real learning-outcome evidence.

## Reporting correction and retention

Use [analysis correction 001](../../05_evaluation/final-cross-method-factual-confirmation-001-analysis-correction-001-results.md) alongside the immutable factual result: recorded source-version validity is 717/800 (89.625%); excluding vacuous successes gives 715/800 (89.375%), or 715/798 (89.60%) conditional on citations. Fully grounded success remains 506/800 (63.25%) and Refine is unchanged.

Factual and visual response ledgers remain locally inspectable. Confirmation 024 and qualification 010 currently rely on committed aggregates and artifact hashes; their raw generated artifacts were not found locally. Qualification 010 used deterministic fast paths and does not independently repeat provider-backed confirmation 024.

Correctness-fix qualification 011 adds 51/51 built-image regressions at source `d9ec1a8`; its raw operational and browser evidence is retained locally. See [qualification 011](../../05_evaluation/local-r1-governed-v2-1-release-qualification-011-results.md). It does not change factual or provider-backed claims.

## Development addendum, 2026-09-06: not promoted

The rows above describe their historical configurations. They do not qualify
the changed question-specific/profile candidate or the new schema-18 workflows.
In particular, 025 replaced model-based planning/generation with deterministic
processing; its 30-day histories are not live final-composition validation.

| Work package / prospective claim | New evidence | Current boundary |
| --- | --- | --- |
| G1: natural question-specific answerability | [Natural baseline](../../05_evaluation/natural-course-quality-development-v1-contract-baseline-001-results.md) exposed one missed paraphrase and one admitted missing-detail answer. [Cross-course live005](../../05_evaluation/cross-course-quality-development-001-live-005-results.md) accepted 44/44 external calls and produced 39/44 candidate versus 28/44 incumbent mechanical source-containment checks. | Development progress only. The literal scorer is not a semantic oracle; prior 63.25% factual Refine remains. Four fictional mini-courses do not establish representative real-course quality. |
| G2: delivered teaching-profile response | Earlier [profile development](../../05_evaluation/teaching-profile-responsiveness-development-001-live-001-results.md) remained Refine. The [v2 Luna progression pilot](../../05_evaluation/final-profile-operational-dialogue-development-001-progression-live-001-results.md) and [Terra comparator](../../05_evaluation/final-profile-operational-dialogue-development-001-progression-terra-live-001-results.md) each completed 24 calls over the same four synthetic histories / 16 stimuli, with two safe graph failures each. | Refine progression and partial hints; schema-valid calls and identical action totals hide different failures. Terra cost USD 0.084888 versus Luna USD 0.0113548 without replacement evidence. This reactive, unblinded development comparison does not establish full Terra autonomy, professor fidelity or learning effects. |
| G3: reviewed text/forum ingestion | [Implementation plan and findings](../../04_experiments/2026-09-06-source-ingestion-and-dashboard-completion-plan.md), actual text/Markdown API upload-to-citation/withdrawal tests, schema18 recovery evidence. | Explicit instructor permission/deidentification attestation, not automatic anonymization; no raw-audio transcription or Canvas connector. New API tests do not inherit old 011container qualification. |
| G4: traceable instructor feedback | Same G3/G4 plan; actual six-student journey tests produce five gap learners among six active students within a 30-day release window, plus suppression/expiry/review audit checks. | Source-level difficulty signals, not evaluated concept mastery. Denominator is students with saved messages in the exact release/window, not all enrolled or currently consented students. Proposal review does not automatically change course content. |
| G5: live longitudinal continuity | Retain the [seven-day predecessor](../../05_evaluation/final-profile-live-longitudinal-development-001-live-001-results.md). The [full candidate development run](../../05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md) completed 24 histories over 30 virtual days: 654 actual Luna calls, 24 restarts, 48 consent changes, 16 proactive deliveries and ten synthetic replies; source hashes remained unchanged. | Operational development is now completed, not merely prospective. Of 654 calls, 643 completed and 11 hit output-token limits; 484 tutor turns include 13 safe graph failures and 16 no-evidence responses. Zero deliveries during the scripted consent-disabled interval does not prove useful intervention. Students, attendance, responses and elapsed time remain simulated; 30 virtual days are not 30 days of uptime. No real learning, fidelity or intervention-effect qualification. |
| G6: schema18 recovery and capacity | [Schema18 control](../../05_evaluation/schema18-foundation-development-20260906-001-results.md) retains 42 in-process recovery checks. Actual provider-backed ASGI [serial run 001](../../05_evaluation/final-profile-asgi-tutoring-concurrency-development-20260906-001-results.md) and [bounded concurrent run 002](../../05_evaluation/final-profile-asgi-tutoring-concurrency-development-20260906-002-results.md) each completed 100 POSTs, 150 model calls and 200 saved messages; provider peak increased from one to five. | Keep explicit development concurrency option; serial default and selected profile unchanged. Observed p95 148.576s versus 31.968s includes queueing and co-resident work, not deployed performance. Candidate delivered 91 answers, five questions, three no-evidence responses and one safe graph failure; no semantic-quality pass. Synthetic identity injection excludes production authentication, Docker, TLS and distributed workers. |

### Retained unfavorable cohorts and independent review

[Live001](../../05_evaluation/cross-course-quality-development-001-live-001-results.md)
rejected all 44 external responses at transport integration;
[live002](../../05_evaluation/cross-course-quality-development-001-live-002-results.md)
accepted 24 and rejected 20;
[diagnostic003](../../05_evaluation/cross-course-quality-development-001-diagnostic-003-results.md)
passed two selected questions but did not reproduce the remaining error;
[live004](../../05_evaluation/cross-course-quality-development-001-live-004-results.md)
accepted 27 and rejected 17. They remain separate unsuccessful/development records,
not omitted runs or equivalent quality estimates. Live 005 uses the same open
packet after prospective general contract corrections, not fresh confirmation.

The [operational failure sidecar](../../05_evaluation/cross-course-quality-development-001-live-005-failure-diagnostic-001-results.md)
confirms four injected timeouts failed closed without changing live 005's 39/44
mechanical result. An ecology answer using shorter supported spans has a separate
qualitative false-negative flag; the gold is unchanged. Ledger balance wording,
privacy guidance, duplicate fragments and weak conversational prompts remain
review issues. No independent human or instructor review has been completed.

### Quantity does not replace validity

The [G7 audit](../../../docs/evaluation-quality-audit-2026-09-06.md) preserves the
quality plan's roughly four heterogeneous permitted-course requirement separately
from the one-course UI journey plus isolation check. Proposed 400 answerable,
200 boundary and200 profile opportunities are not a statistical guarantee. For
independent trials, 380/400 has a 95% Wilson interval 92.40–96.74%;196/200 has 94.97–99.22%.
Source-family/dialogue dependence reduces effective sample size; uncertainty
must be clustered, and repeated turns cannot be counted as independent evidence.
There are no real-student learning, instructor-fidelity or university-approved
grading claims in these development records.

### Subsequent validity and operational repairs

| Claim boundary | Registered evidence | Interpretation |
| --- | --- | --- |
| Mechanical and advisory semantic scores are insufficient for quality qualification | [Calibration/cluster audit](../../05_evaluation/evaluation-calibration-cluster-development-20260906-001-results.md), [advisory transfer audit](../../05_evaluation/completion-semantic-review-development-001-live-002-results.md) | Four substantive defects passed mechanical checks; 64/64 advisory calibration did not transfer reliably. Judge dropped as a decision instrument. |
| Explicit output bounds improve format reliability in the measured comparison | [Bounded contract](../../05_evaluation/bounded-contract-progression-development-001-live-001-results.md) | 14/36 versus 0/36 schema failures; neither count measures teaching accuracy. |
| Named-reference routing and usage accounting defects were corrected | [Referents](../../05_evaluation/bounded-contract-progression-development-001-referents-live-001-results.md), [usage integrity](../../05_evaluation/provider-usage-integrity-development-001-results.md) | Narrow development/test evidence; no general language-understanding or billing certification. |
| A joined mixed-source recovery scenario and short authenticated workload completed | [Mixed source](../../05_evaluation/mixed-source-candidate-recovery-development-001-attempt-006-results.md), [HTTPS load](../../05_evaluation/authenticated-loopback-load-development-001-live-001-results.md) | 143 assertions in one injected-provider scenario; separate 180 real calls/POSTs and 360 messages. Six local bursts passed15s p95; only two factual templates, explicit v3. |

### Typed instructional continuation

| Claim boundary | Registered evidence | Interpretation |
| --- | --- | --- |
| Typed questions/feedback/steps improve some development responses but v5 fails its gates | [V5 comparison](../../05_evaluation/paired-pedagogy-development-001-live-001-results.md), [full review](../../05_evaluation/paired-pedagogy-development-live-001-assistant-review.md) | 30/48 versus16/48 useful; 8/16 versus2/16 primary.29 guarded failures preserved; source bindings are not semantic verification. |
| V6 passes the main development packet but fails a distinct boundary packet | [V6 main](../../05_evaluation/paired-pedagogy-development-001-v6-live-001-results.md), [boundary](../../05_evaluation/paired-pedagogy-development-001-boundary-v6-live-001-results.md) | 43/48 and13/16 main useful, against15/48 and1/16 control; boundary6/8 fails7/8. Missing-detail omission and overbroad access restriction remain. Reused development and assistant judgments do not qualify release. |

The [adverse secondary-disclosure erratum](../../05_evaluation/pedagogy-secondary-disclosure-review-erratum-001-results.md)
corrects the original v5 candidate usefulness count from30 to29/48, with one
premature secondary-concept disclosure. It also adds one such critical event to
the v6 run's control without changing that control's15/48 usefulness count.
Original ratings and raw outputs remain preserved; the paper uses the corrected
v5 count. The v6 candidate's43/48 result is unchanged.

[V7 main](../../05_evaluation/paired-pedagogy-development-001-v7-live-001-results.md),
[V7 boundary](../../05_evaluation/paired-pedagogy-development-001-boundary-v7-live-001-results.md)
and [V7 mixed-stage](../../05_evaluation/paired-pedagogy-development-001-mixed-stage-v7-live-001-results.md)
all failed their unchanged gates (33/48,6/8,5/8). Additional schema detail did not
improve correctness: twelve schema failures and ten local rejections remain in
the main candidate denominator. Confirmation was not opened.

[V8 main review](../../05_evaluation/paired-pedagogy-development-v8-live-001-assistant-review.md),
[boundary review](../../05_evaluation/boundary-classification-v8-live-001-assistant-review.md)
and [mixed-stage review](../../05_evaluation/mixed-evidence-stage-v8-live-001-assistant-review.md)
record39/48 (16/16 primary),8/8 and8/8: all narrow gates pass. The broader
decision remains Refine because six explanatory-profile targets receive
questions instead of requested explanations. All264 provider attempts complete;
one additional local rejection remains in the main history. No candidate
critical violation was observed; this is assistant review, not a guarantee or
human fidelity validation. V8 whole-chunk association does not prove entailment.

[V9 review](../../05_evaluation/paired-pedagogy-development-v9-live-001-assistant-review.md)
records45/48 useful targets but11/12 explanatory moves, retaining Refine.
[V10 review](../../05_evaluation/paired-pedagogy-development-v10-live-001-assistant-review.md)
records48/48,16/16 primary and12/12 explanatory moves; its
[boundary](../../05_evaluation/boundary-classification-v10-live-001-assistant-review.md)
and [mixed-stage](../../05_evaluation/mixed-evidence-stage-v10-live-001-assistant-review.md)
reviews both pass8/8. All208 delivered turns were reviewed; one earlier local
rejection remains, with a useful later target. These reused development results
justify opening confirmation, not population accuracy or human-instructor fidelity.

The [once-only V10 confirmation](../../05_evaluation/paired-pedagogy-confirmation-v10-live-001-assistant-review.md)
failed its critical gate:44/48 definite useful,15/16 primary, one wrong-entity
attribution, one uncertain relationship and two local guards. The
[24-case profile comparison](../../05_evaluation/teaching-profile-responsiveness-v10-live-001-assistant-review.md)
also failed:5/6 context-on style responses useful, one unsupported collision-free
checksum guarantee. Three intended teaching-move contrasts were observed, but
only two were fully qualified. No representative accuracy or candidate selection
follows from development48/48. Confirmation is consumed and preserved.

The [three-model short probe](../../05_evaluation/generation-role-model-development-live-001-assistant-review.md)
tied28/28 with81 actual generation calls, providing no positive gain. The
[repeated dialogue/profile study](../../05_evaluation/generation-model-dialogue-stability-development-001-aggregate-assistant-review.md)
then found main useful counts87/96,95/96 and96/96 for Luna-low, Luna-medium and
Sol-low, respectively, but context-on profile counts10/12,11/12 and11/12 with
critical errors in every alias. The1,417 attempts include six provider failures;
31 planned turns were absent and not counted as successes. All configurations
remain Refine. USD2.1051074 is a known-cost subtotal, not a complete bill because
six calls have unknown usage. Repeated source contexts, exposed development data
and assistant review do not establish independent population accuracy.

The [V11 evidence-strength study](../../05_evaluation/evidence-strength-generation-development-001-aggregate-assistant-review.md)
reaches96/96 main targets,32/32 primary targets and24/24 explanatory moves, but
27/28 short targets and10/12 profile-style opportunities. Two unsupported
checksum guarantees remain critical. Both sidecars reach8/8; all452 planned
turns and563 provider calls complete, costingUSD0.2650354. These are successful
execution and narrow dialogue coverage, not semantic qualification. A prior
noncritical local guard in maintrial1 remains visible. V11 is Refine; the next
revision architecture is prospective and not yet a reported improvement.

[V12's revision controls](../../05_evaluation/independent-factual-revision-controls-live-001-assistant-review.md)
repair32/32 defective drafts but preserve only31/32 adequate drafts: the revision
introduces a complete new-concept solution. All64 calls complete atUSD0.367104.
[V13's bounded controls](../../05_evaluation/independent-factual-revision-controls-v13-live-001-assistant-review.md)
preserve40/40 adequate drafts and repair8/8 fresh disclosure drafts, but repair
only29/32 old defects, below30/32. Its80 calls costUSD0.501304; zero observed
critical errors cannot override the failed repair floor. Both remain Refine.
These are authored-draft component controls, not integrated Luna-plus-Sol student
histories.

[V14 conditional controls](../../05_evaluation/independent-factual-revision-controls-v14-live-001-assistant-review.md)
complete112 calls atUSD1.037656 with known usage. They preserve55/56 adequate
drafts and repair54/56 defective drafts in pooled counts, but reach only39/40
prior-preservation and14/16 fresh-repair against separately registered40/40
and16/16 gates. Two critical
errors remain. Pooled109/112 usefulness does not override these gates. The
post-output adjudication was by the root assistant only because the second
reviewer was unavailable; it is not independent human validation. The low-effort
candidate remains Refine.

The preregistered medium-effort comparison passes112/112 in each of
[trial1](../../05_evaluation/independent-factual-revision-controls-001-v14-medium-trial-1-live-001-results.md)
and [trial2](../../05_evaluation/independent-factual-revision-controls-001-v14-medium-trial-2-live-001-results.md).
All separately registered slices pass, with zero observed criticals and known
combined costUSD2.237892. Four adequate drafts in trial1 and one in trial2 were
unnecessarily rewritten but retained the required meanings. Root-only review,
56 reused scenario pairs and a nonconcurrent low reference preclude an
independent accuracy or causal effort-effect claim. Integrated Stage B is now
running under a separately frozen full composition; no release promotion follows
from these authored-draft component results.

The [integrated medium review](../../05_evaluation/conditional-v14-medium-stage-b-assistant-review.md)
retains794 actual calls,452 delivered turns and known costUSD2.5082096. All source
snapshots remain unchanged, with no provider failures. Short28/28, profile12/12
with six contrasts, boundary8/8 and mixed8/8 pass narrow criteria. However, the
[main oracle audit](../../05_evaluation/meaningful-continuation-v2-oracle-audit.md)
invalidates that packet's aggregate for factual qualification: necessary-only
sources were paired with sufficient-condition gold. This limitation applies to
earlier main scores using the same packet; they remain historical observations,
not verified factual evidence. No main pass, zero-critical group claim or release
promotion follows. Versioned correction and fixed-candidate reruns are required.

The original-source necessity diagnostic has consistent gold and fails V14-medium
qualification:7/8 candidate versus4/8 V4, one critical unsupported transaction
guarantee,24 calls/USD0.0807500. See registered
`paired-pedagogy-development-001-conditional-v14-medium-necessity-trial-1-live-001`.
V3 source correction does not eliminate this model failure. V15 remains a rejected
component experiment; do not describe it as an accepted fix.

V15 global assessment remains rejected: trials109/112 and110/112 with three and
one critical disclosures respectively (plus one uncertain ownership claim).
Both component runs registered;224calls/USD2.458640, no actualLuna generation.
Direct V11/Sol-high also fails:6/8necessity and12/16contrasts, six unsupported
positive guarantees across24targets;48pairedcalls/USD0.2182334. Its later stages
were not dispatched. Do not report higher reasoning effort as an accepted fix.

| Claim/update | Evidence | Permitted interpretation | Limit |
|---|---|---|---|
| Fixed V16 did not generalize into a qualifying revision component | fresh-assessment-generalization-comparison-001;two112-control live runs | Both103/112;V16flawed47/56;onecriticaleach;no integration | Authoredsynthetic drafts,assistantreview;noactualLunageneration |
| Final-response verification v1 did not qualify | final-response-support-audit-001-exposed-live-001 | 54 calls, two schema failures; 20 reached/112 planned; known critical missed and five accepted repairs lost direct answers | Incomplete exposed diagnostic, no fresh-bank calls or integration |

| Final-response verification v2 also fails progression | final-response-support-audit-002-exposed-live-001 | 24 calls, one timeout with unknown usage; 12 reached/100 blocked; same strict-rubric critical retained | Differing incomplete subsets prevent full quality comparison; no fresh128 or integration |

| Actual generated-response approval is operationally evidenced | generated-professor-preview-browser-development-001-live-001 | Two real calls; saved response, exact artifact approval, reload persistence and withdrawn-profile rejection; no student runtime writes | One synthetic case, unselected V14-medium; no source-change/server-restart browser test or human fidelity validation |

## Submission narrative reconciliation (6 September 2026)

The canonical manuscript now uses six chapters: objective, course workflow,
runtime decisions, comparative design, integrated verification, and findings.
The agreed comparisons are in the body, not only in the companion:

| Claim | Evidence | Scope |
| --- | --- | --- |
| Typed target/cardinality improves the evidence interface | course-digital-twin-whole-system-architecture-round-2-001 | 253/397 to 355/397 on one development fold; Refine, not release qualification |
| Guarded planning improves registered utility | successor-architecture-confirmation-005-001 | 1,000 contexts; 0.7954 to 0.8002, preferred agreement 74% to 73% |
| Luna/Luna advances under the engine allocation rule | successor-architecture-engine-comparison-006-001 | Four allocations, 300 contexts each; alternatives did not satisfy positive-lower-bound rule |
| BKT/value is a promising timing hypothesis | successor-learner-timing-simulation-001 | All nine combinations plus two bounds retained; simulator only, not wired into default product adapter |
| Objective-scoped completion fixes an actual lifecycle defect | goal-completion-scope-development-001 and separate baseline/candidate records | Matched 72-history arms, 12 to zero unsupported completions; no simulated learning improvement |
| Original 025 cannot qualify target-scoped goal completion | goal-completion-scope-review-audit-001 | Ten unsupported completions in eight histories; original records remain unchanged |

Runtime calculation and assessment accounting are documented separately:
learner_belief.py accumulates concept-specific assessment counts; the default
planning_architectures.py adapter still builds delivery/event-based proxies.
Neither is a calibrated estimate of actual student mastery.
