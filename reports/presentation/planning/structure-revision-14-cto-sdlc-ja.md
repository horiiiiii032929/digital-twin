# 日本語構成案：継続的な学習支援ソフトウェアの開発

更新日：2026年9月8日。構成案 revision 14。

## 発表の軸

> このソフトウェアは何を実現し、試した設計の中で何が現時点のベストなのか。その選択をどの証拠が支え、継続的な学習支援として使えるようにするには、次に何を改善すべきか？

聴衆は、このプロジェクトを知らないCTOを想定する。技術的な理解力は前提とするが、製品の目的・独自用語・候補名・評価条件を知っているとは仮定しない。大学院CSの発表として、実装の紹介に設計判断、比較、失敗分析、妥当性の限界を結びつける。

一般的なSDLCの講義ではなく、要求→設計・実装→検証・改善→受入状況→継続開発を、このソフトウェアの具体的な事実で説明する。章の順序は説明の順序であり、すべての実験がこの順に実施されたという主張ではない。

今回の成果物は日本語の構成案のみ。既存PPTX・PDF・動画・スクリプトは変更していない。次に作るデッキは本編32枚、付録・バックアップなし。章名は各章の最初の内容ページに組み込み、独立した空の章扉は作らない。

## 章と時間配分

全体約32分を仮置きし、30〜35分を目安に実際の英語でリハーサルして調整する。早口であることを理由に情報を詰め込まない。動画は現在の4分6秒で見積もる。質疑応答は本編の後、全体の持ち時間に収める。

| 章 | ページ | 内容 | 目安 |
| --- | --- | --- | --- |
| 1 | 1–5 | 目的・要求・現在地 | 3分 |
| 2 | 6–10 | システム設計と実装 | 7分（動画4分6秒を含む） |
| 3 | 11–15 | 回答品質の検証と改善 | 5分 |
| 4 | 16–21 | 自律支援の検証と改善 | 6分 |
| 5 | 22–27 | 状態管理・継続動作・統合検証 | 6分 |
| 6 | 28–32 | 現時点のベストと継続開発 | 5分 |

## 「現時点のベスト」の扱い

- 比較対象、評価目的、データ条件を必ず添える。世の中の全手法で最良という主張ではない。
- 「現在の採用実装」「比較で有望だった未統合候補」「次の提案」を区別する。
- 優劣を決められない場合は、暫定的に残す対照と未確定の理由を示す。
- 異なる試験条件の数値を一つの改善曲線にしない。各部品の最良候補を寄せ集めて、システム全体として検証済みとは扱わない。
- 保存方式や配置方式は、比較していなければ「現在の構成」と呼ぶ。

## 各ページの内容

以下の「掲載内容」は構成の指定であり、そのまま長文を貼り付ける原稿ではない。各ページは主図または主表一つを基本とし、理解に必要な定義・条件・結論を画面に残す。根拠リンクは制作時の照合用で、発表用の付録ではない。

### 第1章　目的・要求・現在地

#### 01　継続的な学習支援ソフトウェアの開発

- **伝える結論：** 教授の教材と方針に基づき、学生との対話と後日の支援を継続するソフトウェアを開発した。
- **掲載内容：** 目的を一文で示す。Digital Twinは本プロジェクトの構成可能な教授支援アシスタントを指す、と定義する。教授の再現精度を達成済みとは書かない。
- **図・表：** タイトルと実画面の小さな抜粋。装飾図は不要。
- **次ページへの接続：** 何を作り、どう判断したかを6章で説明する。
- **根拠：** [01-objective.tex](../../../research/06_reports/final/chapters/01-objective.tex)

#### 02　目次：要求・設計・検証・継続開発

- **伝える結論：** 要求を定め、実装を示し、三つの観点で検証して、現在の選択と次の開発につなげる。
- **掲載内容：** 6章の名称を番号順に記載。回答品質、支援判断、継続動作の検証が、それぞれどの要求に対応するか示す。
- **図・表：** 番号付き目次。架空のSDLC図は作らない。
- **次ページへの接続：** まず利用者とシステムの担当範囲を共有する。
- **根拠：** [01-objective.tex](../../../research/06_reports/final/chapters/01-objective.tex)、[02-course-workflow.tex](../../../research/06_reports/final/chapters/02-course-workflow.tex)、[final-profile-operational-dialogue-development-001-full-live-001-results.md](../../../research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md)、[goal-completion-scope-development-001-results.md](../../../research/05_evaluation/goal-completion-scope-development-001-results.md)

#### 03　教授・学生とシステムの担当範囲

