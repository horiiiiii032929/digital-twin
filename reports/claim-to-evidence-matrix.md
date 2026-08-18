# Claim-to-evidence matrix

Status: frozen on 2026-08-18 for the experimental `student-tutor-v1`
technical baseline. A supported claim is intentionally narrow; anything absent
or marked unsupported must not appear as a project result in the report,
presentation, or demonstration.

## Supported and narrowed claims

| Claim ID | Frozen claim | Evidence | Exact boundary | Status |
| --- | --- | --- | --- | --- |
| `C01` | Approved local TXT, Markdown, and selectable-text PDF sources can be parsed with stable provenance and permission checks in the tested local pipeline. | `ingestion-v1-clean`; `cross-course-ingestion-v1` | Five synthetic sources plus the approved four-course selectable-text audit; no OCR/layout-completeness claim | Supported, bounded |
| `C02` | Page-bounded heading/paragraph chunking removed cross-page chunks while preserving deterministic identity and provenance on the audited corpus. | `cross-course-ingestion-v1` | 0/1,322 candidate chunks crossed a page versus 591/598 control chunks | Supported |
| `C03` | M2 hybrid BM25 plus frozen local Qwen3 dense RRF outperformed BM25 on complete-evidence@3 in the one-time 60-case cross-course comparison and passed its operational gates. | `cross-course-retrieval-v1-heldout-001` | 85.0% versus 80.0% complete-evidence@3; four approved courses; 164 ms warm p95; zero isolation/provider/retry failures | Supported, experimental |
| `C04` | The selected M2 retrieval stack has an explicit BM25 rollback and rejects unreviewed dependency replacement. | `cross-course-retrieval-v1-heldout-001`; `dependency-compatibility-python-ml-001` | The tested major ML upgrade changed two of 40 development top-three rankings and was dropped | Supported |
| `C05` | DeepSeek V4 Flash non-thinking with strict-evidence P2 passed the frozen public-synthetic generator qualification used for the experimental profile. | `generator-qualification-v1-heldout-001` | 104/104 one-time held-out attempts plus 20/20 Codex second-review sample; not independent human review or private-course fidelity evidence | Supported, bounded |
| `C06` | The local synthetic publication/student foundation fails closed on tested authorization, release, citation, fallback, persistence, withdrawal, and rollback scenarios. | `student-workflow-slice-v2-publication-synthetic` | 19/19 deterministic synthetic checks; no human user, network provider, concurrent load, or production identity | Supported, bounded |
| `C07` | The professor-fidelity evaluator is not eligible for automated selection and the evaluation remains paused. | `professor-fidelity-v2-anchor-002-machine-review-summary-001-analysis-correction-001` | 33/48 repeat labels agreed across two repeated cases; swapped and Qwen sensitivity attempts invalid; human reference 0/48 | Supported negative result |
| `C08` | The professor review demo renders, starts an onboarding session through the same-origin local API, advances after a suggested answer, and remains explicitly draft-only. | Technical-freeze browser smoke plus frontend/API tests | Local development demonstration only; no usability or release-readiness inference | Demonstration verified, not a research claim |

## Unsupported or rejected claims

| Claim ID | Claim that must not be made | Evidence state | Frozen disposition |
| --- | --- | --- | --- |
| `U01` | Professor policy measurably improves tutoring behavior or matches a professor. | Historical comparison invalid; anchor evaluator ineligible; no completed independent-human reference | Unsupported; `Refine / Paused` |
| `U02` | The system is grounded and citation-complete end to end on representative private-course questions. | Structural/synthetic component evidence exists, but corrected professor-fidelity development and held-out evidence do not | Unsupported |
| `U03` | The system provides reliable multimodal retrieval over figures, tables, diagrams, scans, or equations. | V2 failed the relative development gate; V3 regressed and was dropped; no profile selected | Unsupported; text-only rollback |
| `U04` | The application is production-ready, publicly deployable, or operationally controlled. | No credentialed identity, health/monitoring package, migration, backup/restore, deletion, or operator recovery qualification | Unsupported |
| `U05` | The system supports a bounded concurrent capacity or service-level target. | No concurrent capacity run exists | Unsupported |
| `U06` | The system improves learning, usability, adoption, satisfaction, engagement, or professor approval. | No participant or learning-outcome study and no completed professor approval exercise | Unsupported |
| `U07` | The current dependency stack is vulnerability-free. | npm has zero findings; the optional local ML environment has nine exact temporary reviewed advisories | Rejected wording; say zero **unreviewed** findings and local-only exceptions reviewed by 2026-09-15 |

## Use rules

- Cite the stable result ID and dataset boundary beside every accepted numeric
  statement.
- Preserve failed, invalid, inconclusive, and no-selection results; do not
  rewrite them as successful evidence.
- Generate numeric figures only from machine-readable or frozen source
  artifacts.
- State profile, model/prompt revision, sample size, operational context,
  reviewer boundary, and important limitation with each result.
- Do not generalize a benchmark-specific, synthetic, anchor-only, local, or
  demonstration result into a SOTA, production, human-usability, or
  learning-improvement claim.
- Any post-freeze change to a selected component, claim, result interpretation,
  security exception, or demo-critical route requires a new versioned freeze
  and full regression checks.
