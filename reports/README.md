# Reports

Start with the [submitted snapshot](submitted/2026-09-06/README.md) for the
unchanged abstract, report and source package. The
[LaTeX guide](../research/06_reports/final/README.md) describes the current build.

Generated outputs should go under `generated/`, which is ignored by default.

## Final-report diagrams

The current manuscript uses the `course-twin-*.pdf` figures referenced by its
chapter sources. Their vector builder is `figures/build_sdlc_figures.py`.
Building the LaTeX report uses the checked-in figure PDFs; it does not require
regenerating them.

Earlier editable Draw.io sources live in
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
The Graphviz files under `figures/source/` and earlier Draw.io sources are
retained for design history. They should not be substituted for the current
manuscript's figure files.

## Professor-fidelity closeout

The durable technical report for the paused professor-fidelity evaluation is
[Professor fidelity evaluation closeout](professor-fidelity-closeout-2026-08-17/report.html).
Its adjacent `artifact.json` is the validated source payload used to build the
self-contained report. The current report uses professor-fidelity analysis
correction 001, which preserves the original result while correcting the
repeat scope, citation denominator, and hidden-hard-gate interpretation.
