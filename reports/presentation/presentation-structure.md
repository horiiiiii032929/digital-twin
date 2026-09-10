# Presentation structure for joint review

Prepared: 7 September 2026. Revision 9: delivery against the brief, tested designs and remaining decisions.
Status: structure and aligned English script only. No actual slides are being produced at this stage.

## Working brief

- プロジェクトオーナーである教授に、依頼への到達点、設計を試して分かったこと、残る課題への判断を伝える。
- 英語・オンライン。手元の読み上げ原稿を使う。図と実画面を多用する制作方針を維持。
- 一般的なAI教育・RAG・UMLの説明は追加しない。冒頭の目的説明は、この依頼と成果物の対応に限定する。
- 時間より必要な説明を優先するという今回の指示を反映し、本編24枚に再構成。タイトルと約1分の録画を含む。
- 本編はおおむね35〜38分、質疑5〜7分を加えると約40〜45分。以前の全体40分を超える可能性がある。正式な上限の変更が確認されたわけではなく、現時点の構成上の見積もり。
- [提出レポート](../submitted/2026-09-06/report-with-appendices.pdf)と[提出ソース](../submitted/2026-09-06/report-source.zip)を基準にする。S番号は明示した既存研究記録による補足。
- 実スライドはまだ制作しない。録画素材や画像の確定も今回の構成見直しとは別段階。

## Narrative

最初の5枚で「何を依頼され、何ができ、教員設定がどこまで動作に反映されたか」を共有する。その後、各設計を試した狙いと失敗原因を説明し、最後に未達の依存関係と次の判断へ戻る。

| オーナーからの問い | 対応する本編 |
| --- | --- |
| 依頼したTwinはどこまでできたか | 2。実装と検証、未達を分けた到達点 |
| 自分の設定は実際の指導に効いているか | 3・5。設定のconsumerと保存済み応答、強制条件と未検証のpreferences |
| なぜその設計を試し、なぜ変えたか | 6〜12・15〜20。共通構造と変更箇所、同じstudy内の比較 |
| モデルを使う追加価値は何か | 13。確認済みのcomposition効果と未比較のanalytic-only代替 |
| 今信頼できる証拠は何か | 22。訂正・無効結果を除外したあと、残る有効な主張を再提示 |
| 次になぜその作業をするのか | 23・24。品質とassessmentの前提、adapter接続、instruction、全構成確認の順序 |

「性能が低かった」「共通部品に阻まれ設計価値を識別できなかった」「評価が無効」「まだ統合していない」を区別する。記録にない原因を発表のために作らない。異なるfoldや異なるscorerの結果を一つの性能曲線にしない。

## Delivery against the brief

2枚目の投影内容の核。実装できたことを全体合格として表示せず、未検証を失敗した実験とも混同しない。

| Requested outcome | Implemented behaviour | Evidence and remaining gap |
| --- | --- | --- |
| Configure the course Twin | Reviewed materials, settings and published releases | Bounded local workflow checks |
| Grounded student support | Course-scoped evidence and traceable responses | Fresh factual acceptance remains unmet |
| Teaching preferences | Profile inputs reach the response pathway | Saved cases show partial alignment; actual-instructor fidelity untested |
| Continuing support | Persistent observations, goals and proactive jobs | Operational and targeted lifecycle evidence; learning benefit untested |
| Instructor oversight | Review, pause, consent and withdrawal controls | Bounded local verification; full current composition still needs evaluation |

## Saved configuration-to-response example

5枚目は提出appendixのF21を用いる。合成Socratic設定はdiagnostic question、student attempt、one hint。学生の質問は “How does slot seal work in this course protocol?”。保存された応答は次の通り。

> For 'How does slot seal work', what is your current explanation, and which step are you unsure about?

この例はattemptを促すが、concept固有の困難に踏み込まない。別のexplanatory例F03は異なるcontextであり、同一質問のprofile切替による因果比較として並べない。期待した挙動と観測された挙動の差を説明する。

## Timing and slide map

英語原稿は5,044語。動画60秒と操作45秒込みで、毎分140語なら37:47、150語なら35:23。速度は仮定であり本人の実測ではない。ページ配分は毎分145語を目安に丸めたもの。

