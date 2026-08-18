# Scripts

Use this folder for repeatable project utilities such as ingestion, evaluation,
data validation, or project automation scripts.

Current utilities:

- `evaluate_ml_dependency_compatibility.py` and
  `compare_ml_dependency_compatibility.py`: run and compare a three-trial,
  development-only selected-M2 compatibility check before and after ML-library
  upgrades. They require exact top-three rankings across all 40 cases, no
  quality or isolation regression, no held-out/external access, and at most a
  20% median p95 latency increase.
- `audit_python_dependencies.py`: exports every locked core, development, and
  optional dependency to a temporary pinned requirements file and runs
  `pip-audit` without installing heavy optional ML packages. Use `npm run
  audit:dependencies` for the Python and npm security gates used by CI.
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
  optional `--json-mode` runs a benchmark-only live candidate. Gemma is retired;
  its historical alias requires `npm run
  historical:benchmark:generation-gemma3 --
  --confirm-historical-reproduction`. A non-Ollama model is rejected unless
  `--allow-external-provider` explicitly acknowledges
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
  remains unsealed and cannot run until every case is researcher-verified. The
  page includes the confirmed second-review fixes, pre-adjudicated taxonomy,
  per-case checks, progress counters, and a local confirmation export. Rebuilds
  retain a prior verified review only when all evidence-bearing case fields are
  unchanged; changed cases return to pending and completed cards are hidden by
  default in the generated page.
- `apply_multimodal_researcher_review.py`: validates a complete local review
  export, applies accepted/rejected/revise dispositions to the ignored private
  draft, and leaves revised or rejected cases unverified. Run it with
  `npm run apply:multimodal-private-review -- --review /path/to/export.json`.
- `seal_multimodal_benchmark.py`: creates a deterministic 16-case development
  and 24-case held-out freeze from the fully verified private draft, keeps every
  rendered page and all of its cases in one split, maximizes course and modality
  coverage, writes hash-bound sealed partitions, and creates a pristine
  one-time held-out ledger without running a model. Run it once with `npm run
  seal:multimodal-private-benchmark`; existing seal files are never overwritten.
  Reusable split rules and the development-only loader live in
  `src/digital_twin/evaluation/multimodal_benchmark.py`. The loader verifies the
  seal and pristine ledger but deliberately never reads the held-out file.
- `apple_vision_ocr.swift` and `build_multimodal_development_artifacts.py`:
  build the sealed-development V0-V2 retrieval representations locally. V1
  adds Apple Vision OCR blocks; V2 adds reading-order/layout records and local
  `gemma3:4b` descriptions marked as non-authoritative, unreviewed ranking
  metadata. The builder verifies the seal through the development-only loader,
  records model and platform provenance, makes no external or paid call, and
  does not read the held-out file. Run it with `npm run
  build:multimodal-development-artifacts`.
- `run_multimodal_retrieval_development.py`: verifies the multimodal seal and
  pristine ledger, loads only the 16-case development partition, compares V0,
  V1, and V2 with course-isolated BM25 indexes and common page/region/action
  metrics, and writes private per-case evidence without touching held-out. Run
  it with `npm run benchmark:multimodal-development`.
- `build_multimodal_visual_embeddings.py` and
  `run_multimodal_retrieval_v3_development.py`: implement the conditional V3
  comparison after V2's documented development quality failure. The builder
  uses frozen, locally cached OpenCLIP ViT-B/32 weights to precompute page and
  contextual region vectors without external calls. The runner keeps held-out
  closed, encodes queries on CPU, fuses V2 lexical and visual region ranks with
  fixed RRF, and evaluates only the failed table/scanned-page slices plus all
  fixed controls. Run `npm run build:multimodal-visual-embeddings` followed by
  `npm run benchmark:multimodal-v3-development`.
