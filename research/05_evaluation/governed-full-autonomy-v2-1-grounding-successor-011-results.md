# Grounding successor 011 results

## Outcome

`Keep` for the source-contract-aligned grounding method. The fresh 500-case candidate and fixed 100-case control completed with zero provider calls, zero cost, and no gold leakage. Every frozen gate passed.

## Headline results

- Fully grounded factual success: **99.25%** (source-family bootstrap lower 95% bound: **98.0%**).
- Boundary action accuracy and safety: **100%**.
- Claim and citation precision/recall: **99.25%**.
- Source-version validity: **100%**.
- Complete evidence@3 and evidence recall@5: **99.75%**.
- Paired supported-answer retention delta: **0.0 percentage points**; boundary safety was **100%** for both conditions.

## Failure audit

Three answerable labels did not produce a fully grounded answer. One question contained an unresolved deictic reference (`these`); the product's `clarify` response was the safer behavior, but the frozen answer label was not changed after execution. Two cases retrieved and selected the correct source atoms, then failed closed because the post-generation NLI validator compared canonical source claims with LaTeX authoring markup. This exposed a shared source-contract mismatch, not a retrieval failure.

The validator correction is prospective: canonical claims registered from immutable source atoms are now checked against that same server-owned canonical contract. The 99.25% result is preserved unchanged and the corrected implementation must be confirmed on fresh cases before release binding.

## Decision boundary

Select ambiguity-safe source-semantic evidence atoms V2 plus the deterministic evidence-set compiler as the grounding successor. Retain T0 and the prior source-semantic method as rollback. This result does not promote T1-v2 or establish professor fidelity, human usability, real learning improvement, or visual reasoning.