| 本編 | 内容 | 仮配分 |
| --- | --- | ---: |
| 1–5 | 依頼への到達点、教員設定、録画と実応答 | 5:10 |
| 6–9 | 比較境界とevidence pathの設計判断 | 6:10 |
| 10–14 | plannerの代替案、失敗、モデルの追加価値 | 8:05 |
| 15–17 | learner/timing、未統合部分、instruction | 5:00 |
| 18–21 | goal修正、runtimeの制御、統合結果 | 6:15 |
| 22–24 | 使える証拠、優先順位、成果物と次の比較 | 5:10 |
| 操作 | 原稿外の切り替え | 0:45 |
| **本編計** | **録画込み** | **36:35** |

## Main-slide storyboard

### 01. An Instructor-Configurable Digital Twin for Autonomous Course Tutoring

- 時間: 20秒。
- 内容・主張: 実装したcourse tutoringと、比較・統合試験で発見した限界を発表の対象にする。
- 根拠: 提出プロジェクトの名称・著者・研究課題。
- 考察・判断: AI教育の一般的背景やRAGの定義を置かず、製品と実際の失敗へ入る。
- 想定質問: “What did you actually build and investigate?”
- 本編での答え: “I built the course and tutoring workflows, then tested where evidence selection, planning and persistent state failed.”
- 画面の英文: “Hikaru (Rawin) Horinouchi”
- 図・画面: 最小限のタイトル。録画の注目点は原稿の最後で伝える。
- 出典: R1/R6。

### 02. What the project delivers against the brief

- 時間: 75秒。
- 内容・主張: 依頼されたcourse configuration、grounded support、teaching preferences、continuing support、human controlの到達点を冒頭で対応させる。
- 根拠: R1の5 requirementsとR5のacceptance boundaries。configuration/controlはbounded local verification、factual未達、instructor fidelityとlearning未検証。
- 考察・判断: 実装済み、検証済み、未達を同じ成功マークにしない。最後まで待たず成果物の現在地を共有。
- 想定質問: “How much of the system I asked for is actually delivered?”
- 本編での答え: “The prototype implements course configuration, student access and persistent support with local control checks. Factual acceptance, instructor fidelity and real-student benefit remain unresolved.”
- 画面の英文: “Implemented course workflows and persistent support; factual acceptance and teaching validation remain incomplete.”
- 図・画面: 5つの依頼項目／実装された挙動／検証の範囲／未達の4列。短いEnglish表にし詳細は話す。
- 出典: R1/R5; acceptance boundaries。

### 03. How instructor settings reach executable behaviour

- 時間: 75秒。
- 内容・主張: 教材、objective、teaching preference、proactive policyが異なるruntime consumerへ届く。enforced controlとdescriptive preferenceを区別。
- 根拠: R2 configuration table、profile-examples。release binds policy/source/profile。
- 考察・判断: 設定を入力できることと、その教え方を忠実に実行できることは別の到達点。
- 想定質問: “What changes in the system when I change my teaching settings?”
- 本編での答え: “Structured permissions constrain eligible actions and delivery. Descriptive teaching settings enter generation, but their instructional effect requires separate validation.”
- 画面の英文: “Action permissions constrain execution. Teaching preferences condition the response pathway.”
- 図・画面: 具体的な4設定をrelease、各consumer、観測できるeffectへ接続する図。強制条件と生成への入力をラベルで区別。
- 出典: R2; profile-examples appendix。

### 04. Recorded simulation

- 時間: 60秒。
- 内容・主張: 約1分で製品の実動作を共有する。
- 根拠: 録画素材は未選定。合成コースの画面と継続支援を撮影する案。
- 考察・判断: 映った動作だけを説明し、実学生・正式評価・30日連続稼働の証拠として扱わない。
- 想定質問: “Is this recording the evaluation experiment?”
- 本編での答え: “The recording illustrates operation. The reported studies have separate configurations, datasets and results.”
- 画面の英文: “Recorded simulation · Synthetic course”
- 図・画面: 英語字幕付き60秒動画。仮想時間や待ち時間の編集を表示。録画にない機能を原稿で予告しない。
- 出典: Recording proposal; actual asset pending。

### 05. A saved teaching-profile response shows partial alignment

- 時間: 80秒。
- 内容・主張: Socratic profileがattemptを促す応答にはつながったがconceptの困難に特化せずgeneric。別contextのexplanatory例もcontrolled comparisonではない。
- 根拠: 提出appendix profile-examplesのF21/F03。実応答引用と設定表。
- 考察・判断: 同一質問のprofile切替実験として見せない。設定が原因で改善した、実教授を再現したと断定しない。
- 想定質問: “Can you show an actual response that reflects the configured teaching approach?”
- 本編での答え: “The saved Socratic case elicits the student's explanation, but the question remains generic. It is an illustrative saved case, not a controlled profile-effect comparison.”
- 画面の英文: ““What is your current explanation, and which step are you unsure about?” — saved synthetic Socratic case”
- 図・画面: 左にdiagnostic question/attempt/one hint設定、右にF21の実際の質問と応答。下にattempt elicited／concept-specific diagnosis absentを対応。
- 出典: R2/R5; profile-examples appendix, saved finding F21; F03 as separate context。

