# Online presentation speaker script

Prepared: 7 September 2026. Revision 9, aligned with the [24-slide structure](presentation-structure.md).
Status: script draft; no actual slides produced.

今回追加したオーナー視点を含む本編原稿。英語本文5,044語。動画60秒と操作45秒を加えた目安は以下。正式な時間枠が変更されたと断定しない。

| 仮の読み上げ速度 | 本編 |
| --- | ---: |
| 毎分130語 | 40:33 |
| 毎分140語 | 37:47 |
| 毎分150語 | 35:23 |

操作メモは読まない。録画は4枚目。5枚目は提出資料の保存応答であり、新規録画と同一実験とはしない。

## Main presentation

### 01. An Instructor-Configurable Digital Twin for Autonomous Course Tutoring

目安: 20秒。

**English script**

This project aimed to connect an instructor's course materials and teaching settings to continuing student support. I will first show what the prototype delivers and what remains unvalidated. I will then explain the system designs I tried, the failures that changed my decisions, and the work needed to address the remaining gaps.

**操作メモ:** 最小限のタイトル。録画の注目点は原稿の最後で伝える。 考察: AI教育の一般的背景やRAGの定義を置かず、製品と実際の失敗へ入る。 出典: R1/R6。

### 02. What the project delivers against the brief

目安: 75秒。

**English script**

The brief asked for a course Twin that uses instructor materials and teaching preferences, supports students over time, and preserves instructor oversight. This table separates implemented behaviour from demonstrated quality.

The prototype provides course configuration, reviewed publication and student access. Local checks exercised approval, reload, withdrawal and operational recovery. That supports a bounded claim about these workflows.

The factual response path preserves source references, but its fresh grounded-answer score remains below acceptance. Teaching preferences enter the response pathway, but fidelity to the actual instructor has not been validated.

Continuing support is implemented through stored observations, goals and autonomous jobs. An integrated trial exercised delivery and restart controls. A later correction removed unsupported goal completions in a targeted regression. Neither result demonstrates learning benefit for students.

The deliverable is therefore a working research prototype with inspectable decisions and specific local evidence. It has not satisfied all five acceptance requirements. I will use those remaining gaps to explain why the design comparisons matter.

This is also the scope of the recording. It will show operation, while the tables and saved examples explain which quality claims the evidence supports.

**操作メモ:** 5つの依頼項目／実装された挙動／検証の範囲／未達の4列。短いEnglish表にし詳細は話す。 考察: 実装済み、検証済み、未達を同じ成功マークにしない。最後まで待たず成果物の現在地を共有。 出典: R1/R5; acceptance boundaries。

### 03. How instructor settings reach executable behaviour

目安: 75秒。

**English script**

The instructor's settings reach different parts of the software. Approved materials and their permissions determine which source versions the system may use. Learning objectives map to concepts that the assessment and goal logic can inspect.

Proactive action permissions restrict what the planner may choose. Consent, timing and frequency checks constrain delivery. Those are executable controls: a wording model cannot grant itself a prohibited action.

Teaching preferences have a different role. Tone, explanation depth, example preferences and the help sequence enter the configured generation pathway. They guide the response, but their presence in the input does not prove that the output follows the instructor's teaching practice.

The reviewed release binds the relevant configuration. A student message cannot replace the approved teaching profile, and a change in configuration needs an appropriate reviewed binding.

This distinction is important for the owner's acceptance decision. I can show where a permission is enforced and which local checks exercised it. For a teaching preference, I need to inspect what the student actually received. The saved example after the recording shows both a visible response behaviour and the limitation that remained.

**操作メモ:** 具体的な4設定をrelease、各consumer、観測できるeffectへ接続する図。強制条件と生成への入力をラベルで区別。 考察: 設定を入力できることと、その教え方を忠実に実行できることは別の到達点。 出典: R2; profile-examples appendix。

### 04. Recorded simulation

目安: 60秒。

**English script**

[No speech during the recording.]

**操作メモ:** 英語字幕付き60秒動画。仮想時間や待ち時間の編集を表示。録画にない機能を原稿で予告しない。 考察: 映った動作だけを説明し、実学生・正式評価・30日連続稼働の証拠として扱わない。 出典: Recording proposal; actual asset pending。

### 05. A saved teaching-profile response shows partial alignment

目安: 80秒。

**English script**

The saved Socratic profile requested a diagnostic question, a student attempt and then one hint. In the recorded trial, the student asked how slot seal worked in the synthetic course protocol.

