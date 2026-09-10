# 作成済みスライドの統合改訂

対象は旧1–29枚。既存の6章方針を維持し、第1〜4章の説明を37枚に統合した。第5・6章の新規制作、動画の新規録画、読み上げスクリプトの再作成は今回の対象ではない。アプリ・評価結果・既提出レポートを変更していない。

## 反映した変更

- 保持システム、回答生成の実験対照、監査付き候補、実演の構成を分離。決定論的な事実生成とLunaによる自律計画を両立する構成として説明。
- 教授設定→実出力→承認の保証→生成方式→監査基準→アルゴリズム→比較結果の順に変更。
- 既存の102問の改善を維持。曖昧な教材の例をIT5004の具体例に変更。別々の試験を一つの向上率にしない。
- 回答品質13/24対17/24は評定器ゲート失敗を本文に置き、診断値として扱う。
- 予約配信を自律支援全体と同一視する説明を修正。イベント検知、計画、認可、生成、永続化、配信のつながりをdraw.ioシーケンスと擬似コードで追加。
- 目標完了の修正と72履歴/方式の対応比較を追加。不適切な完了12→0、配信量増加、学習改善未確認を同じ結果として保持。
- 670ケースの外部モデル確認と、7日実モデル/30日決定論的シミュレーションの違いを説明。
- 最後は達成した制約付き自律支援と継続開発を対応させ、第5章につなげる。

## レビューの判断

初見のCTO向けに「何が現在の構成か」、Lek教授向けに「元の依頼に対して何を作ったか」、ソフトウェア工学の評価者向けに「代替設計と修正の根拠」、AI研究者向けに「モデル評価とシミュレーションの有効範囲」、運用担当向けに「権限・再起動・重複送信」を本文で確認できる形にした。実学生による学習効果、教授本人の再現性、本番での無限スケールは実証済みと扱わない。

全37枚の描画を確認し、改訂後の章番号と表示名を確認した。最終のPowerPointアプリ上の再生や、読み上げ所要時間は今回検証していない。

## 改訂後のページ一覧

| 頁 | タイトル |
| --- | --- |
| 1 | Architecting an Digital Twinfor Scalable, Style-AlignedInstructor Presence |
| 2 | Turning the project brief into working software |
| 3 | Course Digital Twin: a student’s view |
| 4 | Presentation outline |
| 5 | How instructors and students use the system |
| 6 | How the software and language model work together |
| 7 | The software behind the course assistant |
| 8 | Preparing lecture material for student use |
| 9 | A course passage becomes part of the AI answer |
| 10 | How this answer was produced |
| 11 | The retained system combines several different components |
| 12 | Four decisions shaped course-grounded answers |
| 13 | Cover both requested topics before assembling an answer |
| 14 | Target-based selection passed 102 more questions |
| 15 | Ambiguous evidence requires a clarification |
| 16 | I retained BM25 with explicit evidence selection locally |
| 17 | The actual model request combines evidence and teaching |
| 18 | The professor can specify how the tutor should help |
| 19 | The same question received two different teaching responses |
| 20 | A published release uses an exact approved profile |
| 21 | Teaching text evolved beyond excerpts and fixed prompts |
| 22 | The audit checks whether the reply actually helps |
| 23 | A revised answer must pass review again |
| 24 | The answer comparison also checks the evaluator |
| 25 | Teaching quality remains inconclusive |
| 26 | Model roles and the current teaching decision |
| 27 | Three ways that continuing support can start |
| 28 | A student can receive support before asking a question |
| 29 | A scheduled check-in passes through delivery checks |
| 30 | Code decides whether to send, wait or suppress |
| 31 | An event becomes a governed autonomous action |
| 32 | Code checks the planner’s proposed action |
| 33 | Goal completion must use evidence for that goal |
| 34 | Unsupported goal completions fell from 12 to zero |
| 35 | Autonomous behavior was tested against simpler designs |
| 36 | Longitudinal tests checked continuity across restarts |
| 37 | The current result is bounded autonomous support |

元の監査: [1–29枚のレビュー](slides-01-29-evidence-and-design-review-ja.md)

成果物: レビュー画面 (local artifact: `../deck/slides-01-37-reviewed.html`)、PowerPoint (local artifact: `../deck/integrated-review/slides-01-37-reviewed-v5.pptx`)。出典・実装根拠は各ページのノートに保持。