### 06. The design alternatives shared a common product boundary

- 時間: 90秒。
- 内容・主張: 全体構成、factual evidence path、action planner、learner/timing、wordingを別の比較単位として試した。
- 根拠: Round 1の3 manifestsとplanner A/B/C/C+Vのablationは別の実験。共通のauthority・evidence・persistence境界を保持。
- 考察・判断: どの部品を変え、何を固定したかを最初に図で共有。すべてを一つの時系列winner競争にしない。
- 想定質問: “Which parts of the system actually changed between designs?”
- 本編での答え: “The comparisons changed specific evidence, planning or learner-state boundaries while retaining shared product controls. They were separate experiments, not one ranking of every system.”
- 画面の英文: “Compared boundaries: evidence selection, action planning, learner estimation and instructional generation.”
- 図・画面: 共通構造を一度描き、比較対象のevidence、planner、learner adapter、wording境界に実際の候補名を添える。
- 出典: R3/R4/R5; S1/S4/S5。

### 07. The first whole-system candidates rejected answerable questions

- 時間: 95秒。
- 内容・主張: Round 1の複雑な2候補はgrounded24.81%、lexical control52.66%。全候補でboundary100%・severe0。
- 根拠: 495 development cases、350 course-scoped chunks、3 complete manifests、外部LLMなし。
- 考察・判断: 共通coverage欠陥のため両候補の本来の設計価値は十分識別できない。今回のcompositionを採択しない判断と、hierarchy/event sourcingの一般的棄却を区別。
- 想定質問: “Why did the more structured system designs perform worse?”
- 本編での答え: “Their shared whole-question coverage requirement rejected many answerable cases. This experiment locates an evidence-contract failure, not a general failure of hierarchy or event sourcing.”
- 画面の英文: “Grounded success: lexical 52.66%; evidence-first 24.81%; plan-observe 24.81%. No arm passed acceptance.”
- 図・画面: 3つの短い処理経路を同じ入力・出力で比較。hierarchical coverageに入るquestion scaffoldingを失敗点として示す。
- 出典: S1/S2; supplementary historical design records。

### 08. Typed targets helped; another ranking stage did not

- 時間: 90秒。
- 内容・主張: grounded success253/397から355/397。追加section rankingの上積みはゼロ。
- 根拠: Study A：253/397→355/397、追加rankingも355/397。p95 1.36→2.79ms。Round 3はcandidate-count違反で選択に無効、診断のみ。
- 考察・判断: target/cardinalityを次のdevelopment baselineに。追加rankingは同品質でlatency増。source-range候補の未採択には性能診断と実験規約違反を区別。
- 想定質問: “Why did you focus on the interface rather than add more ranking?”
- 本編での答え: “The typed contract improved this development comparison; extra section ranking produced no further quality gain.”
- 画面の英文: “Grounded answers: 63.73% / 89.42% / 89.42%. Development result; all arms retained quality failures.”
- 図・画面: lexical、typed-target、typed+rankingの3経路と同foldの結果表。Round 3数値は補足に置き、選択無効という短い注記。
- 出典: R4; Study A; S3/S3c。

### 09. The evidence gate still limited the retained factual path

- 時間: 95秒。
- 内容・主張: ambiguity gateの過剰棄却と、取得根拠から完全な回答への変換が残る弱点。
- 根拠: L3診断84 target-first中69 clarification。Study B evidence98%、grounded63.25%、hybrid62%、boundary192/200。
- 考察・判断: BM25は簡単なfallbackとして保持。全事実と引用対応を要求するscorerにはsemantic flexibilityの限界がある。
- 想定質問: “Why keep BM25 when the final answer score is low? Is your scorer too strict?”
- 本編での答え: “BM25 remained the simpler local fallback; both it and the hybrid failed acceptance. The strict scorer tests complete factual support and has limited semantic flexibility.”
- 画面の英文: “Complete evidence@3: 98%. Fully grounded answers: 506/800 (63.25%). Factual acceptance failed.”
- 図・画面: 候補集合・dominance gate・claim assemblyの一つの図。診断とfresh結果は別のラベルで失敗位置に対応。
- 出典: R4; L3 diagnostic; Study B。

