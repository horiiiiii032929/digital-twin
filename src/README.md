# Source

Domain and provider-neutral contracts live here. API transport code lives in
`services/`, frontend applications live in `apps/`, research notes live in
`research/`, and implementation-facing documentation lives in `docs/`.

```text
src/digital_twin/
├── evaluation/             # Component evidence records and release profiles
├── grounding/              # Documents, chunks, retrieval, citations, protocols
├── onboarding/             # Session, interview, policy, preview, revision, release
├── onboarding_workflow.py  # Compatibility facade for existing imports
├── tutor_policy.py         # Canonical shared tutor-policy schema
└── llm.py                  # Existing provider-neutral LLM client boundary
```

Production grounding code contains provider-neutral contracts plus the approved
local TXT, Markdown, and PDF parser, deterministic chunker, term-overlap control,
BM25 retriever, and retrieval evaluator. Synthetic corpus material belongs in
`tests/fixtures/`; provider selection, embeddings, Canvas, persistence, and live
generation remain separate delivery tasks.

The evaluation package does not replace component-specific contracts. It
validates how implementations are compared and which versions are selected in a
complete experimental or release profile.
