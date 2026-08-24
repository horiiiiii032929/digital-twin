# Evidence-sufficiency candidate comparison 001 build

## Decision

**Go Deeper.** The corrected 120-case decision package and exact candidate
comparison are ready for one separately authorized local execution. The split
remains unopened and no evidence-sufficiency method is selected.

## Frozen design

- Implementation revision: `1c6843417b80facadd4ad0d514394a95af358027`
- Dataset: `evidence-sufficiency-v2-decision-draft-002`, 120 synthetic-public
  cases, frozen at content SHA-256
  `ae367ed195a97e5144667f4936c799edcc64991a96ffbebeb505497ffc58c9df`
- Fixed input: course-scoped active/approved BM25 top five, with no gold
  evidence injection
- Unsafe control: AnyHit, explicitly unselectable
- Selectable methods: inspectable deterministic features; GTE ModernBERT
  cross-encoder support; GTE support plus pairwise DeBERTa NLI contradiction
  checks
- Decision authority: the deterministic calibrated gate; model scores cannot
  create citations or own the final answer/abstain policy

Official Hugging Face metadata was checked on 2026-08-24. The support model is
`Alibaba-NLP/gte-reranker-modernbert-base` at revision
`f7481e6055501a30fb19d090657df9ec1f79ab2c` (149,605,633 parameters), and the
NLI model is `cross-encoder/nli-deberta-v3-base` at revision
`6c749ce3425cd33b46d187e45b92bbf96ee12ec7` (184,424,963 parameters). Both are
recorded as Apache-2.0. These bindings are prospective; model-card results are
not project evidence.

## Verification

- Network-free simulation passed without loading a model or opening the split.
- No-call preflight reports `blocked-not-authorized` only for candidate,
  local-model, and decision-split authority.
- Repository freeze covers the runner for local-model and method execution:
  65/65 protected entrypoints, zero missing guards.
- Correctness inventory: 510/510 audited, zero pending findings.
- Complete local gate: 839 Python tests and 46 frontend tests passed; frontend
  lint and production build passed.
- Provider calls, paid cost, private data, and held-out access: zero.

## Stop boundary

Do not download or run the bound models and do not open the 120 cases until a
separate authorization checkpoint changes only this instrument and its bounded
freeze entry. After execution, audit at most 12 prioritized failures or
ambiguities, register `Keep`, `Refine`, or `invalid-execution`, revoke the
authorization, and do not start another prompt/model-search loop.
