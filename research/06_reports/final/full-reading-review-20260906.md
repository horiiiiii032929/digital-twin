# Full submission reading review — 6 September 2026

## Scope completed

Read the entire standalone abstract (1 page) and combined report and appendices (361 pages): **362/362 pages**. This includes every printed paragraph, table entry, figure label/caption, reference, archived result extract, design/method reconciliation row and prospective-plan listing. The detailed appendix was read sequentially through S-326, not merely searched for keywords. This supersedes the limited reading scope of [the previous review](interpretation-review-20260906.md); that review's detailed main-text findings remain applicable.

This is a review, not a revision. Submission PDFs and report sources have not been changed. Coverage, source SHA-256 hashes, extracted pages and selected rendered pages are retained in `reports/generated/full-reading-review-20260906/`. Visual spot checks were performed on combined PDF pages 25, 30, 91, 122, 125, 154, 254 and 280. These are not a claim of pixel-level inspection of every page. Reading all printed material is also not independent reproduction of all 474 registered result entries, inspection of every omitted raw log, or an external plagiarism certification.

## Principal interpretation

The report does **not establish that students learn nothing**. No real-student learning-effect study is reported. Its evidence comprises working software paths, output-quality evaluations, operational simulations, and several different deterministic/seeded learner simulations. Their comparators and measured quantities must remain separate:

- The goal-completion repair compares old and corrected implementations. Mean final simulated mastery in the autonomous arms changes from 0.3632 to 0.3608. This is neither a tutoring-versus-no-tutoring experiment nor evidence that students cannot learn.
- Historical persona simulation reports a positive autonomous-versus-reactive simulator difference of 0.0498 (95% interval 0.0351–0.0658; S-157–S-158). It belongs to its historical configuration and simulator, not the final repaired system or real students.
- The separate learner-estimator/timing study is research on simulated mechanisms, not an integrated release result.
- The 24-history live-model operational run exercises real model calls and product services over virtual time, but explicitly does not score mastery change (S-221 and S-312). Its 654 calls and 484 turns cannot support a learning-effect conclusion.
- Actual output failures, generic proactive messages and unmet factual-quality gates remain real limitations; clarifying the scope must not remove them.

Suggested abstract wording: “The correction eliminated the observed unsupported goal completions, but did not increase mean final simulator mastery relative to the previous implementation. The evaluations used synthetic students and teaching profiles; effects on real-student learning and fidelity to the actual instructor remain untested.” Keep this distinct from the live-model study.

## Confirmed corrections with highest priority

1. **Missing comparator and overbroad learning language:** abstract; main pp. 21–22, 29; S-126. Replace whole-system teaching conclusions with the specific comparison and endpoint. The previous review provides sentence-level replacements.
2. **Wrong experimental evidence under a correction entry:** S-241–S-242, `evidence-range-match-correction-001`. The correction's status concerns identical sealed-pair decisions and 50 failures/561 passes/22 errors, but its configuration/results instead present the 50.0% versus 36.8% evidence-gate selection experiment. Verified in `design-appendix.tex` and result-registry line 63: the registry itself links to `product-evidence-gate-selection-004` records. Repair the association rather than rewriting the correction as a quality improvement. Preserve its actual instrument and evidence.
3. **Different estimators joined to one interval:** S-49 and S-265. Program 011's source explicitly distinguishes pooled success 44.16% from the hierarchical source-family estimate 42.94%, whose interval is 41.03–44.96%. State both estimates correctly or attach the interval only to 42.94%.
4. **Unclear or missing correction chains:** S-155 points toward invalid confirmation 027 instead of distinguishing the later valid 028; S-143–S-144 and S-203 need the revocation explained at S-204; S-236–S-237 need the production-claim correction at S-257. Historical successes should remain, with conspicuous forward references to their final disposition. Later reconciliation rows alone are insufficient for a reader opening an individual entry.
5. **Wrong or unclear observation units:** main p.19 “44/48 useful outputs” refers to scored targets, not 48 independent outputs/students. S-263 divides ten useful results by 112 planned slots when only twelve reached review and 100 were blocked: distinguish pipeline yield from delivered-response quality. Several archived action rates count events, not histories (S-142, S-151). Define denominators locally.
6. **Provider completion inconsistency:** S-197 says 106/107 completed, while the recorded rate is 0.9814814815 (106/108). Both values occur in the source Markdown/JSON, so this is an upstream inconsistency, not a PDF-only typo. Resolve against the ledger before choosing a value. The adjacent 71 complete clusters versus 63 quota-selected clusters is explained by source modality quotas and should be stated explicitly, not treated as a contradiction.
7. **False impression of unauthorized execution:** S-245 reproduces `live_authorized = False` beside 36 actual calls, then refers to a metadata correction “documented above” that was not included. Include the actual correction annotation and provenance; do not infer misconduct from the stale field.
8. **Visible text corruption:** S-56, S-87 and S-219 contain joined English words, confirmed in page renders. S-90/S-119 visibly print “Plan ů Record.” References 18/19 on main p.25 have doubled punctuation. Main p.30 command flags render as single long dashes; use literal code rendering. These are actual PDF defects, not just extraction artifacts.

