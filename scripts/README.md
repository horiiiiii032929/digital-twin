# Scripts

Use this folder for repeatable project utilities such as ingestion, evaluation,
data validation, or project automation scripts.

Current utilities:

- `validate_submitted_report_links.py`: preserves submitted PDF and source archive
  hashes, internal PDF destinations, 14 cited repository files and the 12-study
  evidence index. Run `npm run check:report-links`; this is included in `npm run check`.

- `run_stateful_clarification_confirmation.py`: validates and executes the
  frozen, network-free 200-case R1.2 mixed-initiative clarification
  confirmation. It drives the actual student service and SQLite persistence,
  checks restart and idempotency, and never reads the known 10,000+1,000
  package or calls a provider. Use `npm run verify:stateful-clarification`,
  `npm run simulate:stateful-clarification`, or—once from a clean committed
  revision—`npm run execute:stateful-clarification`.
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
- `validate_evidence_sufficiency_v2.py`: validates the provider-neutral open-set
  answerability successor and reports a network-free, fail-closed preflight.
  Run `npm run verify:evidence-sufficiency-v2` or
  `npm run preflight:evidence-sufficiency-v2`. The preflight must remain blocked
  until a new independently reviewed decision set, exact candidate, and
  separate execution authorization exist.
- `build_evidence_sufficiency_v2_decision_draft.py`: deterministically builds
  and validates the 120-case synthetic-public decision draft without reading
  private data or calling a model. Run
  `npm run verify:evidence-sufficiency-v2-draft` to reconstruct the design in
  memory and verify the committed draft's exact hash and source lineage. The
  write command remains blocked by the active repository execution freeze; the
  draft is review-pending, not frozen evaluation authority.
- `prepare_evidence_sufficiency_v2_independent_review.py`: reconstructs the
  blinded 120-case review packet, 12 ten-case batches, and a separate 12-item
  clean/defect sensitivity control. It validates strict advisory judgments,
  caps the future priority packet at 12 cases, and reports a fail-closed
  provider preflight. Run
  `npm run verify:evidence-sufficiency-v2-independent-review`,
  `npm run simulate:evidence-sufficiency-v2-independent-review`, or
  `npm run preflight:evidence-sufficiency-v2-independent-review`. Historical
  instrument `002` binds exact OpenRouter routing to
  `mistralai/mistral-small-2603`, the published input/output prices, a USD 0.50
  hard ceiling, and synthetic-public data only. Its one paid call ended as an
  invalid execution and its authorization is revoked. The prepare command keeps
  validating that historical packet; the successor runner below validates the
  new packet independently.
- `run_evidence_sufficiency_v2_independent_review.py`: executes only the exact
  reviewer-bound packet after a separate frozen authorization. It runs the
  six-clean/six-defect sensitivity call before the 12 review batches, stops
  bulk work when reviewer sensitivity is unreliable, disables retries and
  fallbacks, pins model identity, checkpoints after every call, enforces the
  13-call and USD 0.50 ceilings, and supports binding-safe resume. Successor
  instrument `003` used endpoint-qualified strict JSON Schema output and
  preserved malformed response content plus exact parser detail; response
  healing was deliberately disabled. Its authorized sensitivity call stopped
  before a provider response with an authentication-class transport error, so
  the attempt is invalid and revoked with no review-quality conclusion. Use
  `npm run verify:evidence-sufficiency-v2-review-runner`,
  `npm run simulate:evidence-sufficiency-v2-review-runner`, or
  `npm run preflight-live:evidence-sufficiency-v2-review-runner`. The execute
  command is now fail-closed because the one-time `003` authorization is revoked;
  all dataset-freeze, candidate-evaluation, private-source, and later-stage
  execution remains blocked.
  Successor `004` removes the LiteLLM wrapper from this review path and sends the
  documented OpenRouter chat-completions payload directly. It opts into router
  metadata and preserves sanitized HTTP status, request ID, generation ID,
  error code/message, and routing attempts without recording credentials. Run
  `npm run verify:evidence-sufficiency-v2-review-004`,
  `npm run simulate:evidence-sufficiency-v2-review-004`, or
  `npm run preflight-live:evidence-sufficiency-v2-review-004`. Its authorized
  sensitivity request exposed first-party Mistral endpoint statuses 400 and 401
  before any provider response; the attempt is invalid and revoked. The exact
  execute command now fails closed. All dataset-freeze, candidate-evaluation,
  private-source, and later execution remains blocked.
  Successor `005` changes only the dropped reviewer binding: it requests stable
  `google/gemini-3.7-flash` through the exact `google-ai-studio` standard
  endpoint, freezes the dated backend identity, and keeps strict schema, zero
  retries, no fallbacks, native diagnostics, and synthetic-public inputs. Run
  `npm run verify:evidence-sufficiency-v2-review-005`,
  `npm run simulate:evidence-sufficiency-v2-review-005`, or
  `npm run preflight-live:evidence-sufficiency-v2-review-005`. Provider
  execution remains unauthorized, so the execute command fails closed.
  Prospective successor `006` preserves review 005 as build-only evidence and
  pins `openai/gpt-5.4-mini` to OpenRouter's exact `openai` standard endpoint
  and dated backend `openai/gpt-5.4-mini-20260317`. It omits unsupported
  `temperature`, fixes reasoning effort to `none`, fixes seed `0`, requires
  strict structured output, and disables all fallback routing. Run
  `npm run verify:evidence-sufficiency-v2-review-006`,
  `npm run simulate:evidence-sufficiency-v2-review-006`, or
  `npm run preflight-live:evidence-sufficiency-v2-review-006`. Its authorized
  sensitivity request received HTTP 400 before any provider response, so the
  attempt is invalid and revoked. The exact execute command now fails closed;
  all dataset-freeze, candidate-evaluation, private-source, and later execution
  remains blocked.
  Successor `007` keeps the same GPT-5.4 mini snapshot and strict response
  schema but removes nonessential reasoning and seed fields, permits
  same-model OpenAI/Azure provider fallback, and uses a USD 1.50 emergency
  ceiling. Run `npm run verify:evidence-sufficiency-v2-review-007`, `npm run
  simulate:evidence-sufficiency-v2-review-007`, or `npm run
  preflight-live:evidence-sufficiency-v2-review-007`. Its one authorized
  sensitivity request returned HTTP 400 before a provider response; all bulk
  calls were suppressed, authorization is revoked, and this OpenRouter path
  must not be retried. Every dataset and downstream decision remains blocked.
  Successor `008` leaves every OpenRouter attempt unchanged and uses the direct
  official DeepSeek API path already proven by the 10,000-case factual-QA run.
  It binds `deepseek-v4-pro`, JSON-object output with deterministic schema
  validation, thinking disabled, zero retries, no fallback, 13 calls maximum,
  a USD 0.15834 reservation, and a USD 1.50 emergency ceiling. Run `npm run
  verify:evidence-sufficiency-v2-review-008`, `npm run
  simulate:evidence-sufficiency-v2-review-008`, or `npm run
  preflight-live:evidence-sufficiency-v2-review-008`. Live preflight reads only
  the official model list. The authorized sensitivity call returned valid exact-
  model output but detected only 5/6 deliberate defects, so all 12 bulk batches
  were suppressed. Review 008 is completed, dropped for this contract, and
  authorization is revoked; do not retry it. DeepSeek retention and model-
  improvement use are not contractually excluded, so only synthetic-public
  review inputs were permitted.
- `run_evidence_sufficiency_v2_candidate_comparison.py`: validates and simulates
  the frozen 120-case answerability comparison without opening the decision
  split or loading models. It fixes course-scoped eligible BM25 retrieval, keeps
  AnyHit as an unselectable unsafe control, and compares an inspectable feature
  control with revision-pinned GTE ModernBERT support and DeBERTa NLI-augmented
  verifiers. Run `npm run verify:evidence-sufficiency-v2-candidate-comparison`,
  `npm run simulate:evidence-sufficiency-v2-candidate-comparison`, or `npm run
  preflight:evidence-sufficiency-v2-candidate-comparison`. Preflight must remain
  `blocked-not-authorized` until a separate checkpoint authorizes local-model
  execution and opens the exact decision split. The execute command is covered
  by the repository freeze and makes no provider or paid calls.
- `run_autonomous_tutoring_graph_development.py`: preserves the completed ten-
  trajectory T0/T1 comparison against committed synthetic fixtures. It records
  intents, actions, learner-state revisions, citation lineage, restart and
  fallback behavior, latency, and zero provider usage. Run
  `npm run verify:autonomous-tutoring-graph-development` for the no-write
  contract check. The one-time execution authorization is revoked; any future
  confirmation requires a successor instrument and cannot promote T1
  automatically.
- `synthetic_course_corpus.py`: shares the approved synthetic source, PDF, and
  chunk builders used by ingestion and retrieval verification.
- `validate_component_profile.py`: validates the complete component inventory,
  selection status, evidence paths, and linked evaluation decisions; run it
  with `npm run verify:profile`.
- `validate_technical_freeze.py`: validates the experimental freeze status,
  selected/disabled component links to registered results, complete supported
  and unsupported claim inventory, required technical boundary dispositions,
  paused professor-fidelity policy, artifact hashes, reproduction commands,
  and rollback/change-control contract; run it with `npm run
  verify:technical-freeze`.
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
- `second_review_multimodal_benchmark.py`: historical Claude second-review
  instrument retained only to preserve the 2026-08-01 result. The current model
  policy rejects it before provider execution; do not use it for new work.
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
- `bootstrap_admin.py`: provisions or rotates the first staging administrator
  from an environment-only password without emitting it.
- `run_ingestion_worker.py`: claims leased SQLite ingestion jobs, writes
  recoverable results, and safely recovers expired worker leases.
- `backup_runtime.py` and `restore_runtime.py`: create a checksum-verified
  online SQLite/object backup and restore it only into a clean target.
- `manage_runtime_data.py`: performs explicit staging retention, redacted
  account export, confirmation-bound account/course deletion, and retry of the
  durable raw/derived storage-deletion queue.
- `verify_deployable_foundation.py`: runs the network-free 41-gate invited
  professor/student workflow, restart, clean restore, rollback, and 100-request
  capacity measurement.
- `verify_https_staging.py`: drives the credentialed professor upload through
  student answer/original-region citation journey against a live HTTPS origin.
  It reads all passwords from environment variables, supports a private CA
  file for local Caddy qualification, emits no credentials, and can replay a
  sanitized result after container restart or clean restore. The optional
  `--mode-check` path creates a fresh grounded turn and proves that the selected
  T0 or T1 runtime mode is active rather than silently falling back.
- `verify_governed_autonomy_v2_1_implementation.py`: runs the actual governed
  autonomy service for 30 network-free simulated days, including a restart and
  goal expiry, and requires finite execution, preserved progress, no duplicate
  action or delivery, and no work after expiry. Run it with
  `npm run verify:governed-autonomy-v2-1-implementation`; it is a software
  regression check and does not select or academically evaluate T1-v2.1.
- `run_governed_full_autonomy_v2_1_provider_integration.py`: validates and
  simulates the frozen V2.1 direct-OpenAI integration, performs a metadata-only
  live preflight, and—only when its immutable instrument is separately
  authorized—executes two reactive turns plus one proactive job. It uses at
  most 12 calls, zero retries, and USD 1, cannot promote the release, and is
  smaller than the academic full-autonomy evaluation in #157.
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
- `evaluate_ml_dependency_compatibility.py` and
  `compare_ml_dependency_compatibility.py`: run the frozen selected-M2
  development comparison before changing retrieval ML dependencies and fail
  when exact top-three rankings, quality, isolation, data boundaries, or
  latency gates regress. Generated per-case artifacts remain ignored.
- `audit_python_dependencies.py`: audits the fully resolved Python lock,
  including optional retrieval dependencies, and matches every finding by
  exact package, version, advisory, fix versions, and occurrence against the
  tracked time-bounded exception policy. Any new, changed, or stale exception
  fails the command; run `npm run audit:python`.
