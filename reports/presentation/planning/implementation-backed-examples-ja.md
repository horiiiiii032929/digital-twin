# 実装に基づく図とコード例

## 図の完成条件

図の読みやすさを保ちつつ、全体として実際の開始経路・処理順・保存先・見送り・再実行・終了条件を追える構成にする。全体モデルの中で詳細図の範囲を示し、独立した部分図の寄せ集めにしない。

大きな図を縮めて文字を読めなくする代わりに、全体図と接続した詳細図を本編で展開する。重要な詳細を付録へ移す構成にはしない。

各技術ページに次の対応を持たせる。

1. **具体的な場面：** どの教授・授業・学生で、何が起きたか。
2. **図：** 実際の担当・順序・保存・分岐を示す。
3. **実装：** 実在するクラス名・関数名とファイルを示す。
4. **コード例：** 実コードの短い抜粋、または分岐の意味を保った疑似コード。
5. **結果：** 入力から何が返るか、何が保存されるか、何が起きないかを示す。

関数名だけを見出しにせず、平易な動作説明と対応させる。疑似コードを実装のコピーのように見せない。設定値・例外・再試行の扱いを簡略化した場合は、その範囲を隣に記す。

## 全体の対応表

| 段階 | 実際の入口・主要関数 | 入力と出力 | 図に必ず残すこと |
| --- | --- | --- | --- |
| 教授が授業を準備・公開 | `ReleaseLifecycleService.create_draft_from_onboarding()` / `run_preflight()` / `publish()` | オンボーディング内容と教材から公開版へ | 下書きと公開版は別。公開時にも条件を確認する |
| 学生が授業を開く | フロントの `createStudentConversation()` → `StudentTutoringService.create_conversation()` → `SQLiteStudentRepository.save_conversation()` | 学生・授業から公開版に結びつく会話へ | 質問の送信は不要。学習目標の作成とは別の呼び出し |
| 受信を許可する | `ProactiveOutreachService.update_preference()` | 学生・授業・受信設定 | 会話の作成だけでは受信同意にならない |
| イベントから目標・機会を作る | `GovernedAutonomyService.observe_events()` / `_observed_event()` / `create_opportunity()` | 公開版、会話、観測、目標、許可から支援の機会へ | 空の会話と会話未作成を区別。起動条件には優先順がある |
| 予定された再実行を準備する | `materialize_due_wakeups()` | `AutonomousWakeUpV1`から新しい`ProactiveOpportunityV1`へ | 前回の処理を無制限に回すのではなく、新しい機会を作る |
| 期限の来た仕事を引き受ける | `process_due()` → `claim_autonomous_opportunity()` → `_process_claimed()` | 対象の機会から、占有期限付きの実行へ | 一時停止・期限切れ・他ワーカーによる占有 |
| 行動を決め、内容を検証する | `GovernedAutonomousTutoringGraph.run()` / `_build_graph()` | `AutonomousJobInput` → `AutonomousJobResult` | no-action、権限不成立、生成結果の不成立、1回の修復、呼び出し結果不明時の停止 |
| アプリ内に配信する | `_deliver()` → `schedule_trigger()` → `process_trigger()` → `materialize_proactive_message()` | 検証済みの内容から、受信箱のメッセージと引用へ | 保存時の権限再確認、既存メッセージの再利用、配信の見送り |
| 実行結果を保存する | `SQLiteStudentRepository.commit_autonomous_job()` | 計画・行動・結果・トレース・次回予約 | 配信保存とは別。配信成功時の試行回数加算を、目標完了と混同しない |
| 学生が返答する | `StudentTutoringService.submit_message(..., responding_to_outreach_message_id=...)` | 配信メッセージに対応した返答 → 対話・引用・学習記録 | どの働きかけへの返答かを追える。評価できない入力は未評価のまま |
| 目標の完了を判定する | `_autonomous_follow_up()` → `DeterministicAutonomousGoalManager.interpret()` | 対象の目標と同じ公開版の概念別の証拠 → 継続／完了の判定 | 採用経路のモード・方針・証拠条件。無関係な概念の正解で完了させない |
| 教授が配信を予約する | `ProactiveOutreachService.schedule_trigger()` | 教授が指定した学生・時刻・内容・教材 → 予約 | イベント検出による自律判断とは別の開始経路。質問履歴は不要 |

ファイルは主に `src/digital_twin/student/` の `publication.py`、`service.py`、`proactive.py`、`autonomy_service.py`、`autonomy_runtime.py`、`autonomy_control.py`、`repository.py`。

## 例1：何が自律処理を動かしているか

実関数：[scripts/autonomous_tutoring_worker.py:25](../../../scripts/autonomous_tutoring_worker.py)。図：[ワーカーの実行サイクル](../diagrams/implementation/02-worker-cycle-ja.drawio)。

次は**実コードの抜粋**。同じ名前の`process_due()`でも、前半は自律ジョブ、後半は配信予約を扱う別サービスである。

