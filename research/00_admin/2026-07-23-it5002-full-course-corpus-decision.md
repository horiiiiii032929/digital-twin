# IT5002 full-course corpus decision

Date: 2026-07-23

Status: researcher-selected local evaluation corpus; external-provider use is
prohibited and real student-facing release permission remains separate

## Decision

Use all 13 official IT5002 lecture PDFs as the candidate authoritative corpus
for the course-tutor pilot. Replace the earlier five-document feasibility
subset as the final course scope. Retain the subset only as historical local
preparation evidence.

This is a corpus-selection and local-inventory decision. It does not authorize
DeepSeek calls, a human deployment, or a held-out evaluation.

## Why the full lecture set

- A student-facing course tutor should not silently cover only one module while
  being described as an IT5002 tutor.
- Thirteen lectures remain small enough for local indexing and manual source
  inventory while covering the actual hardware-to-operating-system course arc.
- Full-course coverage produces realistic cross-topic, ambiguity, no-evidence,
  and multi-evidence cases.
- The larger corpus makes retrieval and context-sufficiency tests more
  discriminating than the five-document subset.
- Evaluation can still use topic strata and case subsets without deleting
  approved knowledge from the product corpus.

## Local evidence

The ignored snapshot at `data/raw/course_materials/it5002_full/lecture/`
contains:

- 13 PDFs;
- 508 pages;
- 15,738,973 bytes;
- 175,474 characters extracted by `pdftotext` for the inventory check;
- selectable text in every PDF; and
- zero SHA-256 mismatches against the academic-vault sources.

The committed sanitized inventory is
[`it5002_lectures_v1.manifest.json`](../05_evaluation/it5002_lectures_v1.manifest.json).

## Source roles

| Source class | Initial role | Rationale |
| --- | --- | --- |
| Official lecture PDFs 1-13 | Authoritative local-evaluation retrieval and gold evidence | Complete official course sequence with stable pages and hashes |
| Personal Markdown notes | Question wording and misconception discovery only | Useful student perspective, but sampled notes contain labeling and factual errors |
| Tutorials | Excluded initially | May contain answer material and requires a separate permission/integrity decision |
| Assignments, quizzes, exams, solutions, and answer files | Prohibited from retrieval | High academic-integrity risk |
| Project repositories, `.env`, personal records, and unrelated vault content | Prohibited | Secrets, privacy, scope, and provenance risk |

Do not display instructor email addresses from slide boilerplate in tutor
citations. A student-facing citation needs only course, lecture title/number,
page, and approved source version.

## Topic strata

1. Foundations and number representation: lectures 1-2.
2. MIPS instruction-set architecture: lectures 3-5.
3. Datapath and control: lectures 6-8.
4. Memory hierarchy and caches: lecture 9.
5. Operating systems, processes, and IPC: lectures 10-13.

The 12 professor-anchor cases must touch every stratum. Development and held-
out sets report both scenario and topic slices; topic frequency need not be
uniform, but the allocation is frozen before case authoring.

## Evaluation implications

- The gold-case unit and 12/48/104 split sizes do not change.
- Corpus answerability now refers to all 13 lectures, not the earlier subset.
- A no-evidence case must be outside the full approved lecture corpus, not just
  outside one module.
- Full-context C4 remains conditional. Measure the exact corpus token count
  with the frozen generator tokenizer before declaring it eligible.
- Diagram-dependent cases receive an explicit tag so parser limitations are not
  confused with retrieval or generation failures.
- Notes may inspire paraphrases and misconceptions but may not supply required
  claims or gold evidence.

## Remaining gates

1. Freeze the exact local evaluation instruments and source hierarchy under
   issue #11.
2. Keep all course-specific tutor, simulator, and judge processing local;
   external-provider use remains prohibited.
3. Freeze the researcher-authored 12-case anchor before development or held-out
   authoring; record any later professor review as optional expert calibration.
4. Obtain explicit professor or institutional authorization before real
   student-facing release. Local research evaluation does not imply that
   authorization.
