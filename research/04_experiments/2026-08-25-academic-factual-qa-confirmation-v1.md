# Academic factual-QA confirmation v1

Date: 2026-08-25

Status: protocol frozen; sources, questions, reference labels, models, and
execution unopened

Owner issue: [#127](https://github.com/horiiiiii032929/digital-twin/issues/127)

## Decision being tested

On fresh source and question-family clusters, does the two-boundary T0 method
reduce unsupported releases relative to the any-hit control while retaining
supported answers and complete, source-valid citations?

This is a method confirmation, not a 10,000-row stress test, Professor Digital
Twin fidelity test, learning-outcome study, or deployment qualification.

## Why this design

Recent primary RAG-evaluation work supports separating context relevance,
answer faithfulness, and answer relevance rather than compressing them into one
judge score. ARES also uses human annotations to correct automated evaluation;
GaRAGe uses human-curated grounding passages and explicitly tests deflection
when evidence is insufficient; DataMorgana treats workload diversity as a
first-class benchmark design concern. These sources inform the design but do
not substitute for project-specific validation:

- [ARES, NAACL 2024](https://aclanthology.org/2024.naacl-long.20/)
- [DataMorgana, ACL Industry 2025](https://aclanthology.org/2025.acl-industry.33/)
- [GaRAGe, Findings of ACL 2025](https://aclanthology.org/2025.findings-acl.875/)
- [MEMERAG, ACL 2025](https://aclanthology.org/2025.acl-long.1101/)

The prior 160-case result remains development evidence because its source
aliases and questions were authored together. Confirmation v1 therefore changes
the data and review provenance, not the product method.

## Sampling and independence

Confirmation v1 contains 200 cases in 100 source-family clusters. Every cluster
contains exactly one answerable and one boundary case. A source artifact,
source family, underlying fact, or question family may occur in only one
cluster. No cluster may overlap the earlier development datasets.

The public-source confirmation covers four computing-course strata with 25
clusters and 50 cases per course. The answerable and boundary allocations are
fixed before sources or questions are opened:

| Answerable slice | Cases |
| --- | ---: |
| Direct text | 20 |
| Paraphrase text | 20 |
| Multi-source | 20 |
| Code | 10 |
| Table | 10 |
| Diagram | 10 |
| Equation | 10 |
| **Total** | **100** |

| Boundary slice | Cases |
| --- | ---: |
| No evidence | 20 |
| Cross-course confusion | 20 |
| Ambiguous question | 15 |
| Stale version | 10 |
| Academic integrity | 15 |
| Permission filtered | 10 |
| Unsupported premise | 10 |
| **Total** | **100** |

Confirmation sources must be public-domain or openly licensed computing
materials with exact version hashes, license evidence, retrieval dates, and
modality records. Public-source confirmation avoids opening the Academia Vault
without new authority. It cannot establish external validity on private course
materials; that remains a separate real-source checkpoint.

## Reference-label workflow

Candidate questions may be proposed deterministically or by multiple LLMs, but
the authoring role cannot set authoritative labels. Automated reviewers remain
advisory.

1. A case author proposes the question, action, atomic claims, and evidence.
2. Human reviewer A, who did not author the case, independently validates all
   200 cases without seeing product outputs or condition identities.
3. Human reviewer B independently labels a fixed stratified 60-case sample—30
   answerable and 30 boundary—and every case escalated by deterministic or
   advisory checks.
4. Disagreements retain both original labels and receive stable IDs before
   adjudication.
5. Action agreement, Cohen's kappa, evidence-link exact agreement, and claim-set
   agreement are reported. All disagreements must be adjudicated before the
   reference set is sealed.

If the required human review cannot be obtained, the resulting dataset may be
reported as source-linked silver evidence but cannot produce a `Keep` or
production-selection decision.

## Paired system comparison

Each case is evaluated under the same corpus, retriever, generator, decoding,
policy, and persisted draft:

- any-hit T0 control;
- structured evidence-selection ablation;
- evidence selection plus post-generation atomic-claim validation.

Gold actions, claims, evidence, source IDs, and citations remain outside the
product boundary until after the response is persisted. Draft hashes must match
between the ablation and candidate whenever generation is allowed.

## Prospective gates

The following gates are fixed before opening sources or labels:

- zero severe unsupported releases;
- 100% source/version-valid citations on released answers;
- at least 95% supported-answer retention;
- at least 95% action accuracy overall and at least 90% within answerable and
  boundary strata;
- at least 98% atomic-claim precision and 95% atomic-claim recall;
- at least 98% citation precision, 95% citation recall, and 95% complete-evidence
  rate;
- at least 95% Evidence Recall@5 and 90% all-evidence@3;
- zero exact normalized duplicates and human disposition of every flagged
  near-duplicate;
- no more than one malformed response, complete accounting, and no identity or
  persistence drift;
- candidate supported retention has a cluster-bootstrap 95% lower paired
  difference of at least -3 percentage points versus control.

With one boundary case in each of 100 independent clusters, observing zero
severe releases gives a one-sided 95% binomial upper bound of about 2.95%; it
does not prove zero risk. The later 600-case final tranche uses 300 boundary
clusters, reducing the analogous bound to about 1.0%. Confirmation v1 therefore
decides whether to proceed to final evidence, not whether the product is ready
for release.

Primary intervals use 10,000 cluster-bootstrap replicates with seed 20260825.
Raw numerators and denominators, exact zero-event bounds, and all slices are
reported. P-values are descriptive and are not promotion gates.

## Failure and progression

- `Keep-for-final-confirmation`: every gate passes and the independent labels
  are complete; this permits designing the 600-case final tranche only.
- `Refine`: a data, label, harness, integration, or operational defect makes the
  result untrustworthy.
- `Go Deeper`: the result is valid but uncertainty, coverage, or human evidence
  is insufficient.
- `Drop`: the candidate causes a material safety, quality, or operational
  regression.

A failed or consumed confirmation is immutable. Diagnose and change the method
only on development data, then create a new confirmation version with fresh
clusters. Never tune on confirmation or final cases.

## Current stopping boundary

This checkpoint freezes the design only. No source manifest, case text,
reference label, model/provider binding, provider call, private source,
confirmation execution, product selection, or release promotion is authorized.
The next human-dependent input is an eligible public-source manifest and named
independent reviewer arrangement.
