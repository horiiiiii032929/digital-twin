# Project completion plan

Status: development results are registered separately; no completion claim.
The [completion contract](../../docs/project-completion-contract.md) defines the
working end state and supersedes less strict prospective acceptance thresholds
in this earlier plan. Historical run criteria and results remain unchanged.

## 日本語での目的と進め方

最短で埋めるべき不足は、選択済みの構成と実際の外部モデルを使い、学生との
継続的なやり取りを検証することです。既存の30日間実験025は保存・採点・
送信処理の回帰検証であり、モデルによる計画と生成を含む最終構成の検証では
ありません。025は変更せず、新しい実験として追加します。

短い実験が動くだけでPJ全体の完了とはしません。まず接続と継続動作を確認し、
次に回答品質と教授設定への応答を確認し、最後に画面操作を含む同一構成の
一連の流れを確認します。時間をかけられる場合も、新機能を増やす前に品質上の
失敗を修正します。2026-09-05にユーザーが必要な実装・評価について「予算は一旦度外視」と指示しました。
以下の有限上限は費用節約の目標ではなく、暴走防止と段階的な結果確認のための運用上限です。
新規の開発実験3件だけを実行許可に登録し、既存の評価凍結と消費済み確認セットは保持します。

| 段階 | 成果物 | 進む条件 |
| --- | --- | --- |
| 最小の統合検証 | 選択済み構成を使う新しいランナー、模擬クライアントでの接続テスト、短いライブ試行 | 構成一致、呼び出し記録、保存・再起動・送信制約を確認 |
| 中心的な品質の確認 | 新しい問題での根拠付き回答と指導設定の比較、30日間のライブ試行 | 品質基準と安全条件を事前固定し、失敗を保持 |
| 完了判定 | 教授の教材登録から学生支援・教授画面までの操作、同時利用・障害試験、結果とレポートの整合 | 同じリビジョンと構成に結び付く証拠が揃う |

実際の教授らしさには教授による確認、学習効果には学生を対象とした適切な
評価が必要です。人工的な指導設定の比較や仮想学生による試行で代替したとは
扱いません。所要時間は障害や品質結果に依存するため、完了時刻は保証しません。

## Decision question and prediction

Can the selected local tutor composition maintain a governed, persistent
conversation and eligible proactive follow-up when its selected semantic model
is actually invoked, rather than replaced by the deterministic simulation path?

Prediction: binding the existing components through the product composition
will preserve authority, citation lineage, and restart consistency. The main
risks are configuration drift, missing model invocation, an incompatible model
response, and grounding or intervention errors previously hidden by fixtures.

The first instrument is `final-profile-live-longitudinal-development-001`,
implemented in `scripts/run_final_profile_longitudinal.py`. It is a development
instrument, not a sealed confirmation and not a replacement for experiment 025.
Its initial scope is two personas, one common teaching profile, and paired
reactive/autonomous conditions: four histories. Contrasting teaching profiles
are a subsequent stage, not an implemented feature of this first experiment.

## Composition and boundaries

- Bind the selected profile in
  `research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json` and the
  current product assembly. Record their hashes and the effective components;
  fail on divergence rather than silently choosing an older harness default.
- Preserve the selected deterministic factual generator where the final
  profile requires it. Actual model use applies to the selected semantic
  planning paths; making every factual response generative would be a new
  candidate requiring a separate comparison.
- Use the actual tutoring service, persistent repository, autonomy worker,
  delivery path, and virtual clock. Keep learner truth inaccessible to the
  tutor and model prompts.
- Install a fresh synthetic multi-source fixture for the longitudinal runner.
  This does not validate PDF ingestion, professor onboarding, authentication,
  or browser interaction. A separate local HTTPS journey must exercise those
  boundaries using the same selected composition.
- Do not infer the currently selected gate from confirmation 028 alone. The
  subsequent product gate-selection result did not promote its v4 candidate.
  Resolve component selection from the current profile and its decision chain.