- `run_factual_qa_v3_scale_rehearsal.py`: validates the corrected 120-case
  synthetic-public rehearsal source design, including exact per-claim citation
  anchors, 18 distinct controlled visual facts, 18 genuine two-source cases,
  and course-aligned boundary coverage. Attempt `002` is preserved as an invalid
  execution after its first-party Mistral ZDR route failed only after bulk
  authoring. Reviewed successor `003` adds schema-valid author and reviewer
  health canaries before bulk calls. Unexecuted `003` is superseded after the
  researcher allowed data collection for the synthetic evaluation phase.
  Reviewed `004` keeps the same first-party Mistral model, allows data collection
  and retention only for committed synthetic-public fixtures. Its one-time run
  completed but failed reviewer mutation sensitivity because all missing and
  truncated citations were accepted. The authorization is revoked; a rerun
  requires a new instrument and reviewer-method correction while the global
  freeze stays active. Successor `005` made exact target-claim and
  complete verbatim evidence-quote checks mechanical, adds paraphrased-citation
  and extra-supported-claim mutations, and selects 24 probes without reusing any
  004 mutation blueprint. Its one-time run is invalid after one malformed
  DeepSeek dispute response discarded completed in-memory metrics; authorization
  is revoked.
  `npm run preflight:factual-qa-v3-scale-rehearsal` is network-free. The
  explicit execution command requires both environment-owned provider keys,
  writes an ignored non-overwriting artifact, and cannot authorize a 10,000-case
  run. Provider canaries are part of paid execution and stop before every bulk
  call if either exact route is unavailable.
- `run_factual_qa_v3_reviewer_qualification.py`: runs bounded 24-pair reviewer
  qualifications with one provider canary, 48 paired reviews, eight-call
  durable checkpoints, zero retries, and complete malformed/provider failure
  accounting. Qualification 006 passed Mistral Small 4 at 49/49 calls and USD
  0.012175; its authorization is revoked and its result is registered.
  Qualification 007 tested hosted Qwen3.7 Plus on 24 new instances and failed
  completion, specificity, sensitivity, malformed-response, latency, and cost
  gates. Its authorization is revoked; Mistral Small 4 remains qualified.
  Neither qualification authorizes a 10,000-case run.
- `academic_factual_qa_pilot_data.py` and
  `run_academic_factual_qa_end_to_end_pilot.py`: define the corrected
  leakage-free development harness for issue #127. The in-memory dataset has
  160 synthetic-public cases, 32 source units, eight courses, and 80 explicit
  source/question clusters; it is marked unblinded and not independently
  validated. Both unselectable controls run through the normal T0
  `StudentTutoringService`, selected retriever with BM25 fallback, generator,
  citation persistence, and course boundary. A strict input model permits only
  case/request identity, course identity, and the student question to cross the
  product boundary; expected actions, claims, source IDs, slices, and rationales
  remain evaluator-only until after persistence. The simulation reports
  cluster-bootstrap intervals, slices, retrieval, expected-claim completeness,
  citations, actions, latency, persistence, and zero provider usage. Use
  `npm run verify:academic-factual-qa-e2e-pilot`, `npm run
  simulate:academic-factual-qa-e2e-pilot`, or `npm run
  preflight:academic-factual-qa-e2e-pilot`. Development execution, independent
  gold opening, the atomic-claim candidate, product binding, and academic claims
  remain blocked.
- `run_academic_factual_qa_end_to_end_pilot_v2.py`: runs the corrected paired
  development comparison under issue #127. It compares the any-hit T0 control,
  a structured question-to-evidence selection ablation, and the same ablation
  plus post-generation atomic-claim validation. The latter two arms must use
  identical draft hashes. The CLI records the exact Git revision and fails
  closed on a dirty worktree; the instrument permits only the 160-case
  synthetic-public network-free development run. Use `npm run
  verify:academic-factual-qa-e2e-pilot-v2`, `npm run
  preflight:academic-factual-qa-e2e-pilot-v2`, or the separately bounded
  `npm run execute:academic-factual-qa-e2e-pilot-v2`. The one-time development
  run is complete and its authorization is revoked, so the execution command is
  now blocked. Its pass cannot select the method, open independent gold, or
  promote the product.
- `validate_academic_factual_qa_confirmation.py`: validates the preregistered
  200-case public-source confirmation design without opening a source manifest
  or reference labels. It freezes 100 source/question-family clusters, one
  answerable and one boundary case per cluster, the three paired T0 conditions,
  independent-human review requirements, cluster-aware analysis, numeric gates,
  and a later unauthorized 600-case final tranche. Use `npm run
  verify:academic-factual-qa-confirmation` or `npm run
  preflight:academic-factual-qa-confirmation`. Preflight must remain
  `blocked-build-only` until an eligible source manifest, complete independent
  labels, an immutable product/profile binding, and separate execution
  authorization exist.
- `validate_academic_factual_qa_confirmation_v2.py`: validates the feasible
  successor review design without changing or deleting confirmation 001. It
  keeps deterministic source-derived truth authoritative, requires blinded
  isolated Codex, Mistral Small 4, and DeepSeek V4 Pro reviews for all 200 cases,
  qualifies each reviewer on 40 planted controls, requires unanimity for
  automatic semantic acceptance, and bounds the researcher packet to at most
  60 cases. Use `npm run verify:academic-factual-qa-confirmation-v2` or `npm run
  preflight:academic-factual-qa-confirmation-v2`. The source/case build is now
  bound, but preflight remains blocked; no Codex review, provider call,
  researcher audit, product execution, or final tranche is authorized.
- `prepare_public_evaluation_sources.py`: `npm run setup:evaluation-sources`
  fetches the five public Git revisions already specified by the confirmation
  builder. Run it before `npm run check` in a fresh checkout. It checks revisions
  and working-tree cleanliness, refuses to overwrite changed inputs, and leaves
  no partial destination on a failed fetch. Sources stay in ignored
  `data/external/academic_factual_qa_confirmation_002/`; their permissions and
  attribution remain recorded in the existing source manifest. This command
  does not generate or score evaluation cases or call model providers.
- `build_academic_factual_qa_confirmation_v2.py`: reads four locally cached,
  exact public repository revisions and deterministically rebuilds the
  160-section source manifest, 200 confirmation cases, and 40 disjoint planted
  controls. Complete upstream repositories remain ignored. Use `npm run
  verify:academic-factual-qa-confirmation-v2-data`; this makes zero provider
  calls and opens no private source.
- `prepare_academic_factual_qa_panel_review_v2.py`: creates the deterministic
  240-item packet while removing case IDs, strata, gold provenance, planted
  mutation labels, conditions, generator identity, and other votes. Use `npm
  run verify:academic-factual-qa-confirmation-v2-review-packet`.
- `run_academic_factual_qa_panel_review_v2.py`: validates reviewer JSON,
  calibration gates, unanimity, nominal Krippendorff alpha, immutable votes,
  atomic resume/accounting, the 40-disagreement stop, and the bounded researcher
  packet. The current CLI exposes only validation, simulation, and blocked
  preflight; it contains no paid execution mode. Use `npm run
  simulate:academic-factual-qa-confirmation-v2-review-runner` for the no-call
  clean scenario and `npm run
  preflight:academic-factual-qa-confirmation-v2-review-runner` to confirm that
  live review remains unauthorized.
- `execute_academic_factual_qa_panel_review_v2.py`: binds the actual review
  checkpoint to a fresh isolated `gpt-5.6-sol` Codex task, a versioned external
  reviewer route, and direct DeepSeek V4 Pro. Historical attempts 001/002 keep
  their exact Mistral Small 4 zero-data-retention routing through OpenRouter.
  It prepares a gold-free two-phase Codex workspace, performs metadata-only
  live preflight, and runs calibration before confirmation in batches of four.
  The executor has zero retries, a 120-call ceiling, atomic resume, stable
  identity checks, a conservative USD 1.563034 peak reservation, and a USD 3
  emergency stop. Use `npm run
  verify:academic-factual-qa-confirmation-v2-review-execution` and the simulated
  command for no-call verification. Calibration attempts 001 and 002 are
  preserved as invalid one-call Mistral results and their authority is revoked.
  Attempt 002's corrected harness records sanitized HTTP/provider error,
  latency, affected items, explicit unavailable usage/cost, and response hashes
  without retry. Successor attempt 003 reuses the sealed packet and immutable
  40/40 Codex votes, replaces only the failed Mistral slot with exact Gemini
  3.7 Flash revision `20260813` through the standard `google-ai-studio`
  endpoint, and ends after calibration. Its provider schema uses only the
  documented Gemini subset while complete IDs, uniqueness, visible-evidence
  lineage, and action consistency remain local deterministic checks. Use
  `npm run verify:academic-factual-qa-confirmation-v2-review-attempt-003`,
  `npm run simulate:academic-factual-qa-confirmation-v2-review-attempt-003`,
  and the separately authorized live preflight/execute commands. Attempt 003
  permits at most 20 calls, zero retries, USD 0.406426 conservative reservation,
  and the existing USD 3 emergency stop; it never opens the 200-case panel. Its
  live run is preserved as invalid after Gemini completed the first canary and
  direct DeepSeek returned empty content on the second. Authority is revoked;
  any successor calibration and later confirmation require separate decisions.
  Attempt 004 is that finite build-only successor: its reviewer sequence is
  immutable Codex plus exact Gemini only, it imports no attempt-003 Gemini
  votes, and it schedules all 40 controls as ten fresh batches. Only timeout,
  connection failure, HTTP 429/5xx, or empty content may retry, once per batch
  and twice globally. Use `npm run
  verify:academic-factual-qa-confirmation-v2-review-attempt-004`, `npm run
  simulate:academic-factual-qa-confirmation-v2-review-attempt-004`, and the
  separate live preflight/execute commands. The maximum reservation is USD
  0.211968 under the USD 3 stop. Its paid run is preserved as invalid after the
  first Gemini batch and its sole retry both returned HTTP 429. No Gemini vote,
  later batch, or confirmation case opened; provider usage/cost were
  unavailable. Authority is revoked, attempt 004 cannot be rerun, and the
  single-endpoint reviewer path is stopped. Researcher-directed attempt 005
  keeps the exact Gemini revision but uses OpenRouter's bounded health-aware
  transport: Vertex global priority/default followed by AI Studio
  priority/default. It uses seed 0 and the parameter subset shared by all four
  routes, records the actual provider and service tier per completion, requires
  at least two healthy endpoints at live preflight, and keeps model identity
  fixed across fallback. Use `npm run
  verify:academic-factual-qa-confirmation-v2-review-attempt-005`, `npm run
  simulate:academic-factual-qa-confirmation-v2-review-attempt-005`, and its
  separate live preflight/execute commands. Ten primary calls plus two bounded
  retries reserve USD 0.3815424 under the USD 3 stop. Attempt 005 is currently
  provider-unauthorized and cannot open the sealed 200 cases.
- `build_academic_factual_qa_visual_supplement.py`: deterministically builds the
  separate 30-cluster/60-case public visual supplement. It freezes ten tables,
  ten equations, ten original diagrams, one answerable and one balanced
  boundary case per asset, original-region lineage, licenses, versions, and
  source/render hashes. The committed metadata is reproducible; rendered and
  upstream assets remain ignored. Use `npm run
  build:academic-factual-qa-visual-supplement` only when intentionally updating
  the prospective artifact and `npm run
  verify:academic-factual-qa-professor-checkpoint` for the normal no-call gate.
- `run_academic_factual_qa_visual_checkpoint.py`: validates, simulates, and
  executes the separately authorized Gemini qualification and 30-cluster visual
  pilot. The provider-neutral description contract is question-independent,
  routes exactly to Google Gemini 3.7 Flash with fallback disabled, and keeps
  descriptions non-authoritative while citations resolve to original regions.
  Unsupported description facts that deterministic checks cannot clear produce
  an explicit Codex audit packet and `ready-codex-audit` state; they are never
  silently counted as supported. Qualification and pilot each require their own
  authorization and use zero retries, atomic accounting, and independent cost
  ceilings.
