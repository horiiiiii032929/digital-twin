# Literature-to-report map

Status: citation candidates and writing plan, not manuscript prose.
Prepared 2026-09-05. This map uses existing research notes as discovery material;
it does not treat them as primary publications or evidence of current runtime behaviour.

## How literature enters the report

日本語：文献はRelated Workに並べるだけでなく、「課題 → 先行研究の考え方 →
本プロジェクトの設計・比較 → 実験結果 → 限界」をつなぐために使う。
文献で有効だった方法を、本システムでも有効だったとは書かない。

- Section 2: explain the research landscape and the project's bounded position.
- Section 3: justify specific design choices and distinguish alternatives from
  selected implementations. Establish influence from dated project records;
  otherwise describe a retrospective comparison, not an original motivation.
- Section 4: justify separate grounding, tutoring, intervention, and operational
  measures. Do not claim to reproduce an external benchmark without doing so.
- Section 6: interpret negative results and distinguish simulated proxies from
  instructor fidelity, human usability, and measured learning outcomes.

## Existing research material

| Local source | Main report use |
| --- | --- |
| [Pedagogical profile foundations](../../01_literature/pedagogical-profile-foundations.md) | Teaching philosophy, feedback, scaffolding, and why an explicit profile is more than tone imitation |
| [RAG tutoring evaluation](../../01_literature/2026-07-15-rag-tutoring-evaluation-practices.md) and [evaluation review](../../01_literature/2026-07-22-sota-rag-tutor-evaluation.md) | Separate retrieval, evidence sufficiency, claim support, citation completeness, and pedagogy |
| [Retrieval alternatives](../../01_literature/2026-07-23-modern-course-rag-retrieval.md) | Historical alternatives and the rationale for comparing methods on the same corpus |
| [Proactive tutoring](../../01_literature/2026-08-27-proactive-mixed-initiative-tutoring.md) | Assistance timing, mixed initiative, attention cost, and intervention utility |
| [Autonomous loop review](../../01_literature/2026-08-31-autonomous-tutoring-loop-and-evaluation.md) and [architecture audit](../../01_literature/2026-08-31-autonomous-tutor-best-practice-audit.md) | Domain, learner, pedagogy, interaction, and governance responsibilities; bounded loops and evaluation |
| [Independent architecture study](../../../docs/research/sota-autonomous-digital-twin-independent-study.md), [evaluation design](../../../docs/research/sota-autonomous-digital-twin-evaluation-design.md), and [decision](../../../docs/research/sota-autonomous-digital-twin-decision.md) | Competing architectures and project decision history; verify which proposals were selected before describing the final system |
| [Local runtime review](../../01_literature/2026-08-19-local-llm-runtime-options.md) | Supporting operational history only; old model/pricing guidance is not current evidence |

## Prioritized primary-source candidates

“Page checked” means that the official landing page, metadata and abstract were
checked in this pass; it does not mean a complete paper or its numerical claims
have been independently reviewed. “Pending” means discovered in a local note
and awaiting primary-source verification. The list is a shortlist, not a citation quota.