The tutor replied: “For ‘How does slot seal work’, what is your current explanation, and which step are you unsure about?”

That response asks the student to explain their current understanding before receiving an answer. It illustrates part of the requested assistance sequence. However, it does not identify the particular conceptual difficulty behind the question. The response remains generic.

A separate saved explanatory context supplied the course rule for a different topic. Because the topic and context differed, those two outputs are not a controlled comparison of changing only the teaching profile. They cannot establish a causal improvement from one profile over the other.

This is the owner's visible gap: the configuration reaches the response pathway, but specific instructional alignment is still incomplete. A stronger test would hold the question, evidence and student state fixed while varying the approved teaching profile, followed by independent review of the resulting instruction. That comparison is a proposed validation, not a result I already have.

**操作メモ:** 左にdiagnostic question/attempt/one hint設定、右にF21の実際の質問と応答。下にattempt elicited／concept-specific diagnosis absentを対応。 考察: 同一質問のprofile切替実験として見せない。設定が原因で改善した、実教授を再現したと断定しない。 出典: R2/R5; profile-examples appendix, saved finding F21; F03 as separate context。

### 06. The design alternatives shared a common product boundary

目安: 90秒。

**English script**

The alternatives did not all change the same part of the system. This diagram separates the comparison boundaries so that the later results have a clear meaning.

The common product contains a published course release, a student conversation path, persistent learner observations, and a worker that can initiate permitted support. Course authority, evidence checks and persistence remain responsibilities of the application. Model proposals do not replace those controls.

One program compared complete architecture manifests, with a lexical control, an evidence-first hierarchy, and a plan-observe design. Its executed comparison used deterministic factual responses to expose evidence-path behaviour. It did not test every proposed capability of those architectures over a student's learning history.

A different program compared autonomous planners. It started with an event rule, added a model proposal, then added analytic lookahead and a verifier. Those candidates shared the product boundary and learner-state plane.

Other comparisons changed learner estimation and intervention timing, or the way approved source material became an instructional response. I will show what each design was intended to fix, which mechanism it added, and what the corresponding experiment found.

This distinction also limits the Twin claim. The product represents instructor settings and course material, but fidelity to the actual instructor remains untested. The contribution here is the implemented integration and the design decisions supported by these bounded comparisons.

**操作メモ:** 共通構造を一度描き、比較対象のevidence、planner、learner adapter、wording境界に実際の候補名を添える。 考察: どの部品を変え、何を固定したかを最初に図で共有。すべてを一つの時系列winner競争にしない。 出典: R3/R4/R5; S1/S4/S5。

### 07. The first whole-system candidates rejected answerable questions

目安: 95秒。

**English script**

The first whole-system comparison tried three complete manifests. The lexical control retrieved course passages and accepted any available hit. The evidence-first candidate added hierarchical retrieval and an explicit coverage check before producing an answer. The plan-observe candidate added bounded question decomposition and combined the resulting retrieval observations before hierarchical coverage.

The intended benefit was more complete evidence for questions that crossed source regions. The actual result went in the opposite direction. On the same four hundred and ninety-five development cases, grounded factual success was about fifty-three percent for the lexical control and about twenty-five percent for each structured candidate.

All three preserved the expected boundary actions and recorded zero severe unsupported releases. The main problem was excessive abstention on answerable questions. The shared coverage rule treated words in the question's framing as concepts that needed evidence. Additional retrieval planning did not remove that mistaken requirement.

The lexical control answered all answerable cases, but it still selected incomplete or incorrect regions. It therefore remained a diagnostic baseline rather than a release-ready design.

This was a deterministic factual comparison without external model calls. It does not prove that hierarchy or event sourcing is generally ineffective, nor does it test every longitudinal feature described by the manifests. It shows that these particular compositions shared an unsuitable question-to-evidence contract. The next design changed that contract instead of simply adding another planning stage.

**操作メモ:** 3つの短い処理経路を同じ入力・出力で比較。hierarchical coverageに入るquestion scaffoldingを失敗点として示す。 考察: 共通coverage欠陥のため両候補の本来の設計価値は十分識別できない。今回のcompositionを採択しない判断と、hierarchy/event sourcingの一般的棄却を区別。 出典: S1/S2; supplementary historical design records。

### 08. Typed targets helped; another ranking stage did not

目安: 90秒。

**English script**

The successor design changed what the answer path received. Instead of asking whether evidence covered the wording of the whole question, it identified the target and the number of facts required. It then selected claims for those requirements.

