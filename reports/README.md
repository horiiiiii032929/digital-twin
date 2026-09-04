# Reports

Use this folder for shareable figures, generated report assets, and presentation
materials.

Generated outputs should go under `generated/`, which is ignored by default.

## Final-report diagrams

Editable Draw.io sources for the IT5004-aligned final-report diagrams live in
`figures/drawio/`. Render an approved source to both reviewable SVG and
LaTeX-ready PDF with:

```bash
DRAWIO_CLI="/Applications/draw.io.app/Contents/MacOS/draw.io"
"$DRAWIO_CLI" --export --format svg --crop --border 16 --embed-diagram \
  --output reports/figures/FIGURE.svg reports/figures/drawio/FIGURE.drawio
"$DRAWIO_CLI" --export --format pdf --crop --border 16 \
  --output reports/figures/FIGURE.pdf reports/figures/drawio/FIGURE.drawio
```

Rendered files in `reports/figures/` are intentional review artifacts. Proposed
deployment diagrams must retain a visible “not implemented or evaluated” label.
The Graphviz files under `figures/source/` are retained as early content and
layout sketches; they are not the authoritative source for the converted
IT5004 system-design diagrams.

## Professor-fidelity closeout

The durable technical report for the paused professor-fidelity evaluation is
[Professor fidelity evaluation closeout](professor-fidelity-closeout-2026-08-17/report.html).
Its adjacent `artifact.json` is the validated source payload used to build the
self-contained report. The current report uses professor-fidelity analysis
correction 001, which preserves the original result while correcting the
repeat scope, citation denominator, and hidden-hard-gate interpretation.
