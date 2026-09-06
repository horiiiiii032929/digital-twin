# Report outline for joint review

Status: proposed structure, not approved report prose. Prepared 2026-09-05.
The canonical English LaTeX manuscript remains [report.tex](report.tex).
Japanese notes below support discussion and are not manuscript content.

## Academic writing standard

Hikaru requested graduate-level academic report language after reviewing the
compiled draft. All manuscript prose, captions, and figure labels are English;
Japanese remains the language for explanation and collaborative discussion.

- Use formal, neutral, precise prose appropriate for a Master's-level Computer
  Science capstone. Preserve the agreed third-person academic voice.
- Define technical terms and explain mechanisms and design trade-offs. Formality
  should not introduce unnecessary jargon, ornate vocabulary, or long sentences.
- Distinguish objectives, implemented mechanisms, measured results, and
  interpretation. Qualify conclusions by dataset, condition, and evaluation scope.
- Support literature claims with checked primary sources and project results
  with registered evidence. Do not imply novelty, causality, fidelity, or
  general effectiveness beyond the evidence.
- Avoid conversational expressions, promotional language, unsupported superlatives,
  and development-diary narration. Each paragraph should advance a clear point
  with its explanation or evidence.
- Introduce and interpret figures and tables in the text; do not leave them as
  illustrations without an analytical purpose.

Hikaru's positive feedback on the rendered PDF confirms the presentation
direction; it does not automatically approve every provisional claim or section.

## Framing and source of the objective

Official allocated project title, as supplied by Hikaru from the project portal:
**Architecting an Digital Twin for Scalable, Style-Aligned Instructor Presence**.
Retain the official title unless a different submission title is agreed.
Do not reproduce portal account identifiers, contact information, or CV links.

The supplied description has three pillars: identity and knowledge ingestion,
pedagogical alignment, and a student interface with an instructor dashboard.
Hikaru's stated emphasis is whether professor-configured knowledge, policies,
and constraints can support a continuously operating autonomous agent without
per-response professor approval. This is the design objective, not a claim that
every intended capability was successfully demonstrated.

日本語：中心は「教授の設定を継続的な自律指導として実行できるか」。
教授への忠実性、回答の正確さ、学習効果は、それぞれ別に評価する。
正式概要の “infinitely” や “exact teaching style” は実証済みの性能として扱わない。

## Proposed research questions

1. **RQ1 — Architecture:** How can instructor-provided knowledge, pedagogical
   policies, and constraints be translated into an autonomous tutoring runtime
   while preserving instructor authority?
2. **RQ2 — Autonomous operation:** Under controlled synthetic learner scenarios,
   how do reactive and autonomous tutoring differ in policy-valid behaviour,
   state handling, proactive intervention, and continuity over time?
3. **RQ3 — Grounding and limits:** How well does the integrated system ground
   its answers, and what evidence limits claims of style-aligned, useful, and
   scalable instructor presence?

日本語：RQ1は「どう設計したか」、RQ2は「継続的に何ができたか」、
RQ3は「回答品質と教授の目標に対して、何がまだ足りないか」。
RQ2 does not permit a cross-condition uplift estimate from unmatched cases;
compare only matched slices and the explicitly paired histories in 025.

## Research question, design, evidence, and answer

This is the argument spine for drafting, not the final conclusion. Section 3
introduces the mechanisms, Section 4 defines their tests, Section 5 presents
outcomes, and Section 6 returns explicitly to these questions.

| Question | Design to explain | Evaluation evidence | Bounded answer to develop |
| --- | --- | --- | --- |
| RQ1: translate professor settings into autonomous operation | Approved sources and versioned policy; publication boundary; proposal versus authorization; durable state and delivery | Implementation trace, authority-race regressions, and local qualification 011 | The architecture implements enforceable professor controls and local continuity; configurability does not demonstrate imitation of a real instructor. |
| RQ2: reactive versus autonomous behaviour | Observation, learner state, goals, bounded action selection, scheduled execution, consent and stopping conditions | 024's condition/slice results and 025's 36 paired 30-day histories | Registered action/assessment/operational gates passed, while predictive and intervention utility remain limited; synthetic outcomes do not establish human learning. |
| RQ3: grounding and limits of instructor presence | Shared retrieval and evidence gate; claim/citation boundary; teaching-profile and visual alternatives | Fresh five-arm factual comparison and its correction; professor-proxy and visual results; local operations as a separate capability | The selected fallback reached 63.25% fully grounded answers and failed its quality gate. Style fidelity, representative learning and hosted scale remain unproven. |

