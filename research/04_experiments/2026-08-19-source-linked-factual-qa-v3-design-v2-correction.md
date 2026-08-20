# Source-linked factual QA v3 design v2 correction

Date: 2026-08-19

Supersedes: `factual-qa-v3-design-001` for prospective execution

Status: frozen for repository-correctness preflight; all model, provider,
dataset-generation, and held-out execution remains unauthorized

## Correction trigger

The v1 design required complete semantic source disposition before any model
execution while its preferred disposition method required model-assisted review
of ambiguous private sources. That ordering was circular. The first semantic
triage also treated course path and format as sufficient to finalize 253
supporting-context labels and 179 integrity exclusions. Path and format are
routing features, not content-level eligibility evidence.

The original design and `factual-qa-v3-semantic-role-triage-v1` result remain
historical evidence. They are not rewritten or treated as execution authority.

## Corrected ordering

The pipeline now separates three boundaries:

1. **Pre-semantic-review governance.** Complete physical accounting, conversion
   lineage, deterministic mandatory-exclusion prefiltering, private payload
   sanitation, synthetic reviewer sensitivity, the repository correctness
   freeze, and a specific provider/cost record must pass first.
2. **Bounded semantic governance review.** A local cross-family first pass and a
   separately authorized dispute reviewer may classify only the eligible private
   review packet. Reviewers are blinded to one another. Models cannot establish
   authority, clear privacy alone, or become ground truth.
3. **Pre-generation validation.** Complete content-level dispositions, oracle
   mechanics, response and citation contracts, deduplication, mutation
   sensitivity, and sanitized audit rendering must pass before factual-QA
   generation.

This removes the circular dependency without weakening the privacy boundary.
No model review is authorized merely because this ordering is frozen.

## Source-role correction

Only exact hashes with approved official provenance may be promoted to
`authoritative_evidence` deterministically. Course-scoped files, converted
uncommon formats, and assessment-path artifacts remain
`review_or_conversion_required` until content-level review. Existing explicit
duplicate, generated, sensitive, empty, and unrelated exclusions remain intact.

The corrected no-model triage therefore prioritizes false-negative containment
and complete eligibility over reducing reviewer workload.

## Evaluation validity

Cross-model agreement is a screening signal. It is never the factual reference.
The semantic protocol requires deterministic sensitivity probes, a stratified
human calibration sample, human review of all disagreements, a sample of
agreements, and zero critical mandatory-exclusion false negatives. Factual
truth continues to come from approved source evidence or the hidden structured
oracle manifest.

## Decision

**Refine.** Adopt `factual-qa-v3-design-002` prospectively. Finish the repository
correctness program before preparing or authorizing any private semantic-review
run. Dataset generation, held-out evaluation, and scale remain closed.