### 10. Four planner designs changed who selected the action

- 時間: 100秒。
- 内容・主張: Aはevent rule、Bはmodel proposal、Cはanalytic lookahead、C+Vはreject-only verifierを追加した比較。
- 根拠: 共通runtime境界、learner-state plane固定。Bはdepth0、Cはdeterministic forward-model比較、C+Vはreject-only ablation。
- 考察・判断: Cを別のLLM階層やmulti-agent systemとして描かない。モデル数を増やす比較と分析的な先読みを加える比較を区別。
- 想定質問: “What is the actual difference between the four planners?”
- 本編での答え: “A uses the event rule; B uses a permitted model proposal; C adds analytic lookahead; C+V can reject C's selected action. The policy and storage boundaries stay shared.”
- 画面の英文: “A: event rule. B: model proposal. C: analytic lookahead. C+V: additional rejection step.”
- 図・画面: 同じ入力と許可action集合から4本の短い経路を描く。追加要素だけを差分として強調。
- 出典: S4/S5; R4 planner history。

### 11. The verifier suppressed useful moves; lookahead had mixed results

- 時間: 120秒。
- 内容・主張: Fold003 acceptable-move A70.7/B44.0/C74.0/C+V40.0%。auditではAがutility最良、C+Vがvalid moveを過剰拒否。
- 根拠: 150 contexts/600 cells、5 planner failures、provider completion97.9%<99.5%。A utility0.7830/regret0.0057。
- 考察・判断: 当時のacceptable-move判定はpreferred-label一致をvalidityと混同。結果を変更せず監査で訂正し、次のfresh比較でvalidityとpreferenceを分けた。B低下の個別原因を全件説明したとしない。
- 想定質問: “Why did adding a verifier make the system worse?”
- 本編での答え: “The verifier could suppress C's valid action without supplying a better one. The audit found over-rejection, while also identifying a metric-definition problem and local response-contract failures.”
- 画面の英文: “C: 74% reported acceptable moves. C+V: 40%. The audit found over-rejection and a flawed validity interpretation.”
- 図・画面: Cの選択actionがverifierでno-actionになる分岐を強調。Fold003の表にhistorical preferred-action-based metricと明記。
- 出典: S6/S7。

### 12. The successor preserved the baseline unless a proposal earned replacement

- 時間: 100秒。
- 内容・主張: reject-only追加から、baselineを保持し改善を支持できるproposalだけ置換する設計へ変更。
- 根拠: Fold004 A utility0.7860/C0.7807/H0.7880。Study C confirmation A0.7954/H0.8002、valid100%、preferred74/73%。
- 考察・判断: 違うfoldを連続成績として比較しない。モデルの必要性と実学生の改善は未立証。
- 想定質問: “Why use the model if rules guard it, and is this utility improvement educationally meaningful?”
- 本編での答え: “The tested guarded design improved the registered synthetic objective. The result does not establish student learning or superiority on every action label.”
- 画面の英文: “Utility: 0.7954 / 0.8002. Preferred action: 74% / 73%. Conditional progression under the registered objective.”
- 図・画面: Aのfallbackを主経路に、Hの条件付き置換を描く。Fold004とconfirmationは別表。
- 出典: R3/R4; S8; Study C。

### 13. What remains unproven about the model's added value

- 時間: 75秒。
- 内容・主張: HはAとの比較でutility改善。しかし同じanalytic scoreで直接選ぶcontrolとのmodel固有の追加価値は未立証。
- 根拠: R3のH replacement rule、Study Cはdeterministic workflow対guarded H。pure analytic selectorの直接ablationはこの証拠にない。
- 考察・判断: 学術的有意差だけでLLM必要性を主張しない。残す理由は比較済み構成としての条件付き選択であり不可欠性ではない。
- 想定質問: “If the analytic model ranks the actions, why call a language model?”
- 本編での答え: “The study supports the guarded composition relative to the event workflow. It does not isolate the proposal model's value against direct analytic selection.”
- 画面の英文: “The guarded composition improved the tested objective. The proposal model's necessity remains an open comparison.”
- 図・画面: A event rule／analytic-only candidate／H model proposal＋analytic guardを並べる。analytic-onlyにはnot tested in the cited comparisonと明記。
- 出典: R3 planner rules; R4 Study C; proposed ablation。

### 14. The model comparison retained Luna for both roles

