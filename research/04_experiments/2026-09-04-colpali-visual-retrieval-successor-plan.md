# ColPali-style visual retrieval successor plan

## Decision question

Can direct multi-vector retrieval over original visual regions correct the
fine-grained evidence failures measured in `true-visual-supplement-003`, while
preserving exact course isolation, boundary safety, and original-region
citation lineage?

This is a retrieval-method comparison. It does not by itself establish
complete multimodal question answering, representative performance on
professor materials, or real-student utility.

## Prior evidence and diagnosis

`true-visual-supplement-003` is retained as an immutable `Refine` result. It
retrieved 27/30 answerable assets in the top three and preserved 30/30
original-region lineage and boundary safety, but only 19/30 assets met the
visual-fact completeness rule. Diagram recall was the largest failure slice.

The earlier method converted each whole visual into a question-independent
free-text description and indexed that description with BM25. This flattened
table cells, equation symbols, spatial relationships, and diagram edges into
one lexical sequence. The reported 219 unmatched segments are a conservative
lexical-reference proxy against non-exhaustive canonical answers; they are not
219 independently verified hallucinations.

## Selected successor

The candidate follows the ColPali family of document-image retrieval:

1. Preserve every original table, diagram, or equation region as the citation
   authority.
2. Encode each visual region and query as multiple token-level vectors.
3. Rank course-scoped regions with late-interaction MaxSim instead of flattening
   the visual into one description string.
4. Return original source, version, asset hash, render hash, and region bounds
   with every hit.

The first implementation uses first-party Jina Embeddings v4 because its
official interface supports image/PDF input and multi-vector output in one
model. The method is based on ColPali's visually rich document-retrieval
design. Jina output remains non-authoritative: deterministic source lineage,
course policy, boundary decisions, and citations control release.

References:

- ColPali paper: <https://arxiv.org/abs/2407.01449>
- Jina Embeddings v4: <https://jina.ai/models/jina-embeddings-v4/>
- Gemini Embedding 2 alternative: <https://ai.google.dev/gemini-api/docs/embeddings>
- Docling document model: <https://github.com/docling-project/docling/blob/main/docs/concepts/docling_document.md>

Gemini Embedding 2 remains a credible single-vector multimodal alternative,
but the measured failure concerns fine-grained internal visual relationships;
multi-vector late interaction is therefore the better first comparison.
Docling is intentionally deferred because adding a new document parser and a
new retriever in the same experiment would obscure which change caused any
improvement. If retrieval passes but answer construction still loses table or
diagram structure, Docling becomes a separately preregistered ingestion
candidate.

## Frozen comparison

Baseline: source-visible text indexed with BM25.

Candidate: `jina-embeddings-v4` multi-vector image/query embeddings ranked by
`visual-late-interaction-maxsim-v1`.

The only changed factor is visual representation and ranking. Both conditions
use the same fresh source-disjoint 30-asset package:

- 10 tables;
- 10 diagrams;
- 10 equations;
- one answerable and one boundary case per asset;
- six cases for each boundary class: no evidence, cross-course, stale version,
  permission, and unsupported premise.

No answer, expected evidence, or gold label is sent to the embedding provider.
Boundary cases make zero provider calls and are resolved by deterministic
policy. Generated rasters remain ignored; committed metadata binds every
region to its public source, licence, version, character range, file hash,
render hash, and normalized crop coordinates.

## Metrics and gates

Primary retrieval gates:

- complete visual evidence@3 at least 27/30;
- visual evidence recall@5 at least 29/30;
- evidence@3 at least 8/10 in each modality;
- diagram evidence@3 improvement over BM25 at least 10 percentage points;
- original-region lineage and course isolation 30/30;
- the paired 30 boundary cases remain structurally validated and make zero
  calls in this retrieval-only checkpoint. Their action safety is not claimed
  here; it is measured by the later actual-product checkpoint using only
  product-visible inputs.

The network-free simulation proves contracts and accounting only. It is not a
quality result. A live provider run must be separately frozen, use an exact
first-party model binding, make at most 60 calls with zero retries, and retain
the USD 1 emergency stop.

## Progression rule

- `Keep`: all retrieval gates pass. Freeze the embedding result, then build a
  separate actual-product checkpoint that retrieves without gold leakage,
  answers from the selected original regions, and validates claims and region
  citations.
- `Refine`: a valid quality gate fails. Preserve the result and make a
  method-level decision; do not tune against these 30 assets.
- `invalid-execution`: identity, accounting, ledger, source-hash, or harness
  integrity fails. Correct only the demonstrated operational defect.

Even after `Keep`, the release remains text/OCR fallback until the separate
actual-product checkpoint passes. A 30-asset result remains a targeted
supplement and cannot support a representative multimodal-capability claim.