## Other editorial and evidence concerns

The page-by-page notes below retain all additional concerns, including items that require source verification. Do not treat an audit candidate as a proven numerical error. In particular, attribution to a “human,” “researcher,” or “independent” reviewer needs actor-level provenance; the report should distinguish author/Codex review, another model, and a real independent human. No fabrication or plagiarism is alleged by this review.

Recurring issues include unexplained numeric configuration values, historical pending-review text beside completed ratings, zero used for an unmeasured/no-action metric, bounded local tests described too broadly, references to omitted excerpts, and exact-string reconciliation that misses semantically corresponding completed runs. Keep archival IDs for traceability but introduce descriptive names and final dispositions. The plans section correctly warns that missing direct links do not establish nonexecution; improve those links rather than relabeling all such plans “never executed.”

## Complete reading notes

These notes were recorded during sequential reading; confirmed findings above take precedence over preliminary wording below.

### Reading batch 1: abstract; main 1–10

Prior abstract scope issues retained. Main explicitly distinguishes requirements from implementation and planner proxy from evidence. Figures 1–5 labels read. No new factual finding from these pages.

### Reading batch 2: main 11–35

Prior 16 findings confirmed. Additional editorial candidates: semicolon followed by The/Its on pp21,26,34; n.d.. on p25 references18–19; command double hyphens rendered as en dash on p30. Read all captions and numeric rows; references read as printed, not freshly externally verified.

### Reading batch 3: S-1–S-8

Read all fields. S-5 dataset/size private draft 5 development cases is ambiguous: draft version5, not five cases; body says40. S-7 researcher-verified100 cases and explicit adjudication need attribution verification (not assume human). S-8 old dropped dependency versions differ from current table but historical scope explicit.

### Reading batch 4: S-9–S-15