## First bounded drafting unit

**English subsection:** System Objectives and Scope (opening of Section 3).

**Purpose:** Translate the allocated project's three pillars into concrete
system responsibilities and define what autonomous operation means here.

The three points to establish, subject to Hikaru's confirmation:

1. The instructor supplies and approves course evidence, pedagogical settings,
   and operating constraints; publication defines the student's usable version.
2. Student-facing operation includes both responding to questions and initiating
   permitted check-ins, without requiring instructor approval of every response.
3. The application retains authority over access, source scope, state changes,
   and delivery; similarity to a real instructor and learning benefit require
   separate evidence.

Use the user-supplied official brief for motivation, the actual publication,
student and autonomy services plus repository transaction boundary for mechanism,
and qualification 011 for the local operating scope. No external numerical or
effectiveness claim is needed in this opening subsection. Literature comparisons
belong in the following design rationale and Related Work after passage checks.

日本語での説明例：教授が「承認済み教材を使い、すぐ正解を渡さず、必要なら
問い返す」と設定する。その後の通常の対話や許可されたチェックインをシステムが
進める。ただし設定の効果や教授への類似性が常に保証されるという意味ではない。
この例は説明用であり、特定の実教授の発言や実験ケースとして引用しない。

Draft only this subsection after confirming its meaning, then review it with
Hikaru before adding the architecture figure and detailed runtime explanation.

Progress: Hikaru approved the three points on 2026-09-05. The English
`System Objectives and Scope` subsection has been added to `report.tex` and is
awaiting prose review; it is not yet provisionally accepted. The existing
introduction and section numbering remain unchanged pending later revision.
Source/claim and whitespace checks passed. Tectonic 0.17.0 was subsequently
installed at Hikaru's request. The current manuscript compiled successfully to
`reports/generated/final-report/report.pdf` with no compiler warnings or
overfull/underfull box reports. All three pages were visually inspected;
the new subsection is legible and unclipped. Empty section headings and the
provisional introduction remain expected draft content, not accepted final prose.

## English structure and Japanese reading guide

Target allocation: approximately 13–15 pages of main text including figures, provisionally excluding references
and title material. Whether these count toward the 10–15-page limit still
requires the formal submission guidance. Abstract: approximately 150–200 words,
written last. Page allocations are limits for planning, not content quotas.

| Section | Pages | Intended argument and content | 日本語での役割 |
| --- | ---: | --- | --- |
| **1. Introduction** | 1.0 | Instructor time is limited; course knowledge and teaching policy motivate the three-pillar Digital Twin. State the autonomy objective, RQs, and bounded contributions. | 教授の正式な課題から出発し、何を目指したか説明する。 |
| **2. Background and Related Work** | 1.0 | Position course-grounded RAG, pedagogical alignment, tutoring agents, and reactive versus proactive interaction. Define Digital Twin operationally; do not assert biological or exact personal replication. | 用語と既存研究を説明し、このプロジェクトの位置を示す。 |
| **3. Requirements, Architecture and Implementation** | 4.0–5.0 | Map the three pillars to actual components. Explain the question-to-answer path, autonomous loop, professor controls, learner state, dashboard aggregation, and authority checks through course-aligned diagrams. Discuss selected alternatives and trade-offs. | 教授の設定が、どの処理を通って自律行動になるかを図で追う。 |
| **4. Evaluation Methodology** | 2.0 | Define controls, datasets, metrics, hard gates, frozen-run rules, provider versus deterministic execution, and evidence retention. Separate autonomy, learner simulation, factual grounding, and local operations. | 「何を成功としたか」を結果より先に定義する。 |
| **5. Results** | 2.5 | Present autonomy 024, paired learner simulation 025, fresh five-arm factual comparison, and local qualification 011. Include compact visual and professor-proxy negative results where they answer RQ3. | 成功・失敗・未検証を混ぜず、問いごとに結果を示す。 |
| **6. Discussion, Limitations and Future Work** | 2.0 | Answer RQs: autonomous execution does not guarantee useful intervention, retrieval coverage does not guarantee grounding, and configurable pedagogy does not prove instructor fidelity. Discuss synthetic realism, evaluator dependence, missing raw artifacts, and deployment limits. | なぜこの結果になり、どこまで主張できるか考える。 |
| **7. Conclusion** | 0.5 | Restate the implemented contribution and evidence-supported answers to the RQs; preserve the unresolved quality and real-world limits. | 目標に対して達成した範囲を短く答える。 |

