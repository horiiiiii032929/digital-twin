# Anticipated questions: Chapter 4, Event-driven student support (final 70-slide deck)

Covers slides 38–58 and 69. Written 9 September 2026 against the final deck and the professor evidence archive (`reports/generated/professor-evidence`). Evidence paths are relative to the extracted archive. The earlier `defence-notes.md` covers the 24-slide deck and does not include this chapter.

## Slide 46: You used an LLM to judge answers and an LLM to write the gold labels. Why should I trust 32/32?

You should not treat it as accuracy. It is a component regression on a fixed packet. The 32 cases and their expected labels were authored with a coding assistant, never validated by a human, and the same packet was already used to find the V1 failure. So 32/32 shows the V2 gate fixed the observed failure without breaking other cases. The Wilson 95% interval for 32/32 is [0.89, 1.0], and the four concepts make the cases dependent, so no population accuracy claim follows.

**Evidence:** `datasets/research/05_evaluation/datasets/post-report-source-assessment-v1.json` (`gold_author: "coding-assistant; independent human validation pending"`); per-case rows in `outputs/reports/generated/post-report-source-assessment-002-luna-live-001/cases.jsonl`; raw prompts and replies in `provider.jsonl` of the same folder.

**日本語メモ:** 32/32は「同じ袋の中で失敗を直した」証拠。精度主張ではない。gold は assistant 作成で人間未検証と最初に言う。

## Slide 46: What does "label agreement" count, and why does it include abstentions?

Agreement means the assessor's outcome equals the expected label, and the expected label is `not-assessed` for 12 of 32 cases (unsupported additions, questions without an attempt, source and scope boundaries). Abstaining correctly on those is the behaviour being tested, so it counts. The second column, "Assessed", shows how many cases received a substantive judgment. V2 assessed 16 of 32, fewer than V1's 18, so coverage went down while agreement went up. Increasing coverage was not the objective.

**日本語メモ:** agreement = 正しい棄権を含む。Assessed列で「判断した件数」を別に見せている。

## Slide 46: Is the initial Luna 30/32 a fair number?

It flatters Luna V1. On the four "unsupported addition" cases, where the student appends a claim the source does not establish, Luna V1 returned a substantive judgment every time. Three replies used an outcome/reason pair the schema validator rejects, so the assessor recorded them as `not-assessed` with reason `assessment-provider-or-contract-failure`, which then matched the expected label. Only the fourth, a valid `partial`, counted as an error. Judged on what the model intended, Luna V1 agreed on 26 of 32. Sol V1 abstained on all four with `model-insufficient-evidence`, so its 31/32 is genuine. Say this before the professor finds it: the validator masked three V1 errors, and the V2 prompt fixed them.

**Evidence:** `outputs/reports/generated/post-report-source-assessment-001-luna-live-001/cases.jsonl`, kind `unsupported-addition`; raw replies in `provider.jsonl` show `partial/insufficient-evidence` and `incorrect/insufficient-evidence` combinations.

**日本語メモ:** Luna V1 の 30 は validator が 3 件を棄権扱いにした結果。意図ベースでは 26。先に自分から言う。

## Slide 46: What exactly did the "source check" change?

Two things, not one. The target-support gate refuses to judge when a professor target clause is not literally supported by an approved source range. That fires on exactly one case, the unsupported-target boundary, and it prevents the provider call. The other fix was four added sentences in the V2 system prompt telling the model to abstain when an appended claim is not established. Those cases still call the model. Six of the seven "no call" cases were already prevented in V1 by existing source and scope checks; only one is new.

**Evidence:** system messages differ between the V1 and V2 `provider.jsonl` files; `provider_called` flags in `cases.jsonl`.

**日本語メモ:** 「ゲート」で直したのは 1 件、残りはプロンプト修正。7 件の call 抑止のうち新規は 1 件。

## Slide 46: Can I reproduce this run?

The dataset, source snapshot, exact system and user messages, raw model replies, and per-case outcomes are all in the archive. The models were called as `gpt-5.6-luna` and `gpt-5.6-sol` with reasoning effort low and medium, output cap 3000, no seed. Two caveats. The recorded invocation was a temporary script in `/tmp` that was not archived, so the documented reproduction command in the results file uses the checked-in `scripts/run_post_report_assessment.py` instead. And cost is computed locally from the price table in `model_policy.py`, not from a provider invoice. A rerun would produce different model text because no seed was set.

**日本語メモ:** 入力・出力・設定は全部ある。実行スクリプトは /tmp で消えた。コストはローカル計算。

## Slide 46: Why Luna-low and Sol-medium, and why not a stronger model everywhere?

Luna is the low-cost tier already used by the runtime assessor. Sol was the more expensive comparison at about 16 times Luna's cost per call. On this packet Sol V1 made one fewer error than Luna V1 but was not tested under V2. The decision kept Luna V2 as an explicit experimental option and literal assessment as the fallback, and it did not change the default profile.