- **伝える結論：** 教授が教材と方針を設定し、学生が質問・解答し、システムが履歴を使って後から支援する。
- **掲載内容：** 教授の教材公開、学生の利用と同意、システムの回答と後日の連絡。例は全編で同じ合成コース・学生を使う。外部モデルは利用者と区別する。
- **図・表：** 簡潔なC4システムコンテキスト図。矢印には関係を表す動詞を付ける。
- **次ページへの接続：** この利用場面から、満たすべき要求を定める。
- **根拠：** [01-objective.tex](../../../research/06_reports/final/chapters/01-objective.tex)、[02-course-workflow.tex](../../../research/06_reports/final/chapters/02-course-workflow.tex)、[final-profile-operational-dialogue-development-001-full-live-001-results.md](../../../research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md)、[goal-completion-scope-development-001-results.md](../../../research/05_evaluation/goal-completion-scope-development-001-results.md)、[live-virtual-demo.md](../../../reports/presentation/recording/live-virtual-demo.md)

#### 04　正しい回答・適切な支援・制御可能な継続動作

- **伝える結論：** 機能が動くだけでは、継続的な学習支援の要求は満たせない。
- **掲載内容：** R1：教材に裏付けられ必要事項を含む回答。R2：目標と学習証拠に基づく支援。R3：同意・権限・保存状態を守る継続動作。教授の方針への忠実さ、学生への有用性も未検証の受入品質として位置づける。
- **図・表：** 要求トレーサビリティ表の前半。要求、観測したい動作、検証方法を3行で示す。
- **次ページへの接続：** 最初に、現時点でどこまで到達したかを共有する。
- **根拠：** [01-objective.tex](../../../research/06_reports/final/chapters/01-objective.tex)、[02-course-workflow.tex](../../../research/06_reports/final/chapters/02-course-workflow.tex)、[final-profile-operational-dialogue-development-001-full-live-001-results.md](../../../research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md)、[goal-completion-scope-development-001-results.md](../../../research/05_evaluation/goal-completion-scope-development-001-results.md)、[successor-learner-timing-simulation-001-results.md](../../../research/05_evaluation/successor-learner-timing-simulation-001-results.md)、[live-virtual-demo.md](../../../reports/presentation/recording/live-virtual-demo.md)

#### 05　現時点の成果と、最良の選択の概要

- **伝える結論：** 比較から残すべき設計は得られたが、システム全体の教育的有効性はまだ確立していない。
- **掲載内容：** 残す選択：必要な回答事実を明示する、許可された基準行動を残す、目標固有の証拠で完了する。実装済み・実験で有望・未達成を短く分ける。BKTを採用済みとは書かない。
- **図・表：** 3行の現状表。ここでは候補記号や詳細な数値を先に出さない。
- **次ページへの接続：** まず、このプロトタイプが実際にどう動くかを見る。
- **根拠：** [course-digital-twin-whole-system-architecture-round-2-001-results.md](../../../research/05_evaluation/course-digital-twin-whole-system-architecture-round-2-001-results.md)、[successor-architecture-policy-value-fold-004-001-results.md](../../../research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md)、[successor-architecture-confirmation-005-001-results.md](../../../research/05_evaluation/successor-architecture-confirmation-005-001-results.md)、[03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)、[design-comparisons.md](../../../reports/presentation/design-comparisons.md)、[goal-completion-scope-development-001-results.md](../../../research/05_evaluation/goal-completion-scope-development-001-results.md)、[01-objective.tex](../../../research/06_reports/final/chapters/01-objective.tex)、[02-course-workflow.tex](../../../research/06_reports/final/chapters/02-course-workflow.tex)、[final-profile-operational-dialogue-development-001-full-live-001-results.md](../../../research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md)

### 第2章　システム設計と実装

#### 06　デモ：教材公開から30日間の支援まで

- **伝える結論：** 複数の教授と学生の状態を保持し、新しい質問がない間にも支援を開始できる。
- **掲載内容：** 見るポイントは教材公開、学生ごとの履歴、自動支援の三つ。仮想時間・合成データ・デモ用構成を明記。録画の動作を性能や学習効果の証拠にしない。
- **図・表：** 実画面動画と字幕。現在の動画は約4分6秒。動画外に説明の長文を重ねない。
- **次ページへの接続：** この動作を担う実行単位と保存先を説明する。
- **根拠：** [live-virtual-demo.md](../../../reports/presentation/recording/live-virtual-demo.md)

#### 07　システムの構造と責務

- **伝える結論：** 画面、API、バックグラウンド処理、保存先がそれぞれ異なる責務を担う。
- **掲載内容：** 教材取り込み、回答処理、後日の支援、状態保存を担当する実行単位。ローカル構成と実験用部品を区別し、未比較の配置を性能上の最良構成とは呼ばない。
- **図・表：** C4コンテナ図。図の右下に、後半で検証する箇所を短文で示す。
- **次ページへの接続：** 複数の処理をつなぐデータは、どのような関係で保存されるのか。
- **根拠：** [01-objective.tex](../../../research/06_reports/final/chapters/01-objective.tex)、[02-course-workflow.tex](../../../research/06_reports/final/chapters/02-course-workflow.tex)、[live-virtual-demo.md](../../../reports/presentation/recording/live-virtual-demo.md)、[03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)、[autonomy_models.py](../../../src/digital_twin/student/autonomy_models.py)、[models.py](../../../src/digital_twin/student/models.py)

