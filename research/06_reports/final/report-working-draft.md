# Course Digital Twin: an evaluation-first approach to governed, evidence-grounded tutoring

Status: working draft 0.2 for discussion, not a complete report  
Started: 2026-09-02  
Current checkpoint: agreed format, framing, and LaTeX opening only

<!--
This file is intentionally incomplete. Do not fill the remaining sections in one
pass. Review the thesis, questions, voice, and report requirements with Hikaru
before drafting the next section.
-->

## How we will write this together

This report will be built in reviewable sections rather than generated from
beginning to end in one pass.

Hikaru owns the argument, personal understanding, final interpretation, and
decisions about what the project means. In particular, Hikaru should supply or
approve the project motivation, the intended academic audience, the learning
and design reflections, the explanation of important trade-offs, and the final
conclusions.

The assistant supports the work by locating evidence in the repository,
proposing structures, drafting bounded passages from approved points, checking
claims against registered results, maintaining terminology and citation
consistency, and identifying gaps or overclaims. The assistant should not
invent personal reflection, silently decide the project's contribution, or
turn a provisional interpretation into a conclusion.

For each section:

1. Agree on the section's job and the two or three points it must make.
2. Collect the exact repository evidence and any required academic sources.
3. Draft one section or subsection.
4. Have Hikaru correct the meaning, emphasis, and voice.
5. Revise and mark the section provisionally accepted before moving on.

The abstract, final title, discussion, and conclusion should be written late,
after the evidence-bearing sections are stable.

## Agreed report constraints

- **Format:** LaTeX. The canonical report source begins in `report.tex`.
- **Length:** approximately 10--15 pages. Whether references and appendices
  count toward this limit still needs confirmation.
- **Reader assumption:** a university supervisor or examiner with general
  computing and AI knowledge but no prior knowledge of this repository. This is
  the purpose of the earlier “main reader” question; it determines how much
  terminology and project context the report must explain.
- **Voice:** neutral academic prose rather than first person singular or plural.
- **Results stance:** compare favorable, unfavorable, corrected, invalid, and
  no-release outcomes. Component-level or local success must not be presented as
  evidence that the autonomous LLM-backed product passed its release gates.

Still to confirm are the required citation style and the formal title-page
details (author name, module or programme, institution, supervisor, and
submission date).

## Working argument

The Course Digital Twin should be evaluated as a governed tutoring system, not
only as a chatbot or retrieval model. The project shows that course isolation,
professor authority, source provenance, deterministic fallback, state
persistence, and rollback can be implemented and verified in a local release
candidate. The evaluation also exposes a material contrast: deterministic and
component-level controls can pass while an integrated LLM-backed candidate
still fails factual grounding, academic-integrity, or exact claim-to-citation
gates. The report will compare those outcomes and explain why the evidence
supports retaining safe local controls while withholding autonomous LLM-backed
release. The contribution is therefore both an inspectable system architecture
and empirical evidence about where autonomous course tutoring still fails.

This is a provisional argument. It should not be treated as the final abstract
or conclusion until Hikaru approves the emphasis.

## Provisional research questions

1. How can a professor-configurable Course Digital Twin turn source permission,
   teaching policy, academic-integrity rules, and publication authority into
   enforceable product controls?
2. Which retrieval and evidence-representation approaches best support
   course-isolated, fully grounded factual answers under predefined quality and
   operational gates?
3. Can a governed tutoring runtime preserve safe actions, citation lineage,
   learner-state authority, persistence, recovery, and rollback across reactive
   and proactive tutoring flows?
4. Which remaining failures prevent an autonomous LLM-backed tutor from being
   selected for release, despite successful local workflow and operational
   verification?

## Provisional report map and page budget

The page allocations are planning ranges, not content quotas. They target a
roughly 12--14 page main body so that figures and unavoidable expansion do not
force the report beyond 15 pages.

| Section | Approx. pages | Purpose | State |
| --- | ---: | --- | --- |
| 1. Introduction | 1.0 | Establish the problem, objective, questions, and contribution | Opening draft in LaTeX |
| 2. Related work and research gap | 1.0--1.5 | Position RAG tutoring, intelligent tutoring systems, pedagogical agents, and governed autonomy | Not drafted |
| 3. Evaluation-first methodology | 1.0--1.5 | Explain controls, frozen data, gates, failure taxonomy, and decision rules | Not drafted |
| 4. System design and implementation | 2.0--2.5 | Describe professor governance, grounding, tutoring state, publication, and the main implementation boundaries | Not drafted |
| 5. Evaluation design | 1.0--1.5 | Define the datasets, conditions, metrics, operational checks, and claim boundaries | Not drafted |
| 6. Comparative results | 2.5--3.0 | Compare Keep, Refine, invalid, corrected, and No Release outcomes across grounding, autonomy, and operations | Not drafted |
| 7. Discussion | 1.0--1.5 | Explain why control-level success and high retrieval coverage did not guarantee release-quality claims and citations | Not drafted |
| 8. Security, limitations, and future work | 1.0--1.5 | State evaluated safeguards and separate them from unresolved multimodal, human, hosting, and learning-outcome evidence | Not drafted |
| 9. Conclusion | 0.5 | Answer the research questions without broadening the claims | Write last |

The suggested “professor and student pilot usability” section from the folder
guidance is not currently included as a result section because the repository
states that real-professor fidelity, real-student usability, and learning
improvement have not been established. If a completed and authorized human
study exists outside the repository, it should be reviewed before changing
that boundary.

---

## Draft report text

### 1. Problem and motivation

Large language models make it possible to generate explanations, examples, and
questions on demand, but a course tutor has obligations that a general-purpose
assistant does not. It must answer from the correct course and source version,
respect the instructor's permissions and teaching policy, avoid completing
prohibited assessed work, preserve the separation between students and
courses, and fail safely when the available evidence is incomplete. A fluent
answer is therefore insufficient. The system must make the authority for each
action and the evidence for each factual claim inspectable.

This project investigates a Course Digital Twin: a professor-configurable
tutoring system grounded in approved course material and constrained by an
explicit pedagogical and academic-integrity policy. A professor can govern the
sources and behaviour of a course-specific tutor, evaluate it before
publication, and retain the ability to withdraw or roll back a release.
Students interact only with an assigned published release and receive either a
grounded tutoring response or an explicit safe action such as clarification,
refusal, abstention, or operational fallback.

The central engineering difficulty is that these requirements cross several
system boundaries. Parsing and retrieval must retain source identity and
permission. Generation must convert retrieved evidence into claims whose
citations point to the exact supporting source range. Tutoring logic must adapt
to a learner without allowing a model to own identity, policy, delivery, cost,
or learner-state authority. Publication, persistence, recovery, and rollback
must preserve the same constraints when the system restarts or a provider
fails. Evaluating only the quality of an isolated model would miss failures at
these boundaries.

The project therefore follows an evaluation-first method. Baselines and
candidate methods are compared on versioned datasets with predefined metrics,
hard safety gates, operational measurements, and explicit Keep, Refine, Go
Deeper, or Drop decisions. Favorable results are retained alongside invalid and
unfavorable runs. This approach makes a no-release decision a valid research
outcome when a candidate fails the required standard, rather than treating a
convincing demonstration as sufficient evidence of readiness.

<!-- The canonical prose now lives in report.tex. The earlier prose in this
Markdown file is retained as working history until the LaTeX introduction is
accepted. -->
