# Academic factual-QA confirmation source candidates 001

Verified: 2026-08-25

Status: source checkpoint complete; exact revisions, licenses, sections,
dependent assets, and hashes are bound to confirmation 002

## Purpose

This shortlist became the source layer for
`academic-factual-qa-confirmation-002`. Complete upstream snapshots remain in
ignored `data/external/`; Git contains only exact repository metadata, hashes,
short evidence excerpts, and the derived evaluation artifacts. The four
collections cover distinct computing-course strata and expose text, code,
tables, diagrams, and equations.

| Course stratum | Candidate collection | Primary license evidence | Current assessment |
| --- | --- | --- | --- |
| Operating systems | [Open Education Hub Operating Systems](https://github.com/open-education-hub/operating-systems) at `25cac6d` | `COPYING.md` has a conflicting summary header and embedded notice; the stricter embedded CC BY-NC-SA 4.0 notice is binding | Eligible for noncommercial research only; section and local-media hashes bound |
| Computer networking | [Computer Networking: Principles, Protocols and Practice](https://github.com/cnp3/ebook) at `5d27036` | Repository README and per-file notices state CC BY-SA 3.0 | Eligible open-licensed third-edition source; section hashes bound |
| Data structures | [Open Data Structures](https://github.com/patmorin/ods) at `9d22c44` | `COPYING` applies CC BY 2.5 Canada to `latex/`; third-party test directories are excluded | Eligible `latex/` book content only; section and figure hashes bound |
| Programming | [Think Python, third edition](https://github.com/AllenDowney/ThinkPython) at `19cb35f` | [Official third-edition page](https://greenteapress.com/wp/think-python-3rd-edition/) states CC BY-NC-SA 4.0 for text | Eligible for noncommercial research; authored chapter notebooks only |

## Completed source-manifest checks

- exactly four course strata, 25 confirmation clusters, and 10 calibration
  sections per stratum;
- one immutable URL/repository revision, retrieval date, SHA-256, license URL,
  attribution string, modality inventory, and allowed-use decision per artifact;
- no exercises with answer keys or other assessed-work material used as ordinary
  answerable facts;
- no learner submissions, comments, analytics, account data, or third-party
  embedded material whose license is unresolved;
- selected section character ranges do not overlap and each source family is
  used once across confirmation and calibration; and
- raw downloaded content remains under ignored data storage and never enters
  GitHub.

## Bound artifacts

- `research/05_evaluation/datasets/academic_factual_qa_confirmation_002_source_manifest.json`
- `research/05_evaluation/datasets/academic_factual_qa_confirmation_002_cases.json`
- `research/05_evaluation/datasets/academic_factual_qa_confirmation_002_calibration_controls.json`
- `research/05_evaluation/datasets/academic_factual_qa_confirmation_002_blinded_review_packet.json`

The 200 confirmation cases and 40 controls remain unreviewed. Source binding
establishes reproducible construction, not semantic validity or product quality.