#### 08　教材・学生・学習目標・評価証拠の関係

- **伝える結論：** 目標を完了させる証拠は、その学生と目標の対象概念に結びついていなければならない。
- **掲載内容：** 公開教材版、学生の所属、目標、対象概念、評価証拠、支援記録を中心に必要な関係だけ示す。論理的な帰属と物理的な外部キーを混同しない。
- **図・表：** 新規ER図、Crow’s Foot記法。キー・任意性・多重度を実装と照合する。既存UMLドメインクラス図をER図として流用しない。
- **次ページへの接続：** この保存関係が、質問処理と後日の支援でどう使われるかを見る。
- **根拠：** [goal-completion-scope-development-001-results.md](../../../research/05_evaluation/goal-completion-scope-development-001-results.md)、[03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)、[autonomy_models.py](../../../src/digital_twin/student/autonomy_models.py)、[models.py](../../../src/digital_twin/student/models.py)

#### 09　質問への回答と、自律支援の処理

- **伝える結論：** 学生からの要求で始まる処理と、保存された状態から後で始まる処理がある。
- **掲載内容：** 上段は質問→情報取得→行動選択・生成→保存。下段は期限到来→目標と許可確認→支援判断→保存。処理を開始する条件と保存境界を説明する。
- **図・表：** 二つの短いUMLシーケンス図。共通参加者の名称と順序を統一する。
- **次ページへの接続：** 次に、各部品の実装状態と検証対象を整理する。
- **根拠：** [01-objective.tex](../../../research/06_reports/final/chapters/01-objective.tex)、[02-course-workflow.tex](../../../research/06_reports/final/chapters/02-course-workflow.tex)、[live-virtual-demo.md](../../../reports/presentation/recording/live-virtual-demo.md)、[successor-architecture-development-fold-003-single-case-001-results.md](../../../research/05_evaluation/successor-architecture-development-fold-003-single-case-001-results.md)、[successor-architecture-fold-003-causal-audit-001-results.md](../../../research/05_evaluation/successor-architecture-fold-003-causal-audit-001-results.md)、[successor-architecture-policy-value-fold-004-001-results.md](../../../research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md)、[03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)、[autonomy_models.py](../../../src/digital_twin/student/autonomy_models.py)、[models.py](../../../src/digital_twin/student/models.py)

#### 10　実装した部品と、単独で比較した候補

- **伝える結論：** 個別実験の好成績は、その候補が製品で検証済みであることを意味しない。
- **掲載内容：** 回答経路、プランナー、学習者状態、目標管理の4行。現在の構成、比較した候補、検証範囲を示す。デモ、部品比較、統合試験は別の証拠と明示する。
- **図・表：** 実装・評価の対応表。各行に該当する要求R1〜R3を記載。
- **次ページへの接続：** まずR1、教材から正しく答える経路の検証に入る。
- **根拠：** [final-profile-operational-dialogue-development-001-full-live-001-results.md](../../../research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md)、[successor-learner-timing-simulation-001-results.md](../../../research/05_evaluation/successor-learner-timing-simulation-001-results.md)、[live-virtual-demo.md](../../../reports/presentation/recording/live-virtual-demo.md)、[successor-architecture-development-fold-003-single-case-001-results.md](../../../research/05_evaluation/successor-architecture-development-fold-003-single-case-001-results.md)、[successor-architecture-fold-003-causal-audit-001-results.md](../../../research/05_evaluation/successor-architecture-fold-003-causal-audit-001-results.md)、[successor-architecture-policy-value-fold-004-001-results.md](../../../research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md)、[learner_estimators.py](../../../src/digital_twin/student/learner_estimators.py)、[intervention_policies.py](../../../src/digital_twin/student/intervention_policies.py)、[03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)、[design-comparisons.md](../../../reports/presentation/design-comparisons.md)、[goal-completion-scope-development-001-results.md](../../../research/05_evaluation/goal-completion-scope-development-001-results.md)

### 第3章　回答品質の検証と改善

#### 11　教材が見つかっても、回答の必要事項が抜けた

- **伝える結論：** 検索に成功しても、回答として必要な事実がすべて含まれるとは限らない。
- **掲載内容：** 同じ質問、教材の該当箇所、不完全な回答を示し、足りない事実を一つずつ明示する。検索成功と回答成功の判定基準を定義する。
- **図・表：** 実例の対照表。必要箇所だけを抜粋し、意味を変えない。
- **次ページへの接続：** この不完全さを減らすために、どの回答設計を試したのか。
- **根拠：** [course-digital-twin-whole-system-architecture-round-2-001-results.md](../../../research/05_evaluation/course-digital-twin-whole-system-architecture-round-2-001-results.md)