- `run_academic_factual_qa_t0_confirmation.py`: runs the actual T0 service over
  200 main and 60 visual cases using only course ID and question at the product
  boundary. It compares any-hit, structured-coverage, and shared-draft
  structured-plus-atomic-claim conditions, persists every response before
  opening gold, and reports action, retrieval, claim, citation, persistence,
  latency, cost, and seeded paired non-inferiority evidence. Its network-free
  simulation is explicitly marked non-academic. Live execution is blocked until
  the calibrated panel, assisted audit, visual pilot, clean revision, provider
  freshness, and a fifth separate authorization are present.
- `build_factual_qa_v3_10000_blueprints.py`: builds the supervisor-requested
  dummy factual-QA scale design from deterministic source truth. Its default
  mode validates 1,000 synthetic source units, 8,000 atomic claims, and 10,000
  stratified case blueprints without writing files or making provider calls.
  Run the reproducible no-call gate with
  `npm run verify:factual-qa-v3-10000-design`.
  `--write` is fail-closed under the repository freeze; neither dataset writing
  nor the 100, 1,000, or 10,000 paid stages is authorized by the draft design.
- `build_factual_qa_v3_10000_truth_packages.py`: preserves the immutable v1
  blueprints and derives 10,000 deterministic v2 truth packages. Canonical
  questions, answers, actions, structured claims, exact citations, boundary
  reasons, and hashes are authoritative; model output can modify none of them.
  The no-call command `npm run verify:factual-qa-v3-10000-truth` proves exact
  distribution, source lineage, boundary-empty lineage, normalized question
  uniqueness, byte stability, and zero private/provider access. `--write`
  remains blocked by the repository freeze.
- `build_academic_factual_qa_open_10000.py`,
  `build_academic_factual_qa_open_development_v2.py`,
  `build_academic_factual_qa_open_source_plan_v2.py`,
  `build_academic_factual_qa_open_development_v3.py`,
  `audit_academic_factual_qa_open_development_v2.py`,
  `construct_academic_factual_qa_open_10000.py`,
  `run_academic_factual_qa_open_10000.py`, and
  `score_academic_factual_qa_open_10000.py`: define the flow-independent
  professor-facing successor. The builder inventories pinned open educational
  sources and proves the originally requested course allocation is impossible
  under the five-cluster source-family cap. AFQC-035 removes tiny markup and
  mid-token fragments and freezes 2,100 context-bearing windows. The constructor
  derives gold before any model call, limits DeepSeek/Gemini to question wording
  and independent verification, and keeps raw responses in an ignored SQLite
  ledger. Construction attempt 001 is preserved as invalid after its first
  DeepSeek canary exposed a mutable runtime-fingerprint binding. Build-only
  binding 002 retains exact model/route gates, requires and records the runtime
  fingerprint diagnostically, and adds binding-level authorization checks plus
  sanitized failure details. Attempts 001–003 remain immutable invalid
  evidence. AFQC-044 then resolves the method-level construction decision in
  `build_academic_factual_qa_open_development_v2.py`: it writes exactly 500
  provider-free development cases, separate hidden gold, and a 100-case paired
  control from deterministic source truth. Its validation checks source-range
  lineage, boundary-empty lineage, answer leakage, normalized duplicates, and
  byte stability. It also simulates strict direct OpenAI and Mistral transport
  contracts with zero network calls.
  `audit_academic_factual_qa_open_development.py` adds a separate pre-spend
  fitness check over the written package. It preserves the structural build
  result while flagging likely answer fragments, raw markup/runtime artifacts,
  and structured slices whose selected answer does not contain evidence of the
  claimed modality. These diagnostics are a product-execution gate, not a
  replacement for semantic review and not permission to mutate historical
  packages.

  AFQC-046 supersedes that defective development reference layer without
  changing its historical artifacts.
  `build_academic_factual_qa_open_source_plan_v2.py` plans 100 non-overlapping
  complete semantic regions; `build_academic_factual_qa_open_development_v3.py`
  writes 500 public cases, separate hidden gold, and the fixed 100-case control;
  and `audit_academic_factual_qa_open_development_v2.py` verifies complete
  text statements, exact structured-region lineage, uniqueness, leakage, and a
  seeded 12-case semantic packet. The recorded `npm run
  write:academic-factual-qa-open-10000-development-v3` command now fails closed
  because its one-time provider-free build authority was revoked. `npm run
  verify:academic-factual-qa-open-10000` validates both historical evidence and
  the corrected package without network access.

  `run_academic_factual_qa_open_wording.py` implements AFQC-047 as a separate
  public-only wording checkpoint. The author receives case ID, course, slice,
  and canonical question; the reviewer receives only the canonical and proposed
  question. The provider execution function cannot open hidden gold. The scorer
  opens it only after the exclusive SQLite ledger is complete, then applies
  answer-leak, duplicate, reviewer, and canonical-fallback gates. Run `npm run
  simulate:academic-factual-qa-open-10000-wording` for the 500-case no-network
  simulation and `npm run preflight:academic-factual-qa-open-10000-wording` for
  the fail-closed paid readiness report. Execute and score commands remain
  blocked until the exact instrument receives separate authorization.

  `run_academic_factual_qa_open_development_checkpoint_003.py` is the finite
  direct-OpenAI successor. It first runs exact GPT-5.4 over the immutable 20
  clean and 20 planted-defect controls in ten four-item batches. Only a pass on
  action accuracy, mutation sensitivity, clean specificity, citation-defect
  sensitivity, vote coverage, schema, and identity permits the existing 25
  wording-author plus 25 wording-review batches. Accepted wording is then
  materialized as a paired runtime package before separate gold-free subprocesses
  run the 500-case structured-evidence candidate and 100-case any-hit control.
  Both response ledgers must be complete before the scorer can load either gold
  package. The combined checkpoint has zero retries, a 660-call ceiling, and
  separate USD 3/5/8/2 stage stops. Run `npm run
  verify:academic-factual-qa-open-development-003` and `npm run
  simulate:academic-factual-qa-open-development-003` without network access.
  The preflight and execute commands remain blocked until one explicit bounded
  authorization; final 10,000-case execution remains unauthorized.

  The response runner accepts only `EvaluationCaseV1`,
  supports T0/T1/T2/HTTP/control adapters, and persists responses in an
  exclusive resume-bound SQLite ledger without importing or reading hidden
  gold. The scorer opens `EvaluationGoldV1` only after durable completion and
  computes source-range retrieval, atomic-claim, citation, boundary, and
  source-family bootstrap metrics. Run `npm run
  verify:academic-factual-qa-open-10000`, `npm run
  simulate:academic-factual-qa-open-10000`, or the development/final preflight
  commands. Use `npm run
  preflight:academic-factual-qa-open-10000-development-v2` to confirm direct
  provider execution remains blocked. The development scoring and comparison commands open hidden gold
  only after both response ledgers are complete and evaluate the frozen paired
  100-case control using a source-family bootstrap. The deterministic package
  is complete, but the 500-case product run still requires fresh provider
  metadata, credentials, and separate paid authority; final 10,000-case
  execution remains closed.

  `build_academic_factual_qa_open_reference_validation.py` and
  `run_academic_factual_qa_open_reference_validation.py` own the fresh
  source-disjoint reference-question gate. Historical attempt 001 remains the
  default immutable command target. Attempt 002 is selected explicitly with
  `--attempt academic-factual-qa-open-10000-reference-question-validation-002`
  or the `*:academic-factual-qa-reference-validation-002` package commands. It
  adds only the provider-side terminal-question pattern required by the local
  validator and uses distinct ledger, result, and materialized-package paths.
  Attempt 003 is the finite order-insensitive successor. It requires every
  expected case ID exactly once, rejects duplicate/missing/unknown IDs, and
  restores frozen request order deterministically; it does not change source,
  prompt, model, gold, quota, or quality gates. Use the
  `*:academic-factual-qa-reference-validation-003` package commands. Validation,
  simulation, and preflight are network-free. Attempt 003 completed Refine with
  448/800 passing individual questions but only 8/160 complete clusters. Attempt
  004 is the finite method successor: it authors three variants for each
  answerable target, blind-reviews all variants, and keeps deterministic policy
  templates for boundary cases. Use the
  `*:academic-factual-qa-reference-validation-004` commands. Attempt 004 made
  seven durable calls before duplicate author candidates triggered an invalid
  whole-run parser termination. Attempt 005 is the sole harness-only correction:
  duplicate candidates are recorded as deterministic quality failures while the
  remaining batches continue unchanged. Use the
  `*:academic-factual-qa-reference-validation-005` commands; live execution is
  restricted to that exact bounded authorization. Attempt 005 then completed 32
  calls before one non-completed OpenAI author response caused an operational
  invalidity. Attempt 006 is the finite provider-resilient successor: it uses
  three-cluster batches and quarantines isolated non-identity provider failures,
  making affected reserve clusters ineligible while identity, credential,
  binding, request, and budget drift remain terminal. Use the
  `*:academic-factual-qa-reference-validation-006` commands.
- `run_factual_qa_v3_scale_pilot_100.py`: provides the separately bounded
  100-case stage over the hash-bound 10,000-case design. Validation and
  preflight make no provider calls; preflight must report
  `ready` only for an exact frozen instrument on a clean worktree with both
  credentials and an unused output path. Completed attempt 001 returned Refine
  after 226 calls exposed author/reviewer contract and mutation-eligibility
  defects; its authorization is revoked. Successor attempt 002 uses the full
  shared author schema, the exact qualification-006 strict reviewer contract,
  and deterministic canonical mutation controls that do not depend on author
  success. Its paid run completed as Refine with 93/100 deterministic validity,
  97% reviewer agreement, and 20/20 mutation rejection, but ambiguity-boundary,
  duplicate-question, one target-claim, and malformed-response gates failed.
  Attempt 002 authorization is revoked. The network-free
  simulator exercises 100 authors, 100 reviews, 20 mutations, bounded disputes,
  durable per-call checkpoints, safe resume, model identity, cost accounting,
  requested-versus-reported token-limit accounting, a USD 3 emergency stop,
  aggregate/slice gates, and the 12-case priority packet with deterministic fake
  transports. Use `npm run verify:factual-qa-v3-pilot-100`,
  `npm run preflight:factual-qa-v3-pilot-100`, or
  `npm run simulate:factual-qa-v3-pilot-100`. The paid `execute:` command is
  rejected because attempt 002 is completed and revoked. Any successor requires
  a new instrument and separate frozen authorization. Later stages remain blocked.
- `run_factual_qa_v3_scale_pilot_100_003.py`: validates and simulates the
  deterministic-truth successor. The author contract contains only
  `question_variant`; deterministic code assembles the canonical answer,
  action, claims, and citations. Malformed or duplicate variants fall back to
  unique canonical wording with explicit provenance and still count against
  the model-quality gates. The runner reuses qualification-006 review,
  deterministic mutations, atomic checkpoints, safe resume, bounded disputes,
  and the USD 3 emergency stop. Use `npm run
  verify:factual-qa-v3-pilot-100-003`, `npm run
  preflight:factual-qa-v3-pilot-100-003`, or `npm run
  simulate:factual-qa-v3-pilot-100-003`. Paid execution remains unauthorized.
- `run_factual_qa_v3_scale_checkpoint_1000.py` and
  `run_factual_qa_v3_scale_completion_10000.py`: share the validated
  deterministic stage engine. Checkpoint 002 completed the cumulative 1,000
  cases with a Keep decision. Completion 001 then completed exactly the
  remaining 9,000 cases plus 1,800 balanced mutation controls as a cumulative
  10,000-case Keep result. Its one-time authorization is revoked. The runner
  uses an atomic SQLite journal so each result is durable without repeatedly
  rewriting the full growing output. Live preflight requires minimum provider
  balances of USD 3 for DeepSeek and USD 4 for OpenRouter. A provider-reported
  insufficient-credit response pauses immediately without completing the
  current logical item; after top-up, rerun the paid command with `--resume`.
  At most two such no-response continuations are allowed, while ordinary
  provider or quality failures retain zero retries. Run `npm run
  verify:factual-qa-v3-completion-10000`, `npm run
  preflight:factual-qa-v3-completion-10000`, `npm run
  preflight-live:factual-qa-v3-completion-10000`, or `npm run
  simulate:factual-qa-v3-completion-10000`. The paid `execute:` command is now
  blocked by the revoked instrument and removed bounded authorization; the
  completed run must not be repeated under the same ID.
