# Presentation diagrams — first draw.io draft

Status: superseded for presentation use by the [standard C4/UML set](standard/README.md).
The four custom-layout diagrams below remain historical drafts, not recommended insertion assets.

English diagram assets for the presentation. Video work remains paused. No slide deck has been produced.

## Files

- [Editable draw.io source, four pages](presentation-diagrams.drawio)
- [Review PDF, four pages](presentation-diagrams.pdf)

| Page | Intended slide | PNG for insertion | SVG for scaling |
| --- | --- | --- | --- |
| System boundaries and comparison points | 6 | [PNG](01-system-boundaries.png) | [SVG](01-system-boundaries.svg) |
| Three factual paths and their failure point | 7 | [PNG](02-factual-designs.png) | [SVG](02-factual-designs.svg) |
| Planner designs and retained fallback | 10–12, overview asset | [PNG](03-planner-designs.png) | [SVG](03-planner-designs.svg) |
| Assessment and planner input gap | 16; reference for 24 | [PNG](04-learner-input-gap.png) | [SVG](04-learner-input-gap.svg) |

Each canvas is 1600 × 900. PNG exports are approximately 2400 × 1350, with the draw.io source embedded. Boxes, text and connectors are native editable draw.io elements. Exported images are the intended slide-insertion assets; the PDF is for reviewing this batch.

White background, Arial type, restrained blue for comparison components, green for retained controls, amber/red for limitations. Explicit text labels carry the meaning as well as colour.

## Evidence and interpretation

### 01 — System boundaries

Sources: [reported architecture](../../figures/course-twin-architecture.dot), [learner-decision detail](../../../research/06_reports/final/chapters/learner-decision-detail.tex), and [comparison ledger](../design-comparisons.md).

This is a simplified map of service responsibilities and comparison points, not a deployment topology or complete request sequence. The component panel groups mechanisms evaluated in different studies; it does not assert that every candidate runs together. BKT/PFA remain experimental rather than connected to the default adapter.

### 02 — Factual-path comparison

Source: [Round 1 results](../../../research/05_evaluation/course-digital-twin-whole-system-architecture-round-1-001-results.md).

All values belong to the same 495-case development comparison. “Grounded” abbreviates grounded factual success; “Answerable action” is the reported answerable-action metric. The coverage checks in the two complex paths counted question scaffolding as required evidence. The lexical control still selected incomplete or incorrect source regions. None passed the frozen quality gates. This is not a general rejection of hierarchical architecture or event sourcing.

### 03 — Planner design comparison

Sources: [comparison build](../../../research/05_evaluation/successor-architecture-paired-comparison-001-build-001-results.md), [Fold 003 audit](../../../research/05_evaluation/successor-architecture-fold-003-causal-audit-001-results.md), [Fold 004](../../../research/05_evaluation/successor-architecture-policy-value-fold-004-001-results.md), and [planner decision rules](../../../research/06_reports/final/chapters/learner-decision-detail.tex).

This is a structural comparison. It does not merge scores across folds. The H guard requires a valid permitted proposal, analytic-best agreement and a gain of at least 0.04 over fallback; absence of authorized evidence still yields no action. Model-specific added value has not been isolated by the analytic-only ablation proposed in the presentation.

### 04 — Learner evidence gap

Source: [learner-decision detail](../../../research/06_reports/final/chapters/learner-decision-detail.tex), specifically the assessment-confidence, goal-completion and planner-proxy equations.

Here a is the count of assessed attempts, d the delivered goal-action count, and k the number of supporting observation identifiers. The completion rule also requires a valid same-domain objective mapping and nonempty target concepts. Missing or ambiguous mappings remain incomplete. An earlier incorrect count can continue to block completion; the rule does not execute arbitrary free-text success conditions.

The bottom adapter replacement is a proposed comparison, not a measured improvement. A completed software goal or a larger planning proxy does not establish real learning gains.

## Editing and export

Open the draw.io source in draw.io Desktop and select the page tab. Edit the native objects, then use File → Export as → PNG or SVG. Keep the 16:9 canvas and inspect the exported image at presentation size.

To rebuild the initial layouts from the generator:

```sh
uv run python -m scripts.build_presentation_diagrams --export
```

This rebuild replaces the generated draw.io file, so use draw.io's export command directly after manual layout edits unless those edits are also incorporated into the generator.

## Verification

The four pages were exported through draw.io Desktop 30.0.4 and visually inspected. A text overflow in the plan-observe path was corrected. Connectors use native source/target bindings. Numeric results were checked against the cited Round 1 record, and the learner formulas and guard threshold against the report chapter.

Remaining diagram work includes instructor-setting consumers, the detailed H decision branch, goal-scope correction, and the authority/retry sequence. This batch establishes the first four reusable assets.
