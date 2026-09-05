# True visual omni confirmation 002 result

## Outcome

`completed-refine` / **Drop from release selection**.

On 30 fresh, source-disjoint answerable visual questions, the current Jina v5
omni candidate produced 16/30 fully grounded answers (53.3%), compared with
26/30 (86.7%) for the text/OCR control. Both conditions safely released zero
answers on the 30 boundary cases.

## What failed

- Fully grounded success: 16/30, below the preregistered 27/30 gate.
- Original-region lineage: 16/30, below the required 30/30.
- Paired grounded delta: -33.3 percentage points, below the non-regression gate.
- Failure concentration: 10 packet layouts, one protocol flow, and three
  architecture charts.

The candidate failed closed rather than releasing unsupported content: it had
zero boundary releases, unsupported claims, invalid citations, or wrong-course
retrieval. The provider completed all 90 calls without retry or identity drift,
using 10,087 tokens with 1.11-second p95 latency.

## Decision

Do not select `jina-embeddings-v5-omni-small` for the final local release. Keep
the text/OCR path as the operational fallback. The control itself had one
invalid or wrong-region citation, so this result does not support a
representative visual-capability claim.

Historical Jina v4 retrieval evidence remains valid as component evidence, but
its prior actual-product checkpoint also failed selection. This fresh result is
not tuned or rerun.

## Scope and limitations

The dataset uses 30 open-licensed networking assets and is source-disjoint from
the earlier visual sets. It covers packet layouts, protocol flows, and
architecture charts, not every course modality. Generation is deterministic
and extractive; pedagogical response quality is outside this checkpoint.

Raw response and quota ledgers remain ignored under
`reports/generated/true-visual-omni-confirmation-002/`; their hashes are pinned
in the machine-readable record.