- `validate_factual_qa_provider_freshness.py`: validates the frozen 24-hour
  provider snapshot without network access by default. `--live` compares the
  instrument against the official DeepSeek pricing table and OpenRouter model
  list without making inference calls. Any model revision, context limit,
  conservative peak price, exact Mistral slug/price, or routing drift blocks a
  paid preflight. Run `npm run verify:factual-qa-provider-freshness`; the live
  check is invoked by `npm run preflight-live:factual-qa-v3-pilot-100-003`.
- `validate_professor_digital_twin_transition.py`: validates the separate C0-C3
  fidelity design, the explicit/inferred professor-profile provenance schema,
  professor approval gate, and the empty 8-12-case calibration template. It
  opens no held-out content and makes no model call; run `npm run
  verify:professor-digital-twin-transition`.
- `build_academic_factual_qa_source_aligned_confirmation.py`: builds the fresh
  source-family-disjoint 500-case AFQC-101 package. Canonical evidence is
  registered as source-derived exact regions before ranking, so validation
  fails unless every answerable gold reference exists in the runtime corpus.
  The committed build uses public sources only and makes no provider call. Run
  `npm run verify:academic-factual-qa-source-aligned-confirmation` for the
  network-free reconstruction and matchability check.
- `run_academic_factual_qa_source_aligned_wording.py`: runs AFQC-101 stage one
  under the finite non-human program. GPT-5.4 nano proposes context-complete
  wording and GPT-5.6 Terra performs target-blind advisory recovery. Models
  cannot alter source truth; rejected or unavailable wording is replaced by a
  unique deterministic fallback. Use the `verify:`, `simulate:`, `preflight:`,
  `preflight-live:`, `execute:`, and `resume:` package commands with the
  `academic-factual-qa-source-aligned-wording` suffix.
- `run_academic_factual_qa_source_aligned_retrieval.py`: compares the fresh
  source-aligned package across BM25, direct OpenAI small/large dense and
  hybrid retrieval, and deterministic hierarchy. It persists every public
  ranking before opening hidden gold, enforces exact source-range
  matchability, checkpoints API embeddings, supports bound resume, and selects
  only the simplest method within two percentage points of the best passing
  result. Use `npm run verify:academic-factual-qa-source-aligned-retrieval`,
  `npm run simulate:academic-factual-qa-source-aligned-retrieval`,
  `npm run preflight:academic-factual-qa-source-aligned-retrieval`, or the
  execute/resume commands. AFQC-101 program authority removes a separate
  administrative approval; its USD 2 stage stop and all quality/privacy gates
  remain active.
- `build_academic_factual_qa_atomic_m2_confirmation.py` and
  `run_academic_factual_qa_atomic_m2_confirmation.py`: implement the single
  prospective correction to AFQC-103's parent/child evidence-granularity
  defect. The builder freezes 100 fresh source-family-disjoint clusters as 300
  non-overlapping authoritative atoms and 500 unique cases. The runner compares
  unchanged small hybrid M2 with one deterministic question-only marginal
  coverage selector, persists public rankings before opening hidden gold, and
  stops factual scaling if neither method passes the original evidence,
  boundary, isolation, and latency gates. The existing non-human program is the
  only paid authority; execution is capped at 20 calls, zero retries, and USD 1.
  Use the `verify:`, `simulate:`, `preflight:`, `execute:`, and `resume:` package
  commands ending in `academic-factual-qa-atomic-m2-confirmation`.
- `build_academic_factual_qa_action_router_confirmation.py`,
  `build_academic_factual_qa_action_router_product_checkpoint.py`, and
  `run_academic_factual_qa_action_router_product_checkpoint.py`: implement the
  single method-level successor to the valid atomic-M2 product failure. The
  package contains 100 new clusters and 500 questions whose exact source ranges
  do not overlap any earlier development package. Because the four pinned
  repositories cannot supply another fully source-family-disjoint portfolio,
  source-family overlap is disclosed and uncertainty remains clustered by
  family. The candidate adds deterministic ambiguity, cross-course, future,
  and graded-work routing, narrows approved evidence to the one or two facts
  requested by the public question, and requires the generator to return the
  matching atomic-claim count. The fixed 100-case control retains the historical
  structured gate and extractive generator. Network-free validation and all
  terminal simulations are available through package commands ending in
  `academic-factual-qa-action-router-product`; paid execution is not authorized.
- `run_course_digital_twin_nonhuman_supplements.py`: executes the two independent
  non-human supplements under program 002 without reusing the terminated
  program-001 dispatcher. Stage A compares text fallback with course-scoped
  GPT-5.4 nano visual descriptions over 30 public visual clusters and 60 cases;
  original region lineage remains authoritative and a visual quality failure is
  recorded as Refine. Stage B runs an explicitly synthetic C0-C2 profile
  diagnostic over 12 cases with GPT-5.4 mini; C3, real professor fidelity, and
  human claims remain closed. The runner uses exclusive SQLite ledgers, exact
  identity checks, zero retries, safe resume, 66 calls maximum, and separate USD
  2/USD 1.5 stage stops. Use package commands ending in
  `nonhuman-evaluation-supplements`.
- `run_professor_fidelity_proxy_harness.py`: validates and simulates the fresh
  12-case, flow-independent C0-C3 proxy packet. It keeps deterministic factual,
  citation, safety, and boundary gates separate from blinded multi-LLM teaching
  ratings. Its output is explicitly synthetic proxy evidence and cannot become
  a real-professor fidelity reference without professor approval. Use
  `npm run verify:professor-fidelity-proxy-harness` and
  `npm run simulate:professor-fidelity-proxy-harness`.
- `run_professor_fidelity_proxy_c0_c3_003.py`: is the single-change successor
  to invalid attempt 002. It moves unsupported array/string assertions out of
  the provider-facing schemas and retains the same deterministic post-parse
  validation. The 12 cases, C0-C3 conditions, models,
  prompts, seed, gates, USD 3 ceiling, and synthetic-only claim boundary remain
  fixed. Commands ending in `professor-fidelity-proxy-c0-c3-003` validate,
  simulate, preflight, execute, or resume the exclusive successor ledger.
- `run_true_visual_supplement_003.py`: provides the method-level successor to
  the two immutable invalid visual attempts. It preserves question-independent
  visual descriptions and original-region citation authority, but normalizes
  whitespace and removes only exact case-insensitive duplicate semantic-list
  values per asset while accounting for every removal. The completed
  30-asset/60-case run is `Refine`; its one-time authority is revoked. The
  frozen unsupported-segment metric is a conservative lexical-reference proxy,
  not a verified hallucination count, and the result supports no representative
  visual-capability claim. Use network-free package commands ending in
  `true-visual-supplement-003`.
- `build_true_visual_colpali_confirmation.py` and
  `run_true_visual_colpali_confirmation.py`: implement the fresh method-level
  successor to supplement 003. The builder creates a source-disjoint
  30-asset/60-case public package with ten tables, ten diagrams, ten equations,
  paired boundary cases, and hash-bound original-region lineage. The runner
  compares source-visible-text BM25 with first-party Jina Embeddings v4
  multi-vector image/query representations ranked by MaxSim. Use package
  commands ending in `true-visual-colpali-confirmation` to validate, simulate,
  or inspect the no-call preflight. The simulation verifies contracts only and
  is not model-quality evidence. Provider execution remains unauthorized and
  requires `JINA_API_KEY` plus a separate freeze checkpoint.
- `run_course_digital_twin_evaluation_program.py`: owns the finite factual,
  visual, synthetic-profile, and autonomous-tutoring evaluation dispatcher.
  Historical programs 002 and 003 are immutable invalid executions. Program
  004 is also invalid for academic interpretation because its parent-section
  runtime corpus did not contain the development gold ranges exactly; its
  visual and synthetic-profile diagnostics remain recorded separately.
  Program 005 binds the validated 500-case action-router package to its exact
  300-atom source corpus, checks every gold range before any provider call, and
  automatically advances from fresh retrieval through 500+100 product
  development and then the sealed 10,000+1,000 evaluation only when the frozen
  gates pass. One program-level USD 50 authority replaces per-stage approval
  pauses. Privacy, gold isolation, identity, ledger integrity, and the global
  budget remain fail-closed. Use package commands ending in
  `finite-evaluation-program-005`; a stopped run resumes with
  `npm run resume:finite-evaluation-program-005`.
- `build_academic_factual_qa_grounding_selection_002.py` and
  `run_academic_factual_qa_grounding_selection_002.py`: define the one-shot
  issue-153 successor over the frozen 500 candidate and 100 control questions.
  Two public-question canaries must pass exact direct-OpenAI identity and cost
  checks before any bulk call. Product responses are persisted by case ID, both
  ledgers must complete before hidden gold opens, retries remain zero, and the
  emergency stop is USD 50. The historical API retrieval materialization is
  reused by exact hash; no prior response or score is reused. Validation,
  simulation, preflight, execute, and resume commands use the
  `academic-factual-qa-grounding-selection-002` suffix.
- `build_governed_full_autonomy_v2_1_actual_product_evaluation_002.py`,
  `governed_full_autonomy_v2_1_actual_product_runtime.py`, and
  `run_governed_full_autonomy_v2_1_actual_product_evaluation_002.py`: replace
  harness 001's compressed reference timing with an 820-case actual-service
  successor. One injected `VirtualUtcClock` drives tutoring, autonomy, outreach,
  leases, wake-ups, quiet hours, cooldowns, expiry, restart, and the 30-day
  horizon without rewriting database timestamps. The response process uses 50
  source-disjoint synthetic-public releases and keeps hidden policy/source gold
  closed until all responses are durable. The complete network-free execution
  passed as runtime evidence with 820 clock histories and zero provider calls;
  its low deterministic behavior metrics are explicitly not a product-quality
  result. Paid Terra/mini execution remains blocked by #153, fresh metadata,
  freeze authorization, and a separate checkpoint authorization. Commands use
  the `governed-autonomy-v2-1-actual-product-evaluation-002` suffix.
- `build_governed_full_autonomy_v2_1_actual_product_evaluation_003.py` and
  `run_governed_full_autonomy_v2_1_actual_product_evaluation_003.py`: bind the
  same prospective 820-case portfolio to #172's selected ambiguity-safe
  source-semantic evidence-atom V2. Student questions expose only a public
  source/section scope; answer, action, evidence, and policy gold remain
  isolated. The actual `StudentTutoringService` receives the selected semantic
  atom retriever and V2 gate through an explicit retriever factory. Validation
  and the complete network-free simulation must pass before freeze authority
  enables direct OpenAI canaries and a resumable paid run. Commands use the
  `governed-autonomy-v2-1-actual-product-evaluation-003` suffix.
- `build_governed_full_autonomy_v2_1_actual_product_evaluation_004.py` and
  `run_governed_full_autonomy_v2_1_actual_product_evaluation_004.py`: preserve
  003 as invalid canary evidence and apply its one permitted harness-only
  correction. The public events, hidden gold, method, models, and gates are
  unchanged; only Pydantic schemas are translated to OpenAI's conservative
  strict subset before post-parse Pydantic validation. Commands use the
  `governed-autonomy-v2-1-actual-product-evaluation-004` suffix.
- `build_governed_full_autonomy_v2_1_actual_product_evaluation_005.py` and
  `run_governed_full_autonomy_v2_1_actual_product_evaluation_005.py`: preserve
  004's malformed canary as invalid evidence and perform the user's explicit
  final connectivity retry. Events, hidden gold, method, schemas, models, and
  gates are unchanged. Commands use the
  `governed-autonomy-v2-1-actual-product-evaluation-005` suffix.

