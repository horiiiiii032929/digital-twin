# 第2章の制作中スライド

6枚目：`slide-06-architecture-v5.pptx`。ユーザーが固定した冒頭01–05とは別ファイルで制作。標準C4ライブラリへの変更後、ユーザーから「OKです！」を受領。冒頭01–05と同じ明示的な固定指定はまだない。

5枚目で説明した利用を、Webアプリ、API、教材処理ワーカー、支援ワーカー、SQLite、ファイル、外部AIの役割へ対応付ける。C4の論理コンテナ図であり、Dockerコンテナの配置図ではない。

原本：[06-containers-c4-v2.drawio](../../diagrams/chapter02/06-containers-c4-v2.drawio)。スライドにはPNGを掲載。

## 実装との照合

- `compose.local-r1.yml`：API、ingestion-worker、outreach-worker、webと共有ボリューム。
- `scripts/run_ingestion_worker.py`：SQLiteに保存されたジョブとローカル教材ファイルの処理。
- `scripts/autonomous_tutoring_worker.py`：イベント監視、期限の来た自律ジョブと教授予約の処理。
- `services/api/app/factory.py`：サービス、保存先、外部モデルの構成。
- `docs/local-r1-runbook.md`：ローカル構成と過去の資格確認範囲。
- `research/05_evaluation/profiles/post-report-final-decision-v1.json`：標準設定と未昇格の実験候補の区別。

図のモデル接続は、選択した構成で必要な場合の呼び出し。すべての応答が外部モデルを使うという意味ではない。プロキシ・認証内部・バックアップ・障害復旧はこの論理図に展開していない。UI撮影時の構成が、この配置全体の稼働を実証したという意味でもない。

C4の表記参照：[Container diagram](https://c4model.com/diagrams/container)、[Notation](https://c4model.com/diagrams/notation)。

## draw.io標準C4ライブラリの適用

Web Browser Container、Container、Data Container、External Software System、System Scope Boundaryの標準テンプレートを使用。インストール済みdraw.ioの `Sidebar-C4.js` と `mxC4.js` で図形定義を照合。標準の形状を保ち、配色と文字サイズを発表用に調整。円柱はC4ライブラリのデータコンテナであり、SQLiteとファイル保存の両方に使用する。各要素の `c4Name`、`c4Type`、`c4Technology`、`c4Description` はdraw.ioのオブジェクト属性として編集できる。

参照：[draw.ioのC4ライブラリ](https://www.drawio.com/docs/diagram-types/c4-modelling/)。

## 7枚目：教材の取り込みと公開

レビュー用ファイル：`slide-07-materials-v1.pptx`。プレビュー：`slide-07.png`。

IT5004 Lecture 5の実PDFを現行の `LocalCourseSourceIngestionService.ingest_pdf` で処理し、講義ページと実際に保存された抜粋・出典位置を対比。PDFの24ページ目は、ページ上のスライド番号25に対応する。コースIDと教授IDはデモ用。外部AI呼び出し、実際の教授による公開、取り込み品質の比較評価を行ったという意味ではない。

抽出結果と出典のハッシュはローカルの `reports/generated/slide07-build/example-chunk.json` および `source-provenance.json` に記録。教材を含む成果物は発表レビュー用であり、公開配布用ではない。

公開手順は `src/digital_twin/student/publication.py` の `run_preflight` / `publish`、対応形式は `src/digital_twin/grounding/product_ingestion.py` とAPIのpublicationルーターに照合。スライド内でDA・DB・chunkを説明。PPTXからレンダリングし、画像・文字・表の配置を目視確認済み。冒頭01–05は変更していない。

## 8〜10枚目：第2章の後半

**現行レビュー版：`slides-08-10-course-knowledge-v6.pptx`。** プレビューは `slide-08.png`、`slide-09.png`、`slide-10.png`。旧v3は「何を言いたいのか分からない」というユーザー指摘により不採用。v4は作り直し途中の版。v5の全体方針は好評、08について実物の教材スクリーンショットを求められ、v6でLecture 5の印刷スライド35（PDF34ページ目）を掲載。枠は発表用の注釈。09・10の内容は維持。冒頭01〜05を基準に、具体例、設計上の問題、同条件での改善へ組み直した。制作ルールと移動先は [明瞭さの制作基準](../../planning/slide-clarity-contract-ja.md) を参照。

現行08は実際のIT5004質問・講義要点・V19の実回答抜粋。09は [設計比較のdraw.io原本](../../diagrams/chapter02/09-evidence-design-v1.drawio) を使ったUMLアクティビティ比較。10は同じ397問で253件から355件へ増えた結果と残存42件に絞る。異なる試験の数値と生成エラーは別の本編へ移す。新しいAI生成や評価は実行していない。

以下は旧v3の制作記録であり、現行スライドの内容ではない。

- 08：質問、公開版、検索、生成、検査、保存を実装に照合したUMLシーケンス。原本は [08-question-sequence-v1.drawio](../../diagrams/chapter02/08-question-sequence-v1.drawio)。事実回答の基本経路であり、IT5004のgoverned graphの実行トレースと同一ではない。教え方・修正の追加経路は第3章で説明する。
- 09：IT5004の実AI試行で保留文になった例。3件の教材取得と証拠充足判定の後、生成器がinvalid grounded answerとして出力を拒否した。内部の `operational-provider-failure` は広い分類であり、外部サービス停止を意味するとは限らない。元のモデル出力のどの条件が失敗したかはこの記録から断定しない。
- 10：同一開発集合397件での253件対355件を編集可能なグラフで表示。別のfresh試験の506/800は独立した欄へ置く。分母・完全正答条件・目標未達・決定論的評価であることを明記。新しい評価を実行したものではない。

構成案の09は「必要な事実の不足」を主例とする予定だったが、今回のIT5004保存記録の原因に合わせて「取得後の生成失敗」に具体化した。必要な事実を明示する設計変更と過去の結果は10に残す。この設計変更が09の実例を修正したという因果関係は主張しない。

出典は各スライドのノートへ記載。スクリプトは後工程。私的ビルド・検証記録は `reports/generated/chapter02-batch-build/`。現行の講義資料・モデル・アプリを変更せず、追加の外部モデル呼び出しはゼロ。固定済み01〜05の原本ハッシュは維持。

読者別レビュー：初見の読者には処理順と実例、ソフトウェア工学の読者には関数・保存境界、評価者には比較条件と分母、PJオーナーには「教授の教材を使う」実装と残る品質の差を示す。スライド単体の情報で、一般的なAI性能や教授本人の再現を証明したと誤解しないことを確認する。
