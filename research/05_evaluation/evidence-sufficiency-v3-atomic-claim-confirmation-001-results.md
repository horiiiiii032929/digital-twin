# Atomic-claim evidence confirmation 001

## Decision

**Keep the post-generation NLI atomic-claim method.** It passed every frozen
quality and operational gate on the fresh 120-case confirmation. The one-time
local authorization is revoked. Product binding remains a separate checkpoint.

## Execution

- Clean revision: `c9208cbffc4d058c6fbb0523c78eaad9388ef4f3`
- Dataset: 120 fresh synthetic-public cases, opened once
- Distribution: 40 supported and 80 reject cases across 12 balanced slices
- Control: normalized exact-quote containment, unselectable
- Candidate: `cross-encoder/nli-deberta-v3-base` at revision
  `6c749ce3425cd33b46d187e45b92bbf96ee12ec7`
- NLI direction: eligible evidence as premise, atomic claim as hypothesis
- Deterministic authority: active lineage, schema, complete claim coverage, and
  final release or safe fallback
- Provider calls, paid cost, private data, and held-out access: zero

## Results

| Method | False releases | Supported retention | Multi-claim retention | Mutation / lineage / malformed rejection | p95 | Added memory | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Exact-quote control | 0 | 50.0% | 50.0% | 100% / 100% / 100% | 0.04 ms | 245,760 B | Fail / unselectable |
| NLI atomic-claim validator | 0 | 95.0% | 90.0% | 100% / 100% / 100% | 53.15 ms | 599,932,928 B | Keep |

The NLI candidate safely rejected all 80 reject cases and released 38/40
supported cases. It met the frozen minimums of 90% supported retention and 90%
multi-claim retention, the zero-false-release requirement, the complete
mutation/lineage/malformed rejection requirements, the 500 ms p95 ceiling, and
the 2 GiB added-memory ceiling.

## Direct priority audit

Codex directly inspected all 12 prioritized cases against the claim text,
eligible evidence, declared lineage, expected action, and candidate decision.
All 12 labels and expected actions were confirmed.

The only candidate errors were two conservative false rejections in the
supported-paraphrase-multi slice:

- `acv-08-paraphrase-multi`: the model rejected a faithful paraphrase that data
  leakage can make evaluation look better than reality.
- `acv-09-paraphrase-multi`: the model rejected a faithful paraphrase that CSP
  limits where page content may be loaded from.

These errors reduce usefulness but do not create an unsupported release. Ten
stratified controls confirmed exact/paraphrased support, all-claim coverage,
contradiction, unsupported addition, wrong lineage, stale-source, and
cross-course behavior. No ground-truth or harness correction is needed.

## Durable evidence and limitations

- Canonical result SHA-256:
  `42f39eb840ebfc858f3d68e5935bc2bda5223a8aa6464eda9e06f282f77c29c8`
- Raw ignored result SHA-256:
  `95ea159e7c13982905754f6c97cd2ce17a437ae5a09296c515c9bdbb1cd30256`
- Direct review:
  `judgments/evidence-sufficiency-v3-atomic-claim-confirmation-001-priority-review-001.json`

This synthetic confirmation validates the release boundary, not realistic
product-generated prose, retrieval quality, Professor Digital Twin fidelity,
autonomous tutoring, multimodal grounding, deployment, or human usability.
Latency and memory are machine-specific. The two false rejections show that the
gate must retain a safe fallback and observability for conservative abstention.

## Next checkpoint

Bind the selected validator to one immutable product revision, preserve T0 as
rollback, and rerun complete grounded publication/student journeys. Do not tune
the frozen threshold on this confirmation or automatically promote T1,
deployment, or human-pilot access.