| Topic and candidate | Section / purpose | Status and boundary |
| --- | --- | --- |
| [Pedagogical Steering / StratL](https://aclanthology.org/2025.findings-acl.1348/) | 2, 3: explicit multi-turn pedagogical strategy rather than a general assistant instruction | Page checked; official BibTeX captured. Related design, not proof that our implementation reproduces StratL or matches a professor. |
| [Planning-Guided Tutoring with Assessment-Driven Memory](https://aclanthology.org/2026.acl-long.325/) | 2, 3: planning and assessment-driven memory | Page checked; official BibTeX captured. Author metadata differs from local shorthand; use Li et al., not the notes' Wang et al. Verify full text before using the ScaffoldLM name or attributing detailed mechanisms. |
| [MRBench / Unifying AI Tutor Evaluation](https://aclanthology.org/2025.naacl-long.57/) | 2, 4: pedagogical evaluation beyond answer correctness | Page checked; official BibTeX captured. Its mathematical-dialogue benchmark is not our dataset; adapted criteria must be labelled as adaptations. |
| [ReAct](https://arxiv.org/abs/2210.03629) | 2, 3: reasoning/action interaction as an architectural comparison | Page checked; final venue/version and bibliography pending. Do not describe the bounded product as an unrestricted ReAct implementation. |
| [ALCE: Enabling Large Language Models to Generate Text with Citations](https://arxiv.org/abs/2305.14627) | 2, 4, 6: citation-supported generation and evaluation | Page checked; final EMNLP record and bibliography pending. Our factual scorer is a project-specific instrument, not automatically the ALCE metric. |
| [AutoTutor](https://doi.org/10.1109/TE.2005.856149) | 2: prior mixed-initiative intelligent tutoring | Pending primary-source verification |
| [Knowledge Tracing](https://doi.org/10.1007/BF01099821) | 2, 4, 6: learner-model context and simulator assumptions | Pending. BKT-like simulation or candidate comparison does not imply that the selected runtime uses BKT. |
| [Principles of Mixed-Initiative User Interfaces](https://doi.org/10.1145/302979.303030) | 2, 3, 6: when autonomous assistance should occur | Pending. Relate to interruption/initiative trade-offs, not a claim of implemented optimal timing. |
| [HelpNeed / Assistance Dilemma](https://jedm.educationaldatamining.org/index.php/JEDM/article/view/450) | 2, 6: helpful versus unnecessary intervention | Pending. Useful comparison for 025's wasted-intervention diagnostic, with task and metric differences explicit. |
| [Qwen3 Embedding](https://arxiv.org/abs/2506.05176) | 3, 4: embedding candidate used in factual-method comparison | Pending. Vendor benchmarks do not establish our selected winner. |
| [RAGChecker](https://arxiv.org/abs/2408.08067) | 4, 6: component-level versus integrated grounding diagnostics | Pending. Use only if it adds a distinct point beyond ALCE. |
| [tau-bench](https://openreview.net/pdf?id=roNSXZpUDN) | 4: stateful tool/policy evaluation | Pending. Establish conceptual relation, not benchmark equivalence or a new score. |
| [Shulman: Knowledge Growth in Teaching](https://doi.org/10.3102/0013189X015002004) | 1, 2: instructor-specific pedagogical knowledge | Pending. Select only if the brief's teaching-identity discussion needs this foundation. |
| [Generative AI without guardrails can harm learning](https://doi.org/10.1073/pnas.2422633122) | 6: performance with assistance versus independent learning | Pending; the local study notes mention a correction. Inspect the correction before using any number. |

## Bibliography and verification workflow

[references.bib](references.bib) is connected to `report.tex` using
`natbib`/`unsrtnat`. The initial three-entry shortlist has been expanded; see
the [reference verification note](reference-verification.md) for current metadata checks.

For each section, choose only the sources supporting its approved points. Read
the relevant primary-paper passages; check authors, year, venue/version, DOI,
corrections, evaluation conditions, and limitations. Then record the precise
claim and supporting section/page here before adding `\cite{...}` to the LaTeX.
Do not present an abstract check as full-text verification.

Use academic papers for research claims, official technical documentation for
implementation facts, IT5004 material for diagram conventions, and registered
repository results for this project's measured outcomes. These source types
are complementary, not interchangeable. Avoid duplicating preprint and final
publication entries. Do not copy paper figures without checking attribution
and reuse terms; prefer original system diagrams and mark genuine adaptations.

Do not inherit “state of the art” from historical note filenames. No new method,
model, or provider run is authorized or required by this literature map.

## Passages used in the September 6 draft

- Puech et al. (2025), sections 3.1–3.2, pp. 26294 onward: transition-based
  intent selection and pedagogical steering. Official full PDF inspected;
  no numerical study result is transferred to this project.
- Li et al. (2026), sections 4.1–4.3, pp. 7168–7169: stepwise planning and
  assessment/action/tracking/recording. Official PDF inspected.
- Maurya et al. (2025), p. 1234 Table 1 and introduction: eight dimensions
  including disclosure, guidance and actionability. Official PDF downloaded
  and text inspected because the web PDF reader failed.
- Bibliography now uses numeric `natbib`/`unsrtnat` citations. Detailed benchmark
  numbers and unverified remaining shortlist papers are not added.

- Lewis et al. RAG (2020), official arXiv abstract: parametric generation with
  retrieved non-parametric memory. Only this high-level claim is cited.
- Gao et al. ALCE (2023), official ACL abstract and publication metadata:
  fluency/correctness/citation-quality dimensions. No external numerical
  findings or metric implementation equivalence are claimed.

## Academic-integrity pass (6 September 2026)

Full PDFs of all six cited research works (including BM25) were retrieved for
a known-source wording screen. Relevant RAG introduction and ALCE introduction
passages were also checked beyond the earlier abstract-only pass. See the
[academic-integrity review](academic-integrity-review.md) for scope, attribution
repairs and unresolved submission requirements.