On the same second development fold, the lexical control produced two hundred and fifty-three fully grounded answers from three hundred and ninety-seven answerable cases. The typed target and fact-count design produced three hundred and fifty-five. Adding section ranking produced exactly the same count.

The added ranking stage also increased measured ninety-fifth-percentile latency from one point three six to two point seven nine milliseconds. These are local deterministic retrieval measurements. The result supplied no quality reason to keep that extra complexity.

The typed design still had errors involving paraphrased targets, neighbouring source regions and missing answer spans. It remained a development baseline with Refine status because no arm passed every quality gate.

The defensible design change here is the typed contract on its own comparison fold. The sequence does not justify combining results from different folds into a single improvement curve.

The later source-range variants remain diagnostic evidence because their comparison violated its candidate-count limit. I preserve that correction with their results in the backup. Their status does not change the valid typed-target comparison just shown.

**操作メモ:** lexical、typed-target、typed+rankingの3経路と同foldの結果表。Round 3数値は補足に置き、選択無効という短い注記。 考察: target/cardinalityを次のdevelopment baselineに。追加rankingは同品質でlatency増。source-range候補の未採択には性能診断と実験規約違反を区別。 出典: R4; Study A; S3/S3c。

### 09. The evidence gate still limited the retained factual path

目安: 95秒。

**English script**

Two further observations explain why the retained factual path still falls short. First, an earlier ambiguity gate compared distinct answers across every candidate above a coverage threshold. In a full course, a weakly related region could compete with the strongest relevant answer. The earlier confirmation used one approved chunk per release, so it could not exercise that competition.

In a later one-hundred-case diagnostic, the target region ranked first in eighty-four cases. Sixty-nine of those still returned clarification. This motivated comparing dominant interpretations rather than treating every weak match equally.

Second, the fresh five-configuration comparison still found a large gap after retrieval. The retained BM25 and dominance-gate composition retrieved complete evidence in ninety-eight percent of eight hundred answerable cases, but produced fully grounded answers in sixty-three point two five percent. The hybrid with the same gate scored sixty-two percent.

The final-answer rubric requires all necessary facts and exact claim-to-citation coverage. Missing a required fact fails the case even when the retrieved set contains it. Normalized text and source ranges make that scorer inspectable, but limit its semantic flexibility.

BM25 remained the simpler local fallback; both configurations failed acceptance. Its separate boundary score was one hundred and ninety-two of two hundred. The diagnostic explains a gate failure, while the fresh study bounds the retained composition's quality. Together they show why retrieval upgrades alone did not resolve the answer contract.

**操作メモ:** 候補集合・dominance gate・claim assemblyの一つの図。診断とfresh結果は別のラベルで失敗位置に対応。 考察: BM25は簡単なfallbackとして保持。全事実と引用対応を要求するscorerにはsemantic flexibilityの限界がある。 出典: R4; L3 diagnostic; Study B。

### 10. Four planner designs changed who selected the action

目安: 100秒。

**English script**

The autonomous-planning program tested a different set of designs. Candidate A selected the preferred permitted action for the event using a deterministic workflow. It provided a simple baseline that could produce a valid move without a planning model.

Candidate B asked a model for a bounded proposal and used the selected action if it stayed inside the permitted envelope. It had no analytic lookahead and no verifier. The hypothesis was that the model could use the supplied state more effectively than the fixed event rule.

Candidate C added an analytic forward model. It compared permitted actions using an inspectable estimate of their immediate and future value. The term hierarchical in this experiment does not mean that several model agents supervised one another. The additional lookahead was deterministic.

Candidate C plus V added a reject-only model verifier after C selected an action. It could accept that action or suppress it. It did not repair the choice by generating a better alternative.

The comparison kept the learner-state plane and product controls shared. Disabling planning recovered A; zero lookahead recovered B; adding verification produced C plus V. This made the added decision stages visible as distinct hypotheses.

These designs offered different ways to improve action choice, but they also introduced new ways to lose a usable action. The following result explains why the most elaborate path was not retained. All effects refer to the supplied synthetic planning contexts, rather than real student learning.

**操作メモ:** 同じ入力と許可action集合から4本の短い経路を描く。追加要素だけを差分として強調。 考察: Cを別のLLM階層やmulti-agent systemとして描かない。モデル数を増やす比較と分析的な先読みを加える比較を区別。 出典: S4/S5; R4 planner history。

### 11. The verifier suppressed useful moves; lookahead had mixed results

目安: 120秒。

