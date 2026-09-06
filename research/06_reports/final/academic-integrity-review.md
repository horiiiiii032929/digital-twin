# Academic-integrity review

Date: 6 September 2026  
Reviewer: OpenAI Codex (AI-assisted review, not independent academic clearance)  
Status: historical audit plus current-version addendum below; this is not
institutional academic-integrity clearance.

## Findings and repairs

| Finding | Significance | Action |
| --- | --- | --- |
| No declaration of substantial AI assistance | Readers could incorrectly infer that the code, evaluation instruments and prose were produced without AI assistance. | Added a declaration covering implementation, research and evaluation design, synthetic cases, reference answers, analysis, diagrams, English/LaTeX drafting and review. The student confirmed that all development/writing assistance was through Codex. |
| “Assistant review” was ambiguous | AI judgments could be mistaken for independent human or instructor assessment. | Changed the report to “AI review” / “AI-reviewed” and stated the risk of shared errors when AI helps construct instruments and assess outputs. |
| Project framing lacked explicit provenance | The motivation and three pillars came from the approved project brief, not an independently originated research agenda. | Added a footnote identifying the unpublished brief and advisor, without reproducing student identifiers or asserting authorship of the brief. |
| Diagram conventions lacked course attribution | Layering and activity-flow conventions were deliberately informed by IT5004 materials. | Added lecture titles, confirmed lecturer name and relevant PDF pages. The diagrams depict this implementation; this does not establish a novel architecture notation. |
| A published Qwen prompt template lacked explicit report attribution | The reranker prefix/suffix match the official example, so they should not appear to be a novel prompt design. | Added the model-card link and an explicit statement that the template is not a project contribution. No runtime behavior changed. |
| Literature-map status was stale | It still described disconnected/plain-style references and could mislead later verification. | Updated the current bibliography status and the full-text review scope. |

The report already separates project-specific instruments from ALCE, MRBench,
StratL and ScaffoldLM, and does not claim to reproduce or outperform those
systems. It retains failed gates, invalidated source/reference judgments,
stopped trials, missing historical raw artifacts, and the distinction between
virtual students and actual provider calls. These limitations must remain.

## Source and wording checks

The earlier single-file LaTeX draft was checked against full PDF text of the six scholarly
works below. The comparison used lowercase alphanumeric tokens and exact
contiguous eight-word sequences; citation keys, labels, URLs, LaTeX comments and
the bibliography were excluded. There were no matching eight-word sequences in
this bounded screen. This is a local diagnostic, **not a plagiarism score**:
it cannot detect unattributed ideas, translated copying, close structural
paraphrase, unknown sources or text missed by PDF extraction.