- 時間: 90秒。
- 内容・主張: architecture固定の4配分で代替モデルの効果区間が採択条件を満たさずLuna/Lunaを保持。
- 根拠: 300 contexts×4 allocations。planner effectCI0–0.001062、wording effectCI0–0.01042。Terra/Luna provider completion238/240、2fallback。
- 考察・判断: final wording100%validにはfallbackを含む。歴史的study内の選択であり全モデルの現在の優劣ではない。
- 想定質問: “Why did you choose these models, and did every model call succeed?”
- 本編での答え: “Luna/Luna was the simplest and least expensive eligible allocation under the recorded rule. Valid final wording included fallback outcomes.”
- 画面の英文: “Alternatives did not satisfy the positive-effect rule. Final wording validity included deterministic fallbacks.”
- 図・画面: planner/wordingの4構成表。final validityとprovider completionを区別。現在価格を追加しない。
- 出典: R4; Study D。

### 15. Estimator and timing combinations changed the intervention trade-off

- 時間: 120秒。
- 内容・主張: count/conditionalは配信を半減したがsimulated masteryも低下。BKT/valueはwaste減とmastery増を両立したが実装未統合。
- 根拠: Study E：240 simulated learners/condition。count/constant messages14.0/mastery0.314/waste50.6%、count/conditional7.0/0.302/38.8%、BKT/value12.3/0.328/30.1%。
- 考察・判断: estimate改善とtiming改善を別軸で比較。BKT next-answer Brier差はinconclusive、simulator仮定と未統合でGo Deeper。
- 想定質問: “Why not simply send fewer messages or install BKT?”
- 本編での答え: “Conditional timing removed useful practice in the simulator. BKT/value was promising under those assumptions, but prediction calibration and integration with actual committed observations remain unresolved.”
- 画面の英文: “Fewer messages alone reduced simulated mastery. BKT/value remained an experimental candidate.”
- 図・画面: estimator×timingの比較格子からcontrol、count/conditional、BKT/valueの3行を強調。全9組＋2boundsは補足。
- 出典: R4; Study E。

### 16. The promising learner design was not connected to the default planner

- 時間: 85秒。
- 内容・主張: 学生の回答がなくても配信1回でplannerのmastery probability欄が0.5から2/3へ上がる。
- 根拠: p_plan=min(0.95,(d+1)/(d+2))、u_plan=1/(k+1)。goal completionとは別consumer。
- 考察・判断: component比較で与えたstate cardsの結果はdefault proxyの検証ではない。BKT/PFAをdefault組込済みとしない。
- 想定質問: “Does the autonomous planner actually use assessed learning progress?”
- 本編での答え: “The default adapter supplies delivery and event proxies. Detailed assessment evidence exists, but it does not yet drive a calibrated planner estimate.”
- 画面の英文: “One delivery raises the planning proxy from 0.5 to 2/3 without a new student answer.”
- 図・画面: saved activityからcompletionとplannerへの分岐。delivery0/1の値を図に直接表示。
- 出典: R3 learner-decision-detail; R5/R6; learner-state figure。

### 17. Richer instruction improved repair rates but retained critical errors

- 時間: 95秒。
- 内容・主張: source assemblyのgenericさをtyped instruction/revision/visionで改善しようとしたがsemantic errorとlineageが昇格を阻んだ。
- 根拠: R4 typed44/48対16/48（AI rubric）、revision各47/56修復＋critical1、visual別比較でretrieval改善でもgrounded同じ。
- 考察・判断: 魅力的な候補を一律失敗とせず、改善した指標と採択を阻んだ条件を対にする。
- 想定質問: “Why not use more flexible generation to improve the incomplete answers?”
- 本編での答え: “The revision candidates repaired many drafts but each retained a critical semantic error, so neither passed the promotion gate.”
- 画面の英文: “Each revision candidate repaired 47/56 defective drafts and retained one critical error.”
- 図・画面: source assembly、typed/revised wording、visual evidenceの入口と出力を比較。criticalな意味の変化を一例で示す。
- 出典: R4/R5; Study F/G; visual comparisons。

### 18. One concept completed two different goals

- 時間: 105秒。
- 内容・主張: cache coherence正解2回が未評価のvirtual memory目標も完了させ、SQLite再読込でも誤状態が残った。
- 根拠: service shortcutとgoal interpreterが広いlearner evidenceを参照。exact objectiveとcommitted target-concept evidenceへ限定する修正。
- 考察・判断: 保存・assessmentの正しさだけでは誤goalを検出できなかった。fixed thresholdと累積incorrectの制約も答える。
- 想定質問: “How did this pass earlier checks, and is the new completion rule a mastery model?”
- 本編での答え: “Earlier assessment and restart checks passed while the goal used unrelated evidence. The correction enforces objective scope; its threshold is not a validated mastery measure.”
- 画面の英文: “Two correct attempts on Topic A also completed unassessed Topic B. The correction binds completion to each objective.”
- 図・画面: 2目標とconcept evidenceのbefore/after。誤った横断参照を強調し、new guardと制約を短く併記。
- 出典: R3 learner-decision-detail; R5; Study H。