**English script**

On the third development fold, the reported acceptable-move rates were about seventy-one percent for A, forty-four for B, seventy-four for C, and forty for C plus V. The lookahead candidate recovered much of the single-model degradation. Adding the verifier then removed that apparent benefit.

The audit found that the reject-only verifier rejected valid moves too often. Its only correction was to suppress the action. A usable action could therefore disappear without a better alternative replacing it. This is the concrete reason the extra verification stage was not retained.

The initial ranking also needed qualification. The acceptable-move metric treated exact agreement with one preferred action as transition validity, even when another action remained inside the instructor-approved envelope. The audit separated those meanings. It also found that A had the highest mean hidden utility and lowest regret, despite C's higher preferred-action agreement.

Five planner failures came from reason text exceeding the local contract. That field was non-authoritative, yet the formatting failure prevented otherwise usable proposals from proceeding. Provider completion was below the required gate.

The run selected no final architecture. Its original measurements remain intact. The next comparison used a fresh fold, normalized the non-authoritative reason field, and separated hard action validity from preferred-label agreement.

This evidence supports a redesign of fallback handling and evaluation. It does not prove that every low-scoring model decision had the same cause, or that verification is always harmful.

The audit compared the two leading candidates case by case. A beat C on hidden utility in thirty cases, while C beat A in eleven. That makes the ranking issue concrete: adding lookahead improved agreement with a preferred label but did not give the better utility trade-off in that fold. The comparison needed both measures before choosing a successor.

**操作メモ:** Cの選択actionがverifierでno-actionになる分岐を強調。Fold003の表にhistorical preferred-action-based metricと明記。 考察: 当時のacceptable-move判定はpreferred-label一致をvalidityと混同。結果を変更せず監査で訂正し、次のfresh比較でvalidityとpreferenceを分けた。B低下の個別原因を全件説明したとしない。 出典: S6/S7。

### 12. The successor preserved the baseline unless a proposal earned replacement

目安: 100秒。

**English script**

The guarded successor changed the failure behaviour of the planner. It began with A's permitted event fallback. A model proposal could replace that fallback only when the analytic model independently agreed and predicted an improvement of at least zero point zero four. Invalid or unsuitable proposals left the baseline action available. Missing authorized evidence still led to no action.

This directly addressed the earlier designs' loss of usable actions. The guard did not simply add another stage that could reject the whole opportunity. It required positive support for a replacement.

On the fresh fourth development fold, all four tested configurations passed action validity. C had seventy-six percent preferred-action agreement, above A's roughly seventy-one percent, but its utility remained below A. The guarded successor improved utility over A and advanced to a separate confirmation.

That confirmation compared A and the guarded design on one thousand shared contexts. Both had one hundred percent valid actions. Mean utility increased from zero point seven nine five four to zero point eight zero zero two. Preferred agreement moved from seventy-four to seventy-three percent; its difference interval included zero.

The decision was conditional progression under the registered synthetic utility objective. The runtime coefficients and replacement margin remain engineering heuristics, not measured educational effects. A purely analytic selector also remains an alternative worth comparing. The evidence supports the tested successor relative to the named controls, while leaving the model's necessity under other designs open.

**操作メモ:** Aのfallbackを主経路に、Hの条件付き置換を描く。Fold004とconfirmationは別表。 考察: 違うfoldを連続成績として比較しない。モデルの必要性と実学生の改善は未立証。 出典: R3/R4; S8; Study C。

### 13. What remains unproven about the model's added value

目安: 75秒。

**English script**

The guard raises a reasonable question: if the analytic model already ranks the actions, what does the language-model proposal add?

The reported comparison does not fully answer that question. Its control was the deterministic event workflow. The guarded composition improved the registered synthetic utility relative to that control. It did not isolate the proposal model against a selector that directly chose the analytic best action.

I therefore retain two different conclusions. The tested guarded composition earned conditional progression under the recorded decision rule. The evidence does not establish that its model call is necessary.

A direct comparison should include the event rule, an analytic-only selector and the guarded composition under the same state inputs. It should examine decision quality together with provider failures, latency and cost. Any extra metadata or wording benefit would need its own observed evidence rather than being assumed.

For the current prototype, the event baseline remains a control. If analytic selection provides the same useful behaviour with less operational burden, that would justify simplifying the planner. This is a proposed decision test, not a claim that the alternative has already won.

