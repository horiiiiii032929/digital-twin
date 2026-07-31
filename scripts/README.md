# Scripts

Use this folder for repeatable project utilities such as ingestion, evaluation,
data validation, or project automation scripts.

Current utilities:

- `validate_markdown_links.py`: checks local links in repository Markdown files;
  run it with `npm run check:docs`.
- `verify_local_ingestion.py`: parses and chunks five approved synthetic TXT,
  Markdown, and PDF sources twice, then reports stable identifiers, provenance,
  and figure counts; run it with `npm run verify:ingestion`.
- `evaluate_retrieval.py`: compares deterministic term-overlap and BM25 ranking
  over the versioned synthetic retrieval set, emits per-question evidence plus
  aggregate Recall@1, Recall@5, MRR, no-evidence accuracy, latency, and memory,
  and enforces regression thresholds; run it with `npm run verify:retrieval`.
- `evaluate_generation.py`: runs the deterministic generator, policy, citation,
  and no-evidence preflight over 25 synthetic cases without a provider, tokens,
  or cost; run it with `npm run verify:generation`. An explicit `--model` plus
  optional `--json-mode` runs a benchmark-only live candidate; the repository's
  local zero-cost command is `npm run benchmark:generation-local`. A non-Ollama
  model is rejected unless `--allow-external-provider` explicitly acknowledges
  the potentially billable external call; such a run also requires the
  separately recorded budget decision defined by issue #24.
- `benchmark_retrieval.py`: calibrates and compares BM25, local BGE-small dense
  retrieval, and BM25+dense RRF on the harder synthetic v2 corpus, emitting
  held-out metrics, category slices, hard gates, latency, memory, and model
  cache evidence; run it with `npm run benchmark:retrieval`. This optional
  command downloads model files only to ignored `data/external/` storage.
- `benchmark_evidence_sufficiency.py`: calibrates absolute-score and lexical-
  coverage gates against the explicit any-hit control, then evaluates the
  frozen choices on a separate held-out set; run calibration without touching
  held-out results using `npm run calibrate:evidence-sufficiency`, and run the
  recorded comparison with `npm run benchmark:evidence-sufficiency`.
- `synthetic_course_corpus.py`: shares the approved synthetic source, PDF, and
  chunk builders used by ingestion and retrieval verification.
- `validate_component_profile.py`: validates the complete component inventory,
  selection status, evidence paths, and linked evaluation decisions; run it
  with `npm run verify:profile`.
- `validate_cross_course_portfolio.py`: validates the active four-course,
  32-document v2 portfolio plus the superseded v1 snapshot, aggregate counts,
  selectable-text requirement, and duplicate hashes. Pass
  `--source-root /Users/hikaru/Documents/academia_vault` for optional canonical
  source/hash verification; the source files remain outside Git. It runs
  without private sources in CI through
  `npm run verify:cross-course-portfolio`.
- `audit_cross_course_ingestion.py`: compares document-wide and page-bounded
  heading/paragraph chunking over the private active portfolio without writing
  course text to the result artifact. Run `npm run
  audit:cross-course-ingestion`; set `ACADEMIA_VAULT_ROOT` when the canonical
  vault is not at `~/Documents/academia_vault`. The sanitized output is written
  to `reports/generated/cross-course-ingestion-v1.json`.
- `draft_cross_course_benchmark.py`: uses local `gemma3:4b` only to draft
  answerable and cross-course-confusion wording against page-local chunks,
  combines it with explicit boundary cases, and writes the private 100-case
  draft plus researcher checklist under ignored `data/processed/`; run
  `npm run draft:cross-course-benchmark`.
- `draft_cross_course_benchmark_v2.py`: constructs the QC-amended private
  draft separately from draft 1, with prose filtering, balanced direct and
  paraphrase cases, ten two-chunk cases, unused confusion targets, exact source
  quote recovery, and course-adjacent no-evidence cases. It is an authoring
  utility, not an approval mechanism.
- `validate_cross_course_benchmark.py`: validates the public synthetic schema
  in CI through `npm run verify:cross-course-benchmark`. Run it against the
  private draft without `--synthetic` to check allocation, manifest hashes,
  page-local chunk identities, exact quotes, visual sufficiency flags, and
  review gates.