`governed-autonomy-v2-1-actual-product-evaluation-006` is the first
diagnosable successor after the terminal malformed-response retries. It keeps
the 820-case method and hidden gold unchanged while recording only bounded
Responses API status, item/part types, refusal presence, response hashes, model
identity, usage, and cost. It never retains unrestricted provider output.
The run classified the T0 failures at local schema validation and exposed the
non-intent answer-prompt versus atomic-claim-schema mismatch. It is terminal
invalid evidence. The `007` commands preserve the same 820 cases, gold,
retrieval, models, and gates while correcting only that demonstrated runtime
prompt binding. Attempt 007 passed both canaries but stopped before hidden gold
after proving its 3,000-call ceiling could not contain the conservative
5,740-call upper bound. The `008` commands keep every evaluation and product
binding unchanged, perform that call projection before bulk, use a 10,000-call
safety ceiling, and process at most eight independent cases concurrently while
persisting every completed case atomically. Attempt 008 completed 820/820 and is
terminal `Refine`: corrected frequency and paired-grounding analysis pass, but
all 290 expected proactive check-ins were emitted as diagnostic questions. Its
authorization is revoked; the opened cases must not be reused for confirmation.
- `build_governed_full_autonomy_v2_1_actual_product_evaluation_009.py` and
  `run_governed_full_autonomy_v2_1_actual_product_evaluation_009.py`: bind the
  event-scoped-action successor to 820 fresh cases over source families 051–100.
  Validate, simulate, preflight, execute, and resume commands share the actual
  product runner. The network-free simulation passes all gates; provider
  execution remains fail-closed and unauthorized.
- `build_governed_full_autonomy_v2_1_actual_product_confirmation_015.py`
  through `016.py` and their runners preserve the selected H+E1 confirmation
  lineage. Confirmation 015 is immutable formal Keep evidence whose release
  interpretation was blocked by the later SE7-2 audit. Confirmation 016 is a
  fresh pedagogy-aware package but ended invalid before bulk when its reactive
  canary correctly used the deterministic fast path.
- `run_governed_full_autonomy_v2_1_actual_product_confirmation_017.py` preserves
  the sole same-package harness correction and its terminal invalid result. The
  replacement canary also made no provider call. Authority is revoked and the
  016/017 package must never be used for another confirmatory run.
- `build_governed_full_autonomy_v2_1_actual_product_confirmation_018.py` and
  `run_governed_full_autonomy_v2_1_actual_product_confirmation_018.py` create
  the fresh source-disjoint successor over source families 351–400. A direct
  transport/identity canary is persisted separately from reactive and
  autonomous actual-product route canaries. Bulk execution cannot begin unless
  each route records the exact returned Luna identity and complete accounting.
  Validation, full network-free simulation, preflight, execute, and resume
  commands use the `governed-autonomy-v2-1-actual-product-confirmation-018`
  suffix. Paid execution remains unauthorized in the build checkpoint.
- `build_governed_full_autonomy_v2_1_actual_product_confirmation_019.py` and
  `run_governed_full_autonomy_v2_1_actual_product_confirmation_019.py` preserve
  invalid 018 and make its sole harness-only canary-role correction. The direct
  canary still requires a completed exact-identity structured response. The
  product-route canaries instead require an observed exact-identity provider
  attempt plus safe actual-product completion, so malformed semantic output is
  measured through the production fallback rather than misclassified as an
  unexecuted route. Cases, prompts, models, hidden gold, and hard gates are
  unchanged; provider authority remains false in the build checkpoint.
- `build_governed_full_autonomy_v2_1_cross_engine_evaluation_010.py` and
  `run_governed_full_autonomy_v2_1_cross_engine_evaluation_010.py`: freeze the
  six-engine whole-product comparison, verify exact public/gold/prompt/policy
  hashes, and run the 820-case actual-product network-free qualification with
  `independent-autonomy-scorer-v2`. The scorer derives action, authority,
  citation, persistence, delivery, restart, transition, and termination results
  from raw sanitized evidence rather than product-reported invariant flags.
  Use `npm run validate:governed-autonomy-v2-1-cross-engine-evaluation-010`,
  `npm run simulate:governed-autonomy-v2-1-cross-engine-evaluation-010`, or
  `npm run preflight:governed-autonomy-v2-1-cross-engine-evaluation-010`.
  `build_cross_engine_sealed_confirmation_010.py` adds the byte-stable,
  source-range-disjoint 1,000-case confirmation. Execute/resume commands are
  implemented but fail closed until the program instrument and bounded freeze
  both carry the one-time USD 50 authorization.
- `run_successor_architecture_paired_comparison_001.py`: validates the finite
  A/B/C/C+V tournament manifest and runs 48 network-free actual-graph
  conformance cells. It proves that A makes zero model-planning calls, C at
  depth zero recovers B, all candidates stay inside the same deterministic
  action/evidence/authority envelope, and C+V can only reject. Use
  `npm run validate:successor-architecture-paired-comparison-001`,
  `npm run simulate:successor-architecture-paired-comparison-001`, or the
  combined `npm run verify:successor-architecture-paired-comparison-001`.
  These commands never perform provider calls and cannot select an
  architecture.
- `run_course_digital_twin_autonomous_long_run_001.py`: provides the one-
  authority finite controller for the #153/#157 path. Both permitted attempts
  are terminal invalid evidence before provider I/O; authority is revoked and
  the 820-case stage was not opened. The local regression passed 45/45. Its
  revision-bound ledgers and result hashes are preserved, and it references but
  never quality-reruns Program 011's sealed 10,000+1,000 evidence. The package
  commands ending in `autonomous-long-run-001` now validate or simulate only;
  live preflight and execution fail closed.
- `build_atomic_claim_validation_dataset.py` and
  `run_atomic_claim_validation_confirmation.py`: build and protect the fresh
  120-case synthetic-public successor to the failed query/evidence gate. The
  generator may propose atomic claims, but deterministic code owns eligible
  retrieval lineage and the final release decision. The exact-quote control
  and pinned DeBERTa NLI candidate validate evidence as premise and each claim
  as hypothesis. Network-free simulation exercises supported, unsupported,
  malformed, and unknown-lineage paths without loading a model or opening the
  confirmation split. Use `npm run
  verify:evidence-sufficiency-v3-atomic-claim`, `npm run
  simulate:evidence-sufficiency-v3-atomic-claim`, or `npm run
  preflight:evidence-sufficiency-v3-atomic-claim`. Local execution and product
  binding remain unauthorized until a separate checkpoint.
- `build_academic_factual_qa_source_semantic_atoms.py` and
  `run_academic_factual_qa_source_semantic_atom_comparison.py`: implement the
  fresh successor to the rejected question-side semantic resolver. The builder
  derives atom-specific search projections and explicit same-section relations
  from approved canonical source ranges only, then freezes 500 new questions
  over 100 source-range-disjoint clusters. The runner compares this candidate
  with the retained typed-target rollback, persists all public responses before
  opening hidden gold, and emits exactly one Keep, Refine, or invalid result.
  Use `--validate` or `--simulate` for no-result checks and `--execute` once for
  the authorized network-free comparison; no provider or paid call is possible.
- `audit_academic_factual_qa_source_semantic_atom_failures.py`: validates the
  exact 16 answerable failures from that immutable comparison, verifies source
  support and top-three gold retrieval, and aggregates the committed
  Codex-assisted case adjudications. The audit never changes the official
  result or its gates. Use `--validate` for a no-write check and `--execute`
  once for the bounded network-free audit.
# Final-profile longitudinal development

The new runner constructs tutoring services through the production application
factory. It preserves selected deterministic factual claims while allowing the
selected live planning client, durable per-call ledgers, and shared budget limits
across virtual-time restarts. Historical experiment 025 is unchanged.

```bash
uv run python -m scripts.run_final_profile_longitudinal --validate
uv run python -m scripts.run_final_profile_longitudinal --contract-smoke --days 3 --output-dir reports/generated/final-profile-contract-fresh
```

`--contract-smoke` injects malformed provider responses without network access.
It is not live evidence. `--execute` requires recorded bounded authorization for
`final-profile-live-longitudinal-development-001` and accepts `--days`,
`--concurrency`, `--maximum-calls`, and `--maximum-cost-usd`. Defaults are seven
virtual days, concurrency two, 200 attempts, and USD 2 of conservative reserved
allowance. Each admitted call reserves USD 0.01; oversized payloads and budget
exhaustion block before the transport is called. Existing outputs are rejected;
no run-level resume is supported. Prompt/response ledgers are synthetic local
artifacts and remain Git-ignored.

This runner installs a synthetic course fixture directly and does not qualify
ingestion or browser workflows. See the
[completion plan](../research/04_experiments/2026-09-05-project-completion-plan.md)
for independent quality, contrasting-profile, and end-to-end acceptance work.

## Teaching-profile responsiveness development

`uv run python -m scripts.run_teaching_profile_responsiveness_development --validate`
shows the fresh 24-arm packet: two approved synthetic teaching profiles, context
on/off, and six cases. The runner uses isolated reactive production-factory
runtimes and preserves complete delivered responses, pedagogical intents, and
provider attempt records. It does not establish real-professor fidelity.

Use `--contract-smoke --output-dir reports/generated/profile-contract-new` for
network-free malformed-provider handling. Live `--execute --output-dir
reports/generated/profile-live-new --maximum-calls 100 --maximum-cost-usd 1`
requires the exact `teaching-profile-responsiveness-development-001` bounded
instrument authorization and a configured OpenAI credential. Outputs must not
already exist. Defaults permit two concurrent cases. The summary reports style
intent diagnostics; delivered content and boundary quality require independent
review, and qualification is never inferred from execution completion.

## Schema18 source recovery and tutoring request probe

`uv run pytest -q tests/services/test_schema18_product_recovery.py` checks reviewed
UTF-8 text/Markdown jobs through backup and clean restore, plus actual in-process
ASGI tutoring POST contracts. `scripts.tutoring_capacity_probe` exposes
`StudentProbeSession` and `measure_tutoring_requests` for callers with separately
provisioned clients and conversations. It issues sequential turns per student,
concurrent students, and no retries; callers supply deployment/authentication and
must separately score teaching quality. Its mock/ASGI tests are not deployed
capacity evidence. Never substitute the old verifier's sequential course-list
GET loop for model-backed tutoring load.

The professor upload route now accepts `text/plain` and `text/markdown` in the
same worker flow as PDF; see [service source instructions](../services/README.md).
No connector or automatic anonymizer is implied by those accepted formats.

## Shared-runtime ASGI tutoring concurrency

`uv run python -m scripts.run_asgi_tutoring_concurrency_development --validate`
shows the bounded 25-student, four-turn development configuration. Use
`--contract-smoke --students 2 --turns 2 --output-dir reports/generated/asgi-contract-new`
for a network-free smoke check. Live `--execute --output-dir reports/generated/asgi-live-new
--maximum-calls 500 --maximum-cost-usd 5` requires the exact
`final-profile-asgi-tutoring-concurrency-development-001` authorization and configured
provider credentials. Output directories must be new.

The existing student route uses one actual factory-built tutoring service and
SQLite runtime; injected synthetic account headers replace production login.
Outputs retain complete responses, per-request provider attribution, latency,
errors, persistence counts and start/end source hashes. This measures in-process
route concurrency, excluding Docker, sockets, production authentication and
distributed workers. Successful response contracts do not score teaching quality
or establish deployed capacity. See the
[prospective plan](../research/04_experiments/2026-09-06-asgi-tutoring-concurrency-plan.md).

The default provider budget remains serial. The prospective bounded comparison
opts into `--provider-max-concurrency 5`; only a transport exposing a conservative
request-cost ceiling can overlap. Admission reserves all in-flight ceilings under
the dollar cap, and cancellation or unknown usage retains its reservation and
closes further admissions. Client and provider peak concurrency are reported
separately. Clients without the ceiling capability retain serial behavior; an
advertised ceiling returning no bound is rejected before admission. This experimental setting
does not silently select a release profile or change the production default.


Explicit serial control and bounded candidate commands (load the local credential
first; each output directory must be new):

```sh
uv run python -m scripts.run_asgi_tutoring_concurrency_development --execute --students 25 --turns 4 --provider-max-concurrency 1 --maximum-calls 500 --maximum-cost-usd 5 --output-dir reports/generated/asgi-serial-new
uv run python -m scripts.run_asgi_tutoring_concurrency_development --execute --students 25 --turns 4 --provider-max-concurrency 5 --maximum-calls 500 --maximum-cost-usd 5 --output-dir reports/generated/asgi-concurrent-new
```