**操作メモ:** A event rule／analytic-only candidate／H model proposal＋analytic guardを並べる。analytic-onlyにはnot tested in the cited comparisonと明記。 考察: 学術的有意差だけでLLM必要性を主張しない。残す理由は比較済み構成としての条件付き選択であり不可欠性ではない。 出典: R3 planner rules; R4 Study C; proposed ablation。

### 14. The model comparison retained Luna for both roles

目安: 90秒。

**English script**

The model-allocation comparison kept the guarded architecture fixed and crossed two planner choices with two wording choices. It used three hundred contexts and four allocations, giving twelve hundred context and configuration pairs.

The alternatives produced very small pooled effects. The recorded confidence intervals for the planner utility effect and wording validity effect both included zero. Neither satisfied the selection rule requiring the whole interval to be positive. Luna for planning and Luna for wording remained the simplest and least expensive eligible allocation under that recorded comparison.

One detail changes the reliability interpretation. The Terra-planner and Luna-wording allocation completed two hundred and thirty-eight of two hundred and forty generator calls. Two failures used the deterministic fallback. The final wording could therefore remain valid even though some provider calls failed. That allocation missed the provider-completion gate.

The choice follows the recorded objective, completion requirement and cost comparison. It does not establish that Luna is generally the best model, and it is not a recommendation based on current model prices or availability.

This also limits what model substitution alone can solve. Changing the planner model would still leave the product's delivery-count proxy unless the adapter also changed. The model comparison and the input-quality problem concern different boundaries, so one result cannot stand in for the other.

**操作メモ:** planner/wordingの4構成表。final validityとprovider completionを区別。現在価格を追加しない。 考察: final wording100%validにはfallbackを含む。歴史的study内の選択であり全モデルの現在の優劣ではない。 出典: R4; Study D。

### 15. Estimator and timing combinations changed the intervention trade-off

目安: 120秒。

**English script**

The learner and timing experiment compared two design decisions together. One decision estimated the learner's state using a count baseline, BKT or PFA. The other chose intervention timing using constant, conditional or value-based rules. The simulator evaluated nine combinations and two bounds, with two hundred and forty simulated learners per condition.

The simple count and constant-timing baseline delivered an average of fourteen messages. Conditional timing cut that to seven, but final simulated mastery fell from zero point three one four to zero point three zero two. Sending fewer messages removed some useful practice along with unwanted interventions.

BKT with value-based timing delivered about twelve messages. Its wasted-message fraction fell from roughly fifty-one to thirty percent, while mean final simulated mastery increased to zero point three two eight. The paired intervals supported those differences within the simulator.

That did not justify immediately installing BKT in the product. Its improvement in hidden-state estimation did not establish better next-answer prediction: the Brier-score comparison under constant timing was inconclusive. The product integration with committed observations, a decayed-count control and a third simulator family also remained unfinished.

The design decision was Go Deeper. BKT with value-based timing remained a hypothesis and PFA a comparator. These results show why estimator and timing choices need to be evaluated together. They do not establish real learning effects, and the simulation did not execute text retrieval or generation.

The initial simulation attempt also needed correction because one simulator made forgetting overwhelm learning. The corrected attempt and the invalid result remain separate. This matters for design selection because an estimator or timing rule can look favourable under an unrealistic learner process. A third simulator family and an additional simple control are therefore substantive comparisons, not just more repetitions.

**操作メモ:** estimator×timingの比較格子からcontrol、count/conditional、BKT/valueの3行を強調。全9組＋2boundsは補足。 考察: estimate改善とtiming改善を別軸で比較。BKT next-answer Brier差はinconclusive、simulator仮定と未統合でGo Deeper。 出典: R4; Study E。

### 16. The promising learner design was not connected to the default planner

目安: 85秒。

**English script**

The application still exposes a gap between the experimental learner design and the retained runtime. Goal completion uses committed concept assessments. The default planning adapter instead constructs its state from deliveries and event identifiers.

Its field named mastery probability rises from one half to two thirds after one delivered goal action, even without a new student answer. Its uncertainty counts supporting identifiers, and elapsed observation time is absent. That input is a planning proxy, not the BKT estimate from the previous experiment.

The assessment store also has an evidence-confidence field. Two assessed attempts produce the same confidence whether both were correct or incorrect, so the completion rule checks outcome counts as well.

This separation matters because planner comparisons supplied state cards directly. Their gains do not validate the adapter that prepares those cards in the product. The estimator experiment was outside the tutoring service, and its promising result did not automatically become an integrated capability.