#### 12　試した回答設計と、共通して失敗した確認方法

- **伝える結論：** 階層検索や分解処理を追加しても、後段の証拠確認が不適切なら改善しなかった。
- **掲載内容：** 単純検索、階層的な証拠選択、分解と観測の追加を比較。質問の表現まで必要な証拠として要求し、答えられる問題を拒否した原因を示す。
- **図・表：** 候補比較表と、必要最小限のUMLアクティビティ図。全アーキテクチャ一般の失敗に拡張しない。
- **次ページへの接続：** 確認対象を、質問の表現から必要な回答事実へ変えた。
- **根拠：** [course-digital-twin-whole-system-architecture-round-1-001-results.md](../../../research/05_evaluation/course-digital-twin-whole-system-architecture-round-1-001-results.md)

#### 13　必要な回答事実を明示すると、253件から355件へ改善した

- **伝える結論：** 同じ397件の回答可能ケースで、必要な対象と事実数を指定する設計が改善を示した。
- **掲載内容：** 修正前後の例と253/397→355/397。追加の節ランキングは355/397のままで、p95処理時間は1.36→2.79ms。現在残す判断は事実の明示、追加ランキングは支持されない。
- **図・表：** 修正前後の例＋小さな比較表。分母、処理時間の測定対象、開発用ケースであることを記載。
- **次ページへの接続：** 開発用問題での改善が、新しい問題にも通用するかを確認する。
- **根拠：** [course-digital-twin-whole-system-architecture-round-2-001-results.md](../../../research/05_evaluation/course-digital-twin-whole-system-architecture-round-2-001-results.md)

#### 14　新しい問題では、単純な回答経路が比較上優位でも基準未達だった

- **伝える結論：** 比較内で良い構成と、受入可能な品質は別である。
- **掲載内容：** 800回答可能ケースでBM25経路63.25%、比較候補62%。境界ケース200件は別に示す。必要基準と未達状況を示し、単純経路を対照として残す理由を説明する。
- **図・表：** 比較結果表または棒グラフ＋基準線。数値の差だけで統計的優越を断言しない。
- **次ページへの接続：** 検索方式や文章修正を追加すれば、残る問題を解消できるのか。
- **根拠：** [final-cross-method-factual-confirmation-001-results.md](../../../research/05_evaluation/final-cross-method-factual-confirmation-001-results.md)、[final-cross-method-factual-confirmation-001-analysis-correction-001.json](../../../research/05_evaluation/records/final-cross-method-factual-confirmation-001-analysis-correction-001.json)

#### 15　検索改善や文章修正だけでは、最終回答の品質を保証できなかった

- **伝える結論：** 中間工程の改善は、最終回答の正確さを必ずしも改善しない。
- **掲載内容：** 視覚検索では根拠発見が18/30→28/30でも回答成功は両方20/30。別の修正実験では必要条件を十分条件へ変える重大誤りが残る。二つの実験を合算しない。
- **図・表：** 期待・観測・判断を示す2行の表。重大誤りは短い実例を添える。
- **次ページへの接続：** R1の現時点の選択を踏まえ、次にR2の支援行動を検証する。
- **根拠：** [04-comparisons.tex](../../../research/06_reports/final/chapters/04-comparisons.tex)、[independent-factual-revision-controls-001-fresh-v16-live-001-results.md](../../../research/05_evaluation/independent-factual-revision-controls-001-fresh-v16-live-001-results.md)

### 第4章　自律支援の検証と改善

#### 16　プランナーの入力と、選択する支援行動

- **伝える結論：** プランナーは学生状態と許可条件を読み、文章生成の前に行動を決める。
- **掲載内容：** 一人の学生の状況を例に、入力、許可された行動候補、選択結果を示す。モデルは権限を変更できない。
- **図・表：** 具体的な入出力表。候補記号は機能名と併記し、初出で定義する。
- **次ページへの接続：** モデルによる提案を、そのまま採用してよいかを比較した。
- **根拠：** [successor-architecture-development-fold-003-single-case-001-results.md](../../../research/05_evaluation/successor-architecture-development-fold-003-single-case-001-results.md)、[successor-architecture-fold-003-causal-audit-001-results.md](../../../research/05_evaluation/successor-architecture-fold-003-causal-audit-001-results.md)、[successor-architecture-policy-value-fold-004-001-results.md](../../../research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md)

#### 17　拒否だけの検証から、基準行動を残す設計へ

