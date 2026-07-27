# Source

Domain and provider-neutral contracts live here. API transport code lives in
`services/`, frontend applications live in `apps/`, research notes live in
`research/`, and implementation-facing documentation lives in `docs/`.

```text
src/digital_twin/
├── evaluation/             # Component evidence records and release profiles
├── generation/             # Prompt, policy, citation, and generator domain code
├── grounding/              # Documents, chunks, retrieval, citations, protocols
├── onboarding/             # Session, interview, policy, preview, revision, release
├── onboarding_workflow.py  # Active compatibility facade for API/tests
├── tutor_policy.py         # Canonical shared tutor-policy schema
└── llm.py                  # Existing provider-neutral LLM client boundary
```

Production grounding code contains provider-neutral contracts plus the approved
local TXT, Markdown, and PDF parser, deterministic chunker, term-overlap control,
BM25 retriever, grounded-generation control, policy enforcement, citation
validation, and component evaluators. The provider-specific LiteLLM adapter
lives in `services/llm/`; no provider/model is selected or called by default.
Synthetic corpus material belongs in `tests/fixtures/`; provider selection,
embeddings, Canvas, persistence, and paid live evaluation remain separate
delivery tasks.

The evaluation package does not replace component-specific contracts. It
validates how implementations are compared and which versions are selected in a
complete experimental or release profile.

The compatibility facade and shared policy module are not dead code: API,
generation, grounding, scripts, fixtures, and regression tests still import
them. Remove or relocate them only through a dedicated migration that updates
all consumers and preserves compatibility tests.

The locked target architecture will add explicit identity/course-membership,
conversation, publication, and audit/recovery domain packages. Infrastructure
implementations remain in `services/`; do not place provider SDKs or database
clients in this domain package.