## Operational dialogue development

The following commands use fresh synthetic histories through actual product
services. `--progression-contract` needs no external provider. Live modes require
local credentials and the exact operational-dialogue instrument authorization;
all outputs are exclusive. The finite progression packet uses four histories and
16 stimuli. Terra changes reactive planning/generation only, not full autonomous
planning; neither model's successful schema validation is a teaching-quality pass.

```sh
uv run python -m scripts.run_operational_dialogue_development --progression-contract --output-dir reports/generated/progression-contract-new
uv run python -m scripts.run_operational_dialogue_development --progression-live --progression-model gpt-5.6-luna --output-dir reports/generated/progression-luna-new
uv run python -m scripts.run_operational_dialogue_development --progression-live --progression-model gpt-5.6-terra --output-dir reports/generated/progression-terra-new
uv run python -m scripts.run_operational_dialogue_development --full-live --output-dir reports/generated/operational-full-new
```

The full live mode fixes 24 histories over 30 virtual days, six simultaneous
histories, 5,000 maximum calls and a USD 50 conservative reservation cap. Provider
calls within each history remain serial. Its students, replies and elapsed time
are simulated; generation, state persistence, consent checks, scheduled processing
and restart exercise actual services. See the
[operational plan](../research/04_experiments/2026-09-06-operational-dialogue-development-plan.md)
and retained result registry. No private material is automatically ingested.

### Evaluator calibration and clustered development analysis

`uv run python -m scripts.evaluation_calibration_cluster_analysis --output-dir reports/generated/<new-directory>` runs the no-network scorer mutation calibration and paired cluster analysis of frozen live005 and the full operating simulation. It refuses to overwrite an output directory. See the [prospective plan](../research/04_experiments/2026-09-06-evaluator-calibration-and-cluster-analysis-plan.md). These are development diagnostics, not semantic qualification or a learning-effect estimate.

### Output-cap progression development

`uv run python -m scripts.run_output_cap_progression_development --output-dir reports/generated/output-cap-contract-fresh`
runs a network-free contract instrument. With the authorized provider credential
privately loaded, add `--live` for the preregistered500/1500-token comparison:
48 synthetic trajectories,192 actual student turns, three order/repetition
seeds, and a500-call/$10 reservation ceiling. Use a fresh output directory.
The selected/default profile is unchanged; inspect per-case responses and the
plan in `research/04_experiments/2026-09-06-output-cap-progression-development-plan.md`.
Later tutor histories may diverge between arms; this is development, not a
held-out quality confirmation or a learning study.

`uv run python -m scripts.semantic_calibration_v2` validates the 32 synthetic controls with explicit current-turn profiles. Add `--public-output <new.jsonl>` to export only allowlisted judge payloads; gold and control labels are excluded. See the [v2 calibration plan](../research/04_experiments/2026-09-06-semantic-calibration-v2-plan.md). This validation makes no external calls and does not establish human-reviewed labels.

## Mixed-source candidate recovery contract

```sh
uv run python -m scripts.run_mixed_source_recovery_development --execute --output-dir reports/generated/mixed-source-contract-new
uv run pytest -q tests/test_mixed_source_recovery_development.py
```

The exact `mixed-source-candidate-recovery-development-001` instrument authorization
and an exclusive output directory are required. No external credential or private
material is needed. The actual staging TestClient app uses credential/session and
Origin handling, queued PDF/text/Markdown ingestion, approved profile/domain and
publication APIs, candidate dialogue, source-window feedback and clean restore.
A deterministic injected provider makes this an integration contract, not live
model quality or deployed TLS/browser performance. Approved onboarding is a
synthetic setup fixture; the historical staging binding does not qualify the
candidate override. All failed setup attempts remain in the evaluation registry.
See the [coverage and load audit](../docs/evaluation-mixed-source-and-load-audit-2026-09-06.md).

### Bounded-contract v2/v3 development

`uv run python -m scripts.run_bounded_contract_progression_development --output-dir reports/generated/bounded-contract-fresh`
runs the network-free contract version. Add `--live` only with the authorized
credential loaded privately to run the preregistered fixed1500-token v2/v3
comparison:36 trajectories/72 turns, three order/repetition seeds, maximum240
calls/$4.80 reserved. V3 is explicitly opt-in; local count limits and selected
defaults remain unchanged. See the plan at
`research/04_experiments/2026-09-06-bounded-contract-communication-plan.md`.

The preregistered genuine concept-switch supplement uses the same command with
`--concept-switch`, a fresh output directory, and explicit `--live` for provider
calls. It contains six three-turn histories (40 calls / USD 0.80 upper bound).

The bounded-contract runner also supports `--named-referents` for its preregistered
v3/v4 authorized-referent supplement: 26 histories / 32 turns, six replay histories
and fresh boundary cases, at most 120 calls / USD 2.40. Use a fresh output directory;
`--live` is required for external calls. This opts into the v4 contextual admission
candidate without altering the selected release or runtime defaults.

### Authenticated loopback load development

The isolated HTTPS evaluator starts and stops only its own dynamically allocated
Uvicorn process. It creates synthetic credentials and a mixed-source course,
then exercises actual session/Origin middleware over a network socket. The
contract uses an injected generator; it does not contact a provider:

```bash
uv run python -m scripts.run_authenticated_loopback_load_development --contract --bounded-contract --output-dir reports/generated/authenticated-loopback-contract-fresh
```

For the preregistered live v3 operational candidate, provide `OPENAI_API_KEY` in
the process environment and use `--execute` in place of `--contract`, with a
fresh output directory. This is the explicit bounded generation candidate at
1,500 output tokens and provider concurrency 5; the product default remains
serial concurrency 1. The fixed load order is 5/25/25/5/5/25 learners, two turns
each (180 POSTs), with at most 300 model calls and USD 10 of ledger reservations.
The 15-second route p95 gate is unchanged. See the
[plan](../research/04_experiments/2026-09-06-authenticated-loopback-load-plan.md)
for failure accounting, source archive, local-certificate scope and limitations.
A successful contract is not a live load result or a production capacity claim.

### Advisory semantic review and usage integrity

Run the offline evaluator contract checks with:

```bash
uv run pytest -q tests/test_completion_semantic_review.py tests/test_semantic_calibration_v2.py tests/services/test_provider_usage_integrity.py
```

The preserved live review can be reproduced with a fresh output directory using
`uv run python -m scripts.run_completion_semantic_review --execute --calibration-version 2 --output-dir reports/generated/semantic-review-fresh`.
This makes paid external calls on synthetic development evidence only. It gates
88 frozen response reviews behind 32 calibration controls repeated twice.
Despite passing calibration, the recorded reviewer missed important teaching
violations on actual outputs. It is **not an accepted accuracy scorer**; see the
[transfer-validity decision](../research/05_evaluation/completion-semantic-review-development-001-live-002-results.md).
The [human review packet](../research/05_evaluation/professor-review-quality-audit-20260906/README.md)
is prepared but has not been rated by a human.

### Paired pedagogy development

`run_paired_pedagogy_development` compares explicit v4/v5 persistent-runtime arms
using a versioned synthetic packet. It sends only course-filtered public source,
profile and fixed student-turn inputs to the runtime; gold criteria remain
outside provider inputs. Fresh arm histories, actual restarts, full responses,
provider ledgers and a source ZIP are retained. Semantic review remains separate.

```bash
uv run python -m scripts.run_paired_pedagogy_development --packet research/05_evaluation/datasets/meaningful-continuation-development-v2.json --output-dir reports/generated/paired-pedagogy-contract-fresh
```

The default contract transport deliberately exercises provider failure handling;
for a useful successful contract use the injected test transport. Add `--live`
only for the parent-approved frozen development packet, with the provider key in
the process environment. The finite bound is800calls/USD20, Luna3000outputtokens,
four independent histories; a packet whose prospective three-calls-per-turn bound
exceeds this is rejected. Do not use the sealed confirmation packet until the
candidate is frozen and that dispatch is explicitly approved. This measures the
persistent service boundary, not authenticated HTTP, deployment or human learning.

The paired pedagogy runner preserves `--candidate v5` as its default historical
reproduction. Use `--candidate v6` only for the prospectively documented successor
comparison; it retains the v4 control and verifies the actual implementation ID
both initially and after restart. The development-v2 packet is openly reused,
not a fresh confirmation set. Model/cap/limits remain identical in both arms.
Neither candidate becomes the product default through this command.

For the separately authorized boundary sidecar, use the same runner with
`--candidate v6` and
`research/05_evaluation/datasets/boundary-classification-development-v1.json`.
Set CLI options `--maximum-calls 80 --maximum-cost-usd 2`; the sidecar's eight contexts remain separate from the main
48-context denominator. Its prospective plan is
[here](../research/04_experiments/2026-09-06-boundary-classification-sidecar-plan.md).

To classify a preserved v5 pedagogy run without provider calls, use
`uv run python -m scripts.diagnose_instructional_rendering <raw-run-directory> --output <new-audit.json>`.
The helper opens archived runtime SQLite files read-only, replays recorded
proposals through local rendering/graph checks, and checks live-run source hashes.
Run it against the matching preserved v5 source revision; a later revision may
report a source mismatch and must not be described as exact frozen replay.

Use `--candidate v7` for the prospectively authorized request-coverage successor;
`v5` remains the default and `v6` remains reproducible. The mixed-stage sidecar
uses `research/05_evaluation/datasets/mixed-evidence-stage-development-v1.json`
with `--maximum-calls 120 --maximum-cost-usd 3`. Its24 paired turns remain separate
from both the main48 contexts and the boundary8 contexts. Confirmation stays
closed until all relevant development gates pass; the narrower development rubric
does not replace the project's factual/profile and boundary completion thresholds.

When invoked with `--packet`, the runner verifies the file's parsed content against
the supplied packet, archives its original bytes, and snapshots adjacent
`source-lineage.json` and `build_packet.py` when present. Their byte hashes and
end-of-run consistency are recorded separately from the canonical packet hash.
These are provenance artifacts only; the builder is never executed by the runner.
For permission-approved real-course inputs, keep the output directory ignored.
Durable summaries must contain sanitized IDs/hashes and metrics, not the private
packet, source cards, questions, or manifest schedule text.

### Explicit compact tutoring candidate

The shared `experimental_tutoring_configuration("v8")` selector fixes Luna,
3,000 output tokens, low reasoning effort, and the standalone compact response
contract with V4 policy/referent admission. It does not enable the V5–V7
instructional contracts or change a selected/default release. V4–V7 remain
available for reproduction through the paired runner.

```bash
uv run python -m scripts.run_paired_pedagogy_development --candidate v8 --packet research/05_evaluation/datasets/meaningful-continuation-development-v2.json --output-dir reports/generated/FRESH_CONTRACT_ID
uv run python -m scripts.run_authenticated_loopback_load_development --contract --candidate v8 --output-dir reports/generated/FRESH_HTTPS_CONTRACT_ID
```

The paired CLI's default transport is a failure fixture; use the injected test
fixture for the source-bound orchestration contract. Paid execution additionally
requires the existing exact bounded authorization, configured provider credential,
a prospective run plan, and `--live` (paired) or `--execute` (HTTPS). The HTTPS
candidate selector preserves historical runs without a selector at their original
1,500-token configuration. Its isolated server verifies the actual constructed
implementation ID, and the manifest records the complete selector.

The existing operational `run_history(..., candidate="v8")` also accepts this
selector. Its caller must supply a `RecordedRunClient` with Luna and a matching
3,000-token serializer; mismatches fail before runtime creation. The optional
parameter leaves historical V2 schedules unchanged. This is a reusable execution
configuration, not evidence of autonomy utility or release qualification. A new
candidate-specific cohort still needs its own prospective schedule and result.

### Profile-authoritative compact candidate

V9 preserves the compact V8 output contract and applies approved profile
instructions ahead of advisory planning hints. Select it explicitly with
`--candidate v9` in the paired or authenticated HTTPS evaluator. Both use the
same shared configuration and retain the V4 control and historical candidates.
The three development packets and all previous outcomes remain unchanged.

