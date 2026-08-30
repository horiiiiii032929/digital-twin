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
  Validation, simulation, and preflight are network-free; execute and score
  remain freeze blocked until attempt 002 receives separate authorization.
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