A plausible hypothesis is that this weak connection contributes to poorly targeted support. The current evidence does not isolate it as the cause of every generic message. The next design needs an explicit comparison between the current proxy and committed target-concept evidence, with other components held fixed.

**操作メモ:** saved activityからcompletionとplannerへの分岐。delivery0/1の値を図に直接表示。 考察: component比較で与えたstate cardsの結果はdefault proxyの検証ではない。BKT/PFAをdefault組込済みとしない。 出典: R3 learner-decision-detail; R5/R6; learner-state figure。

### 17. Richer instruction improved repair rates but retained critical errors

目安: 95秒。

**English script**

The wording alternatives tried to resolve a different weakness. Constrained assembly preserved approved source text but produced generic questions. In the live integration trial, all sixteen check-ins used wrappers around entire source cards. The delivered question could remain weakly connected to the learner's specific difficulty.

Typed instructional units and bounded revision attempted to produce more useful explanations while retaining source authority. An assistant-reviewed development comparison rated the typed candidate useful on forty-four of forty-eight rubric targets, compared with sixteen for the control. It still retained a critical attribution error.

In the fresh revision comparison, each of two candidates preserved all fifty-six adequate drafts and repaired forty-seven of fifty-six defective drafts. Each still retained one critical error: treating a necessary condition as sufficient. A citation to the source did not prevent the response from changing its meaning.

Both candidates failed the zero-critical-error gate and remained unpromoted. The proposed benefit was more specific instruction; the blocking weakness was semantic correctness.

Visual retrieval showed a similar separation. One historical candidate retrieved more relevant visual evidence, but final grounded answers did not improve. A separate fresh omni candidate underperformed its text and OCR control and was dropped. Source-region lineage and packet layout remained failure points.

These are distinct experiments, not one pooled result. They show why richer inputs and more flexible wording did not automatically produce a better complete tutoring system.

**操作メモ:** source assembly、typed/revised wording、visual evidenceの入口と出力を比較。criticalな意味の変化を一例で示す。 考察: 魅力的な候補を一律失敗とせず、改善した指標と採択を阻んだ条件を対にする。 出典: R4/R5; Study F/G; visual comparisons。

### 18. One concept completed two different goals

目安: 105秒。

**English script**

The goal defect is the clearest example of a correct stored observation leading to an incorrect later decision. Two goals were active: cache coherence and virtual memory. I will call them Topic A and Topic B. After two correct attempts on Topic A, the system completed both goals. Topic B had no assessment evidence. Reopening SQLite preserved both completed statuses.

The old service shortcut and the goal interpreter used evidence too broadly. Strong evidence for a concept anywhere in the learner record could complete a goal about another concept. The assessments themselves could be correct, and the storage could survive a restart, while the goal decision remained wrong.

The correction binds each active goal to its exact objective and checks committed evidence for every target concept in the same scope. Missing or ambiguous mappings remain incomplete. Under the retained rule, each target needs at least two correct assessments, no incorrect assessments, and sufficient evidence confidence.

This fixes the scope error, but the rule still has limitations. An earlier incorrect count continues to block completion in that state. The implementation also does not interpret an instructor's free-text success condition as an arbitrary executable rule. A completed goal therefore records satisfaction of a fixed software condition.

This failure explains why earlier restart and assessment checks were insufficient. They tested whether records persisted and whether attempts received the correct assessment. The missing check linked the completed goal to its own target concepts. The revised regressions cover unrelated, missing, ambiguous and uncommitted evidence, as well as continued work on another goal.

**操作メモ:** 2目標とconcept evidenceのbefore/after。誤った横断参照を強調し、new guardと制約を短く併記。 考察: 保存・assessmentの正しさだけでは誤goalを検出できなかった。fixed thresholdと累積incorrectの制約も答える。 出典: R3 learner-decision-detail; R5; Study H。

### 19. The lifecycle correction fixed status decisions and increased later delivery

目安: 95秒。

**English script**

The lifecycle comparison isolated a much smaller design change. Each arm ran seventy-two histories using the same driver, concepts, seeds, profiles and dependencies. Only two runtime source files differed. Planning and wording were deterministic, and no external model calls were made.

The old implementation completed twenty-six goals. Fourteen had support from the target concepts, and twelve did not. The corrected implementation completed fifteen, all supported. It passed the run's nineteen gates.

Both arms preserved restart consistency and passed the reported attribution and assessment checks. Those equal results explain why persistence and assessment tests had missed the separate completion defect. An audit had to connect each completed goal to its committed target evidence.

