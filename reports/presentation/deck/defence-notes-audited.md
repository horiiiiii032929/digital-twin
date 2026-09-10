# Anticipated questions for online delivery

Reviewed: 8 September 2026. Slide references match digital-twin-presentation-audited.pptx (31 main slides, Questions, seventeen backup slides). Multiple questions can refer to the same slide.
手元用の短い英語回答。本編で答える論点を含む。実際の教授の発言ではない。

## Slide 29: How much of the system I asked for is actually delivered?

**Short answer**

The prototype implements course configuration, student access and persistent support with local control checks. Factual acceptance, instructor fidelity and real-student benefit remain unresolved.

**日本語メモ:** 実装済み、検証済み、未達を同じ成功マークにしない。最後まで待たず成果物の現在地を共有。

**根拠:** R1の5 requirementsとR5のacceptance boundaries。configuration/controlはbounded local verification、factual未達、instructor fidelityとlearning未検証。 出典: R1/R5; acceptance boundaries。

## Slide 06: What changes in the system when I change my teaching settings?

**Short answer**

Structured permissions constrain eligible actions and delivery. Descriptive teaching settings enter generation, but their instructional effect requires separate validation.

**日本語メモ:** 設定を入力できることと、その教え方を忠実に実行できることは別の到達点。

**根拠:** R2 configuration table、profile-examples。release binds policy/source/profile。 出典: R2; profile-examples appendix。

## Slide 06: Can you show an actual response that reflects the configured teaching approach?

**Short answer**

The saved Socratic case elicits the student's explanation, but the question remains generic. It is an illustrative saved case, not a controlled profile-effect comparison.

**日本語メモ:** 同一質問のprofile切替実験として見せない。設定が原因で改善した、実教授を再現したと断定しない。

**根拠:** 提出appendix profile-examplesのF21/F03。実応答引用と設定表。 出典: R2/R5; profile-examples appendix, saved finding F21; F03 as separate context。

## Slide 05: Which parts of the system actually changed between designs?

**Short answer**

The comparisons changed specific evidence, planning or learner-state boundaries while retaining shared product controls. They were separate experiments, not one ranking of every system.

**日本語メモ:** どの部品を変え、何を固定したかを最初に図で共有。すべてを一つの時系列winner競争にしない。

**根拠:** Round 1の3 manifestsとplanner A/B/C/C+Vのablationは別の実験。共通のauthority・evidence・persistence境界を保持。 出典: R3/R4/R5; S1/S4/S5。

## Slide 10: Why did the more structured system designs perform worse?

**Short answer**

Their shared whole-question coverage requirement rejected many answerable cases. This experiment locates an evidence-contract failure, not a general failure of hierarchy or event sourcing.

**日本語メモ:** 共通coverage欠陥のため両候補の本来の設計価値は十分識別できない。今回のcompositionを採択しない判断と、hierarchy/event sourcingの一般的棄却を区別。

**根拠:** 495 development cases、350 course-scoped chunks、3 complete manifests、外部LLMなし。 出典: S1/S2; supplementary historical design records。

## Slide 11: Why did you focus on the interface rather than add more ranking?

**Short answer**

The typed contract improved this development comparison; extra section ranking produced no further quality gain.

**日本語メモ:** target/cardinalityを次のdevelopment baselineに。追加rankingは同品質でlatency増。source-range候補の未採択には性能診断と実験規約違反を区別。

**根拠:** Study A：253/397→355/397、追加rankingも355/397。p95 1.36→2.79ms。Round 3はcandidate-count違反で選択に無効、診断のみ。 出典: R4; Study A; S3/S3c。

## Slide 12: Why keep BM25 when the final answer score is low? Is your scorer too strict?

**Short answer**

BM25 remained the simpler local fallback; both it and the hybrid failed acceptance. The strict scorer tests complete factual support and has limited semantic flexibility.

**日本語メモ:** BM25は簡単なfallbackとして保持。全事実と引用対応を要求するscorerにはsemantic flexibilityの限界がある。

**根拠:** L3診断84 target-first中69 clarification。Study B evidence98%、grounded63.25%、hybrid62%、boundary192/200。 出典: R4; L3 diagnostic; Study B。

## Slide 14: What is the actual difference between the four planners?

**Short answer**

A uses the event rule; B uses a permitted model proposal; C adds analytic lookahead; C+V can reject C's selected action. The policy and storage boundaries stay shared.

**日本語メモ:** Cを別のLLM階層やmulti-agent systemとして描かない。モデル数を増やす比較と分析的な先読みを加える比較を区別。