- `validate_multimodal_retrieval_dataset.py`: validates the public visual
  retrieval fixture, source hashes, normalized evidence regions, permissions,
  positive/boundary semantics, and required modality and safety slices without
  reading private sources or calling a model; run it with `npm run
  verify:multimodal-retrieval-instruments`.
- `inventory_multimodal_sources.py`: creates a private hash-bound per-file
  inventory under ignored storage and a sanitized aggregate without filenames
  or content; it classifies generated and secret-indicated exclusions,
  assessment-like review items, clear course candidates, formats, and possible
  modalities. Run it with `npm run inventory:multimodal-sources`.
- `sample_multimodal_pdf_pages.py`: analyzes eligible and previously approved
  PDF pages, selects a balanced high-visual-score review sample across detected
  courses, renders each selected page with Poppler, and creates private contact
  sheets and a review queue. Run it with `npm run
  sample:multimodal-pdf-pages`; its visual score is a sampling aid, not an
  eligibility or modality decision.
- `build_multimodal_private_draft.py`: combines the private page sample and
  ignored authoring specification into a strict 40-case draft with source/page/
  render hashes, provisional evidence regions, a Markdown checklist, and a
  private local HTML review page that exports decisions without uploading
  content. Run it with `npm run draft:multimodal-private-benchmark`. The output
  remains unsealed and cannot run until every case is researcher-verified.
- `record_cross_course_reviews.py`: records explicit accept or reject decisions
  for one or more private benchmark case IDs, retains reviewer and timestamp
  provenance, and regenerates the ignored researcher checklist.
- `apply_cross_course_qc_patch.py`: applies a hash-bound private QC patch to the
  next draft version, resolves replacement evidence from the approved local
  corpus, resets every changed review, records predecessor lineage, and
  regenerates the private checklist.
- `run_cross_course_retrieval_pilot.py`: runs the local-only, course-scoped
  BM25, Qwen3 dense, reciprocal-rank-fusion, and Qwen3 reranking ladder on the
  historical draft-5 development cases without loading heldout-draft cases. It
  is retained to reproduce the registered pilot, not used for qualification.
- `run_cross_course_retrieval_qualification.py`: verifies the private seal and
  unopened ledger, loads only the 40-case development file, constructs the
  shared course-scoped M0-M3 ladder, and records normalized quality,
  isolation, latency, provider usage, cost, and failure evidence for one frozen
  local or hosted provider pair. Run `npm run
  qualify:retrieval-provider-local` for the local control or set
  `JINA_API_KEY` and run `npm run qualify:retrieval-provider-jina` for the
  hosted candidate. Neither command may read the held-out file.
- `analyze_cross_course_retrieval_pilot.py`: validates and sanitizes the
  private development result, computes seeded paired uncertainty and sign
  tests, and exports a professor-ready CSV plus PNG/SVG comparison chart.
- `second_review_cross_course_benchmark.py`: selects a frozen 20-case,
  four-course positive-label sample and obtains blinded structured semantic
  review from a different local Ollama model without exposing retrieval output
  or original review decisions.
- `apply_cross_course_second_review.py`: validates the private second-review
  result and explicit adjudication, preserves the original disagreement, marks
  the 20-case sample, and advances a fully researcher-verified draft to
  `approved`.
- `seal_cross_course_benchmark.py`: revalidates the approved private benchmark,
  writes immutable-hash development and held-out files without overwriting,
  and creates an unopened one-time held-out access ledger. It does not run or
  configure retrieval candidates.
- `validate_evaluation_results.py`: requires every durable `*-results.md`
  summary and machine-readable component record to appear in the result
  registry, validates record schemas and unique run IDs, and runs as part of
  `npm run check`; run it directly with `npm run verify:evaluation-results`.
- `validate_evaluation_instruments.py`: validates the frozen LLM-judge,
  simulated-student, run-record, and analysis contracts plus public synthetic
  examples, semantic cross-file invariants, and the freeze-manifest hashes; run
  it with `npm run verify:evaluation-instruments`.
- `validate_retrieval_v3_instruments.py`: validates the frozen IT5002
  retrieval-v3 candidate set, the disjoint 59-case rapid checkpoint, primary
  metrics, NotebookLM black-box boundary, held-out locks, and public open-set
  example; run it with
  `npm run verify:retrieval-v3-instruments`.