The correction also changed subsequent support. Across thirty-six autonomous histories per arm, it produced fifty-six more messages. Mean final simulated mastery changed by minus zero point zero zero two four, and the wasted-message fraction increased slightly. Those are descriptive simulator outcomes, not demonstrated effects on students.

Shared starting seeds do not require identical later conversations: different interventions can change simulated replies. The evidence supports keeping the objective-scope correction because an unassessed goal must not complete from another topic's evidence. It does not support a learning-improvement claim.

This result shows both the value and the remaining weakness of the revised design. The state decision became correct under the tested rule, while the quality of the additional support remained unresolved.

**操作メモ:** supported/unsupported表と後続delivery/masteryの小表を同じページに。各分母を明示。 考察: Keepはscopeの正しさに対する判断。goal完了と学習成果、全historyとautonomous sliceを分ける。 出典: R5; Study H。

### 20. The retained runtime separates authority checks from retry recovery

目安: 95秒。

**English script**

Some retained boundaries were requirements-driven choices rather than winning experimental architectures. A published release fixes the approved source versions and configuration. Current authority can still change while a response is being prepared.

The application therefore performs generation outside the database transaction and checks authority again at commit. A withdrawn release or revoked permission prevents an effect from being saved as an authorized delivery. An accepted turn saves its response, citations and learner update together, with a revision check against stale state.

Retries require a separate mechanism. A matching request identifier can reuse a saved turn. For proactive delivery, the message save and job-result save are separate steps. If the worker stops between them, a stable delivery key allows recovery to recognize the existing message.

A worker lease controls the claim on due work. It does not by itself solve that partial-save condition, and the stable key does not replace the authority check. The diagram shows where each mechanism applies.

This is not a global exactly-once guarantee for provider effects. An uncertain provider outcome stops without a blind repeat. The local tests support these particular contracts, but do not establish that SQLite or the process topology outperforms alternatives at production scale.

The design comparison therefore needs two categories: alternatives judged by shared experiments, and retained mechanisms justified by a required invariant and bounded verification. I do not present the second category as an unperformed architecture benchmark.

**操作メモ:** 一つのsequenceにgeneration中の失効、delivery保存後の停止を表示。common servicesとSQLiteを必要範囲で示す。 考察: 実際に比較して負けた方式と、比較していないdeployment代替を混同しない。 出典: R2/R3/R5; publication and tutoring sequences。

### 21. Historical integration exercised consent and restart controls

目安: 80秒。

**English script**

The live-model trial checked whether a historical integrated configuration could execute these paths together. It ran twenty-four synthetic histories over thirty virtual days and used actual external model calls.

The run processed four hundred and eighty-four tutor turns, delivered sixteen check-ins and exercised twenty-four service restarts. Consent was disabled on virtual days ten through nineteen, and no proactive messages arrived during that interval.

There were six hundred and fifty-four model calls, of which eleven reached the output limit. Thirteen tutor turns ended in a safe graph failure. The trial therefore includes actual operational failures and controlled stopping behaviour.

The generic check-ins discussed earlier show the limit of the integration. The worker could initiate support and preserve its effects while the content still failed to target the learner's difficulty. A post-run AI diagnostic inspected seventy-seven deliberately selected responses and failures; that selection cannot estimate overall response quality.

This run supports bounded execution and control claims for its historical configuration. It does not establish thirty days of real uptime, learning benefit, or qualification of every later component change. That is why the final design must preserve a separate evidence status for the components it combines.

**操作メモ:** 30仮想日の時間軸にconsent停止とrestart。実出力は未選定のため所見として表示し、架空の引用を置かない。 考察: 運用の実行と個別指導を分離。77件のAI診断は意図的選択で母集団品質の推定ではない。 出典: R5; Study G。

### 22. Evaluation corrections limit which design claims survive

目安: 120秒。

**English script**

The design history also includes problems in the evaluation itself. An earlier ten-thousand-case pipeline test allowed its authoring path to see the reference answer and supply the answer and citation. The later correction removed its interpretation as independent product-quality evidence.

A separate whole-corpus summary contains an unresolved numerical contradiction. It reports a grounded percentage that is incompatible with its total number of answer actions. The original per-case ledger was not located in the inspected evidence, so that percentage remains excluded from performance comparisons.

The third whole-system development round also tested more candidates than its frozen parent program allowed. Its outputs remain useful as disclosed diagnostics, but the run is invalid for preregistered architecture selection.

