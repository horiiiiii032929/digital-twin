# Non-human evaluation program 002

## Decision

AFQC-101 replaces repeated stage-by-stage user approval with one finite,
program-level authorization. Every public-source or synthetic stage advances
automatically after a passing result. The program stops automatically for a
valid quality failure, a safety/privacy/leakage/identity/accounting failure, a
second invalid execution in one stage, or the USD 50 ceiling.

This does not weaken the evaluation gates. It removes only the administrative
pause that asked the researcher to authorize each already-frozen stage.

## Successor method

AFQC-100 remains valid unfavorable evidence. Cross-review found that 101 of its
235 answerable cases required region identities the runtime corpus did not
carry, and the runtime corpus and gold were bound to different source-plan
hashes. The successor therefore changes the method, not just the model:

1. Register one exact, citable chunk per complete prose or structured region,
   with a source-derived ID shared by runtime retrieval and gold.
2. Add course, section, modality, surrounding source context, and structured
   identifiers only as non-authoritative search metadata.
3. Fail before ranking unless every answerable reference is exactly matchable.
4. Require context-complete questions. A model may author wording but cannot
   alter actions, answers, claims, evidence, or lineage.
5. Confirm the method on a source-family-disjoint 500-case tranche before
   opening the 500+100 actual-product or sealed 10,000+1,000 stages.

## Agent-assisted review

The panel is hierarchical rather than a majority vote:

- D0 deterministic graders are authoritative for source, action, claim,
  citation, version, policy, persistence, and budget facts.
- GPT-5.4 nano flags semantic concerns cheaply.
- GPT-5.6 Terra reviews conflicts and a frozen passing sample.
- A fresh Codex audit proposes `product-defect`, `benchmark-defect`,
  `rubric-ambiguous`, `harness-defect`, or `no-material-concern` dispositions.

Agreement between OpenAI-family models is corroboration, not independent human
ground truth. Unresolved cases remain non-passes. Benchmark or rubric changes
still require a researcher/professor decision and cannot silently change a
sealed result.

## Human boundary

No real professor or student is enrolled, messaged, observed, or evaluated by
this program. Professor-profile approval, external usability, and learning
outcome claims remain the first human-gated stage after the autonomous package.