```python
async def _process_once(app, *, worker_id: str, batch_size: int) -> None:
    app.state.governed_autonomy_service.observe_events(limit=batch_size)
    await app.state.governed_autonomy_service.process_due(
        worker_id=worker_id,
        limit=batch_size,
    )
    app.state.proactive_outreach_service.process_due(limit=batch_size)
```

`main()`は、この処理が終わってから既定30秒待つ。厳密な30秒周期ではない。`--once`なら1回で終了する。予期しない例外をこのループがすべて吸収して継続するわけではなく、その場合は外部からの再起動が必要になる。

## 例2：最初の質問なしで、なぜ復習が始まるか

実関数：`GovernedAutonomyService.observe_events()`と`_observed_event()`。以下は**条件の優先順を保った疑似コード**。名前付きの条件は説明用であり、すべてが実在する関数名ではない。

```text
observe_events:
    公開版・方針・受講登録・受信同意が有効な学生を対象にする
    目標がなく、現行版または旧版の会話があれば、目標を作成する
    各目標について、イベントを次の順序で調べる

_observed_event:
    旧版の会話だけがある              → NEW_COURSE_RELEASE
    現行版の会話がない                → イベントなし
    最新の観測に誤概念がある          → MISCONCEPTION
    同じ概念で高い混乱が2回続く       → REPEATED_CONFUSION
    最新の評価が部分正解または不正解  → PRACTICE_INCOMPLETE
    学生の最後の発言から既定72時間以上 → STUDENT_INACTIVITY
    この目標の過去の行動結果を新しい順に調べる:
        answered / dismissed         → イベントなし
        delivered / failed:
            記録から24時間以上        → PRACTICE_INCOMPLETE
            それ以外                  → イベントなし
    目標の作成から24時間以上          → SPACED_REVIEW_DUE
    それ以外                          → イベントなし
```

過去の行動結果を調べる際、結果がないものや上記以外の種類は読み飛ばす。高い混乱は、直近2件が各0.7以上で概念が重なる条件。初回復習はこの優先順の末尾にあるため、24時間経過だけで常に復習配信になるわけではない。

**具体例：** 学生は授業画面を開いて受信に同意したが、質問は0件。イベント監視で目標が作られ、他の先行条件に該当しなければ、目標作成から24時間以降に復習の候補になる。これは実装から構成した例であり、新しい実測結果ではない。

## 例3：1件の自律ジョブで、どこまで生成を繰り返すか

実関数：`GovernedAutonomousTutoringGraph._build_graph()`。以下は**すべての通常のグラフ遷移を含む疑似コード**。内部例外やプロバイダ呼び出しの保存処理は続く説明に記す。

```text
_observe                          # 機会の時刻・状態・目標・試行上限
if stopped: goto record_no_action
_plan                             # 許可候補から1つ提案
_authorize                        # 方針・同意・教材・行動などを照合
if stopped: goto record_no_action
_generate
_validate
if valid: goto finalize
if provider_outcome_uncertain: goto record_no_action
if repair_already_used: goto record_no_action
_repair                           # 最大1回
_validate                         # グラフ上の名前はvalidate_repair
if invalid: goto record_no_action
goto finalize

record_no_action:
    _record_no_action             # responseを残さず、見送り結果を作る
finalize:
    _finalize                     # 結果と必要な次回予約を作る
    return AutonomousJobResult
```

出力が不成立の場合の修復と、成否不明の外部呼び出しを再送することは区別する。後者は同じ呼び出しを繰り返さず停止する。`run()`はSQLiteのチェックポイントを使い、機会IDを実行の識別子にする。

`_finalize()`が作る結果は、配信が保存済みである証拠ではない。実際のアプリ内配信は、その後の`_deliver()`が行い、結果を更新する。

**次回予約：** 目標がactiveであり、通常の配信候補が作られた場合、または静穏時間・頻度・同概念の間隔で見送った場合には、24時間後のwake-upを作る。実際に予約が残るかは結果の保存に依存し、実行時に目標・方針・試行上限などを改めて確認する。すべての失敗を自動で再実行するわけではない。

## 例4：現在の行動選択と、まだ弱い入力

実関数：`GuardedPolicyValuePlanner.plan_with_trace()`と`default_planning_state_card()`。候補の比較と、現行の組み込み先を図上で区別する。

以下は**選択条件を要約した疑似コード**。

```text
allowed  = event_scoped_eligible_actions(event, policy.allowed_actions)
baseline = preferred_event_action(event, policy.allowed_actions)
if evidence_not_ready: return NO_ACTION

score every allowed action using the analytic forward model
best = highest utility; resolve ties in event order
proposal = model proposes an action and a bounded episode
if provider identity changed: propagate error
if proposal failed or contains disallowed actions: return baseline

if proposal.action == best and best != baseline
   and utility(best) >= utility(baseline) + 0.04:
    select best
else:
    select baseline
```

**実コードの抜粋：**

```python
mastery_probability=min(0.95, (attempts + 1) / (attempts + 2)),
```

