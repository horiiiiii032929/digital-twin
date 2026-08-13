# Digital Twin Delivery

Status date: 2026-08-14

This Project tracks the evidence-first delivery of a professor-configurable
pedagogical Digital Twin for multiple professors and courses. The product
combines professor teaching behaviour, approved course evidence, tutoring
policy, student interaction state, and evaluation-before-publication.

## Current position

- Professor-approved chat-led onboarding and policy configuration exist.
- Local parsing, chunking, BM25, dense/hybrid retrieval candidates, generation
  controls, evaluation instruments, component profiles, and result governance
  exist.
- IT5002 is useful pilot evidence, not the final corpus or method selection.
- The one-time rapid sealed run is invalid and retired; it is not rerun.
- Jina is an unselected implementation spike with no evaluation result.
- The four-course benchmark is frozen and the one-time held-out comparison is
  complete; M2 hybrid RRF is selected for the experimental profile and BM25 is
  the rollback. M1 regressed on quality and latency; M3 exceeded the latency
  ceiling despite higher retrieval quality.
- The scoped multimodal development study is complete: V3 was dropped, V0 is
  retained as rollback, and no multimodal profile is selected.
- Bounded synthetic M2 activation now includes course-isolated student turns,
  persisted conversations, citation lineage, BM25/provider fallback, and
  restart recovery. Evaluation-gated draft publication, atomic replacement,
  withdrawal, rollback, and stale-conversation denial pass the registered
  19-check v2 architecture slice.
- The exact DeepSeek V4 Flash/P2 generator boundary is qualified and selected
  with a deterministic rollback. Professor-fidelity C0-C3 development is
  preserved only as an operational trace and is invalid for selection. The
  correction records missing human authoring review, case-gold leakage, a
  drifted C3 chunking corpus, missing condition/policy bindings, 13/30
  source/page citation correctness, and 0/30 exact selected-passage matches.
  Safe grounding, citation completeness, and pedagogy remain unresolved;
  held-out remains unopened.
  Credentialed identity, complete professor/source
  administration, migration, backup/restore, concurrency, and bounded capacity
  evidence are also incomplete.

The sole `In Progress` item is #24. The immediate R2 work is the frozen local
three-model authoring review of all exact-passage v1.2.3 cases followed by a
stable 16-case independent-human audit, all 19 no-evidence cases, and model
escalations, capped at 48 human cases. The initial 32-sample instrument attempt
is preserved as invalid; v2 corrects local thinking-mode transport and adds
public preflights. The immutable seal also requires confirmation on GitHub
Support ticket #4659958 before the corrected hash-bound development comparison
can run. Held-out tutor outputs remain unopened.
#8 returns to `Todo` with its 19-check synthetic publication foundation
preserved; credentialed identity and complete professor/source lifecycles
resume after the current gate. #25, #10, #9, and #12 remain queued. Do not
reopen the text benchmark for visual claims or continue multimodal V3 tuning.

## Final product

The final local, hosting-ready product supports:

- invite-only administrator, professor, and student roles;
- independently configurable multi-course Digital Twins;
- governed ingestion of approved course sources;
- professor teaching-behaviour and tutoring-policy configuration;
- preview and evaluation gates before professor publication;
- course-isolated, persistent student tutoring with inspectable citations;
- publication withdrawal, source update, and rollback;
- visible quality, failure, latency, and cost evidence; and
- provider failure, recovery, portability, and bounded capacity tests.

The planning envelope is approximately 10 professors, 20 courses, 500
documents, and 100 concurrent student sessions. This is a simulated capacity
target, not an adoption or service-level claim. Public hosting and real-user
recruitment are not required.

## Research programme

1. Cross-course retrieval: compare M0 heading-aware BM25, M1 dense, M2 hybrid,
   and M3 hybrid plus reranking on about 100 verified cases across roughly four
   heterogeneous courses.
2. Professor fidelity and pedagogy: hold generator/evidence constant while
   comparing a generic assistant, grounded generic tutor, and
   professor-configured Digital Twin.
3. End-to-end validity: test professor and student journeys, publication gates,
   persistence, isolation, provider failure, recovery, and bounded capacity.

Hardware latency and cost are operational outcomes. They do not determine
retrieval quality. A provider or method earns selection only through
project-specific evidence.

## Critical path

| Date | Required outcome |
| --- | --- |
| 2026-07-27 to 2026-07-29 | Scope, GitHub roadmap, and repository architecture lock |
| 2026-07-30 to 2026-08-02 | Course portfolio, ingestion QA, benchmark freeze, provider qualification, multimodal development decision, and sealed text retrieval decision |
| 2026-08-03 to 2026-08-08 | Register the retrieval decision, activate M2 behind the BM25 rollback, and freeze the R2/R3 execution plans |
| 2026-08-09 to 2026-08-12 | Complete the minimum professor/student core journeys and regression evidence |
| 2026-08-13 to 2026-08-15 | Fidelity, pedagogy, isolation, recovery, capacity, and packaging evidence |
| 2026-08-16 | Absolute technical and evidence freeze |
| 2026-08-17 to 2026-08-31 | Analysis, figures, report foundation, demo stabilization, and appointment preparation |
| 2026-09-01 to 2026-09-03 | Report and presentation draft |
| 2026-09-04 | Target professor presentation |
| 2026-09-05 to 2026-09-09 | Evidence-backed revision |
| 2026-09-10 to 2026-09-12 | Contingency and packaging only |
| 2026-09-13 | Final submission |

## Evaluation contract

Every replaceable method and architecture boundary must define its decision,
prediction, control, candidates, dataset, metrics, hard gates, failure cases,
operational measures, and rollback before implementation or sealed inspection.
Every named result remains registered, including failed, invalid,
inconclusive, and no-selection outcomes.

Safety, permission, privacy, academic integrity, provenance, isolation, and
sealed-data rules are hard gates. Profiles change only after evidence passes
their prospective gates. No paper, leaderboard, vendor statement, or successful
demo is sufficient by itself.

## Operating rules

- Keep only the current bounded execution issue `In Progress`.
- Use daily reviewable changes as a throughput goal; do not manufacture
  experiments that do not answer a decision.
- Report to the professor every Monday, Wednesday, and Friday only when there
  is decision-bearing evidence: a short message, exact numbers, one table or at
  most two charts, one limitation, and the next decision date.
- Do not commit private course material, student data, credentials, or bulky
  per-case outputs.
- Do not use solution files, answer keys, or student submissions.
- Do not claim human usability, adoption, engagement, or learning outcomes.
- After 2026-08-16, make only changes needed to preserve frozen claims,
  reproducibility, or the demonstration.

The durable baseline is
`research/00_admin/2026-07-27-frontier-digital-twin-scope.md`.