These are different evaluation failures, and I preserve their corrections rather than combining them with successful studies. The same care applies to the planner audit, which separated preferred-label agreement from permitted-action validity on a subsequent fresh comparison.

The remaining studies still rely heavily on synthetic material and AI-assisted construction or review. There was no approved evaluation with the actual instructor or real students. They support bounded software-design findings, while leaving teaching fidelity and learning benefit untested.

This is the limit on the selection argument: a design must earn its claim from its own valid comparison and configuration. A favourable metric from another trial cannot repair a failed gate, a missing artifact or an invalid evaluation protocol.

After those exclusions, the typed-target study still supports a development contract change, the fresh factual study still bounds the retained fallback, and the guarded-planner confirmation supports conditional progression. The goal regression supports its specific scope correction. Those surviving claims remain tied to their own configurations; they do not combine into a release-wide quality score.

**操作メモ:** 失敗したevaluation／どの主張を撤回するか／残せる診断の表。成績の単純ランキングにしない。 考察: 訂正・無効試験を除いたあと、採択に使えるA/B/C/D/Hと各検証範囲を再提示。数字の信頼性への疑問だけを残さない。 出典: R4/R6; L1c/L3; S3c/S7。

### 23. Remaining work follows acceptance gaps and dependencies

目安: 85秒。

**English script**

The next work should follow the acceptance gaps rather than simply continue the most recent experiment.

First, factual claims and assessment decisions need trustworthy evidence and semantic review. An improved planner cannot compensate for an incorrect assessment or an unsupported explanation. These remain acceptance blockers.

Connecting committed concept evidence to planning is a focused engineering comparison that can proceed on fixed, reviewed inputs. It addresses a specific missing connection already identified in the implementation. Its priority comes from making stored learner observations usable in the decision path, not from assuming that this change will solve all instructional problems.

Source-supported questions also need to reflect the approved teaching profile and the student's difficulty. The saved generic responses show why better action selection alone is insufficient.

Before a broader product claim, the chosen components must be frozen and checked together. A later approved course pilot can examine usefulness and student experience after the relevant quality conditions are met.

This ordering is my proposed development rationale. Some bounded comparisons can proceed in parallel, but claims about student benefit depend on reliable upstream evidence and the complete integrated behaviour. I would keep a simple control at each replacement so an unhelpful change can be rejected without losing the inspectable baseline.

**操作メモ:** acceptance gap／次の限定した作業／依存する検証／採択判断の表。未実施proposal表示。 考察: planner改善だけを最優先の全体解決策にしない。固定fixtureでのadapter比較は可能だが、product benefit主張はassessment品質に依存。 出典: R5/R6; proposed prioritization。

### 24. The next comparison and the deliverable I can defend

目安: 105秒。

**English script**

The next experiment would change one specific boundary: the adapter that prepares the planner input. The control would keep the current delivery and event proxy. The candidate would use committed assessment evidence for the goal's target concepts. The planner, permitted actions, evidence path and wording configuration would initially stay fixed.

My hypothesis is that distinguishing correct, incorrect and missing evidence will make action selection respond more directly to the learner's observed difficulty. That is a proposal to test, not a result already established by this project.

I would first compare decisions on the same saved input snapshots, including unrelated concepts, ambiguous assessment and missing evidence. Then I would compare complete histories, where different actions can legitimately produce different later replies. The evaluation should measure inappropriate and useful interventions, missed support, and the existing authority and lifecycle constraints. Latency and cost also belong in the decision. The dataset, scoring rules and acceptance thresholds need to be fixed before the run.

A separate question remains whether the assessment evidence is itself semantically correct. Improving the adapter cannot compensate for an incorrect assessment, so independent review must accompany this work.

The deliverable I can defend is a working research prototype that binds course configuration to student access, persistent support and explicit control boundaries. The comparisons explain which designs I retained and which I did not promote. Factual acceptance, instructional fidelity and student benefit remain incomplete. The proposed comparisons address those gaps without claiming that another model or a single adapter change will finish the project.

**操作メモ:** 16枚目で示したadapter境界にcontrol/candidateと固定条件を対応。下部で2枚目の依頼項目へ戻り、今回の成果と次の検証を接続。 考察: 同一snapshotで比較してからhistoryで後続行動を測る。assessment自体の妥当性は別に検証。 出典: R6; proposed evaluation design, not a recorded run。


## Question time

25枚目の `Questions` へ進む。[短い英語回答](defence-notes.md)と[設計比較台帳](design-comparisons.md)を参照する。
