# 改訂構成の冒頭1〜6枚

配布版：`slides-01-06-v3.pptx`。2026-09-09。旧1〜10枚版とは別ファイル。新40枚構成の冒頭のみ。

1. 承認済みの正式題名と氏名
2. 正式要求と実装した機能
3. IT5004の実AI応答と実験候補の位置付け
4. 六章の目次
5. 学生との対話から教授の集計レビューまで
6. 実AIデモ構成でのLLMと通常コードの役割

表はPowerPoint上で編集可能。5枚目のUML原本は `../../diagrams/opening/course-cycle-v4.drawio`。旧承認版v3を保存。画面は保存済みの実AI応答で、新規AI呼出や架空の応答生成はしていない。ノートは出典・範囲情報であり、発表スクリプトは未作成。

## レビュー

全6枚を最終PPTXから描画し確認。初見の読者に対して、要求と実装の違い、学生画面が示す動作、LLMがどこを担当する構成か、過去評価を同一構成と扱わないことを確認。

- 2枚目：未実装と未検証を区別するため Remaining gaps に修正。教授本人のスタイル再現を設定の存在で達成としない。
- 3枚目：指導設定は試験用、応答は実AI、候補は未昇格と表示。スクリーンショットは原本を維持。
- 5枚目：複数学生との蓄積後に集計。少人数非表示と個別返信承認の不要を明示。これは概略の利用フローで詳細ランタイムの図ではない。
- 6枚目：既存構成にも計画等のLLMがあること、事実回答の組立は通常コードであることを記録と照合。LunaとLLMの説明を追加。未確認の現在稼働環境と一致すると断言しない。

実装詳細・関数・擬似コードは改訂構成の後続章へ。時間の通し測定、PowerPointアプリでの実表示、7枚目以降の作成はこの成果物に含まない。

## 成果中心への改訂（v3）

2枚目は要求と作った機能の対応、3枚目は実応答と改良候補の説明、6枚目はデモ構成内の責務に変更。未昇格を冒頭で強調する構成を撤回したが、実験構成という表示とノート内の採用記録は維持。以前のレビューのRemaining gaps列および構成別表に関する記載はv2についての履歴。v3では2・3・4・6枚目を最終PPTXから描画して確認。比較条件や未達の詳細は関係する後続評価ページで示す。

## Readable design names, 2026-09-09

Latest artifact: `slides-01-06-v4.pptx`. Visible internal generation version labels removed. “Excerpt tutor” means the experimental control that assembles source excerpts/fixed wording. “Audited tutor” means the candidate that generates teaching text and reviews it. Original implementation/run IDs remain in provenance notes and source records. Official model names and implementation identifiers needed to explain actual code are retained. Comparison numbers and release selection unchanged.
