# Finite evaluation program 004 invalid result

## Outcome

The factual retrieval stage is `invalid-execution`, not a valid quality
failure. A post-run exact-matchability audit found that the runtime corpus and
hidden gold were different evidence representations:

- 456 answerable gold references were required;
- 0/456 exactly matched a runtime retrieval unit;
- 393/456 were contained by a broader runtime parent section;
- 63/456 were not contained by any runtime unit.

The reported 36.60–38.30% all-evidence@3 and 40.64–43.19% Recall@5 values are
therefore non-interpretable and must not be used to compare retrievers or the
product. The runner should have applied its existing exact-matchability check
before paid indexing and ranking. Product development and the sealed
10,000+1,000 evaluation did not execute.

The independent supplements remain usable diagnostic evidence because they did
not depend on the mismatched factual corpus. The 30-asset/60-case visual run
reached 17/30 complete visual evidence@3, 76.13% atomic Recall@5, zero boundary
releases, and 30/30 original-region lineage; ten descriptions added unsupported
details, so visual remains `Go Deeper`. The 12-case synthetic C0-C2 profile
diagnostic completed 36/36 calls but is not professor-fidelity evidence.

## Accounting and isolation

- 74 provider calls/batches; USD 0.05216944 total.
- Eight query-embedding batches, 30 visual calls, and 36 profile calls.
- Zero product-development, final-construction, final-product, or provider-
  backed T0/T1 calls.
- Hidden gold was joined for the invalid retrieval analysis, but the product
  never received gold.
- The sealed 10,000+1,000 product evaluation was not executed.
- Only public licensed sources and synthetic profiles were used.

## Decision

Preserve program 004 as invalid evidence and draw no factual-quality
conclusion. Program 005 is the single harness-only successor: it restores the
already reviewed action-router 500+100 package, uses its exactly matchable
non-overlapping atomic corpus, and makes exact reference matchability a
mandatory network-free pre-ranking gate. It also atomizes the final corpus
before any 10,000+1,000 execution.

The qualified local deterministic R1 remains unchanged. Professor fidelity,
external usability, learning outcomes, and hosted-production claims remain
open.

## Limitations

- Program 004 cannot support a retriever or factual-product decision.
- Visual and synthetic-profile results are model-assisted diagnostics without
  independent external human annotation.
- Visual descriptions are advisory and non-authoritative.
- C0-C2 used a synthetic profile; no real professor approved it.