### 19. The lifecycle correction fixed status decisions and increased later delivery

- 時間: 95秒。
- 内容・主張: unsupported12→0、supported14→15。36 autonomous/armで配信56増、simulated mastery差−0.0024。
- 根拠: Study H：72 histories/arm、runtime2files差、deterministic、19gates。後続結果は36 autonomous/arm。
- 考察・判断: Keepはscopeの正しさに対する判断。goal完了と学習成果、全historyとautonomous sliceを分ける。
- 想定質問: “Why did total completions fall? How well did you isolate the fix?”
- 本編での答え: “The original total included twelve unsupported statuses. The matched comparison changed two runtime files and checked each completion against committed target evidence.”
- 画面の英文: “Unsupported: 12 / 0. Target-supported: 14 / 15. Matched regression; 72 histories per arm.”
- 図・画面: supported/unsupported表と後続delivery/masteryの小表を同じページに。各分母を明示。
- 出典: R5; Study H。

### 20. The retained runtime separates authority checks from retry recovery

- 時間: 95秒。
- 内容・主張: authority、revision、request identity、lease、delivery keyが守る条件は異なる。
- 根拠: R3のsave/recovery contract、R5のbounded local verification。DB/topology比較は未実施。
- 考察・判断: 実際に比較して負けた方式と、比較していないdeployment代替を混同しない。
- 想定質問: “What if consent or publication changes while the model is generating? Why this architecture?”
- 本編での答え: “The commit checks current authority and state revision. The shared local services enforce this contract; their deployment topology has not won a scaling comparison.”
- 画面の英文: “A saved turn needs current authority and a valid learner revision, even after generation succeeds.”
- 図・画面: 一つのsequenceにgeneration中の失効、delivery保存後の停止を表示。common servicesとSQLiteを必要範囲で示す。
- 出典: R2/R3/R5; publication and tutoring sequences。

### 21. Historical integration exercised consent and restart controls

- 時間: 80秒。
- 内容・主張: 統合経路は動作したが全16 check-inはsource card全体を包むgeneric wrapperだった。
- 根拠: 24 synthetic histories/30 virtual days、484 turns、16 check-ins、24 restarts、consent off10–19で配信0。654 calls、643 completed、11 output-limit、13 safe graph failures。
- 考察・判断: 運用の実行と個別指導を分離。77件のAI診断は意図的選択で母集団品質の推定ではない。
- 想定質問: “Did the integrated trial demonstrate useful personalized teaching?”
- 本編での答え: “It exercised persistent operation and controls. The saved check-ins were generic, and the trial did not measure learning benefit.”
- 画面の英文: “16 delivered check-ins used generic source-card wrappers. Learning effects were not measured.”
- 図・画面: 30仮想日の時間軸にconsent停止とrestart。実出力は未選定のため所見として表示し、架空の引用を置かない。
- 出典: R5; Study G。

### 22. Evaluation corrections limit which design claims survive

- 時間: 120秒。
- 内容・主張: L1参照回答アクセス、L3数値矛盾、Round3候補数違反をそれぞれの採択主張から除外。
- 根拠: R4/L1c/L3、S3c。AI assistanceと実教員・実学生未評価も残る。
- 考察・判断: 訂正・無効試験を除いたあと、採択に使えるA/B/C/D/Hと各検証範囲を再提示。数字の信頼性への疑問だけを残さない。
- 想定質問: “Did evaluation leakage inflate your results, and which numbers remain usable?”
- 本編での答え: “The pipeline trial could not support independent product quality. Its correction is retained, and the unresolved whole-corpus percentage is excluded; other studies keep their own stated scope.”
- 画面の英文: “Protocol violations, answer access and inconsistent records limit architecture-selection claims.”
- 図・画面: 失敗したevaluation／どの主張を撤回するか／残せる診断の表。成績の単純ランキングにしない。
- 出典: R4/R6; L1c/L3; S3c/S7。

### 23. Remaining work follows acceptance gaps and dependencies

