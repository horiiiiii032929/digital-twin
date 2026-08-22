# Evidence-sufficiency v2 independent-review 007 build result

## Decision

**Go Deeper with one provider-unauthorized resilient review; do not retry or
reinterpret invalid review 006.**

Review 006 failed before a provider response and spent USD 0, so its USD 0.50
ceiling was not the cause. Review 007 makes one operational method correction:
it keeps the same GPT-5.4 mini model and dated backend contract, removes
nonessential reasoning and seed parameters, and permits OpenRouter to route the
same model through compatible OpenAI or Azure capacity. Strict JSON Schema,
deterministic source truth, sensitivity-first stopping, zero retries, and all
downstream decision locks remain unchanged.

## Prospective binding

- Implementation revision: `3685697247fa2d75a277b621b4492033e5eb5903`
- Instrument: `evidence-sufficiency-v2-independent-review-007`
- Instrument SHA-256:
  `8834d028b308a135cc8a6380d3d1e4088f28282afa4940d65c968fbcf4a0786f`
- Review-packet SHA-256:
  `a6cdda77cb824cc620577cc1fcab23ec17166fa78ba525faaf3ff811b062eed7`
- Runner SHA-256:
  `ff2b016f8a3aa6e9286ddab1053ac2ed25e0487e25bdb5fca4333a1d55ae9d87`
- Network-free simulation SHA-256:
  `37addee0c351bb1ee0fda879ac72cb227bf922a5ea45d1e3e7708f770ecda034`
- Provider/model inference calls: zero
- Private or held-out data read: zero

The requested model remains `openai/gpt-5.4-mini`, with dated backend identity
`openai/gpt-5.4-mini-20260317`. Routing orders OpenAI before Azure, allows
same-model fallback, requires requested parameter support, and forbids model
fallback. Temperature, reasoning effort, and seed are omitted. Provider data
collection is allowed only for the synthetic-public packet.

## Bounds

- Unchanged synthetic-public 120-case draft and 12 sensitivity controls.
- One sensitivity-first call followed, only on success, by 12 review batches.
- Maximum 13 calls and zero retries.
- USD 0.858 worst-case reservation under a USD 1.50 emergency ceiling.
- The reviewer remains advisory and cannot modify deterministic source truth.
- Provider execution, private inputs, candidate evaluation, dataset freezing,
  component selection, and release promotion remain unauthorized.

## Verification

- Network-free simulation: 13/13 calls and 132/132 judgments completed.
- Simulated clean specificity, defect detection, and review coverage: 100%.
- Complete repository gate: 804 Python tests and 46 frontend tests passed,
  together with documentation, freeze, inventory, lint, and production build.
- Repository correctness inventory: 491/491 audited.
- Execution freeze: 61/61 protected entrypoints; zero external execution.

## Live no-call preflight

The clean metadata-only preflight found the credential, fresh model and
endpoint metadata, compatible OpenAI and Azure routes, an unused output path,
and no identity or pricing mismatch. It stopped on exactly the three intended
locks:

1. `provider-review-not-authorized`;
2. `instrument-not-frozen`;
3. `bounded-freeze-authorization-missing`.

## Limitation and next gate

This proves build readiness, not reviewer quality or live route stability. A
separate checkpoint must refresh metadata, freeze and allowlist only review
007, and record explicit paid-run authorization before the first inference
call. The USD 1.50 limit is an emergency stop rather than a quality criterion.