Section 3's internal order: requirements and actors; instructor configuration
and publication; ingestion/retrieval/grounding; reactive and proactive runtime;
instructor feedback and operational recovery. Explain representative mechanisms,
not every module or the complete development chronology.

## Evidence anchors and permitted claims

| Report topic | Exact evidence | How to use it |
| --- | --- | --- |
| Enforced professor settings and runtime boundaries | Actual services and domain code; final profile; [runtime audit](../../../docs/research/2026-09-05-runtime-correctness-audit.md) | Trace implemented behaviour and explain alternatives. Do not treat the existence of a setting as measured fidelity. |
| Model-backed autonomous behaviour | [Confirmation 024](../../05_evaluation/governed-full-autonomy-v2-1-persona-confirmation-024-results.md) and its [record](../../05_evaluation/records/governed-full-autonomy-v2-1-persona-confirmation-024.json) | 670 total cases: 150 T0, 150 reactive T1-v2, 370 autonomous T1-v2. Registered hard gates passed. Preferred-action agreement is a separate diagnostic, not 100% best-action selection. |
| Time-dependent learner simulation | [Confirmation 025](../../05_evaluation/governed-full-autonomy-v2-1-multi-concept-confirmation-025-results.md) and its [record](../../05_evaluation/records/governed-full-autonomy-v2-1-multi-concept-confirmation-025.json) | Six personas × two simulator families × three seeds × two conditions = 72 histories / 36 pairs. Thirty virtual days, restart on day 15, zero provider calls. Assessment gates passed; AUROC 0.466 and wasted interventions 32.9% remain limitations. |
| Factual answer grounding | [Fresh factual comparison](../../05_evaluation/final-cross-method-factual-confirmation-001-results.md) and [analysis correction](../../05_evaluation/final-cross-method-factual-confirmation-001-analysis-correction-001-results.md) | Five-arm shared-case comparison; selected fallback reached 506/800 fully grounded answers (63.25%). Preserve Refine, denominators, uncertainty, and corrected citation reporting. |
| Local operations | [Qualification 011](../../05_evaluation/local-r1-governed-v2-1-release-qualification-011-results.md) | 43/43 operations checks and 51/51 focused built-image regressions; deterministic fast paths. Not another model-backed autonomy or learning study. |
| Professor alignment and visual scope | [Claim–evidence matrix](final-claim-evidence-matrix.md) and its linked records | Explain the professor-proxy failure and rejected visual candidate; no completed valid professor-fidelity uplift estimate. |

Confirmation 024's raw artifacts were not found locally in the evidence audit;
its claims rely on committed results and hashes. Do not imply a new per-case
review. Historical experiments used their recorded source revisions; the full
provider evaluation was not rerun against qualification 011's corrected source.
Do not rerun, rescore, or tune on consumed factual datasets.

## Figures, literature, and writing workflow

Hikaru identified the reader as the instructor teaching IT5004 and requested
more diagrams based on that course. Use the course's notation to explain this
system, not as evidence that the capstone requires the unrelated Easy POS
assignment's deliverables or grading rules. The lecture material and assignment
examples are reference sources, not instructions to implement another system.

Use the following six main-text figures, each answering a different question.
These are planned contents, not newly completed figures.

