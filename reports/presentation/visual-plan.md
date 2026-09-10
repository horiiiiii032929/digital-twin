# Visual plan for the owner-oriented structure

Prepared: 7 September 2026. Revision 9, [24-slide structure](presentation-structure.md).
Status: the [standard C4/UML draw.io set](diagrams/standard/README.md) is the recommended diagram source.
The first four custom-layout drafts are superseded. Use standard activity/sequence/state/class notation
for mechanisms; present experimental comparisons in ordinary tables alongside the relevant diagrams.
No actual slides produced. Video work resumed at the user's request; the
[2:50 recording](recording/recorded-video.md) is now available.

## Visual narrative

最初に依頼と到達点を示し、教員設定・実応答から内部の設計比較へ入る。最後に同じ依頼項目へ戻る。genericな背景図、同じ図の強調位置だけが変わるページは追加しない。

2枚目は「実装」「検証」「未達」が混ざらない到達点表。3枚目は実設定からconsumerとeffectへの図。5枚目は保存されたF21のみを実例として表示し、架空のafter応答を作らない。

## Slide allocation

The allocation below retains the required topics and evidence. Mechanism figures must now
use the corresponding UML/C4 notation from the standard set; comparison values belong
in conventional tables. The earlier custom comparison layouts are not the presentation default.

| 本編 | 視覚情報 | 根拠 |
| --- | --- | --- |
| 1 | 最小限のタイトル。録画の注目点は原稿の最後で伝える。 | R1/R6 |
| 2 | 5つの依頼項目／実装された挙動／検証の範囲／未達の4列。短いEnglish表にし詳細は話す。 | R1/R5; acceptance boundaries |
| 3 | 具体的な4設定をrelease、各consumer、観測できるeffectへ接続する図。強制条件と生成への入力をラベルで区別。 | R2; profile-examples appendix |
| 4 | 英語字幕付き60秒動画。仮想時間や待ち時間の編集を表示。録画にない機能を原稿で予告しない。 | Recording proposal; actual asset pending |
| 5 | 左にdiagnostic question/attempt/one hint設定、右にF21の実際の質問と応答。下にattempt elicited／concept-specific diagnosis absentを対応。 | R2/R5; profile-examples appendix, saved finding F21; F03 as separate context |
| 6 | 共通構造を一度描き、比較対象のevidence、planner、learner adapter、wording境界に実際の候補名を添える。 | R3/R4/R5; S1/S4/S5 |
| 7 | 3つの短い処理経路を同じ入力・出力で比較。hierarchical coverageに入るquestion scaffoldingを失敗点として示す。 | S1/S2; supplementary historical design records |
| 8 | lexical、typed-target、typed+rankingの3経路と同foldの結果表。Round 3数値は補足に置き、選択無効という短い注記。 | R4; Study A; S3/S3c |
| 9 | 候補集合・dominance gate・claim assemblyの一つの図。診断とfresh結果は別のラベルで失敗位置に対応。 | R4; L3 diagnostic; Study B |
| 10 | 同じ入力と許可action集合から4本の短い経路を描く。追加要素だけを差分として強調。 | S4/S5; R4 planner history |
| 11 | Cの選択actionがverifierでno-actionになる分岐を強調。Fold003の表にhistorical preferred-action-based metricと明記。 | S6/S7 |
| 12 | Aのfallbackを主経路に、Hの条件付き置換を描く。Fold004とconfirmationは別表。 | R3/R4; S8; Study C |
| 13 | A event rule／analytic-only candidate／H model proposal＋analytic guardを並べる。analytic-onlyにはnot tested in the cited comparisonと明記。 | R3 planner rules; R4 Study C; proposed ablation |
| 14 | planner/wordingの4構成表。final validityとprovider completionを区別。現在価格を追加しない。 | R4; Study D |
| 15 | estimator×timingの比較格子からcontrol、count/conditional、BKT/valueの3行を強調。全9組＋2boundsは補足。 | R4; Study E |
| 16 | saved activityからcompletionとplannerへの分岐。delivery0/1の値を図に直接表示。 | R3 learner-decision-detail; R5/R6; learner-state figure |
| 17 | source assembly、typed/revised wording、visual evidenceの入口と出力を比較。criticalな意味の変化を一例で示す。 | R4/R5; Study F/G; visual comparisons |
| 18 | 2目標とconcept evidenceのbefore/after。誤った横断参照を強調し、new guardと制約を短く併記。 | R3 learner-decision-detail; R5; Study H |
| 19 | supported/unsupported表と後続delivery/masteryの小表を同じページに。各分母を明示。 | R5; Study H |
| 20 | 一つのsequenceにgeneration中の失効、delivery保存後の停止を表示。common servicesとSQLiteを必要範囲で示す。 | R2/R3/R5; publication and tutoring sequences |
| 21 | 30仮想日の時間軸にconsent停止とrestart。実出力は未選定のため所見として表示し、架空の引用を置かない。 | R5; Study G |
| 22 | 失敗したevaluation／どの主張を撤回するか／残せる診断の表。成績の単純ランキングにしない。 | R4/R6; L1c/L3; S3c/S7 |
| 23 | acceptance gap／次の限定した作業／依存する検証／採択判断の表。未実施proposal表示。 | R5/R6; proposed prioritization |
| 24 | 16枚目で示したadapter境界にcontrol/candidateと固定条件を対応。下部で2枚目の依頼項目へ戻り、今回の成果と次の検証を接続。 | R6; proposed evaluation design, not a recorded run |


## Review-sensitive distinctions

7枚目のwhole-system比較は実行したfactual pathの範囲。共通coverage欠陥を理由にhierarchyやevent sourcing全体を棄却した図にしない。

10〜13枚目はevent rule、model proposal、deterministic lookahead、reject-only verifier、guarded replacementの差分を示す。13枚目のanalytic-onlyは未実施の比較候補として表示し、既存結果を割り当てない。

15〜16枚目は実験的estimatorとdefault delivery proxyの未接続を示す。24枚目の提案図では16枚目の同じ境界へ戻る。

19枚目は72 histories/armと36 autonomous histories/armを区別。20枚目はcommit前のauthority変更とdelivery保存後の停止を同じsequenceで説明する。

22枚目は評価の訂正だけで終わらず、A/B/C/D/H等から現在も支持できる主張を対応させる。23枚目は優先順位の提案と依存関係を示し、新しい実測効果として扱わない。

## Assets and production

録画・主要画面は未選定。F21の引用は提出profile-examples appendixにある保存テキストに基づく。新しいスクリーンショットを取得したとは表現しない。F03は別contextでありcontrolled profile comparisonとして使わない。

[Architecture](../figures/course-twin-architecture.pdf)、[Data relationships](../figures/course-twin-data-relationships.pdf)、[Tutoring sequence](../figures/course-twin-tutoring-sequence.pdf)、[Goal states](../figures/course-twin-goal-states.pdf)は前の検討で元資料を確認済み。完成スライドQAではない。

図と比較表は将来の制作時に編集可能な要素で作る。分母、study/fold、experimental status、未達条件は投影面にも保持し、出典をnotesに残す。文字を小さくして旧構成へ押し込まない。