- Keep 024, 025, 028, and the consumed factual sets unchanged. No rerun,
  rescoring, or tuning of the consumed 1,000/10,000 confirmation sets is planned.

## Finite stages

1. **Instrument development.** Validate manifests and profile binding; use a
   fake provider client to test transport accounting, restart, failures, and
   bounds. Label every such result `contract-smoke`, never live evidence. Run
   `npm run verify:evaluation-instruments` before provider execution.
2. **Bounded live development.** Initial operational maximum: four histories, seven virtual
   days, 500 provider attempts, USD 5, concurrency two. Serialize each learner's
   events. Stop at the first exhausted bound or critical violation. Record
   failures and unused allocation. Execute only with recorded bounded authority.
3. **Core quality development.** Introduce a fresh development packet with
   independently checked source-answer mappings and explicit Socratic versus
   explanatory settings. Compare the same model-backed reactive and autonomous
   conditions; add a grounded generic control for profile responsiveness.
   Separate changes to evidence selection from changes to model prompts.
4. **Fresh confirmation.** After development passes, freeze a new source,
   wording, and seed-disjoint packet. Proposed longitudinal design: six personas
   × two teaching profiles × two conditions, 24 histories over 30 virtual days,
   restart on day 15. Proposed limits: 1,500 attempts and USD 5, subject to pilot
   measurements and a recorded prospective confirmation protocol. This is a bounded engineering
   confirmation, not a statistically powered learning-effect study.
5. **Integrated local qualification.** Exercise upload, instructor approval and
   publication, student dialogue and outreach, dashboard aggregation, withdrawal,
   restart and restoration on the same revision. Include enough synthetic
   learners to test the dashboard's five-learner privacy threshold. Add a bounded
   concurrency and provider-failure check; report its actual load and duration.
6. **Decision and report.** Publish Keep/Refine and per-case evidence for every
   named run. A valid quality failure ends that confirmation; any correction is
   developed separately and confirmed on new cases. Avoid an indefinite retry
   loop. Update the release profile only after supporting evidence exists.

## Dataset and metrics

Version the synthetic course, source permissions, concepts, questions, profiles,
learner rules, seeds, expected actions, scorer, and configuration before each
run. Use a separate development and confirmation split. Independently review
source support and at least 20% of quality labels before sealing confirmation.
Include normal questions, misconception attempts, ambiguous/no-evidence input,
cross-course requests, graded work, student opt-out, quiet hours, provider
failure, restart, and stop/goal completion. Synthetic source installation must
be identified in every output summary.

| Measure | Prospective criterion or interpretation |
| --- | --- |
| Wrong recipient/course/release, unauthorized action, consent/timing/frequency breach, duplicate, unbounded loop | Zero; hard stop and preserve evidence |
| Citation locator and release lineage | 100%; unsupported factual content is assessed separately |
| Model invocation and accounting | Every expected attempt recorded with model identity, usage and outcome; no silent substitution counted as live |
| Restart continuity | No lost committed state or duplicate delivery |
| Permitted action and explicit profile adherence | At least 95% on applicable confirmation opportunities, with profile/persona slices |
| Fully supported factual response | At least 95% on fresh answerable confirmation turns; preserve the previous 63.25% result |
| No-evidence and graded-work safe action | At least 95%; any severe unsupported or prohibited answer is separately a hard failure |
| Latency, cost, token usage, memory, fallback rate | Report distributions, maxima, measurement scope and missing values |
| Intervention utility, missed/wasted interventions, simulated mastery | Diagnostics tied to simulator assumptions; no real-learning claim |

Pilot samples test integration rather than estimate population accuracy. Report
counts and uncertainty; cluster comparisons by learner history rather than
treating dependent turns as independent samples. Classify failures as data,
parsing, chunking, query, ranking, model, policy, integration, or operational.

## Commands and evidence

The new runner's intended interface is:

```sh
uv run python -m scripts.run_final_profile_longitudinal --validate
uv run python -m scripts.run_final_profile_longitudinal --contract-smoke
```

The proposed live command, only after instrument checks and bounded authority:

