# Source-aligned retrieval confirmation 001 results

## Decision

**Refine.** None of the six frozen retrieval methods passed every prospective
gate, so the AFQC-101 factual branch stops before product generation and before
the 10,000-case final split.

The run was valid and complete. It used 32 direct OpenAI embedding calls, zero
retries, 95,638 input tokens, and USD 0.00717285. All 500 public rankings were
persisted before hidden gold opened. There was no private data, human
participant, final-split access, identity drift, course violation,
source-version violation, or severe unsupported release.

## Results

| Method | Complete evidence@3 | Evidence Recall@5 | Boundary accuracy | p95 latency | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| M0 BM25 | 85.75% | 99.00% | 99.00% | 0.76 ms | Refine |
| M1 OpenAI small dense | 89.25% | 98.50% | 99.00% | 8.62 ms | Refine |
| M2 BM25 + OpenAI small | **89.75%** | 99.25% | 99.00% | 8.42 ms | Refine |
| M3 OpenAI large dense | **89.75%** | 99.25% | 99.00% | 17.18 ms | Refine |
| M4 BM25 + OpenAI large | 89.25% | **99.75%** | 99.00% | 17.06 ms | Refine |
| M5 large hybrid + hierarchy | 75.25% | 95.38% | 99.00% | 19.64 ms | Refine |

The frozen gates were 90% complete evidence@3, 95% Evidence Recall@5, 98%
boundary accuracy, zero severe/course/version violations, and retrieval p95 no
greater than two seconds. M2 and M3 missed the complete-evidence gate by one
of 400 answerable cases.

## Failure diagnosis

This is a genuine top-three evidence-selection failure rather than an
operational or source-binding failure. For M2, 41 answerable cases missed
complete evidence@3; 37 of those had every required region by rank four, 38 by
rank five, and three still lacked a required region at rank five. The misses
were concentrated in paraphrased, definition, direct-factual, and structured
code questions. M2 and M3 shared only 15 of their 41 misses, so a deterministic
coverage selector over a broader candidate pool is a plausible method-level
successor; changing only the embedding model is not supported.

One cross-course boundary case was classified as `clarify` instead of the gold
`abstain`. It released no answer and therefore was not severe, but it keeps the
boundary result below 100%.

## Next boundary

Do not relax the gate, score product answers, or open the final 10,000 cases
from this result. A successor may make one explicit method-level change:
retrieve a broader source-aligned pool and select the top three regions by
deterministic question-concept and required-coverage signals, then confirm it
on a new source-family-disjoint development tranche. The current 500 cases are
known diagnostic evidence and cannot become fresh confirmation data.

The independent non-human visual, synthetic-profile, local workflow, and
policy evaluations may continue. Real professor/student evaluation remains a
separate human-gated stage.

## Evidence

- Machine-readable record:
  `research/05_evaluation/records/academic-factual-qa-source-aligned-retrieval-confirmation-001.json`
- Ignored rankings and runtime summary:
  `reports/generated/academic-factual-qa-source-aligned-retrieval-confirmation-001/`
- Execution revision: `55837d0c371c52658b8d4e6d5b67fc3f31cd4c4b`
- Public rankings content SHA-256:
  `bfec3b9f87d5797f523b19034c63b743d869f3075fc0a65ca57148d8c6eb2318`
