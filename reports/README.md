# Reports

Use this folder for shareable figures, generated report assets, and presentation
materials.

Generated outputs should go under `generated/`, which is ignored by default.

## Professor-fidelity closeout

The durable technical report for the paused professor-fidelity evaluation is
[Professor fidelity evaluation closeout](professor-fidelity-closeout-2026-08-17/report.html).
Its adjacent `artifact.json` is the validated source payload used to build the
self-contained report. The current report uses professor-fidelity analysis
correction 001, which preserves the original result while correcting the
repeat scope, citation denominator, and hidden-hard-gate interpretation.

## Current RAG numbers

Run `python3 scripts/plot_current_rag_numbers.py` to create compact CSV tables,
a Markdown table, and a Matplotlib figure under `reports/generated/` for a
numbers-first supervisor discussion.