- **伝える結論：** 候補を拒否したときに代替行動がない設計では、実行可能だった支援を失う。
- **掲載内容：** 固定ルール、モデル提案、結果予測、拒否のみの検証を比較。改善構成Hは、許可された基準行動Aを保持し、条件を満たす提案だけで置き換える。
- **図・表：** UMLアクティビティ図の比較。根拠が許可されない場合の「実行しない」分岐を明記する。
- **次ページへの接続：** 基準行動を残す構成が実際に改善したか、独立した確認比較を見る。
- **根拠：** [successor-architecture-development-fold-003-single-case-001-results.md](../../../research/05_evaluation/successor-architecture-development-fold-003-single-case-001-results.md)、[successor-architecture-fold-003-causal-audit-001-results.md](../../../research/05_evaluation/successor-architecture-fold-003-causal-audit-001-results.md)、[successor-architecture-policy-value-fold-004-001-results.md](../../../research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md)、[successor-architecture-confirmation-005-001-results.md](../../../research/05_evaluation/successor-architecture-confirmation-005-001-results.md)

#### 18　基準行動を残す構成は、評価上の小さな改善を再現した

- **伝える結論：** 構成Hは今回の合成評価では次段階へ進める選択だが、全指標で最良ではない。
- **掲載内容：** 1000状況で評価効用0.7954→0.8002、許可された行動は両方100%、推奨行動ラベル一致74%→73%。評価効用の意味、差の不確実性、801呼出し・USD0.335790を短く示す。
- **図・表：** ADR形式の判断表：比較・根拠・残す構成・制約。モデルなしの直接的な数値選択との比較不足も記載する。
- **次ページへの接続：** ただし、良い判断には入力となる学生状態の妥当性も必要になる。
- **根拠：** [successor-architecture-policy-value-fold-004-001-results.md](../../../research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md)、[successor-architecture-confirmation-005-001-results.md](../../../research/05_evaluation/successor-architecture-confirmation-005-001-results.md)、[successor-architecture-confirmation-005-001.json](../../../research/05_evaluation/records/successor-architecture-confirmation-005-001.json)、[planner-math.tex](../../../research/06_reports/final/chapters/planner-math.tex)

#### 19　現在の学生状態入力は、送信回数だけでも上昇する

- **伝える結論：** 支援した回数を、理解した証拠として扱うことはできない。
- **掲載内容：** 評価された解答がない状態で、送信0回の0.50から送信1回の0.67へ上がる例。現在の入力処理と、目標完了の判定は別であると説明する。
- **図・表：** 送信前後の小さな表。入力元を示し、「現在の弱点」と明記。
- **次ページへの接続：** 理解度を正誤履歴から推定する候補を調べた。
- **根拠：** [03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)、[design-comparisons.md](../../../reports/presentation/design-comparisons.md)

#### 20　理解度推定と次の回答予測では、良かった候補が異なる

- **伝える結論：** BKTをすべての目的に対するベストとは呼べない。
- **掲載内容：** Countは回数に基づく基準、BKTは習得確率を更新する方法、PFAは成功・失敗履歴から正答確率を推定する方法。一定時期の連絡条件で、BKTの理解度誤差0.035対Count0.084、次回答のBrierはBKTとCountとも約0.259、PFA0.249。指標の意味と小さいほど良いことを併記する。
- **図・表：** 方法の短い定義と2指標の比較表。MSEとBrierを同じ量として扱わない。240合成学習者、製品未統合を明記。
- **次ページへの接続：** 状態推定と別に、連絡時期も選ぶ必要がある。
- **根拠：** [successor-learner-timing-simulation-001-results.md](../../../research/05_evaluation/successor-learner-timing-simulation-001-results.md)、[learner_estimators.py](../../../src/digital_twin/student/learner_estimators.py)、[intervention_policies.py](../../../src/digital_twin/student/intervention_policies.py)

#### 21　連絡を減らすだけでは、必要な学習機会も減り得る

- **伝える結論：** 状態推定と連絡方針は、組み合わせて評価する必要がある。
- **掲載内容：** Countの一定連絡と条件付き連絡は14→7通、最終推定対象の隠れた習得状態0.314→0.302。評価した実行可能候補の中ではBKT＋価値に基づく連絡の最終状態平均0.328が最大だが、追加検証候補にとどまる。
- **図・表：** 連絡回数と最終状態を単位付きで比較。oracleは実装候補と区別。実学生の成績とは書かない。
- **次ページへの接続：** R2の判断だけでなく、R3の保存状態と完了条件も検証する。
- **根拠：** [successor-learner-timing-simulation-001-results.md](../../../research/05_evaluation/successor-learner-timing-simulation-001-results.md)、[learner_estimators.py](../../../src/digital_twin/student/learner_estimators.py)、[intervention_policies.py](../../../src/digital_twin/student/intervention_policies.py)

### 第5章　状態管理・継続動作・統合検証

#### 22　学習目標の状態と、完了に必要な証拠