For a usable local application, run `VITE_API_BASE_URL='' VITE_AUTH_MODE=session npm run build:web` once. The separate ASGI factory serves that existing built UI and API at the same HTTPS origin and uses the existing
staging database, credential authentication, source/publication controls, and
base T1 qualification configuration. Configure those existing staging settings
and the provider credential first; the candidate selector replaces the need to
set individual instructional flags. With the existing local TLS certificate:

```bash
APP_EXPERIMENTAL_TUTORING_CANDIDATE=v9 uv run uvicorn services.api.app.experimental:create_experimental_app --factory --host 127.0.0.1 --port 8018 --ssl-keyfile /absolute/path/localhost.key --ssl-certfile /absolute/path/localhost.crt
```

The configured HTTPS allowed origin must match `https://127.0.0.1:8018`; open that address in the browser. Startup verifies the inspectable `build-configuration.json` marker and refuses a demo-auth bundle. Known student/professor deep links serve the same index; unknown API and asset paths remain 404. The built UI uses the same origin for API requests, so no Vite proxy change is needed. The factory
rejects demo authentication, missing candidate selection, incompatible base
qualification, and actual implementation mismatch. It fixes Luna, low reasoning,
3,000 output tokens, and bounded provider concurrency of five; existing process
call/cost limits still apply. Inspect
`app.state.experimental_tutoring_configuration` for the actual identity and
settings. This does not change the default ASGI entrypoint, bootstrap accounts,
approve or publish sources, or qualify the candidate for production. The
experimental evidence profile is recorded separately after evaluation.

### Eight-history instructional operating comparison

`uv run python -m scripts.run_instructional_operational_comparison --output reports/generated/instructional-operating-contract-new` runs the bounded injected failure contract for exactly V4/V9 × two personas × reactive/autonomous conditions. Add `--live` only after the candidate quality decision and prospective execution clearance. Both arms use the explicit 3000-token model configuration; the cumulative bounds are 2500 calls/USD62.50 per arm. This records 30 accelerated virtual days, durable restart equality, consent intervals, actual lineage and every provider failure; it does not measure human learning or establish intervention utility. See `research/04_experiments/2026-09-06-final-candidate-eight-history-operational-plan.md`.

The experimental local entrypoint requires these existing staging modes explicitly:

```dotenv
APP_MODE=staging
APP_STUDENT_TUTORING_MODE=governed-autonomous-tutoring-graph-v2.1
APP_AUTONOMY_PLANNER_MODE=openai-gpt-5.6-luna-policy-value
APP_EVIDENCE_GATE_MODE=dominance-scoped-ambiguity-safe-v3
APP_GENERATOR_MODE=deterministic
```

Retain the configured absolute database/data paths, secure cookies, HMAC secret,
base student profile and matching T1 qualification record from the staging setup.
The factory rejects mismatches rather than silently replacing these settings.
Only the explicit instructional selector is new; the base qualification remains
separate from the candidate's semantic evidence.

### Final instructional profile-context comparison

`uv run python -m scripts.run_teaching_profile_responsiveness_development --contract-smoke --candidate v10 --maximum-calls 100 --maximum-cost-usd 3 --output-dir reports/generated/profile-context-v10-contract-new`
keeps the existing24-case packet and compares explicit approved-context handling
off/on with the V10 composition. Replace `--contract-smoke` with `--execute`
only after its development decision and prospective clearance. The model's
actual input binding, all delivered responses and source snapshot are retained;
old intent scores are descriptive. The unchanged default runner remains the
historical500-token configuration. See the
[prospective content criteria](../research/04_experiments/2026-09-06-v10-profile-responsiveness-plan.md).

### Typed compact V10 comparison

Use explicit `--candidate v10` in the paired and authenticated HTTPS evaluators,
or `APP_EXPERIMENTAL_TUTORING_CANDIDATE=v10` with the same validated local ASGI
startup above. V10 keeps a distinct typed factual-unit schema and initial-turn
clarification admission; V9 remains available unchanged. The operational wrapper
also accepts `--candidate v10`; its omitted-argument default remains V9 to preserve
historical commands. The V10 boundary packet runs before main development to
qualify actual provider acceptance of the new schema. This sequence and the
unchanged gates are documented in the V10 prospective plan; no default release
or qualification claim follows from selecting a version.

`APP_GENERATOR_MODE=deterministic` configures the inherited base/fallback
component; it does **not** describe the explicit experimental instructional
generator. The V9/V10 composition constructs Luna through the shared, bounded
provider transport and verifies the actual `question-specific-profile-grounded-v9`
or `question-specific-profile-grounded-v10` implementation. The observed runtime
ID and provider ledger distinguish these live calls from deterministic fixtures.
The legacy setting remains visible so it is not mistaken for evidence that the
experimental tutor avoided the external LLM.

### Match an experimental API with its autonomy worker

The worker now uses the same experimental builder when `APP_EXPERIMENTAL_TUTORING_CANDIDATE` is explicitly exported. With no selector it retains its incumbent composition. Supply the same staging settings, database path, credentials and explicit selector to both processes; a separate worker does not inherit another process's environment. The API's local `.env` loader does not export settings to the worker shell.

```sh
APP_EXPERIMENTAL_TUTORING_CANDIDATE=v10 APP_PROACTIVE_OUTREACH_WORKER_ENABLED=true uv run python -m scripts.autonomous_tutoring_worker --once --batch-size 1
```

The command processes at most one due governed opportunity and one scheduled outreach batch; it does not wait or poll indefinitely. The shared selector also defines explicit model variants when available; use precisely the same alias for API and worker. Worker composition sets `serve_web=False`, preserves staging/worker-enabled checks and rejects incompatible selector settings. Model budgets remain per process, not a shared API-plus-worker global budget. Do not infer pedagogical qualification from matching configuration. Design and injected verification are in [the worker composition plan](../research/04_experiments/2026-09-06-experimental-worker-composition-plan.md).

The operational output audit now counts outreach replies using the actual top-level delivered-message link on `proactive-reply` turns. The prior V10 run's unmodified raw zero count and separately verified two replies are retained in [its result and erratum](../research/05_evaluation/instructional-eight-history-operational-development-001-v10-live-001.md).

For the prospectively accepted V10 generator variant, the same responsiveness
runner accepts `--candidate v10-luna-low`, `v10-luna-medium`, or `v10-sol-low`.
Use `--maximum-calls 100 --maximum-cost-usd 20`; role-separated runs require
USD16..20 to cover conservative fixed allocations. Planner calls remain Luna-low;
the chosen alias applies only to typed V10 generation. Separate role ledgers
preserve actual request model/reasoning, and one shared outer budget spans all
24 isolated cases. Run an injected contract before an authorized `--execute` run.
These are repeated development comparisons under the
[prospective profile plan](../research/04_experiments/2026-09-06-v10-profile-responsiveness-plan.md),
not fresh confirmation or a human-instructor evaluation.

### Generation-only model and reasoning comparison

`run_generation_role_model_comparison.py` compares explicit `v10-luna-low`,
`v10-luna-medium`, and `v10-sol-low` variants with the identical V10 prompt,
schema, source handling and 3,000-token cap. Planner tasks remain Luna-low.
These are experimental configurations; none changes the selected release.

```sh
uv run python -m scripts.run_generation_role_model_comparison \
  --packet reports/generated/fresh-attribution-protocol-v1/entity-implication-development-v2.json \
  --output-dir reports/generated/generation-role-model-development-001-contract-001
```

The CLI without `--live` deliberately uses a failure fixture; positive named
contracts use the injected `RoleFixture` from the runner's tests. An authorized
live run adds `--live` with the existing provider credential in the environment.
Each new run needs an exclusive output directory. The runner archives only the
specified packet, never sibling authoring builders or sealed confirmation. The
three-arm global ceiling is 500 calls/USD100: each arm receives a fixed third,
and each role half of that allocation. Unused role allowance is not pooled.
All role-specific provider ledgers, actual identities, reasoning settings,
source hashes, costs and failures remain inspectable.

For the prospectively declared evidence-strength experiment, select only the new
prompt with `--candidates v11-luna-low --maximum-calls 200
--maximum-cost-usd 32` (the other required arguments remain as above). Explicit
selection accepts one to three distinct declared candidates; budgets are divided
by the actual number of arms and then by role. Omitting `--candidates` retains
the original three V10 variants. V11 keeps the typed schema/task but records a
distinct implementation and prompt ID. See the
[evidence-strength plan](../research/04_experiments/2026-09-06-evidence-strength-generation-plan.md).

The same aliases can be passed to `APP_EXPERIMENTAL_TUTORING_CANDIDATE` for the
separate authenticated application entrypoint documented above. For a session
UI build, explicitly use `VITE_API_BASE_URL='' VITE_AUTH_MODE=session npm run
build:web`. The application uses one shared provider semaphore of five within
its process; API and worker processes do not share a distributed budget.
Catalogued Sol is enabled only by the explicit experimental transport opt-in;
ordinary release-mode constructors remain unchanged.

The authenticated loopback runner also accepts the three aliases. Variant-only
bounds are 800 calls/USD128, divided into two 400-call/USD64 role ledgers;
historical candidates retain 300 calls/USD10. The original six-burst schedule
and 15-second p95 gate are unchanged. Paid timing trials require quality
acceptance and a quiet host; injected HTTPS contracts establish authentication,
configuration and persistence, not semantic quality or provider performance.

Explicit generator-role operating comparisons accept `--candidate v10-luna-low`, `v10-luna-medium` or `v10-sol-low`; all keep Luna-low planning and the same V10 instructional algorithm. They use separate recorded role ledgers and verify actual role/model bindings before and after restart. These aliases have prospective conservative ceilings of 9,600 calls/USD 1,536 across eight histories (effective inner call ceiling 4,800), not the historical V9/V10 5,000-call/USD 125 ceilings. The [plan amendment](../research/04_experiments/2026-09-06-final-candidate-eight-history-operational-plan.md) explains fixed role partitions and retains prior results. Run the injected contract first; no alias is semantically qualified by its presence in the CLI.

For subsequent V4-versus-variant development or confirmation, the existing
`run_paired_pedagogy_development.py` accepts the same aliases. Explicitly supply
the amended bounds: main/confirmation `--maximum-calls 800
--maximum-cost-usd 128`, boundary `80/12.8`, and mixed-stage `120/19.2`.
Historical version defaults remain unchanged. The default input archive includes
only the specified packet. Only for an explicitly approved provenance scope,
repeat `--input-provenance /absolute/path/to/artifact` for each reviewed lineage
or reconstruction file; sibling builders are never discovered automatically.
A real-course run still requires its separate model-specific provider disclosure
and budget decision before transfer.

The explicitly experimental `v11-luna-low` alias uses V11 evidence-strength
instructions with the same typed JSON contract, Luna-low model roles and
3,000-token generation cap. It is available to the paired comparison,
authenticated HTTPS and eight-history operating runners through `--candidate
v11-luna-low`, and to the separate API/worker through
`APP_EXPERIMENTAL_TUTORING_CANDIDATE=v11-luna-low`. Historical aliases and defaults
remain reproducible. This option is not a release selection or semantic
qualification; see the [prospective V11 plan](../research/04_experiments/2026-09-06-evidence-strength-generation-plan.md).

For the synthetic boundary comparison use the paired runner with
`--maximum-calls 80 --maximum-cost-usd 12.8`; the mixed-stage packet uses
`--maximum-calls 120 --maximum-cost-usd 19.2`. Main trials use800 calls/USD128.
The versioned packet, source snapshot, actual implementation ID and role ledgers
must match each named run. Operational and HTTPS provider execution remains
conditional on the prospective quality gates; injected contracts alone do not
satisfy them.

### Independent factual revision controls (experimental V12)

`v12-luna-sol` retains Luna-low planning and drafting, then performs one separate
Sol-low revision. All roles use3,000-token caps and exact task/model ledgers;
unknown usage stops subsequent admission. The final answer identifies Sol while
draft metadata remains Luna. Source IDs are associations, not semantic approval.
V10/V11 and application defaults remain unchanged.

