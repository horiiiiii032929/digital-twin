# 教材から実AI回答まで：7〜11枚目

配布版：`slides-07-11-v3.pptx`。前章の承認済み `../opening-six/slides-01-06-v3.pptx` を変更せず、続きの5枚を作成。

- 07：C4構成図。前章の役割説明をソフトウェア配置へ接続。
- 08：実PDFの抽出と保存結果、公開前確認。次の実AI試験が準備済み抜粋を使うことを明記。
- 09：実際の質問、講義画像、実AI回答、取得・引用件数。
- 10：同じ回答の実行経路。モデル呼出は生成1回、レビュー1回。計画と修正の呼出はこの回ではゼロ。
- 11：最終レビューの短い擬似コード。初回通過／1回の修正と再レビュー／保留。全システムの呼出上限とは区別。

## 原本と確認

07のdraw.io原本：`../../diagrams/chapter02/07-containers-c4-v3.drawio`。
10のdraw.io原本：`../../diagrams/chapter02/10-live-answer-sequence-v3.drawio`。
08の表と11の擬似コードはPowerPointの編集可能なオブジェクト。ノートは出典と範囲説明で、読み上げスクリプトではない。

9〜11の実例は `it5004-presentation-teaching-live-002` の説明型設定、第1ターン。実行DB、provider ledger、保存応答を照合。2回の呼出は同じgpt-5.6-luna、生成lowとレビューmedium。経過時間約16.1秒。グラフのgeneration_calls=1は内部レビューを含むモデルAPI呼出数ではない。全5枚を最終PowerPointから描画して内容とレイアウトを確認。PowerPointアプリでの表示確認や通しの発表時間測定とは区別。

教材の出典位置と引用があること、モデルレビューを通過したことは、一般的な回答精度や教授本人の忠実な再現を証明しない。これは機能と具体的な実行の説明。モデル比較は後続章で説明。新規AI呼出・再評価・実装変更なし。

## Review revision

Chapter review applied: highlight the student-response connections, distinguish full PDF extraction from prepared trial excerpts in body copy, show PDF and printed page numbers, disclose omitted citation markers in the response excerpt, identify code-selected intent and internal generator return, and label model calls explicitly in audit pseudocode. The withheld-response notice is an exact excerpt of QUARANTINE_TEXT. Original approved opening six slides remain unchanged.

## Readable design names, 2026-09-09

Latest artifact: `slides-07-11-v4.pptx`. Visible internal generation version labels removed. “Excerpt tutor” means the experimental control that assembles source excerpts/fixed wording. “Audited tutor” means the candidate that generates teaching text and reviews it. Original implementation/run IDs remain in provenance notes and source records. Official model names and implementation identifiers needed to explain actual code are retained. Comparison numbers and release selection unchanged.
