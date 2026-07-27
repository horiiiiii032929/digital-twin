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