- **伝える結論：** メッセージ送信や別の目標の正解では、その目標を完了にしてはいけない。
- **掲載内容：** Active、Completed、Expired、Cancelledと条件を示す。送信試行上限と目標完了は別。ER図の目標・対象概念・評価証拠の関係を小さく再掲する。
- **図・表：** UML状態機械図。完了遷移のガード条件を明記。ER再掲は関係の確認に限定する。
- **次ページへの接続：** 旧実装がこの条件を満たさなかった具体例と、修正結果を見る。
- **根拠：** [goal-completion-scope-development-001-results.md](../../../research/05_evaluation/goal-completion-scope-development-001-results.md)、[03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)、[autonomy_models.py](../../../src/digital_twin/student/autonomy_models.py)、[models.py](../../../src/digital_twin/student/models.py)

#### 23　目標ごとの証拠を使う修正で、不適切な完了12件を除去した

- **伝える結論：** 目標の帰属を守る修正は保持するが、学習効果の改善とは区別する。
- **掲載内容：** キャッシュの正解で仮想記憶まで完了していた例を示す。72履歴ずつの比較で不適切な完了12→0、修正後は支持された完了15件。判定閾値はソフトウェアのルールであり教育的妥当性は別。
- **図・表：** 修正前後の例と結果表。22枚目の完了条件と対応させる。
- **次ページへの接続：** 保存する内容だけでなく、保存時の権限も変化し得る。
- **根拠：** [goal-completion-scope-development-001-results.md](../../../research/05_evaluation/goal-completion-scope-development-001-results.md)、[03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)、[goal-completion-scope-v2.json](../../../research/05_evaluation/profiles/goal-completion-scope-v2.json)

#### 24　許可が変わった場合、保存前に再確認する

- **伝える結論：** 開始時に許可されていても、処理途中で失効した回答を保存してはいけない。
- **掲載内容：** 生成中の教材公開取り消しを例に、生成開始時の確認と、保存時の権限・状態版の再確認を示す。
- **図・表：** UMLシーケンス図。altで保存可能／拒否を表し、トランザクション境界を明記。
- **次ページへの接続：** 次に、保存直後に処理が止まった場合を扱う。
- **根拠：** [03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)

#### 25　再試行では、保存済みの通知を再利用する

- **伝える結論：** 保存と処理完了記録の間で停止しても、同じ通知を重複して作らない。
- **掲載内容：** 通知保存→停止→ジョブ再実行→同じ識別子で既存通知を取得。ローカルのアプリ内配信で確認した範囲を示す。
- **図・表：** UMLシーケンス図。外部配信全体のexactly-once保証とはしない。
- **次ページへの接続：** これらの部品を長期間一緒に動かした結果を確認する。
- **根拠：** [03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)

#### 26　30日間の統合試験では、有用な支援の継続が課題として残った

- **伝える結論：** 運用機構の動作と、有用な個別指導の成立は別だった。
- **掲載内容：** 24合成履歴、484対話、16自発的支援、10返信。同意停止期間は配信なし、期間後の支援再開なし、支援は一般的。再起動やモデル失敗も含めた観測範囲を記載。
- **図・表：** 観測した動作・結果・解釈の3列表。6枚目のデモとは別構成・別試験と明記。
- **次ページへの接続：** 受入を判断するには、評価記録自体の妥当性も必要になる。
- **根拠：** [final-profile-operational-dialogue-development-001-full-live-001-results.md](../../../research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md)

#### 27　評価上の不備を訂正し、採用根拠から除外した

- **伝える結論：** 無効な評価や誤った指標解釈を、そのまま設計選択の根拠にしない。
- **掲載内容：** 採用判断に影響する例を二つに絞る。評価規約に反した構成比較と、推奨行動ラベル一致を妥当性と混同した評価。訂正後に使う証拠を対応させる。
- **図・表：** 問題・訂正・現在の判断への影響の表。過去の全試験一覧は載せない。
- **次ページへの接続：** 有効な証拠だけを使い、最初の要求への到達点を整理する。
- **根拠：** [factual-qa-v3-scale-completion-10000-001-analysis-correction-001-results.md](../../../research/05_evaluation/factual-qa-v3-scale-completion-10000-001-analysis-correction-001-results.md)、[academic-factual-qa-open-10000-winner-regression-001-results.md](../../../research/05_evaluation/academic-factual-qa-open-10000-winner-regression-001-results.md)、[course-digital-twin-whole-system-architecture-round-3-001-analysis-correction-001-results.md](../../../research/05_evaluation/course-digital-twin-whole-system-architecture-round-3-001-analysis-correction-001-results.md)、[successor-architecture-fold-003-causal-audit-001-results.md](../../../research/05_evaluation/successor-architecture-fold-003-causal-audit-001-results.md)

### 第6章　現時点のベストと継続開発

#### 28　当初の要求に対する到達点

