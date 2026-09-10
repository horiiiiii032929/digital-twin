# AWS デプロイ済み構成と停止状態

確認日：2026年9月10日（Asia/Singapore）。記録 ID：`aws-local-fixes-009`。

**検証済みのアプリ修正をデプロイしました。確認後に EC2 を停止し、EventBridge Scheduler の自動起動・自動停止を両方無効にしました。教授への確認が済むまで、自動では再開しません。**

## 現在の状態

| 対象 | 実際に確認した状態 |
| --- | --- |
| AWS アカウント／CLI | `030334071887`／`--profile digital-twin` |
| リージョン | Singapore `ap-southeast-1` |
| CloudFormation | `DigitalTwinPilot`、`UPDATE_COMPLETE` |
| EC2 | `i-0fde1692c45c87640`、**stopped** |
| 自動起動 | **DISABLED**。保存されている時刻は平日09:00 Singapore |
| 自動停止 | **DISABLED**。保存されている時刻は平日18:00 Singapore |
| 過去の03:00停止 | 過去の一回限りの設定。今回のスケジュール一覧には存在しない |
| URL | <https://d3cccbyk2qjxd6.cloudfront.net>。URL は維持されるが、EC2 停止中はアプリを利用できない |
| データ | EC2 を終了・削除せず、既存 EBS と DB を維持 |
| NAT Gateway | `nat-01af5cc7918c1ca64`、available のまま |

ここで無効にした EventBridge は、EC2 の電源を切り替える2つの Scheduler です。アプリ内のチェックイン機能とは別です。バックアップ設定は削除・無効化していません。

スケジュールの無効化は AWS CLI による運用上の変更です。CDK の既存定義は ENABLED を保持しているため、将来のインフラ更新時はこの停止状態を確認・維持してください。再開の明示的な指示があるまでスケジュールを有効化しないでください。

## 配置構成

```text
ブラウザ（HTTPS、AWS 発行 cloudfront.net URL）
  → CloudFront（認証応答のキャッシュ無効）
  → VPC Origin
  → private EC2 上の Caddy（Web 配信／API プロキシ）
  → FastAPI／Python ドメイン実装
  → SQLite WAL ＋ コース資料（共有 EBS）
```

- EC2：`c7i-flex.large`、1ホスト、1 AZ。公開 IP と SSH 開放なし。IMDSv2 必須。
- API、Web、資料取り込み worker の3コンテナ。起動中の新イメージを確認してから EC2 を停止。
- データ EBS：暗号化 gp3、80 GiB、`vol-042a708b1eb64861b`。ルートディスクは30 GiB。
- NAT Gateway：外部モデル、ECR、SSM、Secrets Manager などへの通信経路。
- Secrets Manager：API キー、HMAC 等を管理。値やアカウントのパスワードはこの文書に記載しない。
- CloudWatch：コンテナログ30日保持、EC2状態アラーム。外部通知先は未設定。
- AWS Backup：日次 EBS バックアップ、14日保持の既存設定。今回のアプリバックアップとは別。
- 独自ドメイン、Route 53、RDS、EFS、複数ホストへの自動スケールは使用しない。
- CloudFront の origin read timeout は既存の60秒。今回この値は変更していない。

EC2 停止は全費用の停止ではありません。NAT、EBS、スナップショット、保持アドレス、ログ、Secrets Manager 等の残存リソースには料金が発生し得ます。今回、ネットワークやデータの削除はしていません。

## 実際に選択されているシステム設計

[選択記録](../../research/05_evaluation/profiles/aws-presentation-demo-v1.json)にある、スライドの **audited teaching demo** を維持しています。研究全体のデフォルトを置き換える昇格ではありません。

| 項目 | デプロイ設定 |
| --- | --- |
| デモ経路 | `audited-presentation-v1` |
| 候補 | `v19-luna-luna-medium` |
| 検索 | BM25、reranker なし、text/OCR fallback |
| 証拠ゲート | `dominance-scoped-ambiguity-safe-v3` |
| 制御フロー | `governed-autonomous-tutoring-graph-v2.1` |
| Planner／回答生成 | GPT-5.6 Luna、low reasoning |
| 最終監査／品質修復 | GPT-5.6 Luna、medium reasoning |
| 生成実装 | `question-specific-profile-grounded-v19` |
| 監査失敗 | 適格な品質修復1回と再監査。検証できない回答は非公開。既存の構造修復は別枠で維持 |
| モデル出力上限 | 既存の各ロール3000 tokens |
| プロセス予算 | 最大250呼び出し、USD5、同時実行上限5 |
| 学習オプション | `learning_configuration: null`、既存 base／lexical control |
| Count／Decay／BKT／PFA | 実験用の選択肢。追加の assessed learner-model 統合は未選択 |
| 自動チェックイン | proactive outreach worker は false。起動している資料取り込み worker とは異なる |
| 教授向け集計 | 同一 topic／signal で異なる学習者5人の既存閾値を維持 |
| 教材 | 合成 Data Systems／Browser Security。スライドの非公開 IT5004 教材は未投入 |

`APP_GENERATOR_MODE=deterministic` は基底 factory の設定として残っていますが、実際のデモ経路は上記の audited Luna 構成です。教授用 runtime-status API で実際の構成を読み、過去の AWS 構成と一致することを確認しました。

