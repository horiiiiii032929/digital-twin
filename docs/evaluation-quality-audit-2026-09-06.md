# Evaluation quality audit, 2026-09-06

Initial scope: G7 prospective instrument and read-only evidence audit. Subsequent
live diagnostics and repairs are recorded in the [follow-up](evaluation-quality-follow-up-2026-09-06.md).
Independent human review, final qualification and a new release selection remain open.

## 日本語での結論

評価件数を増やすだけでは、評価の質は上がりません。現在必要なのは、自然な
質問が教材に本当に答えを持つか、採点器が誤回答を見抜けるか、同じ教材の
言い換えを独立した証拠として数えていないか、という確認です。

既存の品質計画は「約4つの異なる許可済み科目」を求めています。一方、新しい
完了契約の「1科目を通した操作＋別科目との分離」は、製品の一連の動作を
確認する範囲です。これは4科目の研究評価を置き換えません。今回作った4つの
架空ミニ科目も、分野をまたいだ実教材での評価の代わりにはなりません。

まず44件の開発用問題で候補と採点器を検証します。最終確認の前には、許可済み
実教材または利用条件を確認した公開教材に切り替え、問題と出典の対応を
独立に確認する必要があります。人間が確認していないラベルは、そのまま
AI作成・未確認と表示します。

## Scope reconciliation

The [quality plan](quality-and-learning-plan.md) requires roughly four
heterogeneous explicitly permitted courses, cross-course comparisons, and
independent review of at least 20% of quality labels. The
[completion contract](project-completion-contract.md) requires one coherent
multi-document UI journey and a second isolation course. These address distinct
questions: end-to-end product operation versus cross-course quality. Retain both
requirements unless a prospective, explicitly documented scope decision changes
them. Four synthetic mini-courses below test instrument variation only; they do
not fulfill representative four-course evaluation.

## Evidence audit

| Evidence | Useful finding | Quality/quantity limitation and next action |
| --- | --- | --- |
| Fresh factual confirmation 001 | 1,000 cases; 63.25% fully grounded, 96% boundary; negative result preserved | Mechanical question construction and source-family dependence limit interpretation. Do not reuse consumed gold; author natural requirements and check source support independently. |
| Live autonomy 024 / 028 | Actual model and product calls, registered governance checks | 024 has one approved chunk per case; 028 has twelve similar protocol-number sources. Large counts do not imply diverse natural course content or 30-day operation. |
| Longitudinal correction 025 | 72 histories, two learner families, six personas, 30 virtual days | Deterministic model replacement; shared simulator/product semantics. Treat as assessment regression, not independent learning evidence. |
| New seven-day live development | Four histories, 36 real calls and four restarts | Wiring evidence only. Four correlated histories cannot establish the quality, safety prevalence or educational effect of a final composition. |
| Natural question baseline | 12 answerable + four boundary cases, two concrete failures | AI-authored labels, four short source cards; exact span oracle can miss unsupported additional prose and valid paraphrases. |
| Profile development | Actual contrast exposed unchanged 3/6 style-intent score and complete-answer leakage | Intent labels are not delivered-content adherence. Judge full multi-turn content with help-stage-specific rules, not a planner action alone. |
| Local qualification 011 | Restore, rollback, persistence and permission-race evidence | Zero live-provider calls; course-list GET timing is not tutor-response latency; empty dashboard aggregate does not demonstrate useful insight. |

Existing source permissions must be checked per new source version and provider
exposure; old approval does not authorize arbitrary replacements or private
student/forum data. This development packet is wholly synthetic. It contains no
real instructor examples, private course material, student data or provider call.

## New development instrument

- Packet: [cross-course-quality-development-v1.json](../research/05_evaluation/datasets/cross-course-quality-development-v1.json).
- Runner/scorer: [cross_course_quality_development.py](../scripts/cross_course_quality_development.py).
- Adversarial tests: [test_cross_course_quality_development.py](../tests/test_cross_course_quality_development.py).

