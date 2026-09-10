# 第1〜4章の評価掲載対応

対象は作成済みの第1〜4章。改訂前37枚から50枚へ拡張した。必要な設計判断を支持・制限する数値を本編に置き、出典と詳細条件を各スライドのノートへ保持した。新規評価・有料モデル呼出・既提出レポートの変更は行っていない。

## 掲載した判断と評価

| 頁 | 判断 | 主な数値・意味 | 主要な結果記録（research/05_evaluation/ 以下） |
| --- | --- | --- | --- |
| 9 | ページ内分割を採用 | 32文書/1,318ページ。ページをまたぐ断片591/598→0/1,322。短い断片84件という代償も掲載 | cross-course-ingestion-v1-results.md |
| 14 | 最初の複雑な全体設計をそのまま採用しない | 495例の別開発foldで52.66%対24.81%/24.81%。回答可能な質問への過剰な保留を説明 | course-digital-twin-whole-system-architecture-round-1-001-results.md |
| 15–16 | 質問の対象別に根拠を選択 | 同一397問で253→355。追加ランキングは355のまま、p95は1.36→2.79ms | course-digital-twin-whole-system-architecture-round-2-001-results.md |
| 17 | 意味処理の追加を自動的に改善としない | 各400回答可能例の別試験で91→81%、95.25→96%。後者は16件の曖昧な参照ラベルを監査 | academic-factual-qa-semantic-target-comparison-002-results.md / academic-factual-qa-source-semantic-atom-comparison-001-results.md |
| 18 | 曖昧さを確認質問で扱う | 既知16件を全て確認、別の新規400問は97.75%で同点 | academic-factual-qa-ambiguity-safe-comparison-002-results.md |
| 19 | BM25と明示的な選択をローカル保持 | 800回答可能/200境界の5方式。506/800・192/200、目標未達と1件差の弱さも掲載 | final-cross-method-factual-confirmation-001-results.md |
| 20 | 視覚候補を採用しない | 新規30視覚問でテキスト/OCR26/30、omni16/30。双方の境界解放0/30、controlの誤領域引用1件 | true-visual-omni-confirmation-002-results.md |
| 25 | 設定への応答と教授再現性を区別 | 過去の48出力、反復評定33/48一致、順序入替試験5/12で無効化、人間参照0/48 | professor-fidelity-v2-anchor-002-machine-review-summary-001-analysis-correction-001-results.md |
| 27 | モデル変更だけで品質問題を解消したとしない | 3モデル設定、主対象87/96・95/96・96/96、重大事象2・1・1。対応した最初の試行の費用も掲載 | generation-model-dialogue-stability-development-001-results.md |
| 30–33 | 監査付き候補を継続改良 | 13/24対17/24は診断値。評定器1/64・製品評定6/96の無効、欠陥内訳、保留、時間、費用を掲載 | post-report-final-selection-decision-004-results.md |
| 40–41 | 評価がどのデータを更新するかを説明 | 返答→評価→観測・概念帰属→目標判定のUML、保存レコードの論理ER | autonomy_models.py / service.py / source_assessment.py等（実装根拠、評価件数ではない） |
| 42 | 根拠付きの評価基準ゲートを追加 | 32例でliteral24/32、初期Luna30/32、Sol31/32、修正版32/32。未対応目標への判定1→0 | post-report-source-assessment-001-results.md / post-report-source-assessment-002-results.md |
| 43 | 学習状態推定を比較 | 同一480履歴・7,535観測でCount/Decay/BKT/PFAのBrierと対応差区間。各略語・指標を説明 | post-report-learner-policy-001-results.md |
| 44 | 支援量とシミュレータ上の利益を一緒に判断 | 全体8,160履歴。Decay+conditionalの変化+0.00112、BKT+value+0.02885。追加配信+0.75/+5.16 | post-report-learner-policy-001-results.md / records/post-report-learner-policy-001-local-001.json |
| 45–46 | 目標固有の完了判定を採用 | 72履歴/方式、不適切な完了12→0、適切な完了14→15。配信9.06→10.61も掲載 | goal-completion-scope-development-001-results.md |
| 47 | 実モデル接続時の実行制約を確認 | 670例、1,836呼出、US$0.42161。権限・宛先・頻度・重複等の違反0を条件付きで説明 | governed-full-autonomy-v2-1-persona-confirmation-024-results.md |
| 48 | 継続・復旧を別々の検証で支える | 7日4履歴36/36呼出、30日72/72再起動整合性、152/152統合チェック、別途23ワーカーテスト | final-profile-live-longitudinal-development-001-live-001-results.md / post-report-product-integration-003-results.md |
| 49 | 根拠回復検出を観測のみで保持 | 23/24検出、36/36抑制、12/12統合チェック、実送信0。4/9語一致で取り逃した原因 | proactive-outreach-a1-shadow-confirmation-002-results.md |
| 50 | 現在の到達点と継続開発 | 上記評価を総合し、制約付き自律支援として説明。教育効果の実証とはしない | 保持プロファイルと各結果記録 |

## 数値を混ぜないための扱い

- 第14頁と第16頁は別fold。前者から後者へ直接改善率を計算しない。
- 第17頁の二行も別データ。16件のラベル不備を都合よく再採点した改善にしない。
- 第19頁は決定論的事実組立。第31頁のLLM指導応答と正答率を直結しない。
- 第25頁の教授再現性レビューと第30頁の最終Miniレビューは別構成・別試験。
- 第27頁は過去の生成器。最終の監査付き候補との同条件比較ではない。未完了応答を除外しない。
- 第43頁は同じ観測を与える予測試験。第44頁は介入がその後の状態を変えるシミュレーション。BKTの潜在確率は観測成功確率へ変換した指標を使用。
- 第44頁のmasteryはシミュレータの隠れ状態。実学生の学習スコアとは表現しない。
- 第47頁の670は全体のケース数。各違反項目の分母として一律に使用しない。
- 第48頁のケース・履歴・呼出・テストを足して総合件数にしない。
- 第49頁のno-outreach列は固定対照の定義から求まる値。新規の対照実行と偽らない。

## 残した詳細・掲載対象外

完全な実験履歴はresult-registry.mdに保持されている。繰返し試行、無効な試行、後日の訂正を削除していない。全てのrunを独立のスライドにせず、採否に必要な集約・失敗・訂正を対応づけた。旧learner-timing試験の異なる条件の指標を最新の予測順位に混ぜず、現在の対応比較を主表示した。

第5・6章は未制作。教授集計の詳細画面、運用全体、最終開発ロードマップはそこで具体化する。今回、既存章の主張を支える復旧・統合の数値は第48頁に前倒しで掲載した。付録は追加していない。

読み上げスクリプトと所要時間は今回再作成・再計測していない。各スライドのノートは出典・条件の記録であり、完成した読み上げ原稿ではない。