**根拠:** 共通runtime境界、learner-state plane固定。Bはdepth0、Cはdeterministic forward-model比較、C+Vはreject-only ablation。 出典: S4/S5; R4 planner history。

## Slide 14: Why did adding a verifier make the system worse?

**Short answer**

The verifier could suppress C's valid action without supplying a better one. The audit found over-rejection, while also identifying a metric-definition problem and local response-contract failures.

**日本語メモ:** 当時のacceptable-move判定はpreferred-label一致をvalidityと混同。結果を変更せず監査で訂正し、次のfresh比較でvalidityとpreferenceを分けた。B低下の個別原因を全件説明したとしない。

**根拠:** 150 contexts/600 cells、5 planner failures、provider completion97.9%<99.5%。A utility0.7830/regret0.0057。 出典: S6/S7。

## Slide 16: Why use the model if rules guard it, and is this utility improvement educationally meaningful?

**Short answer**

The tested guarded design improved the registered synthetic objective. The result does not establish student learning or superiority on every action label.

**日本語メモ:** 違うfoldを連続成績として比較しない。モデルの必要性と実学生の改善は未立証。

**根拠:** Fold004 A utility0.7860/C0.7807/H0.7880。Study C confirmation A0.7954/H0.8002、valid100%、preferred74/73%。 出典: R3/R4; S8; Study C。

## Slide 16: If the analytic model ranks the actions, why call a language model?

**Short answer**

The study supports the guarded composition relative to the event workflow. It does not isolate the proposal model's value against direct analytic selection.

**日本語メモ:** 学術的有意差だけでLLM必要性を主張しない。残す理由は比較済み構成としての条件付き選択であり不可欠性ではない。

**根拠:** R3のH replacement rule、Study Cはdeterministic workflow対guarded H。pure analytic selectorの直接ablationはこの証拠にない。 出典: R3 planner rules; R4 Study C; proposed ablation。

## Slide 40: Why did you choose these models, and did every model call succeed?

**Short answer**

Luna/Luna was the simplest and least expensive eligible allocation under the recorded rule. Valid final wording included fallback outcomes.

**日本語メモ:** final wording100%validにはfallbackを含む。歴史的study内の選択であり全モデルの現在の優劣ではない。

**根拠:** 300 contexts×4 allocations。planner effectCI0–0.001062、wording effectCI0–0.01042。Terra/Luna provider completion238/240、2fallback。 出典: R4; Study D。

## Slide 20: Why not simply send fewer messages or install BKT?

**Short answer**

Conditional timing removed useful practice in the simulator. BKT/value was promising under those assumptions, but prediction calibration and integration with actual committed observations remain unresolved.

**日本語メモ:** estimate改善とtiming改善を別軸で比較。BKT next-answer Brier差はinconclusive、simulator仮定と未統合でGo Deeper。

**根拠:** Study E：240 simulated learners/condition。count/constant messages14.0/mastery0.314/waste50.6%、count/conditional7.0/0.302/38.8%、BKT/value12.3/0.328/30.1%。 出典: R4; Study E。

## Slide 21: Does the autonomous planner actually use assessed learning progress?

**Short answer**

The default adapter supplies delivery and event proxies. Detailed assessment evidence exists, but it does not yet drive a calibrated planner estimate.

**日本語メモ:** component比較で与えたstate cardsの結果はdefault proxyの検証ではない。BKT/PFAをdefault組込済みとしない。

**根拠:** p_plan=min(0.95,(d+1)/(d+2))、u_plan=1/(k+1)。goal completionとは別consumer。 出典: R3 learner-decision-detail; R5/R6; learner-state figure。

## Slide 22: Why not use more flexible generation to improve the incomplete answers?

**Short answer**

The revision candidates repaired many drafts but each retained a critical semantic error, so neither passed the promotion gate.

**日本語メモ:** 魅力的な候補を一律失敗とせず、改善した指標と採択を阻んだ条件を対にする。

**根拠:** R4 typed44/48対16/48（AI rubric）、revision各47/56修復＋critical1、visual別比較でretrieval改善でもgrounded同じ。 出典: R4/R5; Study F/G; visual comparisons。

## Slide 23: How did this pass earlier checks, and is the new completion rule a mastery model?

**Short answer**

Earlier assessment and restart checks passed while the goal used unrelated evidence. The correction enforces objective scope; its threshold is not a validated mastery measure.

**日本語メモ:** 保存・assessmentの正しさだけでは誤goalを検出できなかった。fixed thresholdと累積incorrectの制約も答える。

**根拠:** service shortcutとgoal interpreterが広いlearner evidenceを参照。exact objectiveとcommitted target-concept evidenceへ限定する修正。 出典: R3 learner-decision-detail; R5; Study H。