| Source | Claim reviewed |
| --- | --- |
| [Lewis et al., RAG](https://proceedings.neurips.cc/paper/2020/file/6b493230205f780e1bc26945df7481e5-Paper.pdf), introduction | Retrieval augments language generation; this project does not claim to implement the original end-to-end trained RAG model. |
| [Gao et al., ALCE](https://aclanthology.org/2023.emnlp-main.398/), introduction | Distinct fluency, correctness and citation-quality assessment. No transfer of their numerical findings or claim of metric equivalence. |
| [Puech et al., StratL](https://aclanthology.org/2025.findings-acl.1348/), sections 3.1–3.2 | Tutoring-intent transitions and pedagogical steering. |
| [Li et al., ScaffoldLM](https://aclanthology.org/2026.acl-long.325/), sections 4.1–4.3 | Stepwise plans and assessment/action/progress/history coordination. |
| [Maurya et al., MRBench](https://aclanthology.org/2025.naacl-long.57/), introduction and Table 1 | Eight pedagogical dimensions; the local rubric is not their benchmark. |
| [Robertson and Zaragoza, BM25](https://doi.org/10.1561/1500000019) | Attribution of the established retrieval method; full-text wording screen. Publication metadata discrepancy is documented in the reference verification note. |

These short related-work paraphrases attribute the underlying ideas locally.
No passage requiring a direct quotation was identified in the inspected report
prose. This finding applies only to the inspected sources and draft.

The original IT5004 title slides confirm “LEK HSIANG HUI” and the lecture titles.
The existing diagram source files and the course-alignment record establish
project-specific content and deliberate use of course conventions. This review
has not certified the reuse rights of every historical figure or assignment.
No course slides were copied into the report during this review.

A bounded source-code search for attribution/reuse notices found the Qwen
reranker prompt match, verified against the [official model card](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B).
This was not a repository-wide code-similarity or license-compliance audit.
Dependency links acknowledge tools; they are not substitutes for any applicable
redistribution notices. No repository license was added or inferred.

## AI-use record

The following is a retrospective, representative record grounded in the
conversation and repository. It is not an exhaustive prompt log. The author
confirmed “全部codexです” on 6 September 2026. Historical Codex model versions
and every intermediate prompt/output have not been reconstructed. Runtime model
identifiers in experiments must not be presented as the identity of the
assistant that wrote the code or report.

| Area | Representative instruction or task | Use of output and retained evidence |
| --- | --- | --- |
| Software | Audit, fix, implement missing capabilities and test | AI-generated and AI-modified application code, tests and technical audit records. This is substantial coding assistance. |
| Research and evaluation | Identify missing evaluations; assess their quantity and quality; run comparisons | AI assistance with plans, synthetic cases, reference answers, rubrics, scripts and result interpretation; records under `research/04_experiments/` and `research/05_evaluation/`. |
| Writing | Write the report in English/LaTeX and make it concise | Generated and revised prose, structure and LaTeX incorporated into `report.tex`; not merely proofreading. |
| Figures | Include system diagrams informed by the instructor's IT5004 course | AI-assisted project diagrams and the course-alignment note. |
| References | Check references and add repository and library links | Bibliography and software attribution; primary-source checks recorded separately. |
| Integrity | Seriously review academic plagiarism and disclose AI use | This note and the declaration; an AI self-review is not independent verification. |

The student supplied the brief and course materials, set priorities, requested
corrections and confirmed the assistance tool. This record does **not** claim
that the student independently wrote, understood or verified every generated
artifact. Before submission, the student must review the declaration and be able
to explain the architecture, key algorithms, experimental design and limitations.
A statement of author responsibility is not evidence that this review is complete.

## Policy and remaining requirements

[NUS Computing's Preventing Plagiarism page](https://www.comp.nus.edu.sg/cug/plagiarism/)
identifies missing source acknowledgement and misrepresentation as integrity
issues and links student AI-use guidance. The [Office of Student Conduct](https://studentconduct.nus.edu.sg/administrative-policies/)
links the University's plagiarism policy. These are authoritative public
starting points, not evidence of permission for this particular MComp project.

The CTLT AI-policy PDF appeared in official search results, but direct retrieval
was unsuccessful or yielded no extractable policy text. The linked library page
was rate-limited. Therefore this review does not claim to have verified the
complete current university policy or an MComp-specific declaration form.
Policies from other departments were not treated as applicable course rules.

The advisor/course rules on substantial AI assistance and any required prompt
log or declaration template remain unknown. A disclosure improves transparency
but cannot make otherwise prohibited assistance permissible. Obtain or inspect
the applicable instructions before treating this draft as submission-ready.

No manuscript was uploaded to Turnitin or another external plagiarism checker.
No detector score or “plagiarism-free” guarantee is provided. An authorised
institutional similarity review, if required, and human review of source use
remain separate from this work.

## Verification artifacts

The preceding manuscript/PDF and the known-source screen output are preserved
locally under `reports/generated/academic-integrity-review-20260906/`.
The screen script is preserved there for inspection; it is a diagnostic, not an
accepted research metric. No new experiment, runtime qualification or learning
outcome is claimed by this editorial review.

The earlier revision reviewed in this section compiled to 15 pages. This is
not the current submission PDF. All pages were visually inspected, with
the disclosure page reviewed at readable scale. Bibliography/citation consistency,
Markdown links, evaluation-record validation and the repository correctness
inventory check passed. Existing diagram PDF-version warnings remain; no
undefined citations or overfull/underfull text boxes were reported. These are
document/record checks, not a fresh execution of the application test suite.

## Declaration wording refinement

The declaration was shortened at the author's request to use neutral, concise
report language. Language/typesetting details and repeated caveats were removed.
Substantial assistance with implementation, evaluation, synthetic materials,
analysis, figures and writing remains disclosed, along with the distinction
between AI review and independent human assessment. The detailed record above
remains available; this wording change does not alter the recorded scope of use.


## Current-version verification after the modular report revision

The old wording-screen script read only `report.tex` and therefore could not
validate the later chapter-based manuscript. It has been corrected to recursively
expand every active LaTeX input, retain file hashes, require all six expected
source texts, and fail on missing inputs. The current run covers the main report
and its included appendices; it excludes the separately compiled trial archive.
The earlier overlap JSON remains a historical artifact, not current clearance.

The current results are in
`reports/generated/academic-integrity-review-20260906/known-source-overlap-current.json`.
This bounded exact-eight-word diagnostic found no matches to the six inspected
source texts. It is not a plagiarism score or a check against all publications,
and does not establish compliance with course-specific AI rules. Human review
and any institutionally required process remain separate.

The related-work sentence now describes what the implementation enforces rather
than implying priority over prior research. IT5004 attribution has been condensed
and moved to the software appendix; the main design explanation uses the cited
C4 and UML conventions. The original project brief, reused Qwen template and
Codex assistance remain explicitly acknowledged. Current PDF page counts and
rebuild results are recorded in `reports/generated/final-report/submission-manifest.json`.

The subsequent layout/status-only revision did not rerun this integrity review.
The wording-screen JSON identifies the exact earlier source snapshot through its
file hashes; it must not be presented as a fresh check of later layout edits.