All fields read. S-9 dangling numbered list 2. from excerpt; S-10 unmatched placeholder [local artifact; [excerpt; full source linked]; S-11 Pages previews typo. Triage correction correctly reverses path-based253 supporting/179 exclusions and is not evidence loss. Rehearsal failure correctly not product-quality failure.

### Reading batch 5: S-16–S-22

All fields read. S-20 original 10000 pipeline entry reports all gates passed but lacks adjacent pointer to its later analysis correction; recommend explicit latest interpretation link at original. Manual/direct review wording S-16/S-19/S-20 needs reviewer identity, not silently treat as human. Invalid calibration/build comparisons correctly marked no quality.

### Reading batch 6: S-23–S-29

All fields read. Historical no-quality conclusions for invalid semantic output must distinguish observed defect vs unavailable population estimate; S-25 cannot support reviewer-quality conclusion should not erase actual semantic inconsistency. S-28 two defects recorded, so no-quality is not no evidence at all. Multiple build rows falsely comparable controls historical/not rerun but labels sufficient except some global gate=True misleading.

### Reading batch 7: S-30–S-36

All fields read. S-30 same0.904 accepted-model gateFalse reviewer-acceptance gateTrue with undisplayed thresholds needs definition; provider-completion1 with zero provider calls should be N/A rather than100% unless convention explicit. S-31/S-33 historical build controls not contemporaneous measurements. S-35 Sunday release obsolete timeline cue. No unsupported learning claims.

### Reading batch 8: S-37–S-43

All fields read. S-37 diagnostic invalid reference rates explicitly bounded. S-42 fresh atomic corpus improvement cannot alone establish AFQC103 failure dominated by overlapping references: causal attribution needs original diagnostic support, phrase confirms is too strong absent that. S-43 additional supported facts penalized off-target clarifies grounding failures are not all falsehoods.

### Reading batch 9: S-44–S-50

All fields read. S-44 evidence37/41 equivalent supports S42 diagnosis but new cohort still not causal isolation. S-44 markdown blockquote > leaks into prose. S-48–49 provider-completion-rate7/80 and32/80 measures planned workload completion not successful attempted calls: rename. S-49 status pairs44.16 with CI41.03–44.96 but prose says hierarchical estimate42.94: attach CI to correct estimator. S-50 configurations 1/2 undefined stand-alone labels.

### Reading batch 10: S-51–S-57

All fields read. S-54 audited regression warning correctly adjacent and should model missing original corrections. S-56 severe unspaced English Assistantreview,notindependenthumanvalidation and Noqualitycomparisonpasswith17externalfailures; S-57 sample rationale concatenated similarly. S-51 undefined issue153/157 are reproduction IDs but add GitHub issue labels. S-55 duplicated results/failure prose is redundant.

### Reading batch 11: S-58–S-64

All fields read. S58 bash npm command concatenation invalid as rendered; S59–62 OCR is injected/instrument-authored not general scannedPDF validation (current main correctly states unqualified). S64 fresh reference package reuses aggregate007 accepted cases hence fresh wording requires source-disjoint relative whom; source claim known development preserved at S47. Relativep95 failures not zero quality.

### Reading batch 12: S-65–S-71

All fields read. S65–67 ColPali run name actuallyJina v4; identify real model prominently. Both visual product arms had criticalcitation defects, omitted mainhistoricalv4 sentence but recorded elsewhere. S66 duplicated configuration/results metrics. S71 generation stability cost subtotal explicit; no selectedgeneral gain. Injected64 control notactualLLMcalls correctly distinguished but fixed envelope64calls might confuse.

### Reading batch 13: S-72–S-78

All fields read. Independent in runID historical but assistant unblinded explicitly identified. S73 64input bytes suggests64 bytes instead of64 input records; verify source wording. S75/76 generic root-only reviewer means primary Codex agent, should expand. S75 firsttrialpending latertrial appears adjacent adequate. S78 no learning outcome explicit; onlyday1–3delivery disproves general30dayproactive coverage but clear limitation.

### Reading batch 14: S-79–S-85

All fields read. Concrete internal contradiction S81–83 boundaryv7/v8/v9: status useful6/8 or8/8 yet limitation semanticreview pending. Likely stale machine limitation vs later reviewed registry; reconcile dates and reviewer artifacts. Missing numeric dataset count for v14 boundary/main/mixed entries generic trial1 insufficient. All persisted budget numbers are reserved not spend, labels preserve.

### Reading batch 15: S-86–S-92

All fields read. S86 confirmation48 contexts actually48 target slots16primary repeated3; previous finding7 use targets right. S87 heavily concatenated prose. S90 Plan ů Record corrupted separator; verify rendered. S91–92 safe failures8/29 =8control and29candidate NOT rate8of29; rewrite distinct armcounts. S90 eightcontexts or24profile is sharedboilerplate differscurrent16histories, clarify onlyapplicablegrid.

### Reading batch 16: S-93–S-99

['Mixed-stage v7/v8/v9 likewise show completed usefulness ratings but stale semantic review pending limitations.', 'Stability trial decisions pending complete group review need forward link to completed aggregate judgment, not silently removed history.']

### Reading batch 17: S-100–S-115

['S-101–103 main v7/v8/v9 repeat stale pending semantic review despite completed useful ratings.', 'S-111 literal Markdown > markers appear in correction prose.', 'S-104 explicitly invalid C0-C3 result still has unqualified isolate policy/isolate retrieval explanatory prose; preserve invalid banner prominently.', 'S-105 independent audit is assistant review, not independent human confirmation; later sentence clarifies but naming ambiguous.']

### Reading batch 18: S-116–S-123

['S-116 machine pending content review fields coexist with completed registry judgment; label historical stage.', 'S-119 Plan ů Record repeated corruption.', 'S-120–122 profile trial boilerplate describes 48 main contexts whereas rows are 24 profile conditions; group/local denominators need distinction.']

### Reading batch 19: S-124–S-130

['S-126 confirms overbroad Correctness improved without teaching improvement; simulator mean -0.0024 is correction-versus-original, not tutoring-versus-no-tutoring.', 'S-127 candidate repeats no learning-quality improvement without comparator.', 'S-124 aggregate messages_sent=14 likely per learner mean, needs unit unlike total count; source check needed.', 'S-130 dirty execution invalid in earlier frozen protocol versus later dirty-tree runs legitimate if source ZIP frozen; not blanket contradiction.']

### Reading batch 20: S-131–S-138

['S-134 disabled worker finite-job-terminal-rate=0 conflates no eligible jobs with failure; control not measured termination denominator.', 'S-136 52.66 ->89.42 ->91.64 sequence is across different folds and includes invalid round; explicit caveat present but arrow implies longitudinal same-test improvement.', 'S-134–138 numeric configuration identities 1/2/3 obscure architecture interpretation.']

### Reading batch 21: S-139–S-146

['S-142 action-validity 0.990854 not obvious denominator from 30 errors/820 cases (likely 3280 turns); expose event denominator.', 'S-145 explicitly reports p95 latency as zero because incomplete distribution; should missing/not measured.', 'S-143/144 same 820 saved outcomes appear in correction and profile selection; not additional independent runs.']

### Reading batch 22: S-147–S-154

['S-147 one zero-row verifier batch supports observed contract failure, not estimated general model reliability.', 'S-148 explicitly preserves original Keep overridden by omitted action gate; clear useful correction, no new contradiction.', 'S-151 82.53% is action/event denominator, not fraction 820 histories passing; specify denominator.']

### Reading batch 23: S-155–S-162

['S-155 invalid 025 limitation says decision evidence is confirmation 027, but next entry 027 is invalid; confirmed stale cross-reference should trace final 028.', 'S-157–158 positive simulated mastery +0.0498 versus T0 is historical different experiment, reinforcing no blanket no-learning conclusion.', 'S-158 deterministic semantic validation accepted wording bank needs distinguish lexical frame checks from human semantics.', 'S-162 provider-backed graph regression followed zero network/provider calls needs label injected transport; otherwise appears contradictory.']

### Reading batch 24: S-163–S-170

['S-165 confirms final valid corpus decision is 028, correcting stale 027 pointer S-155.', 'S-166–167 release bindings show inherited 520 candidate cases though referenced 670 package autonomous370 + reactive150; distinguish composite V2 aggregate from autonomous-only.', 'S-170 local reranker undeployability appropriately scoped to exact hardware and configuration.']

### Reading batch 25: S-171–S-178

['S-175–176 latency below 30-second floor should ceiling.', 'S-171 96/96 attempts includes 24 pre-provider boundary stops; not 96 external calls.', 'S-172 long identical paragraph duplicated in results and failure fields; redundant extraction not independent evidence.']

### Reading batch 26: S-179–S-186

['S-182/183 historical absent control reports focused-test-pass-rate0 and sensitivity0 without executed tests; N/A needed to avoid fabricated measured failures.', 'S-184 calls 100 local requests capacity requests though limited deterministic workload, preserve limitation.', 'S-185/186 10000 construction stage explicitly build only and cannot count as model-quality cases.']

### Reading batch 27: S-187–S-194

['S-191/192 no-action control source-lineage-validity0 reflects no detections not invalid citations; precision undefined if no delivery.', 'S-193 reduced emergency cost ceiling is budget design, not measured cost efficiency or demonstrated unchanged advisory quality.', 'S-194 Sunday boundary historical deadline should dated or removed from reader-facing decision.']

### Reading batch 28: S-195–S-202

['S-197 says106/107 completed but completion rate0.981481 (=106/108), discrepancy needs original attempted/ledger denominator.', 'S-197 complete clusters71 versus prose63 of100 reflect quota filtering; explain 71eligible/63quota usable, not apparent contradiction.', 'S-195 counts of tests and audited files as comparative hard gates favor newer code by construction; bookkeeping not method quality.']

### Reading batch 29: S-203–S-210

['S-204 explicitly revokes confirmation013 and derived qualification; original S-143/144/203 entries lack adjacent revocation notice, serious current-status ambiguity.', 'S-208–209 coverage audit claims bounds what public inputs can achieve, but next correction explicitly denies universal task ceiling; add correction pointer at original.', 'S-208 backtick _coverage rendered as curly quotation symbols, cosmetic.', 'S-210 qualification003 references revoked confirmation001; current binding correction005 later, chronological pointers needed.']

### Reading batch 30: S-211–S-218

['S-212 tie-set audit universal measured floor and S-213/214 later qualification boilerplate still use floor after correction disallows universal ceiling; historical interpretation annotation needed.', 'S-213 title after professor-feedback completion could imply professor participated; actual workflow implementation versus real professor feedback must distinguish.', 'S-215 43 surface passes correctly invalidated after checkpoint-log error; demonstrates checklist not sufficient, useful preserved failure.', 'S-218 load six dependent bursts properly distinguished from180 pedagogical cases.']

### Reading batch 31: S-219–S-226

['S-219 severe missing spaces in timeout diagnostic limitation prose.', 'S-221 explicitly NO simulated or human mastery delta scored confirms main21 inaccurate learning/forgetting simulation wording.', 'S-224 attempt005 says final trial adds negatives while006 actually expands139 to143; group summary reused in005 needs distinguish chronology.', 'S-225 correct missing usage zero handling is current fix, historical missing-as-zero records not globally recertified.']

### Reading batch 32: S-227–S-234

['S-232 no-inference build says proves endpoint compatibility/readiness; later400 contradicts empirical implication; qualify metadata-level advertised compatibility.', 'S-234 fixed BM25 comparison appropriately not selected production retriever; no overall gate quality inference.', 'S-228 Wilson intervals on small designed probes descriptive only, reused development disclosed.']

### Reading batch 33: S-235–S-242

['S-241–242 evidence-range-match correction appears to contain wrong copied selection004 results: says identical decisions/tests in status but Promote50 vs36.8 in results; also mislabeled factual metric corrected elsewhere.', 'S-235 Human-confirmed refers four policy/scope examples, not120 semantic annotations; current wording reasonably delimited.', 'S-240 substantial safer comparison must use paired100 subset not500 versus100 raw score; source should clarify.']

### Reading batch 34: S-243–S-250

['S-245 live_authorized=False and Raw metadata correction documented above but correction omitted in excerpt; apparent unauthorized run unless add actual correction text.', 'S-249 group V11 pending content gates may truly pending unlike completed rows; source final review status check.', 'S-250 56scenario pairs;112controls perarm terminology unclear target cases/conditions not all controls.', 'S-248 concurrency gate configured5 observed1 correctly disclosed; no claiming passed5.']

### Reading batch 35: S-251–S-258

['S-256 human audit accepted seven controls needs provenance confirming user actually checked content; same concern S-7.', 'S-257 NLI correction revokes production interpretation; original S-236/237 lacks immediate later-correction pointer.', 'S-253 output cap improvement only truncations4->0 but count violations1->7, cannot report unilateral success.']

### Reading batch 36: S-259–S-266

['S-263 audit002 useful_rate10/112 uses blocked100 as failed output denominator despite only12 reached; must label planned-scope throughput, not semantic-quality rate like103/112control.', 'S-260 zero severe releases only boundary wrong-answer metric, not all unsupported claims; crucial definition preserved.', 'S-265 same pooled44.16/clusterCI estimator mismatch recurs design row11.', 'S-265/266 matching literal run IDs marks explicit confirmation020/Program011 no exact registered run identifier; not missing entry but reconciliation is lexical rather than semantic linkage.']

### Reading batch 37: S-267–S-274

['S-272 decision row56 retains one false pass interpretation later reclassified cross-layer diagnostic; add correction note at historical row.', 'S-269 Claude Code consumer review authorization historical entry must distinguish implemented model review from author AI-writing disclosure Codex only; do not infer user lied or change without evidence.', 'S-267 past planning scale10prof20courses100clients is plan, not achieved coverage; context-only heading appropriate.']

### Reading batch 38: S-275–S-282

['Historical design decisions include many superseded instructions; chapter heading establishes context not new work.', 'S-275 triage original label dispositions immediately followed later correction within same chapter; chronology clear, but direct pointer better.', 'S-282 scale count cumulative10000 versus remaining9000 explicit, no new arithmetic concern.']

### Reading batch 39: S-283–S-290

['S-283 decision125 treats query/evidence scoring wrong boundary too categorical fromthree failed instantiations; narrow tested methods.', 'S-287 prevents replication inflation claim does not establish statistical independence from nonoverlap alone.', 'S-288 vendor uptime/speed quoted as historical metadata not project measurement; citations only Source log, direct vendor provenance desirable if retained.']

### Reading batch 40

S291–S326 read in full. S312 method catalog repeats old 39/44 containment but explicitly not semantic quality. S314–S326 are linkage-based plan inventory: not evidence of nonexecution; intro correctly qualifies. Hybrid review v3/v4/v5 plan links only preceding invalid attempts, so these do not establish execution of named successors. S325 question-specific plan lacks execution link despite live005 catalog entry. S304 revocation follows original selection but earlier standalone results still require forward pointers.

## Review disposition

Full printed-text reading is complete. Corrections remain outstanding; this document does not certify the PDFs as ready without changes. Prioritize claim scope, evidence associations, correction chains and denominators before typographic cleanup. No new experiment or software behavior change is required merely to make these reporting corrections. Preserve all unfavorable historical records and make missing evidence explicit.