- 時間: 85秒。
- 内容・主張: factual/assessmentの意味の正しさ、learner evidence接続、profile-specific instruction、最終composition検証の依存関係で優先順位を説明。
- 根拠: R5/R6の未達とnext decision。ここで示す順序はowner-reviewを受けた提案であり実証済み優先度ではない。
- 考察・判断: planner改善だけを最優先の全体解決策にしない。固定fixtureでのadapter比較は可能だが、product benefit主張はassessment品質に依存。
- 想定質問: “Why improve the planner input before solving the other quality gaps?”
- 本編での答え: “It is a focused next engineering comparison, not a substitute for factual and assessment quality. Reliable instruction depends on those upstream results as well as the integration.”
- 画面の英文: “Reliable evidence and assessment support targeted planning; instructional quality and full-composition checks remain required.”
- 図・画面: acceptance gap／次の限定した作業／依存する検証／採択判断の表。未実施proposal表示。
- 出典: R5/R6; proposed prioritization。

### 24. The next comparison and the deliverable I can defend

- 時間: 105秒。
- 内容・主張: 次の限定したengineering比較はdelivery/event proxyとcommitted concept evidenceを使うplanner adapter。品質とassessmentの前提を満たす範囲で進める。
- 根拠: R6のnext decision。具体的比較設計は未実施の発表提案であり、新しい測定結果ではない。
- 考察・判断: 同一snapshotで比較してからhistoryで後続行動を測る。assessment自体の妥当性は別に検証。
- 想定質問: “What exactly would you change next, and what result would justify keeping it?”
- 本編での答え: “I would compare the current proxy with an adapter using committed target-concept evidence, holding the other components fixed and checking useful actions, missed support and operational constraints.”
- 画面の英文: “Proposed comparison: current proxy versus committed concept evidence, with the remaining composition held fixed.”
- 図・画面: 16枚目で示したadapter境界にcontrol/candidateと固定条件を対応。下部で2枚目の依頼項目へ戻り、今回の成果と次の検証を接続。
- 出典: R6; proposed evaluation design, not a recorded run。

## Priority and next decision

23〜24枚目は新しい実験結果ではなく、既存の未達から導く提案。

| Remaining gap | Next bounded work | Decision dependency |
| --- | --- | --- |
| Incomplete or semantically wrong answers and assessments | Inspect representative failures and independently review reference/assessment meaning | Product-quality claims require trustworthy evidence and scoring |
| Learner evidence does not feed the default planner | Compare the proxy with committed concept evidence on fixed reviewed inputs | Do not claim benefit from unvalidated assessments |
| Model proposal may add avoidable complexity | Compare event-rule, analytic-only and guarded selection | Keep additional complexity only for measured value, including operational burden |
| Generic instruction despite teaching settings | Compare profile-sensitive responses with controlled inputs and independent review | Changing actions alone cannot establish useful teaching |
| Separate component evidence | Freeze the chosen composition and run integrated acceptance checks | Historical integration does not requalify later changes |
| Instructor fidelity and student benefit untested | Later approved course evaluation after relevant gates | Synthetic utility is not evidence of real learning |

adapter比較は具体的で限定可能な次のengineering作業として提案する。factual品質やassessmentの妥当性より常に優先するという主張にはしない。固定したreviewed fixtureでの比較と、製品の学習効果を主張できる段階を分ける。

## Questions and backup

25枚目を `Questions`、26〜35枚目を補足B1〜B10とする。本編24枚、質疑表示1枚、補足10枚で計35枚の構成案。

| 補足 | 内容 |
| --- | --- |
| B1 | 教員設定の全項目、F21/F03、構成・deployment・domain model |
| B2 | Round 1〜3の全比較とRound 3 correction |
| B3 | Ambiguity診断、fresh factualの全候補・採点・不確実性 |
| B4 | Planner A/B/C/C+V/H、audit、Fold004とconfirmation |
| B5 | Planner全式、model配分、analytic-only比較の未実施範囲 |
| B6 | Estimator×timing全組合せとsimulator訂正 |
| B7 | Revisionとvisionの全結果、critical error、AI review |
| B8 | Goal guard、matched regression、autonomous slice |
| B9 | Authority、commit、retry、local qualification |
| B10 | Source index、評価訂正、残る有効な証拠 |

[英語原稿](speaker-script.md)、[視覚表現の制作メモ](visual-plan.md)、[想定質問](defence-notes.md)、[設計比較台帳](design-comparisons.md)を参照。完成スライドとしての視認性や動画同期は未確認。

## Source map