Count/Decay/BKT/PFA は、[研究結果](../../research/05_evaluation/post-report-learner-policy-001-results.md)が「no product promotion」としたため、このデモでは追加選択していません。予測の改善と介入の効果は別であり、スライドの実験結果をそのまま本番設定とはしていません。今回も評価方式・モデル選択・判断規則は変えていません。

## 今回反映した修正

前回の AWS イメージとの差分は、[機械記録](deployment-009.json)の12ファイルです。主な利用者向け修正は以下です。

- 回答完了後、任意の学習証拠取得を待たずに入力欄を解放。
- 会話本文を先に表示し、引用・証拠の取得失敗で履歴を隠さない。
- 引用・証拠の状態表示、読み取り専用の手動再試行、古い非同期応答の排除。
- 引用の同時取得数を制限し、長い履歴で主要操作が待たされる問題を軽減。
- 回答中の再読み込み後に draft と元の request ID を復元し、手動で同じ要求を回復。自動再送はしない。
- セッション切れでログイン画面へ戻り、古いセッションの遅延401を新しいログインに適用しない。
- Sources 操作の重なり、合成 preview の説明、集計閾値の説明を修正。
- 失敗したモデル呼び出しの使用量と限定的診断情報を保持。監査で不適切な回答を通す変更はしていない。

以前デプロイ済みの教授コース選択保持、公開前 autonomy Save の前提条件、失敗呼び出し会計も維持しています。ローカル seed-password 生成修正は補助ツール側であり、今回アカウントを再 seed／パスワード変更したという意味ではありません。

インフラは、既存 AMI `ami-0872fceefd41a6357` を明示的に固定しました。最初の差分では latest AMI の更新でホスト置換が予定されたためビルド中に中断し、置換なしの差分にしてから実行しました。OS の更新は今後、独立した保守として扱います。

## データと検証結果

デプロイ後の読み取り専用集計：16 accounts、4 courses、2 releases、43 conversations、238 messages、80 citations、119 learner observations。これらは既存のデモ・テスト履歴であり、独立した評価サンプル数ではありません。

Autonomy policies、autonomous goals、proactive messages／triggers／delivery outbox はいずれも0。runtime-status の worker heartbeat 一覧も空でした。したがって、自動チェックインが動いているとは報告できません。

- CDK：更新成功、同じ EC2／EBS ID を維持。
- 新 API／worker イメージ：`f034abb76ddfdc5794d5007eb9bb2eca4b02bd106e8d8bdb9760a3a1a9415ba0`。
- 新 Web イメージ：`8fef761ee1080d6888a57d64b98a455210f94975da9fa65e2520485ad0458d19`。
- SSM activation：`1ab04731-51c6-4c57-80bc-58e321cb9c03`、Success。
- 公開 HTTPS readiness、未認証拒否、偽ヘッダー拒否、異なる Origin の拒否、管理者ログイン、secure／HttpOnly／SameSite cookie、logout後拒否を確認。
- 教授・学生それぞれの実ログインとコース読み取り、Web配信、runtime-status の9設定項目の一致を確認。
- 今回のデプロイ検証ではモデル呼び出しを行わず、既存会話を追加生成していない。直前のローカル paid browser テスト結果は[統合レポート](../../docs/application-test-summary-2026-09-10.md)を参照。
- ローカル：frontend 116、関連 API 115、lint／build 成功。インフラ回帰7件成功。
- 全体 `npm run check` は、別の professor-evidence packaging script の freeze guard 不足で停止する既知状態。全体CI成功とは主張しない。

事前バックアップ：`/opt/digital-twin/backups/pre-local-fixes-20260910.zip`。schema v19、11 data files、アーカイブ検証成功。SHA-256：`fb66dd9660f7ccf6404d9f233ac1e4467bc350daf4efc590a232c793697a61ac`。ホスト上のバックアップであり、今回新たな off-host restore drill は行っていません。

最初の backup コピーは docker cp で失敗し、docker exec 経由のコピーと CRC 検証で回復しました。最初の inventory はイメージに存在しない manifest パス参照で失敗し、読み取り集計を再実行して成功しました。失敗記録はローカル証跡に保持しています。

## 残る制限と再開時の注意

- 監査による回答非公開、文脈だけの短い質問への弱さ、会話中の賞賛と保存評価の不一致、既存 “write my” 拒否規則は未変更。
- 新規教授の教材投入から公開、チェックイン配信、返信、目標完了までの完全な lifecycle は未検証。合成 preview と公開条件の制限を残している。
- 過去の AWS hang が完全に解消した証明はない。今回の短い稼働確認を長時間・全シナリオ試験とは扱わない。
- EC2 を起動すれば既存コンテナが復帰する構成だが、現時点では停止し、スケジュールも両方無効。教授の判断後に再開範囲を決める。
- AMI 固定とスケジュールの手動 drift を次回デプロイ前に必ず確認。既存 EBS や秘密情報を削除・置換しない。

詳細な非公開運用証跡：`output/aws-deploy-2026-09-10/`。秘密の値・パスワード・個別会話本文は本書に含めていません。