- `second_review_multimodal_benchmark.py`: sends blinded, eligible rendered
  pages and case fields to an explicitly approved Claude model in asset-level
  batches, records a private per-case second review plus provider usage, and
  leaves all researcher-verification fields unchanged. Run it with `npm run
  review:multimodal-private-claude` only after the source holder accepts the
  documented Claude consumer-account data boundary.
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
- `run_cross_course_retrieval_heldout.py`: runs the frozen one-time 60-case
  text comparison after explicit confirmation. It marks the unopened ledger
  before reading held-out data, writes a checkpoint after each case, records
  sanitized per-case rankings without query text, and makes any started
  attempt non-rerunnable. Run `npm run benchmark:retrieval-heldout` only after
  the plan and frozen instrument have been reviewed.
- `analyze_cross_course_retrieval_heldout.py`: validates the completed one-time
  result, computes seeded bootstrap intervals and paired comparisons, applies
  the frozen BM25 quality floor and latency rule, and writes the sanitized
  report, machine record, CSV, and chart. Run it with
  `npm run analyze:retrieval-heldout`.
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
- External-provider commands load repository-local secrets from `.env` without
  overriding variables already exported by the shell. Copy `.env.example` to
  `.env`, set `DEEPSEEK_API_KEY` locally, and never commit or share that file.
- `run_professor_fidelity_experiment.py`: validates the frozen R2 conditions,
  exact qualified generator/prompt binding, private split hashes, and sanitized
  preflight without opening held-out outputs; run `npm run
  verify:professor-fidelity-plan`.
- `run_generator_qualification.py` also accepts the prospective
  `generator-qualification-v2-v4-pro-development-001` instrument. That
  development-only boundary uses current GA DeepSeek V4 Pro in non-thinking
  JSON mode with unchanged strict-evidence P2, the v6-established fingerprint,
  conservative current pricing, no retry, and no held-out authorization; run
  its preflight with `npm run verify:generator-qualification-v4-pro` and its
  bounded candidate run with
  `npm run benchmark:generator-qualification-v4-pro-development`.
- `review_generator_qualification_v2.py`: validates and executes the frozen
  all-48-case local Qwen cross-model review of the V4 Pro public-synthetic
  development output. It hides generator identity and deterministic labels,
  requires the exact `qwen3:4b` digest, prohibits Gemma and non-loopback
  endpoints, and must reject five fixed defect probes before reading candidate
  cases. It rejects the invalid v1 template reason and escalates every
  deterministic failure, Qwen revision, or uncertainty. Run `npm run
  verify:generator-qualification-v4-pro-review` before `npm run
  review:generator-qualification-v4-pro`.
- `analyze_generator_qualification_v2.py`: performs the frozen no-model action
  analysis correction over the exact V4 Pro development output. It recognizes
  explicit “which meaning/which one/do you mean?” questions only in ambiguity
  cases, preserves every other hard check, verifies that exactly one action
  changes, and never overwrites the original result. Run `npm run
  analyze:generator-qualification-v4-pro-action-correction`.
- `ClarificationFirstGroundedPromptBuilder` is exposed to the qualification
  runner as P3. Its prospective V4 Pro instrument changes only ambiguity
  behavior and keeps held-out closed. Run `npm run
  verify:generator-qualification-v4-pro-p3` before `npm run
  benchmark:generator-qualification-v4-pro-p3-development`.
- `judge_generator_qualification_v3.py`: runs a bounded same-family semantic
  review of the exact P3 output with current DeepSeek V4 Pro high thinking. It
  must pass five public defect probes before candidate case 1, requires the
  exact fingerprint, has no retries, and records cost/usage per case. It does
  not claim cross-family independence. Run `npm run
  verify:generator-qualification-v4-pro-p3-review` before `npm run
  review:generator-qualification-v4-pro-p3-deepseek`.
- `validate_professor_fidelity_post_audit.py`: validates the tracked paused
  execution policy, non-executing development/held-out preflights, historical
  and deferred command namespaces, DeepSeek V4 Pro/Qwen roles, Gemma exclusion,
  correction record, plan, and purge closure. It checks only private-artifact
  presence, never content, and makes no model call; run `npm run
  verify:professor-fidelity-post-audit`.