この`attempts`は目標に対する配信成功の回数。0回なら0.50、1回なら約0.67になり、学生が正解したことを必要としない。この入力を「正確に推定した理解度」とは説明しない。正誤の記録、目標の完了判定、支援選択の簡易入力をそれぞれの実際の接続で示す。

## 例5：同じメッセージを二重に送らない仕組み

実関数：`GovernedAutonomyService._deliver()`、`ProactiveOutreachService.process_trigger()`、`SQLiteStudentRepository.materialize_proactive_message()`と`commit_autonomous_job()`。図：[配信保存とジョブ保存](../diagrams/implementation/03-delivery-commit-ja.drawio)。

以下は**配信可能な結果に対する疑似コード**。実際の引数のうち、今回の説明で重要なものを示す。

```text
K = "autonomous-action:" + opportunity.idempotency_key
trigger = schedule_trigger(
    idempotency_key=K,
    scheduled_for=opportunity.earliest_action_at,
    expires_at=opportunity.latest_action_at,
    ...
)
delivery = process_trigger(trigger.id)
update the action and outcome using delivery
commit_autonomous_job(result)
```

既存のKがあれば、内容・学生・公開版・配信期間などが一致する予約を再利用する。`process_trigger()`は既に保存されたメッセージを返せる。新規保存では、`materialize_proactive_message()`が書き込みの占有後に権限・同意・公開版・頻度などを再確認し、メッセージと引用などを同時に保存する。

**具体的な障害例：** メッセージ保存後、ジョブ結果の保存前にワーカーが停止した。占有期限が切れてから同じ機会を引き受け直し、同じKと元の配信期間を使うことで、既存メッセージを再利用してジョブ結果を保存する。再試行時の現在時刻で配信期間を書き換えると予約の同一性が崩れるため、元の期間を使う。

これはローカルのアプリ内メッセージとジョブ保存の契約。外部チャネルのexactly-once配信を保証する説明にはしない。

## 例6：目標の完了は、配信の回数と分ける

実関数：`DeterministicAutonomousGoalManager.interpret()`。以下は**証拠カウント方式の学習記録を使う場合の疑似コード**。

```text
require the goal's exact objective in the same course release
require the learner record to have the matching course/release scope
targets = every concept of that objective

complete = all(
    concept exists
    and concept.correct_evidence_count >= 2
    and concept.incorrect_evidence_count == 0
    and concept.attribution_confidence >= 0.5
    for concept in targets
)
```

呼び出し側は当該学生の記録を渡す。対応する目標・領域モデルがない、または曖昧な場合は完了にしない。配信成功は`attempt_count`を増やすが、この完了条件の代わりにはならない。上限に達した目標は、追加の試行を止めるが、それだけでcompletedにならない。

**具体例：** キャッシュコヒーレンスの目標に対する正解の証拠で、仮想記憶の目標まで完了させない。以前の不正解が現在のカウントに残ると完了を妨げる、という現行ルールの限界も説明する。ソフトウェア上の完了は、独立に測定された学習到達度ではない。

## 図とスライドへの反映

- 全体の利用フローでは、会話の作成とワーカーによる目標作成を別のアクションに分け、実関数名と担当を追加した。ワーカー図と配信保存の図を、対応する詳細として接続する。
- 全体図から「ワーカーの実行サイクル」、次に「1件の実行」、最後に「配信と保存」の順に拡大する。同じ関数・対象データを引き継ぐ。
- 権限確認は生成前だけに描かず、配信保存時にも描く。配信保存とジョブ保存の境界を残す。
- 正常経路に加え、権限不成立、教材不足、時刻前、頻度制限、no-action、生成の不成立、成否不明、再試行、目標終了を、全体のモデルで追跡できるようにする。
- ER図は実テーブルと外部キーを照合する。学習目標と評価の概念上の照合を、存在しない物理的な外部キーとして描かない。
- 失敗案は、同じ具体例について期待出力・実際の出力・変更した処理・比較結果を揃える。関数の列挙だけで説明を終えない。
- コードは重要な判断に絞って、図と並べて読める分量にする。説明に必要な分岐が入らない場合は、参照で接続した次の本編ページに分ける。
- ここで作成した技術図は日本語の確認素材であり、英語の本番スライド用には配置と文字量を改めて調整する。

## 確認記録

確認時のHEAD：`9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`。作業ツリーには既存の未コミット変更がある。図の直接の入力ファイルは`diagrams/implementation/source-sha256.txt`に記録する。新しいモデル評価やプロダクト変更は行っていない。

次の既存テスト6件が成功した。いずれもこの資料の実装説明に対応する確認であり、教育的有効性の評価ではない。

- `test_scheduled_wakeup_preserves_concept_and_evidence_lineage`
- `test_delivery_reconciles_after_crash_before_autonomous_commit`
- `test_pause_preserves_goal_and_due_work_until_resume`
- `test_goal_attempt_limit_stops_additional_delivery`
- `test_observer_materializes_new_release_event_once`
- `test_proactive_uncertain_generator_call_is_not_repeated`