- **伝える結論：** 回答品質、支援の有用性、継続動作では、達成できた範囲が異なる。
- **掲載内容：** 4枚目と同じR1〜R3を同じ順序で再掲。実装、検証結果、未達条件を示す。教授方針への忠実さと実学生への有効性は未確立。
- **図・表：** 要求トレーサビリティ表の完成版。実装済みを要求達成と同じ色で扱わない。
- **次ページへの接続：** この到達点を支える、現時点の選択を一か所にまとめる。
- **根拠：** [01-objective.tex](../../../research/06_reports/final/chapters/01-objective.tex)、[02-course-workflow.tex](../../../research/06_reports/final/chapters/02-course-workflow.tex)、[final-profile-operational-dialogue-development-001-full-live-001-results.md](../../../research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md)、[goal-completion-scope-development-001-results.md](../../../research/05_evaluation/goal-completion-scope-development-001-results.md)

#### 29　現時点のベストと、その適用範囲

- **伝える結論：** 現在残す実装と、次に検証すべき候補を明確に分けられる。
- **掲載内容：** 回答：必要事実の明示、単純検索経路を対照として維持。支援判断：基準行動を残すH。学習者状態：指標別にBKT/PFAが有望、未統合。目標管理：対象概念の証拠に限定する修正を保持。継続動作：保存時再確認と再試行の識別。
- **図・表：** 5行の設計判断表。各行に比較範囲／実装状態／残る限界を付ける。未比較の保存技術を最良と断定しない。
- **次ページへの接続：** 次の開発は、この構成を対照として、未解決の入力問題を改善する。
- **根拠：** [course-digital-twin-whole-system-architecture-round-2-001-results.md](../../../research/05_evaluation/course-digital-twin-whole-system-architecture-round-2-001-results.md)、[final-cross-method-factual-confirmation-001-results.md](../../../research/05_evaluation/final-cross-method-factual-confirmation-001-results.md)、[final-cross-method-factual-confirmation-001-analysis-correction-001.json](../../../research/05_evaluation/records/final-cross-method-factual-confirmation-001-analysis-correction-001.json)、[successor-architecture-policy-value-fold-004-001-results.md](../../../research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md)、[successor-architecture-confirmation-005-001-results.md](../../../research/05_evaluation/successor-architecture-confirmation-005-001-results.md)、[successor-architecture-confirmation-005-001.json](../../../research/05_evaluation/records/successor-architecture-confirmation-005-001.json)、[planner-math.tex](../../../research/06_reports/final/chapters/planner-math.tex)、[successor-learner-timing-simulation-001-results.md](../../../research/05_evaluation/successor-learner-timing-simulation-001-results.md)、[goal-completion-scope-development-001-results.md](../../../research/05_evaluation/goal-completion-scope-development-001-results.md)、[03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)、[goal-completion-scope-v2.json](../../../research/05_evaluation/profiles/goal-completion-scope-v2.json)

#### 30　次の変更：学生状態を、関連する評価証拠から作る

- **伝える結論：** 支援回数ではなく、目標の対象概念に関する確定済みの証拠を判断へ渡す。
- **掲載内容：** 現在の入力と提案する入力を比較。評価証拠がない・無関係・矛盾する場合を明示。プランナーなど他の構成は固定する。評価器の品質も別途検証が必要。
- **図・表：** 変更前後のデータ対応表。提案であり未実施と明記。
- **次ページへの接続：** この変更が改善かどうかを、同じ入力で比較する。
- **根拠：** [03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)、[design-comparisons.md](../../../reports/presentation/design-comparisons.md)、[goal-completion-scope-development-001-results.md](../../../research/05_evaluation/goal-completion-scope-development-001-results.md)

#### 31　次の候補を採用するための比較計画

- **伝える結論：** 部品の差を確認してから、継続履歴の中で副作用を検証する。
- **掲載内容：** 対照は現在の入力、候補は関連評価証拠。まず同じ保存状態で比較し、次に同じ履歴で有用な行動・見逃し・不適切な連絡・権限制約・遅延・費用を評価。閾値は実行前に定める。
- **図・表：** 実験計画表。判定は保持・修正・追加検証・不採用。未実行の合格値を作らない。
- **次ページへの接続：** この比較を起点に、継続的な開発の順序を示す。
- **根拠：** [03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)、[goal-completion-scope-development-001-results.md](../../../research/05_evaluation/goal-completion-scope-development-001-results.md)

#### 32　継続開発：回答品質と判断入力を改善し、統合評価へ進む

