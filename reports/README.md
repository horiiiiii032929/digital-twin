# Reports

Start with the [submitted snapshot](submitted/2026-09-06/README.md) for the
unchanged abstract, report and source package. The
[LaTeX guide](../research/06_reports/final/README.md) describes the current build.

Generated outputs should go under `generated/`, which is ignored by default.

## Presentation planning

The current proposed rebuild is the [Japanese revision 15 outline](presentation/planning/structure-revision-15-product-first-ja.md):
32 pages following the actual product experience, implementation-backed sequence diagrams,
failed designs, evaluation, and continuing development. It specifies each page's
visible explanation and standalone comprehension check. Its approximately 35-minute
budget assumes a proposed two-minute demo edit; the PowerPoint and script have not
yet been rebuilt from this outline. The earlier materials below remain historical.

The [presentation structure](presentation/presentation-structure.md) proposes
a 24-slide English talk with an estimated 35–38-minute core, including a one-minute
recorded simulation, plus time for questions. It opens with delivery against the
project brief and an actual teaching-profile response, then compares the system designs
tested, their failure mechanisms and the resulting decisions for a software
engineering expert. The [design comparison matrix](presentation/design-comparisons.md)
records each alternative, its intended benefit, observed weakness and disposition.
The [visual plan](presentation/visual-plan.md) maps report diagrams
and application screens to the talk, while the
[speaking script](presentation/speaker-script.md) supports online delivery.
[Anticipated questions](presentation/defence-notes.md) provide short English
answers to the scrutiny addressed in the main presentation.

The [recording preparation pack](presentation/recording/README.md) contains
synthetic PDF materials, actor URLs, repeatable rehearsal commands, English
input copy and the onboarding-to-follow-up shot list. The [recorded 2:50 film](presentation/recording/recorded-video.md)
now includes browser-only footage, four recorded sessions and a labelled service replay.
The materials include Japanese speaking cues, timing and submitted-report
evidence anchors for joint review.

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

The English graduate-school presentation is in
[presentation/deck/](presentation/deck/README.md), with an embedded actual-software
demo, English speaker notes, a static PDF and editable draw.io sources. It retains
historical study scopes and corrections and does not modify the submitted report.

## Final presentation demos

See [IT5004 recording and verification](presentation/recording/it5004-final/README.md) for the real-screen demo sources, reproducible editing commands, and final packaging checks.