| Placement | English figure title / notation | Question and evidence boundary |
| --- | --- | --- |
| Section 3 | **Logical Architecture of the Course Digital Twin** — multi-tier architecture | Where do presentation, business logic, data access, stores, and model adapters belong? Reuse and verify the existing Draw.io architecture; distinguish logical layers from physical nodes. |
| Section 3 | **Core Design Classes and Relationships** — compact UML design class diagram | How do policies, published releases, conversations, learner state, goals, services, and repositories relate? Add selected attributes/operations and code-verified multiplicities; do not draw every class or invent Handler classes to mimic the assignment. |
| Section 3 | **Governed Autonomous Tutoring Activity** — UML swimlane activity diagram | What is observed, proposed, authorized, delivered, persisted, deferred, or stopped, and by whom? The existing one-student-turn activity is supporting material; add the event-driven loop rather than relabelling a reactive flow as autonomous. |
| Section 3 | **Execution of a Scheduled Tutor Check-in** — UML sequence diagram | How do worker, policy/planner, repositories, and delivery collaborate over time? Show actual commit-time checks and no-delivery branches. Clarify that a model call is conditional, not required for every turn. |
| Section 4 | **Closed-Loop Synthetic Learner Evaluation** — explicitly labelled experimental data-flow diagram | How do simulator, product runtime, virtual clock, observations, hidden truth, and scorer interact? Verify the actual adapter boundary; this is an evaluation figure, not a claim of a real-student study or independent evaluator. |
| Section 5 | **Factual Grounding Across the Five Evaluated Configurations** — quantitative comparison | What differs on the shared fresh cases? Use exact denominators and valid uncertainty; do not rank results from unrelated datasets on one axis. |

Keep four supporting figures in the appendix: actor-organized UML use cases,
the existing professor-publication sequence, the detailed student-turn activity,
and the implemented local Docker deployment (including shared storage and
process boundaries). A use-case description and policy decision table accompany
them where referenced. AWS deployment proposals remain optional future-work
material and must not appear as the implemented topology.

図を読む順序は「構造 → 主要なデータと責務 → 判断の流れ → 実行時の連携 →
シミュレーション → 数値結果」。本文6点＋付録4点を目安とし、文字が小さく
なる場合は付録へ移す。図の枚数ではなく、各図で説明できる設計判断を重視する。

Use English labels/captions and editable Draw.io sources with vector PDF
exports for LaTeX. Verify notation and rendered legibility at final page width.
Every caption states the question, relevant implementation or experiment, and
any abstraction. Reuse existing assets only after checking their September 2
content against qualification 011's runtime; old polished drawings are not
automatically current. Keep 024, 025, and 011 on separate result rows and do not
combine them into a universal success rate. The existing
[IT5004 alignment review](it5004-system-design-alignment.md) provides notation
guidance; this outline updates the figure priority for the latest autonomy focus.

The [literature-to-report map](literature-to-report-map.md) now connects existing
research notes to Sections 2, 3, 4, and 6. It tracks primary-source candidates,
verification status, and claim boundaries; [references.bib](references.bib)
contains an initial three official ACL entries. Relevant full-text passages
still require verification before drafting claims. The bibliography is not yet
connected to the manuscript, and the required citation style remains unknown.

Drafting order: Section 3 → Section 4 → Section 5 → Section 6 → Section 2 →
revise Section 1 → Section 7 → Abstract. Before each drafting unit, explain its
mechanism in Japanese, propose two or three English points and exact evidence,
and confirm meaning with Hikaru. Then write only that unit in English LaTeX,
check claims, compile, and inspect the PDF when a compiler is available.
Hikaru owns motivation, interpretation, reflections, and final conclusions.

The existing introduction and four RQs are provisional and precede the latest
discussion. Revise them only after this outline's emphasis is accepted. Merge
the currently separate methodology/evaluation sections and discussion/limitations
sections at that time to avoid duplication; retain existing labels or update
cross-references consistently. Do not claim blanket autonomous No Release when
the actual boundary is local operational Keep with factual-quality Refine.

Submission items still unknown: required citation style and template, whether
references count toward the page limit, and title-page requirements. These do
not prevent agreeing on the argument or drafting bounded technical sections.