```sh
uv run python -m scripts.run_final_profile_longitudinal --execute --output-dir reports/generated/final-profile-live-longitudinal-development-001 --maximum-cost-usd 5 --maximum-calls 500 --days 7 --concurrency 2
```

Freeze effective code/configuration during execution; do not commit or change
the model/profile while a run is in flight. Preserve per-case transcripts,
component hashes, model identities, call ledger, and aggregate metrics under
the ignored output directory. Add a sanitized result and machine-readable
record to `research/05_evaluation/`, register every outcome in
`research/05_evaluation/result-registry.md`, and retain old unfavorable results.

## Existing evidence

- [Quality contract](../../docs/quality-and-learning-plan.md)
- [Provider-backed confirmation 024](../05_evaluation/governed-full-autonomy-v2-1-persona-confirmation-024-results.md)
- [Deterministic 30-day correction 025](../05_evaluation/governed-full-autonomy-v2-1-multi-concept-confirmation-025-results.md)
- [Multi-source live confirmation 028](../05_evaluation/governed-full-autonomy-v2-1-corpus-confirmation-028-results.md)
- [Product gate decision](../05_evaluation/product-evidence-gate-selection-001-results.md)
- [Profile proxy failure](../05_evaluation/professor-fidelity-proxy-c0-c3-003-analysis-correction-001-results.md)


## Approved profile context candidate

Decision question: do different approved teaching settings reach and influence the
model? The existing control omits these settings from requests. The opt-in
`approved-teaching-profile-context-v1` candidate supplies all eight approved,
course/release/hash-bound fields to reactive planning, hierarchical planning, and
bounded wording. Predict identical context-off requests and distinct context-on
requests; deterministic tests establish propagation only. Compare fresh matched
Socratic/explanatory settings using the versioned responsiveness packet before
promotion. Record style-intent selection, actual delivered content, fallbacks,
boundary violations, provider identity, tokens, latency and cost. A different
intent alone does not demonstrate faithful teaching; the current bounded renderer
may limit the styles that can actually be delivered. Defaults remain unchanged.

## Completion priorities when budget is not the constraint

Priority follows the three approved project pillars, not the number of model
calls or features. Complete each development comparison before a fresh sealed
confirmation; preserve both unsuccessful candidates and the selected control.

1. **Answer adequacy and teaching behavior.** Current source support does not
   establish that requested details were answered. Evaluate an explicit async
   semantic answerability/source-span candidate on fresh public development
   questions, retaining deterministic citation/span validation. Separately test
   whether approved style preferences affect delivered teaching, not just intent
   labels. If the bounded renderer cannot express the required behavior, compare
   a grounded style renderer against it; no silent generator replacement.
2. **Instructor knowledge ingestion.** Product jobs currently accept PDFs.
   Connect transcript and anonymized forum/text ingestion through the same
   permission, preview, approval, provenance and withdrawal workflow. Raw audio
   transcription is a separate optional candidate, not established capability.
3. **Instructor feedback loop.** Current aggregates identify source-level
   confusion. Qualify a time-window and denominator before displaying percentages.
   Concept-level labels require an evaluated mapping. Expose existing draft review
   in the professor interface; changes to course materials remain professor-approved.
4. **Whole-system operation.** Use the accepted composition for PDF/text upload,
   publication, realistic student dialogue, consent-aware proactive help,
   five-learner professor insights, review, withdrawal and recovery. Measure actual
   response latency and bounded concurrency, rather than course-list latency.
5. **Fresh longitudinal confirmation and report.** After the preceding quality
   gates, freeze new sources/questions/seeds for 24 histories over 30 virtual days.
   Record every actual model path, fallback, restart and failure. Real-professor
   review and real-student learning remain distinct evaluations; simulations do
   not replace them. Report implementation, engineering validation and educational
   evidence separately.

Large-scale cloud deployment, extra messaging channels, fine-tuning and additional
retrieval providers are lower priority until these central boundaries work. A more
expensive model alone cannot repair missing profile context or answerability logic.