- **伝える結論：** 現在の成果を対照に、証拠を積み重ねながら改善を続ける。
- **掲載内容：** 回答の受入品質を高める、判断入力を検証する、採用候補を統合して長期動作を再評価する、その後に承認された実コースで教授方針への忠実さと学生への有用性を評価する。
- **図・表：** 開発項目・進む条件・依存関係の表。根拠のない日程やリリース約束を入れない。このページを表示したまま質疑へ。
- **次ページへの接続：** 議論する点は、次の開発優先順位と受入条件。
- **根拠：** [01-objective.tex](../../../research/06_reports/final/chapters/01-objective.tex)、[02-course-workflow.tex](../../../research/06_reports/final/chapters/02-course-workflow.tex)、[final-profile-operational-dialogue-development-001-full-live-001-results.md](../../../research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md)、[goal-completion-scope-development-001-results.md](../../../research/05_evaluation/goal-completion-scope-development-001-results.md)、[03-runtime-design.tex](../../../research/06_reports/final/chapters/03-runtime-design.tex)、[04-comparisons.tex](../../../research/06_reports/final/chapters/04-comparisons.tex)

## 図の制作仕様

| 表現 | 対象ページ | 制作方針 |
| --- | --- | --- |
| C4システムコンテキスト図 | 3 | 利用者、システム境界、外部依存を区別する。内部の処理手順を混ぜない。 |
| C4コンテナ図 | 7 | 実行単位、責務、接続を示す。クラスや概念モデルを混ぜない。 |
| ER図 | 8、22で部分再掲 | Crow’s Foot記法。概念の関係だけでなく永続化実装を確認する。物理FKで強制していない関係を物理FKとして描かない。 |
| UMLシーケンス図 | 9、24、25 | 同じ参加者名を使い、メッセージの向きと処理順序を統一する。条件分岐はalt/opt、繰り返しは必要な場合のみloopを用いる。 |
| UMLアクティビティ図 | 12、17 | 処理順序と分岐条件の説明に使う。C4の構造図と混ぜない。 |
| UML状態機械図 | 22 | 目標の状態と遷移条件を示す。単一ジョブの処理段階とは分離する。 |
| 要求トレーサビリティ表 | 4、28 | 同じ要求IDと名称で、実装・検証・受入状況を対応させる。 |
| ADR形式の設計判断表 | 18、29 | 背景、比較候補、根拠、決定、影響を短く示す。新たな正式ADRや実装採択を行うものではない。 |

図はdraw.ioの編集可能な原本を保ち、画像としてスライドへ配置する。図中の文字も投影時に読める大きさを確保する。読めなくなった場合は字体を小さくする前に対象範囲を絞る。

ER図は新規制作対象。既存の `04-uml-domain-classes.drawio` はUMLドメインモデルであり、ER図の代用としない。ページ8のエンティティ名と多重度は図の制作時に永続化実装へ対応付け、確認できない関係は論理モデルとして明示する。

## スライド単体で理解できるための編集基準

1. 前提説明のタイトルは対象を直接示し、結果のページは発見や判断を示す。すべてのタイトルを無理に結論文にしない。
2. 各ページ上部に章番号と章名を表示する。部品比較には該当要求R1/R2/R3を添える。
3. 図の近くに入力・変化・結果の読み方を書く。図を説明するためだけの独自記号は増やさない。
4. 数値には分母・単位・良い方向・比較条件を添える。グラフの色だけに意味を持たせない。
5. BKT、PFA、評価効用、MSE、Brierは初出のページで意味を説明する。必要な定義を脚注だけに追いやらない。
6. 「未統合」「合成評価」「基準未達」など結論を左右する条件は本文に置く。出典は短い注記と資料内リンクで追えるようにする。
7. コード、ログ、実画面は説明に必要な領域を切り出す。全面の小さな画面を読ませない。
8. 旧デッキの全表・全グラフを持ち込まない。今回の開発判断に必要な証拠を本編に置き、全試験一覧・用語集・追加図の付録は設けない。
9. 講演スクリプトはこの構成の理解不足を補う場所にしない。まずスライドだけで目的・設計・選択理由・限界が追えるか確認する。

## 構成レビュー

- **初見のCTO：** 3〜5枚目で利用者・要求・現在地を共有し、7〜10枚目で構造・データ・動作・実装範囲を説明してから比較へ進む。
- **ソフトウェア工学：** 要求と検証を対応させ、データ帰属、状態遷移、権限変更、再試行を具体的な設計として説明する。
- **大学院CS：** 対照・候補・同条件比較・否定的結果・無効な証拠・妥当性の限界・次の実験を示す。新規性や教育効果を未検証のまま主張しない。
- **現時点のベスト：** 冒頭で選択の概要、各章で根拠、29枚目で適用範囲と実装状態をまとめる。
- **継続開発：** 最後の3枚は変更箇所、比較方法、次段階へ進む条件。32枚目の開発計画を表示したまま質疑に入る。
- **密度の重点確認：** 9枚目の二つのシーケンス、20枚目の推定器と指標、22枚目の状態とER再掲、29枚目の選択一覧は、実スライド制作時に文字を縮小せず対象を絞る。必要ならページ分割し、空の区切りは増やさない。

この構成はスライドの見た目の検証を代替しない。実スライドの読みやすさ・図の多重度・英語での所要時間は、次の制作とレビューで確認する。