- `build_course_tutor_splits.py`: deterministically builds and validates an
  ignored 48-case development plus 104-case held-out **review draft** from
  a private ignored authoring blueprint and a curated case inventory. Every
  positive question, atomic claim, and approved lecture page is explicitly
  re-authored rather than trusted from the invalid rapid instrument. The
  builder rejects exact approved-passage or authored-family overlap across
  development and held-out, validates superseded-version conflicts, preserves
  exact heading/paragraph chunk IDs and content hashes, labels the draft
  honestly, refuses to overwrite prior artifacts, and creates neither a seal
  nor a held-out ledger; run `npm run build:course-tutor-splits`.
- `run_course_tutor_hybrid_review.py`: runs the prospectively frozen v6
  DeepSeek V4 Pro/Qwen/Qwen-derivative ensemble over all 152 authoring cases;
  Gemma is excluded. It binds the external reviewer to the official
  `DeepSeek-V4-Pro-0813` model and its preflight fingerprint, enables `high`
  thinking through the official OpenAI-compatible client, requires strict
  JSON with an 8,192-token allowance, records finish-reason, reasoning-token,
  cost, and latency traces, and stress-tests ten public probes. The split check
  explicitly maps the frozen `development`/`heldout` labels to the `dev`/`test`
  family tokens. It allows one retry only for empty, output-limited, or
  malformed content or a transient timeout/connection failure, and enforces
  314-request and USD 2 limits. It selects a stable
  16-case scenario-by-split human sample before reading verdicts, assigns all
  19 no-evidence cases to human review, and requires both DeepSeek-family and
  local-Qwen-family approval outside the human set. It renders a private human
  packet with all selection classes and model decisions hidden, and stops
  instead of assigning more than 48 cases to the human reviewer; run `npm run
  review:course-tutor-authoring-hybrid` from a clean committed revision after
  confirming the bounded authorization in the v6 plan. If all 456 checkpointed
  decisions completed but deterministic finalization failed, repair and commit
  the finalizer, then pass `--finalize-existing-checkpoint`; this mode requires
  the exact complete frozen reviewer/case set, makes no model call, preserves
  the execution revision, and records the separate finalizer revision.
- `seal_course_tutor_splits.py`: validates all 456 cross-provider model
  records, exact frozen sampling and escalation, the completed blinded
  independent-human audit, two-family model approval outside the human set,
  and explicit GitHub purge confirmation. It then writes a new immutable
  sealed directory and unopened held-out ledger with exclusive-create
  semantics; run `npm run
  seal:course-tutor-splits -- --ensemble-review <ignored-ensemble.json>
  --human-audit <ignored-audit.json> --github-purge-confirmed` only after both
  gates are complete.
- `prepare_course_tutor_authoring_review.py`: renders private development and
  held-out all-case packets plus a hash-bound template for the superseded
  manual protocol. It remains for historical reproduction and is not accepted
  by the current sealer.
- `cross_review_course_tutor_authoring.py`: validates the corrected private
  draft, records a clearly labeled Codex advisory review, preserves the
  rejected and superseded draft findings, and emits a reduced packet for
  no-evidence absence and multi-evidence necessity judgments. This is the
  preserved historical advisory, not evidence for the hybrid seal.
- `seal_course_tutor_anchor.py`: produces the ignored 12-case reviewed anchor
  and review ledger after exact passage and policy inspection; the ledger
  explicitly records Codex-assisted researcher review and keeps professor and
  independent-human review false; run `npm run seal:course-tutor-anchor`.
- `execute_professor_fidelity.py`: enforces
  `professor_fidelity_execution_policy_v1.json` before opening a split. The
  current active commands are `npm run preflight:professor-fidelity-development`
  and `npm run preflight:professor-fidelity-heldout`; both fail closed without
  reading sealed content. Historical anchor reproduction additionally requires
  `--confirm-historical-reproduction`. A future authorized run still requires
  the selected chunker, exact passage hashes, condition and policy/prompt
  hashes, a clean tree, checkpoints, cost stops, and one-time held-out ledger.
- `professor_fidelity_scoring.py`: separates citation-ID validity,
  source-and-locator correctness, claim-level citation coverage, eligible-case
  retrieval completeness, structural success, and unresolved semantic review.
  Exact-phrase matching is retained only as a non-selection diagnostic.
