# Post-report learning and answer candidates

Implementation work follows [the prospective plan](../research/04_experiments/post-report-product-completion-001.md). Submitted report files and the selected release profile are unchanged. These are explicit experimental compositions, pending comparative quality evaluation; implementing a candidate does not qualify it for promotion.

## Implemented components

- Scoped observation reader joins the current student's conversations only within the same course/release. Count, decayed count (seven-day half-life), Bayesian Knowledge Tracing (BKT) and Performance Factors Analysis (PFA) are replaceable planning inputs. Delivery counts do not increase assessed evidence or goal progress. Missing sources, missing turn identity, insufficient confidence, duplicate turns and foreign scopes cannot create additional evidence.
- Recovery-aware completion requires two distinct correct assessed turns in the last seven days after the latest incorrect/partial result for every objective concept. It includes the current pending observation only inside the turn's atomic commit. Failed persistence cannot complete the goal; retry cannot count twice. The rule is a software criterion, not verified unassisted mastery.
- Literal assessment requires target statements to occur within approved source ranges and abstains on unsupported targets, extra claims, uncertainty and paraphrases. The optional model assessor evaluates one scoped attempt with exact source-quotation admission, preserving unknown provider costs and abstaining on failed judgments. Neither method is yet semantically qualified.
- An analytic-only action selector complements rules and guarded model planning. It uses the same permitted event actions and forward model without an external planning call.
- Explicit continuations can supplement retrieval with the previous student's question. Both queries independently pass the existing evidence gate; tutor prose is not a retrieval query. Named topic switches and refused exchanges do not carry context. The known Birch follow-up regression now supplies its causal-limit source across restart. This does not establish general retrieval quality.
- V17 adds one bounded structural/source repair to V11. V18 adds the existing V2 final-response quality audit to V17, with one issue-guided repair and re-audit. The exact rendered response is bound to the audit. Rejected, unchanged, unknown-cost, malformed or failed repairs are withheld. AI audits remain fallible.
- API, worker and generated preview share explicit composition inputs. Runtime identity records the assessment model as well as planner/generator choices, and the professor can inspect the learning configuration. Preview binding includes learning settings.

## Explicit local selectors

Use the existing credential-authenticated experimental entrypoint and existing staging configuration. No environment file is changed automatically.

```sh
APP_EXPERIMENTAL_TUTORING_CANDIDATE=v18-luna-sol-medium \
APP_POST_REPORT_LEARNING=assessed-decay \
APP_POST_REPORT_PLANNER=configured \
APP_POST_REPORT_GOAL_RECOVERY=true \
APP_POST_REPORT_MODEL_ASSESSMENT=true \
APP_POST_REPORT_CONTEXT_RETRIEVAL=true \
uv run uvicorn services.api.app.experimental:create_experimental_app --factory --host 127.0.0.1 --port 8000
```

The worker uses the same environment and `uv run python -m scripts.autonomous_tutoring_worker`. Existing worker-enabled and staging/auth requirements still apply. This example activates paid provider use; it is not a claim that this combination has passed evaluation or been deployed. The current evaluation allowance remains US$30 total.

`APP_POST_REPORT_LEARNING`: `control`, `assessed-count`, `assessed-decay`, `assessed-bkt`, `assessed-pfa`. `APP_POST_REPORT_PLANNER`: `configured`, `rules`, `analytic-only`. Boolean selectors accept only `true` or `false`. `APP_POST_REPORT_SOURCE_ASSESSMENT=true` selects the literal baseline; model assessment takes priority when explicitly enabled. Clearing post-report options and restoring the previously selected experimental version restores the historical behavior without rewriting observations. Legacy observations lacking assessment provenance remain excluded by the new reader.

V17 is `v17-luna-low`. V18 is `v18-luna-sol-medium`: Luna-low drafts and planning, Sol-medium final audit/repair. V18 can spend up to five draft/audit calls per generation plus planner calls; the graph may request generation twice. The paired runner's preflight now includes this worst case. A successful response-schema check is not a semantic pass.

## Engineering verification and remaining evaluation

Development regressions cover API/worker identity, source assessment, recovery, aborted commits/replay, cross-conversation evidence, the Birch retrieval failure, bounded repair, audit rejection, source substitution and cost retention. Existing professor preview tests are included. Logs are retained under `/tmp/post-report-*.log` during this session; the final verification entry will identify the final combined run. These development tests are not the five-hour acceptance evaluation and injected model outputs are not live quality evidence.

The professor configuration disclosure was checked on the real synthetic API at `http://127.0.0.1:8020` and UI at `http://127.0.0.1:5190/professor/delivery`, at desktop 1280×1000 and mobile 390×1000. Browser plugin not available; Playwright CLI was used. This sandbox uses deterministic answer generation and analytic planning. It is not a live V18 demonstration. Screenshots are in `/tmp/post-report-config-*.png`.

Next acceptance work must compare answer usefulness and unsupported claims, assessment precision and coverage, intervention quality, estimator calibration, same-composition operational recovery, and professor review/publication workflows. Human independent review, real-course permissions and longer-term learning effects remain separate dependencies. Do not convert the current implementation checklist into an assertion that all 41 items are completed.

### Review notes

The combined development run passed 249 tests before the final source-permission/time-order hardening (`/tmp/post-report-combined-regression.log`). The subsequent source-assessment tests passed 32 cases and the scoped evidence/recovery tests passed 40 cases. Source admission now also excludes retrieval-disallowed and superseded chunks. Equal-time contradictory binary observations are retained in the audit trail but excluded from order-dependent estimator updates; arbitrary observation hashes must not determine temporal order. Full current-tree verification is recorded separately after these changes.

Code review covers new component inputs, source/learner/release scope, bounded calls, cost retention, current-turn atomicity, replay, and API/worker/preview selector propagation. Known algorithmic limitations remain explicit: narrow literal coverage, fallible model judgments, heuristic temporal completion, a conservative conversation-continuation resolver, and unqualified estimator/policy utility. Engineering review does not certify those research claims.

## 有限範囲で固定した開発構成

[実験用構成記録](../research/05_evaluation/profiles/post-report-bounded-development-v1.json)に、V19、assessed-count、analytic-only、V2学生回答判定、目標回復、会話補助検索を明示した。integration002の152チェックと別の実worker再起動回帰を通した構成であり、標準リリースへの自動採用ではない。

V19は、撤回済み資料を読む要求と「生成中に公開が撤回されたらどうなるか」という仮定質問を限定的に分ける。V18はアプリ履歴のroleを検査器の語彙へ変換し、記録用クライアントが専用の応答schemaを保持するよう修正済み。実際の検査呼び出しを確認した。V2学生判定は教師側の目標全節が承認済み資料の範囲に文字列として存在することを先に要求する。学生の言い換え回答を禁止する仕様ではない。

推定器を高度にすれば改善するとは限らない。今回の30日成分比較では、時間減衰の予測精度が改善しても、conditional方針では不要な介入が増えたため、開発構成は解釈しやすいassessed-countを対照として維持する。

背景から送る支援文は引き続き既存の制約付き文体選択と承認済み引用の組立である。リアクティブなV19回答生成を背景配信にも使っているとは説明しない。両者のモデル・プロンプト・失敗時動作を構成記録で分ける。

追加評価の採点者はNano/Miniで共通化するが、アプリ内部のモデルは無断で置換しない。V19に定義されたSol修正役の追加課金呼び出しは実行しない。モデルレビューで校正が通らない場合、点数は診断用途に限定し、候補を追加して無期限に再挑戦しない。