Stage A uses the actual revision helper and shared server composer on64 authored
synthetic controls. It sends public inputs and draft only; adequacy/gold labels
are withheld. After the prospective packet and source freeze are approved, run:

```sh
PYTHONPATH=. uv run python scripts/run_factual_revision_controls.py \
  --packet reports/generated/revision-controls-v1/packet.json \
  --output-dir reports/generated/independent-factual-revision-controls-001-live-001 \
  --input-provenance reports/generated/revision-controls-v1/preflight-seal.json \
  --input-provenance research/05_evaluation/independent-factual-revision-controls-preflight-review.md \
  --execute
```

The fixed limit is64 calls/USD10.24, one pass per control with no retries.
Original and revised rendered answers, proposals, source links, local guards and
provider failures are retained. Stage B requires semantic acceptance of Stage A.
It uses the paired runner with `--candidate v12-luna-sol`: main1,200 calls/USD192,
boundary120/USD19.20, mixed180/USD28.80. Short diagnostics use
`--candidates v12-luna-sol --maximum-calls 200 --maximum-cost-usd 32`; profile
comparisons use `--candidate v12-luna-sol --maximum-calls 150
--maximum-cost-usd 30`. Three-role partitions and up to five calls per tutoring
turn replace the old two-role/three-call estimate only for V12. Subsequent
HTTPS uses1,200/USD192; eight-history operations retain their9,600/USD1,536 total
ceiling, with the candidate arm split three ways. These are conditional
experimental commands, not a release or deployment qualification.

The V13 controls use `run_factual_revision_controls.py --candidate v13` with the
new independently reviewed80-entry packet and explicit preflight/seal provenance.
V12 remains the default64-entry/64-call contract. V13 permits exactly80 revision
calls / USD12.80 and uses the actual restricted revision task for draft actions
covered by the disclosure ceiling; other drafts retain the V12 revision helper.
Both original and revised server-rendered answers remain review artifacts.

For later conditional integrated experiments, `v13-luna-sol` is an explicit
API/worker and paired/operational/HTTPS selection. It retains V12's three roles,
model/cap settings and five-call-per-turn budgets. Its presence in the selector
is not Stage A acceptance or a release selection. See the
[bounded revision plan](../research/04_experiments/2026-09-06-bounded-revision-plan.md).

### Conditional revision V14 plumbing

The preregistered effort comparison adds `--candidate v14-medium` to the direct
component command below. It uses the same112 frozen controls and V14 helper,
changing only Sol revision reasoning to medium. Run each of the two planned
trials in a distinct new output directory; do not overwrite or retry an
unfavourable result. Each trial is bounded at112 calls / USD17.92, cap3000 and
concurrency1. The matching runtime alias is `v14-luna-sol-medium`; this alias
does not imply semantic acceptance. See the
[effort plan](../research/04_experiments/2026-09-06-conditional-revision-effort-plan.md).

The explicit `v14-luna-sol` alias uses Luna-low planning and drafting plus one
Sol-low conditional keep/repair assessment, all with a 3,000-token output cap.
A kept answer retains Luna as its content provider; a replacement identifies Sol.
Both calls remain observable and charged. Existing versions remain reproducible.
The wrapper's diagnosis and proposed move are model judgments, not correctness
certificates.

The paired runner accepts this alias for the same openly reused development
packets: main `--maximum-calls 1200 --maximum-cost-usd 192`, boundary 120 / 19.2,
and mixed-stage 180 / 28.8. The five-call worst-case turn allowance and three-role
reservations remain unchanged. The authenticated loopback runner also accepts
this alias with its 1,200-call / USD 192 envelope. The eight-history operational
wrapper retains 4,800 calls / USD 768 **per arm** (three equal role partitions).
These are executable configurations, not permission to bypass the prerequisite
Stage A semantic gates or evidence that integrated V14 runs have occurred. The
conditional-revision prospective plan is included in each runner's source archive.

The V14 Stage A component command is:

```bash
PYTHONPATH=. uv run python scripts/run_factual_revision_controls.py \
  --candidate v14 \
  --packet reports/generated/conditional-revision-controls-v1/combined-packet.json \
  --output-dir reports/generated/independent-factual-revision-controls-001-v14-live-001 \
  --execute
```

Use the final reviewed packet and explicit preflight/seal `--input-provenance`
paths when recording the named run. This makes exactly 112 bounded Sol assessment
calls, at most USD 17.92 reserved, with no draft-generation calls: drafts are
researcher-authored controls. A KEEP result therefore retains researcher-authored
origin in this component trial, not a fictional Luna call. Judge the actual
rendered answer separately from disposition/fault diagnostics. Stage B remains
conditional on all prospectively frozen semantic gates; V12 and V13 commands
and failed records are preserved.

### Source–oracle alignment packets

`uv run python -m scripts.build_main_oracle_alignment` materializes the exposed
v3 complete-procedure packet and the eight original-source necessity controls.
It refuses to overwrite either artifact. Use
`uv run python -m scripts.build_main_oracle_alignment --check` to verify their
reproducibility. The v2 packet remains unchanged; see
`research/04_experiments/2026-09-06-main-oracle-alignment-plan.md` for gates and
why historical main accuracy is not factual qualification evidence.

### Fresh fixed-candidate assessment analysis

`analyze_fresh_assessment_comparison.py` validates complete112-control manual
reviews against frozen live packets, reports every adequacy/family/action slice,
and resamples56scenario pairs within families (seed8801;10000draws). It does not
call a provider or infer semantic labels from model dispositions. Critical and
uncertain judgments cannot count as useful; output paths must be new.

```sh
.venv/bin/python -m scripts.analyze_fresh_assessment_comparison --packet research/05_evaluation/datasets/fresh-assessment-generalization-development-v1.json --baseline-dir reports/generated/independent-factual-revision-controls-001-fresh-v14-medium-live-001 --candidate-dir reports/generated/independent-factual-revision-controls-001-fresh-v16-live-001 --baseline-review research/05_evaluation/independent-factual-revision-controls-001-fresh-v14-medium-live-001-assistant-review.json --candidate-review research/05_evaluation/independent-factual-revision-controls-001-fresh-v16-live-001-assistant-review.json --output /tmp/fresh-assessment-reproduction.json
```

The fresh comparison failed; V16 is not integrated or selected. See
`research/05_evaluation/fresh-assessment-generalization-comparison-001-results.md`.

### Final-response verification component study

`run_final_response_support_audit.py` replays fixed responses (C0), compares a
source-only audit (C1) with a quality audit plus one issue-guided repair and final
reaudit (C2). An unchanged rejected repair or failed final audit is quarantined;
no rewritten response bypasses the final check. This is experimental component
code, with no product selector or release-profile change.

Live inputs must match the reviewed bank and explicitly supplied SHA-256:
112exposed responses or128fresh authored controls. The latter have64adequate and
64defective originals byconstruction, not128actualV16generations. Four inputs may
run concurrently; banks run sequentially so the aggregate concurrency stays four.
The shared cap is4calls/USD0.64perinput, with C1<=1 and C2<=3. Audit usesSol-high,
repair Sol-medium, cap3000. The actual serialized request must fit20,000UTF-8bytes
and the conservativeUSD0.16reservation. Unknown cost or contract/provider failure
stops further admissions; already admitted requests remain recorded.

```sh
.venv/bin/python -m scripts.run_final_response_support_audit --bank exposed --packet reports/generated/final-response-support-audit-v1/exposed-packet.json --expected-packet-sha256 7386fe29e2cfa42e95b49d71d127347d42c994f892fe13fa7df09ecbabae26d6 --output-dir reports/generated/final-response-support-audit-001-exposed-live-001 --input-provenance research/04_experiments/2026-09-06-final-response-support-audit-plan.md --input-provenance reports/generated/final-response-support-audit-v1/bank-preflight.json --concurrency 4 --execute
.venv/bin/python -m scripts.run_final_response_support_audit --bank fresh --packet reports/generated/final-response-support-audit-v1/fresh-packet.json --expected-packet-sha256 5b66327006390857f58e064ee0488ba587025704efc57fc78f8d3da2e270f5c9 --output-dir reports/generated/final-response-support-audit-001-fresh-live-001 --input-provenance research/04_experiments/2026-09-06-final-response-support-audit-plan.md --input-provenance reports/generated/final-response-support-audit-v1/bank-preflight.json --concurrency 4 --execute
```

The v1 commands above describe the original planned protocol; its exposed run
stopped and its fresh bank was not executed. Do not automatically run that later bank.
The explicitly selected `--variant v2` refinement uses program
`final-response-support-audit-002`, distinct provider task IDs, unchanged model/cap
and schema limits, and the same frozen packets. It requires the source/serializer
preflight and exposed screening gates in
`research/04_experiments/2026-09-06-final-response-audit-contract-policy-refinement-plan.md`
before any fresh-bank calls. Omitting the variant retains v1.

These commands require configured credentials and completed source/serializer
preflight. Keep credentials out of the source/input archives. The runner archives
exact inputs, source bytes, request/response usage, per-arm latency and outcomes;
independent final-text review is still required. Model acceptance is never the
semantic score. Output directories cannot be overwritten. The complete review and
fresh preservation/correction gates are in the corresponding experiment plan.

`analyze_final_response_audit.py` validates a completed run archive and independent
manual judgments before calculating C0/C1/C2 coverage, critical errors, operational
failures, cost and latency. Review JSON must bind `packet_sha256` and
`cases_sha256`, and include every planned ID with C0/C1/C2 boolean `useful`,
`critical`, `uncertain` and a `reason`. Separate support annotations use
`factual_support_defect` (`true`, `false` or `null`); policy failures do not
implicitly become factual defects. Unknown support labels remain explicit with
conservative precision/recall sensitivities.

```sh
.venv/bin/python -m scripts.analyze_final_response_audit --run-dir reports/generated/final-response-support-audit-001-exposed-live-001 --review reports/generated/final-response-support-audit-v1/exposed-assistant-review.json --support-labels reports/generated/final-response-support-audit-v1/baseline-support-labels.json --output /tmp/final-response-audit-exposed-reproduction.json
```

The reader checks exact IDs, source archive and output hashes, provider ledgers,
original and delivered proposals, rendering and final audit bindings. Blocked,
quarantined and uncertain cases remain in the planned denominator. Bootstrap
comparisons resample whole scenario pairs within families (seed8801,10,000draws).
Exposed results cannot authorize promotion; fresh gates require61/64 in each
adequacy group,30/32 per family, zero criticals and the recorded operational
conditions. Stopped-run intervals describe combined operational and semantic
outcomes, not completed model-quality trials. Output files cannot be overwritten.

## Goal completion scope regression

`run_goal_completion_scope.py` runs the prospective 72-history, 30-day synthetic
goal-scope contract using the real product adapter. It archives code/configuration,
refuses existing output directories and forbids external sockets during product
execution. Select the matching source archive before running an arm:

```bash
uv run --locked python -m scripts.run_goal_completion_scope --arm baseline --output-dir reports/generated/goal-scope-baseline-rerun
uv run --locked python -m scripts.run_goal_completion_scope --arm candidate --output-dir reports/generated/goal-scope-candidate-rerun
uv run --locked python -m scripts.analyze_goal_completion_scope --baseline reports/generated/goal-completion-scope-development-001-baseline --candidate reports/generated/goal-completion-scope-development-001-candidate --output reports/generated/goal-scope-comparison-rerun.json
uv run --locked pytest -q tests/digital_twin/test_goal_completion_scope.py tests/test_goal_completion_scope_evaluation.py tests/digital_twin/test_governed_autonomy.py
```

The baseline requires archived v1 code; it intentionally fails the new correctness
gate. Rerun output names must be new and any decision-bearing rerun must be separately
registered. Six exposed 025 concept cards and seeds 9101–9103 form a development
regression dataset, not held-out quality evidence. Dependency imports may attempt
public pricing-metadata discovery and fall back locally; no external LLM is used.
See the [design and results](../research/05_evaluation/goal-completion-scope-development-001-results.md).
