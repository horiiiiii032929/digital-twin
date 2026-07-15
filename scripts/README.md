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
  or cost; run it with `npm run verify:generation`.
- `synthetic_course_corpus.py`: shares the approved synthetic source, PDF, and
  chunk builders used by ingestion and retrieval verification.
- `validate_component_profile.py`: validates the complete component inventory,
  selection status, evidence paths, and linked evaluation decisions; run it
  with `npm run verify:profile`.