## Slide 24: Why did total completions fall? How well did you isolate the fix?

**Short answer**

The original total included twelve unsupported statuses. The matched comparison changed two runtime files and checked each completion against committed target evidence.

**日本語メモ:** Keepはscopeの正しさに対する判断。goal完了と学習成果、全historyとautonomous sliceを分ける。

**根拠:** Study H：72 histories/arm、runtime2files差、deterministic、19gates。後続結果は36 autonomous/arm。 出典: R5; Study H。

## Slide 25: What if consent or publication changes while the model is generating? Why this architecture?

**Short answer**

The commit checks current authority and state revision. The shared local services enforce this contract; their deployment topology has not won a scaling comparison.

**日本語メモ:** 実際に比較して負けた方式と、比較していないdeployment代替を混同しない。

**根拠:** R3のsave/recovery contract、R5のbounded local verification。DB/topology比較は未実施。 出典: R2/R3/R5; publication and tutoring sequences。

## Slide 27: Did the integrated trial demonstrate useful personalized teaching?

**Short answer**

It exercised persistent operation and controls. The saved check-ins were generic, and the trial did not measure learning benefit.

**日本語メモ:** 運用の実行と個別指導を分離。77件のAI診断は意図的選択で母集団品質の推定ではない。

**根拠:** 24 synthetic histories/30 virtual days、484 turns、16 check-ins、24 restarts、consent off10–19で配信0。654 calls、643 completed、11 output-limit、13 safe graph failures。 出典: R5; Study G。

## Slide 28: Did evaluation leakage inflate your results, and which numbers remain usable?

**Short answer**

The pipeline trial could not support independent product quality. Its correction is retained, and the unresolved whole-corpus percentage is excluded; other studies keep their own stated scope.

**日本語メモ:** 訂正・無効試験を除いたあと、採択に使えるA/B/C/D/Hと各検証範囲を再提示。数字の信頼性への疑問だけを残さない。

**根拠:** R4/L1c/L3、S3c。AI assistanceと実教員・実学生未評価も残る。 出典: R4/R6; L1c/L3; S3c/S7。

## Slide 30: Why improve the planner input before solving the other quality gaps?

**Short answer**

It is a focused next engineering comparison, not a substitute for factual and assessment quality. Reliable instruction depends on those upstream results as well as the integration.

**日本語メモ:** planner改善だけを最優先の全体解決策にしない。固定fixtureでのadapter比較は可能だが、product benefit主張はassessment品質に依存。

**根拠:** R5/R6の未達とnext decision。ここで示す順序はowner-reviewを受けた提案であり実証済み優先度ではない。 出典: R5/R6; proposed prioritization。

## Slide 30: What exactly would you change next, and what result would justify keeping it?

**Short answer**

I would compare the current proxy with an adapter using committed target-concept evidence, holding the other components fixed and checking useful actions, missed support and operational constraints.

**日本語メモ:** 同一snapshotで比較してからhistoryで後続行動を測る。assessment自体の妥当性は別に検証。

**根拠:** R6のnext decision。具体的比較設計は未実施の発表提案であり、新しい測定結果ではない。 出典: R6; proposed evaluation design, not a recorded run。



## Slide 31: What is the research contribution?

**Short answer**

The contribution is the implemented and inspectable support system together with bounded design comparisons and failure analyses. The evidence shows where explicit answer requirements, fallback composition and objective-scoped completion matter in this prototype. It does not introduce BKT or prove a general educational advantage.

## Slide 16: Is the planner gain meaningful, and what did it cost?

**Short answer**

The recorded paired utility improvement is 0.004805, with a 95% interval from 0.003065 to 0.006760. It is a small improvement in a synthetic objective. The study recorded 801 provider calls and about 0.336 US dollars. We still need an analytic-only comparison to isolate the proposal model's value.

**Source:** research/05_evaluation/records/successor-architecture-confirmation-005-001.json. Historical run totals, not current pricing or a controlled runtime benchmark.

## Slide 19: Did BKT win because the simulator behaves like BKT?

**Short answer**

One simulator family is BKT-like. The hidden-state advantage also appears in the logistic-like family, but both families are our assumptions. Held-out seeds do not remove that bias. A decayed-count baseline and a third simulator family are needed. The next-answer result for BKT was inconclusive.

**Source:** research/05_evaluation/successor-learner-timing-simulation-001-results.md, limitations.

## Slide 24: Does zero unsupported completion prove the students mastered the objective?

**Short answer**

No. It shows that completion obeyed the target-evidence contract in these histories. We still need to validate the upstream assessment and the pedagogical meaning of the threshold. Zero observed errors is not a guarantee for all future histories.