Four fictional mini-courses cover scheduling, accounting, ecological sampling and
message protocols. Each has two short versioned sources and eleven cases: natural
paraphrase, misconception, partial explanation, multi-source requirement, missing
detail, cross-course request, injection, privacy, Socratic history, explanatory
history, and provider-failure event. Total: 44 cases, including eight staged
multi-turn contexts. These are development fixtures, not completed conversations.
The timeout event is a public perturbation for an adapter to inject; the scorer
does not itself execute a provider or inject a failure.

`public_case` emits the question, history, profile, event and only that course's
sources. Expected actions and source-span requirements remain in the evaluator's
gold object. Neither the candidate nor a learner simulator may receive gold.
Public and gold coexist on disk for development; this is not a sealed held-out
package. Confirmation must use separate files/access boundaries and a frozen
response ledger before opening gold. Candidate-generated requirement lists must
never replace independently authored scoring requirements.

The current oracle validates exact source offsets, text, version and course;
requires all authored answer spans and citations; checks boundary actions and
literal premature solutions. It is intentionally named `mechanical_pass`, not
semantic correctness. It cannot detect arbitrary unsupported extra prose,
paraphrased solution leakage or plausible but unhelpful hints. A test deliberately
shows a fabricated extra sentence surviving the mechanical checks. Such a case
still has `semantic_review=required-not-performed`. This blind spot prevents a
mechanical aggregate from being presented as the 95% fully correct answer gate.

Before quality confirmation, add an independent content review using a frozen
rubric for correctness, relevance, completeness, support and profile adherence.
Review at least 20% of quality labels independently, record reviewer identity/role
and disagreement resolution, and retain the remaining AI-authored status. Review
both successes and failures. An alternative model can give advisory judgments;
it is neither a human reviewer nor proof of real-instructor fidelity. Calibrate
any judge on authored good/bad pairs, including wrong citations, omitted second
sources, unsupported numeric details, generic nonanswers and premature hints.

## Sample size and uncertainty

The contract's 400 answerable, 200 boundary and 200 profile opportunities are
planning quantities, not a guarantee. Under an optimistic independent-binomial
assumption, two-sided 95% Wilson intervals are:

| Observation | Interval | Meaning |
| --- | --- | --- |
| 380/400 answerable (95%) | 92.40–96.74% | Meeting a 95% point gate does not establish a population rate above 95%. |
| 196/200 boundaries (98%) | 94.97–99.22% | Four failures leave substantial uncertainty below the target. |
| 190/200 profile opportunities (95%) | 91.04–97.26% | Correlated turns will generally support still weaker inference. |
| 95/100 course slice | 88.82–97.85% | Aggregate precision cannot be assigned to each course. |

If a lower 95% Wilson bound were adopted prospectively as the acceptance rule,
400 answerable cases require at least 389 successes to exceed 95%; 200 boundaries
require 200/200 to exceed 98%; 200 profile opportunities require 197 successes to
exceed 95%. These are illustrations, **not newly imposed gates**. Keep current
point thresholds and report intervals unless the contract is prospectively
amended. Zero observed violations is not proof of universal safety.

Recommended allocation for the proposed confirmation is four permitted courses,
100 answerable and 50 boundary questions per course, with distinct source families
and question forms. For 400 answerable questions, aim for at least 100 source
families rather than hundreds of rewrites of a few paragraphs. Predeclare family
clusters and report course slices. At four questions per family and an illustrative
intracluster correlation of 0.2, the design effect is 1.6 and effective n is about
250, not 400. The actual correlation is unknown; this is a sensitivity calculation.

For profiles, 50 dialogues with four applicable opportunities yield 200 turns,
but the dialogue is the resampling unit. Allocate settings and courses explicitly;
with only around twelve dialogues per course, per-course conclusions remain weak.
Use paired cluster-bootstrap intervals for candidate-minus-control differences,
clustered by source family or dialogue. Four courses are too few to infer a broad
population of disciplines: report them as fixed evaluated contexts.

For 24 longitudinal histories, reactive/autonomous pairing yields twelve paired
contexts (six personas × two profiles), not 24 independent treatment contrasts.
Use per-pair results and persona/profile slices. If variability across seeds is
important, preregister three seeds (72 histories) after the pilot demonstrates
stable instrumentation; this improves simulation robustness, not real-learning
validity. Do not increase repeats merely to manufacture a narrow interval.