- `judge_professor_fidelity.py`: runs blinded structured pedagogy judgments
  against the frozen JSON contracts. The active primary binding is the
  official `deepseek-v4-pro` model (`DeepSeek-V4-Pro-0813`) in JSON mode with
  `high` thinking, the v6-observed fingerprint, per-run call and cost stops,
  and complete token/reasoning/cost telemetry. Local `qwen3:4b` is retained as
  a bounded sensitivity reviewer; Gemma is excluded from active
  professor-fidelity commands. CLI judging also reads the execution policy
  before a development or held-out run, while anchor judging requires explicit
  historical confirmation. The runner records one preference per
  pedagogical dimension, a SHA-256 binding for every canonical judge input,
  seeded repeat samples, and a separately invoked swapped-order sensitivity
  sample.
- `analyze_judge_calibration.py`: checks judge repeat, position, and
  cross-family/reference agreement; requires every artifact to match the exact
  run, model, digest, and contract; and fails eligibility when the frozen
  blinded researcher reference, any per-dimension gate, or pairwise position
  gate is absent. Pedagogy-versus-hidden-hard-gate disagreement remains a
  cross-layer diagnostic and is not graded as an evaluator failure.
- `prepare_professor_fidelity_blinded_review.py` and
  `finalize_professor_fidelity_blinded_review.py`: create an ignored private
  condition-blinded packet/template, keep the condition mapping separate during
  review, bind finalization to the exact dataset, and require every authored
  pedagogy dimension before a completed review may resolve semantic, citation,
  evidence-sufficiency, or pedagogical metrics. Prepare the
  historical anchor packet only with `npm run
  historical:prepare:professor-fidelity-anchor-review --
  --confirm-historical-reproduction`. The existing unfilled packet is deferred.
- `analyze_professor_fidelity.py`: ignores embedded scores and prospectively
  rescores a hash-matched development run from retrieved source metadata. It
  uses eligible denominators, computes citation and completion gates, audits
  dataset/candidate bindings, and leaves semantics unresolved without eligible
  review. Its status and `heldout_eligible` field are dynamic; only an all-gates
  `Keep` result can be referenced by a later held-out policy authorization. The
  CLI remains deferred while development is paused.
- `correct_professor_fidelity_anchor_machine_review.py`: recomputes the
  anchor-002 aggregate interpretation without provider calls, calculates
  repeat metrics from source labels, separates citation-applicable
  denominators, and records the correction under a new result identity. Run it
  with `npm run correct:professor-fidelity-anchor-machine`.
- `build_generator_qualification_dataset.py`: deterministically builds the
  public synthetic 48-case development and 104-case sealed held-out generator
  qualification splits plus their hash-bound freeze manifest.
- `run_generator_qualification.py`: validates the exact DeepSeek V4 Flash
  non-thinking binding, two frozen prompt conditions, synthetic-only data
  boundary, split hashes, and cost gates. The default command is network-free;
  `npm run benchmark:generator-qualification-development` requires the
  environment-owned `DEEPSEEK_API_KEY` and writes ignored per-case output.
- `run_generator_qualification_stability.py`: runs the frozen P2-only 12-case
  development subset three times, requires the prior provider fingerprint, and
  writes an ignored 36-attempt ledger without reading held-out. Run it with
  `npm run benchmark:generator-qualification-development-stability`.
- `render_generator_qualification_second_review.py`: renders the frozen
  20-case held-out answer sample after the one-time run. Run it with
  `npm run prepare:generator-qualification-second-review`; the local packet is
  ignored until the researcher completes review.
- `verify_student_workflow_slice.py`: runs the network-free synthetic R3
  acceptance journey against temporary SQLite repositories. It verifies
  assigned-course access, selected-M2 retrieval, BM25 provider fallback,
  restart persistence, citations, duplicate requests, withdrawal, isolation,
  revoked accounts, malformed generation, and redacted audit telemetry. Run
  it with `npm run verify:student-workflow`.
