# 分かりやすい教材による実AIの応答

新しい架空の固有名詞を使わず、パスワード再設定リンクを題材にした。教材と質問は作成した合成データ。以下の回答は実際のアプリの永続会話サービスと既存実験構成を通した外部AIの出力で、作文や模範解答ではない。ブラウザ録画はまだ行っていない。

## 教材（作成した合成ルール）

A password reset link expires after 30 minutes and works only once. Requesting a new link invalidates all previous reset links for the account. An expired or used link cannot change the password.

これは本デモのルールであり、すべての実サービスのパスワード仕様を説明するものではない。

## 指導設定：説明してから理解を確認する

### 監査・修正を追加した候補

**学生**

I requested a password reset link yesterday. Can I still use it today?

**実際に返された回答**

No. A password reset link expires after 30 minutes, so a link requested yesterday is expired and cannot change the password.

What happens to previous reset links when a new one is requested?

**学生**

I think it expired after 30 minutes, so I should request a new one. Will the old link work once I get a new link?

**実際に返された回答**

No. Requesting a new password reset link invalidates all previous reset links for the account, so the old link will not work. The new link expires after 30 minutes and works only once.

What happens if you try to use the new link after it has already been used or after 30 minutes?

### 実験の比較元

**学生**

I requested a password reset link yesterday. Can I still use it today?

**実際に返された回答**

A password reset link expires after 30 minutes and works only once.

**学生**

I think it expired after 30 minutes, so I should request a new one. Will the old link work once I get a new link?

**実際に返された回答**

Requesting a new link invalidates all previous reset links for the account.

An expired or used link cannot change the password.

## 指導設定：最初に学生の考えを尋ねる

### 監査・修正を追加した候補

**学生**

I requested a password reset link yesterday. Can I still use it today?

**実際に返された回答**

Consider the link’s age and whether it has already been used. What does the stated expiration rule imply about using a link requested yesterday today?

**学生**

I think it expired after 30 minutes, so I should request a new one. Will the old link work once I get a new link?

**実際に返された回答**

I could not validate that tutoring response. Please restate the step you are working on or ask the instructor.

### 実験の比較元

**学生**

I requested a password reset link yesterday. Can I still use it today?

**実際に返された回答**

For “Can I still use it today?”, what is your current explanation, and which step are you unsure about?

**学生**

I think it expired after 30 minutes, so I should request a new one. Will the old link work once I get a new link?

**実際に返された回答**

Hint: Requesting a new link invalidates all previous reset links for the account.

How would you use this detail to revise your attempt?

## 今回分かったこと

説明型の候補では、この2ターンについて質問への回答と確認質問が得られた。問い返す候補は1ターン目に期限を考えるよう促したが、2ターン目は保留した。どちらも残し、成功例だけから教授忠実性や一般的品質を主張しない。

使用モデルはgpt-5.6-luna。比較元と候補の計画・生成はlow、候補の監査・修正はmedium。新しいSol呼出なし。
外部呼出試行18回、記録された費用US$0.0125484。今回の2設定は同じ教材・質問を使用。

[実行・評価記録](../../../research/05_evaluation/plain-language-teaching-demo-001-results.md)
