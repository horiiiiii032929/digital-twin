# Source

Domain and provider-neutral contracts live here. API transport code lives in
`services/`, frontend applications live in `apps/`, research notes live in
`research/`, and implementation-facing documentation lives in `docs/`.

```text
src/digital_twin/
├── grounding/              # Documents, chunks, retrieval, citations, protocols
├── onboarding/             # Session, interview, policy, preview, revision, release
├── onboarding_workflow.py  # Compatibility facade for existing imports
├── tutor_policy.py         # Canonical shared tutor-policy schema
└── llm.py                  # Existing provider-neutral LLM client boundary
```

Production grounding code contains provider-neutral contracts plus the approved
local TXT, Markdown, and PDF parser and deterministic chunker. Synthetic corpus
material belongs in `tests/fixtures/`; provider selection, retrieval, embeddings,
Canvas, persistence, and live generation remain separate delivery tasks.