本構成の数値と提出時の状態は、2026年9月6日の提出ZIP内の本文を基準に転記した。現在の作業ツリーの実装や過去の構成案を、提出版の結論として扱わない。以下のR番号はこの構成書の参照記号であり、実験run IDではない。

| 記号 | 提出ZIP内のソース |
| --- | --- |
| R1 | `research/06_reports/final/chapters/01-objective.tex` |
| R2 | `research/06_reports/final/chapters/02-course-workflow.tex` |
| R3 | `research/06_reports/final/chapters/03-runtime-design.tex` と入力する概念・計画の詳細 |
| R4 | `research/06_reports/final/chapters/04-comparisons.tex` |
| R5 | `research/06_reports/final/chapters/05-integration.tex` |
| R6 | `research/06_reports/final/chapters/06-conclusion.tex` |

Study A〜Hは提出版のEvidence Indexと同じ記号。

| Study | 提出ZIP内の評価記録（`research/05_evaluation/` 以下） |
| --- | --- |
| A | `course-digital-twin-whole-system-architecture-round-2-001-results.md` |
| B | `final-cross-method-factual-confirmation-001-results.md` |
| C | `successor-architecture-confirmation-005-001-results.md` |
| D | `successor-architecture-engine-comparison-006-001-results.md` |
| E | `successor-learner-timing-simulation-001-results.md` |
| F | `independent-factual-revision-controls-001-fresh-v16-live-001-results.md` |
| G | `final-profile-operational-dialogue-development-001-full-live-001-results.md` |
| H | `goal-completion-scope-development-001-results.md` |

Large-test records also cited in this revision:

| Study | 提出ZIP内の評価記録（`research/05_evaluation/` 以下） |
| --- | --- |
| L1 | `factual-qa-v3-scale-completion-10000-001-results.md` |
| L1c | `factual-qa-v3-scale-completion-10000-001-analysis-correction-001-results.md` |
| L2 | `course-digital-twin-evaluation-program-011-results.md` |
| L3 | `academic-factual-qa-open-10000-winner-regression-001-results.md` |

Recorded submission hashes from `submission-sha256.json`:

- Report PDF: `240ec6154541d64394a102b4a4ebd2315eddd0f1584f021cfa559e5a84bfe909`
- Source ZIP: `d8022749b235cbf46edaf5980ed500497cb373e02954a2b2f11aa247a9470bd9`

スライド化の際は、出典を該当スライドのノートに付ける。結果の分母、開発／新規評価、合成／実学生、採用／実験中の区別は結論に影響するため、画面でも読める形で保持する。

## Supplementary design-history sources

提出本文が要約した試行過程を、既存の研究記録で補足する。S番号は提出ZIPへの収録を意味しない。新しい実験は実施していない。build-only記録は比較構造の説明にのみ用い、性能の証拠にはしない。S3はS3cと必ず併記する。

- S1: [course-digital-twin-whole-system-architecture-round-1-001-build-results.md](../../research/05_evaluation/course-digital-twin-whole-system-architecture-round-1-001-build-results.md)
- S2: [course-digital-twin-whole-system-architecture-round-1-001-results.md](../../research/05_evaluation/course-digital-twin-whole-system-architecture-round-1-001-results.md)
- S3: [course-digital-twin-whole-system-architecture-round-3-001-results.md](../../research/05_evaluation/course-digital-twin-whole-system-architecture-round-3-001-results.md)
- S3c: [course-digital-twin-whole-system-architecture-round-3-001-analysis-correction-001-results.md](../../research/05_evaluation/course-digital-twin-whole-system-architecture-round-3-001-analysis-correction-001-results.md)
- S4: [successor-architecture-paired-comparison-001-build-001-results.md](../../research/05_evaluation/successor-architecture-paired-comparison-001-build-001-results.md)
- S5: [successor-architecture-development-fold-001-build-results.md](../../research/05_evaluation/successor-architecture-development-fold-001-build-results.md)
- S6: [successor-architecture-development-fold-003-single-case-001-results.md](../../research/05_evaluation/successor-architecture-development-fold-003-single-case-001-results.md)
- S7: [successor-architecture-fold-003-causal-audit-001-results.md](../../research/05_evaluation/successor-architecture-fold-003-causal-audit-001-results.md)
- S8: [successor-architecture-policy-value-fold-004-001-results.md](../../research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md)

Teaching-profile example: R2 and `research/06_reports/final/chapters/profile-examples.tex`. Saved examples F21 and F03 use different synthetic contexts; they are not a controlled profile-switch experiment.