**日本語メモ:** Sol は V2 未実施。V1 比較のみ。デフォルト未変更。

## Slide 44 and 46: In the demo Alex's reply was never assessed. Does slide 46 fix that?

No. Slide 44 is an attempt-recognition failure: the detector did not classify Alex's natural reply as an attempt, so no assessment ran. Slide 46 is about what happens after an attempt is recognised. Both are needed and they are separate components.

**日本語メモ:** 44 は attempt 検出、46 は検出後の判定。別部品。

## Slides 47 to 52: Are these estimators running in the app?

No. The demo planner uses model-supported observation and planning. Count, Decay, BKT and PFA are research estimators compared offline on synthetic histories. Slide 47 is a conceptual separation of three jobs, assess, predict and decide, not a description of one enabled runtime chain.

**日本語メモ:** アプリでは動いていない。研究比較のみ。

## Slide 49: 8,160 runs sounds large. How many students?

Zero. It is 480 synthetic histories reused across 17 conditions. The 480 come from 12 personas, 2 transition families and 20 seeds. The simulator assumptions create both learning and forgetting, and only the oracle condition sees hidden state. No LLM calls, no grades.

**Evidence:** `outputs/reports/generated/post-report-learner-policy-001-local-001/histories.jsonl` and `open-loop-observations.jsonl`.

## Slide 51: The Brier differences are tiny. Are they meaningful?

They are small and the intervals are bootstrap intervals over the synthetic grid, not over students. Decay and BKT improve slightly on Count; PFA is worse in this configuration. The conclusion drawn was only to keep Count as the control and treat Decay as worth refining. The earlier report result, BKT versus Count under constant timing, was inconclusive, and this newer test does not contradict it because the configurations differ.

## Slide 52: BKT with value timing gained mastery. Why not adopt it?

Because the gain of about 0.029 on the 0 to 1 simulator scale came with about 5 extra messages per history, and the baseline changed from the report's count/constant to count/conditional. The report's earlier +0.014 and this +0.029 are not the same comparison and must not be presented as a doubling. The value policy also differs from the app's LLM planner, so a simulator gain does not transfer to the product.

**日本語メモ:** +0.014 → +0.029 を「倍」と言わない。ベースラインが違う。

## Slides 53 and 54: Is "12 to 0 unsupported completions" a learning result?

No. It is a correctness result: goal completion now requires committed evidence about each target concept. The rule is two correct assessments, zero incorrect, confidence at least 0.5. That contract is a prototype threshold, not a validated mastery model. The comparison is matched, 72 histories per arm, only completion logic differs, deterministic planning with no LLM calls, and it passed 19 run gates. Autonomous messages rose from 9.06 to 10.61 per history.

## Slide 55: 670 scenarios, zero violations. What does that not show?

It shows execution controls held across 1,836 real model calls: no unauthorized action, wrong recipient, consent or frequency violation, duplicate or malformed response. It does not rank teaching quality, and 670 is not the denominator for every check because each risk has its own subset. Be aware that the raw run directory for this confirmation is not in the evidence archive, only the machine record, instrument and results markdown.

**日本語メモ:** 実行制御の証拠。教育効果ではない。生ログはアーカイブに無い。

## Slide 57: Why is the recovery detector still observation-only?

It detected 23 of 24 supportable cases and suppressed all 36 no-action cases, but the miss came from word-form differences that left 4 of 9 query terms matched. That is a matching weakness I want fixed on fresh cases before any message is sent. The raw run output for this shadow confirmation is also not in the archive.

## General: You relied on LLMs to evaluate LLM output throughout. Where are the human checks?

Most factual and grounding studies in the deck ran network-free and were scored deterministically against hidden gold, with no judge model. Where an LLM reviewer was used, the audited teaching comparison on slides 31 to 36 has full prompts, raw outputs, calibration controls and a failed reviewer gate that I report as a failure. The source-gated assessor on slide 46 has full prompts and outputs but no human labels. There is no completed independent human label anywhere in the evaluation. The file named a "human audit" for the 120-case rehearsal was actually a manual source audit performed by Codex, the quality-pilot human audit is still marked pending, and the only researcher confirmation is a four-case policy-boundary packet that I signed myself. Every gold label is assistant-authored or script-generated, and the documents say so. Independent human validation is the stated next step, not something already done. Do not claim otherwise if asked.

**Evidence:** volume 2 of the archive, `complete-data/research/05_evaluation/judgments/` (34 files) and `complete-data/research/05_evaluation/instruments/llm_judge_v1.prompt.md`, hold the sanitized judge summaries and the fidelity judge prompt; volume 1 alone did not include them.

**日本語メモ:** 人間による独立ラベルは一件も完了していない。"human-audit" ファイルは Codex 実施か pending。正直に「次の課題」と言う。