## Next decision and verification

Compare the unchanged incumbent with the separately implemented answerability
and profile candidate on the same public development inputs. Keep retrieval and
sources fixed when evaluating answerability. Record correctness and support
separately from citation validity; report unsuccessful and missing judgments.
The fresh confirmation remains closed until the composition, scorer, permissions,
labels, sample rationale and measurement contract are frozen.

```sh
uv run python -m scripts.cross_course_quality_development
uv run python -m scripts.cross_course_quality_development --public-output /tmp/cross-course-public-development.jsonl
uv run pytest tests/test_cross_course_quality_development.py -q
```

Twelve adversarial/contract tests passed on 2026-09-06. They reject missing
multi-source citations, foreign sources, changed versions, invalid offsets,
fabricated quotes, unsafe boundary actions, literal solution leakage and corrupted
gold. They also disclose rather than hide the semantic oracle blind spot. These
tests validate the instrument contract, not tutor quality. No provider calls or
candidate-quality run has been performed by this audit.

## Actual-product comparison harness

`scripts/run_cross_course_quality_development.py` adds a finite 88-case comparison
(44 public cases × incumbent/candidate) through actual tutoring services. It
installs the packet's sources using a saved deterministic identity mapping and
verifies the installed text/version/checksum/location before tutoring. Approved
Socratic/explanatory profiles are created through the profile lifecycle. For
multi-turn cases it submits the packet's student messages and records actual
tutor replies; authored assistant-history examples are not injected into storage.

The candidate jointly changes admission, asynchronous question-specific generation
and approved profile context. This comparison is not an isolated estimate of any
one component's effect. Separate ablations are required for that causal claim.
Product citations currently establish whole-source paragraph containment, not
claim-specific offsets. The product scorer therefore returns
`claim_specific_span_score=null` and a separate source-containment diagnostic.
It does not manufacture exact quote positions from the gold requirements.

Two additional harness tests pass, including all 88 product cases without external
calls. This is contract evidence only. Provider-timeout cases are counted as
exercised only if the injected transport is reached; deterministic fast paths
cannot be counted as provider failure handling. Live execution requires recorded
authority and is not performed by the audit agent. Default finite limits are
500 total calls and USD 5 through the shared durable ledger, with concurrency two.

```sh
uv run python -m scripts.run_cross_course_quality_development --validate
uv run python -m scripts.run_cross_course_quality_development --contract --output-dir <fresh-output-directory>
uv run pytest tests/test_run_cross_course_quality_development.py -q
```


## Completed live development evidence

The descriptions above document instrument construction before live execution.
Subsequent authorised runs are now registered: [cross-course live 005](../research/05_evaluation/cross-course-quality-development-001-live-005-results.md)
and [full operational trial](../research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md).
The latter comprises 24 histories × 30 virtual days, 654 actual provider calls,
484 tutor turns and 16 proactive messages. Calls and within-history turns are
not independent quality samples; six synthetic personas, one seed and simulated
time do not establish course diversity, real-month uptime or learning outcomes.

The [77-case assistant review](../research/05_evaluation/dialogue-full-live-001-assistant-review.md)
selected every safe failure (13), every proactive message (16), and each history's
first and last non-failure tutor response (48). It is a post-run diagnostic
selection, not a random sample or an overall accuracy estimate. Eleven failures
were incomplete outputs at the 500-token cap; two were correctly rejected
question-focus proposals. Generic repeated rules and limited progression leave
pedagogical quality at Refine. Fourteen of sixteen proactive messages followed
an earlier-day correct same-concept attempt; this raises a targeting question,
but a scripted correct attempt is not proof of lasting mastery.

The [professor development review kit](../research/05_evaluation/professor-review-development-005/README.md)
contains eight masked responses, evidence, blank rating fields and a separate
allocation key. It has not been sent, rated or approved by a professor. Fresh
permitted courses, held-out semantic assessment and independent ratings remain
required before a quality qualification; merely increasing the live-call count
would not close those gaps.
